"""
노드 중복 문제 진단 스크립트

이엠앤아이 회사의 Neo4j 노드 중복 여부 및 원인 파악
"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def diagnose_duplicate_nodes(company_id: str, company_name: str):
    """노드 중복 진단"""

    with driver.session() as session:
        print("=" * 80)
        print(f"중복 노드 진단: {company_name}")
        print(f"Company ID: {company_id}")
        print("=" * 80)
        print()

        # 1. 같은 ID의 Company 노드가 여러 개 있는지 확인
        print("1. 동일 ID Company 노드 개수 확인:")
        result = session.run("""
            MATCH (c:Company {id: $company_id})
            RETURN count(c) as node_count, collect(elementId(c)) as element_ids
        """, company_id=company_id)

        record = result.single()
        if record:
            node_count = record['node_count']
            element_ids = record['element_ids']
            print(f"   - 발견된 Company 노드 수: {node_count}")
            print(f"   - Element IDs: {element_ids}")

            if node_count > 1:
                print(f"   ❌ 문제: 동일 ID의 Company 노드가 {node_count}개 존재합니다!")
            else:
                print(f"   ✅ 정상: Company 노드는 1개입니다.")
        print()

        # 2. 같은 이름의 Company 노드가 여러 개 있는지 확인
        print("2. 동일 이름 Company 노드 개수 확인:")
        result = session.run("""
            MATCH (c:Company {name: $company_name})
            RETURN count(c) as node_count,
                   collect(c.id) as ids,
                   collect(c.name) as names,
                   collect(elementId(c)) as element_ids
        """, company_name=company_name)

        record = result.single()
        if record:
            node_count = record['node_count']
            ids = record['ids']
            names = record['names']
            element_ids = record['element_ids']

            print(f"   - 발견된 '{company_name}' 노드 수: {node_count}")
            for i, (node_id, name, elem_id) in enumerate(zip(ids, names, element_ids), 1):
                print(f"   - 노드 {i}: ID={node_id}, Name={name}, ElementID={elem_id}")

            if node_count > 1:
                print(f"   ❌ 문제: '{company_name}' 노드가 {node_count}개 존재합니다!")
            else:
                print(f"   ✅ 정상: '{company_name}' 노드는 1개입니다.")
        print()

        # 3. Path 쿼리 실행 시 반환되는 Company 노드 확인
        print("3. Path 쿼리 실행 결과:")
        cypher = f"""
            MATCH path = (c:Company {{id: '{company_id}'}})-[r]-(n)
            RETURN path
            LIMIT 100
        """

        result = session.run(cypher)

        company_nodes_in_paths = set()
        total_paths = 0

        for record in result:
            total_paths += 1
            path = record['path']
            for node in path.nodes:
                if 'Company' in node.labels:
                    company_nodes_in_paths.add((node.element_id, node.get('name'), node.get('id')))

        print(f"   - 총 Path 수: {total_paths}")
        print(f"   - Path에 포함된 Company 노드 수: {len(company_nodes_in_paths)}")

        if len(company_nodes_in_paths) > 1:
            print(f"   ❌ 문제: Path 쿼리 결과에 Company 노드가 {len(company_nodes_in_paths)}개 포함됩니다!")
            for i, (elem_id, name, node_id) in enumerate(company_nodes_in_paths, 1):
                print(f"   - Company {i}: Name={name}, ID={node_id}, ElementID={elem_id}")
        else:
            print(f"   ✅ 정상: Path에 Company 노드는 1개만 포함됩니다.")
            for elem_id, name, node_id in company_nodes_in_paths:
                print(f"   - Company: Name={name}, ID={node_id}")
        print()

        # 4. HAS_AFFILIATE 관계 확인 (자기 자신과의 관계)
        print("4. HAS_AFFILIATE 관계 확인:")
        result = session.run("""
            MATCH (c:Company {id: $company_id})-[r:HAS_AFFILIATE]-(other:Company)
            RETURN other.id as other_id, other.name as other_name,
                   type(r) as rel_type,
                   startNode(r).id as start_id,
                   endNode(r).id as end_id
        """, company_id=company_id)

        affiliates = list(result)
        if affiliates:
            print(f"   - HAS_AFFILIATE 관계 수: {len(affiliates)}")
            for aff in affiliates:
                print(f"   - {aff['start_id']} -[{aff['rel_type']}]-> {aff['end_id']}")
                print(f"     타겟 회사: {aff['other_name']} (ID: {aff['other_id']})")

                if aff['other_id'] == company_id:
                    print(f"   ⚠️  자기 자신과의 관계 발견!")
        else:
            print(f"   - HAS_AFFILIATE 관계 없음")
        print()

        # 5. 최종 진단
        print("=" * 80)
        print("진단 요약:")
        print("=" * 80)

        if node_count == 1 and len(company_nodes_in_paths) > 1:
            print("❌ 문제 원인: Path 쿼리가 동일한 노드를 여러 경로에서 반환하고 있습니다.")
            print("   이는 정상적인 동작이지만, NeoVis가 이를 중복으로 렌더링할 수 있습니다.")
            print()
            print("해결 방법:")
            print("   1. NeoVis 설정에서 노드 중복 제거 활성화")
            print("   2. 또는 DISTINCT를 사용한 쿼리로 변경")
        elif node_count > 1:
            print(f"❌ 심각한 문제: Neo4j에 동일 ID의 노드가 {node_count}개 존재합니다!")
            print("   데이터베이스 정합성 문제입니다. 중복 노드를 제거해야 합니다.")
        else:
            print("✅ 데이터베이스는 정상입니다.")
            print("   문제는 프론트엔드 렌더링 로직에 있을 수 있습니다.")


if __name__ == "__main__":
    # 이엠앤아이 진단
    company_id = "988b775f-dcc5-473b-a557-be2d13763a02"
    company_name = "이엠앤아이"

    diagnose_duplicate_nodes(company_id, company_name)

    driver.close()
