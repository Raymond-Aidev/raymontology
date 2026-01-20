#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 41차 (한진중공업 시리즈 1-최종, 셀트리온 의심 최종)
마지막 배치 - DRCR 기사 전체 적재 완료
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/9",
        "title": "한진중공업그룹의 숨가쁜 자금거래와 그 이면(최종)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2018-10-09",
        "summary": "한진중공업 자회사 대륜E&S가 750억원 규모 상환전환우선주 발행해 유동화사채로 전환, 모회사와 TRS 파생상품 계약 체결. 대륜발전/별내에너지 손실 영향 제거하고 상장 준비하는 구조.",
        "entities": [
            {"type": "company", "name": "한진중공업홀딩스", "role": "모회사, 유상증자 출자자"},
            {"type": "company", "name": "대륜E&S", "role": "상환전환우선주 발행사, IPO 추진"},
            {"type": "company", "name": "대륜발전", "role": "손실 발생 종속회사"},
            {"type": "company", "name": "별내에너지", "role": "손실 발생 종속회사"},
            {"type": "company", "name": "디알파이프제일차", "role": "유동화사채 발행 SPC"},
        ],
        "relations": [
            {"source": "한진중공업홀딩스", "target": "대륜E&S", "type": "ownership", "detail": "보통주 100% 소유, 상환우선주 전환시 66%로 하락"},
            {"source": "한진중공업홀딩스", "target": "대륜E&S", "type": "derivative", "detail": "TRS 파생상품 계약으로 손익 귀속 변경"},
        ],
        "risks": [
            {"type": "financial", "description": "유동화사채 만기 2020년 1월까지 상환우선주 회수 필요, 미흡시 750억원 부담", "severity": "high"},
            {"type": "operational", "description": "대륜발전/별내에너지 2018년 상반기 100억원 순손실, 연결재무제표 적자 위험", "severity": "high"},
            {"type": "governance", "description": "TRS 계약으로 손실 은폐 구조, 상장 심사 투명성 문제", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/8",
        "title": "한진중공업그룹의 숨가쁜 자금거래와 그 이면(7)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2018-10-08",
        "summary": "한진중공업 자기자본 지속적 적자로 급속 감소, 현재 추세면 2년 내 자본잠식 위험. 부동산 자산 가치에도 실현 시기 불명확해 단기 채무 상환에 도움 안 됨. 대륜E&S IPO로 긴급 자금 조달 필요.",
        "entities": [
            {"type": "company", "name": "한진중공업", "role": "주요 대상 기업"},
            {"type": "company", "name": "수빅조선소", "role": "누적손실 발생 자회사"},
            {"type": "company", "name": "대륜E&S", "role": "IPO 계획 자회사"},
            {"type": "company", "name": "산업은행", "role": "주요 채권자"},
        ],
        "relations": [
            {"source": "한진중공업", "target": "수빅조선소", "type": "parent_subsidiary", "detail": "1조 9천억원 이상 출자, 1조원 지급보증"},
            {"source": "한진중공업", "target": "산업은행", "type": "debtor_creditor", "detail": "1.8조원 차입부채, 연말 만기"},
        ],
        "risks": [
            {"type": "financial", "description": "자기자본 현재 추세대로 감소 시 2년 내 자본잠식 예상", "severity": "critical"},
            {"type": "financial", "description": "1.8조원 차입금 연말 만기인데 상환 능력 부족", "severity": "critical"},
            {"type": "operational", "description": "조선부문 신규 수주 부진, 영도조선소 상반기 신규계약액 0원", "severity": "high"},
            {"type": "market", "description": "상장폐지 기준 위반 임박 가능성", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/7",
        "title": "한진중공업그룹의 숨가쁜 자금거래와 그 이면(6)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2018-10-03",
        "summary": "한진중공업홀딩스의 대륜E&S IPO 추진이 2014년 상장심사 통과 후 무산된 사건 분석. 대륜발전 이자비용 자본화 종료로 당기비용 급증해 연결재무제표 세전순이익 적자 전환.",
        "entities": [
            {"type": "company", "name": "한진중공업홀딩스", "role": "대륜E&S 100% 대주주"},
            {"type": "company", "name": "대륜E&S", "role": "상장 추진 기업"},
            {"type": "company", "name": "산업은행", "role": "경영권 확보, 자율협약 관리자"},
            {"type": "company", "name": "대륜발전", "role": "집단에너지 자회사"},
            {"type": "company", "name": "별내에너지", "role": "집단에너지 자회사"},
        ],
        "relations": [
            {"source": "한진중공업홀딩스", "target": "대륜E&S", "type": "ownership", "detail": "100% 지분 보유"},
            {"source": "산업은행", "target": "한진중공업", "type": "control", "detail": "자율협약 통한 경영 감독"},
        ],
        "risks": [
            {"type": "financial", "description": "한진중공업 현재 시점에서 차입원리금 상환 영업현금흐름 창출능력 없음", "severity": "critical"},
            {"type": "strategic", "description": "대륜E&S 상장 추진 실패로 자금조달 경로 상실", "severity": "high"},
            {"type": "financial", "description": "대륜발전 이자비용 자본화 종료로 연결재무제표 세전순이익 적자 전환", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/6",
        "title": "한진중공업그룹의 숨가쁜 자금거래와 그 이면(5)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2018-10-01",
        "summary": "한진중공업이 대륜E&S로 자산 이전하면서 대륜발전/별내에너지 재무구조 대폭 개선. 현금 증자와 채권 출자전환으로 대륜발전 부채비율 530%→200%대 하락, 별내에너지 자본잠식 해소.",
        "entities": [
            {"type": "company", "name": "한진중공업", "role": "자산 이전사"},
            {"type": "company", "name": "대륜E&S", "role": "자산 양수사"},
            {"type": "company", "name": "대륜발전", "role": "자본확충 대상"},
            {"type": "company", "name": "별내에너지", "role": "유상증자 대상"},
            {"type": "company", "name": "한진중공업홀딩스", "role": "최상위 지배회사"},
            {"type": "company", "name": "산업은행", "role": "채권자, 구조조정 감시자"},
        ],
        "relations": [
            {"source": "한진중공업", "target": "대륜E&S", "type": "asset_transfer", "detail": "보유 주식/채권 장부가액으로 이전"},
            {"source": "대륜E&S", "target": "대륜발전", "type": "debt_conversion", "detail": "895억원 채권을 주식 전환"},
            {"source": "대륜E&S", "target": "별내에너지", "type": "capital_increase", "detail": "770억원 현금 투자로 자본잠식 해소"},
        ],
        "risks": [
            {"type": "financial", "description": "대손상각 통해 678억원 채권 417억원으로 감액 후 매각, 약 226억원 손실 가능", "severity": "high"},
            {"type": "governance", "description": "출자전환 대상 채권 구성 미공개로 거래 투명성 문제", "severity": "medium"},
            {"type": "regulatory", "description": "특수관계자 간 거래로 세무당국 손비인정 거부/이익금 과세 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/5",
        "title": "한진중공업그룹의 숨가쁜 자금거래와 그 이면(4)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2018-09-27",
        "summary": "한진중공업 복잡한 재무구조조정 분석. 조선/에너지 부문 분리. 대륜E&S가 대륜발전/별내에너지 유상증자로 약 1.12조원 투입, 향후 3,500억원 현금 기여 예정.",
        "entities": [
            {"type": "company", "name": "한진중공업", "role": "자율협약 구조조정 중인 모회사"},
            {"type": "company", "name": "한진중공업홀딩스", "role": "최상위 지주회사"},
            {"type": "company", "name": "대륜E&S", "role": "에너지 부문 운영사"},
            {"type": "company", "name": "대륜발전", "role": "자본확충 필요 집단에너지 자회사"},
            {"type": "company", "name": "별내에너지", "role": "770억원 자본 투입 받은 집단에너지 자회사"},
            {"type": "company", "name": "한국남부발전", "role": "대륜발전 소수지분 보유 전력구매사"},
        ],
        "relations": [
            {"source": "한진중공업홀딩스", "target": "대륜E&S", "type": "capital_injection", "detail": "하코 매각 980억원을 대규모 증자로 투입"},
            {"source": "대륜E&S", "target": "대륜발전", "type": "acquisition", "detail": "재무투자자 지분/채권 인수 후 한진중공업 보유분 인수"},
            {"source": "대륜E&S", "target": "별내에너지", "type": "capital_increase", "detail": "9월 20일 770억원 유상증자 단독 참여"},
        ],
        "risks": [
            {"type": "financial", "description": "대륜발전/별내에너지 자립 불가, 부채비율 70%대에 이자비용 커버 못하는 영업이익", "severity": "high"},
            {"type": "governance", "description": "그룹사 간 복잡한 거래/채무보증으로 연말 자율협약 기한 내 세심한 조율 필요", "severity": "high"},
            {"type": "strategic", "description": "대륜E&S IPO가 자회사 수익성 개선에 의존, 실행 위험 존재", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/4",
        "title": "한진중공업그룹의 숨가쁜 자금거래와 그 이면(3)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2018-09-21",
        "summary": "한진중공업그룹 내 자산매각/유상증자로 유입된 1.77조원 자금 사용처 분석. 약 1.2조원이 대륜발전 채무 정리에 사용, 약 5,000억원만 그룹에 남아 불명확한 채권/채무 조정 의문.",
        "entities": [
            {"type": "company", "name": "한진중공업홀딩스", "role": "자본투입/자산거래 수행 모회사"},
            {"type": "company", "name": "대륜E&S", "role": "자본투입 받고 주식/채권 인수하는 자회사"},
            {"type": "company", "name": "대륜발전", "role": "채무 정리 대상 에너지회사"},
            {"type": "company", "name": "별내에너지", "role": "관계자 지분 보유 에너지 자회사"},
            {"type": "company", "name": "인베스트파워", "role": "후순위대출→보통주 전환 투자기구"},
            {"type": "company", "name": "한국남부발전", "role": "대륜발전 주주, 채무상환 책임"},
        ],
        "relations": [
            {"source": "한진중공업홀딩스", "target": "대륜E&S", "type": "capital_injection", "detail": "1,020억원 자본 증자"},
            {"source": "대륜E&S", "target": "한진중공업", "type": "asset_acquisition", "detail": "주식/채권 1,107억원 매입"},
            {"source": "인베스트파워", "target": "대륜발전", "type": "debt_conversion", "detail": "1,100억원 후순위대출→848억원 보통주 전환 (연 7.4% 이자)"},
        ],
        "risks": [
            {"type": "financial", "description": "1.77조원 투입 중 약 4,000억원 불명확한 현금 유출, 채무 탕감 가능성", "severity": "high"},
            {"type": "governance", "description": "관계자 간 복잡한 순환거래로 주식 전환/채무 구조조정 통해 실제 채무 은폐", "severity": "high"},
            {"type": "financial", "description": "반기재무제표에서 2,900억원 채권 공격적 상각, 투명한 설명 없음", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/3",
        "title": "한진중공업그룹의 숨가쁜 자금거래와 그 이면(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2018-09-19",
        "summary": "한진중공업이 설립한 대륜발전/별내에너지가 막대한 시설투자로 8,000억원대 차입금 보유, 한진중공업 재정악화 초래. 인베스트파워 계열사에서 주식/채권 인수 후 대륜E&S로 이관하며 채권/채무 관계 정리.",
        "entities": [
            {"type": "company", "name": "한진중공업", "role": "모회사/주요 출자자"},
            {"type": "company", "name": "한진중공업홀딩스", "role": "지배구조 상위 회사"},
            {"type": "company", "name": "대륜발전", "role": "집단에너지 자회사"},
            {"type": "company", "name": "별내에너지", "role": "집단에너지 자회사"},
            {"type": "company", "name": "대륜E&S", "role": "에너지 부문 운영사"},
            {"type": "company", "name": "산업은행", "role": "주채권은행/경영권 위임자"},
            {"type": "company", "name": "인베스트파워제육차", "role": "채권/주식 보유사"},
        ],
        "relations": [
            {"source": "한진중공업", "target": "대륜발전", "type": "investment_guarantee", "detail": "2009년 설립 시 20.2억원 출자, 차입금 빚보증"},
            {"source": "한진중공업", "target": "별내에너지", "type": "investment_guarantee", "detail": "2010년 인수 시 63억원 출자, 차입금 보증"},
            {"source": "산업은행", "target": "한진중공업", "type": "management_control", "detail": "2014년 재무구조개선약정, 2016년부터 경영권 위임"},
        ],
        "risks": [
            {"type": "financial", "description": "대륜발전/별내에너지 2015년 차입금 8,000억원대, 누적 이자 미상환으로 원금 증가", "severity": "critical"},
            {"type": "governance", "description": "한진중공업홀딩스가 실질적 지배권 없이 한진중공업을 연결대상 포함, 외부주주 권익 침해", "severity": "high"},
            {"type": "financial", "description": "한진중공업 2010~2014년 연속 적자, 영업현금흐름 악화로 현금 1조원→4,000억원대 감소", "severity": "critical"},
            {"type": "regulatory", "description": "인베스트파워 보통주 풋옵션 구조로 실질적 채권성 금융상품을 주식으로 유통", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/2",
        "title": "한진중공업그룹의 숨가쁜 자금거래와 그 이면(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2018-09-11",
        "summary": "한진중공업그룹이 2018년 말 채권단 공동관리 기한 만료 앞두고 대규모 자금거래 추진. 하코 매각(980억원)으로 확보한 자금을 대륜E&S 유상증자(1,770억원)에 투입, IPO 추진이 핵심 전략.",
        "entities": [
            {"type": "company", "name": "한진중공업홀딩스", "role": "최상위 지배회사"},
            {"type": "company", "name": "한진중공업", "role": "조선/건설 부문 중심 계열사"},
            {"type": "company", "name": "대륜E&S", "role": "에너지 부문 자회사"},
            {"type": "company", "name": "대륜발전", "role": "집단에너지 운영 손자회사"},
            {"type": "company", "name": "별내에너지", "role": "집단에너지 운영 손자회사"},
            {"type": "person", "name": "조남호", "role": "회장, 하코 대표이사"},
            {"type": "company", "name": "아워홈", "role": "하코 인수사"},
            {"type": "company", "name": "DB금융투자", "role": "SPC 설립사"},
        ],
        "relations": [
            {"source": "한진중공업홀딩스", "target": "하코", "type": "divestiture", "detail": "100% 자회사, 980억원에 아워홈 매각"},
            {"source": "한진중공업홀딩스", "target": "대륜E&S", "type": "capital_increase", "detail": "100% 자회사, 보통주 1,020억원 유상증자 인수"},
            {"source": "재무투자자", "target": "대륜E&S", "type": "investment", "detail": "상환전환우선주 750억원 인수, 5년 기한, 연복리 5%"},
        ],
        "risks": [
            {"type": "financial", "description": "한진중공업 현금 유동성 부족. 보유현금 1,440억원 대비 만기 차입금 2조원 초과", "severity": "critical"},
            {"type": "governance", "description": "채권단 공동관리로 경영 의사결정권 제한, 재무결정에 채권단 영향력 강함", "severity": "high"},
            {"type": "strategic", "description": "대륜E&S IPO 성공이 재무 구조 개선 핵심, 2021년 1월까지 상장 필요, 풋옵션 행사 위험", "severity": "high"},
            {"type": "financial", "description": "대륜E&S 별도재무제표만 작성해 손자회사 적자 미반영, IPO 시 연결재무제표 작성으로 수익성 악화 노출", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/1",
        "title": "셀트리온, 다시 의심의 대상이 되다(최종)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-05-24",
        "summary": "셀트리온과 자회사 셀트리온헬스케어 관계 구조 재검토. 헬스케어가 셀트리온 제품 구매해 유럽 판매망 통해 판매하는 구조에서 발생하는 재무적 왜곡. 헝가리법인이 5년 만에 다시 주역으로 등장, 2013년 의심 패턴 반복.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "바이오시밀러 의약품 생산사"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "유럽 판매/유통사"},
            {"type": "company", "name": "헝가리법인", "role": "유럽 총판/판매 채널"},
            {"type": "person", "name": "서정진", "role": "셀트리온 회장"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "parent_subsidiary", "detail": "셀트리온 제품 생산, 헬스케어 유럽 판매"},
            {"source": "셀트리온헬스케어", "target": "헝가리법인", "type": "parent_subsidiary", "detail": "헬스케어가 헝가리법인에 제품 공급, 재고/외상 판매"},
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "supply_purchase", "detail": "2011년 이후 4조원 매출 거의 전부를 헬스케어에 판매"},
        ],
        "risks": [
            {"type": "financial", "description": "헬스케어 매출채권이 분기 매출액에 육박, 회수 기간 지속 증가", "severity": "high"},
            {"type": "financial", "description": "헬스케어 2018년 원가율 92% 급등, 바이오시밀러 부분은 더 높을 것으로 예상", "severity": "high"},
            {"type": "governance", "description": "승인 전 상용화 불가능한 람시마SC 500억원을 미리 헬스케어에 공급", "severity": "critical"},
            {"type": "regulatory", "description": "금융감독원 2018년 헬스케어 감리 착수, 매출 실재성/평가방법 문제 지적", "severity": "critical"},
            {"type": "operational", "description": "헝가리법인 재고 3,000억원 누적, 셀트리온의 분기별 제품 배분 전략적 조절", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (41차 - 최종) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:40]}...")
        else:
            print(f"[FAIL] {article['title'][:40]}... - {result.get('error', 'Unknown')}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")
    print("\n*** DRCR 전체 기사 적재 완료! ***")


if __name__ == "__main__":
    asyncio.run(main())
