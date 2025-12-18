"""
NeoVis 쿼리 검증 스크립트

프론트엔드에서 사용하는 쿼리가 제대로 작동하는지 확인
"""
from neo4j import GraphDatabase
import json

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def test_neovis_query(company_id: str):
    """NeoVis 쿼리 테스트"""

    with driver.session() as session:
        # 프론트엔드와 동일한 쿼리
        cypher = f"""
          MATCH (c:Company {{id: '{company_id}'}})
          OPTIONAL MATCH (c)<-[r1:WORKS_AT]-(o:Officer)
          OPTIONAL MATCH (c)<-[r2:BOARD_MEMBER_AT]-(b:Officer)
          OPTIONAL MATCH (c)-[r3:HAS_AFFILIATE]-(aff:Company)
          OPTIONAL MATCH (c)-[r4:ISSUED]->(cb:ConvertibleBond)
          OPTIONAL MATCH (c)<-[r5:INVESTED_IN]-(s:Subscriber)
          RETURN c, r1, o, r2, b, r3, aff, r4, cb, r5, s
        """

        print("=" * 80)
        print("실행 Cypher:")
        print("=" * 80)
        print(cypher)
        print()

        print("=" * 80)
        print("쿼리 결과:")
        print("=" * 80)

        result = session.run(cypher)

        nodes_found = {
            'Company': 0,
            'Officer': set(),
            'ConvertibleBond': set(),
            'Subscriber': set(),
            'Affiliate': set()
        }

        relationships_found = {
            'WORKS_AT': 0,
            'BOARD_MEMBER_AT': 0,
            'HAS_AFFILIATE': 0,
            'ISSUED': 0,
            'INVESTED_IN': 0
        }

        row_count = 0
        for record in result:
            row_count += 1

            # Company
            if record['c']:
                nodes_found['Company'] = 1

            # Officers (WORKS_AT)
            if record['r1'] and record['o']:
                relationships_found['WORKS_AT'] += 1
                nodes_found['Officer'].add(record['o']['id'])

            # Board members (BOARD_MEMBER_AT)
            if record['r2'] and record['b']:
                relationships_found['BOARD_MEMBER_AT'] += 1
                nodes_found['Officer'].add(record['b']['id'])

            # Affiliates
            if record['r3'] and record['aff']:
                relationships_found['HAS_AFFILIATE'] += 1
                nodes_found['Affiliate'].add(record['aff']['id'])

            # Bonds
            if record['r4'] and record['cb']:
                relationships_found['ISSUED'] += 1
                nodes_found['ConvertibleBond'].add(record['cb']['id'])

            # Subscribers
            if record['r5'] and record['s']:
                relationships_found['INVESTED_IN'] += 1
                nodes_found['Subscriber'].add(record['s']['id'])

        print(f"총 반환된 Row 수: {row_count}")
        print()

        print("노드 발견:")
        print(f"  - Company: {nodes_found['Company']}")
        print(f"  - Officer: {len(nodes_found['Officer'])}개 (unique)")
        print(f"  - ConvertibleBond: {len(nodes_found['ConvertibleBond'])}개")
        print(f"  - Subscriber: {len(nodes_found['Subscriber'])}개")
        print(f"  - Affiliate: {len(nodes_found['Affiliate'])}개")
        print()

        print("관계 발견:")
        for rel_type, count in relationships_found.items():
            if count > 0:
                print(f"  - {rel_type}: {count}개")

        print()
        print("=" * 80)
        print("검증 결과:")
        print("=" * 80)

        total_rels = sum(relationships_found.values())
        if total_rels > 0:
            print(f"✅ 성공: {total_rels}개의 관계가 발견되었습니다.")
            print("   NeoVis.js는 이 관계들을 시각화할 수 있어야 합니다.")
        else:
            print("❌ 실패: 관계가 발견되지 않았습니다.")
            print("   쿼리를 확인하거나 Neo4j 데이터를 검증해주세요.")

if __name__ == "__main__":
    test_company_id = "37631ea7-9a45-4d0d-9b8d-03e06418f4e8"
    test_neovis_query(test_company_id)
    driver.close()
