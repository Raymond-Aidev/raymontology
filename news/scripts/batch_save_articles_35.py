#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 35차 (두산중공업 유동성 위기 시리즈 + e커머스 전쟁)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/129",
        "title": "두산중공업 유동성 위기(14) - 두산솔루스가 왜 첫 번째 매물로 나왔을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-05-22",
        "summary": "두산그룹이 두산중공업의 유동성 위기 해결을 위해 추진 중인 자산매각 전략에서 두산솔루스가 첫 번째 매물로 나온 이유를 분석. 오너 일가의 사재 출연을 위해 두산솔루스 매각으로 ㈜두산 재무구조 개선 후 두산중공업 유상증자에 참여하는 구조적 메커니즘.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "유동성 위기 상황 핵심 대상사"},
            {"type": "company", "name": "두산", "role": "두산중공업 모회사 (43.82% 지분)"},
            {"type": "company", "name": "두산솔루스", "role": "2차전지 핵심 부품 제조업체, 매각 대상"},
            {"type": "company", "name": "두산퓨얼셀", "role": "매각 가능 자산"},
            {"type": "person", "name": "박정원", "role": "오너 회장"},
        ],
        "relations": [
            {"source": "두산", "target": "두산중공업", "type": "ownership", "detail": "43.82% 지분 보유"},
            {"source": "두산", "target": "두산솔루스", "type": "divestiture", "detail": "61% 지분 매각 계획"},
        ],
        "risks": [
            {"type": "financial", "description": "매각 자산 가치 평가 불확실성, 예상 9000억원 미달 가능", "severity": "high"},
            {"type": "governance", "description": "오너 일가 보유 지분의 55%가 주식담보대출로 담보 설정", "severity": "high"},
            {"type": "operational", "description": "두산타워, 산업차량 등 주요 자산 매각 지연 시 구조조정 차질", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/128",
        "title": "두산중공업 유동성 위기(13)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-05-20",
        "summary": "두산중공업이 올해 만기 도래 차입금 4조2790억원 상환을 위해 산업은행과 수출입은행으로부터 1조8000억원의 크레디트라인 확보. 두산그룹의 자산매각과 유상증자를 통한 재무구조 개선은 단기간 내 완성 어려울 전망.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "신용위기 상황"},
            {"type": "company", "name": "두산그룹", "role": "모회사, 자구안 제출"},
            {"type": "company", "name": "산업은행", "role": "1조원 크레디트라인 제공"},
            {"type": "company", "name": "수출입은행", "role": "외화공모사채 상환자금 대출 및 8000억원 추가 지원"},
        ],
        "relations": [
            {"source": "산업은행", "target": "두산중공업", "type": "credit_support", "detail": "1조원 크레디트라인"},
            {"source": "수출입은행", "target": "두산중공업", "type": "credit_support", "detail": "8000억원 추가 지원"},
        ],
        "risks": [
            {"type": "operational", "description": "자산매각 진행 지연 가능성", "severity": "high"},
            {"type": "financial", "description": "외화차입금 만기연장 어려움", "severity": "high"},
            {"type": "financial", "description": "모회사 유동성 부족(약 1300억원)", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/127",
        "title": "두산중공업 유동성 위기(12) - 계열사 지분 팔면 얼마나 받을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-05-15",
        "summary": "두산중공업의 유동성 위기 극복을 위해 계열사 지분 매각이 논의 중. 두산건설과 두산메카텍 등의 매각으로 현금 확보 시도하나, 시장 상황 악화로 예상 수익 제한적 전망.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "유동성 위기 상황"},
            {"type": "company", "name": "두산밥캣", "role": "두산인프라코어 손자회사, 매각 후보"},
            {"type": "company", "name": "두산인프라코어", "role": "두산중공업 자회사"},
            {"type": "company", "name": "두산건설", "role": "두산중공업 완전자회사, 매각 후보"},
            {"type": "company", "name": "두산메카텍", "role": "두산중공업 자회사, 산업용 보일러 제조"},
        ],
        "relations": [
            {"source": "두산중공업", "target": "두산건설", "type": "ownership", "detail": "완전자회사"},
            {"source": "두산인프라코어", "target": "두산밥캣", "type": "ownership", "detail": "손자회사"},
        ],
        "risks": [
            {"type": "operational", "description": "두산건설 원매자 부재로 제값 매각 어려움", "severity": "high"},
            {"type": "financial", "description": "코로나19 영향으로 기업가치 평가액 급감", "severity": "high"},
            {"type": "financial", "description": "두산메카텍 매출채권 증가로 영업활동 현금흐름 감소", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/126",
        "title": "두산중공업 유동성 위기(11)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-05-13",
        "summary": "두산그룹이 두산중공업의 유동성 위기 극복을 위해 3조원을 마련하고 채권단으로부터 8,000억원 추가 지원 수령 예정. 두산밥캣 매각이 채권단의 주요 요구사항.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "발전산업 중심 기업, 유동성 위기"},
            {"type": "company", "name": "두산그룹", "role": "모회사, 지원 및 구조조정 주체"},
            {"type": "company", "name": "두산인프라코어", "role": "계열사, 글로벌 인프라 사업"},
            {"type": "company", "name": "두산밥캣", "role": "손자회사, 건설기계 사업"},
        ],
        "relations": [
            {"source": "두산그룹", "target": "두산중공업", "type": "ownership", "detail": "지원 주체"},
            {"source": "두산인프라코어", "target": "두산밥캣", "type": "ownership", "detail": "51% 지분"},
        ],
        "risks": [
            {"type": "financial", "description": "차입금 4조4000억원 누적", "severity": "critical"},
            {"type": "financial", "description": "유동성 부족", "severity": "high"},
            {"type": "market", "description": "발전산업 부진", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/125",
        "title": "두산중공업 유동성 위기(10)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-05-08",
        "summary": "두산중공업의 단기차입금 비중 급증으로 유동성 위기 직면. 신용등급 하락으로 회사채 발행 어려워지면서 금융기관 차입금 의존도 상승. 유상증자와 자산매각을 통한 재무구조 개선 필수.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "유동성 위기 상황"},
            {"type": "company", "name": "산업은행", "role": "1조원 크레디트라인 제공"},
            {"type": "company", "name": "수출입은행", "role": "외화공모사채 보증 및 대출"},
            {"type": "company", "name": "SC제일은행", "role": "신용등급 조건부 대출자"},
        ],
        "relations": [
            {"source": "산업은행", "target": "두산중공업", "type": "credit_line", "detail": "1조원 크레디트라인"},
        ],
        "risks": [
            {"type": "financial", "description": "신용등급 BBB 하락", "severity": "high"},
            {"type": "financial", "description": "만기도래 공모사채 4조원 규모", "severity": "high"},
            {"type": "regulatory", "description": "약정사항 위반 위험", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/124",
        "title": "두산중공업 유동성 위기(9) - 먹거리 투자, 긴급 지원 필요한 숨은 이유?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-05-06",
        "summary": "두산중공업의 유동성 위기는 원전·석탄화력 중심 사업구조 고착과 2013년부터의 현금흐름 악화가 복합 작용. 가스터빈, 태양광, 풍력 등 차세대 성장동력 개발 투자 자금 부족이 구조조정 지연의 원인.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "원전·석탄화력 사업 중심, 신재생에너지 전환 시도"},
            {"type": "company", "name": "두산건설", "role": "자회사, 8700억원 출자 수령"},
        ],
        "relations": [
            {"source": "두산중공업", "target": "두산건설", "type": "capital_injection", "detail": "2013년 8700억원 출자"},
        ],
        "risks": [
            {"type": "operational", "description": "2014-2019년 누적 1조2000억원 현금 유출", "severity": "critical"},
            {"type": "strategic", "description": "투자 미달행으로 성장동력 개발 지연", "severity": "high"},
            {"type": "market", "description": "글로벌 에너지 전환 추세 대응 지연", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/123",
        "title": "두산중공업 유동성 위기(8) - 밑 빠진 독일까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-05-01",
        "summary": "두산중공업의 유동성 위기는 사업 실패보다 운전자본 관리 부실과 계열사 지원으로 인한 과도한 차입이 주요 원인. 2005년 이후 조달한 차입금 4조4000억원의 80%가 계열사 지원에 사용.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "유동성 위기 상황"},
            {"type": "company", "name": "두산그룹", "role": "모회사"},
        ],
        "relations": [
            {"source": "두산중공업", "target": "두산그룹", "type": "subsidiary", "detail": "계열사 자금 지원 부담"},
        ],
        "risks": [
            {"type": "financial", "description": "2010년 이후 차입금 이자로 1조4744억원 지출", "severity": "critical"},
            {"type": "operational", "description": "운전자본 악화로 매출채권 증가, 매입채무 결제 부담", "severity": "high"},
            {"type": "market", "description": "원자력·화력발전 시장 축소", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/122",
        "title": "두산중공업 유동성 위기(7)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-04-28",
        "summary": "두산중공업의 매입채무가 전년 대비 5000억원 이상 급감. 신용등급 하락으로 인한 결제기간 단축과 외상 거래 제약이 원인. 과도한 계열사 지원과 대여금 손실로 약 5조원 규모의 차입금 누적.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "주요 분석 대상"},
            {"type": "company", "name": "두산인프라코어", "role": "종속기업"},
            {"type": "company", "name": "두산건설", "role": "종속기업"},
        ],
        "relations": [
            {"source": "두산중공업", "target": "두산인프라코어", "type": "ownership", "detail": "지분 소유 및 자금 지원"},
            {"source": "두산중공업", "target": "두산건설", "type": "ownership", "detail": "지분 소유 및 정기적 자금 지원"},
        ],
        "risks": [
            {"type": "financial", "description": "신용등급 BBB0 부정적 전망, 결제기간 단축", "severity": "high"},
            {"type": "financial", "description": "과도한 차입금 약 5조원", "severity": "high"},
            {"type": "financial", "description": "장기대여금 5556억원에 대손충당금 4433억원", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/121",
        "title": "두산중공업 유동성 위기(6)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-04-23",
        "summary": "두산중공업의 근본적 위기는 영업 위축. 금융위기 이후 신재생 에너지로의 산업 패러다임 전환에 대응 실패. 매출이 5조원 이하로 하락하면서 고정비 회수가 어려워져 창원공장 휴업 필요.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "주요 분석 대상"},
        ],
        "relations": [],
        "risks": [
            {"type": "operational", "description": "2014년부터 지속적인 매출 감소로 5조원 이하로 하락", "severity": "critical"},
            {"type": "operational", "description": "인건비 등 고정비 감축에도 불구하고 매출원가율 상승", "severity": "high"},
            {"type": "financial", "description": "운전자금 변동으로 영업활동 현금흐름 사실상 마이너스", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/120",
        "title": "두산중공업 유동성 위기(5) - 어두운 터널의 시작, 밥캣 인수",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-04-21",
        "summary": "두산중공업은 2008년 금융위기 이후 해외 수주 감소로 어려움 직면. 2007년 51억달러에 달하는 밥캣 인수는 자회사들의 대규모 손실 초래. 밥캣의 부진한 실적이 두산엔진, 두산인프라코어를 거쳐 모기업까지 영향.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "자회사 손실 영향 받는 모회사"},
            {"type": "company", "name": "밥캣", "role": "인수된 중장비 회사, 재무 문제 원인"},
            {"type": "company", "name": "두산엔진", "role": "자회사, KIKO 파생상품 손실"},
            {"type": "company", "name": "두산인프라코어", "role": "자회사, 인수 후 손실"},
            {"type": "company", "name": "두산건설", "role": "자금 지원 필요 자회사"},
        ],
        "relations": [
            {"source": "두산중공업", "target": "두산엔진", "type": "ownership", "detail": "51% 지분 보유"},
            {"source": "두산중공업", "target": "두산인프라코어", "type": "ownership", "detail": "약 38% 지분"},
        ],
        "risks": [
            {"type": "financial", "description": "2007년 밥캣 51억달러 인수로 약정 위반 발생", "severity": "critical"},
            {"type": "financial", "description": "KIKO 헤지상품으로 약 4.6조원 손실 (2008년)", "severity": "critical"},
            {"type": "market", "description": "2008년 금융위기 이후 해외 수주 감소", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/119",
        "title": "두산중공업 유동성 위기(4)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-04-16",
        "summary": "두산중공업 유동성 위기의 근본 원인은 탈원전 정책보다 2008년 금융위기 이후 해외 수주 감소. 국내 매출은 안정적이었으나 해외 매출이 위기 전 4조원에서 2019년 1.4조원으로 급감.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "분석 대상"},
            {"type": "company", "name": "두산건설", "role": "유동성 지원 필요 자회사"},
            {"type": "company", "name": "두산인프라코어", "role": "실적 부진 자회사"},
        ],
        "relations": [
            {"source": "두산중공업", "target": "두산건설", "type": "support", "detail": "메텍 및 HRSG 사업부 이전"},
        ],
        "risks": [
            {"type": "operational", "description": "해외 수주 급감", "severity": "critical"},
            {"type": "financial", "description": "대형 프로젝트 자금조달 제약", "severity": "high"},
            {"type": "financial", "description": "재무구조 악화로 신용도 저하", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/118",
        "title": "두산중공업 유동성 위기(3) - 탈원전 정책, 위기를 초래했나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-04-14",
        "summary": "한국의 탈원전 정책이 두산중공업 유동성 위기의 원인인지 분석. 정책으로 약 1조원의 잠재적 매출 기회를 잃었지만, 이것만으로는 심각한 재무 위기를 설명할 수 없음. 신용등급 하락에 따른 자금조달 제약이 주요 원인.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "유동성 위기 상황"},
            {"type": "company", "name": "산업통상자원부", "role": "탈원전 정책 시행 기관"},
        ],
        "relations": [
            {"source": "산업통상자원부", "target": "두산중공업", "type": "policy_impact", "detail": "탈원전 정책으로 부정적 영향"},
        ],
        "risks": [
            {"type": "regulatory", "description": "탈원전 정책으로 미래 계약 기회 상실", "severity": "medium"},
            {"type": "financial", "description": "신용등급 A-에서 BBB+로 하락, 차입비용 2.53%에서 5.12%로 상승", "severity": "high"},
            {"type": "financial", "description": "회사채 시장 대규모 자금조달 어려움", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/117",
        "title": "e커머스 전쟁, 최후의 승자는?(완결)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-04-10",
        "summary": "풀필먼트 서비스 중심의 e커머스 경쟁 분석. 아마존의 지배력은 풀필먼트 인프라와 FBA 서비스에서 비롯. 네이버가 방대한 고객 데이터와 IT 역량을 결합한 경쟁력 있는 풀필먼트 서비스로 잠재적 시장 리더로 부상 가능.",
        "entities": [
            {"type": "company", "name": "아마존", "role": "e커머스 선구자, 운송서비스 제공자"},
            {"type": "company", "name": "쿠팡", "role": "한국 e커머스 기업, 로켓배송 풀필먼트 구현"},
            {"type": "company", "name": "네이버", "role": "검색 플랫폼 및 마켓플레이스 운영자, 스마트스토어 플랫폼"},
            {"type": "company", "name": "이베이코리아", "role": "스마일배송 서비스, 메가 풀필먼트 센터 구축"},
            {"type": "company", "name": "CJ대한통운", "role": "선도 물류회사, 풀필먼트 역량"},
            {"type": "company", "name": "신세계그룹", "role": "로젠로지스틱스 인수로 풀필먼트 확장 추진"},
            {"type": "person", "name": "한성숙", "role": "네이버 CEO"},
        ],
        "relations": [
            {"source": "쿠팡", "target": "네이버", "type": "competition", "detail": "배송 속도 경쟁"},
        ],
        "risks": [
            {"type": "operational", "description": "풀필먼트 서비스 인프라 투자 요구", "severity": "high"},
            {"type": "operational", "description": "물류 네트워크 의존성 및 조정 복잡성", "severity": "high"},
            {"type": "market", "description": "기존 e커머스 플랫폼과의 치열한 경쟁", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/116",
        "title": "두산중공업 유동성 위기(2) - 전환상환우선주, 주식의 이름표를 달았던 차입금",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-04-09",
        "summary": "두산중공업이 2014년 발행한 전환상환우선주는 명목상 자본금이지만 실질적으로는 만기가 있는 채무 성격의 금융상품. 펀드를 통한 복잡한 자금조달 구조로 인해 상환을 미룰 수 없었으며, 2019년 말 약 4천억원 규모로 상환.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "우선주 발행사"},
            {"type": "company", "name": "KDB트리니티DHIC", "role": "우선주 주요 인수자"},
            {"type": "company", "name": "산업은행 PE실", "role": "펀드 공동 운영사"},
            {"type": "company", "name": "트리니티PE", "role": "펀드 공동 운영사 및 투자자 모집"},
            {"type": "person", "name": "윤유식", "role": "트리니티PE 대표"},
            {"type": "company", "name": "스마트그리드", "role": "자산유동화회사(SPC)"},
            {"type": "company", "name": "한화투자증권", "role": "ABSTB 인수 및 판매"},
            {"type": "company", "name": "우리은행", "role": "당시 주채권은행"},
        ],
        "relations": [
            {"source": "두산중공업", "target": "KDB트리니티DHIC", "type": "securities_issue", "detail": "전환상환우선주 3730억원 발행"},
            {"source": "스마트그리드", "target": "한화투자증권", "type": "securities_issue", "detail": "ABSTB 발행"},
        ],
        "risks": [
            {"type": "financial", "description": "만기 3개월인 ABSTB 21회 재발행으로 재융자 필요성", "severity": "high"},
            {"type": "financial", "description": "콜옵션 조건에도 5년 후 상환 실질적 필수", "severity": "high"},
            {"type": "financial", "description": "5년 후 스텝업 조건으로 최대 1.5% 추가 배당 의무", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/115",
        "title": "두산중공업 유동성 위기(1) - 전환상환우선주, 유동성 위기 방아쇠를 당기다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-04-07",
        "summary": "두산중공업이 산업은행과 수출입은행으로부터 1조원의 긴급 유동성 지원 수령. 2019년 1044억원 순손실과 7조4000억원 유동성차입금으로 위기 직면. 2019년 12월 전환상환우선주 3856억원 상환이 결정적 역할.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "위기 상황의 중심"},
            {"type": "company", "name": "산업은행", "role": "긴급 유동성 제공"},
            {"type": "company", "name": "수출입은행", "role": "긴급 유동성 제공"},
            {"type": "company", "name": "두산인프라코어", "role": "자회사, 영업이익 창출 중심"},
            {"type": "company", "name": "두산건설", "role": "100% 자회사, 유동성 문제 발생"},
            {"type": "company", "name": "두산", "role": "모기업, 담보 제공"},
            {"type": "company", "name": "KDB트리니티디에이치아이씨", "role": "우선주 보유기관"},
            {"type": "company", "name": "삼정회계법인", "role": "외부감사인"},
        ],
        "relations": [
            {"source": "산업은행", "target": "두산중공업", "type": "emergency_support", "detail": "1조원 긴급 유동성 지원"},
            {"source": "두산중공업", "target": "KDB트리니티디에이치아이씨", "type": "redemption", "detail": "우선주 3856억원 상환"},
        ],
        "risks": [
            {"type": "financial", "description": "유동부채가 유동자산보다 4조4000억원 초과, 유동성차입금 7조4000억원", "severity": "critical"},
            {"type": "financial", "description": "모기업 영업외비용 7400억원 초과, 2014년부터 손실 누적", "severity": "high"},
            {"type": "governance", "description": "감사보고서에서 계속기업 존속능력에 유의적인 의문 제기", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/114",
        "title": "e커머스 전쟁, 최후의 승자는?(23)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-04-02",
        "summary": "한국 e커머스 시장 경쟁 분석. 아마존과 같은 단일 지배자 출현 가능성 낮음. 무신사, 쿠팡, SSG닷컴 등 다양한 전문 플랫폼이 각 니치 시장에서 공존할 전망. 오프라인-온라인 통합이 장기 생존의 핵심.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "빠른 배송 모델 추구하는 주요 e커머스 플랫폼"},
            {"type": "company", "name": "무신사", "role": "수익성 높은 패션 마켓플레이스"},
            {"type": "company", "name": "SSG닷컴", "role": "신세계 운영 종합 쇼핑몰"},
            {"type": "company", "name": "티몬", "role": "사모펀드 후원 e커머스 플랫폼"},
            {"type": "company", "name": "위메프", "role": "혼합 투자자 기반 e커머스 플랫폼"},
            {"type": "company", "name": "KKR", "role": "티몬 사모펀드 투자자"},
            {"type": "person", "name": "김정주", "role": "넥슨그룹 회장, 위메프 투자자"},
            {"type": "company", "name": "롯데그룹", "role": "오프라인 유통 대기업"},
            {"type": "company", "name": "CJ그룹", "role": "e커머스 플랫폼 잠재적 인수자"},
        ],
        "relations": [
            {"source": "KKR", "target": "티몬", "type": "ownership", "detail": "사모펀드 소유"},
            {"source": "김정주", "target": "위메프", "type": "investment", "detail": "넥슨그룹 통한 투자"},
        ],
        "risks": [
            {"type": "market", "description": "시장 분절화로 단일 지배 불가", "severity": "high"},
            {"type": "financial", "description": "사모펀드 투자자들의 IPO 또는 매각 통한 엑싯 압박", "severity": "high"},
            {"type": "strategic", "description": "온라인 전용 모델 불충분, 60% 이상 쇼핑이 오프라인에서 이루어질 전망", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/113",
        "title": "e커머스 전쟁, 최후의 승자는?(22)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-31",
        "summary": "한국 e커머스 시장 경쟁 분석. 쿠팡의 코로나19 영향으로 2020년 2월 거래액 16조원 초과 지속 성장. SSG닷컴은 58% 성장세 보이며 옴니채널 전략으로 쿠팡 지배력에 도전 가능. 손정의의 재정 어려움이 쿠팡 자금 안정성에 우려.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "가장 빠른 배송 서비스의 e커머스 시장 리더"},
            {"type": "company", "name": "SSG닷컴", "role": "이마트 온라인 자회사, 가속 성장"},
            {"type": "company", "name": "이마트", "role": "20조원 매출의 주요 오프라인 유통업체"},
            {"type": "company", "name": "이베이코리아", "role": "쿠팡에 시장점유율 빼앗기는 경쟁사"},
            {"type": "person", "name": "손정의", "role": "소프트뱅크 창업자, 쿠팡 주요 투자자"},
            {"type": "company", "name": "소프트뱅크 비전펀드", "role": "쿠팡 주요 자금원"},
        ],
        "relations": [
            {"source": "쿠팡", "target": "소프트뱅크 비전펀드", "type": "funding", "detail": "투자 수령"},
            {"source": "SSG닷컴", "target": "이마트", "type": "subsidiary", "detail": "자회사"},
        ],
        "risks": [
            {"type": "financial", "description": "소프트뱅크 재정 악화 및 투자자 엑싯 가능성", "severity": "high"},
            {"type": "market", "description": "경쟁사들이 배송 속도 따라잡으면서 경쟁 우위 약화", "severity": "high"},
            {"type": "strategic", "description": "풀필먼트 서비스 수익성 확보 시점 불확실", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/112",
        "title": "e커머스 전쟁, 최후의 승자는?(21)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-27",
        "summary": "쿠팡과 SSG닷컴의 경쟁력 비교 분석. 두 업체의 수익구조와 물류전략이 근본적으로 다름. SSG닷컴은 영업현금흐름 창출능력과 이마트의 오프라인 네트워크라는 강점 보유, 쿠팡은 지속적인 외부자금 조달에 의존.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "온라인 전자상거래 기업"},
            {"type": "company", "name": "SSG닷컴", "role": "신세계그룹 온라인몰"},
            {"type": "company", "name": "신세계그룹", "role": "SSG닷컴 모회사"},
            {"type": "company", "name": "이마트", "role": "신세계그룹 오프라인 유통 브랜드"},
            {"type": "company", "name": "롯데쇼핑", "role": "온라인 전자상거래 시장 진입 예정"},
            {"type": "person", "name": "손정의", "role": "SVF 회장"},
        ],
        "relations": [
            {"source": "SSG닷컴", "target": "이마트", "type": "logistics", "detail": "158개 점포를 물류거점으로 활용"},
            {"source": "쿠팡", "target": "손정의", "type": "funding", "detail": "SVF로부터 외부자금 조달"},
        ],
        "risks": [
            {"type": "market", "description": "국내 온라인 침투율 30% 초과, 시장 확대 가능성 제한", "severity": "high"},
            {"type": "financial", "description": "쿠팡의 적자 구조로 지속적인 외부자금 조달 필수", "severity": "high"},
            {"type": "operational", "description": "SSG닷컴의 7340억원 3년 물류투자 계획이 쿠팡 누적 투자 상회", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/111",
        "title": "e커머스 전쟁, 최후의 승자는?(20)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-25",
        "summary": "쿠팡과 SSG닷컴(신세계그룹 온라인 플랫폼)의 e커머스 경쟁 분석. 온라인-오프라인 통합이 시장 지배에 필수. SSG닷컴이 쿠팡의 현재 시장 리더십에도 불구하고 구조적 비용 우위 보유.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "직접 판매 모델의 e커머스 시장 리더"},
            {"type": "company", "name": "신세계그룹", "role": "e커머스 진출 오프라인 유통 대기업"},
            {"type": "company", "name": "SSG닷컴", "role": "신세계그룹 온라인 플랫폼 자회사"},
            {"type": "company", "name": "이마트", "role": "신세계그룹 할인점 체인"},
            {"type": "company", "name": "롯데", "role": "오프라인 유통 보유 경쟁사"},
            {"type": "company", "name": "아마존", "role": "글로벌 e커머스 기준 모델"},
        ],
        "relations": [
            {"source": "쿠팡", "target": "SSG닷컴", "type": "competition", "detail": "SSG닷컴은 신세계그룹 전체 유통 생태계를 대표"},
        ],
        "risks": [
            {"type": "financial", "description": "지속적인 자본 유입 필요한 영업손실 누적", "severity": "high"},
            {"type": "operational", "description": "구조적 비용 불리함이 수익화 경로 제한", "severity": "high"},
            {"type": "operational", "description": "높은 직접 고용 의존도로 비용 관리 유연성 감소", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/110",
        "title": "e커머스 전쟁, 최후의 승자는?(19)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-23",
        "summary": "쿠팡의 경쟁 환경을 아마존과 비교 분석. 쿠팡은 한국의 이미 성숙한 온라인 시장 침투율(약 30%)과 다수의 강력한 경쟁자로 인해 상당한 도전에 직면. 미국의 미성숙 시장에서 성장한 아마존과 달리 쿠팡은 G마켓, 옥션, 네이버 등 기존 강자들과 경쟁해야 함.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "시장 포화에 직면한 한국 e커머스 플랫폼"},
            {"type": "company", "name": "아마존", "role": "미성숙 온라인 시장에서 성장한 미국 e커머스 리더"},
            {"type": "company", "name": "SSG닷컴", "role": "신세계-이마트 통합 플랫폼, 가속 성장"},
            {"type": "company", "name": "지마켓", "role": "기존 한국 오픈 마켓플레이스 경쟁자"},
            {"type": "company", "name": "네이버", "role": "강력한 플랫폼 영향력의 잠재적 경쟁자"},
            {"type": "company", "name": "카카오", "role": "카카오톡 메시징 지배력 활용 잠재적 경쟁자"},
        ],
        "relations": [
            {"source": "쿠팡", "target": "지마켓", "type": "competition", "detail": "직접 경쟁"},
            {"source": "SSG닷컴", "target": "신세계", "type": "subsidiary", "detail": "자회사, 가속 성장으로 쿠팡 확장 위협"},
        ],
        "risks": [
            {"type": "market", "description": "시장 포화 및 온라인 침투율 성장 둔화, 2019년 7월 이후 성장률 감소", "severity": "high"},
            {"type": "market", "description": "자본력 풍부한 다수 경쟁사와의 치열한 경쟁, SSG닷컴 분기 20-28% 성장", "severity": "high"},
            {"type": "financial", "description": "계획적 적자 정당화를 위한 지속 성장 의존, 성장 둔화 시 자금 부족 급격히 심화", "severity": "critical"},
            {"type": "strategic", "description": "한국 소비자의 약한 플랫폼 록인, 다양한 플랫폼 간 가격 비교 경향", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (35차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:40]}...")
        else:
            print(f"[FAIL] {article['title'][:40]}... - {result.get('error', 'Unknown error')}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
