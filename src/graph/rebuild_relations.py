import os
from neo4j import GraphDatabase

def rebuild_relations():
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd = os.environ.get("NEO4J_PASSWORD")

    if not uri or not pwd:
        print("❌ Error: NEO4J_URI or NEO4J_PASSWORD environment variables not set")
        return

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    
    with driver.session() as session:
        print("🔗 Rebuilding Person-Dynasty CO_OCCURS_WITH relations...")
        res_person = session.run("""
            MATCH (p:Person)-[:MENTIONED_IN]->(c:Chunk)-[:BELONGS_TO_DYNASTY]->(d:Dynasty)
            WITH p, d, count(c) as count
            MERGE (p)-[r:CO_OCCURS_WITH]-(d)
            SET r.count = count, r.source = 'auto_rebuild'
            RETURN count(r) as total
        """).single()
        print(f"✅ Created/updated {res_person['total']} Person-Dynasty relations")

        print("🔗 Rebuilding Event-Dynasty CO_OCCURS_WITH relations...")
        res_event = session.run("""
            MATCH (e:Event)-[:MENTIONED_IN]->(c:Chunk)-[:BELONGS_TO_DYNASTY]->(d:Dynasty)
            WITH e, d, count(c) as count
            MERGE (e)-[r:CO_OCCURS_WITH]-(d)
            SET r.count = count, r.source = 'auto_rebuild'
            RETURN count(r) as total
        """).single()
        print(f"✅ Created/updated {res_event['total']} Event-Dynasty relations")

        print("🔗 Rebuilding Place-Dynasty CO_OCCURS_WITH relations...")
        res_place = session.run("""
            MATCH (pl:Place)-[:MENTIONED_IN]->(c:Chunk)-[:BELONGS_TO_DYNASTY]->(d:Dynasty)
            WITH pl, d, count(c) as count
            MERGE (pl)-[r:CO_OCCURS_WITH]-(d)
            SET r.count = count, r.source = 'auto_rebuild'
            RETURN count(r) as total
        """).single()
        print(f"✅ Created/updated {res_place['total']} Place-Dynasty relations")

    driver.close()
    print("🎉 All relations rebuilt successfully!")

if __name__ == "__main__":
    rebuild_relations()
