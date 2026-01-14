#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 12차 (삼표그룹/롯데/SK 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/438",
        "title": "에스피네이처는 왜 합병 직전 삼표산업 유증에 참여했나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-07-03",
        "summary": "에스피네이처가 합병 전 삼표산업 신주 195만주(600억원) 취득. 정대현의 합병 후 지분율 23.45%로 상승.",
        "entities": [
            {"type": "company", "name": "삼표산업", "role": "합병 주체"},
            {"type": "company", "name": "삼표", "role": "피합병 모회사"},
            {"type": "company", "name": "에스피네이처", "role": "정대현 개인회사"},
            {"type": "person", "name": "정대현", "role": "후계자"},
            {"type": "person", "name": "정도원", "role": "회장"},
        ],
        "relations": [
            {"source": "에스피네이처", "target": "삼표산업", "type": "investment", "detail": "600억원 신주 취득"},
            {"source": "삼표산업", "target": "삼표", "type": "merger", "detail": "역합병 (자회사가 모회사 흡수)"},
        ],
        "risks": [
            {"type": "governance", "description": "역합병으로 후계자 지배력 강화, 시너지 명분과 상충", "severity": "high"},
            {"type": "governance", "description": "합병 전 대규모 유증 미공개", "severity": "high"},
            {"type": "financial", "description": "에스피네이처 삼표산업 대여금 400억원, 순환 금융 우려", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/437",
        "title": "합병법인 삼표산업 자사주, 어차피 정대현 몫?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-29",
        "summary": "삼표그룹 역합병으로 정대현 사장 경영승계 추진. 자기주식 활용으로 지분 이전 없이 총수 지위 확보 가능.",
        "entities": [
            {"type": "company", "name": "삼표", "role": "지주회사"},
            {"type": "company", "name": "삼표산업", "role": "자회사"},
            {"type": "company", "name": "에스피네이처", "role": "정대현 개인회사"},
            {"type": "person", "name": "정도원", "role": "현 회장"},
            {"type": "person", "name": "정대현", "role": "후계자"},
        ],
        "relations": [
            {"source": "정대현", "target": "에스피네이처", "type": "ownership", "detail": "소유/지배"},
            {"source": "에스피네이처", "target": "삼표산업", "type": "ownership", "detail": "1.74% 지분"},
        ],
        "risks": [
            {"type": "governance", "description": "역합병 자기주식 활용으로 지분 이전 없이 경영권 확보", "severity": "high"},
            {"type": "financial", "description": "에스피네이처 789억원 상환우선주 조기상환 발동 가능", "severity": "high"},
            {"type": "governance", "description": "자기주식 48.9%로 명목/실질 지분율 괴리", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/436",
        "title": "몰라보게 커진 에스피네이처의 자금활동",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-26",
        "summary": "에스피네이처가 2020년 이후 1830억원 자금 조달. 정대현 사장 3년간 약 230억원 배당 수령 추정.",
        "entities": [
            {"type": "company", "name": "에스피네이처", "role": "자금조달 주체"},
            {"type": "company", "name": "삼표", "role": "지주회사"},
            {"type": "company", "name": "신한은행", "role": "유동화 신용보강"},
            {"type": "person", "name": "정대현", "role": "에스피네이처 71.95% 보유"},
        ],
        "relations": [
            {"source": "에스피네이처", "target": "삼표", "type": "investment", "detail": "600억원 유증 참여, 19.43% 지분"},
        ],
        "risks": [
            {"type": "financial", "description": "상환우선주 연 배당률 3.98%, 연간 상환압박 가능", "severity": "high"},
            {"type": "financial", "description": "EBITDA 감소 속 배당 확대, 수익성 악화와 배당 괴리", "severity": "high"},
            {"type": "governance", "description": "주요 주주가 자금조달로 배당 수령, 계열사 투자 집중", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/435",
        "title": "정대현의 에스피네이처, 삼표의 든든한 자금줄",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-22",
        "summary": "정대현 사장이 정도원 회장으로부터 대원 지분 양수, 삼표로지스틱스 흡수합병으로 승계 기틀 마련.",
        "entities": [
            {"type": "company", "name": "삼표그룹", "role": "지주회사"},
            {"type": "company", "name": "에스피네이처", "role": "정대현 소유"},
            {"type": "company", "name": "삼표산업", "role": "핵심 계열사"},
            {"type": "company", "name": "삼표시멘트", "role": "상장회사"},
            {"type": "person", "name": "정도원", "role": "회장"},
            {"type": "person", "name": "정대현", "role": "승계자"},
        ],
        "relations": [
            {"source": "정도원", "target": "정대현", "type": "stock_transfer", "detail": "대원 지분 양도"},
            {"source": "에스피네이처", "target": "삼표그룹", "type": "ownership", "detail": "19.43% 지분, 대여금 910억원, 보증 3050억원"},
        ],
        "risks": [
            {"type": "governance", "description": "일가 지분 회피성 이전으로 간접 지배구조 구축", "severity": "high"},
            {"type": "financial", "description": "모그룹 의존도 심화, 매입액 1712억원 > 매출액 1292억원", "severity": "high"},
            {"type": "governance", "description": "개인회사가 상장사 삼표시멘트 4.75% 보유로 경영 영향력", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/434",
        "title": "승계의 발판 에스피네이처, 성장의 역사",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-19",
        "summary": "삼표그룹 지주회사 체제 10년 만에 역합병으로 3세 승계 추진. 정대현 사장이 에스피네이처 통해 경영권 확보.",
        "entities": [
            {"type": "company", "name": "삼표그룹", "role": "지주회사"},
            {"type": "company", "name": "삼표산업", "role": "핵심 자회사"},
            {"type": "company", "name": "삼표로지스틱스", "role": "승계 수단"},
            {"type": "company", "name": "에스피네이처", "role": "정대현 통합법인"},
            {"type": "person", "name": "정도원", "role": "2세 회장"},
            {"type": "person", "name": "정대현", "role": "3세 사장"},
        ],
        "relations": [
            {"source": "삼표산업", "target": "삼표", "type": "merger", "detail": "역합병 예정"},
        ],
        "risks": [
            {"type": "governance", "description": "역합병으로 48.9% 자기주식 발생, 지배력 불균형 심화", "severity": "high"},
            {"type": "governance", "description": "삼표산업이 삼표로지스틱스 지분을 장부가 43억→18억에 매각, 25억 손실", "severity": "high"},
            {"type": "governance", "description": "비상장사 위주 폐쇄적 구조로 소수주주 보호 미약", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/397",
        "title": "롯데건설, 아직 갈 길이 멀다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-30",
        "summary": "롯데건설이 메리츠금융과 1.5조원 투자협약 체결했으나, 올해 만기 차입금 2.5조원에 비해 부족.",
        "entities": [
            {"type": "company", "name": "롯데건설", "role": "건설회사"},
            {"type": "company", "name": "메리츠금융그룹", "role": "투자기관"},
        ],
        "relations": [
            {"source": "메리츠금융그룹", "target": "롯데건설", "type": "investment", "detail": "1.5조원 유동화증권 매입"},
        ],
        "risks": [
            {"type": "financial", "description": "만기 차입금 2.5조원 중 메리츠 1.5조원 제외 후 4.2조원 유동화증권 잔액", "severity": "critical"},
            {"type": "operational", "description": "미착공사업장이 6.9조원 중 4.4조원(63%)으로 높은 비중", "severity": "critical"},
            {"type": "market", "description": "부동산경기 부진으로 공사비 유입 부진", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/396",
        "title": "롯데건설은 부동산PF 위기 어떻게 봉합했나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-26",
        "summary": "롯데건설이 부동산PF 유동성 위기 극복 위해 메리츠금융과 1.5조원 투자협약. 고금리 차입과 롯데지주 개입.",
        "entities": [
            {"type": "company", "name": "롯데건설", "role": "위기 주체"},
            {"type": "company", "name": "메리츠금융그룹", "role": "투자자"},
            {"type": "company", "name": "롯데지주", "role": "모회사"},
            {"type": "company", "name": "롯데케미칼", "role": "보증/대출 제공"},
        ],
        "relations": [
            {"source": "메리츠금융그룹", "target": "롯데건설", "type": "investment", "detail": "1.5조원 유동화증권 매입"},
            {"source": "롯데지주", "target": "롯데건설", "type": "support", "detail": "위기 해결 개입"},
        ],
        "risks": [
            {"type": "financial", "description": "만기 단기 차입금 7870억원 중 4300억원 만기 도래, 고금리 10-14% 부담", "severity": "critical"},
            {"type": "financial", "description": "부동산PF 우발채무 상당 규모 존재", "severity": "high"},
            {"type": "operational", "description": "연 13-14% 이자 상환 후 이익 가능성 불확실", "severity": "high"},
            {"type": "market", "description": "업계 전반 PF 차환 리스크, 시스템 리스크 가능성", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/395",
        "title": "SK온, 6조원 유동성 차입금 갚을 묘수 있나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-24",
        "summary": "SK온이 블루오벌SK 투자 64억달러(8조원) 필요. 1년 내 상환 차입금 6.17조원, 영업현금흐름 음수.",
        "entities": [
            {"type": "company", "name": "SK온", "role": "배터리 자회사"},
            {"type": "company", "name": "SK이노베이션", "role": "모회사"},
            {"type": "company", "name": "포드", "role": "협력사"},
            {"type": "company", "name": "블루오벌SK", "role": "합작법인"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "SK온", "type": "subsidiary", "detail": "배터리사업 물적분할"},
            {"source": "SK온", "target": "블루오벌SK", "type": "investment", "detail": "64억달러 투자 예정"},
        ],
        "risks": [
            {"type": "financial", "description": "영업현금흐름 음수(-1.45조원)에서 6조원대 유동성 차입금 만기", "severity": "critical"},
            {"type": "financial", "description": "5.27조원 단기차입금 중 상세 미공시", "severity": "high"},
            {"type": "operational", "description": "SK배터리 아메리카 3.1조원 지급보증 차입, 추가 차입 여력 부족", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/394",
        "title": "실망스런 SK온 프리IPO, 모회사에 후폭풍 불까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-19",
        "summary": "SK온 프리IPO 기대 이하 성과. SK이노베이션 2조원 추가 투입 필요, 신용등급 하향 위험.",
        "entities": [
            {"type": "company", "name": "SK온", "role": "배터리 자회사"},
            {"type": "company", "name": "SK이노베이션", "role": "모회사"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "SK온", "type": "investment", "detail": "2조원 유상증자 참여 (총 2.82조원 중 71%)"},
        ],
        "risks": [
            {"type": "financial", "description": "보유 현금 1.2조원으로 급감, 영업현금흐름 3분기까지 5000억원", "severity": "critical"},
            {"type": "financial", "description": "1년내 상환 차입금 1.2조원 이상, 순차입금 급증 위험", "severity": "critical"},
            {"type": "governance", "description": "프리IPO 실패로 신용등급 하향 기준 터치 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/393",
        "title": "매력 떨어진 롯데쇼핑 ABCP, 차환발행 잘 되고 있나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-16",
        "summary": "롯데그룹 인천종합터미널 부지 매입 자금 조달 위한 3중 유동화 구조. 2021년 이후 차환발행 실패.",
        "entities": [
            {"type": "company", "name": "롯데쇼핑", "role": "원 차주"},
            {"type": "company", "name": "롯데인천개발", "role": "차입 주체"},
            {"type": "company", "name": "KB증권", "role": "주관사"},
            {"type": "company", "name": "한국투자증권", "role": "유동성공여"},
            {"type": "company", "name": "아이코스제이차", "role": "어음 발행사"},
        ],
        "relations": [
            {"source": "롯데인천개발", "target": "아이코스제이차", "type": "securitization", "detail": "유동화증권 발행"},
        ],
        "risks": [
            {"type": "market", "description": "차환발행 실패: 2021년 206억, 2022년 92억 미매각, 주관사 전량 인수", "severity": "high"},
            {"type": "operational", "description": "3중 유동화 구조로 복잡성 증가, 금리 매력도 저하", "severity": "high"},
            {"type": "market", "description": "금리 인상과 레고랜드 사태로 자산유동화시장 위축", "severity": "high"},
            {"type": "financial", "description": "시장금리 대비 낮은 할인율 ABCP 차환발행 어려움", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/392",
        "title": "롯데쇼핑 8000억원짜리 빚의 정체",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-12",
        "summary": "롯데그룹 2012년 인천종합터미널 부지 9000억원 매입, 자산유동화로 7000억원 차입. 현재 8000억원으로 증가.",
        "entities": [
            {"type": "company", "name": "롯데쇼핑", "role": "차입금 보유사"},
            {"type": "company", "name": "롯데그룹", "role": "매입 주체"},
            {"type": "company", "name": "신세계", "role": "인천 상권 경쟁사"},
            {"type": "company", "name": "에이치앤디에이블", "role": "초기 차입금 SPC"},
        ],
        "relations": [
            {"source": "롯데그룹", "target": "롯데쇼핑", "type": "debt_transfer", "detail": "롯데인천개발 합병으로 8000억원 차입금 이전"},
        ],
        "risks": [
            {"type": "financial", "description": "5년 만기 차입금 8000억원 미상환, 새 만기(2월 23일) 상환 능력 의문", "severity": "critical"},
            {"type": "operational", "description": "롯데쇼핑 자금사정 어려움, 그룹 내 자금지원 불가", "severity": "high"},
            {"type": "governance", "description": "복잡한 SPC 다중화, 브릿지론 활용으로 부채 은폐 가능성", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (12차 - 삼표/롯데/SK) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}...")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
