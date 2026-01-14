#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 2차
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/631",
        "title": "제넥셀세인에서 탈출, 슈넬생명과학 시대 개막",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-09-01",
        "summary": "김재섭 회장이 제넥셀세인을 한국기술산업에 220억원에 매각하고 슈넬생명과학으로 경영진을 옮긴 복잡한 거래 구조 분석.",
        "entities": [
            {"type": "company", "name": "제넥셀세인", "role": "매각회사"},
            {"type": "company", "name": "한국기술산업", "role": "인수회사"},
            {"type": "company", "name": "슈넬생명과학", "role": "신규 경영사"},
            {"type": "company", "name": "에이프로젠", "role": "자회사"},
            {"type": "company", "name": "팝인베스트먼트", "role": "자금조달처"},
            {"type": "person", "name": "김재섭", "role": "회장"},
            {"type": "person", "name": "박미령", "role": "배우자"},
        ],
        "relations": [
            {"source": "김재섭", "target": "제넥셀세인", "type": "divestment", "detail": "220억원 매각"},
            {"source": "한국기술산업", "target": "슈넬생명과학", "type": "debt", "detail": "170억원 사채 인수"},
            {"source": "슈넬생명과학", "target": "팝인베스트먼트", "type": "bond_issuance", "detail": "170억원 신주인수권부사채 발행"},
        ],
        "risks": [
            {"type": "governance", "description": "자회사를 통한 순환 자금 조달로 재무 투명성 훼손", "severity": "high"},
            {"type": "legal", "description": "고가 양도에 따른 98억원 증여세 부과", "severity": "high"},
            {"type": "operational", "description": "인수 직후 1년 내 상장폐지", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/629",
        "title": "제넥셀세인의 실패, 김재섭의 성공",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-08-18",
        "summary": "김재섭 회장이 126억원 투자 후 216억원에 매각하여 90억원 차익을 얻은 거래 구조 분석.",
        "entities": [
            {"type": "company", "name": "제넥셀세인", "role": "피투자회사"},
            {"type": "company", "name": "한국기술산업", "role": "인수회사"},
            {"type": "company", "name": "슈넬생명과학", "role": "관련회사"},
            {"type": "company", "name": "에이프로젠", "role": "계열사"},
            {"type": "company", "name": "청계제약", "role": "계열사"},
            {"type": "person", "name": "김재섭", "role": "회장"},
            {"type": "person", "name": "박미령", "role": "배우자"},
        ],
        "relations": [
            {"source": "김재섭", "target": "제넥셀세인", "type": "divestment", "detail": "216억원 매각, 90억원 차익"},
            {"source": "한국기술산업", "target": "제넥셀세인", "type": "acquisition", "detail": "274억원 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "피투자회사 자산 매각으로 인수자금 조달 (순환 자금구조)", "severity": "high"},
            {"type": "financial", "description": "제넥셀세인 인수 후 수백억원 규모 손실 발생", "severity": "critical"},
            {"type": "operational", "description": "상장폐지로 인한 기업 실패", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/628",
        "title": "과학자에서 M&A전문가로, 제넥셀세인 시절의 인수합병",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-08-11",
        "summary": "김재섭 회장의 적극적인 인수합병 활동 분석. 369억원 조달 중 연구개발 투자는 57억원에 불과.",
        "entities": [
            {"type": "company", "name": "제넥셀세인", "role": "인수주체"},
            {"type": "company", "name": "에이프로젠", "role": "피인수회사"},
            {"type": "company", "name": "한국슈넬제약", "role": "피인수회사"},
            {"type": "company", "name": "청계제약", "role": "피인수회사"},
            {"type": "company", "name": "오로라리조트홀딩스", "role": "투자목적회사"},
            {"type": "person", "name": "김재섭", "role": "회장"},
        ],
        "relations": [
            {"source": "제넥셀세인", "target": "한국슈넬제약", "type": "acquisition", "detail": "201억원 투자, 71.41% 지분"},
            {"source": "오로라리조트홀딩스", "target": "한국슈넬제약", "type": "investment", "detail": "50억원 전환사채"},
        ],
        "risks": [
            {"type": "financial", "description": "자금 조달액 대비 과도한 M&A 투자", "severity": "high"},
            {"type": "governance", "description": "소규모 자본금 회사의 급격한 지위 변화 (오로라리조트홀딩스)", "severity": "high"},
            {"type": "reputational", "description": "기업사냥꾼 이미지로 상장 실패", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/627",
        "title": "신기루로 끝난 제넥셀세인의 바이오사업",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-08-04",
        "summary": "448억원 조달했으나 실제 바이오의약 매출은 2억4600만원에 불과. 2010년 상장폐지.",
        "entities": [
            {"type": "company", "name": "제넥셀세인", "role": "주요 기업"},
            {"type": "company", "name": "제넥셀", "role": "전신"},
            {"type": "company", "name": "에이프로젠", "role": "계열사"},
            {"type": "company", "name": "한국기술산업", "role": "인수회사"},
            {"type": "person", "name": "김재섭", "role": "회장"},
        ],
        "relations": [
            {"source": "한국기술산업", "target": "제넥셀세인", "type": "acquisition", "detail": "인수 후 상장폐지"},
        ],
        "risks": [
            {"type": "financial", "description": "자산가치 대비 과도한 수익가치 평가", "severity": "critical"},
            {"type": "governance", "description": "차명주식 거래로 지배구조 투명성 부족", "severity": "high"},
            {"type": "operational", "description": "부적절한 절차의 대여금 85억원, 선급금 32억원", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/626",
        "title": "에이프로젠과 제넥셀, 20년 전의 기막힌 우연",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-07-28",
        "summary": "2004년 세인전자와 케이아이씨가 동일 구조 해외신주인수권부사채 발행. 의도된 연계성 제시.",
        "entities": [
            {"type": "company", "name": "에이프로젠", "role": "주요 기업"},
            {"type": "company", "name": "제넥셀", "role": "관련회사"},
            {"type": "company", "name": "세인전자", "role": "인수대상"},
            {"type": "company", "name": "케이아이씨", "role": "관련회사"},
            {"type": "person", "name": "김재섭", "role": "회장"},
        ],
        "relations": [
            {"source": "김재섭", "target": "세인전자", "type": "acquisition", "detail": "2005년 지분 인수"},
            {"source": "에이프로젠", "target": "케이아이씨", "type": "acquisition", "detail": "2017년 우회상장 시도"},
        ],
        "risks": [
            {"type": "governance", "description": "동일 구조 채권발행의 의도적 연계성 의심", "severity": "high"},
            {"type": "market", "description": "주가 급등 후 신주인수권 행사로 차익 취득", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/625",
        "title": "바이오벤처 제넥셀, M&A로 코스닥 입성한 이유는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-07-21",
        "summary": "2005년 제넥셀이 세인전자를 합병하며 코스닥 우회상장. 제넥셀 주당가치는 세인전자의 5배 이상.",
        "entities": [
            {"type": "company", "name": "제넥셀", "role": "합병주체"},
            {"type": "company", "name": "세인전자", "role": "합병대상"},
            {"type": "company", "name": "제넥셀세인", "role": "합병회사"},
            {"type": "person", "name": "김재섭", "role": "회장/대표이사"},
        ],
        "relations": [
            {"source": "제넥셀", "target": "세인전자", "type": "merger", "detail": "2005년 주식교환, 우회상장"},
            {"source": "김재섭", "target": "제넥셀세인", "type": "ownership", "detail": "최대주주 11.93%"},
        ],
        "risks": [
            {"type": "financial", "description": "실질 수익 거의 없는 제넥셀에 대한 과도한 가치평가", "severity": "high"},
            {"type": "governance", "description": "창업 교수에서 M&A 전문가로의 경영권 이동", "severity": "medium"},
            {"type": "operational", "description": "의료기기업에서 바이오업으로 급격한 사업 전환", "severity": "medium"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (2차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}, Entities={before_stats['entities']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:30]}...")
        else:
            print(f"[FAIL] {article['title'][:30]}... - {result.get('error', '')[:50]}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, Entities={after_stats['entities']}")
    print(f"성공: {success_count}건, 증가: +{after_stats['articles'] - before_stats['articles']}")


if __name__ == "__main__":
    asyncio.run(main())
