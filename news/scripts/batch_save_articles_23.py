#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 23차 (롯데건설PF/한화건설/금강공업/화천기계 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/369",
        "title": "선제대응 필요한 게 롯데건설 뿐일까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-11-04",
        "summary": "강원중도개발공사의 회생절차 신청과 레고랜드 ABCP 부도로 공기업 채권이 유찰되는 사태가 발생. 부동산PF 시장 전체로 신용위기 확산 우려.",
        "entities": [
            {"type": "company", "name": "롯데건설", "role": "시공사"},
            {"type": "company", "name": "강원중도개발공사", "role": "회생절차 신청"},
            {"type": "company", "name": "현대건설", "role": "시공사"},
            {"type": "company", "name": "대우건설", "role": "시공사"},
            {"type": "company", "name": "GS건설", "role": "시공사"},
            {"type": "company", "name": "롯데케미칼", "role": "롯데건설 최대주주"},
        ],
        "relations": [
            {"source": "롯데케미칼", "target": "롯데건설", "type": "financial_support", "detail": "5000억원 차입 제공"},
        ],
        "risks": [
            {"type": "financial", "description": "부동산PF ABCP 3~6개월 만기 집중으로 건설사들의 단기 자금 부담 급증", "severity": "critical"},
            {"type": "market", "description": "금리 급등과 아파트 가격 하락으로 미분양 증가 및 시행사 부도 위험", "severity": "high"},
            {"type": "governance", "description": "건설사의 연대보증 및 채무인수로 인한 우발채무의 현실화 가능성", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/368",
        "title": "롯데건설이 선제대응에 나선 리스크는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-10-31",
        "summary": "롯데건설이 2000억원 유상증자와 계열사 5000억원 차입으로 총 7000억원을 급하게 조달. 부동산 PF 유동화증권의 차환 실패 위험과 단기 만기 구조로 인한 유동성 위기.",
        "entities": [
            {"type": "company", "name": "롯데건설", "role": "주요 대상"},
            {"type": "company", "name": "롯데케미칼", "role": "최대주주"},
            {"type": "company", "name": "강원중도개발공사", "role": "레고랜드 개발 사업주체"},
        ],
        "relations": [
            {"source": "롯데건설", "target": "롯데케미칼", "type": "financing", "detail": "운영자금 목적 5000억원 차입"},
        ],
        "risks": [
            {"type": "financial", "description": "PF 유동화증권 차환 실패로 인한 돌발적 상환 압박. 단기 만기(3-6개월) 구조로 유동성 위기", "severity": "high"},
            {"type": "market", "description": "레고랜드 사태 이후 건설사 신용 부도설 확산으로 인한 시장 우려", "severity": "high"},
            {"type": "operational", "description": "미착공 사업장 비중 70% 이상, 6개월 이내 만기 프로젝트 80% 이상", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/367",
        "title": "비스마야사업 진행률과 공정률, 차이의 의미는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-10-27",
        "summary": "한화건설의 이라크 비스마야 신도시 개발사업에서 공사진행률과 공정률의 차이가 양측의 분쟁 원인. 공사대금 지급 규모에 큰 차이 발생.",
        "entities": [
            {"type": "company", "name": "한화건설", "role": "시공사"},
            {"type": "company", "name": "이라크 정부", "role": "발주자"},
        ],
        "relations": [
            {"source": "한화건설", "target": "이라크 정부", "type": "contract_dispute", "detail": "공사진행률(44.99%) vs 공정률(38%) 차이"},
        ],
        "risks": [
            {"type": "legal", "description": "양측의 공사 진척도 인식 차이로 인한 계약 분쟁 심화 가능성", "severity": "critical"},
            {"type": "financial", "description": "미청구공사 464억원(인프라공사)이 손실로 귀결될 가능성", "severity": "high"},
            {"type": "financial", "description": "주택보급공사의 진행률과 공정률 차이(약 7,226억원)의 회수 불확실성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/366",
        "title": "이라크 정부의 입장은 한화와 달랐다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-10-24",
        "summary": "한화건설의 100억 달러 규모 비스마야 신도시 프로젝트 철수를 놓고 한화와 이라크 정부가 상반된 주장. 한화는 공사대금 미지급, 이라크는 공기 미준수 주장.",
        "entities": [
            {"type": "company", "name": "한화그룹", "role": "프로젝트 수주사"},
            {"type": "company", "name": "한화건설", "role": "시공 담당"},
            {"type": "company", "name": "이라크 국가 투자위원회", "role": "발주처"},
        ],
        "relations": [
            {"source": "한화건설", "target": "이라크 국가 투자위원회", "type": "contract_dispute", "detail": "비스마야 신도시 프로젝트 공사대금 분쟁"},
        ],
        "risks": [
            {"type": "financial", "description": "6억 2,900만 달러의 미수금이 실제로 회수되지 못할 가능성", "severity": "critical"},
            {"type": "legal", "description": "공사 진행률 및 준공 주택 수에 대한 양측의 상이한 주장으로 장기 분쟁", "severity": "critical"},
            {"type": "market", "description": "약 14조 3,000억 원 규모 사업 포기로 인한 매출 및 실적 악화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/365",
        "title": "이라크가 합병 반대하자 101조 사업 포기?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-10-20",
        "summary": "한화건설이 이라크 비스마야 신도시사업(101억 달러)에서 철수 결정. ㈜한화의 한화건설 합병에 이라크 정부가 동의하지 않자 계약 해지로 대응.",
        "entities": [
            {"type": "company", "name": "한화건설", "role": "사업시행사"},
            {"type": "company", "name": "㈜한화", "role": "모회사"},
            {"type": "company", "name": "이라크 국가투자위원회", "role": "발주처"},
            {"type": "person", "name": "김승연", "role": "한화그룹 회장"},
        ],
        "relations": [
            {"source": "한화건설", "target": "비스마야 신도시사업", "type": "contract_termination", "detail": "2022년 10월 7일 도급계약 해지 통보"},
            {"source": "㈜한화", "target": "한화건설", "type": "merger_planned", "detail": "2022년 11월 1일 예정 흡수합병"},
        ],
        "risks": [
            {"type": "financial", "description": "미회수 공사대금 약 6억 2,900만 달러의 회수 불확실성", "severity": "critical"},
            {"type": "operational", "description": "총 수주잔고의 30% 이상 규모 프로젝트 포기로 사업 규모 축소", "severity": "critical"},
            {"type": "governance", "description": "합병 반대에 대한 계약 해지 대응의 정당성 논란", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/364",
        "title": "급한 건 금강공업이 아닌 산업은행이었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-10-17",
        "summary": "코에프씨밸류업 PEF가 삼미금속 투자 회수 압박에 직면. 금강공업이 삼미금속을 인수하며 코에프씨의 지분과 채권을 인수.",
        "entities": [
            {"type": "company", "name": "삼미금속", "role": "피인수회사"},
            {"type": "company", "name": "금강공업", "role": "인수자"},
            {"type": "company", "name": "코에프씨밸류업 PEF", "role": "전 최대주주"},
            {"type": "company", "name": "케이에스피", "role": "금강공업 자회사"},
            {"type": "person", "name": "신현철", "role": "삼미금속 주주"},
        ],
        "relations": [
            {"source": "금강공업", "target": "삼미금속", "type": "acquisition", "detail": "100% 지분 인수, 160-170억원 지급"},
        ],
        "risks": [
            {"type": "financial", "description": "코에프씨밸류업 PEF 초기 650억원 자본 중 약 70% 손실, 230억원만 회수", "severity": "critical"},
            {"type": "operational", "description": "삼미금속 2018년 이후 연속 영업적자, 지속적 적자 상태", "severity": "high"},
            {"type": "governance", "description": "복잡한 주주 구조 변경으로 실질 소유권 파악 어려움", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/363",
        "title": "부도 냈던 금강공업, 망할 뻔한 기업들 인수해 확장",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-10-13",
        "summary": "금강공업은 1998년 외환위기로 부도 위기 후 법정관리나 화의 상태의 기업들을 인수하며 확장. 회장 일가의 가회동 한옥 123억원 취득 자금출처 의문.",
        "entities": [
            {"type": "company", "name": "금강공업", "role": "기업집단 중심기업"},
            {"type": "person", "name": "전정열", "role": "회장 겸 대표이사"},
            {"type": "person", "name": "안영순", "role": "최대주주"},
            {"type": "person", "name": "전재범", "role": "차남, 3개 상장사 사장"},
            {"type": "company", "name": "고려산업", "role": "자회사"},
            {"type": "company", "name": "케이에스피", "role": "자회사"},
        ],
        "relations": [
            {"source": "금강공업", "target": "고려산업", "type": "acquisition", "detail": "2005년 워크아웃 중 인수"},
            {"source": "금강공업", "target": "케이에스피", "type": "acquisition", "detail": "2018년 회생절차 중 80.13% 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "16년간 영업현금흐름 4,268억원 대비 유무형자산 지출 5,554억원으로 매년 현금 부족", "severity": "high"},
            {"type": "governance", "description": "최대주주 일가의 한옥 취득 자금출처 불명확, 주식 담보 상황에서 대규모 현금 동원 경로 미상", "severity": "high"},
            {"type": "governance", "description": "인수된 자회사에서 전 소유자 및 관련 인사들이 계속 중요 역할 담당", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/362",
        "title": "한화갤러리아 분할, 승계 준비작업으로 보이는 이유",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-10-11",
        "summary": "한화솔루션이 한화갤러리아를 인적분할하는 것은 김승연 회장의 세 아들로의 경영권 승계를 준비하는 과정의 일환. 3남 김동선 상무의 유통부문 승계 입지를 확실히 하는 의도.",
        "entities": [
            {"type": "company", "name": "한화솔루션", "role": "분할 주체"},
            {"type": "company", "name": "한화갤러리아", "role": "분할 대상"},
            {"type": "company", "name": "㈜한화", "role": "지주사"},
            {"type": "person", "name": "김승연", "role": "회장"},
            {"type": "person", "name": "김동관", "role": "부사장, 장남"},
            {"type": "person", "name": "김동원", "role": "부사장, 차남"},
            {"type": "person", "name": "김동선", "role": "상무, 삼남"},
        ],
        "relations": [
            {"source": "한화솔루션", "target": "한화갤러리아", "type": "corporate_restructuring", "detail": "인적분할을 통해 독립화"},
            {"source": "김동선", "target": "한화호텔앤드리조트", "type": "succession_designation", "detail": "유통 및 호텔부문 승계 예상"},
        ],
        "risks": [
            {"type": "governance", "description": "한화호텔앤드리조트의 지분구조가 애매하여 경영권 분산 가능성, ㈜한화 49.8% vs 한화솔루션 49.57%", "severity": "high"},
            {"type": "financial", "description": "한화첨단소재 매각을 통한 자금조달이 글로벌 태양광 사업 투자에 집중되어 집중도 위험", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/361",
        "title": "분할신설 한화갤러리아, 그 많던 빚 어디 갔나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-10-06",
        "summary": "한화솔루션이 인적분할을 통해 백화점 사업부문인 한화갤러리아를 분리. 분할 과정에서 차입금 6,243억원이 존속회사에 남겨져 신설회사의 재무 부담 경감.",
        "entities": [
            {"type": "company", "name": "한화솔루션", "role": "존속회사"},
            {"type": "company", "name": "한화갤러리아", "role": "분할 신설법인"},
            {"type": "company", "name": "한화갤러리아타임월드", "role": "자회사"},
        ],
        "relations": [
            {"source": "한화솔루션", "target": "한화갤러리아", "type": "spin_off", "detail": "2020년 합병 후 1년 5개월만에 분할"},
        ],
        "risks": [
            {"type": "financial", "description": "분할되는 한화갤러리아는 6,243억원의 금융채무가 제거되었으나, 한화솔루션에 남겨놓고 처리", "severity": "high"},
            {"type": "governance", "description": "한화투자증권 주식을 저가에 자회사에 매각 후 고가에 재매각하여 이익 이전 우려", "severity": "high"},
            {"type": "market", "description": "사드 여파 및 온라인 유통 급성장으로 매출 감소 및 적자 상황, 분할 후 독자 생존성 불확실", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/360",
        "title": "쪼들리던 디와이디, 삼부토건 인수자금 어디서 났나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-10-04",
        "summary": "DWD가 삼부토건 8% 지분을 320억원에 인수. 현금 부족 상황에서 CB 재판매를 통한 비정상적 자금 조달 의혹.",
        "entities": [
            {"type": "company", "name": "디와이디", "role": "인수자"},
            {"type": "company", "name": "삼부토건", "role": "피인수회사"},
            {"type": "person", "name": "이일준", "role": "대양D&A 회장"},
            {"type": "company", "name": "대양디엔아이", "role": "공동인수자"},
            {"type": "company", "name": "씨엔아이", "role": "공동인수자"},
            {"type": "company", "name": "와이즈퍼시픽홀딩스", "role": "중개자"},
            {"type": "company", "name": "웰바이오텍", "role": "자금원천 관련"},
        ],
        "relations": [
            {"source": "디와이디", "target": "삼부토건", "type": "acquisition", "detail": "8% 지분(800만주) 320억원에 인수"},
            {"source": "이일준", "target": "디와이디", "type": "control", "detail": "실질적 지배"},
        ],
        "risks": [
            {"type": "financial", "description": "DWD 2022년 3월 현금 10억원 미만에서 320억원 인수자금 출처 불명", "severity": "critical"},
            {"type": "governance", "description": "와이즈퍼시픽, JSTM 등 다수 페이퍼컴퍼니를 통한 불투명한 자금 흐름", "severity": "high"},
            {"type": "financial", "description": "대양D&A 완전 자본잠식(438억원 부채 vs 111억원 자산), 독자적 자금조달 불가", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/359",
        "title": "금강공업은 왜 자회사 대신 빚더미 기업 인수했나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-09-29",
        "summary": "금강공업이 삼미금속 69.4% 지분을 70억원에 인수. 원래 자회사 케이에스피가 추진하던 주식교환 방식이 금융감독원 반려로 무산.",
        "entities": [
            {"type": "company", "name": "금강공업", "role": "인수사"},
            {"type": "company", "name": "삼미금속", "role": "피인수회사"},
            {"type": "company", "name": "케이에스피", "role": "금강공업 자회사"},
            {"type": "company", "name": "코에프씨밸류업 PEF", "role": "전 최대주주"},
            {"type": "person", "name": "이범호", "role": "금강공업 대표"},
            {"type": "person", "name": "김경남", "role": "삼미금속 대표"},
        ],
        "relations": [
            {"source": "금강공업", "target": "삼미금속", "type": "acquisition", "detail": "69.4% 지분 인수, 케이에스피 구주 8.1% 지급"},
        ],
        "risks": [
            {"type": "financial", "description": "삼미금속의 차입금 의존도 51%(757억원), 현금유동성 1억원 미만, 4년 연속 적자", "severity": "critical"},
            {"type": "regulatory", "description": "원래 포괄적 주식교환 방식이 금융감독원 반복 반려로 무산, 인수 방식 변경", "severity": "high"},
            {"type": "governance", "description": "기존 소수주주들이 지분 매각 기회를 제외당하고 코에프씨밸류업만 단독 매각", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/358",
        "title": "디와이디 이일준과 옵트론텍 임지윤의 동거?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-09-26",
        "summary": "이일준(DWD)과 임지윤(옵트론텍)이 녹원씨엔아이에 동시 투자. 복잡한 지분 구조를 통한 공동 지배 의혹.",
        "entities": [
            {"type": "person", "name": "임지윤", "role": "옵트론텍 대표이사"},
            {"type": "person", "name": "이일준", "role": "대양산업개발 회장"},
            {"type": "company", "name": "옵트론텍", "role": "투자자"},
            {"type": "company", "name": "디와이디", "role": "관련회사"},
            {"type": "company", "name": "녹원씨엔아이", "role": "공동투자 대상"},
            {"type": "company", "name": "엠피대산", "role": "관련회사"},
            {"type": "company", "name": "웰바이오텍", "role": "관련회사"},
        ],
        "relations": [
            {"source": "옵트론텍", "target": "엠피대산", "type": "ownership", "detail": "최대출자자로 25.37% 지분 보유"},
            {"source": "임지윤", "target": "녹원씨엔아이", "type": "investment", "detail": "티알아이 투자조합을 통한 25.04% 최대주주"},
            {"source": "이일준", "target": "녹원씨엔아이", "type": "investment", "detail": "웰바이오텍을 통한 18.57% 2대주주"},
        ],
        "risks": [
            {"type": "governance", "description": "두 실질 주인이 동일 기업에 공동 투자하며 이해관계 충돌 가능성", "severity": "high"},
            {"type": "regulatory", "description": "관련회사 거래 및 계열사 거래 규제 대상 가능성", "severity": "high"},
            {"type": "financial", "description": "구조조정 투자조합을 통한 복잡한 소유구조로 실질 영향력 파악 곤란", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/357",
        "title": "녹원씨엔아이 인수, 동년배 3인의 의기투합?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-09-22",
        "summary": "티알인베스트먼트를 통한 녹원씨엔아이 인수는 임지윤, 조철, 이재선 등 동년배 3인의 협력. 각 회사가 경영 위기 상황에서 사업 통합 추진.",
        "entities": [
            {"type": "person", "name": "임지윤", "role": "옵트론텍 최대주주 겸 대표이사"},
            {"type": "person", "name": "조철", "role": "해화 前 최대주주"},
            {"type": "person", "name": "이재선", "role": "해성옵틱스 前 최대주주"},
            {"type": "person", "name": "김성우", "role": "녹원씨엔아이 대표이사"},
            {"type": "company", "name": "녹원씨엔아이", "role": "인수 대상"},
            {"type": "company", "name": "옵트론텍", "role": "광학부품 제조"},
            {"type": "company", "name": "해성옵틱스", "role": "액츄에이터 제조"},
            {"type": "company", "name": "해화", "role": "카메라모듈 부품 제조"},
            {"type": "company", "name": "티알인베스트먼트", "role": "투자회사"},
        ],
        "relations": [
            {"source": "임지윤", "target": "티알인베스트먼트", "type": "ownership", "detail": "95.74% 지분 보유"},
            {"source": "티알인베스트먼트", "target": "녹원씨엔아이", "type": "acquisition", "detail": "2022년 1월 최대주주로 등극"},
            {"source": "조철", "target": "해화", "type": "sale", "detail": "2022년 5월 276억원에 녹원씨엔아이에 매각"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 순환출자 및 간접소유 구조로 인한 실질 경영권 파악의 어려움", "severity": "high"},
            {"type": "financial", "description": "해화는 자본잠식 상태(순자산 음수), 해성옵틱스는 전년도 매출 73% 감소", "severity": "critical"},
            {"type": "governance", "description": "티알인베스트먼트의 순자산 마이너스(-18억원), 차입금 의존도 높음", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/356",
        "title": "상장폐지 위기 기업에 회사를 판다고?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-09-19",
        "summary": "녹원씨엔아이는 8년간 상장폐지 위기에 처한 좀비 기업. 최근 5년간 최대주주가 4번 바뀌었고, 티알아이 투자조합이 신규 최대주주가 되어 자본 확충.",
        "entities": [
            {"type": "company", "name": "녹원씨엔아이", "role": "상장폐지 위기 기업"},
            {"type": "company", "name": "티알아이 리스트럭처링 투자조합1호", "role": "신규 최대주주"},
            {"type": "company", "name": "웰바이오텍", "role": "전 최대주주"},
            {"type": "person", "name": "이일준", "role": "회장"},
            {"type": "person", "name": "조철", "role": "해화 대표이사"},
            {"type": "company", "name": "해화", "role": "피인수 비상장사"},
        ],
        "relations": [
            {"source": "티알아이 투자조합", "target": "녹원씨엔아이", "type": "ownership_change", "detail": "110억원 유상증자로 최대주주 변경"},
            {"source": "녹원씨엔아이", "target": "해화", "type": "acquisition", "detail": "276억원에 지분 100% 인수"},
        ],
        "risks": [
            {"type": "regulatory", "description": "8월 초 상장폐지 심의 결정, 15일 이내 이의신청 또는 상장폐지 확정", "severity": "critical"},
            {"type": "financial", "description": "10년간 단 1회만 흑자 기록, 최근 매출 급격한 감소", "severity": "critical"},
            {"type": "governance", "description": "최대주주 4회 변경, 조합원 정체 불명확, 최대주주 간 연관성 의심", "severity": "high"},
            {"type": "legal", "description": "횡령 및 배임 혐의 기록", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/355",
        "title": "행동주의 투자자인가, 벌처 투자자인가(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-09-15",
        "summary": "김성진 측이 법정관리 중인 충남방적의 경영권 인수를 위해 공개매수에 나섰으나, 법원의 M&A 허가와 SG그룹의 우수 인수제안으로 실패.",
        "entities": [
            {"type": "person", "name": "김성진", "role": "행동주의 투자자"},
            {"type": "company", "name": "충남방적", "role": "대상회사 (현 SG글로벌)"},
            {"type": "person", "name": "서호현", "role": "법정관리인"},
            {"type": "person", "name": "최태호", "role": "비앤피 인베스트먼트 공동대표"},
            {"type": "company", "name": "SG그룹", "role": "최종 인수사"},
        ],
        "relations": [
            {"source": "김성진", "target": "충남방적", "type": "attempted_acquisition", "detail": "총 86억6,532만원 규모 공개매수 (2회)"},
            {"source": "SG그룹", "target": "충남방적", "type": "acquisition", "detail": "989억원 유상증자 및 공개매수로 65.66% 지분확보"},
        ],
        "risks": [
            {"type": "governance", "description": "법정관리 중인 회사의 최대주주 지위가 경영권 행사를 보장하지 않음", "severity": "high"},
            {"type": "legal", "description": "김성진 측의 가처분 신청 기각 및 무효확인 소송 패소로 법적 분쟁 반복", "severity": "high"},
            {"type": "financial", "description": "매매내역 공시 미흡으로 실제 시세차익 규모 파악 불가능", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/354",
        "title": "행동주의 투자자인가, 벌처 투자자인가(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-09-13",
        "summary": "슈퍼개미 김성진씨의 투자 활동 분석. 극동건설 법정관리 졸업 주도 후 신일산업, 고려산업, 오양수산 등에서 단기 대량 매집 후 집중 매도 패턴.",
        "entities": [
            {"type": "person", "name": "김성진", "role": "개인투자자/슈퍼개미"},
            {"type": "company", "name": "극동건설", "role": "투자 대상"},
            {"type": "company", "name": "신일산업", "role": "투자 대상"},
            {"type": "company", "name": "고려산업", "role": "투자 대상"},
            {"type": "company", "name": "오양수산", "role": "투자 대상"},
            {"type": "company", "name": "한국금속공업", "role": "경영권 분쟁 대상"},
            {"type": "company", "name": "충남방적", "role": "경영권 인수 시도"},
            {"type": "person", "name": "이의범", "role": "SG그룹 창립자"},
        ],
        "relations": [
            {"source": "김성진", "target": "극동건설", "type": "investment", "detail": "1999년 6.88% → 17.8% 매집 후 2001년 4.19%로 감소"},
            {"source": "김성진", "target": "충남방적", "type": "attempted_acquisition", "detail": "2005년 매수 시작, 2006년 공개매수신고서 제출"},
        ],
        "risks": [
            {"type": "governance", "description": "회사정리계획안 변경 제안 후 법원 기각 예상 시점에 주식 매도 개시, 단기 차익 추구 의도", "severity": "high"},
            {"type": "market", "description": "극동건설 등에서 대량 매집 후 단기간 내 집중 매도로 주가 변동성 증가", "severity": "high"},
            {"type": "governance", "description": "충남방적 상장폐지 직전 매수 개시, 정보 이용 의혹", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/353",
        "title": "화천기계, 18년전 한국금속공업과 닮았다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-09-08",
        "summary": "김성진 투자자가 2004년 한국금속공업에 벌인 투쟁과 현재 화천기계 분쟁의 유사성 분석. 관계사와의 제조-판매 구조를 통해 지배되는 구도 지적.",
        "entities": [
            {"type": "person", "name": "김성진", "role": "행동주의 투자자"},
            {"type": "company", "name": "화천기계", "role": "투자 분쟁 대상"},
            {"type": "company", "name": "한국금속공업", "role": "과거 투자 대상"},
            {"type": "company", "name": "화천기공", "role": "관련 제조사"},
            {"type": "company", "name": "㈜한금", "role": "관련 제조사"},
        ],
        "relations": [
            {"source": "김성진", "target": "한국금속공업", "type": "investment_conflict", "detail": "2003-2004년 경영권 인수 시도, 22억원 투자 후 49억원 회수"},
            {"source": "화천기공", "target": "화천기계", "type": "business_relationship", "detail": "제조-판매 구조: 화천기공이 제조, 화천기계가 독점 판매"},
        ],
        "risks": [
            {"type": "governance", "description": "관계사 간 제조-판매 구조로 인한 지배구조 투명성 부족 및 의존성 심화", "severity": "high"},
            {"type": "financial", "description": "한국금속공업은 2009년 자본잠식으로 상장폐지, 화천기계도 유사 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/352",
        "title": "화천기공과 화천기계, 사실상 한 몸?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-09-05",
        "summary": "슈퍼개미 김성진의 화천기계 적대적 M&A 시도 분석. 화천기공의 34.54% 지분율로 인해 주요 의사결정 관철이 불가능한 구조.",
        "entities": [
            {"type": "company", "name": "화천기공", "role": "화천그룹 모태 회사"},
            {"type": "company", "name": "화천기계", "role": "상장사"},
            {"type": "person", "name": "권영열", "role": "화천그룹 회장"},
            {"type": "person", "name": "김성진", "role": "슈퍼개미, M&A 시도자"},
            {"type": "company", "name": "보아스에셋", "role": "김성진 회사"},
        ],
        "relations": [
            {"source": "권영열", "target": "화천기공", "type": "ownership", "detail": "48.78% 지분 보유"},
            {"source": "화천기공", "target": "화천기계", "type": "ownership", "detail": "34.54% 지분 보유 (특수관계자 포함)"},
            {"source": "화천기공", "target": "화천기계", "type": "business", "detail": "독점 공급 계약 (2021년 760억원)"},
        ],
        "risks": [
            {"type": "governance", "description": "화천기공의 34.54% 지분율로 인해 특별결의 사항 관철 불가능", "severity": "high"},
            {"type": "operational", "description": "독점공급계약 단절 시 화천기공 매출 1280억원→760억원 감소, 화천기계 매출 반 토막", "severity": "critical"},
            {"type": "market", "description": "양측 경영진 간 지속적인 이사회 주도권 투쟁으로 인한 운영 불안정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/351",
        "title": "끄렘드라끄렘과 합병은 화천기계 인수를 위한 포석이었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-09-01",
        "summary": "슈퍼개미 김성진씨가 보아스에셋과 원옥을 통해 화천기계 지분 10.433%를 약 70억원에 취득. 경영악화 중인 끄렘드라끄렘과 역합병 후 화천기계 M&A 시도.",
        "entities": [
            {"type": "person", "name": "김성진", "role": "슈퍼개미 투자자"},
            {"type": "company", "name": "보아스에셋", "role": "화천기계 주식 매수 주체"},
            {"type": "company", "name": "원옥", "role": "공동 매수 주체"},
            {"type": "company", "name": "끄렘드라끄렘", "role": "패션잡화 제조업체"},
            {"type": "company", "name": "화천기계", "role": "피인수 대상"},
        ],
        "relations": [
            {"source": "김성진", "target": "보아스에셋", "type": "ownership", "detail": "지분율 47.35%, 특수관계자 포함 76%"},
            {"source": "보아스에셋", "target": "끄렘드라끄렘", "type": "merger", "detail": "역합병을 통한 통합"},
            {"source": "보아스에셋", "target": "화천기계", "type": "acquisition", "detail": "지분 10.433% 취득, 약 70억원 투자"},
        ],
        "risks": [
            {"type": "governance", "description": "김성진의 특수관계자 지배구조로 의사결정의 독립성 부족", "severity": "high"},
            {"type": "financial", "description": "끄렘드라끄렘 인수 당시 111억원 결손금 및 47억원 적자 상황", "severity": "high"},
            {"type": "operational", "description": "끄렘드라끄렘의 주력 브랜드 '브비에' 2021년 10월 영업중단", "severity": "critical"},
            {"type": "legal", "description": "끄렘드라끄렘 신주발행금지 가처분 소송 및 노조·채권자와의 갈등", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/350",
        "title": "화천기계에 주당 3500원의 배당 여력 있을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-08-29",
        "summary": "화천기계에서 보아스에셋 대표 김성진씨의 경영권 분쟁으로 주당 3500원의 파격적 배당안 제시. 현금 부족으로 인해 차입이나 증자 없이는 실행 불가능.",
        "entities": [
            {"type": "company", "name": "화천기계", "role": "대상사"},
            {"type": "person", "name": "김성진", "role": "공격자 (보아스에셋 대표)"},
            {"type": "person", "name": "권영열", "role": "현 최대주주 및 회장"},
            {"type": "company", "name": "화천기공", "role": "화천기계 모회사"},
        ],
        "relations": [
            {"source": "김성진", "target": "화천기계", "type": "hostile_acquisition_attempt", "detail": "경영참여 목적 10% 이상 지분 취득 후 임시주주총회 소집"},
            {"source": "권영열", "target": "화천기계", "type": "ownership", "detail": "모회사 통해 34.54% 지분 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "주당 3500원 배당 실행 시 현금 부족으로 차입금 증가. 운영자금 부족 발생 가능", "severity": "critical"},
            {"type": "financial", "description": "부채비율이 29%에서 65% 이상으로 상승 가능성", "severity": "high"},
            {"type": "governance", "description": "경영권 분쟁으로 인한 지배구조 불안정성 및 경영진 교체 리스크", "severity": "high"},
            {"type": "operational", "description": "지난 10년간 매출 감소 추세(2011년 296억원 → 현재 약 150억원)로 성장동력 부족", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (23차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}... - {result.get('error', 'Unknown')}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
