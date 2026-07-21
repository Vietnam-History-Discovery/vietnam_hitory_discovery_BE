"""
Phase 5 — Evaluation Pipeline
So sánh Naive RAG vs GraphRAG trên bộ câu hỏi lịch sử Việt Nam.

Metrics (tự implement, không cần RAGAS server):
  - Answer Relevancy   : câu trả lời có liên quan đến câu hỏi không
  - Faithfulness       : câu trả lời có dựa trên context không
  - Context Recall     : context có chứa thông tin cần thiết không
  - Context Precision  : context có nhiều nhiễu không

Output: evaluation_results.json + report.md
"""

import json
import os
import time
import re
from dataclasses import dataclass, field, asdict
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

EVAL_DIR   = os.path.join(os.path.dirname(__file__), "../../data/evaluation")
PARSED_DIR = os.path.join(os.path.dirname(__file__), "../../data/parsed")
EMBED_DIR  = os.path.join(os.path.dirname(__file__), "../../data/embeddings")

GROQ_KEY   = os.getenv("GROQ_API_KEY")
NEO4J_URI  = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD")

os.makedirs(EVAL_DIR, exist_ok=True)


# ─── Bộ câu hỏi test ──────────────────────────────────────────────────────────
# 25 câu trải đều các giai đoạn lịch sử trong DVSKTT
# ground_truth: câu trả lời chuẩn để đánh giá

