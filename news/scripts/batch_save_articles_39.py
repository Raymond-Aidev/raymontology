#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 39차 (금호그룹/셀트리온 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/49",
        "title": "색동 날개 꺾인 금호그룹(27)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-08-03",
        "summary": "금호그룹이 2008년 대한통운 인수 과정에서 약 1조5000억원을 차입금으로 조달하면서 재무구조가 악화되었다. 이후 글로벌 금융위기와 높은 이자부담으로 아시아나항공은 적자에 빠졌고, 금호산업은 대우건설 풋백옵션으로 인해 워크아웃까지 신청하게 된다.",
        "entities": [
            {"type": "company", "name": "금호그룹", "role": "지주회사"},
            {"type": "company", "name": "아시아나항공", "role": "대한통운 인수 주체"},
            {"type": "company", "name": "대한통운", "role": "인수 대상"},
            {"type": "company", "name": "금호산업", "role": "지주회사"},
            {"type": "company", "name": "대우건설", "role": "2006년 인수 대상"},
        ],
        "relations": [
            {"source": "아시아나항공", "target": "대한통운", "type": "acquisition", "detail": "2008년 약 1조5450억원으로 지분 23.98% 취득"},
            {"source": "대한통운", "target": "금호산업", "type": "financing", "detail": "금호산업에 현금 3400억원 공급"},
        ],
        "risks": [
            {"type": "financial", "description": "대한통운 인수자금 1조4400억원을 차입금으로 조달하여 차입금이 4조원 돌파", "severity": "critical"},
            {"type": "financial", "description": "교환사채 5600억원의 높은 이자율 9.5%로 인한 이자부담 급증", "severity": "high"},
            {"type": "strategic", "description": "대우건설 풋백옵션으로 인해 2009년 금호산업이 2조원의 당기순손실 기록", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/48",
        "title": "색동 날개 꺾인 금호그룹(26)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-08-01",
        "summary": "오버넷이 2004년 엘로우통신 등 3개사를 통해 대한통운 지분을 매집했으며, 실제 투자 주체는 홍콩 투자회사 파마그룹으로 추정된다. 파마그룹은 2000년 오버넷에 270억원을 투자했다가 2006년 200억원만 받고 철수하는 과정에서 의문점이 발견되었다.",
        "entities": [
            {"type": "company", "name": "오버넷", "role": "벤처기업, 자금 대여자"},
            {"type": "company", "name": "대한통운", "role": "지분 매수 대상 회사"},
            {"type": "company", "name": "파마그룹", "role": "실제 투자 주체"},
            {"type": "company", "name": "엘로우통신", "role": "명의 차입자"},
            {"type": "person", "name": "신창호", "role": "오버넷 대표"},
        ],
        "relations": [
            {"source": "파마그룹", "target": "오버넷", "type": "investment", "detail": "2000년 3월 270억원 출자, 2006년 200억원에 회수"},
            {"source": "오버넷", "target": "엘로우통신", "type": "lending", "detail": "2004년 12월 245억원 대여, 담보로 278억원 대한통운 주식"},
        ],
        "risks": [
            {"type": "governance", "description": "대한통운 지분 매집의 실제 주체가 불명확하며, 오버넷 임직원이 회사 현금 전액에 해당하는 245억원을 차입한 목적이 공시되지 않음", "severity": "critical"},
            {"type": "financial", "description": "파마그룹이 투자 원금 대비 70억원의 손실을 입고 철수했으나, 대한통운 투자 수익 배분 구조가 투명하지 않음", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/47",
        "title": "색동 날개 꺾인 금호그룹(25)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-07-27",
        "summary": "대한통운 지분 14.5%를 매집한 주체는 연 매출 100억원의 벤처기업 오버넷이었으나, 실제 투자 주체는 오버넷의 주주인 외국 투자회사 브로드밴드였다. 오버넷은 5% 공시 의무를 피하기 위해 엘로우통신 등 3개사를 통해 지분을 분산 매집했다.",
        "entities": [
            {"type": "company", "name": "오버넷", "role": "대한통운 지분 매집 주체 (명목상)"},
            {"type": "company", "name": "브로드밴드 인베스트먼트", "role": "실제 투자 주체"},
            {"type": "company", "name": "STX 팬오션", "role": "대한통운 지분 최종 인수자"},
            {"type": "company", "name": "금호그룹", "role": "대한통운 인수전 참여자"},
            {"type": "person", "name": "신창호", "role": "오버넷 최대주주 및 대표이사"},
        ],
        "relations": [
            {"source": "브로드밴드 인베스트먼트", "target": "오버넷", "type": "investment", "detail": "대한통운 주식 매집 자금 조성"},
            {"source": "오버넷", "target": "STX 팬오션", "type": "divestiture", "detail": "대한통운 주식 160만주를 주당 7만원에 매각(1120억원)"},
        ],
        "risks": [
            {"type": "regulatory", "description": "5% 이상 지분 공시 의무를 회피하기 위해 엘로우통신 등 3개사를 통한 편법적 분산 매집", "severity": "high"},
            {"type": "governance", "description": "3개사는 외감법인이 아니라 공시 의무가 없었고, 오버넷은 이들과의 거래를 교묘히 숨김", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/46",
        "title": "색동 날개 꺾인 금호그룹(24)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-07-25",
        "summary": "박삼구 회장이 대한통운 인수 후 현금 회수를 위해 금호터미널을 2,190억원에 매각했다. 금호산업은 2006년 부동산 자산 80%를 분할해 금호터미널과 금호리조트를 설립했으며, 이들은 그룹 내 자금 조달 수단으로 활용되었다.",
        "entities": [
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
            {"type": "person", "name": "박찬구", "role": "아시아나항공 회장"},
            {"type": "company", "name": "금호산업", "role": "금호그룹 계열사"},
            {"type": "company", "name": "금호터미널", "role": "여객버스터미널 사업"},
            {"type": "company", "name": "금호리조트", "role": "레저사업"},
            {"type": "company", "name": "대한통운", "role": "인수 대상"},
        ],
        "relations": [
            {"source": "금호산업", "target": "금호터미널", "type": "spin-off", "detail": "2006년 9월 여객버스터미널 사업부문 분할"},
            {"source": "금호산업", "target": "금호터미널", "type": "divestiture", "detail": "2009년 대한통운에 양도하고 2,190억원 현금 회수"},
        ],
        "risks": [
            {"type": "financial", "description": "금호그룹이 영업활동에서 꾸준히 잉여현금흐름을 창출하는 곳이 없어 대규모 인수자금 조달을 위해 자산 매각에 의존", "severity": "high"},
            {"type": "governance", "description": "금호터미널과 금호리조트가 다른 계열사의 자금을 활용하기 위한 도구로 활용되어 계열사 간 자금 이전의 수단화", "severity": "high"},
            {"type": "strategic", "description": "헐값에 팔렸다는 박찬구의 반발로 형제 간 분쟁 재발", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/45",
        "title": "색동 날개 꺾인 금호그룹(23)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-07-19",
        "summary": "금호홀딩스가 금호고속을 인수하는 과정에서 실제 유출된 현금은 약 1,200억원으로, 칸서스KHB 사모펀드에서 돌려받은 자금과 금호고속이 보유한 1,100억원의 현금으로 인수 대가의 일부를 충당했다. 금호고속의 현금은 금호리조트와 금호건설 등 자회사 매각으로 확보되었다.",
        "entities": [
            {"type": "company", "name": "금호홀딩스", "role": "금호고속 인수 주체"},
            {"type": "company", "name": "금호고속", "role": "인수 대상 회사"},
            {"type": "company", "name": "칸서스KHB 사모펀드", "role": "금호고속 중간 보유 주체"},
            {"type": "company", "name": "케이에이인베스트", "role": "금호고속 자회사 인수 주체"},
            {"type": "person", "name": "현정은", "role": "현대투자파트너스 최대 지분 보유자"},
        ],
        "relations": [
            {"source": "금호홀딩스", "target": "금호고속", "type": "acquisition", "detail": "3,676억원에 인수 후 흡수합병"},
            {"source": "금호고속", "target": "금호리조트", "type": "divestiture", "detail": "자회사 매각으로 1,700억원 규모 현금 조성"},
        ],
        "risks": [
            {"type": "financial", "description": "금호홀딩스의 합병으로 인한 부채 증가로 재무상태 악화. 세 회사 통합 과정에서 거액의 외부 차입금 필요", "severity": "critical"},
            {"type": "governance", "description": "현대투자파트너스의 의사결정 구조가 불명확하며, 비계열사 지분 보유로 인한 지배 관계의 투명성 부족", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/44",
        "title": "색동 날개 꺾인 금호그룹(22)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-07-16",
        "summary": "금호그룹 박삼구 회장이 금호고속 인수 자금을 외부 차입금으로 조달했으며, 계열사들을 동원해 유동성 위기를 해결했다. 하이난항공그룹으로부터 1600억원 신주인수권부사채를 발행받아 금호고속 인수에 투입했다.",
        "entities": [
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
            {"type": "company", "name": "금호홀딩스", "role": "금호그룹 지주사"},
            {"type": "company", "name": "금호고속", "role": "인수 대상 기업"},
            {"type": "company", "name": "하이난항공그룹", "role": "신주인수권부사채 인수처"},
            {"type": "company", "name": "아시아나항공", "role": "계열사"},
            {"type": "person", "name": "아담 탄", "role": "하이난항공그룹 최고경영자"},
        ],
        "relations": [
            {"source": "박삼구", "target": "금호고속", "type": "acquisition", "detail": "금호홀딩스를 통해 자체자금 1885억원과 인수금융 1850억원으로 인수"},
            {"source": "하이난항공그룹", "target": "금호홀딩스", "type": "financing", "detail": "1600억원 규모의 신주인수권부사채 발행"},
        ],
        "risks": [
            {"type": "financial", "description": "금호홀딩스가 실질적으로 모든 자금을 외부 차입금으로 조달하고 있으며, 유동성 위기 상황에서 계열사 자금 동원으로 부채 악순환 초래", "severity": "critical"},
            {"type": "governance", "description": "박삼구 회장이 공정거래법 규정을 회피하기 위해 거래를 분할하여 이사회 결의 및 공시 의무를 회피", "severity": "critical"},
            {"type": "regulatory", "description": "금호산업이 상법상 신용공여 금지 규정을 위반하여 금호기업에 자금을 대여하되 이사회 결의 없이 진행", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/43",
        "title": "색동 날개 꺾인 금호그룹(21)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-07-12",
        "summary": "금호고속은 중국·베트남 등에서 운영하던 13개 해외 합작사업에서 단계적으로 철수하고 있다. 웰투씨 사모펀드에 금호건설(홍콩)을 매각한 후 회수된 자금으로 차입금을 상환하는 구조다.",
        "entities": [
            {"type": "company", "name": "금호그룹", "role": "모회사"},
            {"type": "company", "name": "금호고속", "role": "해외사업 운영사"},
            {"type": "company", "name": "금호건설(홍콩)", "role": "해외 합작사 지주회사"},
            {"type": "company", "name": "웰투씨인베스트먼트", "role": "사모펀드 운용사"},
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
        ],
        "relations": [
            {"source": "금호고속", "target": "금호건설(홍콩)", "type": "divestiture", "detail": "2017년 웰투씨에 775억원에 매각, 2019년 2월 재매입"},
        ],
        "risks": [
            {"type": "financial", "description": "금호고속의 해외 합작사 순자산이 2012년 1,600억원에서 2018년 200억원 수준으로 급감", "severity": "high"},
            {"type": "strategic", "description": "금호그룹은 2010년 워크아웃 시와 달리 산업은행과 금융권의 협조가 이루어질 것 같지 않다는 우려", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/42",
        "title": "색동 날개 꺾인 금호그룹(20)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-07-09",
        "summary": "박삼구 회장의 금호그룹 복원 과정에서 계열사 자금을 활용한 M&A 수법이 반복되었으며, 금호고속 인수 시 자회사 분리 매각으로 약 2,160억원의 현금을 확보하여 순매입액을 1,500억원으로 축소했다. 금호건설(홍콩) 등 주요 자산이 외부 투자자에게 넘어가면서 그룹의 완전한 복원에 차질이 생겼다.",
        "entities": [
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
            {"type": "company", "name": "금호고속", "role": "피인수 기업"},
            {"type": "company", "name": "금호산업", "role": "계열사"},
            {"type": "company", "name": "아시아나항공", "role": "계열사"},
            {"type": "company", "name": "금호건설(홍콩)", "role": "지주회사"},
            {"type": "company", "name": "웰투씨인베스트먼트", "role": "금호건설(홍콩) 인수자"},
        ],
        "relations": [
            {"source": "박삼구", "target": "금호고속", "type": "acquisition", "detail": "3,676억원에 100% 지분 인수, 순매입액 약 1,500억원"},
            {"source": "아시아나항공", "target": "대한통운", "type": "financing", "detail": "대한통운 인수 시 1조8,500억원 출자"},
        ],
        "risks": [
            {"type": "governance", "description": "회장이 계열사 자산과 자금을 자신의 지배력 강화에 활용하는 지배구조 문제", "severity": "critical"},
            {"type": "financial", "description": "박삼구 회장 식 M&A는 늘 계열사 돈을 빼먹는 것으로 특징지어지는 현금 유출", "severity": "critical"},
            {"type": "strategic", "description": "금호건설(홍콩) 등 핵심 자산이 외부 투자자에게 이전되어 그룹 복원 불완전", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/41",
        "title": "색동 날개 꺾인 금호그룹(19)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-07-05",
        "summary": "금호그룹이 대우건설 지분 12.3%를 총수익교환약정(TRS)을 통해 유동화하여 약 2200~2400억원의 현금을 확보했으며, 이는 금호고속 인수자금 조성과 재무구조 개선을 위한 것이었다. 웰투씨인베스트먼트가 주도한 이 거래는 라임자산운용의 헤지펀드와 강남 부자들의 투자를 통해 실행되었다.",
        "entities": [
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
            {"type": "company", "name": "금호홀딩스", "role": "대우건설 지분 보유 및 유동화 주체"},
            {"type": "company", "name": "웰투씨인베스트먼트", "role": "사모펀드 운용사, TRS 거래 주관"},
            {"type": "company", "name": "라임자산운용", "role": "700억원 규모 헤지펀드 설정"},
            {"type": "company", "name": "대우건설", "role": "지분 매각 대상 기업"},
            {"type": "person", "name": "정승원", "role": "웰투씨인베스트먼트 대표"},
        ],
        "relations": [
            {"source": "금호홀딩스", "target": "웰투씨인베스트먼트", "type": "transaction", "detail": "대우건설 지분 TRS 계약을 통해 1567억원 차입"},
            {"source": "라임자산운용", "target": "금호홀딩스", "type": "financing", "detail": "700억원 규모 헤지펀드로 금호고속 인수금융 조성"},
        ],
        "risks": [
            {"type": "financial", "description": "금호그룹이 복잡한 구조화 금융(TRS, SPC)을 통해 차입금을 조달하여 재무 투명성과 건전성이 우려된다", "severity": "high"},
            {"type": "governance", "description": "웰투씨인베스트먼트 대표가 금호아시아나그룹 전략경영실 출신으로 박삼구 회장과의 관계 의심이 제기되고 있다", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/40",
        "title": "색동 날개 꺾인 금호그룹(18)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-07-02",
        "summary": "금호산업의 자산 매각과 사모펀드 활용을 통해 자금이 금호터미널로 흘러들어간 구조를 분석한다. 광주신세계의 전세보증금 5000억 원이 핵심 자금원으로 작용하여 금호산업 인수에 활용되었다.",
        "entities": [
            {"type": "company", "name": "금호산업", "role": "사업 운영 회사"},
            {"type": "company", "name": "금호터미널", "role": "자산 소유 및 재무 중심"},
            {"type": "company", "name": "금호고속", "role": "인수 대상"},
            {"type": "company", "name": "광주신세계", "role": "전세보증금 제공자"},
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
        ],
        "relations": [
            {"source": "광주신세계", "target": "금호터미널", "type": "financing", "detail": "2013년 전세보증금 5000억 원 제공"},
            {"source": "금호터미널", "target": "금호기업", "type": "merger", "detail": "2016년 금호기업을 역합병하며 차입금 상속"},
        ],
        "risks": [
            {"type": "financial", "description": "금호홀딩스 현금이 2015년 2600억 원에서 2016년 41억 원으로 급격히 감소", "severity": "critical"},
            {"type": "governance", "description": "비상장 법인 인수·합병 과정에서 공시 부족 및 기업가치 평가 미공개", "severity": "critical"},
            {"type": "operational", "description": "LBO 방식의 저질 인수로 피인수 기업 재무 악화 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/39",
        "title": "색동 날개 꺾인 금호그룹(17)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-06-28",
        "summary": "금호산업이 2012년 패키지 매각한 서울고속버스터미널과 광주신세계의 5000억원 전세 보증금 거래의 연관성을 분석하는 기사. 신세계그룹의 센트럴시티 매입(1조250억원)과 서울고속버스터미널 저가 매입(2200억원)의 전략적 의도를 의문시한다.",
        "entities": [
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
            {"type": "person", "name": "정용진", "role": "신세계그룹 부회장"},
            {"type": "company", "name": "금호산업", "role": "자산 매각자"},
            {"type": "company", "name": "금호터미널", "role": "아시아나항공 자회사"},
            {"type": "company", "name": "신세계그룹", "role": "자산 인수자"},
            {"type": "company", "name": "광주신세계", "role": "전세보증금 제공자"},
        ],
        "relations": [
            {"source": "금호산업", "target": "코에프씨 사모펀드", "type": "divestiture", "detail": "2012년 금호고속, 대우건설, 서울고속버스터미널 지분 패키지 매각"},
            {"source": "광주신세계", "target": "금호터미널", "type": "financing", "detail": "월세를 20년 전세로 변경, 5000억원 추가 보증금 지급(2013년 4월)"},
        ],
        "risks": [
            {"type": "strategic", "description": "신세계의 서울고속버스터미널 저가 매입이 센트럴시티 매입과 연계된 포괄적 부동산 전략의 일환으로 보임", "severity": "high"},
            {"type": "financial", "description": "신세계그룹의 차입금이 2011년 7400억원에서 2012년 2조2260억원으로 급증", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/38",
        "title": "색동 날개 꺾인 금호그룹(16)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-06-25",
        "summary": "금호산업은 2012년 금호고속 등 자산 매각으로 약 9,465억원을 확보하여 워크아웃 정상화의 기틀을 마련했다. 채권단이 주도한 3,000억원 유상증자 계획이 실권되면서 박삼구 회장 부자가 2,200억원 투자로 사실상 지배주주로 복귀했다.",
        "entities": [
            {"type": "company", "name": "금호산업", "role": "주요 피험사"},
            {"type": "company", "name": "금호고속", "role": "매각 대상 자회사"},
            {"type": "company", "name": "아시아나항공", "role": "금호산업 자회사"},
            {"type": "company", "name": "산업은행", "role": "채권단 주요 기관"},
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장, 유상증자 투자자"},
        ],
        "relations": [
            {"source": "박삼구", "target": "금호산업", "type": "ownership", "detail": "2,200억원 유상증자를 통해 14% 지분 확보, 사실상 지배주주 복귀"},
            {"source": "금호산업", "target": "금호고속", "type": "divestiture", "detail": "2012년 3,310억원에 매각"},
        ],
        "risks": [
            {"type": "financial", "description": "영업활동 현금흐름이 지속적으로 적자를 기록하며 운전자본 부담이 심각", "severity": "high"},
            {"type": "governance", "description": "채권단이 계획한 실권 시나리오가 정확히 집행되어 경영진 자율성 제약이 심각", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/37",
        "title": "색동 날개 꺾인 금호그룹(15): 금호고속 매각과 재인수, 차입금 돌려막기",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-06-21",
        "summary": "금호홀딩스가 칸서스KHB 사모펀드로부터 금호고속을 재인수한 거래는 표면상 매매이지만 실질적으로는 차입금을 돌려막기하는 구조다. 금호고속이 배당금으로 자신의 인수자금 일부를 미리 상환하면서 결국 금호고속 자신의 부채로 자신을 인수하는 형태가 되었다.",
        "entities": [
            {"type": "company", "name": "금호홀딩스", "role": "금호고속 재인수주체"},
            {"type": "company", "name": "금호고속", "role": "매매 대상 자회사"},
            {"type": "company", "name": "칸서스KHB 사모펀드", "role": "중간 소유자"},
            {"type": "company", "name": "제이앤케이제삼차", "role": "페이퍼컴퍼니"},
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
        ],
        "relations": [
            {"source": "금호홀딩스", "target": "제이앤케이제삼차", "type": "ownership", "detail": "완전지배 구조로 페이퍼컴퍼니 설립"},
            {"source": "제이앤케이제삼차", "target": "금호고속", "type": "acquisition", "detail": "3,676.5억원 대가로 재인수(전액 차입금)"},
        ],
        "risks": [
            {"type": "financial", "description": "금호고속이 자신의 배당금으로 인수자금 일부를 상환하면서 차입금이 3,676.5억원 증가하여 재무 부담 심화", "severity": "high"},
            {"type": "governance", "description": "차입의 탈을 쓴 매매거래로 실질적 경제 내용과 회계처리 간 괴리, 관련 당사자들 간 이해충돌 구조", "severity": "high"},
            {"type": "strategic", "description": "박삼구 회장이 실질적으로 추가 자금을 투입하지 않고 금호고속을 인수하면서 그룹 내 자금흐름의 순환 구조 형성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/36",
        "title": "색동 날개 꺾인 금호그룹(14)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-06-18",
        "summary": "금호산업이 2012년 금호고속을 코에프씨 사모펀드에 매각할 당시 금호리조트 지분을 600억원 수준의 장부가로 평가했으나, 1년 반 후 아시아나항공의 공정가액 평가에서 1200억원 이상으로 재평가되었다. 금호고속 인수 과정에서 현정은 회장의 현대투자파트너스와 웰투시인베스트먼트 등이 개입되면서 복잡한 구조의 거래가 진행되었다.",
        "entities": [
            {"type": "company", "name": "금호산업", "role": "자산 매각 주체"},
            {"type": "company", "name": "금호고속", "role": "매각 대상 회사"},
            {"type": "company", "name": "금호리조트", "role": "금호고속의 자회사"},
            {"type": "company", "name": "코에프씨 사모펀드", "role": "초기 인수자"},
            {"type": "company", "name": "아시아나항공", "role": "금호리조트 지분 인수자"},
            {"type": "company", "name": "현대투자파트너스", "role": "신주인수권부사채 인수자"},
            {"type": "person", "name": "현정은", "role": "현대그룹 회장"},
        ],
        "relations": [
            {"source": "금호산업", "target": "금호고속", "type": "divestiture", "detail": "2012년 8월 100% 지분을 코에프씨 사모펀드에 3110억원에 매각"},
            {"source": "아시아나항공", "target": "금호리조트", "type": "acquisition", "detail": "2014년 대한통운 지분 50%를 695억원에 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "금호리조트 지분이 600억원에서 1200억원 이상으로 평가 재상향되어 초기 매각가의 적절성 의문 발생", "severity": "high"},
            {"type": "governance", "description": "복잡한 거래 구조 속에 다양한 계열사와 외부 펀드가 얽혀있어 의사결정의 투명성과 독립성 우려", "severity": "high"},
            {"type": "governance", "description": "현정은 회장의 현대투자파트너스가 815억원 신주인수권부사채를 보유하고 있어 구조적 이해충돌 가능성", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/35",
        "title": "색동 날개 꺾인 금호그룹(13)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-06-14",
        "summary": "박삼구 회장의 금호그룹 재건 과정에서 코에프씨 PE 지분(대우건설 12.3%)을 1,581억원에 매각하고, 칸서스 PE에 700억원을 추가 출자하여 차입금을 상환했다. 이러한 거래는 겉으로는 매각이지만 실제로는 담보차입 구조였다.",
        "entities": [
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
            {"type": "person", "name": "박찬구", "role": "금호석유화학 회장"},
            {"type": "company", "name": "금호홀딩스", "role": "그룹 지주사"},
            {"type": "company", "name": "금호고속", "role": "칸서스 PE를 통해 차명 보유"},
            {"type": "company", "name": "대우건설", "role": "코에프씨 PE 주요 자산"},
            {"type": "company", "name": "웰투시인베스트먼트", "role": "케이엠티제일차 설립 운용사"},
            {"type": "person", "name": "정승원", "role": "웰투시인베스트먼트 설립자"},
        ],
        "relations": [
            {"source": "금호기업", "target": "금호산업", "type": "acquisition", "detail": "2015년 말 산업은행으로부터 지분 매입"},
            {"source": "금호기업", "target": "금호터미널", "type": "acquisition", "detail": "2016년 4월 아시아나항공으로부터 100% 지분 인수"},
            {"source": "금호홀딩스", "target": "코에프씨PE", "type": "divestiture", "detail": "2016년 8월 30% 지분을 1,581억원에 매각"},
        ],
        "risks": [
            {"type": "governance", "description": "박삼구 회장이 차명 회사와 장부상 회사를 통해 금호그룹 지배력을 간접 유지하여 소유권과 경영권 분리 및 투명성 부족", "severity": "high"},
            {"type": "governance", "description": "토털리턴스왑과 콜옵션 구조로 실질적 차입과 다름없으나 회계처리 상 매각으로 표현, 재무제표 왜곡 가능성", "severity": "critical"},
            {"type": "regulatory", "description": "박찬구 회장의 아시아나항공이 금호터미널 지분 매각에 대해 헐값 매각 주장하며 법원에 가처분 신청", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/34",
        "title": "색동 날개 꺾인 금호그룹(12)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-06-11",
        "summary": "금호그룹의 구조조정 과정에서 금호고속 거래와 금호터미널 활용이 핵심이었으며, 박삼구 회장은 핵심 계열사에 대한 영향력을 유지했다. 코에프씨사모펀드를 통한 자산 매각으로 대우건설 지분이 금호그룹의 몫으로 남게 되었다.",
        "entities": [
            {"type": "company", "name": "금호그룹", "role": "주요 계열사 그룹"},
            {"type": "company", "name": "금호산업", "role": "핵심 계열사"},
            {"type": "company", "name": "금호고속", "role": "그룹 지배구조의 정점"},
            {"type": "company", "name": "금호터미널", "role": "자산 회수 도구"},
            {"type": "company", "name": "대우건설", "role": "구조조정 대상 자산"},
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
        ],
        "relations": [
            {"source": "박삼구", "target": "금호그룹", "type": "control", "detail": "2015년 이후 그룹 재건 작업 주도"},
            {"source": "코에프씨사모펀드", "target": "대우건설", "type": "ownership", "detail": "금호산업의 5104만주(12.28%) 지분을 4155억원에 매입"},
        ],
        "risks": [
            {"type": "governance", "description": "박삼구 회장이 구조조정 과정 중에도 핵심 계열사에 대한 영향력을 유지하면서 그룹 재건의 실질이 채권단 지분 매입 이상을 넘지 못함", "severity": "high"},
            {"type": "financial", "description": "금호고속이 2200억원의 차입금을 떠안으면서 금호그룹의 대우건설 지분 처분 부담이 경감되었으나, 향후 금호고속의 재정 건전성 악화 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/33",
        "title": "색동 날개 꺾인 금호그룹(11)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-06-07",
        "summary": "금호산업이 코에프씨 사모펀드에 금호고속을 3110억원에 매각한 후, 금호터미널이 우선매수권을 행사하여 3940억원에 인수했다. 서울고속버스터미널은 공시지가 1조원대인 자산을 1999억원의 저가로 평가받아 매각되었으며, 신세계에 2200억원에 재매각되었다.",
        "entities": [
            {"type": "company", "name": "금호산업", "role": "자산 매각자"},
            {"type": "company", "name": "금호고속", "role": "매각 대상 자산"},
            {"type": "company", "name": "금호터미널", "role": "우선매수권 행사자"},
            {"type": "company", "name": "서울고속버스터미널", "role": "저가 평가된 자산"},
            {"type": "company", "name": "신세계", "role": "최종 인수자"},
        ],
        "relations": [
            {"source": "금호산업", "target": "코에프씨 사모펀드", "type": "divestiture", "detail": "금호고속, 서울고속버스터미널, 대우건설 지분 매각"},
            {"source": "코에프씨 사모펀드", "target": "신세계", "type": "divestiture", "detail": "서울고속버스터미널 지분 38.74% 판매"},
        ],
        "risks": [
            {"type": "governance", "description": "자산 평가 과정에서 회계법인의 평가 방법 선택이 의사결정권자의 의도를 반영했을 가능성", "severity": "high"},
            {"type": "financial", "description": "공시지가 1조1000억원대 자산이 2000억원 미만으로 평가되어 그룹의 실질 손실 발생", "severity": "critical"},
            {"type": "strategic", "description": "금호산업-아시아나항공-금호터미널-금호산업 순환출자 구조 형성 의혹 및 자산 파킹 논란", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/32",
        "title": "셀트리온, 다시 의심의 대상이 되다. (2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-05-21",
        "summary": "셀트리온의 반박에 대응하여 헬스케어의 영업현금흐름 부족 실태를 재분석했다. 8년간 약 9,700억원의 영업현금흐름 순유출을 기록했으며, 이는 전환사채와 유상증자로 충당되었다.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "바이오시밀러 항체의약품 제조사"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "의약품 판매사"},
            {"type": "company", "name": "셀트리온헬스케어헝가리", "role": "헝가리 법인"},
            {"type": "person", "name": "서정진", "role": "회장"},
            {"type": "company", "name": "화이자", "role": "전환사채 인수처"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "supply", "detail": "2010년부터 약 4조원 규모의 바이오시밀러 의약품 매입"},
            {"source": "셀트리온헬스케어", "target": "화이자", "type": "financing", "detail": "2083억원 규모 전환사채, 의약품 담보 설정"},
        ],
        "risks": [
            {"type": "financial", "description": "헬스케어의 8년 누적 영업현금흐름이 약 9,700억원 적자로, 본업에서 현금 창출 불가", "severity": "critical"},
            {"type": "governance", "description": "셀트리온과 헬스케어가 회계상 분리되어 있음에도 경영자가 두 회사를 혼동하고 있음", "severity": "high"},
            {"type": "operational", "description": "헬스케어가 판매 부진으로 의약품 재고를 헝가리 법인에 적체시키는 구조", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/31",
        "title": "셀트리온, 다시 의심의 대상이 되다. (1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-05-17",
        "summary": "셀트리온이 현대차를 제치고 시가총액 3위에 오른 것은 놀라운 성과이지만, 공매도 세력은 자회사인 셀트리온헬스케어의 과도한 재고 축적을 통해 실제 판매 능력에 의문을 제기했다. 셀트리온헬스케어가 2010년 인적분할을 통해 독립 회사화되면서 두 회사의 관계가 법적으로 단절되었다.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "바이오시밀러 생산 및 개발 기업"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "셀트리온 의약품 판매 담당 법인"},
            {"type": "company", "name": "셀트리온헬스케어헝가리", "role": "해외 판매 및 유통 담당 자회사"},
            {"type": "person", "name": "서정진", "role": "셀트리온 및 관련 회사 회장 겸 대주주"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "supply", "detail": "독점판매계약을 통해 의약품 원료 공급"},
            {"source": "셀트리온헬스케어", "target": "셀트리온헬스케어헝가리", "type": "ownership", "detail": "100% 자회사"},
        ],
        "risks": [
            {"type": "financial", "description": "셀트리온헬스케어의 과도한 재고 축적으로 인한 유동성 악화. 2012~2013년 창고 재고가 9,300억원을 초과", "severity": "high"},
            {"type": "governance", "description": "셀트리온과 셀트리온헬스케어 간 2010년 인적분할로 법적 독립화되었으나, 사업상 강한 종속성 유지로 인한 지배구조 불명확성", "severity": "high"},
            {"type": "operational", "description": "셀트리온헬스케어헝가리의 실질적 판매 부재. 2013년 감사보고서에 매출액이 기록되지 않았으나 1,227억원 자산 보유", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/30",
        "title": "색동 날개 꺾인 금호그룹(10)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-06-04",
        "summary": "금호고속은 2012년 금호산업에서 분할된 후 사모펀드와 금호터미널을 거치며 복잡한 소유권 변화를 경험했다. 박삼구 회장의 금호그룹 재건 과정에서 광주신세계와의 임차료 인상으로 확보한 자금이 금호고속 인수에 활용되었다.",
        "entities": [
            {"type": "company", "name": "금호고속", "role": "주요 피인수 대상 기업"},
            {"type": "company", "name": "금호산업", "role": "금호고속의 모기업"},
            {"type": "company", "name": "금호터미널", "role": "금호고속 인수자"},
            {"type": "company", "name": "칸서스자산운용", "role": "사모펀드 운용사"},
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
            {"type": "person", "name": "정용진", "role": "신세계 부회장"},
        ],
        "relations": [
            {"source": "금호산업", "target": "금호고속", "type": "spin-off", "detail": "2012년 물적분할로 금호산업에서 금호고속 분리"},
            {"source": "금호터미널", "target": "금호고속", "type": "acquisition", "detail": "2015년 3794억원에 금호고속 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "금호고속이 KoFC펀드로부터 2200억원 인수차입금을 부담하며 매년 100억원 이상의 이자비용 발생", "severity": "high"},
            {"type": "governance", "description": "금호터미널이 칸서스KHB사모펀드에 차입금 담보를 제공하고 자본금을 지원하는 구조로 순환출자 가능성", "severity": "critical"},
            {"type": "strategic", "description": "금호고속을 인수한 지 3개월 만에 사모펀드에 재판매하여 기업 소유권 불안정성 심화", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (39차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:40]}...")
        else:
            print(f"[FAIL] {article['title'][:40]}...")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
