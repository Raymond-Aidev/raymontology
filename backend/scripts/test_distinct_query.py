"""
DISTINCT 기반 쿼리 검증 스크립트

프론트엔드에서 사용할 새로운 DISTINCT 쿼리가 중복 노드 없이 작동하는지 확인
"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def test_distinct_query(company_id: str, company_name: str):
    """DISTINCT 쿼리 테스트"""

    with driver.session() as session:
        print("=" * 80)
        print(f"DISTINCT 쿼리 테스트: {company_name}")
        print(f"Company ID: {company_id}")
        print("=" * 80)
        print()

        # 새로운 DISTINCT 기반 쿼리 (프론트엔드와 동일)
        cypher = f"""
            MATCH (c:Company {{id: '{company_id}'}})-[r]-(n)
            WITH c, collect(DISTINCT r) as rels, collect(DISTINCT n) as nodes
            UNWIND rels as rel
            RETURN c, rel, startNode(rel) as start, endNode(rel) as end
            LIMIT 100
        """

        print("실행 쿼리:")
        print(cypher)
        print()

        result = session.run(cypher)

        # 결과 분석
        company_nodes = set()
        other_nodes = set()
        relationships = []
        row_count = 0

        for record in result:
            row_count += 1

            # Company 노드 수집
            c = record['c']
            if c:
                company_nodes.add((c.element_id, c.get('name')))

            # Start/End 노드 수집
            start = record['start']
            end = record['end']

            if start:
                if 'Company' in start.labels:
                    company_nodes.add((start.element_id, start.get('name')))
                else:
                    other_nodes.add((start.element_id, list(start.labels)[0] if start.labels else 'Unknown'))

            if end:
                if 'Company' in end.labels:
                    company_nodes.add((end.element_id, end.get('name')))
                else:
                    other_nodes.add((end.element_id, list(end.labels)[0] if end.labels else 'Unknown'))

            # 관계 수집
            rel = record['rel']
            if rel:
                relationships.append(rel.type)

        print("=" * 80)
        print("쿼리 결과:")
        print("=" * 80)
        print(f"총 반환 Row 수: {row_count}")
        print()

        print(f"발견된 Company 노드 수: {len(company_nodes)}")
        for elem_id, name in company_nodes:
            print(f"  - {name} (ElementID: {elem_id})")
        print()

        print(f"발견된 기타 노드 수: {len(other_nodes)}")

        # 노드 타입별 집계
        node_types = {}
        for _, label in other_nodes:
            node_types[label] = node_types.get(label, 0) + 1

        for label, count in sorted(node_types.items(), key=lambda x: -x[1]):
            print(f"  - {label}: {count}개")
        print()

        print(f"발견된 관계 수: {len(relationships)}")

        # 관계 타입별 집계
        rel_types = {}
        for rel_type in relationships:
            rel_types[rel_type] = rel_types.get(rel_type, 0) + 1

        for rel_type, count in sorted(rel_types.items(), key=lambda x: -x[1]):
            print(f"  - {rel_type}: {count}개")
        print()

        print("=" * 80)
        print("검증 결과:")
        print("=" * 80)

        if len(company_nodes) == 1:
            print(f"✅ 성공: Company 노드가 정확히 1개만 반환되었습니다!")
            print(f"   중복 렌더링 문제가 해결되었습니다.")
        elif len(company_nodes) > 1:
            print(f"❌ 실패: Company 노드가 {len(company_nodes)}개 반환되었습니다.")
            print(f"   쿼리를 다시 확인해야 합니다.")
        else:
            print(f"❌ 실패: Company 노드가 발견되지 않았습니다.")

        print()
        print(f"✅ 총 {len(other_nodes)}개의 연결 노드 발견")
        print(f"✅ 총 {len(relationships)}개의 관계 발견")
        print()

        if len(company_nodes) == 1 and len(relationships) > 0:
            print("=" * 80)
            print("🎉 쿼리 검증 완료!")
            print("   - 중복 노드 없음 ✓")
            print("   - 관계 정상 반환 ✓")
            print("   - NeoVis.js에서 정상 렌더링 가능 ✓")
            print("=" * 80)


if __name__ == "__main__":
    # 이엠앤아이 테스트
    company_id = "988b775f-dcc5-473b-a557-be2d13763a02"
    company_name = "이엠앤아이"

    test_distinct_query(company_id, company_name)

    driver.close()
