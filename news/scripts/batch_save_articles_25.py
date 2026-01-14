#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 25차 (한화건설/BYC/더블유게임즈/삼부토건/휴림로봇 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/329",
        "title": "한화생명 지분, 한화건설에 계륭?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-06-20",
        "summary": "한화건설이 보유한 한화생명 지분(장부가액 2조2600억원)이 자산의 40%를 차지. 채권평가손실로 순자산 감소, 금리 상승으로 추가 손실 우려.",
        "entities": [
            {"type": "company", "name": "한화건설", "role": "피분석기업"},
            {"type": "company", "name": "한화생명", "role": "주요 투자 대상"},
            {"type": "company", "name": "한화", "role": "한화건설 모회사"},
        ],
        "relations": [
            {"source": "한화건설", "target": "한화생명", "type": "ownership", "detail": "장부가액 2조2601억원(총자산의 40%)"},
            {"source": "한화", "target": "한화건설", "type": "ownership", "detail": "보통주 100% 소유"},
        ],
        "risks": [
            {"type": "financial", "description": "한화생명 채권평가손실 2년 3개월간 1조원 이상, 순자산 감소", "severity": "critical"},
            {"type": "market", "description": "금리 상승으로 한화생명 보유 채권(75조원) 가격 하락 예상", "severity": "high"},
            {"type": "legal", "description": "지분 매각 시 국세청 부당행위 계산 부인 세금 부과 가능", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/328",
        "title": "한화건설 흡수합병, 한화생명 자본확충의 서막인가?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-06-16",
        "summary": "한화건설의 한화 흡수합병 가능성 분석. 한화생명 지급여력비율 하락과 IFRS 17 대비 자본확충 필요.",
        "entities": [
            {"type": "company", "name": "한화건설", "role": "합병 대상"},
            {"type": "company", "name": "한화", "role": "합병 주체"},
            {"type": "company", "name": "한화생명", "role": "자본확충 대상"},
            {"type": "company", "name": "한화손해보험", "role": "자회사"},
        ],
        "relations": [
            {"source": "한화건설", "target": "한화생명", "type": "ownership", "detail": "25.09% 최대주주"},
            {"source": "한화", "target": "한화생명", "type": "ownership", "detail": "18.15% 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "한화생명 지급여력비율 160%로 하락, 규제 우려", "severity": "high"},
            {"type": "regulatory", "description": "IFRS 17 도입(2025년)으로 보험사 재무 변동성 증가", "severity": "high"},
            {"type": "financial", "description": "한화건설 한화생명 지분 매각 시 1.7조원 손실 가능", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/327",
        "title": "한화건설, '부채 같은 자본' RCPS 상환 이유?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-06-13",
        "summary": "한화건설이 2014년 발행한 2,000억원 RCPS 전액 상환 결정. 한화 흡수합병 앞두고 유동화 프로그램 재구성 필요.",
        "entities": [
            {"type": "company", "name": "한화건설", "role": "발행사"},
            {"type": "company", "name": "한화", "role": "모회사"},
            {"type": "company", "name": "레콘", "role": "우선주 보유 SPC"},
        ],
        "relations": [
            {"source": "한화", "target": "한화건설", "type": "ownership", "detail": "보통주 100% 보유"},
            {"source": "레콘", "target": "한화건설", "type": "securities_holding", "detail": "RCPS 2,000억원(우선주 57.70%)"},
        ],
        "risks": [
            {"type": "governance", "description": "RCPS는 회계상 자본이지만 실질적으로 부채 같은 자본", "severity": "high"},
            {"type": "financial", "description": "현금 보유액(2,020억원)이 상환액과 유사, 추가 자금조달 필요", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/326",
        "title": "비와이씨의 내부거래, 줄고는 있는데...",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-06-07",
        "summary": "BYC 내부거래 분석. 1998년 1000억원에서 현재 약 100억원으로 감소했으나, 매출의 절반 이상 외주 의존.",
        "entities": [
            {"type": "company", "name": "비와이씨", "role": "주요 기업"},
            {"type": "person", "name": "한석범", "role": "회장"},
            {"type": "person", "name": "한승우", "role": "상무"},
            {"type": "company", "name": "신한방", "role": "계열사"},
            {"type": "company", "name": "트러스톤자산운용", "role": "투자사"},
        ],
        "relations": [
            {"source": "비와이씨", "target": "신한방", "type": "transaction", "detail": "1998년 502억원 하청 지급"},
        ],
        "risks": [
            {"type": "governance", "description": "다수 가족 계열사로 간접 관련당사자 거래 가능성", "severity": "high"},
            {"type": "financial", "description": "핵심 섬유 매출 2011년 1760억→2021년 1235억 감소", "severity": "medium"},
            {"type": "market", "description": "국내 속옷 시장 위축과 수입품 경쟁 심화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/325",
        "title": "비와이씨 계열의 복잡한 부동산 임대차 거래",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-06-02",
        "summary": "비와이씨 자산의 70% 이상이 건설/임대 부문. 연간 400억원 임대수익. 오너 일가 계열사 간 복잡한 임대차 관계.",
        "entities": [
            {"type": "company", "name": "비와이씨", "role": "주요 기업"},
            {"type": "company", "name": "신한에디피스", "role": "계열사"},
            {"type": "company", "name": "제원기업", "role": "세입자"},
            {"type": "company", "name": "비와이씨마트", "role": "세입자"},
            {"type": "person", "name": "한승우", "role": "신한에디피스 최대주주"},
            {"type": "person", "name": "한석범", "role": "신한방 100% 주주"},
        ],
        "relations": [
            {"source": "비와이씨", "target": "비와이씨마트", "type": "lease", "detail": "2021년 5.4억원 임차료"},
            {"source": "비와이씨", "target": "제원기업", "type": "lease", "detail": "50억원 임차보증금"},
        ],
        "risks": [
            {"type": "governance", "description": "오너 일가 계열사 간 복잡한 임대차 관계, 투명성 문제", "severity": "high"},
            {"type": "financial", "description": "임차보증금 960억원 규모, 반환 시 유동성 위험", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/324",
        "title": "판매담당 비비안마트도 한승우에게 승계될까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-05-30",
        "summary": "BYC 핵심 판매채널 비비안마트 분석. 2007년부터 수수료 기반 서비스 모델로 전환. 한승우 승계 여부 주목.",
        "entities": [
            {"type": "company", "name": "비와이씨", "role": "상장사"},
            {"type": "company", "name": "비비안마트", "role": "판매 자회사"},
            {"type": "person", "name": "한석범", "role": "창업자"},
            {"type": "person", "name": "한승우", "role": "승계자"},
            {"type": "company", "name": "한승홀딩스", "role": "지분 보유 회사"},
            {"type": "person", "name": "한서원", "role": "비비안마트 대표이사"},
        ],
        "relations": [
            {"source": "비와이씨", "target": "비비안마트", "type": "commission_sales", "detail": "수수료 매출 396억, 기타 103억"},
            {"source": "한석범", "target": "24개 가족회사", "type": "ownership", "detail": "복잡한 순환출자 구조"},
        ],
        "risks": [
            {"type": "governance", "description": "27개 가족회사 순환출자로 실소유 불명확, 이해충돌 우려", "severity": "high"},
            {"type": "financial", "description": "비비안마트 520억 매출 중 500억이 BYC 의존, 집중 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/323",
        "title": "한승우의 신한에디피스를 키운 8할은 아버지 회사였다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-05-27",
        "summary": "한승우 상무가 신한에디피스/한승홀딩스로 비와이씨 지분 32.6% 통제. 아버지 신한방/남호섬유로부터 자금/거래 지원.",
        "entities": [
            {"type": "person", "name": "한승우", "role": "신한에디피스 최대주주"},
            {"type": "person", "name": "한석범", "role": "신한방 회장"},
            {"type": "company", "name": "비와이씨", "role": "상장사"},
            {"type": "company", "name": "신한에디피스", "role": "지주회사"},
            {"type": "company", "name": "한승홀딩스", "role": "투자지주사"},
            {"type": "company", "name": "신한방", "role": "임대사업"},
            {"type": "company", "name": "남호섬유", "role": "섬유제조"},
        ],
        "relations": [
            {"source": "한승우", "target": "신한에디피스", "type": "ownership", "detail": "58.34% 지분"},
            {"source": "신한에디피스", "target": "비와이씨", "type": "ownership", "detail": "18.43% 지분"},
            {"source": "신한방", "target": "신한에디피스", "type": "transaction", "detail": "19억 상품 구매, 16억 대출"},
            {"source": "남호섬유", "target": "신한에디피스", "type": "financing", "detail": "53억원 대출 제공"},
        ],
        "risks": [
            {"type": "governance", "description": "순환적 지배구조로 소수주주 보호 부족", "severity": "high"},
            {"type": "operational", "description": "신한에디피스 매입의 83% 비와이씨, 매출의 50% 신한방 의존", "severity": "high"},
            {"type": "regulatory", "description": "지분 이동 경위 공시 통해 확인 불가, 투명성 부족", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/322",
        "title": "BYC의 지분은 어떻게 3세에게 넘어갔나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-05-23",
        "summary": "BYC 경영권이 한석범→한승우로 승계되는 과정. 남호섬유 5주 처분으로 신한에디피스가 최대주주로 변경.",
        "entities": [
            {"type": "company", "name": "비와이씨", "role": "대상 기업"},
            {"type": "company", "name": "신한에디피스", "role": "새 최대주주"},
            {"type": "company", "name": "남호섬유", "role": "기존 최대주주"},
            {"type": "person", "name": "한석범", "role": "회장"},
            {"type": "person", "name": "한승우", "role": "승계자"},
            {"type": "company", "name": "트러스톤자산운용", "role": "행동주의펀드"},
        ],
        "relations": [
            {"source": "남호섬유", "target": "신한에디피스", "type": "ownership_transfer", "detail": "2020년부터 지분 매각, 2021년 2월 완료"},
            {"source": "한승우", "target": "비와이씨", "type": "control", "detail": "32.61% 실질 지배력"},
        ],
        "risks": [
            {"type": "governance", "description": "5주 처분으로 최대주주 변경 공시, 실질 경영권 이전 은폐", "severity": "critical"},
            {"type": "regulatory", "description": "공시와 사업보고서 불일치 - 장내매도 vs 주식매수 기재", "severity": "high"},
            {"type": "financial", "description": "계열사 간 지분 매각으로 소액주주 이익 침해 우려", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/321",
        "title": "더블유게임즈, 5년 만에 나서는 M&A 방향은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-05-20",
        "summary": "더블유게임즈 2017년 DDI 인수 후 재무 부담 해소, 2021년 1,600억원 조달해 M&A 준비. P2E 스킬 게임 진출 목표.",
        "entities": [
            {"type": "company", "name": "더블유게임즈", "role": "주체 기업"},
            {"type": "company", "name": "더블다운인터액티브", "role": "자회사"},
            {"type": "company", "name": "스틱스페셜시츄에이션다이아몬드", "role": "2대주주"},
        ],
        "relations": [
            {"source": "더블유게임즈", "target": "더블다운인터액티브", "type": "ownership", "detail": "67% 지분 보유"},
        ],
        "risks": [
            {"type": "market", "description": "소셜카지노 시장 포화, 게임 인기 급락 위험", "severity": "high"},
            {"type": "operational", "description": "글로벌 시장점유율 7% 수준, 선도업체 대비 경쟁력 약화", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/320",
        "title": "부쩍 성장한 더블유게임즈, M&A가 '신의 한 수'였다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-05-12",
        "summary": "더블유게임즈 2017년 DDI 인수로 매출 3000억→6000억, 순이익률 11%→25% 성장. 코로나 특수와 40대 이상 고충성도 고객.",
        "entities": [
            {"type": "company", "name": "더블유게임즈", "role": "주요 기업"},
            {"type": "company", "name": "더블다운인터액티브", "role": "자회사"},
        ],
        "relations": [
            {"source": "더블유게임즈", "target": "더블다운인터액티브", "type": "acquisition", "detail": "2017년 유상증자, CB, BW 및 인수금융으로 인수"},
        ],
        "risks": [
            {"type": "market", "description": "코로나 엔데믹으로 오프라인 카지노 재개장 시 접속 감소 우려", "severity": "high"},
            {"type": "operational", "description": "소셜카지노 높은 변동성으로 실적 부침 가능", "severity": "high"},
            {"type": "regulatory", "description": "국내 사행성 게임 규제로 국내 시장 진출 불가", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/319",
        "title": "삼부토건 최대주주 휴스토리: 신오너? 구오너?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-05-09",
        "summary": "삼부토건, 에이치엔티, 휴스토리 간 복잡한 소유구조. 조성옥/조원일 부자 페이퍼컴퍼니 통한 실질 지배 의혹.",
        "entities": [
            {"type": "person", "name": "조성옥", "role": "삼부토건 전 회장"},
            {"type": "person", "name": "조원일", "role": "코디엠 실소유자 추정"},
            {"type": "company", "name": "삼부토건", "role": "대상 기업"},
            {"type": "company", "name": "코디엠", "role": "코스닥 상장사"},
            {"type": "company", "name": "에이치엔티", "role": "관련회사"},
            {"type": "company", "name": "휴스토리", "role": "삼부토건 주주"},
            {"type": "company", "name": "크레센", "role": "휴스토리 95.19% 소유"},
        ],
        "relations": [
            {"source": "조원일", "target": "코디엠", "type": "control", "detail": "코디엠바이오컨소시엄(60%) 통한 실질 지배"},
            {"source": "코디엠", "target": "이앤케이컨소시엄", "type": "ownership", "detail": "99% 지분 소유"},
            {"source": "크레센", "target": "휴스토리", "type": "ownership", "detail": "2018년부터 95.19% 지분"},
        ],
        "risks": [
            {"type": "governance", "description": "조 부자 다층 페이퍼컴퍼니로 실소유 은폐 의혹", "severity": "critical"},
            {"type": "legal", "description": "조원일 2021년 3월 에스모 주가조작으로 구속", "severity": "critical"},
            {"type": "financial", "description": "크레센 자본잠식(자산 1억, 부채 1.89억), 휴스토리 소유 자격 의문", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/318",
        "title": "휴림로봇 인수한 에이치엔티와 삼부토건 조성옥 회장의 관계는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-05-05",
        "summary": "한국전자가 에이치엔티 인수 후 휴림로봇 매수해 자율주행 사업 진출. 실제로는 삼부토건 경영권 접근 목적으로 분석.",
        "entities": [
            {"type": "company", "name": "에이치엔티", "role": "카메라모듈 제조사"},
            {"type": "company", "name": "한국전자", "role": "인수사"},
            {"type": "company", "name": "휴림로봇", "role": "피인수사"},
            {"type": "company", "name": "삼부토건", "role": "최종 타겟"},
            {"type": "person", "name": "조성옥", "role": "삼부토건 회장 (2019년 취임)"},
            {"type": "company", "name": "코디엠", "role": "이앤케이컨소시엄 모회사"},
        ],
        "relations": [
            {"source": "한국전자", "target": "에이치엔티", "type": "acquisition", "detail": "코아시아로부터 인수"},
            {"source": "에이치엔티", "target": "휴림로봇", "type": "acquisition", "detail": "6.62% 지분 획득"},
            {"source": "휴림로봇", "target": "삼부토건", "type": "ownership", "detail": "최대주주, 자산 4000억원"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 소유구조로 실질 지배/의사결정 불명확", "severity": "critical"},
            {"type": "operational", "description": "자율주행 자회사들 대규모 손실, 사업 실행력 의문", "severity": "critical"},
            {"type": "financial", "description": "MDI 2019년 59억 손실, UMO 8000만원 순적자", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/317",
        "title": "에이치엔티, 휴림로봇 인수 위한 도구였다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-05-02",
        "summary": "에이치엔티 2019년 베트남 법인 지분 매각 후 휴림로봇에 50억 투자해 최대주주. 1년 반 후 전량 처분해 85억 회수. 현재 상장폐지 위기.",
        "entities": [
            {"type": "company", "name": "에이치엔티", "role": "주요 기업"},
            {"type": "company", "name": "휴림로봇", "role": "피인수 기업"},
            {"type": "company", "name": "삼부토건", "role": "휴림로봇 자회사"},
            {"type": "company", "name": "한국전자", "role": "인수사"},
            {"type": "company", "name": "코아시아", "role": "전 최대주주"},
        ],
        "relations": [
            {"source": "에이치엔티", "target": "휴림로봇", "type": "investment", "detail": "50억 유상증자, 6.62% 지분 후 전량 처분"},
            {"source": "한국전자", "target": "에이치엔티", "type": "acquisition", "detail": "2019년 5월 266억원 무자본 M&A"},
        ],
        "risks": [
            {"type": "financial", "description": "매출 2019년 1000억→2021년 2억으로 붕괴", "severity": "critical"},
            {"type": "regulatory", "description": "감사의견 거절로 상장폐지 결정", "severity": "critical"},
            {"type": "governance", "description": "무자본 M&A 구조로 실질 의사결정자 불명확", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/316",
        "title": "휴림로봇의 삼부토건 최대주주 지위는 허울이었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-04-28",
        "summary": "휴림로봇(구 DST로봇) 2017년 삼부토건 인수 후 경영권 분쟁. 한국 경영진 우진에 지분 매각 추진, 최대주주 베이징링크선 반대.",
        "entities": [
            {"type": "company", "name": "휴림로봇", "role": "삼부토건 최대주주"},
            {"type": "company", "name": "삼부토건", "role": "피인수 기업"},
            {"type": "company", "name": "우진", "role": "경영권 인수 추진"},
            {"type": "company", "name": "베이징링크선", "role": "휴림로봇 최대주주"},
            {"type": "person", "name": "최명규", "role": "DST로봇 전 CEO"},
            {"type": "person", "name": "황만회", "role": "휴림홀딩스 CEO"},
        ],
        "relations": [
            {"source": "휴림로봇", "target": "삼부토건", "type": "ownership", "detail": "2017년 인수, 2018년 우진에 매각 추진"},
            {"source": "베이징링크선", "target": "휴림로봇", "type": "shareholder_conflict", "detail": "경영진 매각 계획 및 이사회 재편 반대"},
        ],
        "risks": [
            {"type": "governance", "description": "주주 교착으로 2018년 4~10월 주총 실패, 경영 분쟁 장기화", "severity": "critical"},
            {"type": "legal", "description": "보전처분/가처분 다수 신청, 재무기록 접근 관련 법적 분쟁", "severity": "high"},
            {"type": "operational", "description": "삼부토건 인수 후 최소한의 운영 관여, 2017년 재무제표 승인 2018년 11월", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/315",
        "title": "2018년 삼부토건 매각은 휴림로봇 이사회의 반란이었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-04-25",
        "summary": "디에스티로봇 2018년 5월 삼부토건 지분 매각 추진, 2020년 9월 계약 해지. 최대주주 베이징링크선과 경영진 갈등, 비선 경영 개입.",
        "entities": [
            {"type": "company", "name": "디에스티로봇", "role": "삼부토건 최대주주"},
            {"type": "company", "name": "삼부토건", "role": "경영권 분쟁 대상"},
            {"type": "company", "name": "베이징링크선", "role": "단독 최대주주"},
            {"type": "company", "name": "우진", "role": "지분 인수자"},
            {"type": "person", "name": "박금성", "role": "비선 경영 관여자"},
            {"type": "person", "name": "김진우", "role": "회장 사칭"},
            {"type": "person", "name": "리밍", "role": "리드드래곤 회장"},
        ],
        "relations": [
            {"source": "베이징링크선", "target": "디에스티로봇", "type": "ownership", "detail": "단독 최대주주 5%대"},
            {"source": "디에스티로봇", "target": "삼부토건", "type": "ownership", "detail": "15.36% 지분, 288만주 매각 결정"},
        ],
        "risks": [
            {"type": "governance", "description": "이사회 공회전 상태, 정체불명 비선 인물들 경영 지배", "severity": "critical"},
            {"type": "legal", "description": "박금성 '전설의 금융브로커' - 이용호게이트, 굿모닝시티 연루, 2006년 구속", "severity": "high"},
            {"type": "financial", "description": "베이징링크선 실체 논란, 디신통그룹 핵심 계열사 실상 미확인", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/314",
        "title": "휴림로봇의 삼부토건 인수 자금 출처는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-04-21",
        "summary": "DST로봇 2017년 삼부토건 인수 시 현금 30억원뿐. 2~9월 CB/유상증자로 370억 조달. 대부분 FI 이후 철수.",
        "entities": [
            {"type": "company", "name": "휴림로봇", "role": "삼부토건 인수사"},
            {"type": "company", "name": "삼부토건", "role": "피인수 기업"},
            {"type": "company", "name": "베이징링크선", "role": "최대주주 7.8%"},
            {"type": "company", "name": "리드드래곤", "role": "주주 4.4%"},
            {"type": "person", "name": "리밍", "role": "리드드래곤 대표"},
            {"type": "company", "name": "제이에이치홀딩스", "role": "CB 투자자"},
            {"type": "company", "name": "무궁화신탁", "role": "컨소시엄 지원"},
        ],
        "relations": [
            {"source": "DST로봇", "target": "삼부토건", "type": "acquisition", "detail": "2017년 9월 2000억 컨소시엄 인수"},
            {"source": "베이징링크선", "target": "DST로봇", "type": "ownership", "detail": "400억 CB로 7.8% 취득"},
            {"source": "제이에이치홀딩스", "target": "DST로봇", "type": "financing", "detail": "300억 유상증자, 200억 CB"},
        ],
        "risks": [
            {"type": "governance", "description": "베이징링크선 등 외국인 투자자 소유구조/자금 출처 불명확", "severity": "high"},
            {"type": "financial", "description": "현금 30억으로 대형 인수, 복잡한 CB 구조 의존", "severity": "high"},
            {"type": "operational", "description": "대부분 FI 12~18개월 내 이탈, 전략적 투자 아닌 일시적 참여", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/313",
        "title": "휴림로봇의 삼부토건 인수를 도운 조력자는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-04-18",
        "summary": "대덕뉴비즈1~3호, SR투자조합 등이 DST로봇의 삼부토건 인수 촉진. 베이징링크선/리드드래곤 M&A 전 전략적 지분 이전.",
        "entities": [
            {"type": "company", "name": "휴림로봇", "role": "삼부토건 인수사"},
            {"type": "company", "name": "삼부토건", "role": "피인수 기업"},
            {"type": "company", "name": "디에스티로봇", "role": "인수 주체"},
            {"type": "company", "name": "베이징링크선", "role": "초기 최대주주"},
            {"type": "company", "name": "리드드래곤", "role": "공동 투자자"},
            {"type": "company", "name": "대덕뉴비즈1~3호", "role": "핵심 촉진자"},
            {"type": "person", "name": "리밍", "role": "리드드래곤 100% 소유"},
        ],
        "relations": [
            {"source": "베이징링크선", "target": "디에스티로봇", "type": "ownership", "detail": "28.20%(2015년)→7.14%(2017년) 단계적 매각"},
            {"source": "대덕뉴비즈", "target": "디에스티로봇", "type": "ownership", "detail": "약 20% 지분(152백만주) 950억원에 취득"},
        ],
        "risks": [
            {"type": "governance", "description": "투자조합 통한 지분 이전, 실소유/의사결정 은폐 구조", "severity": "high"},
            {"type": "financial", "description": "베이징링크선 1000억 투자 후 1.5년 내 1290억 회수, 지속불가능 가치", "severity": "high"},
            {"type": "operational", "description": "AITEC 자회사 $1에 베이징링크선 매각, 28억 대출 30억 대손처리", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/312",
        "title": "무궁화신탁은 왜 휴림로봇의 삼부토건 인수를 도왔나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-04-14",
        "summary": "무궁화신탁이 고위 금융 관료들과 연계되어 르네상스호텔 매각과 디에스티로봇의 삼부토건 인수에 관여. 펀드 조성과 지분 이전 투명성 부족.",
        "entities": [
            {"type": "company", "name": "무궁화신탁", "role": "삼부토건 인수 자금 제공"},
            {"type": "person", "name": "이용만", "role": "무궁화신탁 전 최대주주/회장"},
            {"type": "person", "name": "오창석", "role": "무궁화신탁 부회장/신규 최대주주"},
            {"type": "company", "name": "디에스티글로벌PEF", "role": "삼부토건 지분 인수 펀드"},
            {"type": "company", "name": "제이스톤파트너스", "role": "PEF 운용사"},
            {"type": "company", "name": "VSL코리아", "role": "르네상스호텔 매입"},
            {"type": "person", "name": "조남원", "role": "삼부토건 부회장"},
        ],
        "relations": [
            {"source": "무궁화신탁", "target": "디에스티글로벌PEF", "type": "investment", "detail": "102억원 출자"},
            {"source": "오창석", "target": "무궁화신탁", "type": "ownership_transfer", "detail": "2016년 7~8월 최대주주 지분 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "투자 결정 후 자금 선집행, 사후 이사회 승인 절차 부재", "severity": "high"},
            {"type": "regulatory", "description": "무궁화신탁 지각 보고로 2018년 금감원 징계", "severity": "high"},
            {"type": "legal", "description": "고위 금융 관료(이용만, 이팔성, 권혁세) 연루, 이해충돌 우려", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/311",
        "title": "삼부토건 인수한 한국자본과 중국자본의 이상한 조합",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-04-11",
        "summary": "삼부토건 2017년 법정관리 중 DST로봇 컨소시엄에 인수. 한국 투자자 6개월 내 철수, 중국 히어로스카이인베스트먼트 잔류.",
        "entities": [
            {"type": "company", "name": "삼부토건", "role": "법정관리 대상"},
            {"type": "person", "name": "조남욱", "role": "전 회장/최대주주"},
            {"type": "company", "name": "디에스티로봇", "role": "인수 컨소시엄 주도"},
            {"type": "company", "name": "베이징링크선", "role": "DST로봇 최대주주 28.2%"},
            {"type": "company", "name": "히어로스카이인베스트먼트", "role": "중국 투자자 3.84%"},
            {"type": "company", "name": "무궁화신탁", "role": "DST글로벌 펀드 조성"},
            {"type": "company", "name": "우진", "role": "DST 컨소시엄 자산 인수"},
        ],
        "relations": [
            {"source": "베이징링크선", "target": "디에스티로봇", "type": "ownership", "detail": "2015년 인수 후 28.2% 최대주주"},
            {"source": "디에스티로봇", "target": "삼부토건", "type": "acquisition", "detail": "2017년 6000억 컨소시엄 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "창업자 조남욱 법정관리에도 간접 지배 유지 의혹", "severity": "high"},
            {"type": "governance", "description": "창업자와 특관자 파산신청 전 지분 청산, 내부정보 악용 의혹", "severity": "critical"},
            {"type": "operational", "description": "노조 갈등으로 인수 컨소시엄 6개월 내 철수", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/310",
        "title": "삼부토건, 미등기 임원이 왜 많을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-04-07",
        "summary": "삼부토건 미등기 임원 51명(전직원 340명의 15%). 회생절차 이후 최대주주 변경과 경영권 분쟁 시기에 급증.",
        "entities": [
            {"type": "company", "name": "삼부토건", "role": "대상 기업"},
            {"type": "company", "name": "디에스티로봇", "role": "2017년 인수사"},
            {"type": "company", "name": "우진", "role": "지분 인수자"},
            {"type": "person", "name": "이응근", "role": "대표이사"},
            {"type": "company", "name": "이화전기", "role": "이아이디 최대주주"},
        ],
        "relations": [
            {"source": "디에스티로봇", "target": "삼부토건", "type": "acquisition", "detail": "2017년 9월 회생절차 중 인수"},
            {"source": "우진", "target": "삼부토건", "type": "shareholder", "detail": "2018~2019년 주요 주주"},
        ],
        "risks": [
            {"type": "governance", "description": "경영권 공백 상태에서 미등기 임원 51명 실질 영향력 행사", "severity": "high"},
            {"type": "governance", "description": "최대주주 3회 이상 변경, 지배구조 불안정", "severity": "high"},
            {"type": "legal", "description": "2018년 경영권 분쟁 소송 공방, 이사회 구성 분쟁", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (25차) ===\n")

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