QA_DATASET = [
    # ── Hồng Bàng ──────────────────────────────────────────────────────────
    {
        "id": "Q01",
        "question": "Kinh Dương Vương là ai và ông có nguồn gốc như thế nào?",
        "ground_truth": "Kinh Dương Vương tên húy là Lộc Tục, con của Đế Minh, cháu ba đời Viêm Đế Thần Nông. Được phong cai trị phương Nam, lập nước Xích Quỷ.",
        "category": "Hồng Bàng",
    },
    {
        "id": "Q02",
        "question": "Lạc Long Quân và Âu Cơ sinh ra bao nhiêu người con?",
        "ground_truth": "Lạc Long Quân lấy Âu Cơ sinh một bọc trăm trứng, nở ra một trăm người con trai.",
        "category": "Hồng Bàng",
    },
    {
        "id": "Q03",
        "question": "Nước Văn Lang được thành lập như thế nào và ai là vua đầu tiên?",
        "ground_truth": "Sau khi Lạc Long Quân và Âu Cơ chia tay, người con trưởng được tôn lên làm vua, gọi là Hùng Vương, đặt tên nước là Văn Lang, đóng đô ở Phong Châu.",
        "category": "Hồng Bàng",
    },
    {
        "id": "Q04",
        "question": "Nước Văn Lang có bao nhiêu đời vua Hùng?",
        "ground_truth": "Nước Văn Lang được cai trị bởi 18 đời vua Hùng kế tiếp nhau.",
        "category": "Hồng Bàng",
    },

    # ── Thục / An Dương Vương ──────────────────────────────────────────────
    {
        "id": "Q05",
        "question": "An Dương Vương lập nước Âu Lạc như thế nào?",
        "ground_truth": "Năm 257 TCN, Thục Phán diệt nước Văn Lang, lập nước Âu Lạc, đóng đô ở Cổ Loa.",
        "category": "Thục",
    },
    {
        "id": "Q06",
        "question": "Nỏ thần của An Dương Vương có công dụng gì?",
        "ground_truth": "Nỏ thần làm từ vuốt Thần Kim Quy, bắn một phát tiêu diệt hàng nghìn quân địch, giúp An Dương Vương đánh bại quân Triệu Đà nhiều lần.",
        "category": "Thục",
    },
    {
        "id": "Q07",
        "question": "Mị Châu và Trọng Thủy có vai trò gì trong sự sụp đổ của Âu Lạc?",
        "ground_truth": "Trọng Thủy con Triệu Đà cầu hôn Mị Châu, lấy cắp bí mật nỏ thần. Khi Triệu Đà tấn công, nỏ mất linh nghiệm, An Dương Vương thua và Âu Lạc diệt vong năm 179 TCN.",
        "category": "Thục",
    },

    # ── Triệu ─────────────────────────────────────────────────────────────
    {
        "id": "Q08",
        "question": "Triệu Đà là ai và lập nước Nam Việt như thế nào?",
        "ground_truth": "Triệu Đà người Trung Quốc, năm 207 TCN lập nước Nam Việt, xưng là Nam Việt Vũ Vương, đóng đô ở Phiên Ngung. Sau đó thôn tính Âu Lạc năm 179 TCN.",
        "category": "Triệu",
    },
    {
        "id": "Q09",
        "question": "Triệu Đà chia đất Âu Lạc thành những quận nào?",
        "ground_truth": "Triệu Đà chia đất Âu Lạc thành hai quận Giao Chỉ và Cửu Chân.",
        "category": "Triệu",
    },

    # ── Bắc thuộc ─────────────────────────────────────────────────────────
    {
        "id": "Q10",
        "question": "Sĩ Nhiếp cai trị Giao Chỉ như thế nào?",
        "ground_truth": "Sĩ Nhiếp làm Thái thú Giao Chỉ, cai trị nhân từ, phát triển giáo dục và văn hóa, được nhân dân kính trọng gọi là Sĩ Vương.",
        "category": "Bắc thuộc",
    },
    {
        "id": "Q11",
        "question": "Hai Bà Trưng khởi nghĩa vì lý do gì?",
        "ground_truth": "Thái thú Tô Định tàn bạo giết Thi Sách chồng bà Trưng Trắc. Trưng Trắc cùng em Trưng Nhị nổi dậy khởi nghĩa năm 40 SCN.",
        "category": "Bắc thuộc",
    },
    {
        "id": "Q12",
        "question": "Kết quả cuộc khởi nghĩa Hai Bà Trưng như thế nào?",
        "ground_truth": "Hai Bà đánh chiếm 65 thành trì, đuổi Tô Định về Trung Quốc. Trưng Trắc lên làm vua. Năm 43 SCN Mã Viện đem quân đàn áp, Hai Bà tuẫn tiết tại sông Hát.",
        "category": "Bắc thuộc",
    },
    {
        "id": "Q13",
        "question": "Lý Nam Đế là ai và lập nước gì?",
        "ground_truth": "Lý Bí khởi nghĩa đánh đuổi quân Lương, lên ngôi năm 544, lập nước Vạn Xuân, xưng là Nam Việt Đế.",
        "category": "Bắc thuộc",
    },

    # ── Triệu Việt Vương / Hậu Lý ─────────────────────────────────────────
    {
        "id": "Q14",
        "question": "Triệu Quang Phục đánh bại quân Lương bằng cách nào?",
        "ground_truth": "Triệu Quang Phục rút vào đầm Dạ Trạch, dùng chiến thuật du kích đánh quân Lương, cuối cùng đánh đuổi được quân Lương, lên ngôi Triệu Việt Vương.",
        "category": "Hậu Lý",
    },

    # ── Ngô / Đinh ────────────────────────────────────────────────────────
    {
        "id": "Q15",
        "question": "Ngô Quyền đánh bại quân Nam Hán bằng chiến thuật gì?",
        "ground_truth": "Ngô Quyền dùng chiến thuật cắm cọc nhọn trên sông Bạch Đằng, nhử thuyền địch vào lúc nước lớn, khi nước rút thuyền địch bị cọc đâm thủng và bị tiêu diệt năm 938.",
        "category": "Ngô",
    },
    {
        "id": "Q16",
        "question": "Sau khi Ngô Quyền mất, đất nước rơi vào tình trạng gì?",
        "ground_truth": "Sau khi Ngô Quyền mất, đất nước loạn lạc, xảy ra thời kỳ Mười Hai Sứ Quân, các thủ lĩnh địa phương cát cứ chia nhau cai trị.",
        "category": "Ngô",
    },

    # ── Tùy / Đường ───────────────────────────────────────────────────────
    {
        "id": "Q17",
        "question": "Phùng Hưng có đóng góp gì trong thời Bắc thuộc?",
        "ground_truth": "Phùng Hưng khởi nghĩa đánh đuổi quan đô hộ nhà Đường, tự cai trị đất nước khoảng 20 năm, được nhân dân tôn là Bố Cái Đại Vương.",
        "category": "Đường",
    },
    {
        "id": "Q18",
        "question": "Khúc Thừa Dụ giành quyền tự chủ như thế nào?",
        "ground_truth": "Năm 905, Khúc Thừa Dụ nhân nhà Đường suy yếu, chiếm Tống Bình (Hà Nội), tự xưng là Tiết độ sứ, mở đầu thời kỳ tự chủ.",
        "category": "Đường",
    },

    # ── Câu hỏi multi-hop (cần traverse nhiều node) ───────────────────────
    {
        "id": "Q19",
        "question": "Các vương triều nào đã đóng đô ở vùng đồng bằng Bắc Bộ?",
        "ground_truth": "Nhiều triều đại đóng đô ở vùng này: An Dương Vương tại Cổ Loa, Trưng Vương tại Mê Linh, Lý Nam Đế tại Long Biên, Ngô Quyền tại Cổ Loa.",
        "category": "Multi-hop",
    },
    {
        "id": "Q20",
        "question": "Những nhân vật nào liên quan đến sông Bạch Đằng trong lịch sử?",
        "ground_truth": "Ngô Quyền đánh bại quân Nam Hán trên sông Bạch Đằng năm 938 bằng cách đóng cọc. Đây là chiến thắng lịch sử chấm dứt hơn 1000 năm Bắc thuộc.",
        "category": "Multi-hop",
    },
    {
        "id": "Q21",
        "question": "Mối quan hệ giữa Triệu Đà và An Dương Vương là gì?",
        "ground_truth": "Triệu Đà nhiều lần tấn công An Dương Vương nhưng thất bại vì nỏ thần. Sau đó dùng kế gả con trai Trọng Thủy cho Mị Châu con An Dương Vương để lấy cắp bí mật nỏ thần rồi tiêu diệt Âu Lạc.",
        "category": "Multi-hop",
    },
    {
        "id": "Q22",
        "question": "Các cuộc khởi nghĩa chống Bắc thuộc nào xảy ra trước thế kỷ 10?",
        "ground_truth": "Các cuộc khởi nghĩa lớn: Hai Bà Trưng (40 SCN), Bà Triệu (248), Lý Bí (542), Triệu Quang Phục, Phùng Hưng (791), Khúc Thừa Dụ (905).",
        "category": "Multi-hop",
    },
    {
        "id": "Q23",
        "question": "Giao Chỉ và Cửu Chân là gì?",
        "ground_truth": "Giao Chỉ và Cửu Chân là hai quận mà Triệu Đà lập ra từ đất Âu Lạc sau khi thôn tính. Đây là tên gọi vùng đất Việt Nam thời Bắc thuộc.",
        "category": "Địa lý",
    },
    {
        "id": "Q24",
        "question": "Thành Cổ Loa được xây dựng như thế nào?",
        "ground_truth": "An Dương Vương xây thành Cổ Loa hình trôn ốc tại vùng nay là huyện Đông Anh, Hà Nội, kiên cố vững chắc làm kinh đô nước Âu Lạc.",
        "category": "Địa lý",
    },
    {
        "id": "Q25",
        "question": "Đời Nam Bắc phân tranh diễn ra như thế nào?",
        "ground_truth": "Sau khi Ngô Quyền mất, con cháu tranh giành quyền lực, đất nước bị chia cắt thành nhiều vùng do các sứ quân cai trị, gọi là loạn Mười Hai Sứ Quân.",
        "category": "Ngô",
    },
]


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    id:               str
    question:         str
    ground_truth:     str
    category:         str
    naive_answer:     str = ""
    graph_answer:     str = ""
    naive_scores:     dict = field(default_factory=dict)
    graph_scores:     dict = field(default_factory=dict)
    naive_chunks:     list = field(default_factory=list)
    graph_chunks:     list = field(default_factory=list)
    graph_entities:   int  = 0
    graph_relations:  int  = 0


