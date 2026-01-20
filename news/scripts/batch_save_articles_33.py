#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 33차 (이원컴포텍/비디아이/골드퍼시픽/퓨전/세미콘라이트/화이브라더스/두나무 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/169",
        "title": "이원컴포텍 뒤, 수 많은 투자조합의 정체는?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-10-22",
        "summary": "이원컴포텍은 2019년 5개의 투자조합이 조성되어 인수에 참여했으나 동일 주소 기반의 단일 투자집단으로 밝혀짐. 최종적으로 미국 바이오 회사 프로페이스 사이언스시스가 실질 주주로 등장.",
        "entities": [
            {"type": "company", "name": "이원컴포텍", "role": "인수 대상 기업"},
            {"type": "company", "name": "프로페이스 사이언스시스", "role": "신규 최대주주"},
            {"type": "company", "name": "사보이투자1호", "role": "구주 인수 주체"},
            {"type": "company", "name": "에이루트", "role": "사보이투자1호 최대출자자"},
            {"type": "company", "name": "케이앤티파트너스", "role": "사모펀드 운영사"},
            {"type": "person", "name": "권혁배", "role": "신임 대표이사"},
            {"type": "person", "name": "서문동군", "role": "에이루트 대표이사"},
        ],
        "relations": [
            {"source": "에이루트", "target": "사보이투자1호", "type": "investment", "detail": "40억원 출자로 최대출자자"},
            {"source": "프로페이스 사이언스시스", "target": "이원컴포텍", "type": "acquisition", "detail": "신주 82억6000만원 인수로 16.42% 지분 획득"},
        ],
        "risks": [
            {"type": "governance", "description": "5개 투자조합이 동일 주소에서 운영, 실질적 의사결정 구조 불명확", "severity": "high"},
            {"type": "governance", "description": "포르투나제1호의 실질 자금원 불명확", "severity": "high"},
            {"type": "financial", "description": "전환사채에 풋옵션/콜옵션 부여로 지분율 조정 용이", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/168",
        "title": "현대차 협력업체 이원컴포텍, 세력의 먹잇감 됐나?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-10-19",
        "summary": "이원컴포텍은 현대차 납품 협력업체로 2019년 말 사보이투자1호조합이 최대주주로 변경된 후 225억원 규모 자금으로 신약개발사 이노베이션과 빗썸 관련 투자 추진.",
        "entities": [
            {"type": "company", "name": "이원컴포텍", "role": "자동차 부품 납품사"},
            {"type": "company", "name": "사보이투자1호조합", "role": "신규 최대주주"},
            {"type": "company", "name": "이노베이션", "role": "바이오 투자 대상"},
            {"type": "company", "name": "버킷스튜디오", "role": "코스닥 상장사 자회사"},
            {"type": "person", "name": "김승구", "role": "이노베이션 대표"},
        ],
        "relations": [
            {"source": "사보이투자1호조합", "target": "이원컴포텍", "type": "ownership", "detail": "2019년 11월 최대주주 등극"},
            {"source": "이원컴포텍", "target": "이노베이션", "type": "investment", "detail": "25억원으로 29.41% 지분 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "본업과 무관한 신약개발, 암호화폐 투자 추진", "severity": "high"},
            {"type": "financial", "description": "4개월 된 신생회사 기업가치 2개월 만에 28배 상승", "severity": "critical"},
            {"type": "operational", "description": "이노베이션 독자 기술 없이 기술이전에만 의존", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/167",
        "title": "김재욱의 퇴각과 원영식의 아이오케이컴퍼니 매각의 관계는?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-10-15",
        "summary": "김재욱의 비트갤럭시 지분 매각과 원영식의 아이오케이컴퍼니 매각 사이의 복잡한 연결고리. 빗썸 경영권 분쟁과 전환사채 구조.",
        "entities": [
            {"type": "person", "name": "김재욱", "role": "비트갤럭시 투자자"},
            {"type": "person", "name": "원영식", "role": "더블유홀딩컴퍼니 회장"},
            {"type": "person", "name": "이정훈", "role": "빗썸 실질 지배자"},
            {"type": "company", "name": "이원컴포텍", "role": "비트갤럭시 인수자"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "비덴트 전환사채 보유"},
            {"type": "company", "name": "비덴트", "role": "빗썸 최대주주"},
        ],
        "relations": [
            {"source": "김재욱", "target": "비트갤럭시", "type": "ownership_exit", "detail": "50% 지분과 경영권을 30억원에 매각"},
            {"source": "원영식", "target": "아이오케이컴퍼니", "type": "ownership_exit", "detail": "김재욱 매각 한 달 후 지분 매각"},
            {"source": "아이오케이컴퍼니", "target": "비덴트", "type": "financial_instrument", "detail": "5760억원 전환사채로 24.84% 비덴트 지분 전환 가능"},
        ],
        "risks": [
            {"type": "governance", "description": "김재욱과 원영식의 조율된 매각으로 사전 합의 의혹", "severity": "high"},
            {"type": "financial", "description": "이원컴포텍 자산의 65%를 무관한 분야에 투자", "severity": "high"},
            {"type": "regulatory", "description": "복잡한 투자조합과 전환증권 구조의 공시 투명성 부족", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/166",
        "title": "비디아이 안승만 회장은 왜 100억원을 포기했을까?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-10-12",
        "summary": "비디아이 안승만 회장이 김일강 대표와의 경영권 분쟁 후 합의하면서 100억원 규모의 지분 양도 대금 포기. 복잡한 자금 조달 구조 드러남.",
        "entities": [
            {"type": "person", "name": "안승만", "role": "비디아이 회장"},
            {"type": "person", "name": "김일강", "role": "비디아이 대표"},
            {"type": "person", "name": "이진혁", "role": "비디아이 대표, 바이오사업부"},
            {"type": "company", "name": "비디아이", "role": "발행사"},
            {"type": "company", "name": "엘리슨 파마슈티컬스", "role": "인수 대상사"},
            {"type": "company", "name": "지앤지코리아테크", "role": "전환사채 인수자"},
        ],
        "relations": [
            {"source": "안승만", "target": "김일강", "type": "dispute", "detail": "경영권 매각 계약 후 갈등, 100억원 대금 포기"},
            {"source": "비디아이", "target": "엘리슨 파마슈티컬스", "type": "acquisition", "detail": "300억원 규모 자금 조달로 인수 진행"},
        ],
        "risks": [
            {"type": "governance", "description": "경영권 분쟁으로 지분율 급변동, 사채 발행 구조 설계 의혹", "severity": "high"},
            {"type": "financial", "description": "자본금 6억원 투자자들이 300억원 규모 사채 인수, 대규모 차입", "severity": "high"},
            {"type": "market", "description": "주가 급락, 반대매매로 지분 변동성 증가", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/165",
        "title": "현금흐름 쪼들렸던 비디아이, 엘리슨은 무엇을 위한 선택이었나?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-10-08",
        "summary": "발전플랜트 업체 비디아이는 영업 현금흐름 마이너스에도 신약 개발사 엘리슨 인수 추진. 매출채권 회수 문제와 계열사 대여금 손실로 유동성 악화.",
        "entities": [
            {"type": "company", "name": "비디아이", "role": "발전플랜트 업체"},
            {"type": "company", "name": "엘리슨", "role": "신약 개발사"},
            {"type": "company", "name": "임계솔라파크", "role": "계열사, 태양광발전"},
            {"type": "person", "name": "안승만", "role": "비디아이 회장"},
        ],
        "relations": [
            {"source": "비디아이", "target": "엘리슨", "type": "acquisition", "detail": "250억원 투자로 시가총액 2000억원 이상 증가"},
            {"source": "비디아이", "target": "임계솔라파크", "type": "financial_support", "detail": "2017-2019년 총 72억6000만원 대여금 제공"},
        ],
        "risks": [
            {"type": "financial", "description": "영업활동 현금흐름 2018년까지 지속 음수", "severity": "high"},
            {"type": "operational", "description": "매출채권 800억원 중 480억원이 미청구공사", "severity": "high"},
            {"type": "financial", "description": "임계솔라파크 대여금 72억6000만원 대손충당금 발생", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/164",
        "title": "두 달만에 주가 네 배, 비디아이 '빅 파마'의 꿈?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-10-01",
        "summary": "비디아이의 경영권 분쟁 과정에서 주가가 두 달간 4배 이상 상승. 미국 항암신약개발사 엘리슨 인수 발표하며 글로벌 제약사 진출 선언.",
        "entities": [
            {"type": "company", "name": "비디아이", "role": "발전플랜트 설비 납품사"},
            {"type": "company", "name": "엘리슨 파마슈티컬스", "role": "미국 항암신약개발사"},
            {"type": "company", "name": "에스인베스트먼트플랜", "role": "160억원 신주인수권부사채 인수사"},
            {"type": "company", "name": "지앤지코리아테크", "role": "140억원 전환사채 인수사"},
            {"type": "person", "name": "안승만", "role": "설립자, 회장"},
            {"type": "person", "name": "김일강", "role": "대표이사"},
            {"type": "person", "name": "에드윈 토마스", "role": "엘리슨 CEO"},
        ],
        "relations": [
            {"source": "비디아이", "target": "엘리슨 파마슈티컬스", "type": "acquisition", "detail": "250억원에 51% 지분 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "엘리슨 연 20억원 순손실, 자본잠식, 자산 7300만원 vs 부채 158억원", "severity": "critical"},
            {"type": "governance", "description": "신규 임원진에 바이오업계 경력자 부재", "severity": "high"},
            {"type": "market", "description": "자금 조달처 실체 불명확, 자금 출처 의문", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/163",
        "title": "신박했던 현대로템 전환사채 콜옵션 대작전",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-09-28",
        "summary": "현대로템이 2020년 3월 2400억원 규모 전환사채 발행. 투자자에게 유리한 조건(9,750원 전환가, 한 달 후 전환 가능)으로 두 달 만에 60% 이상 수익.",
        "entities": [
            {"type": "company", "name": "현대로템", "role": "전환사채 발행사"},
            {"type": "company", "name": "현대차", "role": "모회사"},
            {"type": "company", "name": "현대모비스", "role": "자산 인수 계열사"},
            {"type": "person", "name": "이용배", "role": "현대로템 사장"},
        ],
        "relations": [
            {"source": "현대로템", "target": "현대차", "type": "ownership", "detail": "모회사 관계, 현대차가 전환사채 인수 포기"},
            {"source": "현대로템", "target": "현대모비스", "type": "transaction", "detail": "의왕시 연구단지 부지 및 건물 878억원 매각"},
        ],
        "risks": [
            {"type": "financial", "description": "신용등급 하락(A-에서 BBB+로), 현금흐름 부족으로 CP 반복 발행", "severity": "critical"},
            {"type": "governance", "description": "현대차가 인수 포기한 전환사채로 기존 주주 지분 희석", "severity": "high"},
            {"type": "operational", "description": "철도·플랜트·방산 부문 부진, 코로나19로 창원공장 가동 중단", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/162",
        "title": "전환사채 콜옵션 행사의 뒷 이야기",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-09-24",
        "summary": "코스닥 상장사들이 전환사채를 중도 상환하는 현상 급증. 취득한 전환사채를 소각하지 않고 재매각하는 관행으로 최대 주주의 농간 여지 확대.",
        "entities": [
            {"type": "company", "name": "현대로템", "role": "전환사채 콜옵션 행사 사례"},
            {"type": "person", "name": "강종구", "role": "기자"},
        ],
        "relations": [],
        "risks": [
            {"type": "governance", "description": "취득한 전환사채 재매각 권리로 최대주주 농간 여지 증대", "severity": "high"},
            {"type": "financial", "description": "코스닥 전환가액 조정 횟수와 하한 무제한, 액면가까지 인하 가능", "severity": "high"},
            {"type": "operational", "description": "코스닥 기업들이 자금조달을 전환사채에 과도하게 의존", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/161",
        "title": "Did I&Invest Really Sell INCON?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-09-17",
        "summary": "아이앤인베스트가 인콘을 넷마블 방준혁 회장에게서 인수 후 골드퍼시픽에 매각하면서 전환사채로 통제권 유지. 복잡한 금융 조작 의혹.",
        "entities": [
            {"type": "company", "name": "아이앤인베스트", "role": "M&A 투자회사"},
            {"type": "company", "name": "인콘", "role": "CCTV 통합관제 솔루션 업체"},
            {"type": "company", "name": "골드퍼시픽", "role": "인콘 인수자"},
            {"type": "company", "name": "리버스톤", "role": "투자회사"},
            {"type": "company", "name": "케이앤티파트너스", "role": "사모펀드 운영사"},
            {"type": "person", "name": "김동원", "role": "아이앤인베스트 대표, 前 인콘 대표"},
            {"type": "person", "name": "김우동", "role": "골드퍼시픽 인수 핵심인물"},
            {"type": "person", "name": "방준혁", "role": "넷마블 회장, 前 인콘 최대주주"},
        ],
        "relations": [
            {"source": "방준혁", "target": "아이앤인베스트", "type": "sold_to", "detail": "2017년 8월 인콘 지분 매각"},
            {"source": "아이앤인베스트", "target": "골드퍼시픽", "type": "sold_to", "detail": "인콘을 342억원에 매각, 100억원은 전환사채로"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 관련 법인 네트워크로 실제 소유구조 불투명", "severity": "high"},
            {"type": "financial", "description": "관계사 차입과 전환증권으로 인수 자금 조달, 전환가격 대폭 하향 조정", "severity": "high"},
            {"type": "regulatory", "description": "다단계 전환사채 이전으로 공시 회피 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/160",
        "title": "밸런서즈, 골드퍼시픽에서 2년 만에 '더블' 엑시트",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-09-14",
        "summary": "밸런서즈그룹이 골드퍼시픽 지분 137억원 투자 후 2년 만에 240억원에 매각하며 약 100% 수익. 회사 실적 악화에도 과도한 프리미엄.",
        "entities": [
            {"type": "company", "name": "밸런서즈", "role": "골드퍼시픽 인수자 및 매각자"},
            {"type": "company", "name": "골드퍼시픽", "role": "인수 및 매각 대상"},
            {"type": "company", "name": "케이앤티파트너스", "role": "최종 인수자"},
            {"type": "person", "name": "유앤디씨", "role": "골드퍼시픽 최대주주"},
        ],
        "relations": [
            {"source": "밸런서즈", "target": "골드퍼시픽", "type": "investment", "detail": "2016년 바이오프리벤션 통해 137억원 투자"},
            {"source": "케이앤티파트너스", "target": "밸런서즈", "type": "acquisition", "detail": "2019년 3월 보통주 200억원, 전환사채 40억원 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "최대주주 빈번 변경, 지배주주 개인 사업 구조조정에 상장사 자금 활용", "severity": "critical"},
            {"type": "financial", "description": "실적 악화에도 과도한 프리미엄으로 지분 매각", "severity": "high"},
            {"type": "operational", "description": "2017년부터 2년간 304억원 중 175억원이 영업과 무관한 투자", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/159",
        "title": "세미콘라이트의 ㈜액트 단기투자, 그 이면",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-09-10",
        "summary": "세미콘라이트가 2019년 10월 액트 지분 32.1%를 278억원에 인수 후 7개월 만에 매각. 실제로 조광아이엘아이 지분 인수를 위한 중개 역할.",
        "entities": [
            {"type": "company", "name": "세미콘라이트", "role": "액트 지분 인수자"},
            {"type": "company", "name": "액트", "role": "인수 대상"},
            {"type": "company", "name": "조광아이엘아이", "role": "액트의 투자 대상"},
            {"type": "company", "name": "골드퍼시픽", "role": "조광아이엘아이 지분 인수자"},
            {"type": "company", "name": "메리디안홀딩스", "role": "액트 인수자"},
            {"type": "person", "name": "온영두", "role": "세미콘라이트 회장"},
            {"type": "person", "name": "김우동", "role": "조광아이엘아이 대표이사"},
        ],
        "relations": [
            {"source": "세미콘라이트", "target": "액트", "type": "investment", "detail": "278억원으로 32.1% 지분 인수 후 5월 매각"},
            {"source": "액트", "target": "조광아이엘아이", "type": "investment", "detail": "139억원 유상증자로 10.11% 지분 매입"},
            {"source": "김우동", "target": "조광아이엘아이", "type": "control", "detail": "19.22% 지분으로 실제 경영권 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "세미콘라이트 3년 연속 적자로 241억원 매출에 230억원 손실", "severity": "critical"},
            {"type": "governance", "description": "메리디안홀딩스 자기자본 6,300만원으로 경영권 확보, 95억원은 외부 차입", "severity": "high"},
            {"type": "market", "description": "액트의 조광아이엘아이 투자가 단순 재무적 투자로 표기되나 실제 경영권 중개 역할", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/158",
        "title": "벼랑 끝 몰린 퓨전, 운명의 향방은?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-09-07",
        "summary": "퓨전은 감사의견 거절과 결손 누적으로 상장폐지 위기. 세미콘라이트 지분이 생명줄이나 세미콘라이트도 본업 영업이익 미창출.",
        "entities": [
            {"type": "company", "name": "퓨전", "role": "상장사, 세미콘라이트 대주주"},
            {"type": "company", "name": "세미콘라이트", "role": "퓨전의 주요 자산"},
            {"type": "company", "name": "플리트 엔터테인먼트", "role": "인수 대상"},
            {"type": "person", "name": "온영두", "role": "퓨전홀딩스 회장"},
            {"type": "person", "name": "조호걸", "role": "세미콘라이트 전 최대주주"},
        ],
        "relations": [
            {"source": "퓨전", "target": "세미콘라이트", "type": "ownership", "detail": "지분 207억원, 전환사채 60억원 보유"},
            {"source": "세미콘라이트", "target": "플리트 엔터테인먼트", "type": "acquisition", "detail": "11월까지 인수 완료 계획"},
        ],
        "risks": [
            {"type": "regulatory", "description": "감사의견 거절로 인한 내년 4월 상장폐지 위기", "severity": "critical"},
            {"type": "financial", "description": "현금성자산 2억원 수준으로 유동성 부족", "severity": "critical"},
            {"type": "governance", "description": "관련자 거래: 세미콘라이트 매도자가 인수자금 전환사채 인수", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/157",
        "title": "부실기업 퓨전의 잇딴 M&A, 꼭지점은 누구?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-09-03",
        "summary": "부실 가상화 업체 퓨전을 중심으로 한 복잡한 M&A 네트워크. 박일홍을 통해 소수 실권자가 통제하며 전환사채와 유상증자로 비현금 거래.",
        "entities": [
            {"type": "company", "name": "퓨전", "role": "핵심 인수 기구"},
            {"type": "company", "name": "세미콘라이트", "role": "인수 대상 자회사"},
            {"type": "company", "name": "플리트 엔터테인먼트", "role": "세미콘라이트 통한 인수 대상"},
            {"type": "company", "name": "퓨전홀딩스", "role": "퓨전 실질 지배회사"},
            {"type": "person", "name": "박일홍", "role": "퓨전, 퓨전홀딩스, 세미콘라이트 대표"},
            {"type": "person", "name": "이종명", "role": "퓨전 전 최대주주"},
            {"type": "person", "name": "조호걸", "role": "에스엠씨홀딩스 주주"},
            {"type": "person", "name": "온영두", "role": "퓨전홀딩스 100% 주주"},
        ],
        "relations": [
            {"source": "퓨전홀딩스", "target": "퓨전", "type": "control", "detail": "저지분으로 실질 지배"},
            {"source": "박일홍", "target": "퓨전", "type": "management", "detail": "여러 법인 대표로서 통제"},
        ],
        "risks": [
            {"type": "governance", "description": "공시상 지분율과 실제 지배력 사이 괴리", "severity": "critical"},
            {"type": "financial", "description": "본업 매출 200억원에서 14억원으로 급락에도 M&A 적극 추진", "severity": "critical"},
            {"type": "regulatory", "description": "2019년 감사보고서 의견거절로 상장폐지 위기", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/156",
        "title": "세미콘라이트 반기 흑자전환의 비밀",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-08-31",
        "summary": "LED칩 제조 세미콘라이트가 영업적자에도 79억원 당기순이익 달성. 전환사채 거래와 주식 매매를 통한 차익 실현이 핵심.",
        "entities": [
            {"type": "company", "name": "세미콘라이트", "role": "대상 기업"},
            {"type": "company", "name": "에스디시스템", "role": "전환사채 거래 상대방"},
            {"type": "company", "name": "이큐셀", "role": "전환사채 거래 상대방"},
            {"type": "company", "name": "퓨전", "role": "최대주주"},
            {"type": "company", "name": "액트", "role": "투자 대상"},
        ],
        "relations": [
            {"source": "세미콘라이트", "target": "에스디시스템", "type": "convertible_bond", "detail": "115억원 전환사채를 60억원으로 축소된 규모로 대용납입"},
            {"source": "세미콘라이트", "target": "액트", "type": "investment", "detail": "264억원 투자로 최대주주 지위 획득, 5월 일부 80억원에 매각"},
        ],
        "risks": [
            {"type": "governance", "description": "현금 오가지 않은 전환사채 대용납입 방식의 타당성 문제", "severity": "critical"},
            {"type": "financial", "description": "본업 영업적자를 금융거래 처분이익으로 상쇄, 실제 가치 개선 없음", "severity": "critical"},
            {"type": "regulatory", "description": "퓨전, 에스디시스템, 이큐셀 모두 감사의견 '의견거절' 상장폐지 대상", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/155",
        "title": "플리트 엔터테인먼트의 새주인 엔에스엔의 수상한 과거",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-08-27",
        "summary": "엔에스엔(구 에이모션) 황원희와 대주인터내셔널 간의 의심스러운 지분 이전. 동일 가격의 복수 거래와 순환 자금 흐름 의혹.",
        "entities": [
            {"type": "person", "name": "황원희", "role": "엔에스엔 원 최대주주"},
            {"type": "company", "name": "대주인터내셔널", "role": "지분 인수 중간 지주회사"},
            {"type": "company", "name": "엔에스엔", "role": "대상 기업"},
            {"type": "company", "name": "창윤개발", "role": "100억원 무담보 대출 제공"},
            {"type": "person", "name": "안원현", "role": "대주인터내셔널 초기 대표"},
            {"type": "person", "name": "이정현", "role": "대주인터내셔널 후속 최대주주"},
        ],
        "relations": [
            {"source": "황원희", "target": "엔에스엔", "type": "ownership_transfer", "detail": "2016년 4월 107만주(7.83%) 주당 7,454원에 매각"},
            {"source": "창윤개발", "target": "대주인터내셔널", "type": "financing", "detail": "15개월 만기 100억원 무담보 대출"},
            {"source": "황원희", "target": "대주인터내셔널", "type": "debt_offset", "detail": "280만주를 886억원 채무 상계로 재매입"},
        ],
        "risks": [
            {"type": "financial", "description": "순환 자금 흐름, 창윤개발 대출 자금원이 황원희 주식 매각 대금으로 보임", "severity": "high"},
            {"type": "governance", "description": "동일 7,454원 가격의 7개월간 복수 거래로 사전 합의 의혹", "severity": "high"},
            {"type": "financial", "description": "자산 2400만원 페이퍼컴퍼니에서 100억원 무담보 대출 비정상", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/154",
        "title": "엔에스엔·세미콘라이트는 마이너스의 손?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-08-24",
        "summary": "코스닥 상장사 엔에스엔과 세미콘라이트가 영업손실 지속하며 자회사 인수와 매각 반복. 단기 금융 거래로 수익 창출하는 기업 사냥꾼 도구 의혹.",
        "entities": [
            {"type": "company", "name": "엔에스엔", "role": "코스닥 상장사"},
            {"type": "company", "name": "세미콘라이트", "role": "코스닥 상장사"},
            {"type": "company", "name": "플리트 엔터테인먼트", "role": "인수 대상"},
            {"type": "company", "name": "화이브라더스", "role": "이전 투자자"},
            {"type": "person", "name": "지승범", "role": "인수 관련 주요 주주"},
        ],
        "relations": [
            {"source": "엔에스엔", "target": "플리트 엔터테인먼트", "type": "acquisition", "detail": "다수 자회사 2-3년 보유 후 매각 반복"},
        ],
        "risks": [
            {"type": "financial", "description": "연간 100억원 이상 영업손실 지속, 세미콘라이트 자회사 손상차손 710억원", "severity": "high"},
            {"type": "operational", "description": "손을 대는 회사마다 망함, 3개 자회사 청산, 다수 손상차손 인식", "severity": "critical"},
            {"type": "regulatory", "description": "코스닥 상장 지위를 관계사 거래와 기업 사냥 도구로 활용 의혹", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/153",
        "title": "화이브라더스 재매각, 예정된 거래였나",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-08-20",
        "summary": "화이브라더스는 중국 연예기획사 인수 후 적자 행진. 2020년 5월 엔에스엔과 세미콘라이트가 단계적 인수하는 구도 형성, 자금 조달 차질.",
        "entities": [
            {"type": "company", "name": "화이브라더스", "role": "매각 대상"},
            {"type": "company", "name": "엔에스엔", "role": "1차 인수자"},
            {"type": "company", "name": "세미콘라이트", "role": "최종 인수자"},
            {"type": "company", "name": "메리크리스마스", "role": "화이브라더스 계열사"},
            {"type": "company", "name": "엔씨소프트", "role": "메리크리스마스 투자자"},
            {"type": "person", "name": "지승범", "role": "대표이사 및 최대주주"},
        ],
        "relations": [
            {"source": "화이브라더스", "target": "메리크리스마스", "type": "ownership", "detail": "2018년 5월 75% 지분 95억원에 취득"},
            {"source": "엔에스엔", "target": "화이브라더스", "type": "acquisition", "detail": "2020년 5월 250억원에 21.84% 지분 인수"},
            {"source": "세미콘라이트", "target": "화이브라더스", "type": "acquisition", "detail": "엔에스엔으로부터 250억원에 21.6% 지분 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "특별관계인으로 공시하지 않은 다층 구조의 중간 거래자 관여", "severity": "high"},
            {"type": "financial", "description": "514억원 거래대금 중 360억원 미납입, 자금 조달 차질", "severity": "high"},
            {"type": "operational", "description": "엔에스엔과 세미콘라이트 모두 최근 3년간 당기순손실 부실기업", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/152",
        "title": "화이브라더스의 4년 전 M&A가 남긴 의문",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-08-17",
        "summary": "2016년 화이브라더스의 심엔터테인먼트 인수 과정 추적. M&A 전문가 지승범이 레버리지 금융으로 인수 주도, 부실자산 회사에서 무담보 대출.",
        "entities": [
            {"type": "company", "name": "화이브라더스", "role": "인수자"},
            {"type": "company", "name": "심엔터테인먼트", "role": "피인수회사"},
            {"type": "company", "name": "새한자산대부평가관리", "role": "부실자산 대출사"},
            {"type": "company", "name": "화이앤조이엔터테인먼트", "role": "특수목적회사"},
            {"type": "person", "name": "지승범", "role": "M&A 전문가, 공동 인수자"},
            {"type": "person", "name": "지승환", "role": "대출사 대표"},
            {"type": "person", "name": "심정운", "role": "심엔터테인먼트 창업자"},
        ],
        "relations": [
            {"source": "화이브라더스", "target": "심엔터테인먼트", "type": "acquisition", "detail": "2016년 3월 기존주식 26.73%를 156억원에 인수"},
            {"source": "새한자산대부평가관리", "target": "지승범", "type": "unsecured_lending", "detail": "최소 12.2억원 무담보 대출 제공"},
        ],
        "risks": [
            {"type": "financial", "description": "부실자산 회사에서 무담보 대출로 인수 자금 조달", "severity": "high"},
            {"type": "governance", "description": "중국 모회사 지배력 제한, 실제 운영은 로컬 M&A 전문가가 통제", "severity": "high"},
            {"type": "regulatory", "description": "레버리지 인수 패턴, 관계자 거래 공시 규정 위반 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/151",
        "title": "두나무(2): 배당금 잔치 할 때인가?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-08-13",
        "summary": "두나무는 암호화폐 시장 불황에도 자회사 투자를 확대했으나 7개 종속기업이 지속 적자로 투자 원본 30% 손실. 현금 급감 중에도 배당금 지속.",
        "entities": [
            {"type": "company", "name": "두나무", "role": "대상 기업"},
            {"type": "company", "name": "업비트", "role": "암호화폐 거래소 자회사"},
            {"type": "company", "name": "퓨처위즈", "role": "증권 데이터 자회사"},
            {"type": "company", "name": "람다256", "role": "블록체인 연구 자회사"},
            {"type": "company", "name": "디엑스엠", "role": "암호화폐 수탁 자회사"},
        ],
        "relations": [
            {"source": "두나무", "target": "업비트", "type": "ownership", "detail": "암호화폐 거래소 자회사, 주요 수익원"},
            {"source": "두나무", "target": "퓨처위즈", "type": "ownership", "detail": "100% 지분 증권 데이터 제공"},
        ],
        "risks": [
            {"type": "financial", "description": "현금 1.17조원(2017)에서 3110억원(2019)으로 급감", "severity": "high"},
            {"type": "operational", "description": "7개 종속기업 2019년 합산 910억원 손실, 투자 원본 30% 소진", "severity": "high"},
            {"type": "governance", "description": "현금흐름 악화 중에도 2년간 2990억원 배당 지급", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/150",
        "title": "보릿고개가 덜 고달픈 업비트",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-08-10",
        "summary": "두나무는 암호화폐 거래소 업비트와 주식 거래 앱 증권플러스를 운영하며 다른 거래소 대비 재무 안정성 유지. 암호화폐 시장 하락기에도 수익성 유지.",
        "entities": [
            {"type": "company", "name": "두나무", "role": "업비트, 증권플러스 운영사"},
            {"type": "company", "name": "카카오", "role": "소수주주 12.17%"},
            {"type": "person", "name": "송치형", "role": "창업자, 회장, 최대주주"},
        ],
        "relations": [
            {"source": "두나무", "target": "업비트", "type": "operates", "detail": "암호화폐 거래소 운영"},
            {"source": "두나무", "target": "증권플러스", "type": "operates", "detail": "주식 거래 앱 운영, 220만 사용자"},
            {"source": "카카오", "target": "두나무", "type": "ownership", "detail": "12.17% 보통주 + 8.1% 전환우선주"},
        ],
        "risks": [
            {"type": "market", "description": "매출이 암호화폐 시장 사이클에 크게 의존, 2018년 시장 하락으로 급감", "severity": "high"},
            {"type": "financial", "description": "암호화폐 보유분 가치 변동성, 2018-2019년 비트코인 4,437개 매각", "severity": "high"},
            {"type": "operational", "description": "수익성이 암호화폐 자산 처분에 의존, 지속 가능한 운영 아님", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (33차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}... ({result.get('error', 'Unknown error')[:50]})")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
