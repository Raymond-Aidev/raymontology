#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 3차 (SK온/바이오엑스/글람 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/609",
        "title": "글람의 나스닥 상장, 성공사례일까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-03-31",
        "summary": "글람의 2023년 나스닥 상장이 문제적. 2024년 매출 191억원에 불과하고 주가는 90% 이상 폭락.",
        "entities": [
            {"type": "company", "name": "글람", "role": "주요 기업"},
            {"type": "company", "name": "바이오엑스", "role": "최대주주"},
            {"type": "person", "name": "김형기", "role": "회장"},
            {"type": "person", "name": "이호준", "role": "전 부회장"},
        ],
        "relations": [
            {"source": "바이오엑스", "target": "글람", "type": "ownership", "detail": "최대주주"},
        ],
        "risks": [
            {"type": "financial", "description": "주가 90% 이상 폭락, 나스닥 규정 위반", "severity": "critical"},
            {"type": "financial", "description": "IPO 시점 과대 가치평가", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/608",
        "title": "SK온의 흑자전환이 중요한 이유",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-03-24",
        "summary": "SK온은 2026년 IPO 약속 이행을 위해 2024년 흑자전환 필수. 2.8조원 우선주 발행 투자자들과의 계약 조건 분석.",
        "entities": [
            {"type": "company", "name": "SK온", "role": "주요 기업"},
            {"type": "company", "name": "SK이노베이션", "role": "모회사"},
            {"type": "company", "name": "블루오벌SK", "role": "합작법인"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "SK온", "type": "ownership", "detail": "모회사"},
        ],
        "risks": [
            {"type": "financial", "description": "흑자전환 실패 시 투자자 드래그얼롱권 발동", "severity": "critical"},
            {"type": "operational", "description": "트럼프 행정부 EV 보조금 축소 영향", "severity": "high"},
            {"type": "financial", "description": "2026년 IPO 지연 시 1.5조원 주식매수청구 가능", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/607",
        "title": "SK온의 이상한 기업가치",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-03-17",
        "summary": "SK온 기업가치가 28조원~32.2조원으로 변동. 모회사 SK이노베이션 시총 11.4조원과 불일치.",
        "entities": [
            {"type": "company", "name": "SK온", "role": "주요 기업"},
            {"type": "company", "name": "SK이노베이션", "role": "모회사"},
            {"type": "company", "name": "미래에셋증권", "role": "주관사"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "SK온과 SK이노베이션 가치평가 불일치", "severity": "high"},
            {"type": "financial", "description": "20조원 부채 부담", "severity": "critical"},
            {"type": "governance", "description": "가치평가 방법론 불투명", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/606",
        "title": "SK이노베이션에서 SK까지, SK온에서 시작된 나비효과",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-03-06",
        "summary": "SK온 투자 부담으로 SK이노베이션이 SK이엔에스 흡수 결정. SK그룹 전체 구조조정의 연쇄효과.",
        "entities": [
            {"type": "company", "name": "SK온", "role": "원인 제공"},
            {"type": "company", "name": "SK이노베이션", "role": "주요 기업"},
            {"type": "company", "name": "SK이엔에스", "role": "피흡수"},
            {"type": "company", "name": "SK", "role": "지주회사"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "SK이엔에스", "type": "merger", "detail": "2024년 7월 흡수합병"},
            {"source": "SK", "target": "SK이노베이션", "type": "capital_support", "detail": "SK이엔에스 출자"},
        ],
        "risks": [
            {"type": "financial", "description": "SK온 부채 20조원, 그룹 차입금 2/3 차지", "severity": "critical"},
            {"type": "operational", "description": "배터리 가동률 50% 이하로 하락", "severity": "high"},
            {"type": "financial", "description": "2026년 IPO 의무, 풋옵션/드래그얼롱권 존재", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/605",
        "title": "블루오벌SK의 유상감자, 모회사 SK온의 계좌에 꽂혔다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-03-03",
        "summary": "블루오벌SK가 62.8억달러 유상감자 실행. 절반이 모회사 SK온 미국법인으로 유입.",
        "entities": [
            {"type": "company", "name": "블루오벌SK", "role": "주요 기업"},
            {"type": "company", "name": "SK온", "role": "모회사"},
            {"type": "company", "name": "SK배터리아메리카", "role": "자회사"},
            {"type": "company", "name": "포드", "role": "합작파트너"},
        ],
        "relations": [
            {"source": "블루오벌SK", "target": "SK온", "type": "capital_return", "detail": "62.8억달러 유상감자"},
        ],
        "risks": [
            {"type": "financial", "description": "20조원 부채 중 10조원 9개월 내 만기", "severity": "critical"},
            {"type": "financial", "description": "단기채 시장 자금 조달 의존", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/604",
        "title": "BlueOval SK, 미 에너지부 대출금으로 유상감자?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-02-27",
        "summary": "블루오벌SK가 미 에너지부 96억달러 대출 후 62.8억달러 유상감자. 정부 지원금 용도 의문.",
        "entities": [
            {"type": "company", "name": "블루오벌SK", "role": "주요 기업"},
            {"type": "company", "name": "SK온", "role": "모회사"},
            {"type": "company", "name": "포드", "role": "합작파트너"},
        ],
        "relations": [
            {"source": "블루오벌SK", "target": "SK온", "type": "capital_return", "detail": "정부 대출 후 유상감자"},
        ],
        "risks": [
            {"type": "legal", "description": "정부 지원금 설비투자 용도 외 사용 의혹", "severity": "high"},
            {"type": "operational", "description": "테네시 공장 2026년 지연, 켄터키 Q2로 조정", "severity": "medium"},
            {"type": "financial", "description": "포드 EV 부문 51억달러 손실", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/603",
        "title": "공장의 절반을 놀렸던 SK온, 특단의 대책은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-02-24",
        "summary": "SK온 2024년 배터리 매출 6.3조원으로 반감, 영업손실 1조원 초과. 가동률 46.2%로 하락.",
        "entities": [
            {"type": "company", "name": "SK온", "role": "주요 기업"},
            {"type": "company", "name": "SK이노베이션", "role": "모회사"},
            {"type": "company", "name": "CATL", "role": "경쟁사"},
            {"type": "company", "name": "파나소닉", "role": "경쟁사"},
            {"type": "company", "name": "블루오벌SK", "role": "합작법인"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "부채 20조원 대비 매출 감소", "severity": "critical"},
            {"type": "financial", "description": "IPO 수익성 목표 달성 불가능", "severity": "critical"},
            {"type": "operational", "description": "공장 가동률 46.2%로 저조", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/601",
        "title": "바이오엑스와 글람의 진짜 주인은 누구였나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-02-17",
        "summary": "글람(캡티비전코리아) 복잡한 지배구조 추적. 바이오엑스, 김형기, 이호준, 구본호 연결고리.",
        "entities": [
            {"type": "company", "name": "글람", "role": "주요 기업"},
            {"type": "company", "name": "바이오엑스", "role": "최대주주"},
            {"type": "company", "name": "지스마트", "role": "전신"},
            {"type": "company", "name": "케이케이홀딩스", "role": "관련회사"},
            {"type": "person", "name": "김형기", "role": "바이오엑스 대표"},
            {"type": "person", "name": "이호준", "role": "지스마트 창업자"},
            {"type": "person", "name": "구본호", "role": "자금출처 의혹"},
        ],
        "relations": [
            {"source": "바이오엑스", "target": "글람", "type": "ownership", "detail": "전환사채 전환으로 최대주주"},
            {"source": "구본호", "target": "바이오엑스", "type": "suspected_backing", "detail": "자금 지원 의혹"},
        ],
        "risks": [
            {"type": "governance", "description": "숨겨진 지배구조와 페이퍼컴퍼니 의혹", "severity": "critical"},
            {"type": "financial", "description": "고금리(10-15%) 부채 부담", "severity": "high"},
            {"type": "legal", "description": "자산 압류 및 강제매각 발생", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (3차: SK온/글람 시리즈) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}... - {result.get('error', '')[:40]}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