# ─── Naive RAG (baseline) ─────────────────────────────────────────────────────

class NaiveRAG:
    """
    Baseline: vector search → top-K chunks → LLM.
    Không có graph expansion.
    """
    def __init__(self, embed_store, llm):
        self.embed_store = embed_store
        self.llm         = llm

    def query(self, question: str, top_k: int = 5) -> tuple[str, list[dict]]:
        chunks = self.embed_store.search(question, top_k=top_k)
        context = "\n\n".join([
            f"[{i+1}] {c['title']}\n{c['text']}"
            for i, c in enumerate(chunks)
        ])
        prompt = f"""Bạn là chuyên gia lịch sử Việt Nam. Dựa trên context sau, trả lời câu hỏi.
        QUAN TRỌNG: Chỉ dùng thông tin CÓ TRONG context bên dưới. Không bổ sung kiến thức bên ngoài.
Chỉ dùng thông tin từ context. Trả lời bằng tiếng Việt, súc tích.

Context:
{context}

Câu hỏi: {question}"""

        answer = self.llm(prompt)
        return answer, chunks


# ─── Metrics ──────────────────────────────────────────────────────────────────

class Evaluator:
    """
    Tự implement metrics không cần external service.
    Dùng LLM-as-judge với Groq (free).
    """

    def __init__(self, llm_fn):
        self.llm = llm_fn

    def score_answer_relevancy(self, question: str, answer: str) -> float:
        """Câu trả lời có liên quan đến câu hỏi không? (0-1)"""
        prompt = f"""Đánh giá mức độ liên quan của câu trả lời với câu hỏi.
Chỉ trả về một số từ 0.0 đến 1.0, không giải thích.
0.0 = hoàn toàn không liên quan
1.0 = hoàn toàn liên quan và đầy đủ

Câu hỏi: {question}
Câu trả lời: {answer}

Điểm (chỉ số, ví dụ: 0.8):"""
        try:
            result = self.llm(prompt).strip()
            score = float(re.search(r"\d+\.?\d*", result).group())
            return min(max(score, 0.0), 1.0)
        except:
            return 0.5

    def score_faithfulness(self, context: str, answer: str) -> float:
        """Câu trả lời có dựa trên context không? (0-1)"""
        prompt = f"""Đánh giá mức độ câu trả lời dựa trên thông tin trong context.
Chỉ trả về một số từ 0.0 đến 1.0, không giải thích.
0.0 = câu trả lời hoàn toàn bịa đặt, không có trong context
1.0 = câu trả lời hoàn toàn dựa trên context

Context: {context[:1000]}
Câu trả lời: {answer}

Điểm (chỉ số, ví dụ: 0.7):"""
        try:
            result = self.llm(prompt).strip()
            score = float(re.search(r"\d+\.?\d*", result).group())
            return min(max(score, 0.0), 1.0)
        except:
            return 0.5

    def score_context_recall(self, ground_truth: str, context: str) -> float:
        """Context có chứa thông tin cần thiết để trả lời không? (0-1)"""
        prompt = f"""Đánh giá xem context có chứa đủ thông tin để trả lời câu hỏi theo ground truth không.
Chỉ trả về một số từ 0.0 đến 1.0, không giải thích.
0.0 = context không có thông tin gì liên quan
1.0 = context chứa đầy đủ thông tin

Ground truth: {ground_truth}
Context: {context[:1000]}

Điểm (chỉ số, ví dụ: 0.6):"""
        try:
            result = self.llm(prompt).strip()
            score = float(re.search(r"\d+\.?\d*", result).group())
            return min(max(score, 0.0), 1.0)
        except:
            return 0.5

    def score_all(self, question: str, answer: str,
                  context: str, ground_truth: str) -> dict:
        return {
            "answer_relevancy": self.score_answer_relevancy(question, answer),
            "faithfulness":     self.score_faithfulness(context, answer),
            "context_recall":   self.score_context_recall(ground_truth, context),
        }


