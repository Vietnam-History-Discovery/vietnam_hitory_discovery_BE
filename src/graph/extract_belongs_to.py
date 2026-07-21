import os
import json
import re
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Initialize LLM Client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "google/gemini-2.5-flash")

def call_llm(prompt: str) -> str:
    """Call Groq or OpenRouter client depending on what's configured in .env."""
    if GROQ_API_KEY:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        return resp.choices[0].message.content
    elif OPENAI_API_KEY:
        from openai import OpenAI
        client = OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        return resp.choices[0].message.content
    else:
        raise ValueError("No GROQ_API_KEY or OPENAI_API_KEY found in environment.")

def clean_json_output(text: str) -> list[str]:
    """Clean LLM output and parse the JSON list."""
    text = text.strip()
    # Remove markdown code blocks if any
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # Try parsing
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(item).strip() for item in data]
    except Exception as exc:
        print(f"[WARN] JSON parsing failed: {exc}. Trying regex fallback on: {text}")
        
    # Regex fallback: find all quoted strings
    matches = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', text)
    if matches:
        return [m.strip() for m in matches]
    return []

def extract_belongs_to():
    if not NEO4J_URI or not NEO4J_PASSWORD:
        print("❌ Error: Missing Neo4j credentials in environment.")
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # 1. Fetch dynasties
        print("🏛️ Fetching all Dynasties...")
        dynasty_rows = session.run("MATCH (d:Dynasty) RETURN d.name as name").data()
        dynasties = [r["name"] for r in dynasty_rows]
        print(f"Found {len(dynasties)} dynasties: {dynasties}\n")
        
        # We will collect all mappings to run in batch updates
        person_mappings = []
        event_mappings = []
        
        for dynasty in dynasties:
            print(f"🔍 Processing dynasty: '{dynasty}'")
            
            # A. Get Person candidates
            person_rows = session.run("""
                MATCH (p:Person)-[:MENTIONED_IN]->(c:Chunk)-[:BELONGS_TO_DYNASTY]->(d:Dynasty {name: $dynasty})
                RETURN DISTINCT p.name as name
            """, dynasty=dynasty).data()
            person_candidates = [r["name"] for r in person_rows if r["name"]]
            
            if person_candidates:
                print(f"   👥 Person candidates ({len(person_candidates)}): {person_candidates[:15]}...")
                prompt = f"""Bạn là một nhà sử học chuyên nghiệp về Lịch sử Việt Nam.
Dưới đây là danh sách các nhân vật lịch sử được nhắc đến trong các tài liệu liên quan đến triều đại: "{dynasty}".
Danh sách ứng viên: {json.dumps(person_candidates, ensure_ascii=False)}

Hãy phân loại và lọc ra danh sách các nhân vật THỰC SỰ sống, trị vì, làm quan hoặc hoạt động chính dưới thời kỳ của triều đại "{dynasty}".
Lưu ý quan trọng:
- Chỉ chọn các nhân vật trực thuộc hoặc gắn liền trực tiếp với triều đại này.
- Loại bỏ các nhân vật thuộc triều đại khác chỉ xuất hiện do được nhắc đến so sánh (ví dụ: Trần Hưng Đạo không thuộc nhà Ngô; Ngô Quyền không thuộc nhà Lý; Lê Hoàn không thuộc nhà Ngô; Đinh Bộ Lĩnh không thuộc nhà Ngô).
- Trả về kết quả dưới định dạng duy nhất là một JSON array phẳng chứa các tên nhân vật hợp lệ (ví dụ: ["Ngô Quyền", "Dương Tam Kha"]). Không thêm văn bản giải thích hay markdown code blocks ngoài JSON.
"""
                try:
                    resp = call_llm(prompt)
                    validated_persons = clean_json_output(resp)
                    print(f"   ✅ Filtered Persons ({len(validated_persons)}): {validated_persons}")
                    for p in validated_persons:
                        if p in person_candidates: # Safe check
                            person_mappings.append({"dynasty": dynasty, "name": p})
                except Exception as exc:
                    print(f"   ❌ LLM Person filter failed: {exc}")
            
            # B. Get Event candidates
            event_rows = session.run("""
                MATCH (e:Event)-[:MENTIONED_IN]->(c:Chunk)-[:BELONGS_TO_DYNASTY]->(d:Dynasty {name: $dynasty})
                RETURN DISTINCT e.name as name
            """, dynasty=dynasty).data()
            event_candidates = [r["name"] for r in event_rows if r["name"]]
            
            if event_candidates:
                print(f"   ⚔️ Event candidates ({len(event_candidates)}): {event_candidates[:15]}...")
                prompt = f"""Bạn là một nhà sử học chuyên nghiệp về Lịch sử Việt Nam.
Dưới đây là danh sách các sự kiện lịch sử được nhắc đến trong các tài liệu liên quan đến triều đại: "{dynasty}".
Danh sách ứng viên: {json.dumps(event_candidates, ensure_ascii=False)}

Hãy phân loại và lọc ra danh sách các sự kiện THỰC SỰ xảy ra dưới thời kỳ hoặc là sự kiện lập quốc/chính trị của triều đại "{dynasty}".
Lưu ý quan trọng:
- Chỉ chọn các sự kiện xảy ra trực tiếp dưới triều đại này.
- Loại bỏ các sự kiện thuộc triều đại khác chỉ được nhắc đến để so sánh hoặc tham chiếu.
- Trả về kết quả dưới định dạng duy nhất là một JSON array phẳng chứa các tên sự kiện hợp lệ (ví dụ: ["Trận Bạch Đằng 938", "Loạn 12 sứ quân"]). Không thêm văn bản giải thích hay markdown code blocks ngoài JSON.
"""
                try:
                    resp = call_llm(prompt)
                    validated_events = clean_json_output(resp)
                    print(f"   ✅ Filtered Events ({len(validated_events)}): {validated_events}")
                    for e in validated_events:
                        if e in event_candidates: # Safe check
                            event_mappings.append({"dynasty": dynasty, "name": e})
                except Exception as exc:
                    print(f"   ❌ LLM Event filter failed: {exc}")

        # 2. Write Person -> Dynasty relations
        if person_mappings:
            print(f"\n💾 Writing {len(person_mappings)} Person BELONGS_TO_DYNASTY relations...")
            session.run("""
                UNWIND $mappings AS row
                MATCH (p:Person {name: row.name})
                MATCH (d:Dynasty {name: row.dynasty})
                MERGE (p)-[:BELONGS_TO_DYNASTY]->(d)
            """, mappings=person_mappings)
            print("   Done.")

        # 3. Write Event -> Dynasty relations
        if event_mappings:
            print(f"\n💾 Writing {len(event_mappings)} Event BELONGS_TO_DYNASTY relations...")
            session.run("""
                UNWIND $mappings AS row
                MATCH (e:Event {name: row.name})
                MATCH (d:Dynasty {name: row.dynasty})
                MERGE (e)-[:BELONGS_TO_DYNASTY]->(d)
            """, mappings=event_mappings)
            print("   Done.")

    driver.close()
    print("\n🎉 LLM extraction and Neo4j loading completed successfully!")

if __name__ == "__main__":
    extract_belongs_to()
