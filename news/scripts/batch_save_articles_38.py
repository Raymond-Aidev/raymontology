#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 38차 (이마트/SPC삼립/셀트리온/신라젠/금호그룹 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/69",
        "title": "흔들리는 이마트(4) - SSG, 차세대 먹거리 될까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-12-04",
        "summary": "이마트는 오프라인 할인점 투자를 축소하고 SSG.com 온라인 채널에 1조원 이상을 투자 중이나, 오프라인 매출 부진으로 현금흐름 창출에 어려움을 겪고 있다. SSG.com은 3조원의 기업가치로 평가받았으나 강력한 경쟁사들 속에서 5년 내 상장 목표 달성이 불확실한 상황이다.",
        "entities": [
            {"type": "company", "name": "이마트", "role": "모회사 겸 주요 수익원"},
            {"type": "company", "name": "SSG.com", "role": "온라인 유통 자회사"},
            {"type": "company", "name": "신세계그룹", "role": "최상위 모회사"},
            {"type": "company", "name": "어피너티에쿼티파트너스", "role": "사모펀드 투자자"},
            {"type": "company", "name": "블루런벤처스", "role": "사모펀드 투자자"},
            {"type": "company", "name": "쿠팡", "role": "경쟁사"},
        ],
        "relations": [
            {"source": "신세계그룹", "target": "이마트", "type": "ownership", "detail": "최상위 모회사"},
            {"source": "이마트", "target": "SSG.com", "type": "ownership", "detail": "주요 자회사"},
        ],
        "risks": [
            {"type": "financial", "description": "이마트 연결법인의 잉여현금흐름이 적자(약 3000억원) 상태로 투자 자금 조달 능력 부족", "severity": "high"},
            {"type": "operational", "description": "SSG.com이 현재 적자 운영 중이며, 규모의 경제 달성까지 상당 기간 필요", "severity": "high"},
            {"type": "governance", "description": "사모펀드의 풋백옵션으로 인해 5년 내 IPO 미달성 시 연율 25% 이자로 지분 되매입 의무", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/68",
        "title": "흔들리는 이마트(3) - 온라인을 새로운 성장판으로",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-10-16",
        "summary": "이마트의 2분기 연결기준 순매출은 4조5810억원으로 14.8% 증가했으나, 이는 주로 SSG.com 같은 자회사 매출 성장에 기인하며 본체 매출은 2.3% 감소했다. 영업손실의 주요 원인은 부동산 보유세 증가와 온라인·트레이더스 같은 신사업 투자다.",
        "entities": [
            {"type": "company", "name": "이마트", "role": "주요 피분석 기업"},
            {"type": "company", "name": "SSG.com", "role": "온라인 자회사"},
            {"type": "company", "name": "트레이더스", "role": "창고형 매장 사업부"},
            {"type": "company", "name": "이마트24", "role": "편의점 자회사"},
            {"type": "company", "name": "GFH", "role": "미국 식품소매 인수법인"},
        ],
        "relations": [
            {"source": "이마트", "target": "SSG.com", "type": "ownership", "detail": "자회사로서 온라인 판매 담당"},
            {"source": "이마트", "target": "GFH", "type": "acquisition", "detail": "2018년 3070억원에 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "연결기준 영업이익이 299억원 적자로 전환, SSG.com과 이마트24의 적자폭 확대", "severity": "high"},
            {"type": "operational", "description": "기존 할인점 매출이 4.6% 역신장, 국내 할인점 시장 포화상태", "severity": "high"},
            {"type": "regulatory", "description": "부동산 보유세 부담이 1012억원으로 증가하여 수익성 압박", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/67",
        "title": "흔들리는 이마트(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-10-11",
        "summary": "이마트의 핵심 할인점 사업부에서 기존점 매출이 지속적으로 감소하고 있으며, 마진율 하락으로 수익성이 악화되고 있다. 운전자본 부담 증가로 영업활동 현금흐름이 급감하는 상황에서 온라인 채널 이동과 높은 고정비 구조 문제에 직면해 있다.",
        "entities": [
            {"type": "company", "name": "이마트", "role": "주요 대형 할인점 업체"},
            {"type": "company", "name": "롯데마트", "role": "경쟁사"},
            {"type": "company", "name": "홈플러스", "role": "경쟁사"},
            {"type": "company", "name": "SSG.com", "role": "이마트의 온라인 자회사"},
        ],
        "relations": [
            {"source": "이마트", "target": "SSG.com", "type": "ownership", "detail": "온라인사업부 통합 운영"},
        ],
        "risks": [
            {"type": "market", "description": "온라인 소비채널로의 이동으로 오프라인 할인점 시장 축소", "severity": "critical"},
            {"type": "financial", "description": "마진율 지속적 하락으로 수익성 악화, 올해 상반기 기존점 매출 3.5% 감소", "severity": "critical"},
            {"type": "operational", "description": "높은 고정 인건비(약 2만5850명) 부담으로 매출 감소 시 손실 확대", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/66",
        "title": "흔들리는 이마트(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-10-04",
        "summary": "이마트를 포함한 국내 대형마트 시장이 쿠팡의 로켓배송 같은 새로운 유통채널에 밀려 역성장하고 있다. 이마트는 SSG.COM과 쓱배송으로 반격을 시작했으나, 자회사들의 손실로 인해 전체 영업이익이 감소하고 있다.",
        "entities": [
            {"type": "company", "name": "이마트", "role": "국내 대형마트 선두주자"},
            {"type": "company", "name": "쿠팡", "role": "온라인 배송 신규사업자"},
            {"type": "company", "name": "SSG.COM", "role": "이마트의 온라인 쇼핑몰"},
            {"type": "company", "name": "롯데마트", "role": "대형마트 경쟁사"},
            {"type": "company", "name": "홈플러스", "role": "대형마트 경쟁사"},
            {"type": "person", "name": "정용진", "role": "이마트 부회장"},
        ],
        "relations": [
            {"source": "쿠팡", "target": "이마트", "type": "competition", "detail": "로켓배송 vs 쓱배송 배송 전쟁"},
            {"source": "이마트", "target": "SSG.COM", "type": "ownership", "detail": "신세계와의 물적분할을 통한 온라인사업 통합"},
        ],
        "risks": [
            {"type": "market", "description": "대형마트 시장이 역성장 진입, 2018년 매출 33.5조원으로 처음 감소", "severity": "high"},
            {"type": "operational", "description": "할인점 매출 정체로 인한 핵심사업 부진, 2019년 상반기 영업이익 50% 감소", "severity": "high"},
            {"type": "financial", "description": "자회사 확대로 인한 손실 누적, 연결법인 영업이익이 개별법인을 하회", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/65",
        "title": "SPC삼립 빵빵한가(3)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-10-02",
        "summary": "SPC GFS의 외부 매출이 증가하면서 삼립의 판매망이 확대되고 있다. 특히 2019년 상반기 SPC GFS의 외부 매출이 약 1000억원에 달할 것으로 추정되며, 가평휴게소 위탁운영으로 추가적인 성장 기회가 생겼다.",
        "entities": [
            {"type": "company", "name": "SPC삼립", "role": "모회사"},
            {"type": "company", "name": "SPC GFS", "role": "식자재 유통 및 푸드서비스 자회사"},
            {"type": "company", "name": "삼립식품", "role": "제빵 사업 자회사"},
            {"type": "company", "name": "파리크라상", "role": "SPC 계열사"},
        ],
        "relations": [
            {"source": "SPC삼립", "target": "SPC GFS", "type": "ownership", "detail": "모회사-자회사 관계"},
            {"source": "SPC삼립", "target": "가평휴게소", "type": "operation", "detail": "2019년 9월부터 10년간 위탁운영"},
        ],
        "risks": [
            {"type": "financial", "description": "가평휴게소 위탁운영으로 연간 258억원의 리스료 발생, 연결자산의 34% 규모", "severity": "high"},
            {"type": "operational", "description": "SPC GFS 수익성이 낮아 외부 매출 증가가 이익으로 직결되지 않을 위험", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/64",
        "title": "SPC삼립 빵빵한가(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-09-27",
        "summary": "SPC삼립의 상반기 실적 호조는 샌드위치 확대가 아닌 유통사업부문의 급속한 성장이 주요 원인이다. 밀다원 등 자회사 합병으로 내부거래 제거 규모가 줄어들면서 연결매출이 크게 증가한 반면, 유통사업의 낮은 이익률로 인해 실질적 수익성은 오히려 감소했다.",
        "entities": [
            {"type": "company", "name": "SPC삼립", "role": "SPC그룹의 식자재 제조 및 유통 중심 계열사"},
            {"type": "company", "name": "삼립식품", "role": "SPC삼립의 푸드사업부문 담당"},
            {"type": "company", "name": "샌드팜", "role": "삼립식품의 샌드위치 공급업체"},
            {"type": "company", "name": "샤니", "role": "샌드팜의 모회사"},
            {"type": "person", "name": "허영인", "role": "샤니 대주주 (90% 지분 보유)"},
        ],
        "relations": [
            {"source": "삼립식품", "target": "샌드팜", "type": "supply", "detail": "샌드위치 납품받아 유통"},
            {"source": "샤니", "target": "샌드팜", "type": "ownership", "detail": "100% 자회사로 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "유통사업부문의 영업이익률이 0.4~0.5%에 불과해 실질적 수익성 미흡", "severity": "high"},
            {"type": "financial", "description": "상반기 매출 12% 증가에도 영업이익이 281억원에서 262억원으로 하락", "severity": "high"},
            {"type": "governance", "description": "샤니의 허영인 일가가 90% 지분 보유로 상장사 소수주주 이익 침해 우려", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/63",
        "title": "SPC삼립 빵빵한가(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-10-07",
        "summary": "삼립식품은 양산빵 시장에서 71% 점유율을 보유한 지배적 사업자로, SPC그룹의 핵심 캐쉬카우 역할을 하고 있다. 편의점 시장 진출과 샤니의 영업권 통합을 통해 그룹 내 양산빵 사업을 일원화하며 지속적 성장을 이루고 있다.",
        "entities": [
            {"type": "company", "name": "SPC삼립", "role": "양산빵 시장 주요 사업자"},
            {"type": "company", "name": "파리크라상", "role": "SPC그룹 최상위 지배회사"},
            {"type": "company", "name": "파리바게트", "role": "베이커리 시장 주요 사업자"},
            {"type": "company", "name": "샤니", "role": "과거 경쟁자, 현재 삼립식품 공급사"},
        ],
        "relations": [
            {"source": "파리크라상", "target": "SPC삼립", "type": "ownership", "detail": "삼립식품 지분 40.7% 보유"},
            {"source": "SPC그룹", "target": "샤니", "type": "consolidation", "detail": "2011년 샤니 매출처 영업권을 삼립식품으로 통합"},
        ],
        "risks": [
            {"type": "market", "description": "양산빵 시장이 정체 또는 축소되고 있는 상황에서 지속성장이 제한될 수 있음", "severity": "high"},
            {"type": "operational", "description": "2분기 매출 12.3% 증가에도 영업이익은 전년 동기와 동일 수준으로, 수익성 개선이 미흡", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/62",
        "title": "셀트리온 형제 반기실적 리뷰(7) - 셀트리온헬스케어 실적호전의 진짜 배경은",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-10-06",
        "summary": "셀트리온 합체의 매출원가 추정을 위해서는 헬스케어 장부의 셀트리온 판매 마진을 제거하고, 헬스케어의 추가 원가를 반영해야 한다. 올해 상반기 셀트리온의 재고 전략 변화로 인해 합체 회사의 영업이익이 두 회사 합계를 초과하는 긍정적 흐름이 나타났다.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "의약품 제조사"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "의약품 유통·판매사"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "supply", "detail": "셀트리온이 제조한 의약품을 헬스케어에 판매"},
        ],
        "risks": [
            {"type": "financial", "description": "합체 회사 매출원가 추정에 상당한 오차 가능성이 있어 영업이익 추정치 신뢰도 저하", "severity": "high"},
            {"type": "operational", "description": "셀트리온이 헬스케어에 판매한 의약품 중 다량이 2년치 재고로 보관되어 현금흐름 악화 우려", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/61",
        "title": "셀트리온 형제 반기실적 리뷰(6)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-09-18",
        "summary": "셀트리온과 셀트리온헬스케어를 하나의 사업실체로 합쳐 분석한 결과, 합체 자산은 6조4500억원의 단순합산에서 4조6000억원으로 감소한다. 특히 이익잉여금은 2조2461억원에서 실질 3400억원 수준으로 축소되어, 셀트리온 이익잉여금의 상당 부분이 허수임을 시사한다.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "모기업, 생산 및 판매 담당"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "자회사, 판매 전담 법인"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "transaction", "detail": "매출채권 7000억원 규모"},
        ],
        "risks": [
            {"type": "financial", "description": "이익잉여금 실질가치가 단순합산의 15% 수준으로 축소되어 자본 건전성이 과장된 상태", "severity": "high"},
            {"type": "governance", "description": "두 회사 간 출자 관계 부재로 인한 재무 투명성 저하 및 관계자거래 감시 어려움", "severity": "medium"},
            {"type": "strategic", "description": "셀트리온의 생산·재고 전략이 헬스케어 실적을 왜곡시켜 실질 영업성과 판단 곤란", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/60",
        "title": "셀트리온 형제 반기실적 리뷰(5)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-09-17",
        "summary": "셀트리온과 셀트리온헬스케어의 반기 실적을 분석한 글로, 재고 이전이 양사 실적에 미치는 영향을 지적한다. 헬스케어의 영업현금흐름 흑자가 재고자산 감소에 의존하고 있으며, 직접판매 전환에 따른 비용 구조 개선이 불확실하다.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "생산 담당 회사"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "판매 담당 회사"},
            {"type": "person", "name": "서정진", "role": "회장"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "supply", "detail": "완제품 재고를 헬스케어에 이전"},
        ],
        "risks": [
            {"type": "financial", "description": "헬스케어의 영업현금흐름 흑자가 재고자산 감소에 크게 의존 중", "severity": "high"},
            {"type": "operational", "description": "직접판매 전환에 따른 인건비 증가가 전망치와 괴리", "severity": "high"},
            {"type": "market", "description": "램시마, 트룩시마, 허쥬마의 가격 추가 하락 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/59",
        "title": "셀트리온 형제 반기실적 리뷰(4): 두 몸 전략에 변곡점이 온다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-09-11",
        "summary": "셀트리온과 셀트리온헬스케어의 상반기 실적에서 헬스케어 매출이 처음 5000억원을 넘은 긍정적 신호가 나타난 반면, 셀트리온 합체의 재고 부담이 증가했다. 두 회사의 분리 전략이 변곡점을 맞이하고 있으며, 상장사 헬스케어 주주들의 불만이 고조되는 상황이다.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "제조사"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "판매사"},
            {"type": "person", "name": "서정진", "role": "회장"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "business_structure", "detail": "제조-판매 분리 구조로 운영되는 관계사"},
        ],
        "risks": [
            {"type": "strategic", "description": "두 회사 분리 전략의 지속가능성이 의문의 대상, 헬스케어 재고 증가가 이를 상징", "severity": "high"},
            {"type": "governance", "description": "상장사 헬스케어 주주들이 배임 문제를 제기할 가능성", "severity": "high"},
            {"type": "financial", "description": "헬스케어가 매출 전부를 셀트리온에 주면서 외부 차입이나 추가 출자로 생존하는 구조의 지속성 문제", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/58",
        "title": "셀트리온 형제 반기실적 리뷰(3)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-09-07",
        "summary": "셀트리온이 700억원 규모의 완제품 재고를 보유함으로써 헬스케어의 재고 부담을 경감했으나, 이는 회계적 미화에 불과하며 '셀트리온 합체' 관점에서 실질적인 재고 규모는 역대 최대수준에 달한다. 두 회사를 통합으로 봤을 때 약 2조2000억원의 재고자산은 연간 매출의 2년 이상에 해당하는 위험 수준이다.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "제조 부문"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "판매 부문"},
            {"type": "company", "name": "셀트리온제약", "role": "자회사"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "supply", "detail": "완제품 및 반제품 공급"},
        ],
        "risks": [
            {"type": "financial", "description": "셀트리온 합체 기준 6월말 재고자산이 약 2조2000억원으로 역대 최대 규모, 연간 매출의 2배 이상", "severity": "high"},
            {"type": "governance", "description": "셀트리온과 헬스케어 간 내부거래를 통한 재고 분산으로 개별 재무제표 해석이 왜곡될 수 있음", "severity": "high"},
            {"type": "operational", "description": "과도한 재고 규모는 재고 부실화, 유동성 악화, 제품 수명 만료 위험 증가를 의미", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/57",
        "title": "셀트리온 형제 반기실적 리뷰(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-09-05",
        "summary": "셀트리온헬스케어가 상반기 5000억원을 넘는 매출을 기록하며 가격하락 충격에서 벗어났으나, 매출채권과 재고자산의 감소가 두드러진다. 헬스케어의 재고전략 수정으로 현금흐름이 개선되고 있으며, 이는 그룹의 실적 관리 방식 변화를 시사한다.",
        "entities": [
            {"type": "company", "name": "셀트리온헬스케어", "role": "판매 및 유통 회사"},
            {"type": "company", "name": "셀트리온", "role": "제조 및 공급 회사"},
            {"type": "company", "name": "화이자", "role": "유통 파트너사"},
            {"type": "company", "name": "테바", "role": "유통 파트너사"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "supply", "detail": "제조한 의약품을 공급하고 헬스케어가 유통 판매"},
            {"source": "셀트리온헬스케어", "target": "화이자", "type": "distribution", "detail": "유통 파트너사와 변동대가 계약으로 제품 판매"},
        ],
        "risks": [
            {"type": "financial", "description": "램시마 등 제품의 시장가격 급락으로 변동대가 손실 발생 가능성", "severity": "high"},
            {"type": "governance", "description": "셀트리온의 실적 포장을 위해 헬스케어가 일방적으로 희생되고 있다는 의심", "severity": "high"},
            {"type": "market", "description": "유럽 지역 매출 의존도 85% 수준으로 환율 변동 영향 민감", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/56",
        "title": "셀트리온 형제 반기실적 리뷰(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-09-02",
        "summary": "셀트리온은 2019년 상반기에 헬스케어로의 출하를 감소시키면서 재고전략에 변화를 보였으며, 생산량은 늘리되 판매는 줄이는 전략을 펼쳤다. 아울러 자기주식 582억원을 취득하여 주가 관리에 상당한 역량을 집중했다.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "바이오시밀러 제조사"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "바이오시밀러 판매사"},
            {"type": "company", "name": "셀트리온제약", "role": "의약품 판매사"},
        ],
        "relations": [
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "supply", "detail": "바이오시밀러 제품 출하, 재고전략 공조"},
        ],
        "risks": [
            {"type": "operational", "description": "상반기 영업현금흐름이 2분기에 급감하여 재고자산 급증으로 인한 자금 부담 증가", "severity": "medium"},
            {"type": "market", "description": "주가 하락 폭이 크지만 상대주가 지표는 긍정적이나 바이오업계 악재 영향으로 불확실성 존재", "severity": "high"},
            {"type": "financial", "description": "자기주식 취득에 582억원 투입으로 인한 현금유출, 주가 방어 효과 불확실", "severity": "low"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/55",
        "title": "펙사벡 꿈 깨진 신라젠, 돈(錢) 문제에 봉착하다(4)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-08-27",
        "summary": "신라젠의 펙사벡 간암 임상시험이 조기 종료되면서 회사의 계속기업 가정이 흔들리고 있다. 펙사벡 관련 무형자산 688억원이 손상차손으로 처리되었으며, 3분기부터 매출이 사실상 0원으로 수렴할 것으로 예상된다.",
        "entities": [
            {"type": "company", "name": "신라젠", "role": "주요 피사자"},
            {"type": "company", "name": "리즈파마", "role": "홍콩 파트너사"},
            {"type": "company", "name": "트랜스젠", "role": "프랑스 파트너사"},
            {"type": "company", "name": "녹십자", "role": "한국 파트너사"},
            {"type": "company", "name": "리제네론", "role": "신장암 임상 협력사"},
        ],
        "relations": [
            {"source": "신라젠", "target": "리즈파마", "type": "license", "detail": "홍콩·중국·마카오 지역 라이선스 및 공동연구"},
            {"source": "신라젠", "target": "트랜스젠", "type": "license", "detail": "유럽 지역 라이선스 및 공동연구"},
        ],
        "risks": [
            {"type": "financial", "description": "펙사벡 임상 조기 종료로 라이선스·마일스톤 수익이 3분기부터 0원으로 수렴할 예정", "severity": "critical"},
            {"type": "strategic", "description": "기업가치의 80%를 차지했던 펙사벡 실패로 후속 파이프라인 개발이 필수적이나 불확실성 존재", "severity": "critical"},
            {"type": "governance", "description": "계속기업의 가정이 흔들려 재무제표의 회계처리 원칙 의미가 훼손됨", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/54",
        "title": "펙사벡 꿈 깨진 신라젠, 돈(錢) 문제에 봉착하다(3)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-08-21",
        "summary": "신라젠의 펙사벡 임상 3상 실패로 자금조달 능력이 저하되었으며, 3월 발행한 1100억원 규모의 전환사채가 회사의 생명줄이 되었다. 2021년 3월 전환사채 만기를 앞두고 신라젠은 자본시장에서의 신규 자금조달 능력 회복이 절실한 상황이다.",
        "entities": [
            {"type": "company", "name": "신라젠", "role": "주요 대상 기업"},
            {"type": "person", "name": "문은상", "role": "신라젠 대표"},
            {"type": "company", "name": "키움증권", "role": "전환사채 인수사"},
            {"type": "company", "name": "리제네론", "role": "신장암 공동개발 파트너"},
        ],
        "relations": [
            {"source": "신라젠", "target": "키움증권", "type": "financing", "detail": "1100억원 규모 전환사채 발행"},
            {"source": "신라젠", "target": "리제네론", "type": "cooperation", "detail": "신장암 치료제 공동개발 협약"},
        ],
        "risks": [
            {"type": "financial", "description": "전환사채 2021년 3월 만기 도래 시 상환 의무 발생 가능성이 높으며, 현금성자산 1700억원 중 70%가 전환사채 발행자금", "severity": "critical"},
            {"type": "strategic", "description": "펙사벡 임상 3상 실패로 주가 15만원에서 1만원대로 하락하여 자본시장 신규 자금조달 능력 상실", "severity": "critical"},
            {"type": "governance", "description": "기존 대주주인 문은상 등의 추가 출자 또는 주식 처분을 통한 전환사채 상환에 의존", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/53",
        "title": "펙사벡 꿈 깨진 신라젠, 돈(錢) 문제에 봉착하다(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-08-16",
        "summary": "신라젠의 핵심 자산인 펙사벡이 임상 3상에서 무용성 평가에 탈락하며 회사의 기업가치 기반을 상실했다. 연간 500억원의 영업 적자 속에서도 약 2000억원의 현금 동원 능력으로 향후 4년을 버틸 수 있으나, 3월 발행 전환사채 1100억원은 투자자 원금 회수 위협에 직면해 있다.",
        "entities": [
            {"type": "company", "name": "신라젠", "role": "주체 기업"},
            {"type": "company", "name": "신라젠 바이오테라퓨틱스", "role": "100% 자회사"},
            {"type": "person", "name": "문은상", "role": "신라젠 대표"},
        ],
        "relations": [
            {"source": "신라젠", "target": "신라젠 바이오테라퓨틱스", "type": "ownership", "detail": "100% 지분 소유"},
        ],
        "risks": [
            {"type": "strategic", "description": "펙사벡 임상 3상이 무용성 평가 탈락으로 최소한의 약효도 인정받지 못함", "severity": "critical"},
            {"type": "financial", "description": "연간 500억원 규모 영업현금흐름 적자로 보유 현금 소진 가속화", "severity": "critical"},
            {"type": "market", "description": "주가 1만4000원대로 급락으로 전환사채 전환 가능성 극히 낮음", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/52",
        "title": "펙사벡 꿈 깨진 신라젠, 돈(錢) 문제에 봉착하다(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-08-16",
        "summary": "신라젠은 펙사벡 신약 개발이라는 '꿈'에 의존하는 바이오 기업으로, 영업활동으로 수익을 창출하지 못하고 외부 자금조달에 의존하고 있다. 기업공개와 메자닌을 통해 자금을 조달해 왔으나, 임상실패 가능성 속에서 자금 문제에 직면하고 있다.",
        "entities": [
            {"type": "company", "name": "신라젠", "role": "주요 바이오 기업"},
            {"type": "company", "name": "삼성바이오로직스", "role": "비교 기업"},
            {"type": "company", "name": "셀트리온", "role": "비교 기업"},
            {"type": "company", "name": "코오롱티슈진", "role": "비교 기업"},
        ],
        "relations": [
            {"source": "신라젠", "target": "투자자", "type": "funding", "detail": "꿈을 믿는 투자자의 자금 공급에 의존"},
        ],
        "risks": [
            {"type": "financial", "description": "2016년 이후 영업활동으로 2372억원의 현금 손실 기록, 외부 자금조달에 전적 의존", "severity": "critical"},
            {"type": "strategic", "description": "펙사벡 임상3상 실패 임박 상황에서 전환사채 발행으로 기대와 현실 괴리 심화", "severity": "critical"},
            {"type": "market", "description": "메자닌 자금의 특성상 기업 사정 악화 시 부채로 변모하여 리스크 급증", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/51",
        "title": "색동 날개 꺾인 금호그룹(29) - 대한통운 매각 후 원위치 못한 금호터미널",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-08-11",
        "summary": "금호그룹이 2011년 자금난 해소를 위해 대한통운을 매각했으나, 핵심 자산인 금호터미널은 아시아나항공에 맡겨진 채 원래 소속사인 금호산업으로 복귀하지 못했다. 버스터미널 운영 등 사업상 금호산업과 긴밀한 금호터미널은 경영 위기 속에서 외부 자산이 되어버렸다.",
        "entities": [
            {"type": "company", "name": "금호그룹", "role": "주요 기업집단"},
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
            {"type": "company", "name": "대한통운", "role": "운송·물류 자회사"},
            {"type": "company", "name": "금호터미널", "role": "버스터미널 운영 자회사"},
            {"type": "company", "name": "아시아나항공", "role": "항공사 계열사"},
            {"type": "company", "name": "CJ그룹", "role": "인수 기업"},
        ],
        "relations": [
            {"source": "금호그룹", "target": "대한통운", "type": "divestiture", "detail": "2011년 자금난 해소를 위해 대한통운 매각"},
            {"source": "CJ그룹", "target": "대한통운", "type": "acquisition", "detail": "2011년 대한통운 인수 완료"},
            {"source": "아시아나항공", "target": "금호터미널", "type": "acquisition", "detail": "6월 17일 이사회에서 2555억원에 인수 결의"},
        ],
        "risks": [
            {"type": "strategic", "description": "금호터미널이 금호산업으로 복귀하지 못하고 아시아나항공에 계속 소속되어 사업 효율성 저하", "severity": "high"},
            {"type": "financial", "description": "금호산업의 산소호흡기식 경영으로 인해 금호터미널 회수 불가능", "severity": "critical"},
            {"type": "governance", "description": "채권단의 일괄 매각 방침으로 인한 그룹 핵심자산의 외부 매각", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/50",
        "title": "색동 날개 꺾인 금호그룹(28) - 대한통운 인수 후 찾아 온 유동성 위기",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2019-08-07",
        "summary": "금호그룹이 대우건설 인수 이후 과도한 차입금으로 자금난에 처한 상황에서 대한통운 인수를 추진했으나, 금호산업의 유동성 부족으로 대우건설과 아시아나항공이 주체가 되어 인수를 진행했다. 결국 자산 매각 부진과 새로운 투자자 확보 실패로 2009년 워크아웃을 신청하게 된 경위를 분석한다.",
        "entities": [
            {"type": "company", "name": "금호그룹", "role": "피인수자/재정위기 기업"},
            {"type": "company", "name": "금호산업", "role": "지주회사 전환 시도 기업"},
            {"type": "company", "name": "대한통운", "role": "인수 대상 기업"},
            {"type": "company", "name": "대우건설", "role": "인수 주체"},
            {"type": "company", "name": "아시아나항공", "role": "인수 컨소시엄 참여"},
            {"type": "person", "name": "박삼구", "role": "금호그룹 회장"},
        ],
        "relations": [
            {"source": "금호산업", "target": "대우건설", "type": "acquisition", "detail": "2007년경 인수 후 자금압박 심화"},
            {"source": "대우건설", "target": "대한통운", "type": "acquisition", "detail": "2008년 대한통운 인수 시 주도적 역할"},
        ],
        "risks": [
            {"type": "financial", "description": "2007~2008년 영업현금흐름 적자로 유동성 위기 심화", "severity": "critical"},
            {"type": "financial", "description": "2009년 1조원 이상의 차입부채 만기도래로 자금난 초래", "severity": "critical"},
            {"type": "governance", "description": "풋백옵션 리스크: 재무적 투자자의 39% 지분에 대한 3만3000~3만4000원 보장 의무", "severity": "critical"},
            {"type": "market", "description": "2008년 서브프라임 사태로 대우건설 주가 급락", "severity": "critical"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (38차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:40]}...")
        else:
            print(f"[FAIL] {article['title'][:40]}...")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