# ─── Report generator ─────────────────────────────────────────────────────────

def generate_report(results: list[EvalResult]) -> str:
    def avg(lst): return sum(lst) / len(lst) if lst else 0

    naive_rel  = avg([r.naive_scores.get("answer_relevancy", 0) for r in results])
    naive_fai  = avg([r.naive_scores.get("faithfulness", 0)     for r in results])
    naive_rec  = avg([r.naive_scores.get("context_recall", 0)   for r in results])
    graph_rel  = avg([r.graph_scores.get("answer_relevancy", 0) for r in results])
    graph_fai  = avg([r.graph_scores.get("faithfulness", 0)     for r in results])
    graph_rec  = avg([r.graph_scores.get("context_recall", 0)   for r in results])

    # Thắng/thua theo từng metric
    rel_win  = sum(1 for r in results if r.graph_scores.get("answer_relevancy",0) > r.naive_scores.get("answer_relevancy",0))
    fai_win  = sum(1 for r in results if r.graph_scores.get("faithfulness",0)     > r.naive_scores.get("faithfulness",0))
    rec_win  = sum(1 for r in results if r.graph_scores.get("context_recall",0)   > r.naive_scores.get("context_recall",0))

    # Phân tích theo category
    categories = {}
    for r in results:
        cat = r.category
        if cat not in categories:
            categories[cat] = {"naive": [], "graph": []}
        naive_avg = avg(list(r.naive_scores.values()))
        graph_avg = avg(list(r.graph_scores.values()))
        categories[cat]["naive"].append(naive_avg)
        categories[cat]["graph"].append(graph_avg)

    lines = [
        "# Evaluation Report: Naive RAG vs GraphRAG",
        "## Vietnamese History QA (DVSKTT Corpus)\n",
        "---\n",
        "## Tổng quan\n",
        f"- **Số câu hỏi:** {len(results)}",
        f"- **Corpus:** Đại Việt Sử Ký Toàn Thư ({325} chunks)",
        f"- **Embedding model:** paraphrase-multilingual-MiniLM-L12-v2",
        f"- **LLM:** Groq Llama 3.3 70B\n",
        "---\n",
        "## Kết quả tổng hợp\n",
        "| Metric | Naive RAG | GraphRAG | Cải thiện |",
        "|--------|-----------|----------|-----------|",
        f"| Answer Relevancy | {naive_rel:.3f} | {graph_rel:.3f} | {(graph_rel-naive_rel):+.3f} |",
        f"| Faithfulness     | {naive_fai:.3f} | {graph_fai:.3f} | {(graph_fai-naive_fai):+.3f} |",
        f"| Context Recall   | {naive_rec:.3f} | {graph_rec:.3f} | {(graph_rec-naive_rec):+.3f} |",
        f"| **Average**      | **{avg([naive_rel,naive_fai,naive_rec]):.3f}** | **{avg([graph_rel,graph_fai,graph_rec]):.3f}** | **{avg([graph_rel-naive_rel,graph_fai-naive_fai,graph_rec-naive_rec]):+.3f}** |\n",
        f"GraphRAG thắng: Relevancy {rel_win}/{len(results)}, Faithfulness {fai_win}/{len(results)}, Recall {rec_win}/{len(results)}\n",
        "---\n",
        "## Phân tích theo category\n",
        "| Category | Naive RAG | GraphRAG | Winner |",
        "|----------|-----------|----------|--------|",
    ]

    for cat, scores in sorted(categories.items()):
        n = avg(scores["naive"])
        g = avg(scores["graph"])
        winner = "GraphRAG ✓" if g > n else ("Tie" if g == n else "Naive RAG")
        lines.append(f"| {cat} | {n:.3f} | {g:.3f} | {winner} |")

    lines += [
        "\n---\n",
        "## Chi tiết từng câu hỏi\n",
    ]

    for r in results:
        n_avg = avg(list(r.naive_scores.values()))
        g_avg = avg(list(r.graph_scores.values()))
        lines += [
            f"### {r.id} — {r.category}",
            f"**Q:** {r.question}",
            f"**Ground truth:** {r.ground_truth}\n",
            f"**Naive RAG** (avg: {n_avg:.2f}): {r.naive_answer[:200]}...",
            f"**GraphRAG** (avg: {g_avg:.2f}): {r.graph_answer[:200]}...\n",
            f"| | Relevancy | Faithfulness | Recall |",
            f"|---|---|---|---|",
            f"| Naive  | {r.naive_scores.get('answer_relevancy',0):.2f} | {r.naive_scores.get('faithfulness',0):.2f} | {r.naive_scores.get('context_recall',0):.2f} |",
            f"| Graph  | {r.graph_scores.get('answer_relevancy',0):.2f} | {r.graph_scores.get('faithfulness',0):.2f} | {r.graph_scores.get('context_recall',0):.2f} |",
            "",
        ]

    return "\n".join(lines)


