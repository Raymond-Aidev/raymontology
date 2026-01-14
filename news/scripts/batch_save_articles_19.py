#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 19차 (457-436: 에스엘에너지/롯데/효성/두산/쌍방울/미래산업/삼표 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/457",
        "title": "에스엘에너지 매각 나선 최대주주의 자금거래",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-09-14",
        "summary": "온성준·온영두 형제가 지배하는 에스엘홀딩스가 에스엘에너지 매각을 추진 중인 상황에서 자회사 넥스턴바이오사이언스가 미래산업 인수를 결정. 에스엘홀딩스는 대부업체 담보로 잡힌 주식 등 복잡한 자금거래 구조를 통해 우성인더스트리 인수에 필요한 자금을 조달했으며, 현재 완전 자본잠식 상태.",
        "entities": [
            {"type": "person", "name": "온성준", "role": "에스엘홀딩스 실질 지배자"},
            {"type": "person", "name": "온영두", "role": "에스엘홀딩스컴퍼니 100% 지분 보유자"},
            {"type": "person", "name": "이진규", "role": "루시드홀딩스 설립자"},
            {"type": "person", "name": "손오동", "role": "우성코퍼레이션 실질 지배자"},
            {"type": "company", "name": "에스엘에너지", "role": "피인수 대상"},
            {"type": "company", "name": "에스엘홀딩스컴퍼니", "role": "에스엘에너지 최대주주"},
            {"type": "company", "name": "루시드홀딩스", "role": "에스엘에너지 2대주주"},
            {"type": "company", "name": "넥스턴바이오사이언스", "role": "미래산업 인수자"},
            {"type": "company", "name": "우성인더스트리", "role": "에스엘에너지가 인수한 회사"},
        ],
        "relations": [
            {"source": "에스엘홀딩스컴퍼니", "target": "에스엘에너지", "type": "ownership", "detail": "15.42% 보유, 1대주주"},
            {"source": "루시드홀딩스", "target": "에스엘에너지", "type": "ownership", "detail": "10.52% 보유, 2대주주"},
            {"source": "넥스턴바이오사이언스", "target": "미래산업", "type": "acquisition", "detail": "경영권 지분 매입"},
        ],
        "risks": [
            {"type": "financial", "description": "에스엘홀딩스컴퍼니가 자산 97억원에 부채 140억원으로 완전 자본잠식 상태", "severity": "critical"},
            {"type": "governance", "description": "복잡한 자금거래 구조로 인해 실제 자금흐름 추적이 어려움", "severity": "high"},
            {"type": "legal", "description": "에스엘홀딩스컴퍼니가 채권양도 부당 주장 소송 준비 중", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/456",
        "title": "미래산업도 이제 2차전지 소재 테마주?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-09-07",
        "summary": "넥스턴바이오사이언스가 미래산업의 지배권을 인수한 지 두 달여가 지났으며, 온성준·온영두 형제가 이끄는 계열사들이 차헬스케어 프리IPO 투자와 니켈·리튬 신사업에 자금을 집중. 현금흐름 부족으로 전환사채 발행과 유상증자에 의존하면서 호재 소식으로 주가 상승을 유도하는 패턴.",
        "entities": [
            {"type": "company", "name": "미래산업", "role": "반도체 장비업체, 넥스턴바이오사이언스에 인수됨"},
            {"type": "company", "name": "넥스턴바이오사이언스", "role": "미래산업 지배주주"},
            {"type": "company", "name": "이브이첨단소재", "role": "리튬·니켈 사업 추진"},
            {"type": "company", "name": "차헬스케어", "role": "글로벌 병원 운영기업"},
            {"type": "company", "name": "다이나믹디자인", "role": "니켈광산 사업 추진"},
            {"type": "person", "name": "온성준", "role": "계열사 실질적 주인"},
            {"type": "person", "name": "온영두", "role": "온성준의 형"},
        ],
        "relations": [
            {"source": "넥스턴바이오사이언스", "target": "미래산업", "type": "ownership", "detail": "245억원에 지분 10.59% 인수"},
            {"source": "미래산업", "target": "차헬스케어", "type": "investment", "detail": "투자조합을 통해 130억원 출자"},
        ],
        "risks": [
            {"type": "financial", "description": "계열사 전체가 현금흐름 부족으로 전환사채와 유상증자에 의존, 미래산업·이브이첨단소재는 결손기업", "severity": "critical"},
            {"type": "governance", "description": "온성준이 지분을 직접 소유하지 않으면서 경영 투명성 낮음", "severity": "high"},
            {"type": "market", "description": "이브이첨단소재 주가가 1만7780원에서 4715원으로 급락", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/455",
        "title": "롯데케미칼의 빈 자리",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-09-04",
        "summary": "롯데지주의 배당금 수입이 계열사들의 부진으로 감소하고 있으며, 특히 캐시카우 역할을 하던 롯데케미칼의 영업적자 전환과 대규모 투자로 인해 심각한 자금난. 롯데지주는 외부차입과 자산매각으로 버티고 있으며, 롯데케미칼의 실적 회복이 그룹 재정 안정화의 핵심 과제.",
        "entities": [
            {"type": "company", "name": "롯데지주", "role": "지주사"},
            {"type": "company", "name": "롯데케미칼", "role": "주요 자금원(캐시카우)"},
            {"type": "company", "name": "롯데쇼핑", "role": "배당금 수입원"},
            {"type": "company", "name": "롯데바이오로직스", "role": "자금 수혜 계열사"},
            {"type": "company", "name": "롯데건설", "role": "유동성 위기 계열사"},
        ],
        "relations": [
            {"source": "롯데지주", "target": "롯데케미칼", "type": "ownership", "detail": "24.03% 지분 보유"},
            {"source": "롯데케미칼", "target": "롯데건설", "type": "ownership", "detail": "최대주주"},
        ],
        "risks": [
            {"type": "financial", "description": "롯데케미칼 지난해 7626억원 영업적자 및 현금흐름 악화", "severity": "critical"},
            {"type": "financial", "description": "롯데지주 총차입금 4조원 초과, 차입금의존도 43.67%", "severity": "critical"},
            {"type": "financial", "description": "순차입금/EBITDA 비율 13.29배로 악화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/454",
        "title": "양평사옥, 왜 우리홈쇼핑에 팔았나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-08-31",
        "summary": "우리홈쇼핑이 약 2000억원대 양평사옥 매입을 결정했으나, 2대 주주 태광산업이 강력히 반발. 태광산업은 이것이 우리홈쇼핑의 필요가 아닌 유동성 위기에 처한 롯데지주 지원 목적이라고 주장하며 경영진 배임을 제기.",
        "entities": [
            {"type": "company", "name": "우리홈쇼핑", "role": "양평사옥 매입 결정 회사"},
            {"type": "company", "name": "롯데지주", "role": "양평사옥 공동 소유자(64.6%)"},
            {"type": "company", "name": "롯데웰푸드", "role": "양평사옥 공동 소유자(35.4%)"},
            {"type": "company", "name": "태광산업", "role": "우리홈쇼핑 2대 주주(44.49%)"},
            {"type": "company", "name": "롯데쇼핑", "role": "우리홈쇼핑 최대주주(53.49%)"},
        ],
        "relations": [
            {"source": "우리홈쇼핑", "target": "롯데지주", "type": "asset_transaction", "detail": "양평사옥 약 2000억원 매입 결정"},
            {"source": "태광산업", "target": "우리홈쇼핑", "type": "shareholder_dispute", "detail": "사옥 매입 반발 및 배임 주장"},
        ],
        "risks": [
            {"type": "governance", "description": "소수주주(태광산업)의 강한 반발로 인한 주주 분쟁 및 법적 분쟁 가능성", "severity": "high"},
            {"type": "financial", "description": "롯데지주 현금 7000억원 대비 총차입금 4조1100억원", "severity": "critical"},
            {"type": "financial", "description": "롯데케미칼 미국·인도네시아 법인 차입금 약정 위반", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/453",
        "title": "상호출자 지분 5.83%의 향방은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-08-28",
        "summary": "DB아이엔씨의 DB메탈 흡수합병은 지주회사 전환 요건을 피하기 위한 전략으로, 합병 후 자산 규모가 1조원을 넘어 자회사 주식 비중이 50% 이하로 하락할 예정. 합병으로 인한 상호출자 문제 해결이 과제이며, DB하이텍이 보유하게 될 DB아이엔씨 지분 5.83%를 6개월 내에 처리해야 함.",
        "entities": [
            {"type": "company", "name": "DB아이엔씨", "role": "DB그룹 지주회사 역할, 흡수합병 주체"},
            {"type": "company", "name": "DB하이텍", "role": "핵심 계열사, 반도체 기업"},
            {"type": "company", "name": "DB메탈", "role": "DB아이엔씨에 흡수합병되는 회사"},
            {"type": "company", "name": "KCGI", "role": "행동주의 펀드, DB하이텍 지분 7.05% 보유"},
            {"type": "person", "name": "김남호", "role": "DB그룹 회장"},
        ],
        "relations": [
            {"source": "DB아이엔씨", "target": "DB하이텍", "type": "ownership", "detail": "지분율 12.42%"},
            {"source": "KCGI", "target": "DB하이텍", "type": "ownership", "detail": "지분 7.05% 보유"},
            {"source": "DB아이엔씨", "target": "DB메탈", "type": "merger", "detail": "흡수합병으로 자산 규모 1조원 이상 확대"},
        ],
        "risks": [
            {"type": "regulatory", "description": "지주회사 전환 의무 회피 가능성. DB하이텍 주가 상승 시 자회사 주식 비중 50% 초과 가능", "severity": "high"},
            {"type": "governance", "description": "합병 후 6개월 내 상호출자 5.83% 해소 필수", "severity": "high"},
            {"type": "market", "description": "합병 후 재상장 시 지분 5.83% 시장 공급으로 주가 하락 가능성", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/452",
        "title": "김남호 회장이 지켜 낸 DB메탈, 지배력 강화의 도구로",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-08-24",
        "summary": "DB아이엔씨가 DB메탈을 흡수합병함으로써 김남호 회장의 그룹 지배력이 강화될 것으로 예상. DB메탈 지분을 DB아이엔씨 지분으로 교환하면서 김남호 회장의 최대주주 위상이 확립되고 개인 지분율은 18.35%로 상승할 전망.",
        "entities": [
            {"type": "person", "name": "김남호", "role": "DB그룹 현 회장"},
            {"type": "person", "name": "김준기", "role": "DB그룹 창업회장"},
            {"type": "person", "name": "김주원", "role": "DB그룹 부회장"},
            {"type": "company", "name": "DB아이엔씨", "role": "DB그룹 최상위 지배회사"},
            {"type": "company", "name": "DB메탈", "role": "합금철 생산·판매 계열사"},
            {"type": "company", "name": "DB인베스트", "role": "김준기·김남호 소유 부자회사"},
        ],
        "relations": [
            {"source": "DB아이엔씨", "target": "DB메탈", "type": "merger", "detail": "흡수합병을 통해 김남호 회장의 지분율 상승"},
            {"source": "김남호", "target": "DB아이엔씨", "type": "ownership", "detail": "합병 후 지분율 18.35%로 증가 예정"},
        ],
        "risks": [
            {"type": "governance", "description": "합병을 통한 소수주주의 지분 희석 및 경영 지배력 집중 우려", "severity": "high"},
            {"type": "financial", "description": "DB메탈의 과거 재무 위기(2019-2020 연속 적자, 워크아웃) 기록", "severity": "medium"},
            {"type": "operational", "description": "전혀 관련 없는 사업을 하는 두 회사의 합병으로 시너지 불명확", "severity": "low"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/451",
        "title": "오리온그룹, 배당을 노린 지주회사 전환이었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-08-21",
        "summary": "오리온그룹의 2017년 지주회사 전환으로 오너일가의 지분율이 28.4%에서 63.8%로 급상승. 지주회사 오리온홀딩스는 영업현금흐름(190억원)보다 많은 배당금(331억원)을 지급하며 차입금이 985억원에 달함.",
        "entities": [
            {"type": "company", "name": "오리온홀딩스", "role": "지주회사"},
            {"type": "company", "name": "오리온", "role": "사업회사"},
            {"type": "company", "name": "쇼박스", "role": "코스닥 상장사 자회사"},
            {"type": "person", "name": "담철곤", "role": "회장/최대주주"},
            {"type": "person", "name": "이화경", "role": "부회장/담철곤 배우자"},
        ],
        "relations": [
            {"source": "담철곤 일가", "target": "오리온홀딩스", "type": "ownership", "detail": "지분율 63.8% 보유로 절대적 지배권 행사"},
            {"source": "오리온홀딩스", "target": "오리온", "type": "subsidiary", "detail": "매출의 90% 이상을 오리온과의 거래에서 창출"},
        ],
        "risks": [
            {"type": "governance", "description": "오너일가의 절대적 지분(63.8%)으로 일반주주(30%) 이익 침해 우려", "severity": "high"},
            {"type": "financial", "description": "영업현금흐름(190억원)보다 배당금(331억원)이 많으며, 차입금 985억원 누적", "severity": "critical"},
            {"type": "financial", "description": "미처분이익잉여금 부족으로 기타자본잉여금을 이익잉여금으로 전환하여 배당 가능액 확대", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/450",
        "title": "㈜효성, 위기에 빠진 자회사보다 중요한 배당?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-08-17",
        "summary": "효성그룹 지주회사인 ㈜효성이 경영난을 겪는 자회사 효성화학보다 주주배당을 우선시하고 있다는 지적. 2018년 이후 5년간 영업현금의 부족에도 불구하고 5986억원을 배당했으며, 효성화학은 부채비율 9941%로 유동성 위기 상황.",
        "entities": [
            {"type": "company", "name": "㈜효성", "role": "지주회사"},
            {"type": "company", "name": "효성화학", "role": "자회사"},
            {"type": "company", "name": "효성중공업", "role": "자회사"},
            {"type": "company", "name": "효성티앤씨", "role": "자회사"},
            {"type": "person", "name": "조현준", "role": "회장"},
            {"type": "person", "name": "조현상", "role": "부회장"},
        ],
        "relations": [
            {"source": "조현준·조현상", "target": "㈜효성", "type": "ownership", "detail": "2013년 30.27%에서 2023년 55.92%로 지분 증가"},
            {"source": "㈜효성", "target": "효성화학", "type": "parent_subsidiary", "detail": "2018년 인적분할로 자회사 설립"},
        ],
        "risks": [
            {"type": "financial", "description": "효성화학이 5분기 연속 적자, 부채비율 9941%, 순차입금 2조5000억원", "severity": "critical"},
            {"type": "financial", "description": "㈜효성이 자회사로부터 받은 배당금이 지급 배당금을 밑돌아 자금 여력 부족", "severity": "high"},
            {"type": "governance", "description": "오너 일가의 주식담보대출이 957만주에 달하며, 배당금 수취로 개인 사업 확장 추진", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/449",
        "title": "에이치디현대, 배당 확대를 위해 차입도 불사",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-08-14",
        "summary": "에이치디현대는 자회사 배당금보다 더 많은 규모의 주주배당을 지급하면서 부족분을 차입금으로 충당. 2019년부터 4년간 1조2582억원을 배당했으나 영업활동 현금흐름은 9700억원에 불과해 약 6000억원을 외부 차입으로 조달.",
        "entities": [
            {"type": "company", "name": "에이치디현대", "role": "분석 대상 지주회사"},
            {"type": "person", "name": "정몽준", "role": "이사장 겸 주요 주주(25.80%)"},
            {"type": "company", "name": "현대중공업", "role": "주요 자회사"},
            {"type": "company", "name": "현대삼호중공업", "role": "자회사"},
        ],
        "relations": [
            {"source": "에이치디현대", "target": "현대중공업", "type": "ownership", "detail": "에이치디한국조선해양을 통해 지배"},
            {"source": "정몽준", "target": "에이치디현대", "type": "ownership", "detail": "25.80% 지분 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "배당금이 영업활동 현금흐름을 지속적으로 초과하며 장기차입금이 4조3000억원 증가", "severity": "high"},
            {"type": "financial", "description": "보유 현금이 설립시 3000억원에서 968억원으로 급감", "severity": "high"},
            {"type": "governance", "description": "오너 일가의 과도한 배당 수입(4500억원 이상)과 부실화 위험", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/448",
        "title": "㈜두산, 그룹 구조조정이 배당 재원?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-08-10",
        "summary": "두산은 영업활동 현금흐름이 3년 연속 적자임에도 불구하고 총 3585억원의 배당금을 지급. 이는 계열사 지분 매각 등 그룹 구조조정으로 인한 약 1조3000억원의 투자자산 매각 수익으로 재원이 마련된 것으로 분석.",
        "entities": [
            {"type": "company", "name": "㈜두산", "role": "지주회사"},
            {"type": "person", "name": "박정원", "role": "회장"},
            {"type": "company", "name": "두산중공업", "role": "계열사"},
            {"type": "company", "name": "두산밥캣", "role": "계열사"},
            {"type": "company", "name": "두산에너빌리티", "role": "계열사"},
        ],
        "relations": [
            {"source": "박정원 일가", "target": "㈜두산", "type": "ownership", "detail": "보통주 39.68%, 우선주 33.22% 보유"},
            {"source": "㈜두산", "target": "두산산업차량", "type": "asset_sale", "detail": "두산밥캣에 7500억원에 매각"},
        ],
        "risks": [
            {"type": "financial", "description": "3년 연속 영업활동 현금흐름이 음수로 배당 재원이 주로 자산 매각에 의존", "severity": "high"},
            {"type": "operational", "description": "연간 700억원 이상의 이자 지급과 운전자본 증가로 인한 현금 소비 지속", "severity": "high"},
            {"type": "governance", "description": "총수 일가가 배당금의 절반 이상을 수취하는 구조로 소수주주 이익 침해 우려", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/447",
        "title": "쌍방울그룹에게 제이준코스메틱의 의미는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-08-07",
        "summary": "제이준코스메틱은 마스크 팩 사업의 전성기 이후 본사와 공장을 매각하며 약 500억원을 확보했으나, 실질적인 현금 창출 없이 지분투자에 집중. 현재 514억원의 자산 중 274억원이 종속회사 및 관계회사 지분이며, 쌍방울그룹의 순환출자 고리가 됨.",
        "entities": [
            {"type": "company", "name": "제이준코스메틱", "role": "주요 대상 회사"},
            {"type": "company", "name": "쌍방울그룹", "role": "최종 모기업"},
            {"type": "company", "name": "칼라스홀딩스", "role": "쌍방울그룹 지주회사"},
            {"type": "company", "name": "광림", "role": "주요 자산 대상"},
            {"type": "company", "name": "에프앤리퍼블릭", "role": "최대 거래처이자 매출채권 손상 발생처"},
        ],
        "relations": [
            {"source": "제이준코스메틱", "target": "광림", "type": "ownership", "detail": "15.92% 지분 보유, 225억원 규모"},
            {"source": "칼라스홀딩스", "target": "광림", "type": "asset_sale", "detail": "광림 지분 매각 필요"},
        ],
        "risks": [
            {"type": "financial", "description": "매출 급감으로 은행 차입금 상환 불가능, 증권사 주식담보대출로 전환", "severity": "critical"},
            {"type": "operational", "description": "매출이 거의 발생하지 않고 설비자산도 없는 상황으로 실질 사업 능력 상실", "severity": "critical"},
            {"type": "governance", "description": "복수의 순환출자 구조 형성으로 투명성 및 지배구조 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/446",
        "title": "사세 기우는 와중에 지분 투자에 열중했던 제이준코스메틱",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-08-03",
        "summary": "제이준코스메틱은 2018년 전성기 이후 급격한 매출 감소를 겪었으나, 본업 회복보다는 지분 투자와 자산 매각에 집중. 화장품 장사보다 알에프텍 인수·매각, 다양한 타사 지분 취득 등 지분 거래에 더 열중.",
        "entities": [
            {"type": "company", "name": "제이준코스메틱", "role": "주 대상 기업"},
            {"type": "company", "name": "이도헬스케어", "role": "전 최대주주"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "현 최대주주"},
            {"type": "company", "name": "알에프텍", "role": "인수 후 매각 대상 회사"},
            {"type": "person", "name": "이진형", "role": "알에프텍 및 이도헬스케어 대표이사"},
        ],
        "relations": [
            {"source": "제이준코스메틱", "target": "알에프텍", "type": "acquisition_disposal", "detail": "2018년 433억원 인수, 2022년 9월 매각"},
            {"source": "아이오케이컴퍼니", "target": "제이준코스메틱", "type": "acquisition", "detail": "2022년 8월 270억원에 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "2018년 매출 대비 2022년 매출이 22% 수준으로 급격히 감소", "severity": "critical"},
            {"type": "market", "description": "중국 시장 부진으로 주력 제품인 마스크팩 매출 급감", "severity": "high"},
            {"type": "governance", "description": "본업 회복 노력 부재, 지분 투자와 자산 매각에만 집중하는 경영 방향", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/445",
        "title": "제이준코스메틱, 쌍방울그룹 순환출자 '새 고리' 되기까지",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-07-31",
        "summary": "제이준코스메틱은 1995년 피혁업체 신우로 상장된 후 28년간 14번의 최대주주 변화를 겪었다. 법정관리를 거쳐 2016년 우회상장한 후 2018년까지 전성기를 누렸으나, 이후 매출이 급락하여 2023년 쌍방울그룹의 지배 하에 들어가게 됨.",
        "entities": [
            {"type": "company", "name": "제이준코스메틱", "role": "주요 피사기업"},
            {"type": "company", "name": "쌍방울그룹", "role": "최종 인수자"},
            {"type": "company", "name": "신우", "role": "원래 회사명"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "현 최대주주"},
            {"type": "person", "name": "박범규", "role": "제이준코스메틱 대표이사"},
        ],
        "relations": [
            {"source": "신우", "target": "제이준코스메틱", "type": "merger", "detail": "2016년 유상증자 및 합병을 통한 우회상장"},
            {"source": "칼라스홀딩스", "target": "제이준코스메틱", "type": "asset_transfer", "detail": "광림 지분을 순환출자 구조의 중요 고리로 이전"},
        ],
        "risks": [
            {"type": "financial", "description": "2019년 이후 누적 영업손실 806억원, 2023년 매출 58억원으로 급락", "severity": "critical"},
            {"type": "governance", "description": "28년간 14회 최대주주 변경, 순환출자 지배구조 형성", "severity": "high"},
            {"type": "legal", "description": "선포커스 관련 모회사 위드윈네트웍이 검찰 고발 및 상장폐지 위기", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/444",
        "title": "미래산업 진짜 새 주인은 안갯속?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-07-27",
        "summary": "반도체 검사장비 제조사 미래산업의 실제 소유 구조가 복잡하게 얽혀 있다. 기업사냥꾼으로 알려진 온성준씨의 계열사들이 연쇄적으로 미래산업과 연결되어 있으며, 부실기업들의 전환사채 발행과 자금 순환이 반복.",
        "entities": [
            {"type": "company", "name": "미래산업", "role": "반도체 검사장비 제조업체"},
            {"type": "company", "name": "넥스턴바이오사이언스", "role": "미래산업 인수자"},
            {"type": "company", "name": "스튜디오산타클로스", "role": "넥스턴바이오사이언스 최대주주"},
            {"type": "company", "name": "이브이첨단소재", "role": "미래산업 연관사"},
            {"type": "company", "name": "에스엘에너지", "role": "우성인더스트리 최대주주"},
            {"type": "person", "name": "온성준", "role": "기업사냥꾼, 스튜디오산타클로스 실질 사주"},
            {"type": "person", "name": "김성태", "role": "쌍방울그룹 회장"},
        ],
        "relations": [
            {"source": "온성준", "target": "스튜디오산타클로스", "type": "ownership", "detail": "실질 사주"},
            {"source": "스튜디오산타클로스", "target": "넥스턴바이오사이언스", "type": "acquisition", "detail": "2021년 3월 인수"},
            {"source": "넥스턴바이오사이언스", "target": "미래산업", "type": "acquisition", "detail": "전환사채 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "넥스턴바이오사이언스의 순차입이 826억원에 달하고 현금이 4분의 1로 감소. 3년 연속 적자", "severity": "critical"},
            {"type": "financial", "description": "에스엘에너지가 상상인저축은행에서 120억원 차입하면서 스튜디오산타클로스 지분을 담보로 제시", "severity": "critical"},
            {"type": "regulatory", "description": "에스엘에너지가 불성실공시로 벌점 누적되어 상장적격성 실질심사 대상", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/443",
        "title": "미래산업 새주인, 인수대금 어디서 났나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-07-24",
        "summary": "넥스턴바이오사이언스가 쌍방울그룹으로부터 미래산업을 인수한 자금 조달 과정 분석. 제한적인 유동성을 보유한 회사가 이브이첨단소재 주식 매각과 전환사채 발행으로 약 400억원 규모의 인수자금을 마련.",
        "entities": [
            {"type": "company", "name": "넥스턴바이오사이언스", "role": "미래산업 인수자"},
            {"type": "company", "name": "미래산업", "role": "인수 대상 회사"},
            {"type": "company", "name": "쌍방울그룹", "role": "미래산업 전 소유사"},
            {"type": "company", "name": "이브이첨단소재", "role": "자금 조달 목적 주식 매각 대상"},
            {"type": "company", "name": "스튜디오산타클로스엔터테인먼트", "role": "넥스턴바이오사이언스 최대주주"},
        ],
        "relations": [
            {"source": "넥스턴바이오사이언스", "target": "미래산업", "type": "acquisition", "detail": "약 400억원 규모로 경영권 지분 10.59%와 전환사채 인수"},
            {"source": "넥스턴바이오사이언스", "target": "이브이첨단소재", "type": "asset_sale", "detail": "300만주 시간외 대량매매로 233억원 확보"},
        ],
        "risks": [
            {"type": "financial", "description": "넥스턴바이오사이언스의 유동성 악화. 3월말 현금 151억원 대비 차입금 744억원으로 과다", "severity": "high"},
            {"type": "financial", "description": "스튜디오산타클로스의 심각한 자금난. 현금 23억원 대비 1년내 상환 차입금 315억원", "severity": "critical"},
            {"type": "operational", "description": "스튜디오산타클로스의 극도로 부진한 영업(1분기 매출 14억원, 누적 적자 300억원 이상)", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/442",
        "title": "미래산업에 남은 전 주인의 잔재",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-07-20",
        "summary": "넥스턴바이오사이언스가 395억원을 투입해 미래산업의 경영권을 인수했으며, 새로운 경영진이 구성. 미래산업에는 쌍방울그룹의 화현관광개발 지분과 아이오케이컴퍼니 전환사채 등 미처 정리되지 못한 과제들이 남아 있음.",
        "entities": [
            {"type": "company", "name": "미래산업", "role": "인수 대상 회사"},
            {"type": "company", "name": "넥스턴바이오사이언스", "role": "경영권 인수자"},
            {"type": "company", "name": "쌍방울그룹", "role": "전 경영권자"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "전환사채 발행사"},
            {"type": "company", "name": "화현관광개발", "role": "골프장사업 추진 관계사"},
            {"type": "person", "name": "이창재", "role": "미래산업 신임 대표이사"},
        ],
        "relations": [
            {"source": "넥스턴바이오사이언스", "target": "미래산업", "type": "acquisition", "detail": "395억원 투입으로 경영권 획득 및 전환사채 150억원 인수"},
            {"source": "미래산업", "target": "화현관광개발", "type": "ownership", "detail": "12.08% 지분 보유, 장부가 37억원"},
            {"source": "미래산업", "target": "아이오케이컴퍼니", "type": "bond_holding", "detail": "전환사채 100억원 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "아이오케이컴퍼니가 누적 결손금 1394억원, 현금성자산 90억원에 불과하여 전환사채 100억원 상환 능력 불확실", "severity": "critical"},
            {"type": "governance", "description": "미래산업이 쌍방울그룹 계열사들과의 복잡한 채권·채무 관계", "severity": "high"},
            {"type": "regulatory", "description": "쌍방울그룹의 여러 계열사가 상장폐지 위기에 놓여 있는 상황", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/441",
        "title": "미래산업 경영권 매각, 씨비아이에 불똥?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-07-13",
        "summary": "쌍방울그룹 계열사 미래산업의 경영권 매각으로 넥스턴바이오사이언스가 신주인이 되면서, 씨비아이와의 관계가 정리되고 있다. 미래산업과 SBW생명과학이 보유 중인 지브이비티 조합 지분을 전량 매각하기로 결정.",
        "entities": [
            {"type": "company", "name": "미래산업", "role": "쌍방울그룹 계열사, 경영권 매각 대상"},
            {"type": "company", "name": "씨비아이", "role": "바이오 투자회사"},
            {"type": "company", "name": "넥스턴바이오사이언스", "role": "미래산업의 새로운 경영진"},
            {"type": "company", "name": "SBW생명과학", "role": "쌍방울그룹 관계회사"},
            {"type": "company", "name": "디지피", "role": "신재생에너지업체"},
            {"type": "person", "name": "오경원", "role": "씨비아이 대표이사"},
        ],
        "relations": [
            {"source": "미래산업", "target": "넥스턴바이오사이언스", "type": "ownership_transfer", "detail": "경영권 매각, 전환사채(8회차) 150억원 인수 약정"},
            {"source": "씨비아이", "target": "디지피", "type": "acquisition_disposal", "detail": "3개월 만에 지분 일부 및 전환사채 매각"},
        ],
        "risks": [
            {"type": "financial", "description": "씨비아이는 2년 3개월간 약 386억원 손실 기록, 그 중 300억원이 종속·관계기업 투자에서 발생", "severity": "critical"},
            {"type": "market", "description": "씨비아이 주가 2020년 1,000원대에서 피크 15,000원 후 현재 2,000원대로 급락", "severity": "high"},
            {"type": "financial", "description": "2021년 이후 전환사채 발행 371억원, 유상증자 293억원으로 급속 자본조달 의존", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/440",
        "title": "광림이 포기한 미래산업 CB의 행방",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-07-10",
        "summary": "쌍방울그룹의 자금난으로 인해 광림이 미래산업 지분 10.59%를 245억원에 넥스턴바이오사이언스에 매각. 지난해 대비 약 4배 상승한 주가에 71% 프리미엄을 더해 판매한 것으로, 전환사채 조기상환과 재매각을 통한 복잡한 자금흐름이 동반.",
        "entities": [
            {"type": "company", "name": "광림", "role": "쌍방울그룹 중심 계열사, 미래산업 지분 매도자"},
            {"type": "company", "name": "미래산업", "role": "유가증권시장 상장사, 매각 대상"},
            {"type": "company", "name": "넥스턴바이오사이언스", "role": "미래산업 지분 인수자"},
            {"type": "company", "name": "미래컨소시엄", "role": "전환사채 매입자"},
            {"type": "person", "name": "김성태", "role": "쌍방울그룹 회장"},
        ],
        "relations": [
            {"source": "광림", "target": "미래산업", "type": "ownership_transfer", "detail": "10.59% 지분을 245억원에 매각 (2021년 82억원에 인수, 약 3배 수익)"},
            {"source": "넥스턴바이오사이언스", "target": "미래산업", "type": "acquisition", "detail": "경영권 인수, 신규 8회차 전환사채 150억원 발행"},
        ],
        "risks": [
            {"type": "financial", "description": "광림의 비정상적으로 높은 매각가격(71% 프리미엄)은 숨겨진 거래구조를 시사", "severity": "high"},
            {"type": "governance", "description": "와이투헬스케어의 최대주주 정보가 공시상 상이하며, 지배구조 투명성 문제", "severity": "high"},
            {"type": "legal", "description": "미래컨소시엄이 17억원의 출자금으로 100억원대 전환사채를 매입한 자금 출처 불명", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/439",
        "title": "광림 지분 매각 후, 꼬여 버린 계열사 자금흐름",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-07-06",
        "summary": "김성태 회장 구속으로 쌍방울 그룹 계열사들이 동시에 위기에 처했다. 순환출자 구조로 외형을 키운 그룹이 칼라스홀딩스의 광림 지분 매각 후 복잡한 자금흐름 속에서 유동성 확보에 어려움을 겪고 있음.",
        "entities": [
            {"type": "person", "name": "김성태", "role": "쌍방울 그룹 회장"},
            {"type": "company", "name": "광림", "role": "특장차 회사, 상장폐지 위기"},
            {"type": "company", "name": "쌍방울", "role": "그룹 계열사, 감자 검토"},
            {"type": "company", "name": "아이오케이컴퍼니", "role": "결손법인, 제이준코스메틱 보유"},
            {"type": "company", "name": "칼라스홀딩스", "role": "최상위 지배회사"},
            {"type": "company", "name": "비비안", "role": "계열사, 전환사채 보유"},
        ],
        "relations": [
            {"source": "칼라스홀딩스", "target": "제이준코스메틱", "type": "asset_sale", "detail": "광림 지분 16.17% 매각, 225억원 회수"},
            {"source": "아이오케이컴퍼니", "target": "비비안", "type": "debt", "detail": "전환사채 100억원, 미상환 상태"},
        ],
        "risks": [
            {"type": "financial", "description": "아이오케이컴퍼니의 현금 보유액 56억원으로 급감, 미상환 전환사채 200억원 존재", "severity": "critical"},
            {"type": "financial", "description": "광림 상장폐지 가능성 및 쌍방울, 아이오케이컴퍼니의 감자 필요", "severity": "critical"},
            {"type": "governance", "description": "순환출자 구조로 인한 자본 과다 계상, 연결 부채비율 실제보다 과다 표시", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/438",
        "title": "에스피네이처가 합병 전 삼표산업 유상증자 참여한 이유?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-07-03",
        "summary": "삼표산업이 2023년 3월 600억원 규모의 유상증자를 실시했으며, 신주 195만주를 정대현 사장의 개인회사 에스피네이처가 인수. 5월 합병 전 이루어진 거래로, 합병 후 정대현 사장의 지배력을 약 23.45%로 크게 상승시킴.",
        "entities": [
            {"type": "company", "name": "에스피네이처", "role": "유상증자 신주 인수자"},
            {"type": "company", "name": "삼표산업", "role": "유상증자 실시 회사"},
            {"type": "company", "name": "㈜삼표", "role": "삼표산업의 모회사"},
            {"type": "person", "name": "정대현", "role": "사장, 에스피네이처 소유자"},
            {"type": "person", "name": "정도원", "role": "회장"},
        ],
        "relations": [
            {"source": "에스피네이처", "target": "삼표산업", "type": "ownership", "detail": "신주 195만주(600억원) 인수로 보유지분 상향"},
            {"source": "정대현", "target": "에스피네이처", "type": "ownership", "detail": "개인 소유 회사"},
        ],
        "risks": [
            {"type": "governance", "description": "합병을 앞두고 후계자 개인회사에 대규모 유상증자를 실시하여 지배력을 집중시키는 구조, 소수주주 이익침해 우려", "severity": "critical"},
            {"type": "governance", "description": "공정거래위원회 공시에서만 신주 인수자 정보가 드러났으며, 감사보고서에는 미공개로 투명성 부족", "severity": "high"},
            {"type": "financial", "description": "에스피네이처의 삼표산업 대여금 400억원과 신주인수 상계 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/437",
        "title": "합병법인 삼표산업 자사주, 어차피 정대현 몫?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-29",
        "summary": "삼표그룹이 역합병을 통해 정대현 사장의 경영승계를 추진. 삼표산업이 모회사 삼표를 흡수하면서 48.9%의 자기주식이 발생하며, 이를 에스피네이처에 이전하면 정대현 사장이 아버지 지분 없이도 총수 지위를 확보할 수 있는 구조.",
        "entities": [
            {"type": "person", "name": "정대현", "role": "삼표그룹 후계자, 사장"},
            {"type": "person", "name": "정도원", "role": "삼표그룹 회장"},
            {"type": "company", "name": "삼표산업", "role": "합병 주체 (역합병)"},
            {"type": "company", "name": "삼표", "role": "모회사, 지주회사"},
            {"type": "company", "name": "에스피네이처", "role": "정대현 개인회사 통합법인"},
        ],
        "relations": [
            {"source": "삼표산업", "target": "삼표", "type": "merger", "detail": "역합병을 통해 자기주식 48.9% 발생"},
            {"source": "정대현", "target": "에스피네이처", "type": "ownership", "detail": "개인회사들을 통합한 법인"},
        ],
        "risks": [
            {"type": "governance", "description": "역합병 구조를 통해 아버지의 지분 증여/상속 없이 경영권 이전 추진으로 소수주주 이익 침해 가능성", "severity": "high"},
            {"type": "financial", "description": "에스피네이처 보유 상환우선주(789억원) 조기상환 요건이 합병으로 발동될 수 있음", "severity": "medium"},
            {"type": "governance", "description": "자기주식을 통한 실질 지분율 조정으로 지배구조 왜곡 우려", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/436",
        "title": "몰라보게 커진 에스피네이처의 자금활동",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-26",
        "summary": "에스피네이처는 2020년 이후 자산유동화, 사채발행, 상환우선주 등을 통해 약 1830억원을 순조달. 조달 자금은 주로 계열사 주식 취득과 배당금 지급에 사용되었으며, 영업실적 대비 배당이 크게 증가.",
        "entities": [
            {"type": "company", "name": "에스피네이처", "role": "삼표그룹 정대현 사장의 회사"},
            {"type": "company", "name": "㈜삼표", "role": "삼표그룹 지주회사"},
            {"type": "company", "name": "에스타이거에스피㈜", "role": "대출채권 유동화 목적 SPC"},
            {"type": "person", "name": "정대현", "role": "에스피네이처 보통주 71.95% 보유자"},
        ],
        "relations": [
            {"source": "에스피네이처", "target": "㈜삼표", "type": "investment", "detail": "2020년 유상증자 600억원 전부 인수, 지분 19.43% 취득"},
            {"source": "에스피네이처", "target": "정대현", "type": "dividend", "detail": "3년간 약 230억원 배당 지급"},
        ],
        "risks": [
            {"type": "financial", "description": "상환우선주 연 3.98% 배당 고정, 2024년부터 상환압박 가능성", "severity": "high"},
            {"type": "financial", "description": "EBITDA 감소 추세에도 배당금 증가로 현금유출 확대", "severity": "high"},
            {"type": "governance", "description": "외감기업으로 상환우선주 발행 조건 공시 부족", "severity": "medium"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (19차) ===\n")

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
