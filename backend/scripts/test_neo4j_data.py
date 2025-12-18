"""
Neo4j 데이터 구조 검증 스크립트

특정 회사의 노드와 관계 데이터를 확인합니다.
"""
from neo4j import GraphDatabase
import json

# Neo4j 연결
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def test_company_data(company_id: str):
    """회사 데이터 및 관계 검증"""

    with driver.session() as session:
        # 1. 회사 노드 확인
        print(f"=" * 80)
        print(f"1. 회사 노드 확인 (ID: {company_id})")
        print(f"=" * 80)

        result = session.run("""
            MATCH (c:Company {id: $company_id})
            RETURN c.id as id, c.name as name, c.corp_code as corp_code, labels(c) as labels
        """, company_id=company_id)

        company = result.single()
        if company:
            print(f"✅ 회사 노드 존재:")
            print(f"   - ID: {company['id']}")
            print(f"   - Name: {company['name']}")
            print(f"   - Corp Code: {company['corp_code']}")
            print(f"   - Labels: {company['labels']}")
        else:
            print(f"❌ 회사 노드 없음")
            return

        print()

        # 2. 회사와 연결된 모든 관계 확인
        print(f"=" * 80)
        print(f"2. 회사와 연결된 관계 확인")
        print(f"=" * 80)

        result = session.run("""
            MATCH (c:Company {id: $company_id})-[r]->(target)
            RETURN type(r) as rel_type, labels(target) as target_labels, count(*) as count
            ORDER BY count DESC
        """, company_id=company_id)

        outgoing = list(result)
        if outgoing:
            print("Outgoing 관계 (회사 → 다른 노드):")
            for row in outgoing:
                print(f"   - {row['rel_type']} → {row['target_labels']}: {row['count']}개")
        else:
            print("   ❌ Outgoing 관계 없음")

        print()

        result = session.run("""
            MATCH (source)-[r]->(c:Company {id: $company_id})
            RETURN type(r) as rel_type, labels(source) as source_labels, count(*) as count
            ORDER BY count DESC
        """, company_id=company_id)

        incoming = list(result)
        if incoming:
            print("Incoming 관계 (다른 노드 → 회사):")
            for row in incoming:
                print(f"   - {row['source_labels']} → {row['rel_type']}: {row['count']}개")
        else:
            print("   ❌ Incoming 관계 없음")

        print()

        # 3. 상세 샘플 데이터 확인
        print(f"=" * 80)
        print(f"3. 샘플 관계 데이터 (각 타입별 최대 3개)")
        print(f"=" * 80)

        # WORKS_AT 관계
        result = session.run("""
            MATCH (o:Officer)-[r:WORKS_AT]->(c:Company {id: $company_id})
            RETURN o.name as officer_name, o.id as officer_id, type(r) as rel_type
            LIMIT 3
        """, company_id=company_id)

        officers = list(result)
        if officers:
            print(f"\n📍 WORKS_AT 관계 (임원 → 회사): {len(officers)}개 샘플")
            for idx, row in enumerate(officers, 1):
                print(f"   {idx}. {row['officer_name']} (ID: {row['officer_id']})")
        else:
            print(f"\n❌ WORKS_AT 관계 없음")

        # HAS_AFFILIATE 관계
        result = session.run("""
            MATCH (c:Company {id: $company_id})-[r:HAS_AFFILIATE]-(aff:Company)
            RETURN aff.name as affiliate_name, aff.id as affiliate_id, type(r) as rel_type
            LIMIT 3
        """, company_id=company_id)

        affiliates = list(result)
        if affiliates:
            print(f"\n📍 HAS_AFFILIATE 관계 (계열사): {len(affiliates)}개 샘플")
            for idx, row in enumerate(affiliates, 1):
                print(f"   {idx}. {row['affiliate_name']} (ID: {row['affiliate_id']})")
        else:
            print(f"\n❌ HAS_AFFILIATE 관계 없음")

        # ISSUED 관계
        result = session.run("""
            MATCH (c:Company {id: $company_id})-[r:ISSUED]->(cb:ConvertibleBond)
            RETURN cb.bond_name as bond_name, cb.id as bond_id, type(r) as rel_type
            LIMIT 3
        """, company_id=company_id)

        bonds = list(result)
        if bonds:
            print(f"\n📍 ISSUED 관계 (전환사채): {len(bonds)}개 샘플")
            for idx, row in enumerate(bonds, 1):
                print(f"   {idx}. {row['bond_name']} (ID: {row['bond_id']})")
        else:
            print(f"\n❌ ISSUED 관계 없음")

        print()

        # 4. 전체 연결 그래프 테스트 (실제 프론트엔드 쿼리와 동일)
        print(f"=" * 80)
        print(f"4. 프론트엔드 쿼리 테스트")
        print(f"=" * 80)

        result = session.run("""
            MATCH (c:Company {id: $company_id})
            OPTIONAL MATCH (c)<-[:WORKS_AT]-(o:Officer)
            OPTIONAL MATCH (c)-[:HAS_AFFILIATE]-(aff:Company)
            OPTIONAL MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
            OPTIONAL MATCH (cb)<-[:SUBSCRIBED]-(s:Subscriber)
            RETURN c, collect(DISTINCT o) as officers,
                   collect(DISTINCT aff) as affiliates,
                   collect(DISTINCT cb) as bonds,
                   collect(DISTINCT s) as subscribers
        """, company_id=company_id)

        graph_result = result.single()
        if graph_result:
            print(f"✅ 쿼리 실행 성공:")
            print(f"   - Company: {graph_result['c']['name'] if graph_result['c'] else 'None'}")
            print(f"   - Officers: {len([x for x in graph_result['officers'] if x])}개")
            print(f"   - Affiliates: {len([x for x in graph_result['affiliates'] if x])}개")
            print(f"   - Bonds: {len([x for x in graph_result['bonds'] if x])}개")
            print(f"   - Subscribers: {len([x for x in graph_result['subscribers'] if x])}개")
        else:
            print(f"❌ 쿼리 결과 없음")

        print()
        print(f"=" * 80)
        print(f"진단 완료")
        print(f"=" * 80)


if __name__ == "__main__":
    # 엑시온그룹 테스트
    test_company_id = "37631ea7-9a45-4d0d-9b8d-03e06418f4e8"
    test_company_data(test_company_id)

    driver.close()
