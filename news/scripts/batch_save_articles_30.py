#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 30차 (현대차그룹/남화산업/장산/라이브플렉스/부산주공/엔케이물산 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/229",
        "title": "분할합병 후 현대글로비스의 총수 일가 지분율은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-06-03",
        "summary": "현대모비스 분할합병 시나리오에 따라 분할법인의 가치 평가가 총수 일가의 현대글로비스 지분율에 미치는 영향 분석.",
        "entities": [
            {"type": "company", "name": "현대모비스", "role": "분할 대상 회사"},
            {"type": "company", "name": "현대글로비스", "role": "합병 대상 회사"},
            {"type": "company", "name": "현대자동차", "role": "계열사"},
            {"type": "company", "name": "기아차", "role": "현대모비스 주요 주주"},
            {"type": "person", "name": "정몽구", "role": "총수 (현대글로비스 29.9% 보유)"},
            {"type": "person", "name": "정의선", "role": "후계자"},
        ],
        "relations": [
            {"source": "현대모비스", "target": "현대글로비스", "type": "merger", "detail": "현대모비스 분할법인이 현대글로비스와 합병될 예정"},
            {"source": "정몽구-정의선", "target": "현대글로비스", "type": "ownership", "detail": "34.45% 지분율 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "분할법인의 가치 평가 기준에 따라 총수 일가 지분율이 크게 달라져 공정성 문제 발생 가능", "severity": "high"},
            {"type": "regulatory", "description": "자사주를 활용한 지배력 강화(자사주 마법)에 대한 규제 강화 추진 중", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/228",
        "title": "현대모비스, 지주회사냐 지주회사'격'이냐",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-05-31",
        "summary": "현대차그룹이 현대모비스를 분할합병하면서 투자회사를 공정거래법상 지주회사로 지정하지 않으려는 의도 분석.",
        "entities": [
            {"type": "company", "name": "현대모비스", "role": "분할 대상 회사"},
            {"type": "company", "name": "현대글로비스", "role": "합병 예정 회사"},
            {"type": "company", "name": "현대자동차", "role": "피지배 계열사"},
            {"type": "company", "name": "기아차", "role": "피지배 계열사"},
            {"type": "person", "name": "정의선", "role": "회장"},
        ],
        "relations": [
            {"source": "현대모비스", "target": "현대자동차", "type": "ownership", "detail": "장부가액 3조8802억원, 공정가치 9조9805억원"},
        ],
        "risks": [
            {"type": "regulatory", "description": "원가법 회계처리로 지주회사 지정 회피 가능성", "severity": "high"},
            {"type": "governance", "description": "총수일가의 그룹 지배력 강화 의도와 순환출자 해소 목표 간 불일치", "severity": "high"},
            {"type": "legal", "description": "지주회사 지정 회피 시 자회사 지분율 규제 등 미적용으로 인한 법적 공백", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/227",
        "title": "현대모비스 분할하면, 기업가치 얼마나 될까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-05-27",
        "summary": "현대모비스 분할 시 모듈/AS부문 신설법인과 현대글로비스의 합병비율 결정이 핵심 쟁점.",
        "entities": [
            {"type": "company", "name": "현대모비스", "role": "분할 대상 기업"},
            {"type": "company", "name": "현대글로비스", "role": "합병 대상 기업"},
            {"type": "company", "name": "현대자동차", "role": "계열사"},
            {"type": "person", "name": "정의선", "role": "현대차그룹 회장"},
        ],
        "relations": [
            {"source": "현대모비스", "target": "현대글로비스", "type": "merger_plan", "detail": "모듈/AS부문 분할 후 합병 계획"},
        ],
        "risks": [
            {"type": "governance", "description": "합병비율 결정 과정에서 정의선 회장의 이익 편향 가능성", "severity": "high"},
            {"type": "financial", "description": "비영업자산 가치 평가 방식의 불일치로 인한 분할법인 가치 결정 불확실성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/226",
        "title": "현대모비스 분할비율 높일까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-05-24",
        "summary": "현대모비스 인적분할 시 분할비율 결정이 핵심 과제. 개정 공정거래법의 강화된 의무 지분율(30%) 요건 분석.",
        "entities": [
            {"type": "company", "name": "현대모비스", "role": "분할 대상 기업"},
            {"type": "company", "name": "현대자동차", "role": "최대주주"},
            {"type": "company", "name": "현대글로비스", "role": "합병 대상 기업"},
            {"type": "person", "name": "정의선", "role": "현대엔지니어링 최대주주"},
        ],
        "relations": [
            {"source": "현대모비스", "target": "현대자동차", "type": "ownership", "detail": "현대자동차 지분율 21.43% 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "분할비율 낮게 책정 시 총수일가에 유리하다는 지배구조 비난", "severity": "high"},
            {"type": "financial", "description": "현대차 지분율 30%로 올리려면 약 4조 1658억원 추가 자금 필요", "severity": "high"},
            {"type": "regulatory", "description": "개정 공정거래법 시행 시 강화된 의무 지분율 준수 의무", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/225",
        "title": "현대모비스 분할법인, 상장 먼저? 합병 먼저?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-05-20",
        "summary": "현대차그룹의 순환출자 해소와 지배구조 개편을 위해 현대모비스 분할 추진. 2018년 실패 사례의 핵심 문제 분석.",
        "entities": [
            {"type": "company", "name": "현대모비스", "role": "분할 대상 기업"},
            {"type": "company", "name": "현대글로비스", "role": "합병 대상 기업"},
            {"type": "company", "name": "현대차", "role": "계열사"},
            {"type": "company", "name": "기아차", "role": "계열사"},
            {"type": "person", "name": "정의선", "role": "현대차그룹 회장"},
        ],
        "relations": [
            {"source": "현대모비스", "target": "현대글로비스", "type": "merger_plan", "detail": "모듈/AS사업부 분할 후 합병 계획"},
        ],
        "risks": [
            {"type": "governance", "description": "분할비율을 순자산 장부가액으로 결정하여 실제 수익창출능력을 반영하지 못함", "severity": "critical"},
            {"type": "legal", "description": "본질가치법과 시장가치법 혼용으로 인한 주주 부의 훼손", "severity": "high"},
            {"type": "regulatory", "description": "공정거래법 개정으로 사익편취 규제 기준 강화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/224",
        "title": "호시절 누리는 남화산업, 약점은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-05-18",
        "summary": "코로나19 수혜로 골프장 운영업체 남화산업의 실적이 크게 개선. 성장의 한계와 관계기업 투자로 인한 자산회전율 저하가 주요 약점.",
        "entities": [
            {"type": "company", "name": "남화산업", "role": "골프장 운영사"},
            {"type": "company", "name": "무안컨트리클럽", "role": "남화산업 자회사"},
            {"type": "company", "name": "한국씨엔티", "role": "관계기업"},
            {"type": "company", "name": "남화토건", "role": "최대주주"},
        ],
        "relations": [
            {"source": "남화산업", "target": "무안컨트리클럽", "type": "operation", "detail": "54홀 규모의 국내 3번째 대중제 골프장 운영"},
            {"source": "남화산업", "target": "한국씨엔티", "type": "investment", "detail": "지분율 42.54% 보유, 자산 677억원 규모"},
        ],
        "risks": [
            {"type": "market", "description": "코로나19 특수 해소 시 골프 수요 감소 가능성 및 그린피 인상의 한계", "severity": "high"},
            {"type": "operational", "description": "홀 가동률이 80% 근처로 포화되어 성장성 한계", "severity": "high"},
            {"type": "regulatory", "description": "골프장 신설 인허가의 엄격함과 환경·교통 영향평가로 인한 확장 제약", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/223",
        "title": "현대글로비스, 20년의 빅 피처가 실현될 것인가?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-05-13",
        "summary": "현대글로비스는 정의선 회장의 그룹 승계를 위해 설립된 회사. 현대모비스 인적분할과 합병을 통해 지주회사 체제 구축 예상.",
        "entities": [
            {"type": "company", "name": "현대글로비스", "role": "물류·운송 담당 회사"},
            {"type": "company", "name": "현대자동차", "role": "모그룹 주력사"},
            {"type": "company", "name": "현대모비스", "role": "부품제조 회사"},
            {"type": "person", "name": "정의선", "role": "현대글로비스 최대주주, 회장"},
            {"type": "person", "name": "정몽구", "role": "현대글로비스 대주주, 명예회장"},
        ],
        "relations": [
            {"source": "정의선", "target": "현대글로비스", "type": "ownership", "detail": "23.29% 지분 보유"},
            {"source": "현대글로비스", "target": "현대자동차", "type": "transaction", "detail": "2020년 11조원 이상 거래"},
        ],
        "risks": [
            {"type": "regulatory", "description": "공정거래법 개정으로 내부거래 규제 대상이 30%에서 20%로 강화될 예정", "severity": "high"},
            {"type": "governance", "description": "현대모비스 분할 및 합병 시 분할비율과 합병비율의 공정성 문제 발생 가능", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/222",
        "title": "현대차그룹의 지주회사 체제, 왜 하필 지금인가?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-05-10",
        "summary": "현대차그룹이 2018년 무산된 지배구조 개편을 재추진하려는 배경 분석. 공정거래법 개정으로 인한 규제 강화가 주요 원인.",
        "entities": [
            {"type": "company", "name": "현대차그룹", "role": "재벌그룹"},
            {"type": "company", "name": "현대모비스", "role": "지배구조의 정점"},
            {"type": "company", "name": "현대자동차", "role": "핵심 계열사"},
            {"type": "company", "name": "현대글로비스", "role": "종합물류 회사"},
            {"type": "person", "name": "정의선", "role": "현대차그룹 회장"},
            {"type": "person", "name": "정몽구", "role": "명예회장"},
        ],
        "relations": [
            {"source": "현대모비스", "target": "현대자동차", "type": "ownership", "detail": "21.43% 보유"},
            {"source": "정몽구-정의선", "target": "현대글로비스", "type": "ownership", "detail": "29.9% 지분 보유"},
        ],
        "risks": [
            {"type": "regulatory", "description": "2022년부터 사익 편취 규제 대상 확대로 현대글로비스와 이노션이 새로 규제 대상 포함", "severity": "high"},
            {"type": "governance", "description": "정의선 회장의 현대모비스 지분 0.32%로 극히 낮아 지배권 강화 필요", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/221",
        "title": "현대로템 철도부문 매각의 필요충분 조건?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-05-06",
        "summary": "현대차그룹의 현대로템 철도부문 매각설 분석. 방산업체 규제와 국가핵심기술 지정으로 인한 정부 승인 필요성 지적.",
        "entities": [
            {"type": "company", "name": "현대로템", "role": "철도부문 매각 대상 기업"},
            {"type": "company", "name": "현대차그룹", "role": "현대로템 최대 주주"},
            {"type": "company", "name": "지멘스", "role": "철도부문 인수 협상 상대"},
            {"type": "company", "name": "현대모비스", "role": "현대차 최대 주주"},
            {"type": "person", "name": "정의선", "role": "현대차그룹 회장"},
        ],
        "relations": [
            {"source": "현대차", "target": "현대로템", "type": "ownership", "detail": "33.7% 지분율 보유"},
        ],
        "risks": [
            {"type": "regulatory", "description": "방산업체 지분 외국 소유 및 국가핵심기술 보유 회사 인수에 산업자원부 장관 승인 필수", "severity": "critical"},
            {"type": "market", "description": "철도부문 3년 연속 적자, 저가 공세로 시장 경쟁력 약화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/220",
        "title": "실적 좋아진 현대로템을 매각한다고?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-05-03",
        "summary": "현대차그룹의 현대로템 매각설 보도 후 부인. 철도차량·방산·플랜트 부문 모두 수익성 개선 중.",
        "entities": [
            {"type": "company", "name": "현대로템", "role": "철도차량 및 플랜트 제조업체"},
            {"type": "company", "name": "현대차", "role": "현대로템의 최대 주주"},
            {"type": "company", "name": "지멘스", "role": "인수 가능성 보도된 기업"},
            {"type": "person", "name": "정의선", "role": "현대차그룹 회장"},
        ],
        "relations": [
            {"source": "현대차", "target": "현대로템", "type": "ownership", "detail": "현대차가 43.86% 지분 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "철도차량 부문 만성 적자 역사 및 신용등급 하락(A-에서 BBB+)", "severity": "high"},
            {"type": "governance", "description": "현대차의 현대로템 지원 축소 신호(전환사채 인수 거부)", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/219",
        "title": "왜 장산을 블루베리NFT의 최대주주로 세웠을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-04-29",
        "summary": "김병진 회장이 라이브플렉스 매각 후 경남제약 계열사를 대폭 개편. 블루베리NFT 최대주주를 개인회사 장산으로 변경.",
        "entities": [
            {"type": "company", "name": "블루베리NFT", "role": "유상증자 대상사"},
            {"type": "company", "name": "장산", "role": "최대주주"},
            {"type": "company", "name": "클라우드에어", "role": "전 최대주주"},
            {"type": "company", "name": "경남제약", "role": "계열사"},
            {"type": "company", "name": "라이브플렉스", "role": "매각대상"},
            {"type": "person", "name": "김병진", "role": "회장"},
        ],
        "relations": [
            {"source": "장산", "target": "블루베리NFT", "type": "ownership", "detail": "100억원 규모 제3자 배정 유상증자로 최대주주 지위 확보"},
            {"source": "김병진", "target": "장산", "type": "ownership", "detail": "1인 주주로 100% 지분 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "지분 이동을 통한 지배구조 급변으로 기업 안정성 우려", "severity": "high"},
            {"type": "financial", "description": "블루베리NFT 2020년 269억원 순손실, 현금흐름 악화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/218",
        "title": "부산주공에서 무슨 일이 벌어지고 있는 걸까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-04-22",
        "summary": "자동차 부품업체 부산주공은 5년 연속 영업적자와 설비 과잉 문제로 극적인 변화가 필요한 상황.",
        "entities": [
            {"type": "company", "name": "부산주공", "role": "자동차 부품업체 (주물 제조)"},
            {"type": "company", "name": "현대자동차", "role": "완성차 제조사"},
            {"type": "company", "name": "기아", "role": "완성차 제조사"},
            {"type": "company", "name": "세연에이엠", "role": "최대주주"},
            {"type": "person", "name": "장세훈", "role": "부산주공 대표이사, 동국제강 3세"},
        ],
        "relations": [
            {"source": "부산주공", "target": "현대자동차", "type": "supply", "detail": "자동차 부품 공급"},
        ],
        "risks": [
            {"type": "financial", "description": "5년 연속 영업적자, 지난해 말 부분잠식 상태", "severity": "critical"},
            {"type": "operational", "description": "설비 과잉 심각, 생산능력 16.8만톤 대비 실적 6.5만톤", "severity": "critical"},
            {"type": "financial", "description": "높은 이자부담, 지난해 이자비용 76억원이 당기손실의 57% 차지", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/217",
        "title": "김병진 장산 회장을 도운 우호 지분들",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-04-19",
        "summary": "김병진 장산 회장이 클라우드에어, 경남바이오파마, 경남제약을 인수하는 과정에서 우호세력들의 지분 지원 분석.",
        "entities": [
            {"type": "person", "name": "김병진", "role": "장산 회장"},
            {"type": "company", "name": "장산", "role": "주요 지주사"},
            {"type": "company", "name": "클라우드에어", "role": "자산관리회사"},
            {"type": "company", "name": "경남제약", "role": "의약품회사"},
            {"type": "company", "name": "경남바이오파마", "role": "바이오제약회사"},
            {"type": "company", "name": "위드윈홀딩스", "role": "우호 투자자"},
            {"type": "person", "name": "안성민", "role": "위드윈홀딩스 대표"},
        ],
        "relations": [
            {"source": "김병진", "target": "장산", "type": "ownership", "detail": "장산은 클라우드에어, 경남바이오파마, 경남제약의 핵심 지주사"},
        ],
        "risks": [
            {"type": "governance", "description": "수직 계열 구조에서 김병진 회장의 지배력이 강화, 지배구조 투명성 우려", "severity": "high"},
            {"type": "financial", "description": "2018-2019년 집중된 전환사채 발행으로 인한 미래 주식 희석 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/216",
        "title": "라이브플렉스 인수한 사모펀드의 배후는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-04-15",
        "summary": "라이브플렉스를 750억원에 인수한 지에프금융산업제1호 사모펀드의 배경 추적. 대부업체가 저축은행 자금을 활용한 기업 인수 구조 분석.",
        "entities": [
            {"type": "company", "name": "라이브플렉스", "role": "인수 대상 상장사"},
            {"type": "company", "name": "지에프금융산업제1호", "role": "인수자(사모펀드)"},
            {"type": "company", "name": "에이치비파이낸셜", "role": "경영진 파견 및 투자 실행사"},
            {"type": "company", "name": "한빛자산관리대부", "role": "자금 조달 주체"},
            {"type": "person", "name": "양은혁", "role": "한빛자산관리대부 최대주주"},
        ],
        "relations": [
            {"source": "지에프금융산업제1호", "target": "라이브플렉스", "type": "acquisition", "detail": "2021년 750억원(32.19% 지분)에 인수"},
            {"source": "에이치비파이낸셜", "target": "라이브플렉스", "type": "management", "detail": "신희민, 양은혁, 홍권표 등 경영진 배치"},
        ],
        "risks": [
            {"type": "financial", "description": "무자본에 가까운 인수 구조로 투자자금 회수 불확실", "severity": "high"},
            {"type": "governance", "description": "대부업체-저축은행-컨설팅사로 연결된 복잡한 지분 구조", "severity": "high"},
            {"type": "regulatory", "description": "자산유동화증권을 통한 자금 순환 구조가 감독당국 눈피할 우려", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/215",
        "title": "김병진과 안성민, 라이브플렉스에서 어떻게 엑시트했나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-04-12",
        "summary": "김병진 회장이 라이브플렉스 지분 16.09%를 지에프금융산업제1호에 매각. 1년 전 대규모 전환사채 발행과 연계된 구조적 엑시트 전략 분석.",
        "entities": [
            {"type": "person", "name": "김병진", "role": "라이브플렉스 회장, 지분 매각자"},
            {"type": "person", "name": "안성민", "role": "위드윈홀딩스 최대주주"},
            {"type": "company", "name": "라이브플렉스", "role": "피인수 대상사"},
            {"type": "company", "name": "지에프금융산업제1호", "role": "신규 최대주주"},
            {"type": "company", "name": "위드윈홀딩스", "role": "전환사채 보유사"},
        ],
        "relations": [
            {"source": "김병진", "target": "라이브플렉스", "type": "divestment", "detail": "16.09% 지분을 주당 3,184원에 지에프1호에 매각"},
            {"source": "지에프금융산업제1호", "target": "라이브플렉스", "type": "acquisition", "detail": "32.19% 지분을 총 750억원에 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "태일 인수 시 117억원 규모의 과도한 영업권 인식으로 손상차손 발생", "severity": "high"},
            {"type": "governance", "description": "1년 전 대규모 전환사채 발행 후 정확히 1년 만의 지분 매각으로 구조적 거래의혹", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/214",
        "title": "매각설 경남제약, 빌딩을 왜 샀을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-04-08",
        "summary": "경남제약이 김병진 회장의 지배구조 최상단 회사인 라이브플렉스 소유의 빌딩을 410억원에 매입.",
        "entities": [
            {"type": "company", "name": "경남제약", "role": "제약회사, 레모나 판매"},
            {"type": "company", "name": "라이브플렉스", "role": "지배구조 최상단 회사, 빌딩 소유"},
            {"type": "company", "name": "경남바이오파마", "role": "경남제약의 모회사"},
            {"type": "person", "name": "김병진", "role": "라이브플렉스 전 최대주주"},
        ],
        "relations": [
            {"source": "경남제약", "target": "라이브플렉스타워 빌딩", "type": "acquisition", "detail": "410억원에 양수, 274억5000만원 은행차입금 포함"},
        ],
        "risks": [
            {"type": "governance", "description": "지배구조 최상단 회사의 빌딩을 자회사가 고가에 매입하는 관련거래", "severity": "critical"},
            {"type": "financial", "description": "빌딩 매입을 위해 274억원 이상 신규 차입, 부채 급증", "severity": "high"},
            {"type": "operational", "description": "외주가공비가 76% 증가, 내부 설비 활용 부족", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/213",
        "title": "iHQ 8년만의 전환사채 발행 왜?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-04-05",
        "summary": "필룩스그룹에 인수된 iHQ가 8년 만에 200억원 규모의 전환사채 발행. 충분한 유동성 보유 상황에서의 발행 의도 분석.",
        "entities": [
            {"type": "company", "name": "iHQ", "role": "엔터테인먼트 회사, 전환사채 발행사"},
            {"type": "company", "name": "필룩스그룹", "role": "iHQ 인수사, 모회사"},
            {"type": "person", "name": "배상윤", "role": "필룩스그룹 회장"},
            {"type": "person", "name": "박종진", "role": "iHQ 경영진, 방송인 출신"},
        ],
        "relations": [
            {"source": "필룩스그룹", "target": "iHQ", "type": "acquisition", "detail": "배상윤 회장의 필룩스그룹이 iHQ 인수 완료"},
            {"source": "iHQ", "target": "에스에스2호조합", "type": "cb_issuance", "detail": "200억원 규모 사모 전환사채 발행"},
        ],
        "risks": [
            {"type": "governance", "description": "그룹 계열사 간 자금거래 활발화로 독립적 경영 우려", "severity": "high"},
            {"type": "financial", "description": "자금 사용처 명확하지 않음, 공시상 '신규사업' 명목이나 실제 대상 미확정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/212",
        "title": "남궁견 회장에게 엔케이물산의 역할은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-04-01",
        "summary": "남궁견 회장이 2006년 엔케이물산을 인수한 이후 지속적인 기업 인수·매각을 반복. 엔케이물산은 자금조달과 기업 장사의 수단으로 기능.",
        "entities": [
            {"type": "person", "name": "남궁견", "role": "회장/투자자"},
            {"type": "company", "name": "엔케이물산", "role": "상장사/지주회사"},
            {"type": "company", "name": "하나모두", "role": "모회사"},
            {"type": "company", "name": "미래아이앤지", "role": "자회사"},
            {"type": "company", "name": "포비스티앤씨", "role": "자회사"},
        ],
        "relations": [
            {"source": "남궁견", "target": "엔케이물산", "type": "ownership", "detail": "2006년 11월 하나모두·세종로봇을 통해 최대주주 등극"},
        ],
        "risks": [
            {"type": "governance", "description": "관련자 거래와 지배구조 투명성 문제", "severity": "critical"},
            {"type": "financial", "description": "60억원 투자 골드플러스에서 43억원 감액손실, 반복되는 손실 매각", "severity": "high"},
            {"type": "operational", "description": "본업 부재로 지속적 현금흐름 창출 불가, 영업손실 심화 추세", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/211",
        "title": "미래아이앤지, 포비스티앤씨 매각자금 어디에 쓸까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-03-29",
        "summary": "미래아이앤지가 포비스티앤씨 지분을 497억원에 매각하여 약 207억원의 수익. 매각 자금으로 아티스트코스메틱 유상증자와 판타지오 지분 인수.",
        "entities": [
            {"type": "company", "name": "미래아이앤지", "role": "포비스티앤씨 지분 보유사"},
            {"type": "company", "name": "포비스티앤씨", "role": "미래아이앤지에 의해 매각된 기업"},
            {"type": "company", "name": "엔케이물산", "role": "미래아이앤지의 모회사"},
            {"type": "company", "name": "광림그룹", "role": "포비스티앤씨 인수사"},
            {"type": "company", "name": "아티스트코스메틱", "role": "미래아이앤지의 종속회사"},
            {"type": "company", "name": "판타지오", "role": "아티스트코스메틱이 인수한 엔터테인먼트 회사"},
            {"type": "person", "name": "남궁견", "role": "회장"},
        ],
        "relations": [
            {"source": "미래아이앤지", "target": "포비스티앤씨", "type": "divestment", "detail": "지분 22.6%를 497억원에 광림그룹에 매각"},
        ],
        "risks": [
            {"type": "operational", "description": "솔루션 사업 외 방산·콘텐츠 부문 매출 부재로 단일 사업 의존 상태", "severity": "high"},
            {"type": "financial", "description": "영업활동 현금흐름이 매년 20-30억원 적자로 본업 수익성 악화", "severity": "high"},
            {"type": "financial", "description": "자산회전율 0.06배로 자산 규모 대비 매출 창출 능력 극히 미약", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/210",
        "title": "엔케이물산은 왜 포비스티앤씨를 팔아야 했을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-03-25",
        "summary": "남궁견 회장의 기업사냥 전략으로 성장한 엔케이물산이 계열사 중 최대 자산 규모인 포비스티앤씨를 매각.",
        "entities": [
            {"type": "company", "name": "엔케이물산", "role": "상장사, 기업그룹 모회사"},
            {"type": "company", "name": "포비스티앤씨", "role": "소프트웨어 총판업체, 판매 대상"},
            {"type": "company", "name": "미래아이앤지", "role": "계열사, 영상콘텐츠 회사"},
            {"type": "person", "name": "남궁견", "role": "엔케이물산 회장, 기업사냥꾼"},
        ],
        "relations": [
            {"source": "남궁견", "target": "엔케이물산", "type": "ownership", "detail": "2006년 고려포리머 인수 후 회사명 변경"},
            {"source": "엔케이물산", "target": "포비스티앤씨", "type": "divestment", "detail": "자산총액 1124억원 규모의 계열사 매각"},
        ],
        "risks": [
            {"type": "financial", "description": "2019년까지 4년 연속 영업적자 지속, 관리종목 지정 가능 수준", "severity": "critical"},
            {"type": "operational", "description": "영상콘텐츠 사업 2018년 이후 매출 거의 없음", "severity": "high"},
            {"type": "financial", "description": "2017년 이후 외부자금 유입 단절", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (30차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}... ({result.get('error', 'Unknown')})")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
