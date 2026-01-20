#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 40차 (금호그룹1-9/웅진에너지1-4/롯데물류1-최종/대한방직/수빅조선)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/29",
        "title": "색동 날개 꺾인 금호그룹(9)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-05-31",
        "summary": "금호그룹 워크아웃 기간 재무구조조정 분석. 금호고속 매각 후 재취득 과정. 2012년 산업은행 주도 사모펀드에 3,310억원 매각 후 2015년 박삼구 회장의 그룹 재건 전략의 일환으로 재취득.",
        "entities": [
            {"type": "person", "name": "박삼구", "role": "그룹회장"},
            {"type": "company", "name": "금호산업", "role": "금호그룹 핵심 지주회사"},
            {"type": "company", "name": "금호고속", "role": "고속도로 운송 자회사"},
            {"type": "company", "name": "산업은행", "role": "주채권기관, 워크아웃 관리"},
            {"type": "company", "name": "금호터미널", "role": "터미널 운영 자회사"},
            {"type": "company", "name": "아시아나항공", "role": "금호터미널 모회사"},
        ],
        "relations": [
            {"source": "금호산업", "target": "금호고속", "type": "divestiture", "detail": "2012년 사모펀드에 3,310억원 매각"},
            {"source": "금호터미널", "target": "금호고속", "type": "acquisition", "detail": "2015년 4,150억원에 100% 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "LBO 구조로 금호고속에 2,000억원 부채 전가, 약 1,000억원 영업권 발생", "severity": "high"},
            {"type": "governance", "description": "금호터미널→금호고속→금호리조트 순환 지배구조로 자기거래 가능, 투명성 저하", "severity": "high"},
            {"type": "strategic", "description": "박 회장 지분 0.2%로 축소하면서 우선매수권 유지, 자본 투입 없이 지배권 유지", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/28",
        "title": "색동 날개 꺾인 금호그룹(8)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-05-28",
        "summary": "금호아시아나문화재단과 죽호학원이 박삼구 회장의 금호그룹 재건에 550억원 출자. 'K'로 시작하는 자회사들이 금호계열사와 수의계약으로 연간 1,500억원 매출. 공익법인 자산이 박삼구 회장 개인 이익에 동원됐다는 의혹.",
        "entities": [
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장, 금호재단 및 죽호학원 이사"},
            {"type": "company", "name": "금호아시아나문화재단", "role": "공익법인"},
            {"type": "company", "name": "죽호학원", "role": "공익법인"},
            {"type": "company", "name": "금호그룹", "role": "주요 기업집단"},
            {"type": "company", "name": "아시아나항공", "role": "금호그룹 계열사"},
            {"type": "company", "name": "금호산업", "role": "인수 대상 기업"},
        ],
        "relations": [
            {"source": "금호아시아나문화재단", "target": "금호기업", "type": "capital_injection", "detail": "보통주 200억원, 우선주 200억원 출자"},
            {"source": "죽호학원", "target": "금호기업", "type": "capital_injection", "detail": "우선주 150억원 출자"},
        ],
        "risks": [
            {"type": "governance", "description": "박삼구 회장이 금호재단/죽호학원 이사로서 자신 지배 기업에 공익법인 자산 출자, 이해충돌", "severity": "critical"},
            {"type": "regulatory", "description": "공익법인이 설립 취지와 무관하게 박삼구 회장 개인 이해를 위해 자산 동원 의혹, 검찰 고발", "severity": "critical"},
            {"type": "governance", "description": "공익법인 자회사들이 금호계열사와 경쟁 없는 수의계약으로 연간 1,500억원 매출", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/27",
        "title": "색동 날개 꺾인 금호그룹(7)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-05-14",
        "summary": "금호그룹 2009년 워크아웃 구조조정과 박삼구 회장의 자산 이전 전략 분석. 아시아나항공 지분이 금호석유화학에 매각 후 금호산업으로 반환. 박삼구 회장이 금호타이어 대신 금호산업 주식에 투자.",
        "entities": [
            {"type": "person", "name": "박삼구", "role": "회장/대주주"},
            {"type": "person", "name": "박찬구", "role": "금호석유화학 회장"},
            {"type": "company", "name": "금호그룹", "role": "모그룹"},
            {"type": "company", "name": "금호산업", "role": "지주회사"},
            {"type": "company", "name": "아시아나항공", "role": "항공 자회사"},
            {"type": "company", "name": "금호타이어", "role": "타이어 자회사"},
            {"type": "company", "name": "금호석유화학", "role": "화학 자회사"},
            {"type": "company", "name": "산업은행", "role": "주채권은행"},
        ],
        "relations": [
            {"source": "금호산업", "target": "아시아나항공", "type": "ownership", "detail": "2009년 12월 12.7% 지분 947억원에 금호석유화학 매각 후 재매입"},
            {"source": "박삼구", "target": "금호산업", "type": "investment", "detail": "2년 구조조정 후 2,200억원 투자"},
        ],
        "risks": [
            {"type": "governance", "description": "박삼구 회장 자산 투자 배분 합의 불이행, 금호타이어에서 금호산업으로 자금 전환", "severity": "high"},
            {"type": "regulatory", "description": "워크아웃 직전 경영권 프리미엄 없이 아시아나항공 지분 매각, 불공정 거래 의혹", "severity": "high"},
            {"type": "financial", "description": "계열사 간 아시아나항공 주식 이전 시 공정가치 평가 없음", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/26",
        "title": "색동 날개 꺾인 금호그룹(6)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-05-10",
        "summary": "금호그룹 2009년 워크아웃 후 산업은행이 박삼구 회장에게 부여한 우선매수청구권 분석. 산업은행은 내부 준칙을 위반하며 박 회장을 우선협상자로 지정, 2014년 금호산업과 2015년 아시아나항공 인수에 결정적 영향.",
        "entities": [
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
            {"type": "company", "name": "산업은행", "role": "주채권기관, 워크아웃 관리자"},
            {"type": "company", "name": "금호산업", "role": "주요 계열사"},
            {"type": "company", "name": "아시아나항공", "role": "주요 계열사"},
            {"type": "company", "name": "금호타이어", "role": "워크아웃 계열사"},
            {"type": "person", "name": "이정환", "role": "전 산업은행 총재, 박삼구 장인"},
        ],
        "relations": [
            {"source": "산업은행", "target": "박삼구", "type": "preferential_treatment", "detail": "2010년 2월 밀실 합의서로 우선매수청구권 부여"},
            {"source": "박삼구", "target": "금호산업", "type": "acquisition", "detail": "2012년 유상증자로 최대주주 복귀, 2014년 워크아웃 졸업 후 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "산업은행 출자전환 주식 관리 및 매각준칙 위반, 부실책임 경영진에 우선매수권 부여", "severity": "critical"},
            {"type": "regulatory", "description": "밀실 합의서 작성, 타 채권단에 비밀 유지로 투명성/공정성 위반", "severity": "critical"},
            {"type": "strategic", "description": "2012년 유상증자가 2014-2015년 인수의 교두보, 사전 계획된 구도 의심", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/25",
        "title": "색동 날개 꺾인 금호그룹(5)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-05-07",
        "summary": "아시아나항공 영업실적은 양호했으나 2015년 박삼구 회장 금호그룹 재건 과정에서 금호터미널 매각과 차입금 증가로 부채비율 1,000% 초과, 유동성 위기. 산업은행이 구주 가격 높여 금호산업 지분 비싸게 매각 시도, 아시아나 구조개선보다 박삼구 이익 우선 의혹.",
        "entities": [
            {"type": "company", "name": "아시아나항공", "role": "유동성 위기 항공사"},
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장, 아시아나 대주주"},
            {"type": "company", "name": "금호그룹", "role": "모그룹"},
            {"type": "company", "name": "산업은행", "role": "채권자, 구조조정 촉진자"},
            {"type": "company", "name": "금호산업", "role": "아시아나항공 30% 보유 지주회사"},
            {"type": "company", "name": "금호터미널", "role": "아시아나항공 전 자회사"},
        ],
        "relations": [
            {"source": "박삼구", "target": "아시아나항공", "type": "ownership", "detail": "금호산업 30% 지분 통한 지배"},
            {"source": "아시아나항공", "target": "금호터미널", "type": "asset_sale", "detail": "2015년 금호기업에 약 2,700억원 저평가 매각"},
        ],
        "risks": [
            {"type": "financial", "description": "2015년 부채비율 1,000% 도달, 2018년말 누적손실 약 3,000억원, 단기부채 만기 연장 부담", "severity": "critical"},
            {"type": "governance", "description": "대주주의 자산 이전/특관거래로 경영 실패, 산업은행의 실패한 경영진 복귀 결정", "severity": "critical"},
            {"type": "market", "description": "신용등급 BBB- 미만으로 일반채권 발행 불가, 주가 액면가 미만으로 유상증자 불가", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/24",
        "title": "색동 날개 꺾인 금호그룹(4)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-05-04",
        "summary": "산업은행과 아시아나항공 재무구조개선 약정은 기업 구조조정이 아닌 채권 회수 목적. 자산 매각과 자본 확충 강제로 유동성 위기 심화, 신용등급 하락 시 추가 위험 대기.",
        "entities": [
            {"type": "company", "name": "산업은행", "role": "주채권은행, 구조조정 주도"},
            {"type": "company", "name": "아시아나항공", "role": "대출 대상 기업"},
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장, 아시아나 이사"},
            {"type": "person", "name": "박세창", "role": "박삼구 회장 아들, 금호기업 공동설립자"},
            {"type": "company", "name": "금호산업", "role": "아시아나항공 모기업"},
            {"type": "company", "name": "금호터미널", "role": "매각 대상 자산"},
        ],
        "relations": [
            {"source": "산업은행", "target": "아시아나항공", "type": "financial_control", "detail": "재무구조개선 약정으로 자산매각/자본확충 강제"},
            {"source": "박삼구", "target": "금호터미널", "type": "acquisition", "detail": "금호기업 통한 저가 매입 의혹 (1조원→2,700억원)"},
        ],
        "risks": [
            {"type": "financial", "description": "단기성 차입금 비중 38%, 유동화사채 의존도 심화로 자금조달 경로 제한", "severity": "critical"},
            {"type": "governance", "description": "산업은행 이해상충: 채권회수와 구조조정 목표 충돌, 박삼구 회장과 우대거래 의혹", "severity": "high"},
            {"type": "regulatory", "description": "신용등급 하락 시 기한이익상실 발동으로 유동화사채/금융리스부채 전액 상환 압박", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/23",
        "title": "색동 날개 꺾인 금호그룹(3)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-04-30",
        "summary": "금호그룹 아시아나항공 매각 공식화로 주가 급등, 전환사채 투자자들 예상 외 수익 기회. 큐캐피탈 등 1,000억원 규모 전환사채, 상황 반전으로 60% 이상 수익 실현 가능.",
        "entities": [
            {"type": "company", "name": "금호그룹", "role": "매각 대상 그룹"},
            {"type": "company", "name": "아시아나항공", "role": "매각 대상 계열사, CB 발행사"},
            {"type": "company", "name": "큐캐피탈", "role": "400억원 CB 투자자"},
            {"type": "company", "name": "케이프투자증권", "role": "550억원 CB 인수, 고유계정 보유"},
            {"type": "company", "name": "삼일회계법인", "role": "감사기관"},
            {"type": "company", "name": "산업은행", "role": "주요 채권자"},
        ],
        "relations": [
            {"source": "큐캐피탈", "target": "아시아나항공", "type": "investor", "detail": "400억원 CB 인수, 주식전환 결정"},
            {"source": "삼일회계법인", "target": "아시아나항공", "type": "auditor", "detail": "한정의견→적정의견 변경으로 EOD 회피"},
        ],
        "risks": [
            {"type": "financial", "description": "아시아나항공 유동성 악화 및 광범위한 담보 설정으로 채권 회수 불확실", "severity": "critical"},
            {"type": "governance", "description": "감사의견 변경(한정→적정)에 따른 기한이익상실 조건 해제의 투명성 문제", "severity": "high"},
            {"type": "market", "description": "M&A 이슈에 따른 주가 급등 후 폭락 가능성, 개인투자자 손실 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/22",
        "title": "색동 날개 꺾인 금호그룹(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-04-26",
        "summary": "삼일회계법인의 아시아나항공 2018년 재무제표 감사 분석. 정비충당부채 적정 인식 여부, 마일리지 이연수익 계산 적정성 의문. 2017년과 2018년 감사 간 불일치로 회계법인 소홀 의혹.",
        "entities": [
            {"type": "company", "name": "아시아나항공", "role": "감사 비판 대상"},
            {"type": "company", "name": "삼일회계법인", "role": "외부감사인"},
            {"type": "company", "name": "금호그룹", "role": "모회사"},
        ],
        "relations": [
            {"source": "삼일회계법인", "target": "아시아나항공", "type": "auditor", "detail": "2017년부터 외부감사, 2018년 한정의견 후 수정"},
        ],
        "risks": [
            {"type": "governance", "description": "2017년 정비충당부채 부적절 승인 후 2018년 대폭 조정(4,240억원), 일관성 없는 감사 기준", "severity": "high"},
            {"type": "financial", "description": "마일리지 이연수익 3,900억원 과소계상, 계산 방법론 의문", "severity": "high"},
            {"type": "market", "description": "2018년 감사인 적정의견 기반으로 2,000억원 무담보채권, 1조원 CB, 6.6조원 ABS 발행", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/21",
        "title": "색동 날개 꺾인 금호그룹(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-04-24",
        "summary": "금호그룹 아시아나항공이 삼일회계법인 한정의견 후 매각 결정. 핵심은 반납정비충당부채 미인식 문제, 운용리스 항공기 정비충당부채 과소계상.",
        "entities": [
            {"type": "company", "name": "금호그룹", "role": "아시아나항공 모기업"},
            {"type": "company", "name": "아시아나항공", "role": "금호그룹 산하 항공사"},
            {"type": "company", "name": "삼일회계법인", "role": "외부감사인"},
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
            {"type": "company", "name": "대한항공", "role": "비교대상 항공사"},
        ],
        "relations": [
            {"source": "금호그룹", "target": "아시아나항공", "type": "ownership", "detail": "유동성 위기로 매각 결정"},
            {"source": "삼일회계법인", "target": "아시아나항공", "type": "audit", "detail": "한정의견 후 적정의견 변경, 반납정비충당부채 424억원 과소계상 지적"},
        ],
        "risks": [
            {"type": "financial", "description": "부채비율 505%→649% 악화, 유동성 위기 진행", "severity": "critical"},
            {"type": "governance", "description": "금호그룹 형제 분쟁과 자금난으로 그룹 해체 상황", "severity": "critical"},
            {"type": "regulatory", "description": "한정의견으로 금융당국/채권은행 신뢰 상실, 자금 줄 차단", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/20",
        "title": "웅진에너지 '의견거절'의 막전막후(4)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-04-19",
        "summary": "웅진에너지 90% 무상감자 결정이 자본잠식 50% 미만 유지와 감사의견 회피 전략. 채권자에 반강제적 출자전환 요구, 웅진에너지 결손 구조로 코웨이 매입자금 상환 불가.",
        "entities": [
            {"type": "company", "name": "웅진에너지", "role": "자본잠식 기업"},
            {"type": "person", "name": "윤석금", "role": "웅진그룹 회장"},
            {"type": "company", "name": "웅진그룹", "role": "모지주회사"},
            {"type": "company", "name": "한영회계법인", "role": "외부감사인"},
            {"type": "company", "name": "코웨이", "role": "웅진그룹 재취득 자회사"},
            {"type": "company", "name": "한화케미칼", "role": "전략적 투자자/주주"},
        ],
        "relations": [
            {"source": "웅진에너지", "target": "웅진그룹", "type": "subsidiary", "detail": "모지주회사 지배 하 자회사"},
            {"source": "웅진그룹", "target": "코웨이", "type": "acquisition", "detail": "이전 매각 후 재취득, 상당한 자금조달 필요"},
        ],
        "risks": [
            {"type": "governance", "description": "무상감자 결정이 소수주주 동의 없이 진행, 보통결의 정족수(27%)만 필요", "severity": "critical"},
            {"type": "financial", "description": "자본잠식률 50% 초과 시 관리종목 지정 및 상장폐지 위험", "severity": "critical"},
            {"type": "regulatory", "description": "감사의견 거절로 상장폐지 위험 (1년 유예 규정 적용)", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/19",
        "title": "웅진에너지 '의견거절'의 막전막후(3)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-04-16",
        "summary": "웅진에너지 태양광 시장 호황에도 영업 축소. 생산능력 2,000MW로 증설에도 가동률 55%로 감소, 주요 고객과 계약 해지. 수요 문제 시사.",
        "entities": [
            {"type": "company", "name": "웅진에너지", "role": "대상 기업"},
            {"type": "company", "name": "썬파워", "role": "전 합작투자 파트너"},
            {"type": "person", "name": "윤석금", "role": "웅진그룹 회장"},
            {"type": "company", "name": "한영회계법인", "role": "외부감사인"},
            {"type": "company", "name": "신성이엔지", "role": "고객"},
            {"type": "company", "name": "한화큐셀", "role": "고객"},
        ],
        "relations": [
            {"source": "웅진에너지", "target": "썬파워", "type": "jv_dissolved", "detail": "2011년 락업 종료 후 40%+ 지분 매각"},
            {"source": "웅진에너지", "target": "신성이엔지", "type": "customer_contract", "detail": "2018년 장기공급계약 종료, 2017년 1,200억원→2018년 600억원"},
        ],
        "risks": [
            {"type": "operational", "description": "생산능력 33% 증가해 2,000MW지만 가동률 25%로 급락, 시장 수요에도 감산", "severity": "critical"},
            {"type": "financial", "description": "국내 고객 웨이퍼 매출 전년대비 절반 감소 (1,200억원→600억원), 시장점유율 5%→4.4% 하락", "severity": "critical"},
            {"type": "governance", "description": "장기공급계약에 물량 보장 없음, 고객이 중도 해지 가능", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/18",
        "title": "웅진에너지 '의견거절'의 막전막후(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-04-12",
        "summary": "웅진에너지 2011년 주요 파트너 썬파워 결별 이후 지속적 적자로 좀비 기업 상태. 외부 차입 어려워 주주 증자 의존, 매출채권 손상 급증과 심각한 유동성 부족.",
        "entities": [
            {"type": "company", "name": "웅진에너지", "role": "대상 기업"},
            {"type": "company", "name": "썬파워", "role": "전 파트너/주요 고객"},
            {"type": "company", "name": "웅진그룹", "role": "모회사"},
            {"type": "person", "name": "윤석금", "role": "웅진그룹 회장"},
            {"type": "company", "name": "한영회계법인", "role": "외부감사인"},
        ],
        "relations": [
            {"source": "썬파워", "target": "웅진에너지", "type": "partnership_termination", "detail": "2011년 지분 100% 처분 및 계약 종료로 매출 60% 손실"},
            {"source": "웅진그룹", "target": "웅진에너지", "type": "ownership", "detail": "대주주로서 2014년, 2016년 증자 참여"},
        ],
        "risks": [
            {"type": "financial", "description": "2011년 이후 영업이익 창출 실패, 매년 현금유출", "severity": "critical"},
            {"type": "financial", "description": "유동자산 대부분이 회수 불가능한 매출채권/재고, 유동부채 > 유동자산 지속", "severity": "critical"},
            {"type": "operational", "description": "매출채권 손상처리 2015년 28억원→2017년 270억원 급증", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/17",
        "title": "웅진에너지 '의견거절'의 막전막후(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-04-10",
        "summary": "웅진에너지 한영회계법인 의견거절로 상장폐지 위기. 감사 후 당기순손실 400억원 이상 증가, 자본잠식 70% 이상 확대, 유형자산 420억원 손상차손.",
        "entities": [
            {"type": "company", "name": "웅진에너지", "role": "피감사기업"},
            {"type": "company", "name": "한영회계법인", "role": "외부감사인"},
            {"type": "company", "name": "웅진그룹", "role": "모회사"},
        ],
        "relations": [
            {"source": "한영회계법인", "target": "웅진에너지", "type": "audit", "detail": "의견거절 감사의견 제시"},
            {"source": "웅진그룹", "target": "웅진에너지", "type": "ownership", "detail": "계열사 재구조화 계획에서 매각 예정"},
        ],
        "risks": [
            {"type": "financial", "description": "자본잠식 70% 이상으로 상장폐지 기준 초과", "severity": "critical"},
            {"type": "regulatory", "description": "외부감사인 의견거절로 상장폐지 위기", "severity": "critical"},
            {"type": "operational", "description": "유형자산 420억원 손상차손으로 자산가치 20% 감소", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/16",
        "title": "롯데그룹 물류법인 합병, 무엇을 노린 포석인가(최종)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-04-05",
        "summary": "신동빈 회장 롯데지주 설립과 물류법인 합병 전략 분석. 글로벌로지스 유상증자와 로지스틱스 분할로 합병비율 조정, 롯데지주가 통합 물류회사 최대주주가 되도록 설계.",
        "entities": [
            {"type": "person", "name": "신동빈", "role": "롯데지주 회장, 롯데그룹 지배인물"},
            {"type": "company", "name": "롯데지주", "role": "한국 롯데그룹 중간지주회사"},
            {"type": "company", "name": "글로벌로지스", "role": "1,500억원 유상증자 실시"},
            {"type": "company", "name": "롯데로지스틱스", "role": "투자부문 분할 후 합병 대상"},
            {"type": "company", "name": "호텔롯데", "role": "한국 롯데그룹 중간 지주회사"},
            {"type": "company", "name": "엘엘에이치", "role": "글로벌로지스 재무적 투자자"},
        ],
        "relations": [
            {"source": "신동빈", "target": "롯데지주", "type": "ownership", "detail": "단일 최대주주 11.71% 보유, 우호지분 포함 20% 이상"},
            {"source": "롯데지주", "target": "글로벌로지스", "type": "ownership", "detail": "합병 후 약 22% 지분, 최대주주"},
            {"source": "글로벌로지스", "target": "롯데로지스틱스", "type": "merger", "detail": "2018년 3월 합병비율 1:16"},
        ],
        "risks": [
            {"type": "governance", "description": "유상증자/분할합병 타이밍으로 합병비율 조정, 실제 비율 1:44 가능성 분석", "severity": "high"},
            {"type": "financial", "description": "글로벌로지스/로지스틱스 순자산 1년 미만에 완전 역전, 약 3,500억원 평가 차이", "severity": "high"},
            {"type": "strategic", "description": "신동빈 회장이 일본 롯데홀딩스 중심에서 본인 중심으로 새로운 지배구조 구축", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/15",
        "title": "롯데그룹 물류법인 합병, 무엇을 노린 포석인가(4)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-04-02",
        "summary": "롯데글로벌로지스와 롯데로지스틱스 합병은 장기 계획. 글로벌로지스 2017년 유상증자 후 투자 미실행, 현금 적치 상태. 합병 후 투자 순서가 자연스러우나 투자 먼저 후 합병 구조.",
        "entities": [
            {"type": "company", "name": "롯데그룹", "role": "물류 통합 주도자"},
            {"type": "company", "name": "롯데글로벌로지스", "role": "인수 대상(합병 생존자)"},
            {"type": "company", "name": "롯데로지스틱스", "role": "인수 대상(합병 소멸자)"},
            {"type": "company", "name": "엘엘에이치", "role": "글로벌로지스 최대주주"},
            {"type": "company", "name": "메디치인베스트먼트", "role": "엘엘에이치 조성 VC"},
        ],
        "relations": [
            {"source": "롯데그룹", "target": "롯데글로벌로지스", "type": "ownership", "detail": "2016년 거의 모든 지분 확보"},
            {"source": "롯데글로벌로지스", "target": "롯데로지스틱스", "type": "merger", "detail": "2019년 초 합병 완료"},
            {"source": "엘엘에이치", "target": "롯데글로벌로지스", "type": "ownership", "detail": "2017년 2분기 유상증자로 최대주주"},
        ],
        "risks": [
            {"type": "financial", "description": "2017년 유상증자 1,500억원이 2년 이상 미투자 적치, 자금 효율성 의문", "severity": "high"},
            {"type": "governance", "description": "엘엘에이치 풋옵션 연 3% 수익률이 시장 관례보다 낮아 특수거래 의심", "severity": "high"},
            {"type": "strategic", "description": "투자 먼저 후 합병 구조가 시너지 극대화 위한 합병 후 투자 순서와 불일치", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/14",
        "title": "롯데그룹 물류법인 합병, 무엇을 노린 포석인가(3)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-03-29",
        "summary": "롯데그룹 물류법인 합병 기업가치 평가 분석. 평가방법 선택이 로지스틱스에 유리한 결과. 상속세법 기준 vs 2018년 DCF 평가의 상대가치 차이.",
        "entities": [
            {"type": "company", "name": "롯데그룹", "role": "지배주체"},
            {"type": "company", "name": "로지스틱스", "role": "피합병사"},
            {"type": "company", "name": "글로벌로지스", "role": "존속사"},
            {"type": "company", "name": "삼일회계법인", "role": "기업가치평가기관"},
            {"type": "company", "name": "한영회계법인", "role": "2018년 평가기관"},
        ],
        "relations": [
            {"source": "롯데그룹", "target": "삼일회계법인", "type": "engagement", "detail": "기업가치평가 의뢰"},
            {"source": "로지스틱스", "target": "글로벌로지스", "type": "merger", "detail": "상속세법 평가 기준 1:16 합병비율"},
        ],
        "risks": [
            {"type": "governance", "description": "기업가치평가 방법 선택이 의뢰인 입장 반영 의심, 회계법인 독립성 부족", "severity": "high"},
            {"type": "financial", "description": "상속세법 기준 합병비율이 DCF 기준 1.89배에서 2.25배로 확대, 로지스틱스 주주 유리", "severity": "high"},
            {"type": "strategic", "description": "글로벌로지스 2018년 흑자전환 예상이 실제 적자 지속, 과거 평가 신뢰성 문제", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/13",
        "title": "롯데그룹 물류법인 합병, 무엇을 노린 포석인가(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-03-27",
        "summary": "롯데글로벌로지스와 롯데로지스틱스 합병비율(1:16.35) 논쟁. 불충분한 공시가 논란 확대, 특히 로지스틱스가 포기한 코리아세븐 벤더사업 가치의 주식평가 반영 여부 불명확.",
        "entities": [
            {"type": "company", "name": "롯데글로벌로지스", "role": "합병 대상사"},
            {"type": "company", "name": "롯데로지스틱스", "role": "합병 대상사"},
            {"type": "company", "name": "롯데그룹", "role": "지주사"},
            {"type": "company", "name": "코리아세븐", "role": "로지스틱스 주요 거래처"},
            {"type": "company", "name": "삼일회계법인", "role": "기업가치 평가"},
        ],
        "relations": [
            {"source": "롯데로지스틱스", "target": "코리아세븐", "type": "business", "detail": "벤더사업 제공 (2019년부터 중단)"},
            {"source": "롯데글로벌로지스", "target": "롯데로지스틱스", "type": "merger", "detail": "합병비율 1:16.35 (주당 가치: 글로벌 14,545원 vs 로지스틱스 237,764원)"},
        ],
        "risks": [
            {"type": "governance", "description": "합병비율 산정 근거 불완전 공시로 이해관계자 신뢰 저하", "severity": "high"},
            {"type": "operational", "description": "로지스틱스 주요 수익원 코리아세븐 벤더사업 중단으로 매출 대폭 감소 (3조원→1조원)", "severity": "critical"},
            {"type": "financial", "description": "벤더사업 제외 여부가 기업가치 평가 미반영 가능성, 합병비율 적절성 의문", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/12",
        "title": "롯데그룹 물류법인 합병, 무엇을 노린 포석인가(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2018-11-29",
        "summary": "롯데글로벌로지스와 롯데로지스틱스 합병으로 통합 물류법인 매출 예상 외 감소 전망. 로지스틱스가 코리아세븐 구매대행 서비스(매출 70%) 중단으로 적자 가능성.",
        "entities": [
            {"type": "company", "name": "롯데글로벌로지스", "role": "합병당사자 (종속회사)"},
            {"type": "company", "name": "롯데로지스틱스", "role": "합병당사자 (피합병회사)"},
            {"type": "company", "name": "코리아세븐", "role": "롯데로지스틱스 주요 고객"},
            {"type": "company", "name": "롯데그룹", "role": "지주회사"},
            {"type": "person", "name": "신동빈", "role": "롯데그룹 리더십"},
        ],
        "relations": [
            {"source": "롯데글로벌로지스", "target": "롯데로지스틱스", "type": "merger", "detail": "2019년 3월 1일 합병, 신주 발행으로 약 1,554억원 합병대가"},
            {"source": "롯데로지스틱스", "target": "코리아세븐", "type": "service", "detail": "구매대행 서비스 제공, 2018년 3분기 매출액 71% (1조 2,478억원)"},
        ],
        "risks": [
            {"type": "operational", "description": "로지스틱스 구매대행 사업 중단으로 매출 70% 감소 예상, 매출총이익 1,350억원→600억원대 급감", "severity": "critical"},
            {"type": "financial", "description": "합병 후 통합법인 영업이익 연간 200억원 이하 하락, 당기순이익 적자 전환 가능성", "severity": "high"},
            {"type": "governance", "description": "로지스틱스 코리아세븐 구매대행이 일감 몰아주기 논란 대상이었으나 오너 일가 지분 없어 제재 회피", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/11",
        "title": "대한방직의 전주공장 매각, 누가 웃고 있을까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2018-10-20",
        "summary": "대한방직 전주공장 부지 약 1,980억원 매각. 시세보다 저평가 의혹. 개발사 자광과 시공사 롯데건설 관계, 회장 과거 비위로 거래 투명성 의심.",
        "entities": [
            {"type": "company", "name": "대한방직", "role": "토지 매도자"},
            {"type": "company", "name": "자광", "role": "토지 매수자, 시행사"},
            {"type": "company", "name": "롯데건설", "role": "시공사, 지급확약자"},
            {"type": "person", "name": "설범", "role": "대한방직 대주주 겸 회장"},
            {"type": "person", "name": "전은수", "role": "자광 및 자광건설 대표이사"},
        ],
        "relations": [
            {"source": "자광", "target": "롯데건설", "type": "contract", "detail": "143층 초고층타워 개발 시공사, 지급확약서 제공"},
            {"source": "설범", "target": "대한방직", "type": "control", "detail": "대주주로서 차명 지분 4.88% 보유, 감사선임권 행사 의혹"},
        ],
        "risks": [
            {"type": "governance", "description": "대주주 설범 회장 차명 지분 보유로 감사선임권 불법 행사 의혹", "severity": "high"},
            {"type": "financial", "description": "매매가격이 현지 부동산업자 평가 3,000억원 대비 약 34% 저평가", "severity": "high"},
            {"type": "operational", "description": "용도변경/도시기본계획 변경 2025년까지 불가한데 143층 초고층 개발 추진", "severity": "high"},
            {"type": "governance", "description": "설범 회장 2005년 월배공장 매각 시 리베이트 수수 및 횡령 혐의", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/10",
        "title": "수빅조선소는 회복가능한가",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2018-10-15",
        "summary": "한진중공업 필리핀 자회사 수빅조선소 재무상황 분석. 낮은 수주잔고와 지속 적자로 매각 또는 유상증자 선택 앞둠. 미청구공사와 저가 수주로 인한 구조적 문제.",
        "entities": [
            {"type": "company", "name": "수빅조선소", "role": "한진중공업 필리핀 자회사"},
            {"type": "company", "name": "한진중공업", "role": "수빅조선소 모회사 (85% 지분)"},
            {"type": "company", "name": "우덴나 코퍼레이션", "role": "수빅조선소 인수 협상 중인 필리핀 기업"},
        ],
        "relations": [
            {"source": "한진중공업", "target": "수빅조선소", "type": "ownership", "detail": "지분 85% 보유, 자본 1.9조원 투입"},
            {"source": "우덴나 코퍼레이션", "target": "수빅조선소", "type": "acquisition", "detail": "지분 85% 매각 협상 중, 추정가 약 1조원"},
        ],
        "risks": [
            {"type": "financial", "description": "매출원가가 매출액 초과하는 손실 구조 지속, 미청구공사 규모 적정성 의문", "severity": "critical"},
            {"type": "operational", "description": "2018년 상반기 매출 약 2,000억원 수준, 신규 수주 부족으로 가동률 저하 예상", "severity": "critical"},
            {"type": "strategic", "description": "저가 수주로 수익성 악화, 본원적 수주경쟁력 회복 불확실", "severity": "high"},
            {"type": "financial", "description": "약 3,700억원 연내 만기 장기차입금 상환 압박, 유동성 제약", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (40차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:40]}...")
        else:
            print(f"[FAIL] {article['title'][:40]}... - {result.get('error', 'Unknown')}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
