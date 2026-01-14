#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 16차 (누락 기사: 두산/삼성전자/풀무원/SK/넷마블)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/581",
        "title": "기업가치 평가, 코에 걸면 코걸이 귀에 걸면 귀걸이?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-12-02",
        "summary": "두산그룹의 두산밥캣 인적분할-합병 밸류에이션 방법론 비판. 자산/이익가치에 경영권 프리미엄 선택적 적용으로 불공정 가격 형성.",
        "entities": [
            {"type": "company", "name": "두산그룹", "role": "모회사/구조조정 주체"},
            {"type": "company", "name": "두산에너빌리티", "role": "거래조건 불리 주주"},
            {"type": "company", "name": "두산밥캣", "role": "분할 대상 현금창출 자산"},
            {"type": "company", "name": "두산로보틱스", "role": "합병 인수 주체"},
            {"type": "company", "name": "금융감독원", "role": "규제기관"},
        ],
        "relations": [
            {"source": "두산에너빌리티", "target": "두산밥캣", "type": "spin-off", "detail": "인적분할"},
        ],
        "risks": [
            {"type": "governance", "description": "이익가치에만 경영권 프리미엄 적용, 자산가치 미적용 - 밸류에이션 불일치", "severity": "high"},
            {"type": "financial", "description": "분할구조로 자산매각 대비 약 4000억원 주주가치 감소", "severity": "high"},
            {"type": "regulatory", "description": "투명성 요구에도 감독기관 일관적 자본시장법 적용 실패", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/580",
        "title": "삼성전자 현금의 대부분은 왜 해외에 있을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-11-28",
        "summary": "삼성전자 연결 현금 104조원 중 본사 17조원만 보유. 해외 자회사(베트남 등) 대규모 설비투자/배당 부담 없어 자금 축적.",
        "entities": [
            {"type": "company", "name": "삼성전자", "role": "한국 본사"},
            {"type": "company", "name": "삼성디스플레이", "role": "국내 자회사"},
            {"type": "company", "name": "SAPL", "role": "베트남 생산 자회사"},
            {"type": "company", "name": "SEVT", "role": "베트남 생산 자회사"},
            {"type": "person", "name": "이건희", "role": "전 회장 (사망)"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "구조적 유동성 불균형 - 본사 외부금융 필요, 해외자회사 미사용 자본 축적, 연간 100조원 자금필요 전망", "severity": "high"},
            {"type": "governance", "description": "본사가 운영자금 조달에 자회사 배당에 점점 의존, 약속 배당성향(50%)과 운영현금 간 정책 긴장", "severity": "high"},
            {"type": "regulatory", "description": "2023년 세법 개정으로 해외자회사 배당 면제 폐지, 베트남 등 세제혜택 향후 규제 변화 가능성", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/579",
        "title": "10조원 플렉스, 담대한 혹은 대담한",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-11-25",
        "summary": "삼성전자 10조원 자사주 매입 발표에도 재무상태 악화. 개별 현금 30조원→16조원 감소, 적정 수준 50조원 추정 대비 부족.",
        "entities": [
            {"type": "company", "name": "삼성전자", "role": "자사주 매입 발표"},
            {"type": "company", "name": "삼성디스플레이", "role": "긴급대출 제공 자회사 (22조원)"},
            {"type": "company", "name": "우리은행", "role": "담보대출 제공 (4조원)"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "현금보유액 부족 (16조원 vs 50조원 기준) - 운영/투자/부채상환 대응 어려움", "severity": "critical"},
            {"type": "operational", "description": "영업현금흐름 감소, 핵심사업 대신 자회사 배당에 의존", "severity": "high"},
            {"type": "financial", "description": "1년 내 리파이낸싱 필요한 단기부채 32.7조원 부담", "severity": "high"},
            {"type": "market", "description": "반도체 경쟁력 약화, 자회사 실적 악화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/573",
        "title": "안진회계법인의 경영권프리미엄 반영, 이상하지 않나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-11-07",
        "summary": "안진회계법인의 두산로보틱스 분할합병 밸류에이션 불규칙성 분석. 금감원 DCF 방법론 지시 거부, 이익가치에만 43.71% 경영권프리미엄 적용 - 약 6000억원 합병대가 추가 발생.",
        "entities": [
            {"type": "company", "name": "두산그룹", "role": "거래 주관 모기업"},
            {"type": "company", "name": "두산로보틱스", "role": "분할 주체, 2023년 안진으로 감사인 변경"},
            {"type": "company", "name": "두산에너빌리티", "role": "합병 상대방/두산밥캣 지분 보유"},
            {"type": "company", "name": "두산밥캣", "role": "밸류에이션 분쟁 핵심 자산"},
            {"type": "company", "name": "안진회계법인", "role": "외부평가인/동시에 두산로보틱스 감사인"},
        ],
        "relations": [],
        "risks": [
            {"type": "governance", "description": "안진이 동일 거래에서 감사인과 평가인 겸임 - 이해충돌/두산로보틱스 편향 가능성", "severity": "critical"},
            {"type": "regulatory", "description": "안진이 금감원 현금흐름할인 방법론 지시 2회 거부 - 자본시장법 위반", "severity": "critical"},
            {"type": "financial", "description": "이익가치에만 경영권프리미엄 43.71% 적용으로 합병대가 약 6000억원 과대계상", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/572",
        "title": "두산밥캣 분할로 두산에너빌리티 재무개선?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-11-04",
        "summary": "두산에너빌리티의 두산밥캣 지분을 두산로보틱스와 합병하기 위한 분할 계획 비판적 분석. 경영진은 재무건전성 개선 주장, 실제로는 대차대조표 악화.",
        "entities": [
            {"type": "company", "name": "두산에너빌리티", "role": "자산 분할 모회사"},
            {"type": "company", "name": "두산밥캣", "role": "건설장비 자회사 (지분 46.11%, 가치 약 3.36조원)"},
            {"type": "company", "name": "두산로보틱스", "role": "현 매출 미미한 인수 주체"},
            {"type": "company", "name": "금융감독원", "role": "공시 해명 요청 규제기관"},
            {"type": "person", "name": "박지원", "role": "두산에너빌리티 회장/대표/이사회 의장, 두산그룹 부회장"},
        ],
        "relations": [
            {"source": "두산에너빌리티", "target": "두산밥캣", "type": "spin-off", "detail": "인적분할 계획"},
        ],
        "risks": [
            {"type": "financial", "description": "분할구조로 재무개선 아닌 순자산 2.5조원+ 감소", "severity": "high"},
            {"type": "governance", "description": "이사회 의장=대표=지배주주 대리인, 반대 이사회 결의 없음", "severity": "critical"},
            {"type": "regulatory", "description": "금감원 거래 근거 해명 요구, 주주 반대로 거래계약 해지", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/571",
        "title": "두산에너빌리티 경영진은 누구의 편일까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-11-01",
        "summary": "두산로보틱스와 두산에너빌리티 분할합병을 2021년 두산인프라코어 구조조정과 비교 분석. 매출 50%+, 영업이익 95% 창출 두산밥캣의 현금보상 없는 이전에 의문.",
        "entities": [
            {"type": "company", "name": "두산에너빌리티", "role": "분할합병 제안 모회사"},
            {"type": "company", "name": "두산로보틱스", "role": "인수 대상"},
            {"type": "company", "name": "두산밥캣", "role": "자회사 (지분 51.05%), 핵심 현금창출원"},
            {"type": "company", "name": "두산인프라코어", "role": "HD현대에 매각된 전신"},
        ],
        "relations": [],
        "risks": [
            {"type": "governance", "description": "경영진이 소수주주보다 그룹 이익 우선시한 자산이전 구조", "severity": "high"},
            {"type": "financial", "description": "직접 보상 없이 핵심 현금창출 자회사 상실로 유동성/과거 수익 회복 계획 위협", "severity": "critical"},
            {"type": "regulatory", "description": "금융감독당국 반복 수정 요청, 밸류에이션 불일치 지속", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/554",
        "title": "지주회사 풀무원의 아찔한 재무정책",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-09-09",
        "summary": "31개 자회사 보유 순수지주회사 풀무원, 자회사 배당보다 이자비용 증가 속도 빨라 재무압박. 부채 1.568조원+하이브리드증권 2.4조원, 현금 21억원만 보유.",
        "entities": [
            {"type": "company", "name": "풀무원", "role": "지주회사"},
            {"type": "company", "name": "풀무원식품", "role": "최대 자회사"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "이자비용 연간 1000억원 접근 vs 배당수익 약 1100억원, 리파이낸싱 시장 경색 시 유동성 위기", "severity": "critical"},
            {"type": "operational", "description": "연간 부채구조조정 의존, 1년 내 만기 부채 1.176조원 - 지속적 롤오버 압박", "severity": "high"},
            {"type": "market", "description": "의무적 리파이낸싱 기간 중 신용시장 급변 취약, 자회사 실적 정체로 수익성장 제한", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/553",
        "title": "풀무원 그룹의 차입금 돌려 막기",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-09-05",
        "summary": "풀무원그룹 2024년 6월 기준 총차입금 1.2조원 사상 최대. 5.5년간 누적 영업이익 2359억원에도 이자비용 약 2500억원으로 순손실 122억원.",
        "entities": [
            {"type": "company", "name": "풀무원", "role": "지주회사/모기업"},
            {"type": "company", "name": "풀무원식품", "role": "최대 자회사"},
            {"type": "company", "name": "풀무원USA", "role": "미국 자회사"},
            {"type": "company", "name": "풀무원푸드앤컬처", "role": "급식 자회사"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "부채비율 56%, 유동성 제한(현금 1220억원), 단기차입 위주 - 연간 만기부채 리파이낸싱 강제", "severity": "critical"},
            {"type": "operational", "description": "국내 식품사업 매출 전년 대비 감소(7.78조원 vs 8.01조원), 성장은 불확실한 미국시장 확대에 의존", "severity": "high"},
            {"type": "market", "description": "신용 위축 또는 금융위기 시 리파이낸싱 접근 차단 - 유동성 위기 촉발 가능", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/551",
        "title": "합병비율 산정, 애당초 기울어진 운동장?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-08-30",
        "summary": "두산그룹의 두산밥캣(수익성 자회사) 두산에너빌리티→두산로보틱스 분할합병 이전 계획 분석. 합병비율 0.1275856이 에너빌리티 주주에 불리하게 산정.",
        "entities": [
            {"type": "company", "name": "두산그룹", "role": "구조조정 주관 지주회사"},
            {"type": "company", "name": "두산에너빌리티", "role": "두산밥캣 현 소유주/불리한 거래조건"},
            {"type": "company", "name": "두산로보틱스", "role": "유리한 밸류에이션 조건 인수회사"},
            {"type": "company", "name": "두산밥캣", "role": "이전 대상 수익성 현금창출 자회사"},
        ],
        "relations": [
            {"source": "두산에너빌리티", "target": "두산밥캣", "type": "spin-off", "detail": "두산로보틱스 합병 위한 분할"},
        ],
        "risks": [
            {"type": "governance", "description": "합병비율 산정이 인수자 유리, 에너빌리티→로보틱스 주주가치 이전", "severity": "critical"},
            {"type": "financial", "description": "밥캣 본질가치(약 3.8-4.6조원)가 배정가치(1.6조원) 크게 초과 - 상당한 저평가", "severity": "critical"},
            {"type": "regulatory", "description": "현행 자본시장법이 상장-비상장 합병에 자산기준 밸류에이션 허용", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/550",
        "title": "회사와 주주의 이익은 뒷전?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-08-26",
        "summary": "두산에너빌리티의 두산밥캣 인적분할이 에너빌리티 주주보다 모회사 (주)두산 이익 우선시 비판. 영업이익 1조원+ 밥캣을 친환경에너지 투자용 현금매각 대신 주식배분.",
        "entities": [
            {"type": "company", "name": "두산에너빌리티", "role": "2020년 이후 주주 유상증자 수혜 모회사"},
            {"type": "company", "name": "주두산", "role": "분할구조 주수혜 지주회사"},
            {"type": "company", "name": "두산밥캣", "role": "자회사, 연간 영업이익 1조원+, 분할 대상"},
            {"type": "company", "name": "두산로보틱스", "role": "주식교환 인수회사"},
            {"type": "company", "name": "기업은행", "role": "긴급자금 제공 (2020)"},
        ],
        "relations": [],
        "risks": [
            {"type": "governance", "description": "인적분할이 소수주주 가치극대화보다 지배주주 이익 우선", "severity": "high"},
            {"type": "financial", "description": "가장 수익성 높은 현금창출 자산 상실, 상응 현금유입 없이 부채 7200억원 이전", "severity": "high"},
            {"type": "operational", "description": "명시된 친환경에너지 투자(SMR, 가스터빈) 재원 능력 감소", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/549",
        "title": "두산에너빌리티 주식분할이 주주에 불리한 이유",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-08-22",
        "summary": "두산그룹의 두산밥캣 두산에너빌리티 분할이 소수주주에 불공정 주장. 분할비율 0.25(25%)가 실제 사업기여도 아닌 장부가치 기준 - 밥캣이 영업이익 80%+ 기여에도 자산 25%만 분리.",
        "entities": [
            {"type": "company", "name": "두산그룹", "role": "모회사, 에너빌리티 지분 30.39%"},
            {"type": "company", "name": "두산에너빌리티", "role": "상장 자회사, 소수주주 69.33%"},
            {"type": "company", "name": "두산밥캣", "role": "에너빌리티 이익 대부분 창출 운영 자회사"},
            {"type": "company", "name": "두산로보틱스", "role": "상장 자회사, 합병 상대방"},
            {"type": "person", "name": "이복현", "role": "금융감독원장, 지배주주 관행 비판"},
        ],
        "relations": [],
        "risks": [
            {"type": "governance", "description": "자산 밸류에이션 방법론으로 소수주주 이익이 지배가문 이익에 종속", "severity": "critical"},
            {"type": "financial", "description": "분할비율(0.25)이 밥캣의 수익성 기여 저평가, 소수주주 불균형 저지분 수령", "severity": "high"},
            {"type": "regulatory", "description": "현행 프레임워크가 경제가치/이익기여 아닌 장부가치 회계로 분할비율 결정 허용", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/548",
        "title": "두산로보틱스 성장이 예상 범위를 벗어났다?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-08-19",
        "summary": "두산그룹 미래성장동력 협동로봇 두산로보틱스가 IPO 전망 크게 하회. 2024년 영업이익 370억원 전망 vs Q1 2024 손실 690억원 - 두산밥캣 합병으로 재무안정/스마트기계 지주회사 구축 추진.",
        "entities": [
            {"type": "company", "name": "두산그룹", "role": "모기업"},
            {"type": "company", "name": "두산로보틱스", "role": "협동로봇 제조, 2023년 10월 상장"},
            {"type": "company", "name": "두산밥캣", "role": "중장비 자회사, 주수익원"},
            {"type": "company", "name": "두산에너지앤모빌리티", "role": "핵심 산업사업"},
        ],
        "relations": [],
        "risks": [
            {"type": "market", "description": "협동로봇 시장이 광의 로봇시장보다 훨씬 작음, 2030년 글로벌 코봇 시장 99억달러 전망", "severity": "high"},
            {"type": "operational", "description": "Q1 2024 매출 109억원 횡보, 규모화 기대에도 영업손실 확대", "severity": "critical"},
            {"type": "financial", "description": "IPO 밸류에이션 가정이 미실현 수익성 목표 의존, 2026년 순이익 9420억원 전망 의문", "severity": "high"},
            {"type": "governance", "description": "두산밥캣 합병이 재무통합으로 로보틱스 부진 은폐 목적 추정", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/547",
        "title": "SK이노베이션 주주에게 가장 불리한 합병비율",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-08-15",
        "summary": "SK이노베이션-SK이엔에스 합병비율 1.19 분석, 다른 밸류에이션 방법론 대안 비교. 상환전환우선주 밸류에이션 가정이 밸류에이션 구성요소 간 불일치 적용.",
        "entities": [
            {"type": "company", "name": "SK이노베이션", "role": "합병 상장 모회사"},
            {"type": "company", "name": "SK이엔에스", "role": "합병 비상장 자회사"},
            {"type": "company", "name": "SK그룹", "role": "합병 총괄 지주회사"},
            {"type": "company", "name": "KKR", "role": "전환우선주 보유 글로벌 PE"},
            {"type": "company", "name": "한영회계법인", "role": "외부 밸류에이션 평가인"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "SK이엔에스", "type": "merger", "detail": "합병 (비율 1.19)"},
        ],
        "risks": [
            {"type": "governance", "description": "우선주 상환 가정이 자산/이익 밸류에이션 간 불일치 적용 - 불일관적 방법론", "severity": "high"},
            {"type": "financial", "description": "현 합병비율 1.19가 SK이노베이션 주주에 불리, 대안 비율 1.13 또는 1.06이 더 유리", "severity": "high"},
            {"type": "regulatory", "description": "자본시장법 제약으로 상장-비상장 합병 밸류에이션 방법 옵션 제한", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/546",
        "title": "SK이엔에스 합병가액이 이상한 이유",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-08-12",
        "summary": "SK이노베이션과 SK이엔에스 합병 밸류에이션 방법론 비판. 이익가치(주당 168,262원) 대신 자산가치(주당 133,947원) 사용으로 비상장 자회사 저평가, 우선주 처리 불일치.",
        "entities": [
            {"type": "company", "name": "SK이노베이션", "role": "합병 인수자"},
            {"type": "company", "name": "SK이엔에스", "role": "합병 피인수 대상"},
            {"type": "company", "name": "KKR", "role": "가스유틸리티 자회사 인수 협상 글로벌 PE"},
            {"type": "company", "name": "SK그룹", "role": "지주회사"},
            {"type": "person", "name": "김지원", "role": "SK이노베이션 CFO"},
            {"type": "person", "name": "박상규", "role": "SK이엔에스 사장"},
        ],
        "relations": [],
        "risks": [
            {"type": "governance", "description": "밸류에이션 방법 간 우선주 처리 상이 - 소수주주 불리 가능성", "severity": "high"},
            {"type": "financial", "description": "합병 밸류에이션이 이익기준 접근법보다 낮은 주당가격 산출", "severity": "high"},
            {"type": "operational", "description": "11월 합병 완료 전 압축된 일정 내 우선주 상환 조건부 자산매각", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/545",
        "title": "휴림로봇의 이큐셀 인수철회, 무리없이 이루어질까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-08-08",
        "summary": "코스닥 산업용로봇 휴림로봇이 이큐셀 1조원 인수 추진 후 대상 상장폐지로 철회. 기투자 230억원 회수 불확실, 자본금등록 절차 완료 시 환불협상과 주주 재무리스크 노출.",
        "entities": [
            {"type": "company", "name": "휴림로봇", "role": "코스닥 인수자"},
            {"type": "company", "name": "이큐셀", "role": "코스닥 상장폐지 인수대상"},
            {"type": "company", "name": "이화그룹", "role": "이큐셀 모회사"},
            {"type": "company", "name": "이화전기", "role": "이큐셀 지분 매각 주주"},
            {"type": "company", "name": "삼부토건", "role": "휴림로봇 전 계열사"},
        ],
        "relations": [
            {"source": "휴림로봇", "target": "이큐셀", "type": "failed_acquisition", "detail": "1조원 인수 철회"},
        ],
        "risks": [
            {"type": "financial", "description": "230억원 자본투자 회수 불확실, 약 1조원 유동성 운용계획 불명확", "severity": "high"},
            {"type": "legal", "description": "자본금등록 분쟁으로 환불 방해 가능, 자금 미회수 시 주주소송 가능", "severity": "high"},
            {"type": "governance", "description": "지속적 영업손실에도 인수 중심 전략, 투자이익으로 취약한 운영실적 은폐", "severity": "high"},
            {"type": "operational", "description": "지능형로봇 표방에도 시설 설비투자 최소, 2018년 이후 핵심사업 적자", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/544",
        "title": "SK그룹, 도시가스업 포기 방침 세웠나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-08-06",
        "summary": "SK그룹이 SK이노베이션 재무안정 위해 SK이엔에스 합병 승인. 신용등급 하락/배터리 투자 부담 속 합병 밸류에이션 방법론 공정성 우려, 우선주 상환 위한 도시가스 자산 청산 가능성.",
        "entities": [
            {"type": "company", "name": "SK이노베이션", "role": "재무압박 상장 배터리/에너지"},
            {"type": "company", "name": "SK이엔에스", "role": "도시가스 운영 비상장 자회사"},
            {"type": "company", "name": "SK주식회사", "role": "지주회사, SK이노베이션 지분 36.2%"},
            {"type": "company", "name": "S&P글로벌", "role": "2024년 3월 SK이노베이션 BB+로 강등 신용평가사"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "SK이엔에스", "type": "merger", "detail": "재무안정 목적 합병"},
        ],
        "risks": [
            {"type": "financial", "description": "S&P 투기등급(BB+) 강등으로 자본접근 제약, 지속적 대규모 설비투자 필요(잔여 14조원+) 유동성 압박", "severity": "critical"},
            {"type": "governance", "description": "합병 밸류에이션 방법론 괴리(시가 vs 본질가치)로 소수주주 약 8.4% 지분희석 불이익", "severity": "high"},
            {"type": "operational", "description": "우선주 상환의무(3.1조원) 위한 도시가스 자회사 강제청산 가능 - 핵심 현금창출 사업 위협", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/537",
        "title": "합병비율 숨겨진 쟁점②, SK이엔에스의 불편한 현금흐름",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-07-11",
        "summary": "SK이엔에스가 높은 EBITDA/수익성에도 현금흐름 역학 우려. 고설비투자/공격적 배당으로 5년간 지속적 마이너스 잉여현금흐름(연평균 -271억원).",
        "entities": [
            {"type": "company", "name": "SK이엔에스", "role": "분석 대상"},
            {"type": "company", "name": "SK이노베이션", "role": "잠재 합병 파트너"},
            {"type": "company", "name": "SK주식회사", "role": "TRS 계약 10% 주주"},
            {"type": "company", "name": "KKR", "role": "우선주 주주"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "5년간 잉여현금흐름 적자(연 -2710억원), 영업현금 초과 지속불가 배당지급", "severity": "critical"},
            {"type": "financial", "description": "부채부담 증가(2020-2024년 2.5조원 증가), 우선주 발행이 실제 재무의무 은폐", "severity": "high"},
            {"type": "governance", "description": "우선주/하이브리드증권이 자본 회계처리에도 부채 기능, 자기자본 계산 왜곡", "severity": "high"},
            {"type": "operational", "description": "과도한 설비투자 강도(3년간 4조원)로 배당 지속성 외부금융 의존", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/536",
        "title": "합병비율 숨겨진 쟁점①, SK이엔에스 자산가치는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-07-08",
        "summary": "SK이노베이션-SK이엔에스 합병 분석, 자산 밸류에이션 방법론이 합병비율에 미치는 영향. 우선주/후순위채 회계처리가 SK이엔에스 순자산가치와 양사 주주 공정성에 중대 영향.",
        "entities": [
            {"type": "company", "name": "SK이노베이션", "role": "상장회사/합병 대상, SK이엔에스 지분 34.5% 보유"},
            {"type": "company", "name": "SK이엔에스", "role": "비상장회사/합병 파트너, SK주식회사 100% 소유"},
            {"type": "company", "name": "SK주식회사", "role": "지주회사, 양사 지배"},
            {"type": "company", "name": "KKR", "role": "전환우선주 보유 (3.135조원)"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "우선주 상환 총 4.618조원 필요 가능, 부채 재분류 시 순자산가치 대폭 감소", "severity": "critical"},
            {"type": "financial", "description": "후순위채(73억원) 자본 분류가 자기자본주 귀속 아닐 수 있음 - 자산 밸류에이션 과대계상", "severity": "high"},
            {"type": "governance", "description": "합병비율 결정에 주식전환 시점/상환 가능성 주관적 가정 투명성 부족", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/535",
        "title": "SK이엔에스 우선주에 숨겨진 결정적 리스크",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-07-04",
        "summary": "SK이엔에스가 KKR 보유 상환전환우선주 3.135조원 발행, 상당한 재무의무 발생. SK이노베이션 합병 시 2026년 조기상환 유발 가능, 상환 지연 시 배당률/IRR 요건 상승으로 비용 가중.",
        "entities": [
            {"type": "company", "name": "SK이엔에스", "role": "우선주 발행사"},
            {"type": "company", "name": "SK이노베이션", "role": "합병 파트너"},
            {"type": "company", "name": "KKR", "role": "우선주 100% 보유"},
            {"type": "company", "name": "SK주식회사", "role": "지주회사, TRS 계약 체결"},
            {"type": "company", "name": "SK온", "role": "배터리 자회사"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "우선주 의무 조기상환(2026년까지 약 3.98조원), 지연 시 비용 상승, 연간 배당부담 1.25조원", "severity": "critical"},
            {"type": "financial", "description": "KKR 전환 거부 시 배당률 8.99%로 상승, 참가적 우선주화로 자본 유출 심화", "severity": "high"},
            {"type": "governance", "description": "KKR 전환권이 비대칭 레버리지 형성, 행사가(기준 67만원)로 합병 이익 투자자가 주주 대신 포획 가능", "severity": "high"},
            {"type": "operational", "description": "합병 수익이 SK이노베이션 운영 안정 대신 우선주 상환에 전용 가능", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/534",
        "title": "SK이엔에스 주식 TRS계약, 콜옵션 행사될까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-07-01",
        "summary": "SK주식회사가 2017년 TRS 계약으로 현금 없이 SK이엔에스 주식 취득, 금융사 설립 페이퍼컴퍼니 활용. 원만기 2022년→2027년 11월 연장, SK이엔에스 IPO 대기 추정. SK이노베이션-SK이엔에스 합병 시 콜옵션 행사/누적이자(6780억원 약 연 5.4%) 관리 결정 복잡화.",
        "entities": [
            {"type": "company", "name": "SK주식회사", "role": "TRS 계약 보유 지주회사"},
            {"type": "company", "name": "SK이엔에스", "role": "TRS 대상 주식 발행 자회사"},
            {"type": "company", "name": "SK이노베이션", "role": "잠재 합병 파트너"},
            {"type": "company", "name": "미래에셋", "role": "페이퍼컴퍼니(MDPrime 1호, 2호) 설립"},
            {"type": "person", "name": "최태원", "role": "SK그룹 회장"},
        ],
        "relations": [
            {"source": "SK주식회사", "target": "SK이엔에스", "type": "TRS", "detail": "주식 TRS 계약"},
        ],
        "risks": [
            {"type": "financial", "description": "연간 TRS 이자비용(연 약 340억원), 2027년 전 콜옵션 행사 시 유동성 압박", "severity": "high"},
            {"type": "governance", "description": "TRS 구조로 간접 지분지배, 합병 협상/자본배분 결정 복잡화", "severity": "high"},
            {"type": "market", "description": "합병 후 SK이노베이션 주가 변동이 TRS 정산 손익에 영향, SK온 IPO 시점 불확실성이 밸류에이션 영향", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/533",
        "title": "SK이엔에스가 합병 대상으로 거론되는 이유",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-06-27",
        "summary": "SK이노베이션이 비수익 배터리 사업부 SK온으로 극심한 재무압박, 안정적 자회사 SK이엔에스와 합병 논의 촉발. 합병으로 중요한 현금흐름 안정/신용도 회복 제공, S&P가 SK이노베이션 투기등급 BB+로 강등 후.",
        "entities": [
            {"type": "company", "name": "SK이노베이션", "role": "재무곤란 모회사"},
            {"type": "company", "name": "SK이엔에스", "role": "안정적 에너지 운영 자회사"},
            {"type": "company", "name": "SK온", "role": "손실 배터리 사업부"},
            {"type": "company", "name": "SK주식회사", "role": "양사 지배 지주회사"},
            {"type": "company", "name": "S&P", "role": "신용평가사"},
            {"type": "company", "name": "KB국민은행", "role": "채권 보증인"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "SK이엔에스", "type": "merger_discussion", "detail": "재무안정 목적 합병 논의"},
        ],
        "risks": [
            {"type": "financial", "description": "SK이노베이션 '상당한 현재 현금적자' 직면, 신용접근 저하 속 지속적 외부금융 필요", "severity": "critical"},
            {"type": "governance", "description": "SK이노베이션 경영진 배터리 수익성 목표 반복 미달 - 실행 리스크", "severity": "high"},
            {"type": "market", "description": "BB+ 투기등급이 기관투자자 배제, 차입비용 상승", "severity": "high"},
            {"type": "operational", "description": "SK온 2025년까지 수익성 일정 불확실, 지속적 자본투자 필요", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/521",
        "title": "넷마블은 왜 하이브 주식까지 팔아야 했나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-05-16",
        "summary": "넷마블이 분기 연속 영업흑자에도 유동성 확보 위해 하이브 주식 110만주(2200억원)를 매각. 6월만 8547억원 단기부채 만기로 영업이익에도 자산청산 강제.",
        "entities": [
            {"type": "company", "name": "넷마블", "role": "게임회사, 부채압박"},
            {"type": "company", "name": "하이브", "role": "관계사, 넷마블 12% 보유, K-pop 엔터"},
            {"type": "person", "name": "방시혁", "role": "하이브 회장, 지분 31.6%, 넷마블 경영진과 친인척"},
            {"type": "person", "name": "방준혁", "role": "넷마블 회장"},
            {"type": "person", "name": "김병규", "role": "넷마블 상무이사/하이브 이사"},
        ],
        "relations": [
            {"source": "넷마블", "target": "하이브", "type": "ownership", "detail": "12% 지분 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "2024년 6월 단기부채 8547억원 만기, 자산매각에도 현금보유액 부족", "severity": "critical"},
            {"type": "operational", "description": "9분기 연속 순손실, 분기 매출 12% 감소", "severity": "high"},
            {"type": "governance", "description": "공격적 비용절감에 노조 결성 대응", "severity": "high"},
            {"type": "market", "description": "유동성 관리 단일 자산(하이브 주식) 의존", "severity": "medium"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (16차 - 누락기사: 두산/삼성전자/풀무원/SK/넷마블) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}... - {result.get('error', '')[:50]}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
