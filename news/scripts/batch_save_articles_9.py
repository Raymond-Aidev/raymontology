#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 9차 (엔켐/광무/중앙첨단소재 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/532",
        "title": "광무가 투자했던 HLB테라퓨닉스 인수전",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-06-24",
        "summary": "광무의 지트리홀딩스 CB 투자. 지트리비앤티 인수 목적이었으나 추가 자금 조달 실패.",
        "entities": [
            {"type": "company", "name": "광무", "role": "투자자"},
            {"type": "company", "name": "지트리홀딩스", "role": "SPC"},
            {"type": "company", "name": "지트리비앤티", "role": "인수대상"},
            {"type": "person", "name": "최기보", "role": "광무 배후"},
            {"type": "person", "name": "김범준", "role": "지트리홀딩스 대표"},
        ],
        "relations": [
            {"source": "광무", "target": "지트리홀딩스", "type": "investment", "detail": "CB 투자"},
        ],
        "risks": [
            {"type": "financial", "description": "자금조달 실패로 인수 무산", "severity": "high"},
            {"type": "financial", "description": "담보권 실행으로 대출 디폴트 시사", "severity": "high"},
            {"type": "operational", "description": "바이오 열풍 기반 투자 실패", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/531",
        "title": "광무는 왜 엔켐 비상장주식을 일찍 팔았을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-06-21",
        "summary": "광무의 엔켐 비상장주식 조기 매각. 6개월 보유 후 유의미한 수익 없이 매각, 재무 압박 시사.",
        "entities": [
            {"type": "company", "name": "광무", "role": "매각자"},
            {"type": "company", "name": "엔켐", "role": "투자대상"},
            {"type": "company", "name": "바른네트웍스", "role": "자회사"},
            {"type": "company", "name": "아틀라스팔천", "role": "관련회사"},
            {"type": "person", "name": "최기보", "role": "관련인물"},
            {"type": "person", "name": "오정강", "role": "엔켐 대표"},
        ],
        "relations": [
            {"source": "광무", "target": "엔켐", "type": "divestment", "detail": "55억원 상당 비상장주 조기 매각"},
        ],
        "risks": [
            {"type": "governance", "description": "불투명한 특관거래, 가치 이전 가능성", "severity": "high"},
            {"type": "financial", "description": "재무 압박 중 의문스러운 자산 처분 타이밍", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/530",
        "title": "친절과는 거리가 먼 엔켐의 공시",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-06-17",
        "summary": "엔켐의 불투명한 공시 관행. 2021년 이후 6000억원 조달했으나 3.2조원 대출/투자 미공시.",
        "entities": [
            {"type": "company", "name": "엔켐", "role": "주요 기업"},
            {"type": "company", "name": "중앙첨단소재", "role": "관련회사"},
            {"type": "company", "name": "아틀란스팔천", "role": "관련회사"},
            {"type": "company", "name": "광무", "role": "관련회사"},
            {"type": "person", "name": "오정강", "role": "대표/최대주주"},
        ],
        "relations": [],
        "risks": [
            {"type": "regulatory", "description": "특관거래 공시 부적절", "severity": "high"},
            {"type": "regulatory", "description": "공시의무 초과 대출활동 미공시", "severity": "high"},
            {"type": "financial", "description": "평가손실 1000억원, 세전손실의 25%", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/529",
        "title": "오정강 대표가 풀어야 할, 빚 청산의 숙제",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-06-13",
        "summary": "오정강 대표의 레버리지 투자. 아틀라스팔천 통한 광무, 중앙첨단소재 인수에 2600억원 차입.",
        "entities": [
            {"type": "company", "name": "엔켐", "role": "담보제공"},
            {"type": "company", "name": "광무", "role": "피인수회사"},
            {"type": "company", "name": "아틀라스팔천", "role": "투자기구"},
            {"type": "company", "name": "메리츠증권", "role": "대출자"},
            {"type": "person", "name": "오정강", "role": "대표"},
            {"type": "person", "name": "최기보", "role": "관련인물"},
        ],
        "relations": [
            {"source": "오정강", "target": "광무", "type": "acquisition", "detail": "아틀라스팔천 통한 2600억원 인수"},
            {"source": "오정강", "target": "메리츠증권", "type": "collateral", "detail": "엔켐주 186만주 담보, 959억원 대출"},
        ],
        "risks": [
            {"type": "financial", "description": "마진 유지 위한 주가 의존", "severity": "critical"},
            {"type": "financial", "description": "재융자 취약성", "severity": "high"},
            {"type": "financial", "description": "다수 법인 간 연결된 부채 구조", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/528",
        "title": "엔켐 전환사채로 손해 본 회사, 상지카일룸",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-06-10",
        "summary": "상지카일룸의 엔켐 7회차 CB 32억원 취득. 85억원 지급 후 전환 시 약 14억원 손실.",
        "entities": [
            {"type": "company", "name": "엔켐", "role": "CB 발행"},
            {"type": "company", "name": "상지카일룸", "role": "CB 취득"},
            {"type": "company", "name": "중앙첨단소재", "role": "모회사"},
            {"type": "company", "name": "광무", "role": "관련회사"},
            {"type": "person", "name": "오정강", "role": "대표"},
            {"type": "person", "name": "최기보", "role": "관련인물"},
        ],
        "relations": [
            {"source": "상지카일룸", "target": "엔켐", "type": "bond_purchase", "detail": "7회차 CB 85억원 취득"},
        ],
        "risks": [
            {"type": "financial", "description": "CB 투자 상당한 미실현 손실", "severity": "high"},
            {"type": "governance", "description": "복잡한 특관거래와 재무구조", "severity": "high"},
            {"type": "governance", "description": "콜옵션 권리와 실수익자 불일치 가능", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/527",
        "title": "광무, 엔켐 주식 TRS로 초대박 예약",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-06-07",
        "summary": "광무의 메리츠증권 엔켐 TRS 계약으로 1분기 순이익 928억원 달성. 2차전지 소재 판매 중단에도 대박.",
        "entities": [
            {"type": "company", "name": "광무", "role": "주요 기업"},
            {"type": "company", "name": "엔켐", "role": "기초자산"},
            {"type": "company", "name": "중앙첨단소재", "role": "관련회사"},
            {"type": "company", "name": "메리츠증권", "role": "TRS 상대방"},
            {"type": "person", "name": "오정강", "role": "엔켐 대표"},
        ],
        "relations": [
            {"source": "광무", "target": "메리츠증권", "type": "derivative", "detail": "엔켐 TRS 계약"},
        ],
        "risks": [
            {"type": "financial", "description": "중앙첨단소재 자본투입에도 상당 손실 지속", "severity": "high"},
            {"type": "financial", "description": "TRS 계약 고평가 엔켐 유지에 의존", "severity": "high"},
            {"type": "financial", "description": "TRS 만기(2024.6.13) 시 주가 변동성 가능", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/526",
        "title": "광무와 중앙첨단소재 2차전지 소재사업의 공회전",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-06-03",
        "summary": "엔켐 대표 오정강의 광무 인수. 2022년 2차전지 소재 매출 5390억원→2023년 1320억원으로 급감.",
        "entities": [
            {"type": "company", "name": "엔켐", "role": "주요 기업"},
            {"type": "company", "name": "광무", "role": "피인수회사"},
            {"type": "company", "name": "중앙첨단소재", "role": "관련회사"},
            {"type": "company", "name": "이디엘", "role": "합작사"},
            {"type": "person", "name": "오정강", "role": "대표"},
            {"type": "person", "name": "최기보", "role": "관련인물"},
        ],
        "relations": [
            {"source": "오정강", "target": "광무", "type": "acquisition", "detail": "페이퍼컴퍼니 통한 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "매출 집중과 불연속성", "severity": "high"},
            {"type": "operational", "description": "통합 생산능력 부재, 외주 의존", "severity": "high"},
            {"type": "governance", "description": "투명성 부족한 특관거래 구조", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/525",
        "title": "이상연 광무 대표이사의 독특한 이력",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-05-31",
        "summary": "광무 대표 이상연의 6년 재임 분석. 5회 대주주 변경, 대부분 연도 손실로 관리종목 지정.",
        "entities": [
            {"type": "company", "name": "광무", "role": "주요 기업"},
            {"type": "company", "name": "엔켐", "role": "투자회사"},
            {"type": "company", "name": "아틀라스팔천", "role": "투자기구"},
            {"type": "company", "name": "중앙첨단소재", "role": "관련회사"},
            {"type": "person", "name": "이상연", "role": "광무 대표"},
            {"type": "person", "name": "오정강", "role": "엔켐 대표"},
        ],
        "relations": [
            {"source": "오정강", "target": "광무", "type": "investment", "detail": "개인 투자회사"},
        ],
        "risks": [
            {"type": "financial", "description": "반복적 영업손실과 누적 적자", "severity": "high"},
            {"type": "governance", "description": "실질 지배 불명확한 복잡한 지배구조", "severity": "high"},
            {"type": "financial", "description": "최소 자본 페이퍼컴퍼니의 대규모 거래", "severity": "medium"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (9차) ===\n")

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
