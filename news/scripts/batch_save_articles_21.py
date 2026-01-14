#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 21차 (삼성/LG/롯데/에스엠 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/413",
        "title": "상장기업 현금사정 크게 나빠졌다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-03-30",
        "summary": "코스피 상장기업들의 2022년 실적에서 매출은 소폭 증가했으나 영업이익과 당기순이익은 크게 감소. 운전자본 증가로 영업활동 현금흐름이 40% 감소, 기업들은 차입금과 사모시장을 통해 부족한 자금 조달.",
        "entities": [
            {"type": "company", "name": "코스피 상장기업", "role": "분석대상"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "차입금 비중 증가로 재무구조 악화 가능성", "severity": "high"},
            {"type": "financial", "description": "고금리 전환으로 금융비용 부담 증가", "severity": "high"},
            {"type": "market", "description": "금융자산 가치 하락 및 기타포괄손익 감소", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/412",
        "title": "공모 회사채 시장은 귀족기업만의 놀이터",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-03-27",
        "summary": "한국 공모 회사채 시장은 A등급 이상 기업에 한정되어 양극화 심각. 277개 기업만 공모채 발행, 3,930개는 정책 프로그램 의존.",
        "entities": [
            {"type": "company", "name": "애플", "role": "사례 기업"},
            {"type": "company", "name": "삼성전자", "role": "비교 대상"},
            {"type": "company", "name": "현대자동차", "role": "비교 대상"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "주요 상장사 부채 40%가 1년 내 만기, 차환 취약성", "severity": "high"},
            {"type": "market", "description": "투기등급 공모채 시장 부재로 성장기업 자금조달 제약", "severity": "high"},
            {"type": "financial", "description": "신용경색 시 AAA 외 기업에 불균형 영향", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/411",
        "title": "삼성생명 자기자본이 어쯔다 반토막 됐나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-03-23",
        "summary": "삼성생명 자기자본 34조원에서 17조원으로 반감. 주요 원인은 16조원 기타포괄손실. 금리 상승과 주가 하락으로 매도가능금융자산 평가손실 발생.",
        "entities": [
            {"type": "company", "name": "삼성생명", "role": "주요 대상"},
            {"type": "company", "name": "삼성전자", "role": "자산 보유 대상"},
        ],
        "relations": [
            {"source": "삼성생명", "target": "삼성전자", "type": "ownership", "detail": "8.51% 지분 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "자기자본 반감으로 RBC비율 304%→244% 저하, 지급여력 건전성 악화", "severity": "high"},
            {"type": "regulatory", "description": "만기보유금융자산 분류 폐지로 4조9천억원 미인식 손실 표면화 예정", "severity": "high"},
            {"type": "governance", "description": "회계 재분류를 통한 평가손실 은폐는 회계 투명성 문제", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/410",
        "title": "사상 최대 실적 낸 삼성물산, 자산 왜 줄었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-03-20",
        "summary": "삼성물산 2022년 영업이익 9,394억원, 순이익 1조4,618억원으로 사상 최대 실적. 그러나 자산총액은 44조원에서 39조원으로 감소. 삼성전자 주가 하락으로 6조8,728억원 평가손실.",
        "entities": [
            {"type": "company", "name": "삼성물산", "role": "주요 대상"},
            {"type": "company", "name": "삼성전자", "role": "자회사 지분"},
            {"type": "company", "name": "삼성생명", "role": "자회사 지분"},
            {"type": "company", "name": "삼성바이오로직스", "role": "자회사 지분"},
        ],
        "relations": [
            {"source": "삼성물산", "target": "삼성전자", "type": "ownership", "detail": "5.01% 지분 2대주주"},
            {"source": "삼성물산", "target": "삼성바이오로직스", "type": "ownership", "detail": "43.1% 지분"},
        ],
        "risks": [
            {"type": "market", "description": "삼성전자 주가 하락으로 6조8,728억원 평가손실 기타포괄손익 반영", "severity": "high"},
            {"type": "financial", "description": "총자산 중 21조6,000억원이 상장주식으로 시장변동성에 높은 노출", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/409",
        "title": "작년 이맘때 321개사, 올해는 70개사",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-03-16",
        "summary": "2023년 초 회사채 시장 회복 조짐, 3월 9일까지 17.69조원 발행. 그러나 시장 접근은 최상위 신용등급 기업에 제한되어 70개사만 발행 성공, 작년 321개사 대비 급감.",
        "entities": [
            {"type": "company", "name": "SK㈜", "role": "채권 발행사"},
            {"type": "company", "name": "SK텔레콤", "role": "채권 발행사"},
            {"type": "company", "name": "한국전력", "role": "시장 안정화 역할"},
        ],
        "relations": [],
        "risks": [
            {"type": "market", "description": "회사채 시장 접근이 최고등급 발행사에 제한, 중견기업 심각한 자금조달 제약", "severity": "critical"},
            {"type": "financial", "description": "만기 불일치로 단기금융 의존, 장기 투자 능력 저하", "severity": "high"},
            {"type": "financial", "description": "유동성 제약 재발 시 시스템 디폴트 위험", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/408",
        "title": "에스엠, 비핵심자산 매각 Go? Stop?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-03-13",
        "summary": "법원의 가처분 결정으로 카카오의 신주 인수가 저지되면서 에스엠 경영권 분쟁 판도 변화. 하이브가 최대주주 지위 확보 가능성 높아짐. 비핵심자산 매각 검토 중.",
        "entities": [
            {"type": "company", "name": "SM엔터테인먼트", "role": "주제 회사"},
            {"type": "company", "name": "카카오", "role": "2대 주주 후보"},
            {"type": "company", "name": "하이브", "role": "최대주주 후보"},
            {"type": "company", "name": "얼라인파트너스", "role": "행동주의 투자자"},
            {"type": "person", "name": "이수만", "role": "창업자"},
            {"type": "company", "name": "SM Culture & Contents", "role": "매각 검토 대상"},
            {"type": "company", "name": "키이스트", "role": "매각 검토 대상"},
        ],
        "relations": [
            {"source": "이수만", "target": "하이브", "type": "share_sale", "detail": "14.8% 지분 4228억원 매각"},
        ],
        "risks": [
            {"type": "governance", "description": "카카오 신주 인수 금지로 현 경영진 경영권 안정성 저하", "severity": "high"},
            {"type": "operational", "description": "비핵심자산 매각 시 음원 유통 구조 변화 위험", "severity": "high"},
            {"type": "financial", "description": "우선적 신주인수권 부여로 일반 주주 지분 희석 위험", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/407",
        "title": "카카오, 링에 오르나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-03-06",
        "summary": "카카오가 에스엠과의 전략적 제휴에서 경영권 확보로 전략 수정, 하이브와 경영권 분쟁 심화. 에스엠 경영진은 주주환원 정책 강화하고 카카오에 우선적 신주인수권 부여로 하이브 공개매수 저지.",
        "entities": [
            {"type": "company", "name": "카카오", "role": "경영권 추구자"},
            {"type": "company", "name": "하이브", "role": "적대적 인수자"},
            {"type": "company", "name": "에스엠", "role": "경영권 분쟁 대상"},
            {"type": "company", "name": "카카오엔터", "role": "카카오 자회사"},
            {"type": "company", "name": "얼라인파트너스", "role": "현 경영진 지원"},
            {"type": "person", "name": "이수만", "role": "최대주주"},
        ],
        "relations": [
            {"source": "카카오", "target": "에스엠", "type": "strategic_shift", "detail": "전략적 제휴에서 경영권 확보로 전환"},
            {"source": "하이브", "target": "에스엠", "type": "hostile_takeover", "detail": "12만원 공개매수로 25% 추가 취득 시도"},
        ],
        "risks": [
            {"type": "governance", "description": "우선적 신주인수권 조항이 카카오 경영권 확보 도구로 활용 가능성", "severity": "high"},
            {"type": "legal", "description": "하이브의 발행금지 가처분신청으로 카카오 신주 인수 불발 가능성", "severity": "high"},
            {"type": "market", "description": "공개매수 경쟁으로 장기 경영권 분쟁 기업가치 훼손 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/406",
        "title": "하이브와 카카오의 동거는 불가능할까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-03-02",
        "summary": "SM엔터테인먼트 경영권 분쟁 분석. 하이브 공개매수와 카카오 2대주주 등극 과정에서 소액주주 역할 중심으로 전개. 하이브와 카카오가 협력하는 동거 시나리오가 SM 성장에 최선일 수 있음 제안.",
        "entities": [
            {"type": "company", "name": "하이브", "role": "최대주주 후보"},
            {"type": "company", "name": "카카오", "role": "2대주주 예정"},
            {"type": "company", "name": "SM엔터테인먼트", "role": "경영권 분쟁 대상"},
            {"type": "person", "name": "이수만", "role": "전 최대주주"},
            {"type": "company", "name": "얼라인파트너스", "role": "행동주의 펀드"},
            {"type": "company", "name": "두나무", "role": "하이브-카카오 연결고리"},
            {"type": "company", "name": "국민연금", "role": "기관투자가"},
        ],
        "relations": [
            {"source": "하이브", "target": "이수만", "type": "share_agreement", "detail": "공동보유 약정, 이수만 풋옵션 보유"},
            {"source": "하이브", "target": "두나무", "type": "strategic_alliance", "detail": "2021년 상호 출자, NFT 합작투자"},
        ],
        "risks": [
            {"type": "governance", "description": "이수만 풋옵션으로 하이브가 3.65% 지분 강제 인수 가능, 콜옵션 부재로 지분 통제 어려움", "severity": "high"},
            {"type": "legal", "description": "신주 및 전환사채 발행금지 가처분 법원 판단이 주총 양상 변화시킬 변수", "severity": "high"},
            {"type": "market", "description": "주가가 공개매수 마감일까지 12만원 상회 시 하이브 지분율 목표 이하 하락", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/405",
        "title": "얼라인파트너스는 언제까지 싸울까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-02-27",
        "summary": "에스엠 경영권 분쟁에서 얼라인파트너스 역할 변화 분석. 이수만 지분 매각으로 싸움 구도가 하이브와 현 경영진 간 대립으로 변모. 얼라인파트너스는 0.91% 지분으로 직접 영향력 상실.",
        "entities": [
            {"type": "company", "name": "에스엠엔터테인먼트", "role": "경영권 분쟁 대상"},
            {"type": "company", "name": "얼라인파트너스", "role": "행동주의 펀드"},
            {"type": "company", "name": "하이브", "role": "이수만 지분 인수"},
            {"type": "company", "name": "카카오", "role": "9.05% 협력자"},
            {"type": "person", "name": "이수만", "role": "전 최대주주"},
            {"type": "person", "name": "이성수", "role": "에스엠 대표이사"},
            {"type": "person", "name": "방시혁", "role": "하이브 의장"},
        ],
        "relations": [
            {"source": "얼라인파트너스", "target": "에스엠", "type": "shareholder", "detail": "0.91% 지분 보유, 주주제안으로 지배구조 개선 추진"},
            {"source": "이수만", "target": "에스엠", "type": "related_party", "detail": "라이크기획, CT Planning 개인회사를 통한 역외 거래"},
        ],
        "risks": [
            {"type": "governance", "description": "최대주주 교체로 지배구조 불안정성", "severity": "high"},
            {"type": "legal", "description": "이수만의 라이크기획, CT Planning을 통한 역외 탈세 의혹, 법적 분쟁 가능성", "severity": "critical"},
            {"type": "operational", "description": "경영권 분쟁 장기화로 핵심 사업 추진 지연", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/404",
        "title": "이수만과 측근들은 어떻게 갈라섰을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-02-23",
        "summary": "SM엔터테인먼트 최대주주 이수만과 경영진 관계 악화 과정 분석. 얼라인파트너스 주주제안으로 지배구조 개편, 라이크기획 계약 종료, 카카오 지분 투자로 이어진 갈등 추적.",
        "entities": [
            {"type": "person", "name": "이수만", "role": "SM 최대주주, 프로듀서"},
            {"type": "person", "name": "이성수", "role": "SM 공동 대표이사"},
            {"type": "person", "name": "이창환", "role": "얼라인파트너스 창업자"},
            {"type": "person", "name": "방시혁", "role": "하이브 이사회 의장"},
            {"type": "company", "name": "SM엔터테인먼트", "role": "주제 회사"},
            {"type": "company", "name": "카카오", "role": "지분투자자"},
            {"type": "company", "name": "하이브", "role": "구주 인수자"},
            {"type": "company", "name": "얼라인파트너스", "role": "행동주의 투자자"},
            {"type": "company", "name": "라이크기획", "role": "이수만 개인회사"},
            {"type": "company", "name": "CT Planning", "role": "이수만 홍콩 개인회사"},
        ],
        "relations": [
            {"source": "이수만", "target": "이성수", "type": "conflict", "detail": "최측근 관계에서 의견 대립으로 결별"},
            {"source": "카카오", "target": "SM엔터테인먼트", "type": "investment", "detail": "1119억원 유상증자, 1052억원 전환사채로 9.05% 취득"},
        ],
        "risks": [
            {"type": "governance", "description": "최대주주와 경영진 갈등으로 지배구조 불안정. 이수만 경영 배제.", "severity": "critical"},
            {"type": "legal", "description": "이수만이 신주 및 전환사채 발행 금지 가처분 신청, 지분 분쟁 위험", "severity": "high"},
            {"type": "financial", "description": "라이크기획에 총 1666억원 지급. CT Planning 계약 취소 시 추가 손실 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/403",
        "title": "하이브, 인수자금은 충분한가",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-02-20",
        "summary": "하이브가 에스엠 지분 39.8% 확보를 위해 약 1조 1,371억원 투자 계획. 단기간에 대규모 자금 필요한 상황에서 현금 유동성 부족으로 재무 부담 우려.",
        "entities": [
            {"type": "company", "name": "하이브", "role": "인수자"},
            {"type": "company", "name": "에스엠엔터테인먼트", "role": "인수대상"},
            {"type": "person", "name": "이수만", "role": "에스엠 최대주주"},
            {"type": "company", "name": "얼라인파트너스", "role": "행동주의 펀드"},
        ],
        "relations": [
            {"source": "하이브", "target": "에스엠", "type": "acquisition", "detail": "지분 39.8% 인수 계획, 3월 2일까지 1조 1,371억원 투자"},
            {"source": "이수만", "target": "하이브", "type": "share_transfer", "detail": "지분 14.8% 매각 및 25% 공개매수"},
        ],
        "risks": [
            {"type": "financial", "description": "9월말 현금 유동성 약 8,700억원으로 필요 자금 1조 1,371억원에 미달", "severity": "high"},
            {"type": "financial", "description": "순차입금이 현재 46억원에서 1조원 이상으로 급증 가능성", "severity": "high"},
            {"type": "operational", "description": "차입금 증가로 공격적 투자 행보에 브레이크 걸릴 수 있음", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/402",
        "title": "대우건설의 사업 포기, 단발성일까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-02-16",
        "summary": "대우건설이 울산 일산동 주상복합 사업을 포기하면서 부동산PF 위기감 재고조. 미착공 상태에서 440억원 후순위 차입금 보증 손실 감수. 8개 추가 미착공 사업장에서 8,971억원 채무보증 보유.",
        "entities": [
            {"type": "company", "name": "대우건설", "role": "시공사"},
            {"type": "company", "name": "팜헤이븐플래닝", "role": "시행사"},
            {"type": "company", "name": "에이블동일제일차", "role": "SPC"},
            {"type": "company", "name": "KB증권", "role": "유동화프로그램 구성"},
        ],
        "relations": [
            {"source": "대우건설", "target": "팜헤이븐플래닝", "type": "contract", "detail": "2021년 시공계약, 440억원 후순위 차입금 연대보증"},
        ],
        "risks": [
            {"type": "financial", "description": "울산 일산동 사업 포기로 440억원 손실, 미착공 8개 사업장 추가 손실 위험", "severity": "critical"},
            {"type": "market", "description": "부동산 경기 침체로 미분양 위험 증가, 특히 울산, 대전 지역 위험 높음", "severity": "high"},
            {"type": "financial", "description": "1분기 만기 유동화증권 6,249억원 상환 어려움, 신용보강 의존도 높음", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/401",
        "title": "코스피 상장사 자금사정 어떻게 변했을까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-02-13",
        "summary": "금리 급등으로 코스피 상장사들 자금사정 악화. 영업활동 현금흐름 60% 이상 감소, 420개사 현금 부족 상태, 단기차입금 200조원 초과.",
        "entities": [
            {"type": "company", "name": "한국전력", "role": "영업활동 현금적자 기업"},
            {"type": "company", "name": "한국가스공사", "role": "영업활동 현금적자 기업"},
            {"type": "company", "name": "삼성전자", "role": "현금 부족 기업"},
            {"type": "company", "name": "롯데건설", "role": "부도 위험 기업"},
            {"type": "company", "name": "태영건설", "role": "고금리 차환 기업"},
        ],
        "relations": [
            {"source": "롯데건설", "target": "부동산PF 시장", "type": "crisis_indicator", "detail": "부도 위험으로 신용경색 현상 심화"},
        ],
        "risks": [
            {"type": "financial", "description": "영업현금흐름 악화로 276개사가 지출초과 상태, 420개사가 잉여현금흐름 부족", "severity": "critical"},
            {"type": "market", "description": "부동산PF 유동화증권 차환 금리 13~15%로 상승, 신용경색 현상", "severity": "critical"},
            {"type": "financial", "description": "단기차입금 비중 40%로 높아 분기당 전체 차입금 10% 상환 의무 발생", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/400",
        "title": "IPO로 들어온 10조, 빛의 속도로 줄고 있다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-02-09",
        "summary": "LG에너지솔루션이 2022년 초 IPO로 조성한 10조원 자금이 9개월 만에 절반 소진. 해외 자회사 설비투자 지원과 차입금 상환에 자금 집중. 올해 7조원 추가 투자 계획으로 재무 부담 심화 예상.",
        "entities": [
            {"type": "company", "name": "LG에너지솔루션", "role": "주요 대상사"},
            {"type": "company", "name": "LG화학", "role": "모회사"},
            {"type": "company", "name": "혼다", "role": "합작사"},
            {"type": "company", "name": "스텔란티스", "role": "합작사"},
            {"type": "company", "name": "SK온", "role": "분쟁 상대사"},
        ],
        "relations": [
            {"source": "LG에너지솔루션", "target": "LG화학", "type": "ownership", "detail": "물적분할 후 LG화학이 구주 판매로 2조5500억원 수익"},
            {"source": "LG에너지솔루션", "target": "혼다", "type": "partnership", "detail": "2조4000억원 규모 합작투자 계약"},
        ],
        "risks": [
            {"type": "financial", "description": "IPO 자금 급속 소진, 5조원 현금 보유액이 출자와 단기 차입금 상환에 이미 할당", "severity": "critical"},
            {"type": "operational", "description": "자회사 단기성 차입금이 1년 9개월간 2배 이상 증가, 상환 능력 부족 위험", "severity": "high"},
            {"type": "financial", "description": "올해 설비투자 목표 7조원 규모로 추가 자금 조달 필요", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/399",
        "title": "LG에너지솔루션을 키운 8할은 IPO였다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-02-06",
        "summary": "LG에너지솔루션은 2020년 12월 LG화학에서 분할, 2022년 1월 상장. 지난해 매출 25조5986억원으로 43.4% 증가. IPO로 조달한 10조2000억원이 대규모 해외 투자의 주요 자금원이나 현금흐름 악화 구조적 문제 존재.",
        "entities": [
            {"type": "company", "name": "LG에너지솔루션", "role": "분석 대상"},
            {"type": "company", "name": "LG화학", "role": "모회사"},
        ],
        "relations": [
            {"source": "LG화학", "target": "LG에너지솔루션", "type": "spin-off", "detail": "2020년 12월 물적분할"},
        ],
        "risks": [
            {"type": "financial", "description": "매출 및 영업이익 증가에도 현금 주머니 가벼워지고 추가 자금 조달 없이 지속 가능성 불확실", "severity": "high"},
            {"type": "operational", "description": "연간 6조원 이상 설비투자 계획 대비 미발생 자본적 지출 약정액 4조3000억원", "severity": "high"},
            {"type": "market", "description": "세계 시장 점유율 20%대에서 14%로 하락, 중국 배터리업체 경쟁 심화", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/398",
        "title": "그 많았던 현금 다 어디에 썼길래",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-02-02",
        "summary": "LG화학은 LG에너지솔루션 IPO로 15조원 확보했으나, 석유화학 부문 실적 부진과 AVEO 제약회사 인수로 현금 급속 소진. 회사채 8000억원 발행은 만기 채무 상환과 인수대금 지급용.",
        "entities": [
            {"type": "company", "name": "LG화학", "role": "모회사"},
            {"type": "company", "name": "LG에너지솔루션", "role": "자회사"},
            {"type": "company", "name": "AVEO Pharmaceuticals", "role": "인수 대상"},
        ],
        "relations": [
            {"source": "LG화학", "target": "LG에너지솔루션", "type": "ownership", "detail": "물적분할 및 IPO, 구주 매각으로 2조5500억원 조성"},
            {"source": "LG화학", "target": "AVEO Pharmaceuticals", "type": "acquisition", "detail": "2023년 1월 완료, 인수가 7072억원"},
        ],
        "risks": [
            {"type": "financial", "description": "모회사 현금 유동성 악화. 9월말 1조2000억원에서 AVEO 인수 및 채무상환으로 극도로 감소", "severity": "high"},
            {"type": "operational", "description": "석유화학 부문 실적 부진으로 영업현금흐름 악화. 나프타 가격 상승으로 영업이익 2조원 이상 감소", "severity": "high"},
            {"type": "financial", "description": "차입금 의존도 증가. 개별 LG화학 총차입금 7조8000억원, 순차입금 6조5000억원 사상 최대", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/397",
        "title": "롯데건설, 아직 갈 길이 멀다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-30",
        "summary": "롯데건설이 메리츠금융그룹과 투자협약으로 1조5000억원 유동성 확보했으나, 올해 만기도래 차입금 약 2조5000억원에 비해 부족. 미착공 사업장 비중 높고 부동산경기 침체로 차환 부담 전망.",
        "entities": [
            {"type": "company", "name": "롯데건설", "role": "주요 대상사"},
            {"type": "company", "name": "메리츠금융그룹", "role": "투자 파트너"},
        ],
        "relations": [
            {"source": "롯데건설", "target": "메리츠금융그룹", "type": "investment", "detail": "공동펀드를 통한 부동산PF 유동화증권 매입협약"},
        ],
        "risks": [
            {"type": "financial", "description": "1조5000억원 유동성으로는 올해 약 2조5000억원 만기 차입금 상환에 부족", "severity": "critical"},
            {"type": "market", "description": "부동산경기 부진으로 2021년 이후 현금부족 흐름 올해까지 이어질 가능성", "severity": "high"},
            {"type": "operational", "description": "미착공 사업장이 6조9775억원 유동화증권 중 4조4126억원으로 매우 높음", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/396",
        "title": "롯데건설은 부동산PF 위기 어떻게 봉합했나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-26",
        "summary": "롯데건설이 레고랜드 사태 이후 부동산PF 유동성 위기에 직면했으나, 메리츠금융그룹과 1조5000억원 규모 투자협약으로 위기 극복. 다만 높은 금리 차입과 우발채무 문제 여전.",
        "entities": [
            {"type": "company", "name": "롯데건설", "role": "위기 대상"},
            {"type": "company", "name": "메리츠금융그룹", "role": "유동화증권 인수자"},
            {"type": "company", "name": "롯데그룹", "role": "모회사"},
            {"type": "company", "name": "태영건설", "role": "유사 위기 사례"},
            {"type": "company", "name": "롯데케미칼", "role": "차입금 제공 계열사"},
            {"type": "company", "name": "호텔롯데", "role": "TRS 계약 체결 계열사"},
        ],
        "relations": [
            {"source": "롯데건설", "target": "메리츠금융그룹", "type": "transaction", "detail": "1조5000억원 규모 유동화증권 매입 및 투자협약"},
            {"source": "롯데건설", "target": "롯데케미칼", "type": "debt", "detail": "5000억원 및 추가 3000억원 차입"},
        ],
        "risks": [
            {"type": "financial", "description": "초단기 차입금 높은 금리(연 10% 이상) 및 연쇄 차환 리스크", "severity": "high"},
            {"type": "financial", "description": "전환사채 금리 10.03%로 매우 높으며, 3년 후 상환 의무", "severity": "high"},
            {"type": "market", "description": "부동산PF 차환 시장 위축으로 금융권 전반에 미칠 영향", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/395",
        "title": "SK온, 6조원 유동성 차입금 갚을 묘수 있나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-24",
        "summary": "SK온이 북미 배터리 공장 투자를 위해 64억 달러 조달 필요한 상황에서 동시에 6조 이상 유동성 차입금 상환 압박. 영업현금흐름이 마이너스인 상황에서 자본확충 없이는 악순환 탈피 어려울 전망.",
        "entities": [
            {"type": "company", "name": "SK온", "role": "배터리 제조사"},
            {"type": "company", "name": "SK이노베이션", "role": "모회사"},
            {"type": "company", "name": "블루오벌SK", "role": "포드 합작법인"},
            {"type": "company", "name": "SK배터리 아메리카", "role": "SK온 미국 자회사"},
            {"type": "company", "name": "Ford Motor", "role": "합작 파트너"},
            {"type": "company", "name": "LG에너지솔루션", "role": "분쟁 상대방"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "SK온", "type": "spin-off", "detail": "배터리 사업 물적분할로 설립"},
            {"source": "SK온", "target": "LG에너지솔루션", "type": "settlement", "detail": "총 1조원 지급 합의"},
        ],
        "risks": [
            {"type": "financial", "description": "1년 이내 상환 차입금 6조1723억원(전체 62.1%), 단기차입금 5조2700억원", "severity": "critical"},
            {"type": "operational", "description": "연결실체 영업활동 현금흐름 마이너스 1조4523억원으로 자체 현금창출 불가", "severity": "critical"},
            {"type": "financial", "description": "북미 배터리 공장 투자로 64억 달러(약 8조원) 추가 자금 필요", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/394",
        "title": "실망스런 SK온 프리IPO, 모회사에 후폭풍 불까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-19",
        "summary": "SK온의 지난해 프리IPO는 기대에 미치지 못했으며, 모회사 SK이노베이션이 유상증자 규모 중 2조원 직접 투입. SK이노베이션은 현금부족과 단기차입금 증가로 재무압박, 신용등급 추가 하락 위험.",
        "entities": [
            {"type": "company", "name": "SK온", "role": "배터리 사업 자회사"},
            {"type": "company", "name": "SK이노베이션", "role": "모회사"},
            {"type": "company", "name": "한국기업평가", "role": "신용평가사"},
            {"type": "company", "name": "NICE신용평가", "role": "신용평가사"},
        ],
        "relations": [
            {"source": "SK온", "target": "SK이노베이션", "type": "subsidiary", "detail": "SK이노베이션이 물적분할로 SK온 설립, 지분 보유"},
            {"source": "SK이노베이션", "target": "SK온", "type": "investment", "detail": "프리IPO 유상증자에 2조원 투입"},
        ],
        "risks": [
            {"type": "financial", "description": "SK이노베이션 보유 현금 약 1조2000억원, 1년내 상환 차입금이 1조2000억원 초과", "severity": "high"},
            {"type": "governance", "description": "순차입금이 EBITDA 4~5배 초과 시 신용등급 하향조정 검토 대상", "severity": "high"},
            {"type": "operational", "description": "프리IPO 부진으로 예정된 배터리 부문 투자(약 14조원) 재정 압박 증대", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/393",
        "title": "매력 떨어진 롯데쇼핑 ABCP, 차환발행 잘 되고 있나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-16",
        "summary": "롯데그룹의 인천종합터미널 부지 매입 자금조달 과정에서 복잡한 3중 유동화 구조 형성. 낮은 할인율 ABCP 차환발행이 시장금리 상승으로 어려움. 아이코스제이차 기업어음 298억원 미매각으로 한국투자증권 인수 상황.",
        "entities": [
            {"type": "company", "name": "롯데쇼핑", "role": "주요 차주 관련사"},
            {"type": "company", "name": "롯데인천개발", "role": "원 채무자"},
            {"type": "company", "name": "KB증권", "role": "자산유동화 주관사"},
            {"type": "company", "name": "한국투자증권", "role": "유동성공여 약정체결사"},
            {"type": "company", "name": "국민은행", "role": "대주단 참여 및 주관회사"},
            {"type": "company", "name": "롯데캐피탈", "role": "신용보강 제공사"},
        ],
        "relations": [
            {"source": "롯데인천개발", "target": "엘인천제일차(유)", "type": "debt", "detail": "3000억원 차입금"},
            {"source": "한국투자증권", "target": "아이코스제이차", "type": "liquidity_support", "detail": "기업어음 매입 약정"},
        ],
        "risks": [
            {"type": "market", "description": "2.05% 할인율 ABCP 차환발행 실패로 유동성 위험. 시장금리 상승으로 차환 어려운 환경", "severity": "high"},
            {"type": "operational", "description": "3중 유동화 구조로 복잡성 증가. 아이코스제이차 기업어음 298억원 미매각으로 한국투자증권 보유 부담", "severity": "high"},
            {"type": "regulatory", "description": "엘인천제일차, 엘인천제이차 공시 의무 위반. 500억원 이상 자산규모 법개정 이후에도 공시 없음", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/392",
        "title": "롯데쇼핑 8000억원짜리 빚의 정체",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-12",
        "summary": "롯데그룹이 2012년 인천종합터미널 부지를 9000억원에 매입하면서 조성한 7000억원 차입금이 유동화 과정을 거쳐 현재 8000억원으로 증가해 롯데쇼핑 장부에 남아있음. 2월 23일 만기 도래 앞두고 상환 가능성 의문.",
        "entities": [
            {"type": "company", "name": "롯데쇼핑", "role": "차입금 보유 기업"},
            {"type": "company", "name": "롯데인천개발", "role": "부지 매입 주체"},
            {"type": "company", "name": "에이치앤디에이블(유)", "role": "SPC"},
            {"type": "company", "name": "현대증권", "role": "ABCP 인수기관"},
        ],
        "relations": [
            {"source": "롯데그룹", "target": "인천종합터미널 부지", "type": "acquisition", "detail": "2013년 1월 최종 매매계약, 9000억원 규모"},
            {"source": "롯데인천개발", "target": "롯데쇼핑", "type": "merger", "detail": "지난해 흡수합병, 8000억원 차입금 이전"},
        ],
        "risks": [
            {"type": "financial", "description": "8000억원 차입금 만기가 2월 23일 임박, 롯데쇼핑 자금사정 녹록치 않고 그룹 지원도 기대 어려움", "severity": "critical"},
            {"type": "operational", "description": "복잡한 다층 유동화 구조로 투명성 부족. SPC와 브릿지론을 통한 간접 차입으로 실제 부채 구조 파악 어려움", "severity": "high"},
            {"type": "market", "description": "롯데건설 부동산PF 우발채무 문제로 그룹 전체 자금사정 악화, 롯데쇼핑 추가 지원 능력 제약", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (21차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}... - {result.get('error', 'Unknown error')}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
