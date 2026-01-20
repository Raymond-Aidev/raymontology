#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 37차 (LG디스플레이 + 웅진코웨이 + 넷마블 + 홈플러스)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/89",
        "title": "가시밭길 LG디스플레이(5)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-03",
        "summary": "LG디스플레이의 주력 제품인 TV용 LCD 패널에서 대규모 적자 발생. OLED로의 전환 과정에서 LCD 적자 심화, 이를 충당하기 위해 차입금 급증하면서 재무 악화 심각.",
        "entities": [
            {"type": "company", "name": "LG디스플레이", "role": "주요 대상 기업"},
            {"type": "company", "name": "하이투자증권", "role": "분석 자료 제공"},
        ],
        "relations": [
            {"source": "LG디스플레이", "target": "중국 업체들", "type": "competition", "detail": "시장 주도권 경쟁"},
        ],
        "risks": [
            {"type": "operational", "description": "LCD TV 대규모 적자", "severity": "critical"},
            {"type": "financial", "description": "차입금 급증 및 이자비용 증가", "severity": "high"},
            {"type": "financial", "description": "영업현금흐름 악화", "severity": "high"},
            {"type": "financial", "description": "레버리지 비율 악화 (차입금 36% 증가)", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/88",
        "title": "가시밭길 LG디스플레이(4)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-01-31",
        "summary": "LG디스플레이는 TV패널 수요 정체와 대형 LCD 패널 판가 급락으로 실적 악화. 재고자산 평가손실이 5000억원에 달하면서 3분기 누적 적자 9375억원 기록. 디스플레이산업 공급과잉이 지속되는 한 흑자 전환 기대 어려움.",
        "entities": [
            {"type": "company", "name": "LG디스플레이", "role": "분석 대상 기업"},
            {"type": "company", "name": "삼성디스플레이", "role": "경쟁사"},
            {"type": "company", "name": "중국 디스플레이 업체들", "role": "경쟁사"},
        ],
        "relations": [
            {"source": "LG디스플레이", "target": "삼성디스플레이", "type": "competition", "detail": "대형 디스플레이 패널 시장 경쟁"},
        ],
        "risks": [
            {"type": "market", "description": "디스플레이 산업 공급과잉", "severity": "high"},
            {"type": "financial", "description": "LCD 패널 가격 하락 (600→513달러/m²)", "severity": "high"},
            {"type": "market", "description": "중국 TV 시장 정체", "severity": "high"},
            {"type": "financial", "description": "대규모 재고자산 평가손실 (5000억원)", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/87",
        "title": "가시밭길 LG디스플레이(3)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-01-29",
        "summary": "LG디스플레이의 대형 LCD 시장 공급과잉과 중국 업체들의 가격 경쟁 분석. 삼성디스플레이는 삼성전자 캡티브 마켓 구조와 중소형 OLED 지배력으로 회복력 있는 반면, LG디스플레이는 글로벌 직접 경쟁에 노출.",
        "entities": [
            {"type": "company", "name": "LG디스플레이", "role": "시장 압박받는 대형 LCD 패널 제조사"},
            {"type": "company", "name": "삼성디스플레이", "role": "캡티브 마켓 우위 보유 다각화 패널 공급사"},
            {"type": "company", "name": "삼성전자", "role": "삼성디스플레이 대주주 (84%)"},
            {"type": "company", "name": "LG전자", "role": "LG디스플레이 대주주 (37%)"},
            {"type": "company", "name": "BOE", "role": "중국 디스플레이 시장 경쟁자"},
        ],
        "relations": [
            {"source": "삼성전자", "target": "삼성디스플레이", "type": "ownership", "detail": "84% 지분 보유"},
            {"source": "LG전자", "target": "LG디스플레이", "type": "ownership", "detail": "37% 지분 보유"},
        ],
        "risks": [
            {"type": "market", "description": "대형 LCD 패널 가격 급락, 공급이 수요 초과", "severity": "high"},
            {"type": "market", "description": "삼성디스플레이 대형 패널 점유율 2015년 약 20%에서 2020년 3분기 약 9.7%로 하락", "severity": "high"},
            {"type": "market", "description": "정부 지원받는 중국 업체들의 대규모 대형 LCD 투자", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/86",
        "title": "가시밭길 LG디스플레이(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-01-22",
        "summary": "LG디스플레이의 실적 악화는 중국 업체들의 과잉공급으로 인한 LCD 가격 급락과 OLED 전환 전략 부진이 복합 작용. 삼성디스플레이 안정적 실적과 비교하면 LG디스플레이의 영업이익률이 가장 큰 폭으로 하락, 95% 매출원가율이 수익성 악화의 핵심.",
        "entities": [
            {"type": "company", "name": "LG디스플레이", "role": "디스플레이 패널 제조사"},
            {"type": "company", "name": "삼성디스플레이", "role": "디스플레이 패널 제조사"},
            {"type": "company", "name": "LG전자", "role": "가전제품 생산사"},
            {"type": "company", "name": "삼성전자", "role": "가전제품 생산사"},
        ],
        "relations": [
            {"source": "LG전자", "target": "LG디스플레이", "type": "supply", "detail": "패널 납품"},
            {"source": "삼성전자", "target": "삼성디스플레이", "type": "supply", "detail": "패널 납품"},
        ],
        "risks": [
            {"type": "market", "description": "중국 과잉생산으로 인한 LCD 가격 붕괴", "severity": "critical"},
            {"type": "strategic", "description": "OLED 투자 전략 부진", "severity": "high"},
            {"type": "financial", "description": "영업이익률 거의 제로 수준으로 압축", "severity": "critical"},
            {"type": "financial", "description": "신용등급 하향, 부정적 전망", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/85",
        "title": "가시밭길 LG디스플레이(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-01-20",
        "summary": "LG디스플레이의 AA- 신용등급이 재무 지표 대비 부당하게 높음. 5년간 EBITDA 마진, 부채 커버리지, CAPEX 지표가 지속적으로 AA- 등급 기준 미달, 최대 A+ 등급이 적정. 신용평가사들이 펀더멘털 악화를 간과.",
        "entities": [
            {"type": "company", "name": "LG디스플레이", "role": "분석 대상 기업"},
            {"type": "company", "name": "LG전자", "role": "약 40% 지분 보유 모회사"},
            {"type": "company", "name": "한국기업평가", "role": "전망 부정적으로 하향"},
            {"type": "company", "name": "한국신용평가", "role": "10월 하향"},
            {"type": "company", "name": "나이스신용평가", "role": "1월 19일 하향"},
        ],
        "relations": [
            {"source": "LG전자", "target": "LG디스플레이", "type": "ownership", "detail": "약 40% 지분 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "EBITDA 마진이 20% 임계값 지속 미달", "severity": "high"},
            {"type": "financial", "description": "순부채 대 EBITDA 비율 9.6배 (2019년 9월), AA 등급 요건 0.5배 크게 초과", "severity": "critical"},
            {"type": "financial", "description": "EBITDA가 CAPEX 요건 충당 부족", "severity": "high"},
            {"type": "financial", "description": "단일 회계연도 내 2노치 하향 압력", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/84",
        "title": "웅진코웨이 기업가치의 변화(8)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-01-17",
        "summary": "현금흐름할인법으로 웅진코웨이 기업가치 분석. 현재 시장 기업가치 6.6-6.7조원이 추정 영업가치 3.25조원을 크게 상회, 현금 창출 잠재력 과소평가이거나 시장 고평가 시사.",
        "entities": [
            {"type": "company", "name": "웅진코웨이", "role": "기업가치 분석 대상"},
            {"type": "company", "name": "안진회계법인", "role": "2012년 기업가치 평가 수행"},
        ],
        "relations": [
            {"source": "안진회계법인", "target": "웅진코웨이", "type": "valuation", "detail": "2012년 기업가치 평가 수행"},
        ],
        "risks": [
            {"type": "financial", "description": "시장 기업가치와 내재가치 추정 간 상당한 괴리", "severity": "high"},
            {"type": "operational", "description": "사모펀드 기간 이후 현금흐름 창출 하락 추세", "severity": "high"},
            {"type": "financial", "description": "미래 성장률 모델 가정 불확실성", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/83",
        "title": "웅진코웨이 기업가치의 변화(7)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-01-15",
        "summary": "2012년과 2019년 사이 가중평균자본비용(WACC) 변화를 통한 웅진코웨이 기업가치 분석. 체계적 위험 증가(베타 0.74에서 0.95로 상승)에도 불구하고 국채금리 하락으로 전체 자본비용 감소하여 기업가치 상승.",
        "entities": [
            {"type": "company", "name": "웅진코웨이", "role": "기업가치 분석 대상"},
            {"type": "company", "name": "안진회계법인", "role": "2012년 CAPM 모델로 기업가치 평가"},
            {"type": "company", "name": "fn가이드", "role": "베타 계수 이력 제공 금융 데이터 제공사"},
            {"type": "company", "name": "넷마블", "role": "웅진코웨이 잠재적 인수자"},
        ],
        "relations": [
            {"source": "안진회계법인", "target": "웅진코웨이", "type": "valuation", "detail": "2012년 기업가치 분석 수행"},
            {"source": "넷마블", "target": "웅진코웨이", "type": "acquisition", "detail": "잠재적 인수 대상"},
        ],
        "risks": [
            {"type": "market", "description": "체계적 위험(베타) 2012년 0.74에서 2019년 0.95로 증가", "severity": "medium"},
            {"type": "financial", "description": "부채비율 20% 미만에서 자기자본의 80%로 상승, 신용등급 불안정", "severity": "high"},
            {"type": "market", "description": "국채금리에 대한 기업가치 평가 민감도, 2% 하락이 가치 크게 증가", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/82",
        "title": "웅진코웨이 기업가치의 변화(6)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-01-13",
        "summary": "현금흐름할인법으로 웅진코웨이 기업가치 분석. 최근 인플레이션 추세 기반 영구성장률 1.5% 추정, 과거 재무비율과 추세 사용하여 5년간 잉여현금흐름 추정.",
        "entities": [
            {"type": "company", "name": "웅진코웨이", "role": "기업가치 평가 대상"},
            {"type": "company", "name": "MBK파트너스", "role": "웅진코웨이 인수한 사모펀드"},
            {"type": "company", "name": "LG전자", "role": "정수기, 공기청정기 시장 경쟁사"},
            {"type": "company", "name": "SK", "role": "구독경제 경쟁사"},
            {"type": "company", "name": "안진회계법인", "role": "2012년 기업가치 평가 회계법인"},
            {"type": "company", "name": "넷마블", "role": "기업가치 평가 시나리오에 언급된 잠재적 인수자"},
        ],
        "relations": [
            {"source": "MBK파트너스", "target": "웅진코웨이", "type": "ownership", "detail": "사모펀드 소유, 이후 웅진그룹에 매각"},
        ],
        "risks": [
            {"type": "market", "description": "정수기 부문 시장 포화", "severity": "high"},
            {"type": "market", "description": "대기업 경쟁 심화", "severity": "high"},
            {"type": "operational", "description": "신규 성장 제품 도입 역량 제한", "severity": "medium"},
            {"type": "financial", "description": "영업현금흐름 마진 하락 추세", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/81",
        "title": "웅진코웨이 기업가치의 변화(5)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-01-10",
        "summary": "웅진코웨이의 사모펀드 인수 이후 현금흐름 패턴 분석. 매출 성장은 추정치 미달이나 잉여현금흐름은 추정치 초과. 이 역설은 운영 효율성 개선보다 4년간 약 2600억원의 자본지출 및 운전자본 투자 감소에서 기인.",
        "entities": [
            {"type": "company", "name": "웅진코웨이", "role": "분석 대상"},
            {"type": "company", "name": "안진회계법인", "role": "기업가치 추정자"},
            {"type": "company", "name": "MBK파트너스", "role": "사모펀드 인수자"},
        ],
        "relations": [
            {"source": "MBK파트너스", "target": "웅진코웨이", "type": "acquisition", "detail": "인수"},
            {"source": "안진회계법인", "target": "웅진코웨이", "type": "valuation", "detail": "기업가치 추정 제공"},
        ],
        "risks": [
            {"type": "operational", "description": "자본지출 감소가 장기 성장 역량 손상 가능", "severity": "high"},
            {"type": "operational", "description": "공격적 운전자본 관리가 공급업체/고객 관계 긴장 가능", "severity": "medium"},
            {"type": "financial", "description": "배당금 지급이 영업현금흐름 지속가능성 초과", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/80",
        "title": "웅진코웨이 기업가치의 변화(4)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-01-08",
        "summary": "배당 정책과 할인율이 웅진코웨이 기업가치 평가에 미치는 영향 분석. 2012년 사모펀드 인수 분석하며 이후 금리 하락이 현금흐름 변동 없이도 현재 기업가치 상승 지지.",
        "entities": [
            {"type": "company", "name": "웅진코웨이", "role": "기업가치 분석 대상"},
            {"type": "company", "name": "안진회계법인", "role": "2012년 기업가치 평가 수행 회계법인"},
            {"type": "company", "name": "넷마블", "role": "웅진코웨이 인수자"},
            {"type": "company", "name": "웅진그룹", "role": "차입을 통한 재인수 수행"},
            {"type": "company", "name": "웅진씽크빅", "role": "2020년 초 경영권 재인수"},
        ],
        "relations": [
            {"source": "안진회계법인", "target": "웅진코웨이", "type": "valuation", "detail": "2012년 4.07조원 평가"},
            {"source": "웅진그룹", "target": "웅진코웨이", "type": "acquisition", "detail": "배당 배분 필요한 차입을 통한 재인수"},
            {"source": "넷마블", "target": "웅진코웨이", "type": "acquisition", "detail": "웅진그룹 이후 인수자"},
        ],
        "risks": [
            {"type": "financial", "description": "고배당 지급으로 재투자 및 성장 잠재력 감소", "severity": "high"},
            {"type": "financial", "description": "대규모 배당 유출로 신용등급 하향", "severity": "high"},
            {"type": "financial", "description": "부채 상환 의무로 지속적 고배당 강제", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/79",
        "title": "웅진코웨이 기업가치의 변화(3)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-01-06",
        "summary": "2012년 안진회계법인의 DCF 방법론을 이용한 웅진코웨이 기업가치 분석. 3.8조원 영업가치 계산 방법 분석, 잔존가치 계산에 영향 미치는 2.9% 영구성장률 가정의 우려 논의.",
        "entities": [
            {"type": "company", "name": "웅진코웨이", "role": "기업가치 분석 대상"},
            {"type": "company", "name": "안진회계법인", "role": "DCF 분석 수행 평가 법인"},
        ],
        "relations": [
            {"source": "안진회계법인", "target": "웅진코웨이", "type": "valuation", "detail": "DCF 기업가치 평가 수행"},
        ],
        "risks": [
            {"type": "financial", "description": "영구성장률 가정이 실증적 근거 부족", "severity": "high"},
            {"type": "financial", "description": "잔존가치 계산이 검증되지 않은 성장 가정에 크게 의존", "severity": "high"},
            {"type": "governance", "description": "공시된 잔존가치 계산의 불일치 설명 부족", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/78",
        "title": "웅진코웨이 기업가치의 변화(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-01-02",
        "summary": "2012년 MBK파트너스 인수 당시 웅진코웨이 기업가치 평가 분석. 안진회계법인이 사용한 3가지 평가 방법론 분석, 8.54%에서 68.28%에 이르는 경영권 프리미엄으로 인해 최저(38,640원)와 최고(70,861원) 주가 간 상당한 괴리.",
        "entities": [
            {"type": "company", "name": "웅진코웨이", "role": "기업가치 평가 대상"},
            {"type": "company", "name": "MBK파트너스", "role": "인수 법인"},
            {"type": "company", "name": "안진회계법인", "role": "외부 평가 기관"},
        ],
        "relations": [
            {"source": "MBK파트너스", "target": "웅진코웨이", "type": "acquisition", "detail": "2012년 웅진그룹으로부터 주당 50,000원에 인수"},
            {"source": "안진회계법인", "target": "웅진코웨이", "type": "valuation", "detail": "거래를 위한 기업가치 분석 수행"},
        ],
        "risks": [
            {"type": "financial", "description": "최저와 최고 평가 간 큰 격차 (84% 차이)", "severity": "high"},
            {"type": "financial", "description": "EV/EBITDA 방법론에서 비영업자산 이중 계상 의문", "severity": "medium"},
            {"type": "financial", "description": "경영권 프리미엄이 거래마다 극적으로 변동, 표준화된 평가 어려움", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/77",
        "title": "웅진코웨이 기업가치의 변화(1) - 25% 지분 값 1.8조원, 싼 걸까 비싼 걸까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-12-26",
        "summary": "웅진코웨이의 지분 거래 가격 변화 추적하며 기업가치 평가 방법론 검토. 2013년 MBK파트너스 매각(주당 5만원)부터 2019년 넷마블 재매각까지 거래에서 경영권 프리미엄과 기업가치 관계 분석.",
        "entities": [
            {"type": "company", "name": "웅진코웨이", "role": "주요 피매각 기업"},
            {"type": "company", "name": "MBK파트너스", "role": "2012년 인수자"},
            {"type": "company", "name": "웅진그룹", "role": "원래 소유사, 2019년 재판매 주체"},
            {"type": "company", "name": "웅진씽크빅", "role": "2019년 인수자"},
            {"type": "company", "name": "넷마블", "role": "최종 인수 예정자"},
        ],
        "relations": [
            {"source": "웅진그룹", "target": "웅진코웨이", "type": "ownership", "detail": "2012년 23.37% 지분 MBK파트너스에 1조939억원 매각"},
            {"source": "웅진씽크빅", "target": "웅진코웨이", "type": "acquisition", "detail": "2019년 3월 22.17% 지분 1조6832억원에 인수"},
            {"source": "넷마블", "target": "웅진코웨이", "type": "acquisition", "detail": "25.08% 지분 1조8000억원에 인수 예정"},
        ],
        "risks": [
            {"type": "financial", "description": "과도한 인수차입금, 웅진씽크빅 차입금 900억에서 1조2000억으로 증가", "severity": "high"},
            {"type": "financial", "description": "이자 지급 부담, 상반기 이자지급액 15억에서 158억으로 10배 이상 증가", "severity": "high"},
            {"type": "financial", "description": "한국투자증권 전환사채에 미상환시 웅진씽크빅 지분 처분 옵션", "severity": "high"},
            {"type": "operational", "description": "웅진에너지 감사의견 거절로 그룹 전체 유동성 위기", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/76",
        "title": "코웨이 인수, 넷마블의 외도?(6) - 웅진코웨이, 고배당 굴레에서 벗어날까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-12-27",
        "summary": "넷마블이 웅진코웨이 지분 인수 추진 중, 1조8000억원 투자하여 현금성 자산 거의 소진 전망. 웅진코웨이는 렌탈 시장 압도적 1위이나 사모펀드 소유 이후 고배당으로 7700억원 순차입금 보유.",
        "entities": [
            {"type": "company", "name": "넷마블", "role": "인수자 (웅진코웨이 지분 25% 인수 예정)"},
            {"type": "company", "name": "웅진코웨이", "role": "인수 대상"},
            {"type": "person", "name": "방준혁", "role": "넷마블 회장"},
            {"type": "company", "name": "SK매직", "role": "경쟁사 (2위)"},
            {"type": "company", "name": "국민연금", "role": "주요 주주 (9.6% 보유)"},
            {"type": "company", "name": "웅진씽크빅", "role": "현재 주요 주주 (25% 보유)"},
        ],
        "relations": [
            {"source": "넷마블", "target": "웅진코웨이", "type": "acquisition", "detail": "1조8000억원 인수 추진"},
            {"source": "웅진코웨이", "target": "SK매직", "type": "competition", "detail": "렌탈 시장 경쟁"},
        ],
        "risks": [
            {"type": "financial", "description": "웅진코웨이 순차입금 7700억원 대부분이 1년 내 상환 대상", "severity": "high"},
            {"type": "financial", "description": "넷마블 2조원 현금 거의 전부 인수에 투입, 향후 성장 투자 제약", "severity": "high"},
            {"type": "market", "description": "웅진코웨이 주력 정수기 렌탈 시장 성장 한계 도달", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/75",
        "title": "코웨이 인수, 넷마블의 외도?(5) - 글로벌 시장 5위의 꿈, 게임 아닌 실물 구독 경제로?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-12-23",
        "summary": "방준혁 회장의 웅진코웨이 인수 분석. 제시된 스마트홈 구독경제 명분보다 게임 사업 성장 둔화로 안정적 현금흐름 필요한 넷마블의 재무전략적 선택으로 해석. 웅진코웨이의 렌탈 유통망과 현금창출능력(EBITDA 7000억원대)이 넷마블의 주요 약점 보완 가능.",
        "entities": [
            {"type": "person", "name": "방준혁", "role": "넷마블 회장"},
            {"type": "company", "name": "넷마블", "role": "게임사, 인수자"},
            {"type": "company", "name": "웅진코웨이", "role": "환경가전 렌탈업체, 인수대상"},
            {"type": "company", "name": "넥슨", "role": "경쟁사"},
            {"type": "company", "name": "엔씨소프트", "role": "경쟁사"},
        ],
        "relations": [
            {"source": "방준혁", "target": "넷마블", "type": "management", "detail": "회장으로 재직"},
            {"source": "넷마블", "target": "웅진코웨이", "type": "acquisition", "detail": "지분 약 25% 인수 추진"},
        ],
        "risks": [
            {"type": "operational", "description": "게임 사업 성장 정체, 2017년 2.4조원 매출 이후 감소 추세", "severity": "high"},
            {"type": "market", "description": "중국 시장 문제로 성장 급감, 경쟁력 지속성 불확실", "severity": "high"},
            {"type": "financial", "description": "영업이익률 2017년 21%에서 2019년 상반기 6.7%로 급락", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/74",
        "title": "코웨이 인수, 넷마블의 외도?(4)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-12-23",
        "summary": "넷마블은 게임 매출 1위이나 실질적 수익성 낮음. 자회사 인수에 1조7000억원 투자했으나 잉여현금흐름 음수, 높은 지급수수료로 경쟁사 대비 이익률 현저히 낮음.",
        "entities": [
            {"type": "company", "name": "넷마블", "role": "게임 퍼블리셔 및 투자사"},
            {"type": "company", "name": "엔씨소프트", "role": "경쟁사 (게임 퍼블리셔)"},
            {"type": "company", "name": "넥슨코리아", "role": "경쟁사"},
            {"type": "company", "name": "웅진코웨이", "role": "인수 대상"},
            {"type": "company", "name": "빅히트엔터테인먼트", "role": "투자 대상"},
        ],
        "relations": [
            {"source": "넷마블", "target": "웅진코웨이", "type": "acquisition", "detail": "게임 영역 외 투자"},
            {"source": "넷마블", "target": "엔씨소프트", "type": "competition", "detail": "영업이익률 비교"},
        ],
        "risks": [
            {"type": "financial", "description": "2011년 이후 누적 잉여현금흐름 음수", "severity": "high"},
            {"type": "operational", "description": "엔씨소프트 대비 연 3배 이상 지급수수료 (9000억~1조원)", "severity": "high"},
            {"type": "market", "description": "지난해부터 중국 수출 끊김", "severity": "high"},
            {"type": "strategic", "description": "자체 IP 게임 비중 10% 미만, IP 라이선스 의존", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/73",
        "title": "코웨이 인수, 넷마블의 외도?(3)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-12-16",
        "summary": "한국 '3N' 게임사(넷마블, 넥슨, 엔씨소프트) 중 넷마블이 빠른 매출 성장에도 최저 수익성인 이유 분석. 중국의 게임 라이선스 중단이 넷마블 재무에 큰 영향, 자체 IP보다 외부 IP에 의존하는 비즈니스 모델의 구조적 약점 노출.",
        "entities": [
            {"type": "company", "name": "넷마블", "role": "외부 IP 기반 게임 중심 게임 퍼블리셔"},
            {"type": "company", "name": "넥슨", "role": "강력한 자체 개발 역량 보유 게임사"},
            {"type": "company", "name": "엔씨소프트", "role": "개발과 퍼블리싱 균형 게임사"},
            {"type": "company", "name": "스마일게이트", "role": "크로스파이어 모바일 개발사"},
        ],
        "relations": [
            {"source": "넷마블", "target": "넥슨", "type": "competition", "detail": "'3N' 한국 주요 게임사 그룹"},
        ],
        "risks": [
            {"type": "regulatory", "description": "중국 게임 라이선스 중단, 2017년 3월 이후 한국 게임 신규 라이선스 미발급", "severity": "high"},
            {"type": "financial", "description": "영업이익률 2019년 상반기 7% 미만으로 하락, 경쟁사의 1/3", "severity": "high"},
            {"type": "strategic", "description": "제3자 IP 의존으로 경쟁사 대비 이익률 제한", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/72",
        "title": "코웨이 인수, 넷마블의 외도?(2) - 게임과 구독경제 시너지 있을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-12-12",
        "summary": "넷마블의 웅진코웨이 인수를 '스마트 홈 구독경제'로 포장하고 있으나, IT 기술과 게임 데이터가 정수기 사업과 실제 시너지 낼 수 있을지 의문. 게임 산업의 중국 판호 불가 정책으로 인한 매출 감소가 인수의 실제 배경.",
        "entities": [
            {"type": "company", "name": "넷마블", "role": "인수자"},
            {"type": "company", "name": "웅진코웨이", "role": "인수 대상"},
            {"type": "company", "name": "CJ그룹", "role": "넷마블 대주주 (20%+)"},
        ],
        "relations": [
            {"source": "넷마블", "target": "웅진코웨이", "type": "acquisition", "detail": "1.8조원 인수 시도"},
            {"source": "CJ그룹", "target": "넷마블", "type": "ownership", "detail": "분사 회사, 20%+ 보유"},
        ],
        "risks": [
            {"type": "regulatory", "description": "2017년 이후 중국 게임 유통 금지", "severity": "high"},
            {"type": "financial", "description": "넷마블 매출 전년 대비 약 20% 감소", "severity": "high"},
            {"type": "financial", "description": "영업현금흐름 50% 이상 감소", "severity": "high"},
            {"type": "strategic", "description": "게임과 정수기 사업 간 전략적 시너지 의문", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/71",
        "title": "코웨이 인수, 넷마블의 외도?(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-12-11",
        "summary": "넷마블의 1.8조원 코웨이 인수가 기업가치 평가 의문 제기. 게임사가 실사 없이 3일 만에 코웨이를 우선협상대상자로 선정, 글로벌 PE 및 국내 대기업 포함 다른 주요 매수자들은 철수. 매수 가격이 공정가치인지 잠재적 고평가인지 분석.",
        "entities": [
            {"type": "company", "name": "넷마블", "role": "인수자"},
            {"type": "company", "name": "웅진코웨이", "role": "대상 기업"},
            {"type": "company", "name": "웅진그룹", "role": "매도자"},
            {"type": "person", "name": "윤석금", "role": "웅진그룹 회장"},
            {"type": "company", "name": "MBK파트너스", "role": "이전 소유자"},
            {"type": "company", "name": "한국투자증권", "role": "재무자문/채권자"},
        ],
        "relations": [
            {"source": "넷마블", "target": "웅진코웨이", "type": "acquisition", "detail": "1.8조원 제시"},
            {"source": "웅진그룹", "target": "웅진코웨이", "type": "ownership", "detail": "2012년 MBK파트너스, 2019년 넷마블에 매각"},
            {"source": "한국투자증권", "target": "웅진그룹", "type": "financing", "detail": "웅진코웨이 재매입 시 1.6조원 중 5000억원 전환사채 인수"},
        ],
        "risks": [
            {"type": "operational", "description": "적절한 실사 부재, 3일 만에 선정되어 충분한 검토 과정 없음", "severity": "high"},
            {"type": "financial", "description": "과다 평가 가능성, 6년 사이 기업가치 2배 상승이 실제 성과 반영 불명확", "severity": "high"},
            {"type": "strategic", "description": "게임사의 렌탈업 미경험, 시너지 부재", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/70",
        "title": "풍랑 휩싸인 홈플러스(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-12-10",
        "summary": "홈플러스는 온라인 유통 확산으로 심각한 경영 위기 직면, 매출액 지속 하락하고 수익성 악화. 대주주 MBK파트너스는 부동산 매각과 리츠 상장으로 차입금 줄이려 했으나 리츠 상장 실패로 투자회수 전략 막힘.",
        "entities": [
            {"type": "company", "name": "홈플러스", "role": "경영난 겪는 소매 할인점 체인"},
            {"type": "company", "name": "홈플러스스토어즈", "role": "홈플러스 자회사"},
            {"type": "company", "name": "MBK파트너스", "role": "대주주, 사모펀드"},
            {"type": "company", "name": "이마트", "role": "경쟁사, 시장 리더"},
            {"type": "company", "name": "롯데마트", "role": "경쟁사"},
            {"type": "company", "name": "이지스자산운용", "role": "세일즈앤리스백 거래 자산운용사"},
        ],
        "relations": [
            {"source": "MBK파트너스", "target": "홈플러스", "type": "ownership", "detail": "2015년 이후 소유/지배"},
            {"source": "홈플러스", "target": "이마트", "type": "competition", "detail": "할인점 시장 직접 경쟁"},
        ],
        "risks": [
            {"type": "operational", "description": "매출액 8조원대에서 7조원대 중반으로 하락", "severity": "high"},
            {"type": "strategic", "description": "온라인 투자 저조, 자본적 지출 매년 1000억원 미만", "severity": "high"},
            {"type": "financial", "description": "리츠 IPO 실패, 기관투자자 수요예측에서 목표 절반인 8000억원만 모임", "severity": "critical"},
            {"type": "market", "description": "이마트는 매출 증가 중이나 홈플러스는 감소", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (37차) ===\n")

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
