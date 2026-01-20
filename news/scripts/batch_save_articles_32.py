#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 32차 (필룩스그룹/셀트리온/아이오케이컴퍼니/이원컴포텍 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/189",
        "title": "정체성 바뀐 필룩스, 무엇으로 사는가?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-01-04",
        "summary": "필룩스가 조명기기 업체에서 기업투자 회사로 변모. 1,400억원 이상을 신약개발사 및 투자조합에 투자, 1,300억원 전환사채 발행.",
        "entities": [
            {"type": "company", "name": "필룩스", "role": "주요 분석 대상"},
            {"type": "company", "name": "VIRAL GENE", "role": "미국 신약개발 종속회사"},
            {"type": "company", "name": "장원테크", "role": "투자대상"},
            {"type": "company", "name": "CAR-TCELLKOR", "role": "신약개발 투자대상"},
            {"type": "company", "name": "LIMINAYUS PHARMA", "role": "신약개발 투자대상"},
        ],
        "relations": [
            {"source": "필룩스", "target": "VIRAL GENE", "type": "investment", "detail": "621억원 투자 매출 기여 없음"},
        ],
        "risks": [
            {"type": "financial", "description": "영업이익 100억원 이상에서 간신히 흑자 수준으로 급감", "severity": "critical"},
            {"type": "operational", "description": "621억원 투자한 신약개발사들 아직 매출/이익 기여 없음", "severity": "high"},
            {"type": "financial", "description": "1,300억원 전환사채 2021년 4월 이후 만기 도래", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/188",
        "title": "필룩스그룹에 배상윤 회장 돈 얼마나 들어갔나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-12-31",
        "summary": "배상윤 회장이 삼본전자를 무자본 M&A로 인수 후 상장사 4곳 인수. 필룩스 자금 등 700억원 이상 동원, 그랜드 하얏트 호텔 투자로 손실 누적.",
        "entities": [
            {"type": "person", "name": "배상윤", "role": "회장"},
            {"type": "company", "name": "삼본전자", "role": "인수 대상"},
            {"type": "company", "name": "필룩스", "role": "인수 대상"},
            {"type": "company", "name": "장원테크", "role": "인수 대상"},
            {"type": "company", "name": "이엑스티", "role": "인수 대상"},
            {"type": "company", "name": "인마크제일호사모투자", "role": "펀드"},
        ],
        "relations": [
            {"source": "배상윤", "target": "삼본전자", "type": "acquisition", "detail": "2018년 8월 무자본 M&A 인수"},
            {"source": "삼본전자", "target": "장원테크", "type": "acquisition", "detail": "2019년 1월 인수 182억원"},
            {"source": "필룩스", "target": "인마크제일호사모투자", "type": "investment", "detail": "총 440억원 출자"},
        ],
        "risks": [
            {"type": "financial", "description": "그랜드 하얏트 호텔 투자에서 400억원 이상 손실", "severity": "critical"},
            {"type": "governance", "description": "복잡한 투자 구조로 자금 흐름 추적 어려움", "severity": "high"},
            {"type": "financial", "description": "배상윤 회장이 2년간 자기 자금 없이 상장사 4곳 인수", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/187",
        "title": "삼본전자는 어떻게 필룩스그룹의 꼭지점이 됐나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-12-28",
        "summary": "배상윤 회장의 클로이투자조합이 삼본전자를 인수하며 필룩스 기업집단 형성. 자본잠식 상태의 여러 회사들이 무자본 인수에 나서는 복잡한 구조.",
        "entities": [
            {"type": "company", "name": "삼본전자", "role": "필룩스그룹 최상위 지배회사"},
            {"type": "company", "name": "필룩스", "role": "기업집단"},
            {"type": "person", "name": "배상윤", "role": "실질적 주인"},
            {"type": "company", "name": "클로이투자조합", "role": "삼본전자 최대주주"},
            {"type": "company", "name": "케이에이치블루홀딩스", "role": "삼본전자 인수 주체"},
            {"type": "company", "name": "에스모", "role": "인수자금 대출 기관"},
        ],
        "relations": [
            {"source": "배상윤", "target": "클로이투자조합", "type": "control", "detail": "최대 출자자"},
            {"source": "삼본전자", "target": "장원테크", "type": "acquisition", "detail": "2019년 1월 482억원 61.2% 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "자본잠식 상태 회사들의 연쇄적 무자본 M&A", "severity": "critical"},
            {"type": "governance", "description": "복합적 투자조합 구조를 통한 실질적 지배자 은폐", "severity": "critical"},
            {"type": "financial", "description": "매출 지속적 감소 영업이익 2018년 이후 적자 전환", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/186",
        "title": "장원테크는 전환사채 발행자금으로 무엇을 했을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-12-24",
        "summary": "장원테크가 9차례 전환사채 발행으로 막대한 자금 조달했으나 본업 확대보다 투자조합과 상장사 주식 매입에 사용. 당기순손실 550억원.",
        "entities": [
            {"type": "company", "name": "장원테크", "role": "자금 조달 및 투자 실행"},
            {"type": "company", "name": "삼본전자", "role": "최대주주"},
            {"type": "company", "name": "필룩스", "role": "최대주주"},
            {"type": "company", "name": "이엑스티", "role": "관계사"},
            {"type": "company", "name": "광림", "role": "투자처"},
        ],
        "relations": [
            {"source": "삼본전자", "target": "장원테크", "type": "ownership", "detail": "2019년 최대주주 변경"},
            {"source": "장원테크", "target": "광림", "type": "investment", "detail": "전환사채 100억원 매입"},
        ],
        "risks": [
            {"type": "financial", "description": "2020년 9월까지 영업손실 48억원 당기순손실 550억원", "severity": "critical"},
            {"type": "financial", "description": "매출 급락 전년 대비 50% 이하 현금유출 44억원", "severity": "critical"},
            {"type": "financial", "description": "자본 급감 572억원→300억원 부채 폭증 53억원→1113억원", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/185",
        "title": "장원테크 전환사채 전환가격의 비밀",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-12-21",
        "summary": "장원테크 2년간 9회 830억원 전환사채 발행. 5회차 전환사채가 994원에 전환되어 주주 이익이 사채권자에게 이전되는 구조.",
        "entities": [
            {"type": "company", "name": "장원테크", "role": "대상 기업"},
            {"type": "company", "name": "삼본전자", "role": "인수자"},
            {"type": "company", "name": "필룩스", "role": "현재 최대주주"},
            {"type": "company", "name": "한국채권투자자문", "role": "5회차 전환사채 인수자"},
            {"type": "person", "name": "배상윤", "role": "필룩스그룹 회장"},
        ],
        "relations": [
            {"source": "배상윤", "target": "건하홀딩스", "type": "ownership", "detail": "최대주주"},
            {"source": "필룩스", "target": "장원테크", "type": "ownership", "detail": "23.16% 지분 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 계층적 지배구조로 4개 상장사 간접 지배", "severity": "high"},
            {"type": "financial", "description": "5회차 전환사채 994원 전환 시가 대비 50% 할인", "severity": "critical"},
            {"type": "market", "description": "주가 오르는 중 낮은 가격 발행 주식 등장 희석효과로 주가 하락", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/184",
        "title": "셀트리온 '합병법인'의 올해 매출과 영업이익 얼마?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-12-17",
        "summary": "셀트리온 3사를 하나로 가정했을 때 3분기 누적 매출 1조4288억원(59%↑), 영업이익 5114억원(73%↑). 합병 시 이중계산 문제 분석.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "의약품 제조사"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "의약품 판매사"},
            {"type": "company", "name": "셀트리온제약", "role": "계열사"},
            {"type": "person", "name": "서정진", "role": "셀트리온그룹 회장"},
        ],
        "relations": [
            {"source": "셀트리온홀딩스", "target": "셀트리온", "type": "ownership", "detail": "계열사로 보유"},
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "business", "detail": "의약품 판매"},
        ],
        "risks": [
            {"type": "operational", "description": "셀트리온헬스케어 재고자산 3분기 3000억원 이상 증가", "severity": "medium"},
            {"type": "financial", "description": "합병법인 매출이 단순 합산의 55%로 축소 이중계산 문제", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/183",
        "title": "셀트리온 매출 급증, 어떻게 볼 것인가?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-12-14",
        "summary": "셀트리온과 셀트리온헬스케어 3분기 매출 역대 최고 기록. 매출채권과 재고자산 동시 증가로 현금흐름 문제 발생.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "의약품 생산업체"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "의약품 판매업체"},
            {"type": "company", "name": "셀트리온제약", "role": "국내 판매 담당"},
            {"type": "person", "name": "서정진", "role": "셀트리온 회장"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "supply", "detail": "의약품 판매 대부분 외상"},
        ],
        "risks": [
            {"type": "financial", "description": "매출채권 9월말 4628억원 증가 영업현금흐름 1508억원 괴리", "severity": "high"},
            {"type": "financial", "description": "셀트리온헬스케어 매출채권 2000억원 재고자산 3000억원 증가 5000억원 자산 잠김", "severity": "high"},
            {"type": "operational", "description": "셀트리온헬스케어 영업활동 현금흐름 -160억원 적자", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/182",
        "title": "코로나19의 시대, 투자도 자금조달도 달랐다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-12-10",
        "summary": "코로나19로 코스피 상장사 매출 평균 4.3% 감소했으나 현금흐름 중심 경영으로 영업현금흐름 41.2% 증가. 자본적지출 줄이고 외부차입으로 유동성 확보.",
        "entities": [
            {"type": "company", "name": "삼성전자", "role": "대형 상장사"},
            {"type": "company", "name": "코스피 상장사", "role": "분석 대상 633개사"},
        ],
        "relations": [],
        "risks": [
            {"type": "operational", "description": "코로나19로 사람 이동 제한 기업 매출에 직접적 영향", "severity": "high"},
            {"type": "financial", "description": "차입금 급증 약 2배로 재정 건전성 우려", "severity": "high"},
            {"type": "operational", "description": "자본적지출 축소로 장기적 경쟁력 저하 가능성", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/181",
        "title": "나쁘지 않은 상장기업 실적, 현금흐름의 실속은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-12-07",
        "summary": "코스피 상장기업 536개사 3분기 실적 분석. 영업현금흐름의 47%가 운전자금 회수에서 비롯 실제 영업 성과와 괴리.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "바이오시밀러 제조사"},
            {"type": "company", "name": "삼성바이오로직스", "role": "CMO업체"},
            {"type": "company", "name": "엔씨소프트", "role": "게임사"},
            {"type": "company", "name": "씨제이씨지브이", "role": "영화관 운영사"},
            {"type": "company", "name": "제주항공", "role": "항공사"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "sales", "detail": "특수관계인 통해 해외 매출 대부분 외상판매"},
        ],
        "risks": [
            {"type": "financial", "description": "237개 기업 영업현금흐름 47%가 운전자금 회수에서 비롯", "severity": "high"},
            {"type": "financial", "description": "17개 기업 영업현금흐름 전부가 운전자금 회수에만 의존", "severity": "critical"},
            {"type": "operational", "description": "셀트리온 4867억원이 운전자금에 묶여 현금 수취 지연", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/180",
        "title": "온라인 쇼핑과 코로나19의 이중 습격, 신세계 실적은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-12-03",
        "summary": "신세계가 온라인 쇼핑 약진과 코로나19 사회적 거리두기 이중 타격. 백화점은 명품/가전 중심 전환, 면세점 극심한 부진으로 전체 실적 악화.",
        "entities": [
            {"type": "company", "name": "신세계", "role": "백화점 및 유통 그룹"},
            {"type": "company", "name": "신세계디에프", "role": "면세점 운영사"},
            {"type": "company", "name": "신세계센트럴시티", "role": "호텔업 계열사"},
            {"type": "company", "name": "쿠팡", "role": "온라인 쇼핑업체"},
        ],
        "relations": [
            {"source": "신세계", "target": "신세계디에프", "type": "ownership", "detail": "계열사로 면세점 운영"},
        ],
        "risks": [
            {"type": "market", "description": "온라인 쇼핑업체 약진으로 오프라인 유통 시장 지속 축소", "severity": "critical"},
            {"type": "operational", "description": "면세점 매출 거의 반 토막 누적 영업손실 899억원", "severity": "critical"},
            {"type": "financial", "description": "연결 기준 매출 전년 74% 수준 3분기까지 누적 적자", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/179",
        "title": "실적 좋아진 ㈜한진, 왜 유상증자까지 했을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-11-30",
        "summary": "한진이 20년 만에 1084억원 유상증자. 영업실적 개선에도 금융비용 부담이 크고 금융리스 비용이 영업이익 초과. 택배사업 시설투자 자금 확보 목적.",
        "entities": [
            {"type": "company", "name": "한진", "role": "주요 분석 대상"},
            {"type": "company", "name": "한진그룹", "role": "상위 그룹사"},
            {"type": "company", "name": "대한항공", "role": "계열사 유동성 위기"},
            {"type": "company", "name": "한진칼", "role": "지주사 경영권 분쟁"},
            {"type": "company", "name": "CJ대한통운", "role": "택배업계 1위"},
            {"type": "person", "name": "강성부", "role": "KCGI펀드 대표"},
        ],
        "relations": [
            {"source": "한진", "target": "대한항공", "type": "ownership", "detail": "한진칼을 통한 간접 지배"},
        ],
        "risks": [
            {"type": "financial", "description": "연간 1100억원대 금융비용 영업이익이 순이익으로 전환 못함", "severity": "critical"},
            {"type": "financial", "description": "1조 8369억원 총 리스료 상환 의무 약 20년 상환 기간", "severity": "high"},
            {"type": "governance", "description": "한진칼 경영권 분쟁으로 그룹 자금 배분 불확실성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/178",
        "title": "아이오케이컴퍼니 매각, 초록뱀 살리기였나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-11-26",
        "summary": "원영식 회장이 아이오케이컴퍼니를 포비스티앤씨에 850억원에 매각 후 더스카이팜 지분을 초록뱀을 통해 인수. 초록뱀 불안정한 사업 실적 보완 전략.",
        "entities": [
            {"type": "company", "name": "아이오케이컴퍼니", "role": "매각 대상"},
            {"type": "company", "name": "초록뱀", "role": "수익사업 운영사"},
            {"type": "company", "name": "포비스티앤씨", "role": "인수자"},
            {"type": "company", "name": "더스카이팜", "role": "외식 사업 자회사"},
            {"type": "company", "name": "W홀딩컴퍼니", "role": "원영식 계열 지주회사"},
            {"type": "person", "name": "원영식", "role": "전 최대주주"},
        ],
        "relations": [
            {"source": "아이오케이컴퍼니", "target": "포비스티앤씨", "type": "acquisition", "detail": "850억원에 매각 2020년 8월"},
            {"source": "원영식", "target": "초록뱀", "type": "ownership_transfer", "detail": "더스카이팜 지분 138억원 인수"},
        ],
        "risks": [
            {"type": "operational", "description": "초록뱀 방송프로그램사업 매출 변동성 크고 하향세", "severity": "high"},
            {"type": "governance", "description": "계열사 간 복잡한 지분 거래 및 전환사채 구조", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/177",
        "title": "원영식씨는 왜 아이오케이컴퍼니를 팔았을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-11-20",
        "summary": "원영식 회장 아이오케이컴퍼니 매각 배경 분석. 투자 축소 신호, 홈캐스트 사건 심리적 영향, 아들 원성준에게 자산 이전 전략 가능성.",
        "entities": [
            {"type": "person", "name": "원영식", "role": "W홀딩컴퍼니 회장"},
            {"type": "person", "name": "원성준", "role": "원영식의 아들"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "엔터테인먼트 회사"},
            {"type": "company", "name": "초록뱀", "role": "엔터테인먼트/프로그램 제작사"},
            {"type": "company", "name": "W홀딩컴퍼니", "role": "지주회사"},
            {"type": "company", "name": "더스카이팜", "role": "외식업체"},
        ],
        "relations": [
            {"source": "원영식", "target": "오션인더블유", "type": "ownership", "detail": "100% 지분 소유"},
            {"source": "오션인더블유", "target": "W홀딩컴퍼니", "type": "control", "detail": "지배주주"},
            {"source": "W홀딩컴퍼니", "target": "아이오케이컴퍼니", "type": "ownership", "detail": "단독 최대주주"},
        ],
        "risks": [
            {"type": "legal", "description": "홈캐스트 사건 1심 징역 2년 대법원 무죄 판결 명성 손상 지속", "severity": "high"},
            {"type": "governance", "description": "원성준 이름 투자조합 구조화 상속/증여세 회피 의도", "severity": "high"},
            {"type": "financial", "description": "아이오케이컴퍼니 6월말 245억원 결손 상장사 축소 시 자금조달 어려움", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/176",
        "title": "포비스티앤씨는 아이오케이컴퍼니를 왜 그렇게 비싸게 샀을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-11-16",
        "summary": "포비스티앤씨가 아이오케이컴퍼니 지분을 주당 4356원에 인수. 전환사채 인수와 현금 회수 고려 시 실제 비용 600억원 수준. 경영권 프리미엄 87-158%.",
        "entities": [
            {"type": "company", "name": "포비스티앤씨", "role": "인수자"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "피인수 대상"},
            {"type": "company", "name": "W홀딩컴퍼니", "role": "주식 매도자"},
            {"type": "person", "name": "원영식", "role": "주요 주주 및 매도자"},
            {"type": "person", "name": "원성준", "role": "원영식 아들"},
        ],
        "relations": [
            {"source": "포비스티앤씨", "target": "아이오케이컴퍼니", "type": "acquisition", "detail": "주당 4356원 1951만주 850억원 규모"},
        ],
        "risks": [
            {"type": "governance", "description": "87-158% 경영권 프리미엄 외부평가 객관성 부족", "severity": "high"},
            {"type": "financial", "description": "거래 구조로 실제 인수 비용 대폭 절감 소액주주 의결권 가치 부당 평가", "severity": "high"},
            {"type": "market", "description": "M&A 공시 직전 급등 주가 기준 정보 비대칭 공시 후 주가 급락", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/175",
        "title": "포비스티앤씨는 아이오케이컴퍼니를 무슨 돈으로 인수했을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-11-12",
        "summary": "포비스티앤씨가 아이오케이컴퍼니 인수에 100억원을 우리들휴브레인 전환사채로 조달 후 5일 만에 상환. 매도자가 매수자에게 간접적 자금 지원 구조.",
        "entities": [
            {"type": "company", "name": "포비스티앤씨", "role": "인수자"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "인수 대상"},
            {"type": "company", "name": "W홀딩컴퍼니", "role": "매도자"},
            {"type": "company", "name": "우리들휴브레인", "role": "전환사채 발행사"},
            {"type": "company", "name": "미래산업", "role": "공동 인수자"},
            {"type": "person", "name": "원영식", "role": "W홀딩컴퍼니 회장"},
            {"type": "person", "name": "강수진", "role": "원영식 배우자"},
        ],
        "relations": [
            {"source": "포비스티앤씨", "target": "아이오케이컴퍼니", "type": "acquisition", "detail": "850억원에 지분 38.45% 인수"},
            {"source": "W홀딩컴퍼니", "target": "우리들휴브레인", "type": "control", "detail": "투자조합 통해 실질적 지배"},
            {"source": "우리들휴브레인", "target": "포비스티앤씨", "type": "financing", "detail": "100억원 전환사채 5일간 보유 후 상환"},
        ],
        "risks": [
            {"type": "financial", "description": "843억원 인수자금 필요했으나 자체 유동성 240억원으로 부족 자금 출처 추적 어려움", "severity": "critical"},
            {"type": "governance", "description": "매도자가 우리들휴브레인 통해 매수자 자금 간접 지원 이해관계 상충", "severity": "high"},
            {"type": "financial", "description": "5일 만에 상환한 100억원 전환사채 상환 자금 출처 불명확", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/174",
        "title": "배 부른 이원컴포텍 인수자들, 바이오사업 적극 나설까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-11-09",
        "summary": "이원컴포텍 주가 1년 미만에 1000원대→1만원대 급등했으나 실적 악화. 신약 개발 기대감으로 상승했지만 리미나투스파마와 협력일 뿐 지분 관계 없음.",
        "entities": [
            {"type": "company", "name": "이원컴포텍", "role": "주요 분석 대상"},
            {"type": "company", "name": "리미나투스파마", "role": "신약 개발 파트너"},
            {"type": "company", "name": "프로페이스 사이언시스", "role": "대주주"},
            {"type": "company", "name": "비트갤럭시아", "role": "빗썸 지배구조 최정점"},
            {"type": "person", "name": "스캇 월드만", "role": "리미나투스파마 개발 주도"},
        ],
        "relations": [
            {"source": "이원컴포텍", "target": "리미나투스파마", "type": "partnership", "detail": "신약개발 협력 지분 관계 없음"},
            {"source": "이원컴포텍", "target": "비트갤럭시아", "type": "investment", "detail": "300억원 지분 인수"},
        ],
        "risks": [
            {"type": "market", "description": "주가 상승이 실적 개선 없이 기대감에만 의존 신약 개발 성공 불확실", "severity": "critical"},
            {"type": "operational", "description": "자금조달 계획 1년 이상 지연 바이오사업 추진 정체", "severity": "high"},
            {"type": "financial", "description": "실적 악화 매출 75% 감소 영업적자 전환 고평가 주가 조정 위험", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/173",
        "title": "비덴트와 빗썸, 경영권 분쟁의 불씨 남았나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-11-05",
        "summary": "김재욱과 이정훈 빗썸 경영권 분쟁 합의로 마무리. 아이오케이컴퍼니 신규 주인이 비덴트 경영권 도전 시 새로운 경영권 싸움 가능.",
        "entities": [
            {"type": "person", "name": "강지연", "role": "이니셜 인수자"},
            {"type": "person", "name": "김재욱", "role": "버킷스튜디오 최대주주"},
            {"type": "person", "name": "이정훈", "role": "빗썸홀딩스 최대주주"},
            {"type": "person", "name": "원영식", "role": "아이오케이컴퍼니 이전 경영권"},
            {"type": "company", "name": "비덴트", "role": "코스닥 상장사"},
            {"type": "company", "name": "빗썸홀딩스", "role": "경영권 분쟁 대상"},
            {"type": "company", "name": "비티원", "role": "비덴트 최대주주"},
        ],
        "relations": [
            {"source": "비티원", "target": "비덴트", "type": "ownership", "detail": "18.52% 지분 보유"},
            {"source": "아이오케이컴퍼니", "target": "비덴트", "type": "ownership", "detail": "928만주 전환사채 보유 지분율 21.12%"},
            {"source": "비덴트", "target": "빗썸홀딩스", "type": "ownership", "detail": "34.22% 지분 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "아이오케이컴퍼니 신규 경영진 보유 비덴트 전환사채 전환 시 경영권 구도 변경", "severity": "critical"},
            {"type": "financial", "description": "비트갤럭시아1호 비덴트 지분 8.26% 7% 이자율 차입금 담보 추가 자금 압박", "severity": "high"},
            {"type": "legal", "description": "복잡한 지분구조와 전환사채로 향후 경영권 분쟁 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/172",
        "title": "이원컴포텍과 이니셜, 한 몸일까 딴 몸일까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-11-02",
        "summary": "이원컴포텍이 비트갤럭시아 지분 300억원 인수 후 430주를 이니셜에 양도하며 실질적 경영권 이전. 자금동원 능력 의문의 이니셜이 경영진 임명권 행사.",
        "entities": [
            {"type": "company", "name": "이원컴포텍", "role": "비트갤럭시아 초기 인수사"},
            {"type": "company", "name": "이니셜", "role": "중소벤처기업 경영권 행사"},
            {"type": "company", "name": "비트갤럭시아1호투자조합", "role": "빗썸 지배구조 최상단"},
            {"type": "person", "name": "김재욱", "role": "비트갤럭시아 원래 지분 보유자"},
            {"type": "person", "name": "강지연", "role": "이니셜 대표"},
            {"type": "person", "name": "이경훈", "role": "이원컴포텍 대표"},
        ],
        "relations": [
            {"source": "이원컴포텍", "target": "비트갤럭시아1호투자조합", "type": "acquisition", "detail": "300억원 749주 인수 후 430주 이니셜 양도"},
            {"source": "이니셜", "target": "비트갤럭시아1호투자조합", "type": "acquisition", "detail": "430주 인수 약 232억원 경영권 실질 장악"},
        ],
        "risks": [
            {"type": "governance", "description": "이원컴포텍 이사회 결의 전 120억원 계약금 선집행 사후 결의 투명성 부재", "severity": "critical"},
            {"type": "financial", "description": "자산 446억원 자기자본 172억원 회사가 300억원 투자 과도한 레버리지", "severity": "critical"},
            {"type": "financial", "description": "매출 47억원 순이익 7000만원 이니셜이 200억원 이상 자금 동원 경로 미공시", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/171",
        "title": "이원컴포텍의 수상한 경영진, 이 조합 뭐야?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-10-29",
        "summary": "이원컴포텍의 실제 주인이 베일에 가려져 있으며 최대주주 변경 과정에서 투자조합들의 복잡한 지분 구조와 의심스러운 경영진 구성 드러남.",
        "entities": [
            {"type": "company", "name": "이원컴포텍", "role": "분석 대상"},
            {"type": "company", "name": "사보이투자1호조합", "role": "현재 최대주주"},
            {"type": "company", "name": "에이루트", "role": "세우테크 후신"},
            {"type": "company", "name": "필룩스", "role": "리미나투스파마 모회사"},
            {"type": "company", "name": "리미나투스파마", "role": "필룩스 자회사"},
            {"type": "person", "name": "서문동군", "role": "이원컴포텍 사내이사"},
            {"type": "person", "name": "스캇 월드만", "role": "리미나투스파마 대표"},
            {"type": "person", "name": "이경훈", "role": "이원컴포텍 대표"},
        ],
        "relations": [
            {"source": "이원컴포텍", "target": "사보이투자1호조합", "type": "ownership", "detail": "최대주주 관계"},
            {"source": "스캇 월드만", "target": "필룩스", "type": "employment", "detail": "지난해 10월까지 사내이사"},
            {"source": "리미나투스파마", "target": "이원컴포텍", "type": "partnership", "detail": "연구개발 제휴 아시아 판권"},
        ],
        "risks": [
            {"type": "governance", "description": "실제 최대주주 정체 불명확 포르투나제1호 출자자 7인 신원 미공개", "severity": "critical"},
            {"type": "governance", "description": "필룩스가 리미나투스파마 100% 지분 보유하면서 관계기업 분류 실질 지배력 부재 의심", "severity": "high"},
            {"type": "operational", "description": "스캇 월드만 해리 아레나 필룩스에서 이원컴포텍으로 이동 리미나투스파마 나스닥 상장 중단", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/170",
        "title": "이원컴포텍의 실제 주주, 과연 누구일까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-10-26",
        "summary": "이원컴포텍의 지배구조가 투자조합과 미국 바이오기업을 통해 복잡하게 얽혀 있으며 실제 주주 관계 불명확. 프로페이스 사이언시스는 실체 확인 안 되는 미국 기업.",
        "entities": [
            {"type": "company", "name": "이원컴포텍", "role": "피인수 기업"},
            {"type": "company", "name": "에이루트", "role": "최대 출자자 코스닥"},
            {"type": "company", "name": "프로페이스 사이언시스", "role": "미국 바이오기업 신규 투자자"},
            {"type": "company", "name": "사보이투자1호", "role": "구주 인수 투자조합"},
            {"type": "company", "name": "필룩스", "role": "LED 조명 제조사"},
            {"type": "company", "name": "리미나투스파마", "role": "필룩스 100% 자회사"},
            {"type": "person", "name": "헬렌 킴", "role": "프로페이스 사이언시스 최대주주"},
            {"type": "person", "name": "스캇 월드만", "role": "리미나투스파마 대표"},
        ],
        "relations": [
            {"source": "에이루트", "target": "이원컴포텍", "type": "ownership", "detail": "5% 이상 지분 투자조합 통해 간접보유"},
            {"source": "프로페이스 사이언시스", "target": "이원컴포텍", "type": "investment", "detail": "유상신주 82.6억원+전환사채 48-52억원 총 130억원"},
            {"source": "스캇 월드만", "target": "이원컴포텍", "type": "management", "detail": "글로벌 및 아시아 바이오사업 진두지휘"},
        ],
        "risks": [
            {"type": "governance", "description": "투자조합과 해외 기업 통한 복잡한 지배구조 실제 주주 추적 어려움", "severity": "critical"},
            {"type": "regulatory", "description": "프로페이스 사이언시스 실체 미확인 블룸버그 구글 검색 불가능", "severity": "critical"},
            {"type": "financial", "description": "프로페이스 사이언시스 자산총액 85.2억원보다 많은 130억원 투자 수행", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (32차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}... ({result.get('error', 'Unknown error')})")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
