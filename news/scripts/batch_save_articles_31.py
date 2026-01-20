#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 31차 (필룩스/광림그룹/해덕파워웨이 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/209",
        "title": "비비안 전환사채, 수익권 진입했는데 전환권 포기?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-03-22",
        "summary": "비비안이 포비스티앤씨의 100억원 전환사채를 조기상환하면서 이미 수익권에 진입한 채권을 포기했다. 계열사 간 복잡한 자금 이동이 이루어지고 있다.",
        "entities": [
            {"type": "company", "name": "비비안", "role": "최대주주"},
            {"type": "company", "name": "포비스티앤씨", "role": "거래정지 상장사"},
            {"type": "company", "name": "미래산업", "role": "관계회사"},
            {"type": "company", "name": "아이오케이", "role": "인수대상"},
            {"type": "company", "name": "SBW홀딩스", "role": "관계회사"},
            {"type": "person", "name": "원영식", "role": "경영진"},
            {"type": "person", "name": "남석우", "role": "비비안 전 주인"},
        ],
        "relations": [
            {"source": "비비안", "target": "포비스티앤씨", "type": "ownership", "detail": "최대주주 지분 28.07%→20.43%"},
            {"source": "미래산업", "target": "아이오케이", "type": "investment", "detail": "강수진 지분 4.72% 104억원에 매입"},
        ],
        "risks": [
            {"type": "financial", "description": "포비스티앤씨 현금성자산 38억원 수준 유동성 위기", "severity": "critical"},
            {"type": "regulatory", "description": "상장적격성 실질심사 대상 지정 거래정지 중", "severity": "critical"},
            {"type": "governance", "description": "전환사채 상환 자금 출처 불명확", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/208",
        "title": "200만원짜리 케이에이치미디어, IHQ 어떻게 인수했나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-03-18",
        "summary": "필룩스그룹 계열사 케이에이치미디어가 자본금 200만원으로 IHQ를 1104억원에 인수. 삼본전자, 장원테크, 이엑스티가 전환사채로 자금 조달.",
        "entities": [
            {"type": "company", "name": "케이에이치미디어", "role": "IHQ 인수주체"},
            {"type": "company", "name": "필룩스그룹", "role": "모기업"},
            {"type": "company", "name": "IHQ", "role": "인수대상"},
            {"type": "company", "name": "삼본전자", "role": "전환사채 발행사"},
            {"type": "company", "name": "장원테크", "role": "전환사채 발행사"},
            {"type": "company", "name": "이엑스티", "role": "케이에이치미디어 모회사"},
            {"type": "company", "name": "메리츠증권", "role": "전환사채 인수사"},
        ],
        "relations": [
            {"source": "이엑스티", "target": "케이에이치미디어", "type": "ownership", "detail": "100% 자회사"},
            {"source": "케이에이치미디어", "target": "IHQ", "type": "acquisition", "detail": "50.49% 지분 1104억원 인수"},
            {"source": "메리츠증권", "target": "삼본전자", "type": "financing", "detail": "600억원 전환사채 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "케이에이치미디어 자본금 200만원으로 1104억원 차입 인수", "severity": "critical"},
            {"type": "governance", "description": "복잡한 계열사 간 전환사채 구조", "severity": "high"},
            {"type": "market", "description": "인수 후 주가 하락으로 전환가액 연쇄 조정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/207",
        "title": "해덕파워웨이 M&A, 승자는 없었다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-03-11",
        "summary": "해덕파워웨이 M&A는 이종희 원장과 이상필씨 간 복잡한 거래로 모든 이해관계자에게 손실. 옵티머스 펀드와 연결되어 상장폐지.",
        "entities": [
            {"type": "person", "name": "이종희", "role": "이지앤성형외과 원장"},
            {"type": "person", "name": "이상필", "role": "KJ프리텍 실소유주"},
            {"type": "person", "name": "박윤구", "role": "화성산업 대표"},
            {"type": "company", "name": "해덕파워웨이", "role": "M&A 대상"},
            {"type": "company", "name": "지와이커머스", "role": "자금 공급자"},
            {"type": "company", "name": "화성산업", "role": "최종 인수사"},
            {"type": "company", "name": "옵티머스", "role": "사모펀드"},
        ],
        "relations": [
            {"source": "이종희", "target": "해덕파워웨이", "type": "ownership_transition", "detail": "15.89% 지분 360억원 양도 계약 무산"},
            {"source": "화성산업", "target": "해덕파워웨이", "type": "acquisition", "detail": "15.89% 지분 300억원 인수"},
            {"source": "해덕파워웨이", "target": "옵티머스", "type": "investment", "detail": "펀드 수익증권 230억원 투자"},
        ],
        "risks": [
            {"type": "governance", "description": "임시주총 후보 7명 전원 선임 부결", "severity": "critical"},
            {"type": "financial", "description": "지와이커머스 현금 64억원→2억원 급감", "severity": "critical"},
            {"type": "legal", "description": "이상필 구속, 박윤구 사기/배임/횡령 혐의 구속", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/206",
        "title": "이상필씨에게 해덕파워웨이는 마지막 비상구였나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-03-08",
        "summary": "해덕파워웨이의 무자본 M&A 거래 분석. 이종희 원장이 주도한 인수 과정에서 360억원 투자 약속 불이행, 옵티머스 사기사건과 조직폭력배 동원 의혹.",
        "entities": [
            {"type": "person", "name": "이상필", "role": "지와이커머스 실소유주"},
            {"type": "person", "name": "이종희", "role": "해덕파워웨이 최대주주"},
            {"type": "person", "name": "구재고", "role": "해덕파워웨이 창업주"},
            {"type": "company", "name": "해덕파워웨이", "role": "부산 선박부품회사"},
            {"type": "company", "name": "지와이커머스", "role": "이상필 실소유 회사"},
            {"type": "company", "name": "옵티머스자산운용", "role": "펀드 운용사"},
            {"type": "company", "name": "KJ프리텍", "role": "지분 인수회사"},
        ],
        "relations": [
            {"source": "이종희", "target": "이상필", "type": "contract_breach", "detail": "360억원 투자 약속 불이행"},
            {"source": "옵티머스자산운용", "target": "해덕파워웨이", "type": "fraud", "detail": "회사자금 370억원 펀드 투자 자금세탁"},
        ],
        "risks": [
            {"type": "legal", "description": "인수대금 360억원 중 287억원 미회수", "severity": "critical"},
            {"type": "governance", "description": "무자본 M&A와 조직폭력배 동원 주총 개최", "severity": "critical"},
            {"type": "regulatory", "description": "옵티머스 사기사건 연루 370억원 손실", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/205",
        "title": "이엠앤아이와 지와이커머스, 어떻게 공동 운명체 되었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-03-04",
        "summary": "이상필 회장이 2017년 KJ프리텍(현 이엠앤아이) 경영권 장악 후 복잡한 투자조합과 차입금 구조로 지와이커머스와 연결되는 과정 추적.",
        "entities": [
            {"type": "person", "name": "이상필", "role": "회장"},
            {"type": "person", "name": "금상연", "role": "지와이커머스 전 지분 보유자"},
            {"type": "company", "name": "KJ프리텍", "role": "현 이엠앤아이"},
            {"type": "company", "name": "지와이커머스", "role": "최종 지배 대상"},
            {"type": "company", "name": "마누스파트너스", "role": "공동 인수자"},
            {"type": "company", "name": "에스티투자조합", "role": "공동 인수자"},
            {"type": "company", "name": "레이젠", "role": "현 디케이씨"},
        ],
        "relations": [
            {"source": "마누스파트너스", "target": "KJ프리텍", "type": "acquisition", "detail": "210만주 9.87% 인수 226억원"},
            {"source": "레이젠", "target": "에스티투자조합", "type": "investment", "detail": "80억원 초기 출자"},
        ],
        "risks": [
            {"type": "financial", "description": "대부분 차입금으로 조달한 226억원 레버리지 위험", "severity": "critical"},
            {"type": "governance", "description": "다층 투자조합 구조로 실질 지배구조 불투명", "severity": "critical"},
            {"type": "legal", "description": "담보권 실행 및 반대매매로 주식 몰수 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/204",
        "title": "이엠앤아이와 지와이커머스의 닮은꼴 회계부정, 우연일까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-03-02",
        "summary": "금감원 2020년 감리에서 적발된 이엠앤아이(KJ프리텍)와 지와이커머스의 회계부정 사건 분석. 대여금 허위 계상 등 유사한 부정행위.",
        "entities": [
            {"type": "company", "name": "이엠앤아이", "role": "구 KJ프리텍"},
            {"type": "company", "name": "지와이커머스", "role": "구 처음앤씨"},
            {"type": "company", "name": "씨피어쏘시에이츠", "role": "지와이커머스 인수 목적"},
            {"type": "company", "name": "레이젠", "role": "현 디케이씨"},
            {"type": "person", "name": "금상연", "role": "지와이커머스 전 최대주주"},
            {"type": "person", "name": "이상필", "role": "레이젠 실소유주"},
        ],
        "relations": [
            {"source": "이엠앤아이", "target": "지와이커머스", "type": "mutual_ownership", "detail": "상호 최대주주 지위 확보"},
            {"source": "이엠앤아이", "target": "씨피어쏘시에이츠", "type": "financial_transaction", "detail": "46억원 대여"},
        ],
        "risks": [
            {"type": "regulatory", "description": "금감원 회계감리에서 대여금 허위 계상 적발", "severity": "critical"},
            {"type": "financial", "description": "계속된 적자와 자본잠식으로 상장폐지 위기", "severity": "critical"},
            {"type": "governance", "description": "무자본 M&A로 담보 주식 반대매매 발생", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/203",
        "title": "아이오케이, 순환출자의 핵심 고리가 되다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-02-25",
        "summary": "광림그룹이 비비안, 포비스티앤씨, 아이오케이를 인수하면서 복잡한 지분 교환 진행. 순환출자 고리 형성.",
        "entities": [
            {"type": "company", "name": "광림", "role": "모회사"},
            {"type": "company", "name": "쌍방울", "role": "계열사"},
            {"type": "company", "name": "비비안", "role": "피인수 계열사"},
            {"type": "company", "name": "포비스티앤씨", "role": "피인수 계열사"},
            {"type": "company", "name": "아이오케이", "role": "신규 편입 계열사"},
            {"type": "company", "name": "칼라스홀딩스", "role": "광림 최대주주"},
            {"type": "person", "name": "배상윤", "role": "필룩스그룹 회장"},
            {"type": "person", "name": "원영식", "role": "W홀딩스컴퍼니 회장"},
        ],
        "relations": [
            {"source": "광림", "target": "쌍방울", "type": "transaction", "detail": "비비안 지분 15% 매각 약 222억원"},
            {"source": "쌍방울", "target": "아이오케이", "type": "transaction", "detail": "광림 지분 전량 매각 약 147억원"},
            {"source": "광림", "target": "비비안", "type": "circular_ownership", "detail": "칼라스홀딩스→광림→비비안→포비스티앤씨→아이오케이→광림 순환구조"},
        ],
        "risks": [
            {"type": "governance", "description": "순환출자 구조로 지배구조 감시 어려움", "severity": "high"},
            {"type": "financial", "description": "계열사 간 주식/전환사채 빈번한 거래로 자금 순환", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/202",
        "title": "비비안-쌍방울-광림의 3각 자금거래",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-02-22",
        "summary": "비비안이 8년 연속 영업손실을 기록하며 2019년 광림에 인수되는 과정에서 쌍방울, 광림, 비비안 간 복잡한 자금거래 발생.",
        "entities": [
            {"type": "company", "name": "비비안", "role": "인수 대상"},
            {"type": "company", "name": "쌍방울그룹", "role": "우선협상자"},
            {"type": "company", "name": "광림", "role": "최종 인수사"},
            {"type": "person", "name": "남석우", "role": "비비안 회장"},
            {"type": "company", "name": "남영산업", "role": "남석우 개인 회사"},
            {"type": "company", "name": "글로리조합", "role": "지분 인수 투자조합"},
            {"type": "person", "name": "진용주", "role": "글로리조합 이사"},
        ],
        "relations": [
            {"source": "쌍방울그룹", "target": "광림", "type": "financing", "detail": "100억원 전환사채→광림 80억원 유상증자"},
            {"source": "광림", "target": "비비안", "type": "acquisition", "detail": "남석우 외 8인으로부터 405만주 538억원 인수"},
            {"source": "비비안", "target": "쌍방울그룹", "type": "investment", "detail": "쌍방울 7회차 전환사채 100억원 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "8년 연속 영업손실 중 132억원 배당금 지급, 75%가 남석우 회장 친인척 집중", "severity": "high"},
            {"type": "financial", "description": "복잡한 자금 순환 구조로 투명성 불명확", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/201",
        "title": "아이오케이의 현금은 어떻게 광림으로 흘러갔나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-02-18",
        "summary": "광림그룹이 아이오케이 인수 후 계열사 거래를 통해 아이오케이 현금이 광림으로 이동. 비비안 지분 44% 프리미엄 매각.",
        "entities": [
            {"type": "company", "name": "광림", "role": "최상위 지배기업"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "연예기획사"},
            {"type": "company", "name": "쌍방울", "role": "상호지분 보유"},
            {"type": "company", "name": "비비안", "role": "속옷회사"},
            {"type": "company", "name": "포비스티앤씨", "role": "아이오케이 인수 주체"},
            {"type": "company", "name": "미래산업", "role": "인수 동원"},
            {"type": "person", "name": "원영식", "role": "회장"},
            {"type": "person", "name": "강수진", "role": "원영식 부인"},
        ],
        "relations": [
            {"source": "아이오케이", "target": "쌍방울", "type": "acquisition", "detail": "광림 14.03% 지분 147억원 인수"},
            {"source": "광림", "target": "비비안", "type": "sale", "detail": "15% 지분 약 222억원 쌍방울에 판매 44% 프리미엄"},
            {"source": "포비스티앤씨", "target": "아이오케이", "type": "acquisition", "detail": "미래산업과 함께 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "광림-비비안-포비스티앤씨-아이오케이-광림 순환출자 고리", "severity": "high"},
            {"type": "financial", "description": "계열사 간 44% 프리미엄 거래로 자산 부풀리기", "severity": "high"},
            {"type": "financial", "description": "아이오케이 인수 자금이 광림 채무 상환에 활용", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/200",
        "title": "원영식과 김성태, 배상윤의 IHQ 인수 도울까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-02-15",
        "summary": "필룩스그룹 배상윤 회장의 IHQ 989억원 인수에 원영식과 김성태 회장이 자금조달 지원. 약 900억원 추가 자금 필요.",
        "entities": [
            {"type": "person", "name": "원영식", "role": "회장"},
            {"type": "person", "name": "김성태", "role": "광림 회장"},
            {"type": "person", "name": "배상윤", "role": "필룩스그룹 회장"},
            {"type": "company", "name": "필룩스그룹", "role": "IHQ 인수 주체"},
            {"type": "company", "name": "케이에이치미디어", "role": "IHQ 인수 계약자"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "W홀딩컴퍼니 자회사"},
            {"type": "company", "name": "삼본전자", "role": "계열사"},
            {"type": "company", "name": "장원테크", "role": "최대주주"},
            {"type": "company", "name": "이엑스티", "role": "계열사"},
            {"type": "company", "name": "IHQ", "role": "인수 대상"},
        ],
        "relations": [
            {"source": "원영식", "target": "배상윤", "type": "financial_support", "detail": "필룩스그룹 자금조달 참여"},
            {"source": "김성태", "target": "배상윤", "type": "financial_support", "detail": "삼본전자 등이 광림 전환사채 약 200억원 인수"},
            {"source": "케이에이치미디어", "target": "IHQ", "type": "acquisition", "detail": "989억원 인수 3월 잔금 납부 예정"},
        ],
        "risks": [
            {"type": "financial", "description": "약 900억원 추가 자금 확보 불확실", "severity": "critical"},
            {"type": "governance", "description": "삼본전자/장원테크/이엑스티 간 복잡한 관계사 자금거래", "severity": "high"},
            {"type": "financial", "description": "인수금융 LBO 구조 담보가치 하락 시 반대매매 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/199",
        "title": "IHQ 인수자금 1000억원, 이엑스티가 총대 메나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-02-08",
        "summary": "필룩스그룹이 IHQ 지분 50.49%를 약 1088억원에 인수. 자산 200만원의 케이에이치미디어가 인수 주체, 이엑스티가 전환사채로 자금 조달.",
        "entities": [
            {"type": "company", "name": "필룩스그룹", "role": "IHQ 인수 주도"},
            {"type": "company", "name": "이엑스티", "role": "자금 조달 담당"},
            {"type": "company", "name": "케이에이치미디어", "role": "이엑스티 100% 자회사"},
            {"type": "company", "name": "IHQ", "role": "인수 대상"},
            {"type": "company", "name": "삼본전자", "role": "보증 계열사"},
            {"type": "company", "name": "장원테크", "role": "보증 계열사"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "케이에이치글로벌조합 출자사"},
            {"type": "person", "name": "배상윤", "role": "필룩스그룹 회장"},
        ],
        "relations": [
            {"source": "이엑스티", "target": "케이에이치미디어", "type": "ownership", "detail": "100% 자회사"},
            {"source": "케이에이치미디어", "target": "IHQ", "type": "acquisition", "detail": "지분 50.49% 약 1088억원 인수"},
            {"source": "아이오케이컴퍼니", "target": "케이에이치글로벌조합", "type": "investment", "detail": "130억원 중 99.99% 출자"},
        ],
        "risks": [
            {"type": "financial", "description": "케이에이치미디어 자산 200만원으로 979억원 잔금 조달 필요", "severity": "critical"},
            {"type": "financial", "description": "이엑스티 연간 영업이익 30-40억원 대비 500억원 이상 비영업 투자", "severity": "high"},
            {"type": "governance", "description": "케이에이치미디어가 사업보고서 미기재 유령 자회사", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/198",
        "title": "하얏트호텔 인수, 필룩스에 복 될까 화 될까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-02-04",
        "summary": "필룩스 유상증자 1차 발행가액 3660원 결정, 약 1321억원 조달. 경영진 스톡옵션 행사로 목돈 챙김. 하얏트호텔 인수는 코로나19로 부진.",
        "entities": [
            {"type": "company", "name": "필룩스", "role": "호텔 인수 주체"},
            {"type": "company", "name": "서울미라마", "role": "그랜드 하얏트호텔 서울 운영사"},
            {"type": "company", "name": "인마크1호 사모펀드", "role": "호텔 지분 인수 펀드"},
            {"type": "company", "name": "삼본전자", "role": "최대주주"},
            {"type": "person", "name": "김진명", "role": "필룩스 부사장"},
            {"type": "person", "name": "장준", "role": "필룩스 상무"},
            {"type": "person", "name": "김형철", "role": "필룩스 이사"},
        ],
        "relations": [
            {"source": "필룩스", "target": "서울미라마", "type": "ownership", "detail": "인마크1호 펀드를 통해 지분 100% 인수 추진"},
            {"source": "필룩스", "target": "인마크1호 사모펀드", "type": "investment", "detail": "출자금 440억원→지분가치 157억원 64% 손해"},
        ],
        "risks": [
            {"type": "financial", "description": "하얏트호텔 3분기 매출 404억원 영업손실 269억원 연 155억원 이자비용", "severity": "critical"},
            {"type": "operational", "description": "코로나19로 연 6.3% 매출증가 EBITDA마진 20% 달성 불가능", "severity": "critical"},
            {"type": "governance", "description": "경영진이 신주배정 기준일 전 보유 주식 전량 매도", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/197",
        "title": "필룩스, 그랜드 하얏트 인수용 유상증자로 유동성 가뭄 해소?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-02-01",
        "summary": "필룩스가 3월 예정 40% 유상증자로 약 1,045억원 조달 계획. 대부분 차입금 상환, 315억원은 하얏트 관련 우선주 매입.",
        "entities": [
            {"type": "company", "name": "필룩스", "role": "주요 당사자"},
            {"type": "company", "name": "인마크1호 사모투자합자회사", "role": "하얏트 지분 인수 펀드"},
            {"type": "company", "name": "삼본전자", "role": "필룩스 최대주주"},
            {"type": "company", "name": "서울미라마", "role": "하얏트호텔 운영사"},
        ],
        "relations": [
            {"source": "필룩스", "target": "인마크1호 PEF", "type": "investment", "detail": "460억원 출자 22.28% 지분, 우선주 315억원 추가 매입 계획"},
            {"source": "삼본전자", "target": "필룩스", "type": "ownership", "detail": "최대주주"},
        ],
        "risks": [
            {"type": "financial", "description": "유상증자 발행가액 주가 변동에 따라 결정 예상 조달액 편차", "severity": "high"},
            {"type": "financial", "description": "인마크24호 펀드 우선주 384억원 인수가 자금사용 목적에서 제외", "severity": "high"},
            {"type": "operational", "description": "2020년 9월까지 영업이익 29억원 적자 매출 전년 70% 수준", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/196",
        "title": "필룩스 항암치료제 어디까지 왔나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-01-28",
        "summary": "필룩스가 제넨셀에 15억원 투자하여 코로나19 치료제 개발 지원. 바이럴진과 리미나투스파마 통해 항암제 개발 진행. 동일 연구자가 경쟁 프로젝트 동시 진행 이해충돌 문제.",
        "entities": [
            {"type": "company", "name": "필룩스", "role": "제약 투자사"},
            {"type": "company", "name": "제넨셀", "role": "코로나19 치료제 개발사"},
            {"type": "company", "name": "바이럴진", "role": "대장암 치료제 개발사"},
            {"type": "company", "name": "리미나투스파마", "role": "고형암 치료제 개발사"},
            {"type": "company", "name": "이원컴포텍", "role": "대장암 치료제 협력사"},
            {"type": "person", "name": "스콧 월드만", "role": "토마스 제퍼슨 대학 교수"},
            {"type": "person", "name": "크리스 김", "role": "리미나투스파마/바이럴진 대표"},
        ],
        "relations": [
            {"source": "필룩스", "target": "제넨셀", "type": "investment", "detail": "2020년 11월 주당 3,300원 45만4천주 15억원 인수"},
            {"source": "필룩스", "target": "바이럴진", "type": "ownership", "detail": "2018년 4월 코아젠투스로부터 인수"},
            {"source": "스콧 월드만", "target": "바이럴진", "type": "leadership", "detail": "대장암 치료제 연구팀 주도"},
            {"source": "스콧 월드만", "target": "이원컴포텍", "type": "leadership", "detail": "2019년 10월 필룩스 이사직 사임 후 대장암 치료제 개발"},
        ],
        "risks": [
            {"type": "governance", "description": "동일 연구자가 필룩스와 경쟁사 이원컴포텍 양쪽에서 대장암 치료제 개발 이해충돌", "severity": "critical"},
            {"type": "operational", "description": "바이럴진/리미나투스파마에 임직원 파견 없어 개발 진행상황 파악 어려움", "severity": "high"},
            {"type": "regulatory", "description": "리미나투스파마 FDA IND 미제출 임상 지연", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/195",
        "title": "필룩스는 어떻게 바이럴 진 최대 주주가 되었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-01-25",
        "summary": "필룩스가 2018년 미국 바이오기업 바이럴 진의 최대 주주가 되는 과정 추적. 코아젠투스 파마와 지분 스왑 거래, 알파홀딩스와 분쟁.",
        "entities": [
            {"type": "company", "name": "필룩스", "role": "바이럴 진 최대 주주"},
            {"type": "company", "name": "바이럴 진", "role": "미국 자회사"},
            {"type": "company", "name": "코아젠투스 파마", "role": "바이럴 진 전 모회사"},
            {"type": "company", "name": "알파홀딩스", "role": "바이럴 진 2대 주주"},
            {"type": "company", "name": "이원컴포텍", "role": "스콧 월드만 협력"},
            {"type": "person", "name": "스콧 월드만", "role": "바이럴 진 설립자/CTO"},
            {"type": "person", "name": "크리스 김", "role": "코아젠투스 파마 공동 대표"},
            {"type": "person", "name": "이경훈", "role": "이원컴포텍 대표"},
        ],
        "relations": [
            {"source": "필룩스", "target": "바이럴 진", "type": "ownership", "detail": "2018년 3월 코아젠투스로부터 62.34%→85.45% 지분 인수"},
            {"source": "필룩스", "target": "코아젠투스 파마", "type": "transaction", "detail": "티제이유/펜라이프 100% 지분 378억원 인수 지분 스왑"},
            {"source": "필룩스", "target": "알파홀딩스", "type": "litigation", "detail": "2018년 11월 우선매수권 분쟁 합의"},
        ],
        "risks": [
            {"type": "legal", "description": "알파홀딩스와 우선매수권 소송 및 투자금 유용 의혹", "severity": "high"},
            {"type": "governance", "description": "스콧 월드만 교수 필룩스 이사직 사임 후 이원컴포텍 이동 리더십 공백", "severity": "high"},
            {"type": "financial", "description": "자회사 재무제표 1원 단위까지 동일한 회계 이상", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/194",
        "title": "대규모 유증 앞둔 급등, 필룩스 주가의 기막힌 타이밍",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-01-21",
        "summary": "필룩스 주가가 제넨셀 코로나19 치료제 임상 성공 소식에 상한가 기록. 대규모 1060억원 유상증자 앞두고 주가 급등으로 기준가 상승 효과.",
        "entities": [
            {"type": "company", "name": "필룩스", "role": "제넨셀 투자사"},
            {"type": "company", "name": "제넨셀", "role": "코로나19 치료제 개발 벤처"},
            {"type": "company", "name": "한국파마", "role": "제넨셀 의약품 생산"},
            {"type": "company", "name": "골드퍼시픽", "role": "컨소시엄 참여사"},
            {"type": "person", "name": "강세찬", "role": "전 필룩스 사외이사"},
            {"type": "person", "name": "원영식", "role": "전환사채 보유자"},
        ],
        "relations": [
            {"source": "필룩스", "target": "제넨셀", "type": "investment", "detail": "2020년 11월 15억원 제3자배정 유상증자 참여"},
            {"source": "필룩스", "target": "한국파마", "type": "partnership", "detail": "제넨셀 코로나19 치료제 개발 컨소시엄"},
        ],
        "risks": [
            {"type": "market", "description": "동일한 뉴스가 반복적으로 주가 부양하는 패턴", "severity": "high"},
            {"type": "financial", "description": "1060억원 대규모 유상증자로 기존 주주 지분 40% 희석", "severity": "high"},
            {"type": "operational", "description": "제넨셀 설립 6년차 직원 4명으로 5개월 만에 임상 2-3상 비정상 속도", "severity": "medium"},
            {"type": "financial", "description": "필룩스 단기차입금 536억원 보유현금 263억원 대비 높은 수준", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/193",
        "title": "상지카일룸은 어떻게 필룩스 디딤돌이 되었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-01-18",
        "summary": "필룩스가 2016년 상지건설 인수 후 1년여 만에 포워드컴퍼니스(후 상지카일룸)에 매각하는 과정 분석. 전환사채로 자금 조달하여 도곡동 토지 개발.",
        "entities": [
            {"type": "company", "name": "필룩스", "role": "상지건설 투자사"},
            {"type": "company", "name": "상지건설", "role": "부동산 개발회사"},
            {"type": "company", "name": "포워드컴퍼니스", "role": "상지카일룸 전신"},
            {"type": "company", "name": "바이필룩스", "role": "필룩스 자회사"},
            {"type": "person", "name": "유지호", "role": "상지건설 최대주주 62.29%"},
            {"type": "person", "name": "한종희", "role": "상지건설 2대주주/대표"},
            {"type": "person", "name": "신동걸", "role": "포워드컴퍼니스 대표"},
        ],
        "relations": [
            {"source": "필룩스", "target": "상지건설", "type": "acquisition", "detail": "2016년 7월 75.88% 지분 94억원대 인수 현금58억원+전환사채35억원"},
            {"source": "포워드컴퍼니스", "target": "상지건설", "type": "acquisition", "detail": "3차례 거래로 94.41% 지분 총 120억원 투입"},
            {"source": "필룩스", "target": "상지카일룸", "type": "sale", "detail": "2019년부터 주식 매각 31억원 회수"},
        ],
        "risks": [
            {"type": "financial", "description": "차입금으로 대여해 인수하고 전환사채 발행으로 자금 조달 자본구조 취약", "severity": "high"},
            {"type": "governance", "description": "원래 주주들이 전환사채 전환 시 주가 희석 효과", "severity": "high"},
            {"type": "governance", "description": "포워드컴퍼니스와 필룩스 간 계열사 거래 투명성 문제", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/192",
        "title": "필룩스·삼본전자·장원테크의 전환사채 활용법",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-01-14",
        "summary": "필룩스그룹 4개 상장사가 본업 현금흐름 없이 전환사채로 4,200억원을 부업에 투자. 전환사채 대부분이 보통주로 전환되어 자본 편입.",
        "entities": [
            {"type": "company", "name": "필룩스", "role": "지주사"},
            {"type": "company", "name": "삼본전자", "role": "계열사"},
            {"type": "company", "name": "장원테크", "role": "계열사"},
            {"type": "company", "name": "이엑스티", "role": "계열사"},
            {"type": "company", "name": "블루커넬", "role": "최대주주"},
        ],
        "relations": [
            {"source": "필룩스", "target": "삼본전자", "type": "ownership", "detail": "계열사 관계"},
            {"source": "블루커넬", "target": "필룩스", "type": "ownership", "detail": "2016년 이후 최대주주"},
            {"source": "필룩스그룹", "target": "전환사채", "type": "financing", "detail": "2016-2020년 총 1,500억원 이상 발행"},
        ],
        "risks": [
            {"type": "financial", "description": "2016년 이후 본업 영업활동 현금흐름 마이너스 외부자금 의존", "severity": "critical"},
            {"type": "operational", "description": "부업 투자(신약개발/호텔/IHQ 인수 등) 실질적 수익성 미확보", "severity": "high"},
            {"type": "governance", "description": "주가 하락 시 전환가액 낮추고 상승 시 전환해 매도 소수주주 이익 침해", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/191",
        "title": "최규선 사단인가? 필룩스 인물 열전",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-01-11",
        "summary": "케이티롤 경영권 인수부터 필룩스 인수에 이르기까지 복잡한 구조 추적. 전과자 최규선을 중심으로 한 인물 네트워크와 계열사 연계 분석.",
        "entities": [
            {"type": "person", "name": "최규선", "role": "케이티롤 대표이사 필룩스 실질 경영자"},
            {"type": "person", "name": "원영식", "role": "W홀딩컴퍼니 대표"},
            {"type": "person", "name": "이주석", "role": "에이블리 대표"},
            {"type": "person", "name": "진용주", "role": "블루커넬 대표"},
            {"type": "person", "name": "배기복", "role": "필룩스 대표"},
            {"type": "company", "name": "케이티롤", "role": "열간 압연롤 전문업체"},
            {"type": "company", "name": "필룩스", "role": "케이티롤에 인수된 회사"},
            {"type": "company", "name": "블루커넬", "role": "필룩스 인수 회사"},
            {"type": "company", "name": "W홀딩컴퍼니", "role": "더블유투자금융 모회사"},
        ],
        "relations": [
            {"source": "최규선", "target": "케이티롤", "type": "control", "detail": "2016년 3월 필룩스 인수 당일 대표이사 추대"},
            {"source": "블루커넬", "target": "필룩스", "type": "acquisition", "detail": "2016년 4월 케이티롤로부터 필룩스 인수"},
            {"source": "원영식", "target": "필룩스", "type": "investment", "detail": "더블우9호 통한 전환사채 100억원 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "에이블리가 순자산 없이 120억원 차입금으로 인수 실행", "severity": "critical"},
            {"type": "governance", "description": "최대주주 5회 이상 교체 4개월 만에 담보권 실행 반대매매 경영권 불안정", "severity": "critical"},
            {"type": "legal", "description": "최규선 2003년 뇌물수수 징역 2년 2018년 대법원 징역 9년 선고", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/190",
        "title": "필룩스는 어떻게 무자본 M&A 되었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-01-07",
        "summary": "블루커넬이 2016년 필룩스 지분을 전액 차입금으로 인수 후 2018년 약 650억원에 매각. 블루 계열 회사들로 연결되어 실질 동일인 추정.",
        "entities": [
            {"type": "company", "name": "필룩스", "role": "M&A 대상"},
            {"type": "company", "name": "블루커넬", "role": "필룩스 인수 주체"},
            {"type": "company", "name": "블루비스타", "role": "2018년 필룩스 최대 주주"},
            {"type": "company", "name": "삼본전자", "role": "후속 인수 대상"},
            {"type": "company", "name": "장원테크", "role": "삼본전자 자회사"},
            {"type": "company", "name": "케이에이치블루홀딩스", "role": "삼본전자 최대 주주"},
            {"type": "person", "name": "노시청", "role": "필룩스 전 최대 주주"},
            {"type": "person", "name": "진용주", "role": "블루커넬 전 최대 주주"},
            {"type": "person", "name": "이수래", "role": "블루커넬 최대 주주"},
        ],
        "relations": [
            {"source": "블루커넬", "target": "필룩스", "type": "acquisition", "detail": "2016년 4월 17% 지분 142억원 인수 차입금 전액"},
            {"source": "블루비스타", "target": "필룩스", "type": "acquisition", "detail": "2018년 3-4월 15.77% 지분 190억원 인수"},
            {"source": "블루커넬", "target": "블루비스타", "type": "succession", "detail": "2018년 4월 최대 주주 지위 이양 동일인 추정"},
            {"source": "케이에이치블루홀딩스", "target": "삼본전자", "type": "acquisition", "detail": "2018년 8월 컨소시엄으로 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "블루커넬과 블루비스타의 무자본 M&A 부채 기반 성장 주가 변동성 의존", "severity": "critical"},
            {"type": "governance", "description": "블루커넬과 블루비스타 동일 전화/팩스/담당자 실질 동일인 구조 공시상 불명확", "severity": "critical"},
            {"type": "legal", "description": "필룩스와 삼본전자 간 장원테크 지분 현물출자와 전환사채 재판매 순환 거래 소지", "severity": "high"},
            {"type": "market", "description": "2018년 2-4월 필룩스 주가 3,480원→27,150원 급등 시점에 전환사채/유상증자 집중", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (31차) ===\n")

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
