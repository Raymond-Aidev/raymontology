#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 14차 (경남제약/필룩스/비덴트 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/219",
        "title": "왜 장산을 블루베리NFT의 최대주주로 세웠을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-04-29",
        "summary": "경남제약 매각 이후 계열사 경영진 교체. 블루베리NFT가 100억원 유증으로 최대주주 변경.",
        "entities": [
            {"type": "company", "name": "장산", "role": "신규 최대주주"},
            {"type": "company", "name": "블루베리NFT", "role": "유증 실시"},
            {"type": "company", "name": "클라우드에어", "role": "전 최대주주"},
            {"type": "company", "name": "경남제약", "role": "계열사"},
            {"type": "person", "name": "김병진", "role": "장산 100% 소유 회장"},
            {"type": "person", "name": "안성민", "role": "전 지분 보유자"},
        ],
        "relations": [
            {"source": "장산", "target": "블루베리NFT", "type": "acquisition", "detail": "신규 최대주주"},
            {"source": "김병진", "target": "장산", "type": "ownership", "detail": "100% 소유"},
        ],
        "risks": [
            {"type": "governance", "description": "최대주주 변경, 클라우드에어 거치지 않고 장산 직접 개입으로 투명성 저하", "severity": "high"},
            {"type": "financial", "description": "블루베리NFT 269억원 순손실, 현금 277→94억원 급감", "severity": "high"},
            {"type": "operational", "description": "영업적자 전환, 재고자산 증가로 운전자본 악화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/218",
        "title": "부산주공에서 무슨 일이 벌어지고 있는 걸까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-04-22",
        "summary": "부산주공, 현대차 국내 생산 감소로 5년 연속 영업적자. 심각한 유동성 부족.",
        "entities": [
            {"type": "company", "name": "부산주공", "role": "자동차 부품 주물"},
            {"type": "company", "name": "세연에이엠", "role": "최대주주 5.12%"},
            {"type": "company", "name": "재단법인 중도", "role": "CB 인수"},
            {"type": "company", "name": "현대자동차", "role": "주요 거래처"},
            {"type": "person", "name": "장세훈", "role": "동국제강 3세, 대표이사"},
        ],
        "relations": [
            {"source": "재단법인 중도", "target": "부산주공", "type": "bond_purchase", "detail": "CB 2차례 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "누적 결손금 510억원, 부분잠식 진행", "severity": "critical"},
            {"type": "operational", "description": "울산공장 주조2라인 가동률 2.2%, 매출 전년비 34% 급감", "severity": "critical"},
            {"type": "financial", "description": "1년 내 상환 차입원리금 996억원, 유동성 압박", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/208",
        "title": "200만원짜리 케이에이치미디어, IHQ 어떻게 인수했나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-03-18",
        "summary": "필룩스그룹 계열사 자본금 200만원 케이에이치미디어가 1104억원으로 IHQ 인수. 메리츠증권 자금 공급.",
        "entities": [
            {"type": "company", "name": "필룩스그룹", "role": "지주회사"},
            {"type": "company", "name": "케이에이치미디어", "role": "인수 주체"},
            {"type": "company", "name": "IHQ", "role": "인수 대상"},
            {"type": "company", "name": "삼본전자", "role": "CB 발행"},
            {"type": "company", "name": "장원테크", "role": "CB 발행"},
            {"type": "company", "name": "이엑스티", "role": "CB 발행"},
            {"type": "company", "name": "메리츠증권", "role": "자금 공급"},
        ],
        "relations": [
            {"source": "케이에이치미디어", "target": "IHQ", "type": "acquisition", "detail": "1104억원 50.49% 인수"},
            {"source": "메리츠증권", "target": "케이에이치미디어", "type": "financing", "detail": "600억원 CB 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "자본금 200만원 회사가 1104억원 차입금으로 인수, 희석화 위험", "severity": "critical"},
            {"type": "governance", "description": "복수 계열사 CB 보유로 지배구조 복잡화, 케이에이치미디어 실질 장부회사", "severity": "high"},
            {"type": "market", "description": "이엑스티 주가 하락으로 전환가액 지속 하향조정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/203",
        "title": "아이오케이, 순환출자의 핵심 고리가 되다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-02-25",
        "summary": "광림그룹 2020년 12월 계열사 간 지분거래로 순환출자 구조 형성. 광림→아이오케이→광림 자금 순환.",
        "entities": [
            {"type": "company", "name": "광림", "role": "최상위 계열사"},
            {"type": "company", "name": "쌍방울", "role": "주요 주주"},
            {"type": "company", "name": "비비안", "role": "피인수회사"},
            {"type": "company", "name": "아이오케이", "role": "순환출자 핵심"},
            {"type": "company", "name": "포비스티앤씨", "role": "중간 계열사"},
            {"type": "person", "name": "배상윤", "role": "광림그룹 회장"},
            {"type": "person", "name": "원영식", "role": "W홀딩스컴퍼니 회장"},
        ],
        "relations": [
            {"source": "쌍방울", "target": "아이오케이", "type": "stock_transfer", "detail": "광림 지분 147억원 매각"},
            {"source": "광림", "target": "쌍방울", "type": "stock_transfer", "detail": "비비안 지분 222억원 매각"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 순환출자 구조로 지배권 추적 불명확", "severity": "high"},
            {"type": "financial", "description": "계열사 간 대규모 자금 이동으로 실제 자본 흐름 불투명", "severity": "high"},
            {"type": "regulatory", "description": "연쇄 거래 관련 공시 부족 및 투명성 부재", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/200",
        "title": "원영식과 김성태, 배상윤의 IHQ 인수 도울까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-02-15",
        "summary": "필룩스그룹 IHQ 인수에 989억원 필요. 원영식의 아이오케이와 김성태의 광림이 자금조달 지원.",
        "entities": [
            {"type": "company", "name": "필룩스그룹", "role": "IHQ 인수 주체"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "자금 제공"},
            {"type": "company", "name": "광림", "role": "자금 지원"},
            {"type": "company", "name": "케이에이치미디어", "role": "인수 실행"},
            {"type": "company", "name": "IHQ", "role": "인수 대상"},
            {"type": "person", "name": "원영식", "role": "W홀딩컴퍼니 회장"},
            {"type": "person", "name": "김성태", "role": "광림 회장"},
            {"type": "person", "name": "배상윤", "role": "필룩스그룹 회장"},
        ],
        "relations": [
            {"source": "아이오케이", "target": "필룩스그룹", "type": "financing", "detail": "이엑스티 CB 100억원 인수"},
            {"source": "광림", "target": "필룩스그룹", "type": "financing", "detail": "200억원 CB 상호 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "IHQ 인수 필요 989억원 중 900억원 미확보", "severity": "critical"},
            {"type": "governance", "description": "원영식/김성태/배상윤 간 복잡한 자금 순환, 관련당사자 거래 과다", "severity": "high"},
            {"type": "financial", "description": "차입인수(LBO) 활용 시 담보 주가 하락 반대매매 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/185",
        "title": "장원테크 전환사채 전환가격의 비밀",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-12-21",
        "summary": "장원테크 2년간 9차례 830억원 CB 발행. 5회차 CB가 공시가(1455원)보다 훨씬 낮은 994원에 전환.",
        "entities": [
            {"type": "company", "name": "장원테크", "role": "금속소재 IT기기 부품"},
            {"type": "company", "name": "필룩스", "role": "최대주주"},
            {"type": "company", "name": "삼본전자", "role": "필룩스 전신"},
            {"type": "company", "name": "한국채권투자자문", "role": "5회차 CB 인수"},
            {"type": "person", "name": "배상윤", "role": "필룩스그룹 회장"},
            {"type": "person", "name": "김형호", "role": "한국채권투자자문 대표"},
        ],
        "relations": [
            {"source": "필룩스", "target": "장원테크", "type": "ownership", "detail": "최대주주"},
        ],
        "risks": [
            {"type": "governance", "description": "리픽싱 조항으로 전환가액 액면가까지 인하 가능, 대주주 특혜", "severity": "high"},
            {"type": "financial", "description": "CB 830억원 발행으로 주주자본 희석 위험", "severity": "high"},
            {"type": "market", "description": "유상증자 할인 조건을 CB에 역적용하는 가장 심한 특혜 조항", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/178",
        "title": "아이오케이컴퍼니 매각, 초록뱀 살리기였나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-11-26",
        "summary": "아이오케이컴퍼니의 포비스티앤씨 인수(850억원)는 W홀딩컴퍼니 자산 재편 전략.",
        "entities": [
            {"type": "company", "name": "아이오케이컴퍼니", "role": "매각 대상"},
            {"type": "company", "name": "초록뱀", "role": "계열사"},
            {"type": "company", "name": "포비스티앤씨", "role": "인수자"},
            {"type": "company", "name": "더스카이팜", "role": "외식업 자회사"},
            {"type": "company", "name": "W홀딩컴퍼니", "role": "최대주주"},
            {"type": "person", "name": "원영식", "role": "W홀딩컴퍼니 회장"},
        ],
        "relations": [
            {"source": "포비스티앤씨", "target": "아이오케이컴퍼니", "type": "acquisition", "detail": "850억원 인수"},
            {"source": "초록뱀", "target": "더스카이팜", "type": "acquisition", "detail": "138억원, 유증 427억원"},
        ],
        "risks": [
            {"type": "governance", "description": "초록뱀 지분 전량 장내 매도 후 더스카이팜 지분 재이전, 일관성 부재", "severity": "high"},
            {"type": "financial", "description": "초록뱀 방송프로그램사업 실적 악화, 적자 상황", "severity": "high"},
            {"type": "market", "description": "투자조합 청산 예정으로 유동성 불확실", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/173",
        "title": "비덴트와 빗썸, 경영권 분쟁의 불씨 남았나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-11-05",
        "summary": "자본금 2억원 이니셜이 비트갤럭시아 지분 234억원 인수로 코스닥 상장사 3개 지배.",
        "entities": [
            {"type": "company", "name": "이니셜", "role": "비트갤럭시아 인수"},
            {"type": "company", "name": "비덴트", "role": "코스닥 상장사"},
            {"type": "company", "name": "비티원", "role": "비덴트 최대주주"},
            {"type": "company", "name": "빗썸홀딩스", "role": "암호화폐 지주사"},
            {"type": "company", "name": "포비스티앤씨", "role": "아이오케이 신규 경영권"},
            {"type": "person", "name": "강지연", "role": "이니셜 경영권자"},
            {"type": "person", "name": "김재욱", "role": "비티원 전 최대주주"},
            {"type": "person", "name": "이정훈", "role": "빗썸홀딩스 최대주주"},
        ],
        "relations": [
            {"source": "이니셜", "target": "비트갤럭시아", "type": "acquisition", "detail": "38.7% 지분 234억원 인수"},
            {"source": "비티원", "target": "비덴트", "type": "ownership", "detail": "18.52% 보유"},
            {"source": "비덴트", "target": "빗썸홀딩스", "type": "ownership", "detail": "34.22% 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "비덴트 경영권 놓고 이원컴포텍/이니셜 vs 포비스티앤씨 충돌 가능", "severity": "high"},
            {"type": "governance", "description": "아이오케이컴퍼니 새 주인이 빗썸홀딩스에 욕심 낼 경우 추가 분쟁", "severity": "high"},
            {"type": "financial", "description": "비트갤럭시아1호 비덴트 지분 8.26%가 7% 이자율 담보", "severity": "medium"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (14차 - 경남제약/필룩스/비덴트) ===\n")

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
