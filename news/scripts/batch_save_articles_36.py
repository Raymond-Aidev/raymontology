#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 36차 (e커머스 전쟁 시리즈 1-18 + LG디스플레이 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/109",
        "title": "e커머스 전쟁, 최후의 승자는?(18)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-20",
        "summary": "쿠팡, 월마트, 아마존, 이베이코리아의 e커머스 경쟁 역학 분석. 아마존의 다양한 수익원(AWS, 클라우드 서비스)은 지속 가능한 성장을 가능하게 하는 반면, 쿠팡은 온라인 쇼핑에 의존하며 마이너스 현금흐름. 네이버의 모바일 앱과 검색 통합을 통한 플랫폼 지배력이 최종 승자를 결정할 가능성.",
        "entities": [
            {"type": "company", "name": "아마존", "role": "글로벌 e커머스 리더, 미국 시장점유율 44.8%, AWS 클라우드 서비스 지배"},
            {"type": "company", "name": "쿠팡", "role": "한국 e커머스 플랫폼, 약 12% 시장점유율, 공격적 물류 확장"},
            {"type": "company", "name": "월마트", "role": "오프라인 소매 거인, 온라인 확장 위해 오프라인 매장 활용"},
            {"type": "company", "name": "이베이코리아", "role": "한국 e커머스 플랫폼, 약 13% 시장점유율"},
            {"type": "company", "name": "네이버", "role": "포털, 88.9% 도달률로 검색 및 쇼핑 발견 지배"},
            {"type": "company", "name": "롯데그룹", "role": "한국 오프라인 유통 경쟁사"},
            {"type": "company", "name": "신세계그룹", "role": "한국 오프라인 유통 경쟁사"},
        ],
        "relations": [
            {"source": "쿠팡", "target": "네이버", "type": "dependency", "detail": "상품 검색은 네이버에서 이루어짐, 플랫폼 지배력 부재"},
        ],
        "risks": [
            {"type": "financial", "description": "쿠팡의 마이너스 영업현금흐름으로 인접 서비스 다각화 불가능", "severity": "high"},
            {"type": "strategic", "description": "네이버에 대한 고객 획득 플랫폼 의존성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/108",
        "title": "e커머스 전쟁, 최후의 승자는?(17)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-18",
        "summary": "쿠팡의 파괴적 물류 모델이 전통 유통업체들에게 가격/속도 경쟁 또는 수익성 추구 양자택일을 강요. 이마트 창사 이래 첫 분기 적자 기록 등 온/오프라인 유통업체 모두 마진 압박. 롯데와 신세계는 미국 월마트의 성공적인 옴니채널 전략처럼 온라인 시장 진출이 생존의 필수 조건.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "빠른 배송 서비스의 시장 교란자"},
            {"type": "company", "name": "이마트", "role": "마진 압박 받는 오프라인 할인점"},
            {"type": "company", "name": "홈플러스", "role": "매출 감소 겪는 오프라인 유통업체"},
            {"type": "company", "name": "티몬", "role": "전략 불분명한 소셜커머스 플랫폼"},
            {"type": "company", "name": "위메프", "role": "수익성 중심으로 전환한 e커머스 업체"},
            {"type": "company", "name": "월마트", "role": "옴니채널 전략 성공한 미국 오프라인 리더"},
            {"type": "company", "name": "아마존", "role": "미국 온라인 시장 리더, 37.8% 시장점유율"},
        ],
        "relations": [
            {"source": "쿠팡", "target": "이마트", "type": "competition", "detail": "경쟁 압박으로 이마트 마진 감소, 첫 분기 적자 발생"},
            {"source": "쿠팡", "target": "홈플러스", "type": "competition", "detail": "쿠팡의 시장 교란으로 홈플러스 2018년 매출 3.7% 감소"},
        ],
        "risks": [
            {"type": "financial", "description": "유통 업계 전반 마진 압박", "severity": "high"},
            {"type": "operational", "description": "온라인 침투 가속화로 오프라인 매장 고정비 부담 증가", "severity": "high"},
            {"type": "financial", "description": "물류 경쟁의 자본 집약성으로 현금흐름 압박", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/107",
        "title": "e커머스 전쟁, 최후의 승자는?(16)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-16",
        "summary": "이베이코리아의 쿠팡 대비 경쟁력 도전 분석. 이베이의 오픈마켓 모델과 아마존의 풀필먼트 기반 접근 비교. 이베이코리아의 수익성은 마진 압박과 자본 제약으로 하락 중. 전략적 개입과 인프라 대규모 투자 없이는 시장점유율 계속 잠식 예상.",
        "entities": [
            {"type": "company", "name": "이베이코리아", "role": "G마켓, 옥션 플랫폼 운영 한국 자회사"},
            {"type": "company", "name": "이베이", "role": "글로벌 오픈마켓 모회사"},
            {"type": "company", "name": "쿠팡", "role": "아마존 풀필먼트 모델 한국 적용 경쟁자"},
            {"type": "company", "name": "아마존", "role": "풀필먼트 인프라 보유 글로벌 e커머스 리더"},
            {"type": "company", "name": "G마켓", "role": "이베이코리아 자회사 마켓플레이스"},
            {"type": "company", "name": "옥션", "role": "이베이코리아 자회사 마켓플레이스"},
        ],
        "relations": [
            {"source": "이베이", "target": "이베이코리아", "type": "ownership", "detail": "2017년 이후 연간 1000억원 이상 배당금 추출"},
            {"source": "이베이코리아", "target": "쿠팡", "type": "competition", "detail": "쿠팡이 우월한 물류로 시장 지배력 확보"},
        ],
        "risks": [
            {"type": "financial", "description": "영업이익률 40%에서 매출원가율 50% 이하로 하락", "severity": "high"},
            {"type": "strategic", "description": "모회사의 연간 1000억원 이상 배당금 추출로 재투자 역량 제한", "severity": "high"},
            {"type": "operational", "description": "연간 2000-3000억원 자본지출로 쿠팡 인프라와 경쟁 불충분", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/106",
        "title": "e커머스 전쟁, 최후의 승자는?(15)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-13",
        "summary": "쿠팡과 이베이코리아(G마켓, 옥션)의 한국 e커머스 시장 경쟁 분석. 쿠팡이 2019년 거래액에서 이베이코리아 추월했으나, 이베이코리아는 수익성과 상당한 유동성 유지. 다만 모회사에 대한 대규모 배당금 지급이 장기 경쟁력 우려.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "고성장하나 지속 적자인 e커머스 경쟁자"},
            {"type": "company", "name": "이베이코리아", "role": "G마켓, 옥션 플랫폼 운영 기존 시장 리더"},
            {"type": "company", "name": "G마켓", "role": "연간 거래액 약 10조원의 주요 오픈마켓 플랫폼"},
            {"type": "company", "name": "옥션", "role": "연간 거래액 약 5조원의 이베이코리아 플랫폼"},
            {"type": "company", "name": "11번가", "role": "SK텔레콤 80%+ 소유, 거래액 약 9조원의 3위 경쟁자"},
            {"type": "company", "name": "이베이", "role": "이베이코리아에서 배당금 추출하는 모회사"},
            {"type": "company", "name": "SK텔레콤", "role": "11번가 대주주"},
        ],
        "relations": [
            {"source": "이베이", "target": "이베이코리아", "type": "ownership", "detail": "2017년 이후 연간 1.3-1.6조원 배당금 추출"},
        ],
        "risks": [
            {"type": "financial", "description": "이베이 모회사 배당금 추출로 경쟁력 약화", "severity": "high"},
            {"type": "market", "description": "이베이코리아 고객층이 PC 사용 감소하는 고령층에 치우침", "severity": "medium"},
            {"type": "strategic", "description": "모회사에 대한 이베이코리아의 전략적 중요성 불확실, 매각 리스크", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/105",
        "title": "e커머스 전쟁, 최후의 승자는?(14)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-11",
        "summary": "쿠팡의 10조원 기업가치가 전통적 수익 지표로는 정당화될 수 없음. 가치는 AI와 결합하고 소프트뱅크 비전펀드 포트폴리오 기업들 간 통합될 때 중요해지는 축적된 고객 및 쇼핑 데이터에서 비롯됨.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "대규모 데이터 자산 보유 e커머스 플랫폼"},
            {"type": "company", "name": "아마존", "role": "경쟁 e커머스 거인"},
            {"type": "company", "name": "소프트뱅크 비전펀드", "role": "쿠팡 및 기타 e커머스 플랫폼 투자자"},
            {"type": "company", "name": "우버", "role": "SVF 투자 라이드쉐어링 기업"},
            {"type": "company", "name": "디디추싱", "role": "SVF 투자 라이드쉐어링 기업"},
            {"type": "company", "name": "마켓컬리", "role": "쿠팡과 유사 비즈니스 모델의 신선식품 e커머스 스타트업"},
            {"type": "company", "name": "SSG닷컴", "role": "새벽배송 서비스 제공 경쟁사"},
            {"type": "person", "name": "제프리 하우젠볼드", "role": "소프트뱅크 비전펀드 매니징 파트너"},
            {"type": "person", "name": "손정의", "role": "소프트뱅크 회장"},
        ],
        "relations": [
            {"source": "소프트뱅크 비전펀드", "target": "쿠팡", "type": "investment", "detail": "고객 데이터를 전략적 가치로 인식"},
        ],
        "risks": [
            {"type": "financial", "description": "명확한 수익화 경로 없는 지속 불가능한 현금 소진율", "severity": "high"},
            {"type": "financial", "description": "SVF로부터의 지속적 자본 주입에 의존", "severity": "high"},
            {"type": "financial", "description": "수익 창출 능력과 괴리된 기업가치", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/104",
        "title": "e커머스 전쟁, 최후의 승자는?(13)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-09",
        "summary": "쿠팡의 지속적 적자 전략은 손정의 회장의 소프트뱅크 비전펀드를 통한 막대한 자금 지원에 의존. 위메프와 티몬은 충분한 투자 재원 부족으로 수익성 위주 전략 추구 불가피. 이는 e커머스 시장 경쟁에서 근본적 차이를 형성.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "계획적 적자 전략 추진 e커머스 기업"},
            {"type": "person", "name": "손정의", "role": "소프트뱅크 회장, 주요 투자자"},
            {"type": "company", "name": "소프트뱅크 비전펀드", "role": "쿠팡 투자기관"},
            {"type": "company", "name": "위메프", "role": "e커머스 기업"},
            {"type": "person", "name": "김정주", "role": "NXC 대표, 위메프 투자자"},
            {"type": "company", "name": "티몬", "role": "e커머스 기업"},
            {"type": "person", "name": "신현성", "role": "티몬 창업자"},
        ],
        "relations": [
            {"source": "손정의", "target": "쿠팡", "type": "investment", "detail": "2015년과 2018년 총 30억 달러 투자"},
            {"source": "김정주", "target": "위메프", "type": "investment", "detail": "상환전환우선주로 11.3% 지분 보유"},
        ],
        "risks": [
            {"type": "market", "description": "자금조달 능력 차이에 따른 경쟁력 격차", "severity": "high"},
            {"type": "financial", "description": "쿠팡의 계획적 적자 지속 가능성 불확실", "severity": "high"},
            {"type": "operational", "description": "티몬의 매입채무 결제 기한 연장으로 공급망 위험", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/103",
        "title": "e커머스 전쟁, 최후의 승자는?(12)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-06",
        "summary": "3대 소셜커머스(쿠팡, 티몬, 위메프)의 재무 지표를 통한 전략적 차이 분석. 매출원가율과 영업손실 비교 결과: 쿠팡은 높은 직매입 비용으로 공격적 성장 추구, 위메프는 수익성 위해 수수료 기반 모델로 전환, 티몬은 두 전략 사이에 위치.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "빠른 배송과 시장 지배 추구하는 e커머스 리더"},
            {"type": "company", "name": "티몬", "role": "중간 전략의 소셜커머스 기업"},
            {"type": "company", "name": "위메프", "role": "수수료 기반 모델로 전환한 소셜커머스 기업"},
        ],
        "relations": [
            {"source": "쿠팡", "target": "티몬", "type": "competition", "detail": "서로 다른 전략적 선택의 직접 경쟁사"},
            {"source": "쿠팡", "target": "위메프", "type": "competition", "detail": "매출원가 접근 방식에서 경쟁 전략"},
        ],
        "risks": [
            {"type": "financial", "description": "쿠팡의 자본 집약적 성장 모델로 인한 막대한 영업손실", "severity": "high"},
            {"type": "operational", "description": "쿠팡의 높은 판관비 상쇄 위한 지속적 매출 성장 의존", "severity": "high"},
            {"type": "strategic", "description": "티몬의 불명확한 전략적 방향이 경쟁 불확실성 조성", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/102",
        "title": "e커머스 전쟁, 최후의 승자는?(11)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-04",
        "summary": "한국 e커머스 경쟁에서 3대 소셜커머스(쿠팡, 티몬, 위메프)의 운전자본 관리 전략 분석. 매입채무와 매출채권 관리를 통한 현금흐름 창출 방식을 분석, 유사 비즈니스 모델에도 불구하고 운영 접근 방식의 상당한 차이 발견.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "e커머스 플랫폼 운영사"},
            {"type": "company", "name": "티몬", "role": "소셜커머스 플랫폼 운영사"},
            {"type": "company", "name": "위메프", "role": "소셜커머스 플랫폼 운영사"},
        ],
        "relations": [
            {"source": "쿠팡", "target": "티몬", "type": "comparison", "detail": "2017년 둘 다 소셜커머스에서 오픈마켓 형태로 전환, 유사 운전자본 전략"},
        ],
        "risks": [
            {"type": "operational", "description": "성장 의존적 현금흐름 모델, 매출 성장 정체 시 문제", "severity": "high"},
            {"type": "financial", "description": "쿠팡 2018년 상당한 재고 (45억원) 보유로 자본 묶임", "severity": "medium"},
            {"type": "strategic", "description": "위메프 2018년 직매입 전략 철회, 이전 접근 방식의 지속 불가능성 시사", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/101",
        "title": "e커머스 전쟁, 최후의 승자는?(10)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-03-02",
        "summary": "아마존의 성공적인 '계획적 적자' 전략을 쿠팡의 지속적 손실과 대비 분석. 아마존은 8년간 적자 운영하며 물류에 대규모 투자 후 최종 수익화 달성. 쿠팡은 한국의 제한적 시장과 경쟁 심화로 이 성공 복제에 도전.",
        "entities": [
            {"type": "company", "name": "아마존", "role": "글로벌 e커머스 리더, 성장 전략 모델"},
            {"type": "company", "name": "쿠팡", "role": "공격적 확장 추구하는 한국 e커머스 경쟁자"},
            {"type": "company", "name": "월마트", "role": "아마존에 추월당한 전통 소매 경쟁사"},
            {"type": "company", "name": "티몬", "role": "소셜커머스 경쟁자"},
            {"type": "company", "name": "롯데쇼핑", "role": "온라인 시장 진입하는 오프라인 소매 거인"},
            {"type": "company", "name": "신세계그룹", "role": "온라인 시장 진입하는 오프라인 소매 거인"},
            {"type": "company", "name": "이베이코리아", "role": "기존 온라인 소매 경쟁사"},
            {"type": "person", "name": "손정의", "role": "소프트뱅크 회장, 쿠팡 주요 투자자"},
        ],
        "relations": [
            {"source": "쿠팡", "target": "손정의", "type": "funding", "detail": "소프트뱅크 2015년 이후 약 2.9조원 투자"},
            {"source": "쿠팡", "target": "아마존", "type": "strategy", "detail": "아마존의 '계획적 적자' 접근 방식 모방"},
        ],
        "risks": [
            {"type": "financial", "description": "현재 소진율로 3년 내 추가 자본 필요", "severity": "high"},
            {"type": "market", "description": "롯데, 신세계의 경쟁 심화로 시장 지배 잠재력 감소", "severity": "high"},
            {"type": "market", "description": "제한적 국내 시장으로 글로벌 아마존 대비 규모의 경제 달성 제약", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/100",
        "title": "e커머스 전쟁, 최후의 승자는?(9)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-28",
        "summary": "쿠팡의 2014년 로켓배송 도입으로 거래 방식이 중개에서 직매입으로 전환. 이는 재고자산과 매입채무 급증 초래, 현금흐름 구조를 근본적으로 변화. 쿠팡의 재무 프로필이 온라인 할인점에 유사해짐.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "로켓배송 서비스 구현 e커머스 플랫폼 운영사"},
            {"type": "company", "name": "이마트", "role": "쿠팡 전략에 영향받는 오프라인 할인점"},
        ],
        "relations": [
            {"source": "쿠팡", "target": "이마트", "type": "competition", "detail": "신선식품 소매 부문에서 직접 경쟁 영향"},
        ],
        "risks": [
            {"type": "operational", "description": "수익성보다 성장 우선하는 전략으로 지속적 영업손실", "severity": "high"},
            {"type": "financial", "description": "재고 및 매입채무 관리로 인한 상당한 운전자본 변동성", "severity": "high"},
            {"type": "operational", "description": "매출 변동에 반응하지 않는 높은 고정 인건비", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/99",
        "title": "e커머스 전쟁, 최후의 승자는?(8)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-26",
        "summary": "한국 소셜커머스 '빅3'(쿠팡, 티몬, 위메프)와 그들의 공격적 확장 전략 분석. 쿠팡이 2015년 수수료 기반 마켓플레이스에서 직매입 모델로 전환하여 매출 수치가 인위적으로 부풀려진 점 강조. 그루폰의 부상과 몰락과 비교하며 지속 가능성에 의문.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "직매입 모델과 빠른 확장 추구하는 시장 리더"},
            {"type": "company", "name": "티몬", "role": "성장 완화하고 손실 줄이는 소셜커머스 업체"},
            {"type": "company", "name": "위메프", "role": "수익성 유지하며 점진적 확장하는 소셜커머스 업체"},
            {"type": "company", "name": "그루폰", "role": "급성장 후 하락의 역사적 비교 사례"},
            {"type": "company", "name": "아마존", "role": "지배적 e커머스 플랫폼 기준 모델"},
            {"type": "person", "name": "손정의", "role": "쿠팡 주요 투자자"},
        ],
        "relations": [
            {"source": "손정의", "target": "쿠팡", "type": "investment", "detail": "대규모 투자를 통해 공격적 확장"},
        ],
        "risks": [
            {"type": "financial", "description": "지속적 영업손실로 인한 지속 불가능한 현금 소진율", "severity": "high"},
            {"type": "financial", "description": "매출 회계 방법론 변경으로 오도된 성장 지표", "severity": "medium"},
            {"type": "market", "description": "시장 통합 압력으로 공격적 할인 필요성 감소", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/98",
        "title": "e커머스 전쟁, 최후의 승자는?(7)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-24",
        "summary": "국내 e커머스 시장이 100조원 규모로 성장하면서 오프라인 유통업계 빠르게 잠식. 할인점과 슈퍼마켓은 온라인 쇼핑의 가격 경쟁력에 밀려 롯데와 신세계가 온라인 채널 강화에 대규모 투자 추진. e커머스 시장은 쿠팡 같은 소셜커머스, 오픈마켓, 오프라인 강자들로 나뉘어 치열한 경쟁.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "소셜커머스/오픈마켓 사업자, 시장 주도 기업"},
            {"type": "company", "name": "롯데", "role": "대형 할인점/백화점 운영사, 온라인 투자 계획"},
            {"type": "company", "name": "신세계", "role": "대형 할인점/백화점 운영사, 온라인 투자 계획"},
            {"type": "company", "name": "G마켓", "role": "오픈마켓 사업자"},
            {"type": "company", "name": "옥션", "role": "오픈마켓 사업자"},
            {"type": "company", "name": "11번가", "role": "오픈마켓 사업자"},
            {"type": "company", "name": "티몬", "role": "소셜커머스 사업자"},
            {"type": "company", "name": "위메프", "role": "소셜커머스 사업자"},
        ],
        "relations": [
            {"source": "롯데", "target": "신세계", "type": "competition", "detail": "온라인 시장 진출 동시 추진"},
        ],
        "risks": [
            {"type": "market", "description": "오프라인 할인점 시장 축소, 1인 가구 증가와 스마트폰 확산으로 대량구매 모델 약화", "severity": "high"},
            {"type": "market", "description": "온라인 가격 경쟁 심화, 점포 임차료 및 인건비 없는 온라인이 가격 경쟁에서 우월", "severity": "high"},
            {"type": "market", "description": "신규 플레이어 시장점유율 확보 어려움", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/97",
        "title": "e커머스 전쟁, 최후의 승자는?(6)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-21",
        "summary": "온라인 쇼핑 성장으로 오프라인 유통 패러다임 변화. 이마트는 기존점 매출 감소로 신규 출점에 의존. 롯데쇼핑은 현금흐름 창출 실패로 매장 세일즈앤리스백과 외부 자금조달에 의존, 할인점 투자 중단하고 구조조정 중.",
        "entities": [
            {"type": "company", "name": "이마트", "role": "국내 할인점 운영업체"},
            {"type": "company", "name": "롯데쇼핑", "role": "백화점, 슈퍼마켓, 할인점 운영"},
            {"type": "company", "name": "롯데마트", "role": "롯데그룹 할인점 브랜드"},
            {"type": "company", "name": "신세계그룹", "role": "온라인 쇼핑 투자 진행 중"},
            {"type": "company", "name": "홈플러스", "role": "할인점 운영업체"},
        ],
        "relations": [
            {"source": "이마트", "target": "롯데쇼핑", "type": "competition", "detail": "국내 할인점 시장 주요 경쟁사"},
        ],
        "risks": [
            {"type": "market", "description": "온라인 쇼핑 성장으로 오프라인 유통 수요 감소", "severity": "high"},
            {"type": "financial", "description": "롯데쇼핑의 영업현금흐름 악화 및 외부 자금조달 의존", "severity": "high"},
            {"type": "strategic", "description": "롯데마트 할인점 투자 중단 및 구조조정 진행", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/96",
        "title": "e커머스 전쟁, 최후의 승자는?(5)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-19",
        "summary": "신세계와 롯데의 유통 전략 차이 분석. 신세계는 혁신적 신규 사업 개척(이마트, 프리미엄 아울렛, 스타필드)으로 리더십 확보, 롯데는 M&A를 통한 외적 성장에 집중. 온라인 쇼핑 시대 진입으로 두 그룹 실적 엇갈리며, 롯데마트 부진이 심각.",
        "entities": [
            {"type": "company", "name": "신세계그룹", "role": "유통 업계 리더"},
            {"type": "company", "name": "롯데그룹", "role": "경쟁사"},
            {"type": "company", "name": "이마트", "role": "할인점 사업부"},
            {"type": "company", "name": "롯데마트", "role": "할인점 사업부"},
        ],
        "relations": [
            {"source": "신세계그룹", "target": "이마트", "type": "ownership", "detail": "소유 관계"},
            {"source": "롯데그룹", "target": "롯데마트", "type": "ownership", "detail": "소유 관계"},
        ],
        "risks": [
            {"type": "market", "description": "온라인 쇼핑 시장 확대가 이마트, 롯데마트에 영향", "severity": "high"},
            {"type": "operational", "description": "롯데그룹의 중국시장 실패 및 불매운동", "severity": "high"},
            {"type": "market", "description": "할인점 시장 전반 부진", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/95",
        "title": "e커머스 전쟁, 최후의 승자는?(4)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-17",
        "summary": "롯데쇼핑과 신세계그룹의 한국 유통업계 시장 지위 비교. 롯데쇼핑이 더 높은 매출을 보고하지만, 직매입 vs 위탁판매 회계 방법 차이로 실제 시장점유율 차이는 더 작음. 두 그룹이 e커머스 교란에 어떻게 다르게 대응하는지 분석 배경 제시.",
        "entities": [
            {"type": "company", "name": "롯데쇼핑", "role": "백화점, 할인점, 홈쇼핑 보유 국내 주요 소매 리더"},
            {"type": "company", "name": "신세계", "role": "백화점과 할인점(이마트) 중심 주요 경쟁사"},
            {"type": "company", "name": "이마트", "role": "신세계그룹 계열 할인점 체인"},
            {"type": "company", "name": "롯데마트", "role": "롯데쇼핑 할인점 사업부"},
        ],
        "relations": [
            {"source": "롯데쇼핑", "target": "신세계", "type": "competition", "detail": "한국 소매 유통의 서로 다른 사업 전략을 가진 주요 라이벌"},
            {"source": "신세계", "target": "이마트", "type": "affiliation", "detail": "이마트는 별도 법인이나 신세계와 밀접한 운영 조율 유지"},
        ],
        "risks": [
            {"type": "market", "description": "e커머스 교란이 전통 소매에 영향, 2015년 이후 두 그룹 모두 직접적 영향", "severity": "high"},
            {"type": "financial", "description": "매출 회계 방법론 차이로 진정한 시장 지위 불명확", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/94",
        "title": "e커머스 전쟁, 최후의 승자는?(3)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-14",
        "summary": "한국 소매업계 패러다임 전환 추적: 백화점에서 할인점(1990-2000년대), 이제 온라인 쇼핑으로. 이마트가 월마트 진출에도 불구하고 어떻게 지배했는지, 젊은 세대가 온라인 배송 서비스를 선호하면서 할인점이 쇠퇴하는 현상 분석.",
        "entities": [
            {"type": "company", "name": "이마트", "role": "월마트를 이긴 시장 리더 할인점 체인"},
            {"type": "company", "name": "월마트", "role": "1998년 한국 시장 진입, 2006년 철수한 국제 유통업체"},
            {"type": "company", "name": "까르푸", "role": "한국에서 경쟁 실패한 세계 2위 할인점"},
            {"type": "company", "name": "신세계-이마트그룹", "role": "이마트 모회사, 온라인 대응으로 SSG.com 출시"},
            {"type": "company", "name": "홈플러스", "role": "이마트와 경쟁하는 할인점 체인"},
            {"type": "company", "name": "롯데마트", "role": "소매 경쟁 참여 할인점 체인"},
            {"type": "company", "name": "쿠팡", "role": "할인점 교란하는 온라인 쇼핑 플랫폼"},
            {"type": "company", "name": "SSG닷컴", "role": "신세계-이마트그룹이 출시한 온라인 플랫폼"},
            {"type": "person", "name": "이명희", "role": "미국에서 할인점 개념 도입한 신세계그룹 회장"},
        ],
        "relations": [
            {"source": "신세계그룹", "target": "이마트", "type": "ownership", "detail": "소유 및 운영"},
            {"source": "이마트", "target": "월마트", "type": "acquisition", "detail": "2006년 월마트 한국 16개 매장 인수"},
        ],
        "risks": [
            {"type": "market", "description": "소비자 인구 변화로 할인점 방문객 감소", "severity": "high"},
            {"type": "market", "description": "온라인 유통업체들이 더 빠른 배송과 낮은 가격 제공", "severity": "high"},
            {"type": "financial", "description": "할인점 업계 2018년 사상 첫 매출 감소", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/93",
        "title": "e커머스 전쟁, 최후의 승자는?(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-12",
        "summary": "한국 소매 유통이 오프라인에서 온라인 채널로 전환 중. 백화점은 회복세 보이나 할인점은 매출 감소 직면. 인터넷 쇼핑은 연간 20% 이상 성장 유지하나 홈쇼핑은 정체.",
        "entities": [
            {"type": "company", "name": "신세계", "role": "백화점 운영사"},
            {"type": "company", "name": "현대백화점", "role": "백화점 운영사"},
            {"type": "company", "name": "롯데쇼핑", "role": "할인점, 백화점 등 소매 업태 운영"},
            {"type": "company", "name": "이마트", "role": "국내 선도 할인점 운영사"},
            {"type": "company", "name": "롯데마트", "role": "국내 3위 할인점"},
            {"type": "company", "name": "BGF리테일", "role": "CU 편의점 프랜차이저"},
            {"type": "company", "name": "GS리테일", "role": "GS25 편의점 프랜차이저"},
        ],
        "relations": [
            {"source": "롯데쇼핑", "target": "롯데마트", "type": "ownership", "detail": "운영 법인, 자회사"},
        ],
        "risks": [
            {"type": "market", "description": "슈퍼마켓, 할인점 전반의 오프라인 소매 매출 감소", "severity": "high"},
            {"type": "market", "description": "온라인 쇼핑 급성장으로 전통 소매 채널 잠식", "severity": "high"},
            {"type": "market", "description": "편의점 업계 2018년 이후 성장 둔화", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/92",
        "title": "e커머스 전쟁, 최후의 승자는?(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-10",
        "summary": "한국 유통시장이 오프라인에서 온라인으로 패러다임 전환하면서 e커머스 경쟁 심화. 쿠팡의 급성장으로 타격받은 신세계-이마트그룹과 롯데그룹이 온라인사업 통합하여 SSG.com과 롯데닷컴으로 반격 시작. 최종 승자는 여전히 불확실.",
        "entities": [
            {"type": "company", "name": "쿠팡", "role": "소셜커머스 업체, 시장 선도자"},
            {"type": "company", "name": "신세계-이마트그룹", "role": "할인점/백화점 운영, SSG.com 설립사"},
            {"type": "company", "name": "롯데그룹", "role": "유통공룡, 온라인사업 통합 추진"},
            {"type": "company", "name": "이베이코리아", "role": "오픈마켓 사업자"},
            {"type": "person", "name": "손정의", "role": "소프트뱅크 회장, 쿠팡 투자자"},
            {"type": "company", "name": "SSG닷컴", "role": "이마트와 신세계 온라인 통합 법인"},
            {"type": "company", "name": "롯데닷컴", "role": "롯데 온라인 통합 플랫폼"},
        ],
        "relations": [
            {"source": "신세계-이마트그룹", "target": "SSG닷컴", "type": "ownership", "detail": "자회사 설립/통합"},
            {"source": "쿠팡", "target": "손정의", "type": "investment", "detail": "투자 지원"},
        ],
        "risks": [
            {"type": "financial", "description": "쿠팡 연간 1조원 적자, 티몬, 위메프도 누적 적자", "severity": "high"},
            {"type": "operational", "description": "온라인 쇼핑 시장 빠른 성장은 오프라인 쇼핑 둔화 의미", "severity": "high"},
            {"type": "market", "description": "대형 유통사들 참전으로 e커머스 시장 경쟁 심화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/91",
        "title": "가시밭길 LG디스플레이(7)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-07",
        "summary": "LG디스플레이는 광저우 팹 본격 가동으로 OLED 생산능력 2배 증가 기대. 그러나 중국 업체의 10.5세대 LCD 공급 증가와 삼성의 QD-LCD 경쟁으로 수익성 개선이 기대 이하가 될 수 있음. 구조적 공급 과잉은 당분간 해소 어려움.",
        "entities": [
            {"type": "company", "name": "LG디스플레이", "role": "대형 OLED 패널 독점 공급사"},
            {"type": "company", "name": "삼성디스플레이", "role": "중소형 OLED 및 QD-LCD 생산사"},
            {"type": "company", "name": "BOE", "role": "중국 최대 패널업체, 10.5세대 팹 운영"},
            {"type": "company", "name": "삼성전자", "role": "QD-LCD TV 판매사"},
        ],
        "relations": [
            {"source": "LG디스플레이", "target": "BOE", "type": "competition", "detail": "OLED와 LCD 시장에서 경쟁 관계"},
            {"source": "LG디스플레이", "target": "삼성디스플레이", "type": "competition", "detail": "OLED 시장 선도 경쟁"},
        ],
        "risks": [
            {"type": "market", "description": "중국 업체의 지속적 설비 증설로 LCD 패널 가격 하락 가속화", "severity": "high"},
            {"type": "operational", "description": "LCD와 QD-LCD와의 경쟁을 통해 OLED 채용 확대 필요", "severity": "high"},
            {"type": "financial", "description": "연간 1조원 규모의 감가상각비 증가로 영업이익 압박", "severity": "high"},
            {"type": "market", "description": "2018년 이후 BOE 등 5개 업체 OLED 팹에 정부 각각 22-32억 달러 지원", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/90",
        "title": "가시밭길 LG디스플레이(6)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2020-02-05",
        "summary": "LG디스플레이의 2020년 실적은 전년보다 악화되지 않을 전망이나, LCD 시장 주도권이 중국으로 넘어간 상황에서 회사 미래는 OLED 사업 성과에 달림. OLED 패널 가격 하락 폭이 수익성 좌우, 광저우 공장의 MMG 기술 적용이 원가 경쟁력 강화의 열쇠.",
        "entities": [
            {"type": "company", "name": "LG디스플레이", "role": "LCD 및 OLED 패널 제조사"},
            {"type": "company", "name": "삼성디스플레이", "role": "중소형 OLED 시장 주도사"},
            {"type": "company", "name": "BOE", "role": "중국 대형 디스플레이 업체"},
            {"type": "company", "name": "비전옥스", "role": "중국 디스플레이 업체"},
            {"type": "company", "name": "티안마", "role": "중국 디스플레이 업체"},
        ],
        "relations": [
            {"source": "LG디스플레이", "target": "삼성디스플레이", "type": "competition", "detail": "OLED 시장 경쟁자이면서 LCD에서는 협력적"},
            {"source": "LG디스플레이", "target": "BOE", "type": "competition", "detail": "LCD 시장 경쟁, BOE는 정부 보조금으로 우위"},
        ],
        "risks": [
            {"type": "market", "description": "LCD 시장 구조적 수급 불균형 지속", "severity": "high"},
            {"type": "market", "description": "중국 정부 지원으로 강화되는 중국 업체 경쟁력", "severity": "critical"},
            {"type": "market", "description": "OLED 패널 가격 하락으로 인한 수익성 악화", "severity": "high"},
            {"type": "market", "description": "중국 업체의 OLED 분야 추격으로 선점 우위 희석", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (36차) ===\n")

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
