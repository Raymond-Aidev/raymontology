#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 10차 (엔켐/광무/웰바이오텍 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/524",
        "title": "웰바이오텍→아센디오→씨씨에스 고리의 진짜 배후는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-05-27",
        "summary": "웰바이오텍, 아센디오, 씨씨에스 3개 회사 복잡한 지배구조 추적. 양남희가 실질적 배후 의혹.",
        "entities": [
            {"type": "company", "name": "웰바이오텍", "role": "관련회사"},
            {"type": "company", "name": "아센디오", "role": "관련회사"},
            {"type": "company", "name": "씨씨에스", "role": "관련회사"},
            {"type": "company", "name": "에스유홀딩스", "role": "관련회사"},
            {"type": "person", "name": "양남희", "role": "실질 배후 추정"},
            {"type": "person", "name": "김한국", "role": "웰바이오텍 대표"},
            {"type": "person", "name": "한승일", "role": "아센디오 대표"},
        ],
        "relations": [
            {"source": "양남희", "target": "웰바이오텍", "type": "suspected_control", "detail": "실질 지배 의혹"},
        ],
        "risks": [
            {"type": "governance", "description": "시장가 2배 이상 프리미엄에 7.01% 지분 인수", "severity": "high"},
            {"type": "governance", "description": "순환 지배구조로 실소유자 불명확", "severity": "high"},
            {"type": "financial", "description": "웰바이오텍 6년 연속 적자, 누적손실 1000억원 초과", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/523",
        "title": "엔에스엔, 지더블유바이텍, 세원이앤씨, 이엔플러스의 접점",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-05-25",
        "summary": "4개 회사의 복잡한 연결고리. 지주회사, 투자펀드, 페이퍼컴퍼니를 통한 레버리지 인수 추적.",
        "entities": [
            {"type": "company", "name": "엔에스엔", "role": "관련회사"},
            {"type": "company", "name": "지더블유바이텍", "role": "관련회사"},
            {"type": "company", "name": "세원이앤씨", "role": "관련회사"},
            {"type": "company", "name": "이엔플러스", "role": "관련회사"},
            {"type": "person", "name": "황원희", "role": "관련인물"},
            {"type": "person", "name": "한승일", "role": "관련인물"},
        ],
        "relations": [],
        "risks": [
            {"type": "regulatory", "description": "경영권 계약 공시 지연/부적절", "severity": "high"},
            {"type": "financial", "description": "적극적 인수에도 지분투자 연속 손실", "severity": "high"},
            {"type": "governance", "description": "고레버리지 무자본 M&A 구조", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/522",
        "title": "웰바이오텍과 아센디오의 그들, 어디에서 왔나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-05-20",
        "summary": "웰바이오텍, 아센디오 핵심 인물의 출신 추적. 황원희의 자전거 제조업체 인수로 시작된 복잡한 네트워크.",
        "entities": [
            {"type": "company", "name": "웰바이오텍", "role": "주요 기업"},
            {"type": "company", "name": "아센디오", "role": "관련회사"},
            {"type": "company", "name": "에이모션", "role": "전신"},
            {"type": "person", "name": "황원희", "role": "핵심인물"},
            {"type": "person", "name": "양남희", "role": "관련인물"},
            {"type": "person", "name": "한승일", "role": "관련인물"},
        ],
        "relations": [
            {"source": "황원희", "target": "웰바이오텍", "type": "network", "detail": "네트워크 형성"},
        ],
        "risks": [
            {"type": "market", "description": "조정된 거래를 통한 주가조작 가능성", "severity": "high"},
            {"type": "governance", "description": "특관거래의 자기거래", "severity": "high"},
            {"type": "financial", "description": "비정상 가격의 자산 이전", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/520",
        "title": "이상했던 광무의 엠아이팜이천 인수합병",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-05-13",
        "summary": "광무의 엠아이팜제천 인수 의혹. 오정강 개인회사를 1000억원에 재인수, 자금 순환 의혹.",
        "entities": [
            {"type": "company", "name": "광무", "role": "인수주체"},
            {"type": "company", "name": "엠아이팜제천", "role": "피인수회사"},
            {"type": "company", "name": "엔켐", "role": "관련회사"},
            {"type": "company", "name": "아틀라스팔천", "role": "투자기구"},
            {"type": "person", "name": "오정강", "role": "대표"},
            {"type": "person", "name": "최기보", "role": "투자그룹 리더"},
        ],
        "relations": [
            {"source": "광무", "target": "엠아이팜제천", "type": "acquisition", "detail": "1000억원, 98.04% 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "경제적 실질 없는 특관거래", "severity": "critical"},
            {"type": "financial", "description": "순환 자금흐름으로 실제 투자 목적 위장", "severity": "critical"},
            {"type": "financial", "description": "상품매출/제품매출 회계 분류 오류 가능", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/519",
        "title": "광무는 어떻게 오정강 대표 회사가 됐나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-05-10",
        "summary": "광무(릭스솔루션)의 오정강 인수 과정. 아틀라스팔천이 2021년 유상증자로 최대주주 등극.",
        "entities": [
            {"type": "company", "name": "광무", "role": "피인수회사"},
            {"type": "company", "name": "아틀라스팔천", "role": "인수주체"},
            {"type": "company", "name": "중앙첨단소재", "role": "관련회사"},
            {"type": "company", "name": "상지카일룸", "role": "관련회사"},
            {"type": "person", "name": "오정강", "role": "인수자"},
            {"type": "person", "name": "최기보", "role": "핵심 기획자"},
        ],
        "relations": [
            {"source": "아틀라스팔천", "target": "광무", "type": "acquisition", "detail": "2021년 유상증자 통한 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "다수 투자조합 통한 불투명 지배구조", "severity": "high"},
            {"type": "governance", "description": "지분이전, 출자전환의 의문스러운 조작", "severity": "high"},
            {"type": "governance", "description": "중복 경영직의 이해충돌 가능", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/518",
        "title": "오정강 대표가 인수한 광무와 중앙첨단소재의 과거",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-05-07",
        "summary": "광무(바른테크놀로지), 중앙첨단소재(중앙바이오)의 복잡한 지배구조 변경 이력 추적.",
        "entities": [
            {"type": "company", "name": "엔켐", "role": "관련회사"},
            {"type": "company", "name": "광무", "role": "피인수회사"},
            {"type": "company", "name": "중앙첨단소재", "role": "피인수회사"},
            {"type": "company", "name": "아틀라스팔천", "role": "투자기구"},
            {"type": "company", "name": "상지카일룸", "role": "관련회사"},
            {"type": "person", "name": "오정강", "role": "인수자"},
            {"type": "person", "name": "최기보", "role": "관련인물"},
        ],
        "relations": [
            {"source": "오정강", "target": "광무", "type": "acquisition", "detail": "아틀라스팔천 통한 2021년 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "실체 은폐 시사하는 복잡한 지배구조", "severity": "high"},
            {"type": "governance", "description": "문제있는 역사 시사하는 잦은 상호변경", "severity": "medium"},
            {"type": "governance", "description": "기관 대신 관련 개인 통한 부채 조달", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/517",
        "title": "오정강 대표의 특급 도우미, 광무와 메리츠증권",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-04-29",
        "summary": "엔켐 오정강 대표의 2021년 상장 후 복잡한 재무구조. 와이어트그룹, 아틀라스팔천의 콜옵션과 메리츠 TRS.",
        "entities": [
            {"type": "company", "name": "엔켐", "role": "주요 기업"},
            {"type": "company", "name": "메리츠증권", "role": "중개자"},
            {"type": "company", "name": "와이어트그룹", "role": "개인회사"},
            {"type": "company", "name": "아틀라스팔천", "role": "개인회사"},
            {"type": "company", "name": "광무", "role": "관련회사"},
            {"type": "person", "name": "오정강", "role": "대표"},
        ],
        "relations": [
            {"source": "오정강", "target": "메리츠증권", "type": "derivative", "detail": "TRS 계약"},
        ],
        "risks": [
            {"type": "governance", "description": "대규모 투자계획의 공개주주 정보 비대칭", "severity": "high"},
            {"type": "governance", "description": "실소유 불명확한 특관거래 구조", "severity": "high"},
            {"type": "financial", "description": "CB로 인한 상당한 희석과 주가 하락 압력", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/516",
        "title": "대규모 자금조달과 최대주주 지분율의 함수 관계?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-04-27",
        "summary": "엔켐의 자금조달 전략과 대주주 지분 희석. 2012년 3700만원→2022년 5000억원 성장. 천보와의 대주주 분쟁.",
        "entities": [
            {"type": "company", "name": "엔켐", "role": "주요 기업"},
            {"type": "company", "name": "천보", "role": "대주주"},
            {"type": "person", "name": "오정강", "role": "엔켐 대표"},
            {"type": "person", "name": "이상률", "role": "천보 창업자"},
        ],
        "relations": [
            {"source": "천보", "target": "엔켐", "type": "ownership", "detail": "대주주 분쟁 후 합의"},
        ],
        "risks": [
            {"type": "governance", "description": "CB 통한 소수주주 지분 희석", "severity": "high"},
            {"type": "governance", "description": "경영권 분쟁", "severity": "medium"},
            {"type": "governance", "description": "사모 유상증자 우대 조건 지배구조 우려", "severity": "medium"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (10차) ===\n")

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