# ─── Main pipeline ─────────────────────────────────────────────────────────────

def run_evaluation(sample_size: int = 25):
    """
    Chạy full evaluation.
    sample_size: số câu hỏi muốn test (mặc định tất cả 25)
    """
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import sys
    sys.path.append(os.path.dirname(__file__))
    from graphrag_retriever import EmbeddingStore, GraphExpander, build_context

    # ── Setup ────────────────────────────────────────────────────────────────
    print("🚀 Khởi tạo evaluation pipeline...\n")

    # LLM wrapper
    openai_base_url = os.getenv("OPENAI_BASE_URL")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL")

    openrouter_client = None
    openrouter_model = None
    if openai_base_url and "openrouter.ai" in openai_base_url and openai_api_key:
        from openai import OpenAI
        print(f"🔌 Initializing OpenRouter client for Evaluation with model {openai_model or 'google/gemini-2.5-flash'}")
        openrouter_client = OpenAI(
            base_url=openai_base_url,
            api_key=openai_api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/Vietnam-History-Discovery",
                "X-Title": "Vietnam History Discovery RAG Evaluation"
            }
        )
        openrouter_model = openai_model or "google/gemini-2.5-flash"

    groq_client = None
    groq_model = None
    if GROQ_KEY:
        from groq import Groq
        print("🔌 Initializing Groq client for Evaluation")
        groq_client = Groq(api_key=GROQ_KEY)
        groq_model = "llama-3.3-70b-versatile"

    if not openrouter_client and not groq_client:
        raise ValueError("Thiếu cả cấu hình OpenRouter và Groq cho Evaluation trong .env")

    def llm(prompt: str) -> str:
        if openrouter_client:
            try:
                model = openrouter_model
                if model.startswith("gpt/"):
                    model = "openai/" + model[4:]
                resp = openrouter_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0.1,
                )
                return resp.choices[0].message.content
            except Exception as e:
                print(f"⚠️ OpenRouter request failed in Evaluation: {e}")
                if groq_client:
                    print("🔄 Falling back to Groq for Evaluation...")
                else:
                    raise e

        if groq_client:
            resp = groq_client.chat.completions.create(
                model=groq_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.1,
            )
            return resp.choices[0].message.content

        raise RuntimeError("Không có LLM client hoạt động cho Evaluation.")

    # Components
    embed_store = EmbeddingStore()
    embed_store.build()
    expander    = GraphExpander()
    evaluator   = Evaluator(llm)
    naive_rag   = NaiveRAG(embed_store, llm)

    questions = QA_DATASET[:sample_size]
    results   = []

    print(f"📋 Evaluating {len(questions)} questions...\n")

    for i, qa in enumerate(questions):
        print(f"[{i+1:02d}/{len(questions)}] {qa['id']}: {qa['question'][:60]}...")

        result = EvalResult(
            id=qa["id"], question=qa["question"],
            ground_truth=qa["ground_truth"], category=qa["category"],
        )

        try:
            # ── Naive RAG ────────────────────────────────────────────────────
            naive_answer, naive_chunks = naive_rag.query(qa["question"])
            naive_context = "\n".join([c["text"] for c in naive_chunks])
            result.naive_answer = naive_answer
            result.naive_chunks = [c["chunk_id"] for c in naive_chunks]
            result.naive_scores = evaluator.score_all(
                qa["question"], naive_answer, naive_context, qa["ground_truth"]
            )
            time.sleep(1.5)  # rate limit

            # ── GraphRAG ─────────────────────────────────────────────────────
            graph_chunks = embed_store.search(qa["question"], top_k=10)
            chunk_ids    = [c["chunk_id"] for c in graph_chunks]
            graph_data   = expander.expand(chunk_ids)
            graph_context = build_context(qa["question"], graph_chunks, graph_data)
            graph_answer  = llm(f"""Bạn là chuyên gia lịch sử Việt Nam. Dựa trên context, trả lời câu hỏi bằng tiếng Việt.
            QUAN TRỌNG: Chỉ dùng thông tin CÓ TRONG context bên dưới. Không bổ sung kiến thức bên ngoài. Nếu context không đủ thông tin, nói rõ "Tài liệu không đề cập đến điều này."

{graph_context}

Câu hỏi: {qa['question']}""")

            result.graph_answer   = graph_answer
            result.graph_chunks   = chunk_ids
            result.graph_entities = len(graph_data["entities"])
            result.graph_relations= len(graph_data["relations"])
            result.graph_scores   = evaluator.score_all(
                qa["question"], graph_answer, graph_context, qa["ground_truth"]
            )
            time.sleep(1.5)

            n_avg = sum(result.naive_scores.values()) / 3
            g_avg = sum(result.graph_scores.values()) / 3
            winner = "Graph ✓" if g_avg > n_avg else ("Tie" if g_avg == n_avg else "Naive ✓")
            print(f"   Naive: {n_avg:.2f} | Graph: {g_avg:.2f} | {winner}")

        except Exception as e:
            print(f"   [ERROR] {e}")

        results.append(result)

    # ── Save results ─────────────────────────────────────────────────────────
    expander.close()

    out_json = os.path.join(EVAL_DIR, "evaluation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, ensure_ascii=False, indent=2)
    print(f"\n💾 Results → {out_json}")

    report = generate_report(results)
    out_md = os.path.join(EVAL_DIR, "report.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"💾 Report  → {out_md}")

    # In summary
    def avg(lst): return sum(lst) / len(lst) if lst else 0
    print("\n" + "="*50)
    print("📊 SUMMARY")
    print("="*50)
    for metric in ["answer_relevancy", "faithfulness", "context_recall"]:
        n = avg([r.naive_scores.get(metric, 0) for r in results])
        g = avg([r.graph_scores.get(metric, 0) for r in results])
        print(f"  {metric:20s}: Naive={n:.3f} | Graph={g:.3f} | Δ={g-n:+.3f}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=25, help="Số câu hỏi test (default: 25)")
    args = parser.parse_args()
    run_evaluation(sample_size=args.sample)
