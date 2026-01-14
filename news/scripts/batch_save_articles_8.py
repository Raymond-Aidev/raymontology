#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 8차 (위즈돔/디에이테크놀로지/라임 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/559",
        "title": "퀀타피아·중앙첨단소재·리튬포어스의 공통점",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-09-12",
        "summary": "주가조작, 분식회계 의혹의 3개 코스닥 회사 연결고리. 이성락, 변익성 중심의 투자기구 추적.",
        "entities": [
            {"type": "company", "name": "퀀타피아", "role": "주요 기업"},
            {"type": "company", "name": "중앙첨단소재", "role": "관련회사"},
            {"type": "company", "name": "리튬포어스", "role": "관련회사"},
            {"type": "company", "name": "샌드크래프트", "role": "관련회사"},
            {"type": "person", "name": "이성락", "role": "실소유자 추정"},
            {"type": "person", "name": "변익성", "role": "관련인물"},
            {"type": "person", "name": "김훈", "role": "샌드크래프트 창업자"},
        ],
        "relations": [
            {"source": "이성락", "target": "퀀타피아", "type": "beneficial_owner", "detail": "실소유자 추정"},
            {"source": "이성락", "target": "중앙첨단소재", "type": "investment", "detail": "라크나가조합 CB 투자"},
        ],
        "risks": [
            {"type": "legal", "description": "분식회계로 검찰 고발", "severity": "critical"},
            {"type": "market", "description": "연결된 투자기구/CB를 통한 주가조작 의혹", "severity": "critical"},
            {"type": "operational", "description": "나노 이미지 센서 기술 진위 불명", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/552",
        "title": "위즈돔과 오이코스, SK그룹과 무슨 관계?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-09-02",
        "summary": "스마트모빌리티 위즈돔, 환경복원 오이코스, SK그룹의 연결고리. 최기보의 지주회사 활용한 지배구조.",
        "entities": [
            {"type": "company", "name": "위즈돔", "role": "주요 기업"},
            {"type": "company", "name": "오이코스", "role": "관련회사"},
            {"type": "company", "name": "오아시스홀딩스", "role": "지주회사"},
            {"type": "company", "name": "SK하이닉스", "role": "고객사"},
            {"type": "company", "name": "디에이테크놀로지", "role": "관련회사"},
            {"type": "person", "name": "최기보", "role": "실질 운영자"},
            {"type": "person", "name": "한상우", "role": "위즈돔 대표"},
        ],
        "relations": [
            {"source": "오아시스홀딩스", "target": "위즈돔", "type": "ownership", "detail": "지분 보유"},
            {"source": "위즈돔", "target": "SK하이닉스", "type": "business", "detail": "2011년 이후 계약"},
        ],
        "risks": [
            {"type": "governance", "description": "지분구조와 자금조달 불투명", "severity": "high"},
            {"type": "governance", "description": "페이퍼컴퍼니와 불투명한 외국법인 활용", "severity": "high"},
            {"type": "regulatory", "description": "외부감사 면제 기업의 규제 공백", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/543",
        "title": "오아시스홀딩스가 디에이테크놀로지의 진짜 주인?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-08-01",
        "summary": "디에이테크놀로지, 에스모와 오아시스홀딩스 인수 후 수익→적자 전환. 회생절차 및 상장폐지 위기.",
        "entities": [
            {"type": "company", "name": "디에이테크놀로지", "role": "주요 기업"},
            {"type": "company", "name": "오아시스홀딩스", "role": "지배회사 의혹"},
            {"type": "company", "name": "에스모", "role": "인수회사"},
            {"type": "company", "name": "위즈돔", "role": "피인수회사"},
            {"type": "person", "name": "최기보", "role": "관련인물"},
            {"type": "person", "name": "이현철", "role": "관련인물"},
        ],
        "relations": [
            {"source": "오아시스홀딩스", "target": "디에이테크놀로지", "type": "suspected_control", "detail": "에스모보다 큰 영향력"},
        ],
        "risks": [
            {"type": "financial", "description": "연간 2120~3000억원 이상 누적 손실", "severity": "critical"},
            {"type": "financial", "description": "2020년까지 매출 1/3로 감소", "severity": "critical"},
            {"type": "legal", "description": "창업자 횡령, 배임 혐의", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/542",
        "title": "위즈돔은 라임사태 주범이 기획한 디에이테크 인수의 마지막 퍼즐",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-07-29",
        "summary": "디에이테크놀로지 인수와 라임 자산운용 사기 연결. 오아시스홀딩스의 위즈돔 지분 활용 추적.",
        "entities": [
            {"type": "company", "name": "디에이테크놀로지", "role": "피인수회사"},
            {"type": "company", "name": "위즈돔", "role": "자금경유"},
            {"type": "company", "name": "라임자산운용", "role": "자금출처"},
            {"type": "company", "name": "오아시스홀딩스", "role": "인수주체"},
            {"type": "company", "name": "에스모", "role": "인수주체"},
            {"type": "person", "name": "이인광", "role": "라임 주범"},
            {"type": "person", "name": "조원일", "role": "라임 주범"},
            {"type": "person", "name": "최기보", "role": "M&A 전문가"},
        ],
        "relations": [
            {"source": "오아시스홀딩스", "target": "위즈돔", "type": "acquisition", "detail": "38억원에 25.98% 인수"},
            {"source": "라임자산운용", "target": "디에이테크놀로지", "type": "fund_flow", "detail": "복잡한 M&A 구조 통한 자금 유입"},
        ],
        "risks": [
            {"type": "legal", "description": "허위 유상증자 구조로 자금 순환 위장", "severity": "critical"},
            {"type": "governance", "description": "투자기구 간 미공개 지배관계", "severity": "high"},
            {"type": "legal", "description": "라임자산운용 자금의 복잡한 M&A 구조 유입", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/541",
        "title": "디에이테크놀로지에 인수되었던 위즈돔에 무슨 일이?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-07-25",
        "summary": "위즈돔, 디에이테크놀로지 인수 후 재무 붕괴. 2017-2019년 920억원 손실. 2022-2023년 900억원에 전량 매각.",
        "entities": [
            {"type": "company", "name": "위즈돔", "role": "피인수회사"},
            {"type": "company", "name": "디에이테크놀로지", "role": "인수회사"},
            {"type": "company", "name": "오아시스홀딩스", "role": "관련회사"},
            {"type": "person", "name": "한상우", "role": "위즈돔 대표"},
            {"type": "person", "name": "최기보", "role": "관련인물"},
        ],
        "relations": [
            {"source": "디에이테크놀로지", "target": "위즈돔", "type": "acquisition", "detail": "26% 지분 3800억원 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "과도한 레버리지 (부채비율 1106%)", "severity": "critical"},
            {"type": "financial", "description": "매출 성장에도 누적 손실", "severity": "high"},
            {"type": "governance", "description": "불일치 가치평가의 미공개 숨은 주주", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/540",
        "title": "위즈돔은 어쩌다 라임사태에 연루되었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-07-22",
        "summary": "위즈돔이 라임 스캔들에 연루된 과정. 2017년 기가레인 인수, 2018년 디에이테크놀로지 28% 인수로 연루 네트워크 편입.",
        "entities": [
            {"type": "company", "name": "위즈돔", "role": "주요 기업"},
            {"type": "company", "name": "기가레인", "role": "피인수회사"},
            {"type": "company", "name": "디에이테크놀로지", "role": "인수회사"},
            {"type": "company", "name": "에스모", "role": "관련회사"},
            {"type": "company", "name": "상지건설", "role": "관련회사"},
            {"type": "person", "name": "이인광", "role": "라임 주범"},
            {"type": "person", "name": "최기보", "role": "관련인물"},
            {"type": "person", "name": "한상우", "role": "위즈돔 대표"},
        ],
        "relations": [
            {"source": "디에이테크놀로지", "target": "위즈돔", "type": "acquisition", "detail": "2018년 10월 28% 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "불투명한 지배구조와 특관거래", "severity": "high"},
            {"type": "governance", "description": "관련 법인 통한 자본 순환", "severity": "high"},
            {"type": "legal", "description": "라임펀드 연결로 규제 조사 취약", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/539",
        "title": "씨그널엔터-위즈돔-기가레인-상지건설의 관계는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-07-18",
        "summary": "의문스러운 M&A에 연루된 4개 회사의 연결고리. 김준범, 신동걸 중심의 주가조작과 페이퍼컴퍼니, 무자본 인수 추적.",
        "entities": [
            {"type": "company", "name": "씨그널엔터테인먼트그룹", "role": "관련회사"},
            {"type": "company", "name": "위즈돔", "role": "관련회사"},
            {"type": "company", "name": "기가레인", "role": "관련회사"},
            {"type": "company", "name": "상지건설", "role": "관련회사"},
            {"type": "person", "name": "김준범", "role": "주가조작 주도자"},
            {"type": "person", "name": "신동걸", "role": "M&A 전문가"},
            {"type": "person", "name": "한상우", "role": "위즈돔 대표"},
        ],
        "relations": [
            {"source": "위즈돔", "target": "기가레인", "type": "acquisition", "detail": "경영권 인수"},
            {"source": "기가레인", "target": "상지건설", "type": "divestment", "detail": "매각"},
        ],
        "risks": [
            {"type": "legal", "description": "주가조작, 허위공시", "severity": "critical"},
            {"type": "governance", "description": "페이퍼컴퍼니, 차입금 활용 무자본 인수", "severity": "high"},
            {"type": "legal", "description": "옵티머스 펀드 사기 연결", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/538",
        "title": "위즈돔은 왜 기가레인을 상지건설에 팔았나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-07-15",
        "summary": "한국 최대 버스공유 플랫폼 위즈돔의 복잡한 재무 거래. 오이코스, 기가레인 인수 후 상지건설 매각 추적.",
        "entities": [
            {"type": "company", "name": "위즈돔", "role": "주요 기업"},
            {"type": "company", "name": "기가레인", "role": "피인수회사"},
            {"type": "company", "name": "상지건설", "role": "인수회사"},
            {"type": "company", "name": "오이코스", "role": "피인수회사"},
            {"type": "person", "name": "한상우", "role": "위즈돔 대표"},
            {"type": "person", "name": "최기보", "role": "관련인물"},
            {"type": "person", "name": "신동걸", "role": "전 상지건설 대주주"},
        ],
        "relations": [
            {"source": "위즈돔", "target": "기가레인", "type": "acquisition", "detail": "인수"},
            {"source": "위즈돔", "target": "상지건설", "type": "divestment", "detail": "기가레인 매각"},
        ],
        "risks": [
            {"type": "governance", "description": "예정된 결과 시사하는 조정된 투자/매각 패턴", "severity": "high"},
            {"type": "financial", "description": "최소 가치창출의 관련 법인 간 자본 순환", "severity": "high"},
            {"type": "financial", "description": "회사간 거래 통한 주주가치 파괴 가능성", "severity": "medium"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (8차) ===\n")

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
