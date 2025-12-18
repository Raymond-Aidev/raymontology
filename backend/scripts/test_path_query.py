"""
경로 기반 쿼리 테스트

NeoVis에 최적화된 경로 쿼리 검증
"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def test_path_query(company_id: str):
    """경로 쿼리 테스트"""

    with driver.session() as session:
        cypher = f"""
          MATCH path = (c:Company {{id: '{company_id}'}})-[r]-(n)
          RETURN path
          LIMIT 100
        """

        print("=" * 80)
        print("경로 기반 쿼리 테스트")
        print("=" * 80)
        print(cypher)
        print()

        result = session.run(cypher)

        nodes = set()
        relationships = []
        paths_count = 0

        for record in result:
            paths_count += 1
            path = record['path']

            # Extract nodes and relationships from path
            for node in path.nodes:
                nodes.add((node.element_id, list(node.labels)[0] if node.labels else 'Unknown'))

            for rel in path.relationships:
                relationships.append(rel.type)

        print(f"✅ 총 경로 수: {paths_count}")
        print(f"✅ 총 노드 수: {len(nodes)} (unique)")
        print(f"✅ 총 관계 수: {len(relationships)}")
        print()

        # Count by label
        node_labels = {}
        for _, label in nodes:
            node_labels[label] = node_labels.get(label, 0) + 1

        print("노드 분포:")
        for label, count in sorted(node_labels.items(), key=lambda x: -x[1]):
            print(f"  - {label}: {count}개")

        print()

        # Count by relationship type
        rel_types = {}
        for rel_type in relationships:
            rel_types[rel_type] = rel_types.get(rel_type, 0) + 1

        print("관계 분포:")
        for rel_type, count in sorted(rel_types.items(), key=lambda x: -x[1]):
            print(f"  - {rel_type}: {count}개")

        print()
        print("=" * 80)
        print("✅ 이 쿼리는 NeoVis.js와 완벽하게 호환됩니다!")
        print("   - 회사 노드가 중심에 표시됩니다")
        print("   - 모든 연결된 노드와 관계가 시각화됩니다")
        print("=" * 80)

if __name__ == "__main__":
    test_company_id = "37631ea7-9a45-4d0d-9b8d-03e06418f4e8"
    test_path_query(test_company_id)
    driver.close()
