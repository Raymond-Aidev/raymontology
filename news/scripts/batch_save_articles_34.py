#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 34차 (빗썸 시리즈 완결/코인원/코빗/두산중공업 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/149",
        "title": "암호화폐 거래소편(완결) - 빗썸 경영권 경쟁, 정말 끝났을까?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-08-06",
        "summary": "빗썸의 복잡한 지배구조와 2018-2019년 경영권 분쟁 분석. 김병건, 이정훈, 김재욱, 원영식 등 여러 당사자들의 쉘컴퍼니와 후순위 증권을 통한 통제권 경쟁.",
        "entities": [
            {"type": "person", "name": "김병건", "role": "BK SG그룹 리더, 빗썸홀딩스 인수 시도"},
            {"type": "person", "name": "이정훈", "role": "前 빗썸홀딩스 대표"},
            {"type": "person", "name": "김재욱", "role": "비트갤럭시아1호 투자조합 주도자"},
            {"type": "person", "name": "원영식", "role": "비덴트 투자자"},
            {"type": "company", "name": "빗썸홀딩스", "role": "인수 및 통제권 분쟁 대상"},
            {"type": "company", "name": "비덴트", "role": "빗썸홀딩스 지분 보유"},
            {"type": "company", "name": "버킷스튜디오", "role": "비트원 주식 인수사"},
            {"type": "company", "name": "BTHMB홀딩스", "role": "빗썸홀딩스 모회사"},
        ],
        "relations": [
            {"source": "김병건", "target": "빗썸홀딩스", "type": "acquisition_attempt", "detail": "SG 브레인테크놀로지 통해 인수 시도, 2019년 9월 실패"},
            {"source": "원영식", "target": "비덴트", "type": "investment", "detail": "50억원 전환사채 인수, 주요 주주 전환"},
            {"source": "비덴트", "target": "빗썸홀딩스", "type": "ownership", "detail": "약 35.44% 지분 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "비트원-비덴트-빗썸홀딩스 순환출자 구조로 불투명성과 이해상충 발생", "severity": "critical"},
            {"type": "financial", "description": "빗썸홀딩스 1년 내 가치 37% 하락(주당 78백만원→49.5백만원)", "severity": "high"},
            {"type": "governance", "description": "빗썸홀딩스 25% '기타주주' 정체와 정렬 불명확", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/148",
        "title": "암호화폐 거래소편(14) - 원영식의 빗썸 투자, 성공이냐 실패냐",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-08-03",
        "summary": "원영식이 전환사채로 빗썸 인수 자금 지원했으나 비덴트 주가 하락으로 수익성 악화. 이정훈이 65% 의결권으로 빗썸 경영권 장악.",
        "entities": [
            {"type": "person", "name": "원영식", "role": "W홀딩컴퍼니 회장"},
            {"type": "person", "name": "김병건", "role": "초기 빗썸 인수 주도자"},
            {"type": "person", "name": "이정훈", "role": "현재 경영권 보유자"},
            {"type": "person", "name": "김재욱", "role": "빗썸 구주주"},
            {"type": "company", "name": "비덴트", "role": "빗썸홀딩스 최대주주"},
            {"type": "company", "name": "빗썸", "role": "암호화폐 거래소"},
            {"type": "company", "name": "아이오케이", "role": "전환사채 인수자"},
        ],
        "relations": [
            {"source": "원영식", "target": "아이오케이", "type": "ownership", "detail": "W홀딩컴퍼니 경유 80% 이상 지분"},
            {"source": "아이오케이", "target": "비덴트", "type": "investment", "detail": "650억원 전환사채 인수"},
            {"source": "이정훈", "target": "빗썸홀딩스", "type": "control", "detail": "우호지분 포함 65% 의결권 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "비덴트 2년 연속 영업현금흐름 적자, 600억원 이상 전환사채 상환 의무, 현금 170억원으로 430억원 부족", "severity": "critical"},
            {"type": "governance", "description": "비덴트가 최대주주이나 경영권 부재, 아이오케이 전환 시 24.84% 지분으로 분쟁 심화 가능", "severity": "high"},
            {"type": "market", "description": "암호화폐 시장 침체로 빗썸 가치 급락, 비덴트 주가 16,000원대에서 6,000원 이하로 하락", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/147",
        "title": "암호화폐 거래소편(13) - 김재욱과 이정훈, 빗썸 인수 동지의 갈림길",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-07-29",
        "summary": "빗썸 인수 과정에서 비덴트, 비티원, 버킷스튜디오, 옴니텔 4개 상장사가 자금조달 수단으로 활용되었으나 실질적 현금흐름 창출 없음. 2018년 하반기 블록체인 시장 악화로 인수자들 간 갈등 발생.",
        "entities": [
            {"type": "person", "name": "김재욱", "role": "빗썸 초기 인수자"},
            {"type": "person", "name": "이정훈", "role": "빗썸 재인수 주도자"},
            {"type": "person", "name": "김병건", "role": "SG BK그룹 회장"},
            {"type": "company", "name": "비덴트", "role": "빗썸홀딩스 지분 보유 상장사"},
            {"type": "company", "name": "빗썸", "role": "암호화폐 거래소"},
            {"type": "company", "name": "SG브레인테크놀로지", "role": "싱가포르 법인"},
        ],
        "relations": [
            {"source": "이정훈", "target": "SG브레인테크놀로지", "type": "ownership", "detail": "49.997% 지분 보유, 주도권 확보"},
            {"source": "비덴트", "target": "빗썸홀딩스", "type": "ownership", "detail": "최대주주에서 지분 3.5% 양도, 질권 행사됨"},
        ],
        "risks": [
            {"type": "financial", "description": "3000억원 이상 조달 자금의 2% 미만만 실제 자산 구입에 사용", "severity": "critical"},
            {"type": "market", "description": "2018년 하반기부터 블록체인 업황 급격히 악화, 빗썸 가치 추락", "severity": "critical"},
            {"type": "legal", "description": "BTHMB홀딩스의 BXA 코인 사기 논란으로 인수자금 조달 및 신뢰도 악화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/146",
        "title": "암호화폐 거래소편(12) - 김상우는 빗썸 인수에서 발을 뺀 걸까?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-07-24",
        "summary": "김상우의 옴니텔이 빗썸 인수 전략의 도구로 활용된 과정 추적. 언론 해석과 달리 옴니텔은 빗썸코리아와 비티원 지분을 여전히 보유하며 완전 철수 아님.",
        "entities": [
            {"type": "person", "name": "김상우", "role": "옴니텔 최대주주"},
            {"type": "person", "name": "김재욱", "role": "비트갤럭시아 투자조합 핵심 출연자"},
            {"type": "person", "name": "김병건", "role": "BK메디컬그룹 회장"},
            {"type": "company", "name": "옴니텔", "role": "빗썸 인수 도구"},
            {"type": "company", "name": "빗썸홀딩스", "role": "아티스/비티원 인수사"},
            {"type": "company", "name": "비덴트", "role": "지분 보유사"},
        ],
        "relations": [
            {"source": "김상우", "target": "옴니텔", "type": "ownership", "detail": "위지트 통해 최대주주 지위 유지"},
            {"source": "옴니텔", "target": "비티원", "type": "investment", "detail": "지분 6.08% 보유"},
            {"source": "옴니텔", "target": "빗썸코리아", "type": "investment", "detail": "지분 8.43% 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 다층 투자기구 구조로 실질 수익 소유권과 의사결정 권한 불투명", "severity": "high"},
            {"type": "operational", "description": "옴니텔 4년 연속 영업손실 및 2019년 3월 관리종목 지정 상태에서 대규모 자금 투입", "severity": "high"},
            {"type": "legal", "description": "김병건 빗썸 인수 실패 및 BXL 코인 발행 관련 사기 혐의로 법적 노출", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/145",
        "title": "암호화폐 거래소편(11): 비티원은 왜 빗썸 경영권 분쟁의 전선이 되었나",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-07-22",
        "summary": "비티원이 빗썸 경영권 분쟁의 핵심 위치. 김재욱파와 이정훈파 간 복잡한 순환출자 구조를 통해 빗썸홀딩스 지배권 경쟁.",
        "entities": [
            {"type": "person", "name": "김재욱", "role": "비덴트/버킷스튜디오/비티원 대표"},
            {"type": "person", "name": "이정훈", "role": "빗썸홀딩스 이사회 의장, 실질지배자(65%)"},
            {"type": "company", "name": "비티원", "role": "코스피 상장사, 분쟁 중심"},
            {"type": "company", "name": "빗썸홀딩스", "role": "암호화폐 거래소 모회사"},
            {"type": "company", "name": "비덴트", "role": "빗썸홀딩스 34.2% 지분 보유"},
            {"type": "company", "name": "버킷스튜디오", "role": "비티원 주요 주주"},
            {"type": "person", "name": "김상우", "role": "옴니텔 경영진, 김재욱 혈맹"},
        ],
        "relations": [
            {"source": "비트갤럭시아1호 투자조합", "target": "버킷스튜디오", "type": "ownership", "detail": "최대주주"},
            {"source": "버킷스튜디오", "target": "비티원", "type": "ownership", "detail": "주요 지분 보유"},
            {"source": "비덴트", "target": "빗썸홀딩스", "type": "ownership", "detail": "34.2% 지분 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "순환출자 구조로 인한 지배권 불안정성 및 이해관계 상충", "severity": "critical"},
            {"type": "financial", "description": "복잡한 자금 순환과 전환사채 거래를 통한 현금 흐름 의혹", "severity": "high"},
            {"type": "operational", "description": "경영권 분쟁에 따른 기업 운영 불확실성 및 의사결정 지연", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/144",
        "title": "암호화폐 거래소편(10)",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-07-17",
        "summary": "2017년 김재욱과 김상우가 쉘컴퍼니 비덴트와 옴니텔을 통해 빗썸 인수한 과정 분석. 이정훈의 주요 주주로서 동시 등장 배경 추적.",
        "entities": [
            {"type": "person", "name": "김재욱", "role": "아티스트컴퍼니 창업자, 핵심 투자자"},
            {"type": "person", "name": "김상우", "role": "위지트 창업자, 공동 투자자"},
            {"type": "person", "name": "이정훈", "role": "IT메모리 대표, 약 25% 지분 주요 주주"},
            {"type": "company", "name": "빗썸", "role": "타겟 암호화폐 거래소"},
            {"type": "company", "name": "비덴트", "role": "빗썸 인수 쉘컴퍼니"},
            {"type": "company", "name": "옴니텔", "role": "빗썸 인수 쉘컴퍼니"},
            {"type": "company", "name": "코인스닥", "role": "빗썸 복제 거래소"},
        ],
        "relations": [
            {"source": "김재욱, 김상우", "target": "빗썸", "type": "acquisition", "detail": "2017년 비트갤럭시아 투자조합으로 지배지분 인수"},
            {"source": "비덴트, 옴니텔", "target": "빗썸코리아", "type": "ownership", "detail": "각각 1000주를 주당 240만원에 매입"},
            {"source": "비덴트, 옴니텔", "target": "코인스닥", "type": "investment", "detail": "각각 25억원 투자로 빗썸 복제 거래소 설립"},
        ],
        "risks": [
            {"type": "governance", "description": "빗썸홀딩스 주주구조 불투명, 공시에도 모회사 소유 기록 확인 불가", "severity": "high"},
            {"type": "operational", "description": "빗썸 복제 코인스닥 설립은 이해상충 및 시장 잠식 가능성", "severity": "high"},
            {"type": "financial", "description": "비덴트, 옴니텔, 빗썸코리아 간 전략적 가격책정과 주식매입에 복잡한 자금 흐름", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/143",
        "title": "암호화폐 거래소편(9) - 빗썸의 지배구조, 왜 이렇게 복잡할까",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-07-15",
        "summary": "빗썸의 지배구조는 두 세력이 양분하는 복층적 순환출자 구조. 이정훈이 BTHMB홀딩스와 DAA 통해 40.7% 통제하고 우호지분 25% 확보로 실질적 주인.",
        "entities": [
            {"type": "company", "name": "빗썸코리아", "role": "암호화폐 거래소"},
            {"type": "company", "name": "빗썸홀딩스", "role": "빗썸코리아 모회사"},
            {"type": "person", "name": "이정훈", "role": "빗썸홀딩스 이사회 의장, 실질적 주인"},
            {"type": "person", "name": "김재욱", "role": "비덴트 대표, 경영권 분쟁 상대"},
            {"type": "company", "name": "비덴트", "role": "빗썸홀딩스 34.24% 주주"},
            {"type": "company", "name": "BTHMB홀딩스", "role": "싱가포르 소재 이정훈 지분 통제 회사"},
            {"type": "company", "name": "DAA", "role": "이정훈 지분 통제 회사"},
        ],
        "relations": [
            {"source": "이정훈", "target": "빗썸홀딩스", "type": "control", "detail": "BTHMB홀딩스와 DAA 통해 40.7% 통제, 우호지분 포함 65%"},
            {"source": "빗썸홀딩스", "target": "빗썸코리아", "type": "ownership", "detail": "74.1% 지분 보유"},
            {"source": "비덴트", "target": "빗썸홀딩스", "type": "ownership", "detail": "34.24% 지분 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "복층적 순환출자 구조로 실제 경영권과 책임소재 불명확", "severity": "high"},
            {"type": "governance", "description": "해외 투자조합과 정체 불명 회사들 통한 지분 소유로 투명성 부족", "severity": "high"},
            {"type": "legal", "description": "옴니텔 자사주 거래 사례로 '가장납입' 우려", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/142",
        "title": "암호화폐 거래소편(8) - 빗썸, 보릿고개 중 과감한 투자의 정체는?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-07-09",
        "summary": "빗썸은 암호화폐 시황 침체 속에서도 관계회사 지분 취득과 900억원 규모의 설비투자 추진. 계열사 대부분 손실로 향후 성과 창출이 과제.",
        "entities": [
            {"type": "company", "name": "빗썸", "role": "암호화폐 거래소"},
            {"type": "company", "name": "아시아에스테이트", "role": "부동산 중개 자회사"},
            {"type": "company", "name": "비덴트", "role": "빗썸 2대 주주"},
            {"type": "company", "name": "루프이칠사사", "role": "암호화폐 환전업 자회사"},
        ],
        "relations": [
            {"source": "빗썸", "target": "아시아에스테이트", "type": "ownership", "detail": "100% 지분, 116억원 투자"},
            {"source": "빗썸", "target": "비덴트", "type": "investment", "detail": "254억원 취득, 지난해 시가 159억원 (97억원 손실)"},
        ],
        "risks": [
            {"type": "financial", "description": "현금 급감 중 900억원 대규모 투자 집행으로 유동성 위험 증가", "severity": "high"},
            {"type": "operational", "description": "계열사 대부분 손실, 지분법손실 지난해 19억원으로 확대", "severity": "high"},
            {"type": "market", "description": "암호화폐 시황 침체로 계열사 실적 개선 어려움", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/141",
        "title": "암호화폐 거래소편(7): 빗썸이 비덴트와 옴니텔의 자금조달 창구?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-07-06",
        "summary": "빗썸코리아 재무분석 결과, 2019년 영업이익 679억원으로 급감했으나 암호화폐 평가손실 감소로 흑자전환. 주주회사 비덴트와 옴니텔의 전환사채 인수로 자금 유출 구조.",
        "entities": [
            {"type": "company", "name": "빗썸코리아", "role": "암호화폐 거래소"},
            {"type": "company", "name": "비덴트", "role": "빗썸홀딩스 주요주주, 빗썸 2대주주"},
            {"type": "company", "name": "옴니텔", "role": "빗썸 3대주주"},
            {"type": "company", "name": "빗썸홀딩스", "role": "빗썸코리아 모회사"},
        ],
        "relations": [
            {"source": "빗썸코리아", "target": "비덴트", "type": "investment", "detail": "160억원 규모 주식 보유"},
            {"source": "빗썸코리아", "target": "옴니텔", "type": "debt_investment", "detail": "58억원 규모 전환사채 보유"},
            {"source": "비덴트", "target": "빗썸코리아", "type": "ownership", "detail": "지분율 10.29%"},
        ],
        "risks": [
            {"type": "financial", "description": "암호화폐 보유액 2017년 4,160억원에서 2019년 174억원으로 95% 감소", "severity": "critical"},
            {"type": "operational", "description": "2019년 거래량 급감으로 영업이익 2,560억원에서 679억원으로 73% 감소", "severity": "high"},
            {"type": "governance", "description": "주주회사 전환사채 인수로 '유상증자 후 주주에게 거의 다 갖다 바친' 자금 유출 구조", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/140",
        "title": "암호화폐 거래소편(6) - 코빗보다 나을 게 없는 코인원의 유동성",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-07-02",
        "summary": "코인원의 현금성자산은 729억원에서 480억원으로 감소했으며, 고객 예치금 제외 실제 현금은 2억원. 경영진과 사모사채로 자금 조달 의존.",
        "entities": [
            {"type": "company", "name": "코인원", "role": "암호화폐 거래소"},
            {"type": "company", "name": "고위드", "role": "코인원 모회사"},
            {"type": "company", "name": "옐로모바일", "role": "최상위 지배회사(구)"},
            {"type": "company", "name": "에스티비벤처스", "role": "계열사"},
        ],
        "relations": [
            {"source": "고위드", "target": "코인원", "type": "ownership", "detail": "모회사, 매각 추진 중"},
            {"source": "코인원", "target": "옐로모바일", "type": "loan", "detail": "270억원 대여금, 반환 소송 승소하였으나 회수 시기 불확실"},
        ],
        "risks": [
            {"type": "financial", "description": "실제 운용 가능한 현금 2억원으로 극도로 제한적, 영업활동 현금 지속 유출", "severity": "critical"},
            {"type": "governance", "description": "3개월 만기 7.5% 고금리 사채 발행 후 연말까지 상환 미이행", "severity": "high"},
            {"type": "governance", "description": "차입 77억원 중 43억원만 재무제표 반영, 30억원 추적 불가", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/139",
        "title": "암호화폐 거래소편(5) - 코인원, 대여금만 제대로 회수했더라면",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-06-30",
        "summary": "코인원이 지난해 121억원 적자의 절반인 62억원을 대손상각비로 처리. 특수관계자 대여금 621억원 중 250억원 미회수. 최대주주 고위드는 배당금과 대물변제로 현금 유출 회피.",
        "entities": [
            {"type": "company", "name": "코인원", "role": "피분석 회사"},
            {"type": "company", "name": "옐로모바일", "role": "전 최상위 지배회사, 채무자"},
            {"type": "company", "name": "고위드", "role": "현 최대주주, 채무자"},
        ],
        "relations": [
            {"source": "코인원", "target": "옐로모바일", "type": "debt_claim", "detail": "621억원 대여금 중 270억원만 회수, 미회수액 250억원, 소송 진행 중"},
            {"source": "코인원", "target": "고위드", "type": "debt_claim", "detail": "80억원 대여금, 출자전환 및 배당금 상계로 현금 회수 없음"},
            {"source": "고위드", "target": "코인원", "type": "distribution", "detail": "2018년 하반기 68억원 배당결의"},
        ],
        "risks": [
            {"type": "financial", "description": "특수관계자 대여금 621억원 중 약 250억원(40%) 미회수로 대손상각", "severity": "critical"},
            {"type": "governance", "description": "거래소 운영 수익 46억원, 57억원 적자에도 68억원 배당 결의", "severity": "critical"},
            {"type": "legal", "description": "옐로모바일 상대 265억원 반환소송 진행 중이나 회사 산산조각으로 회수 가능성 극히 낮음", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/138",
        "title": "암호화폐 거래소편(4) - 매각 앞둔 코인원, 거래소만 남기고 정리 중?",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-06-26",
        "summary": "코인원은 2017년 암호화폐 호황 시 연 940억원 매출을 기록했으나, 2018년 이후 시장 침체로 지난해 120억원 매출에 121억원 순손실. 거래소 외 사업 청산 중.",
        "entities": [
            {"type": "company", "name": "코인원", "role": "구조조정 중인 암호화폐 거래소"},
            {"type": "company", "name": "고위드", "role": "코인원 모회사"},
            {"type": "company", "name": "아이펀팩토리", "role": "게임서버 엔진 자회사 (68% 보유)"},
        ],
        "relations": [
            {"source": "고위드", "target": "코인원", "type": "ownership", "detail": "모회사"},
            {"source": "코인원", "target": "아이펀팩토리", "type": "investment", "detail": "68% 지분 2018년 취득, 취득가 171억원"},
        ],
        "risks": [
            {"type": "financial", "description": "매출 안정에도 영업손실 심화, 62억원 대손충당금은 문제 있는 채권 시사", "severity": "high"},
            {"type": "market", "description": "2017년 하반기 940억원에서 2019년 120억원으로 암호화폐 시장 침체", "severity": "critical"},
            {"type": "operational", "description": "다수 자회사 청산과 자산 손상으로 다각화에서 전략적 후퇴", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/137",
        "title": "암호화폐 거래소편(3) - 고위드는, 왜 코인원 손절에 나섰나",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-06-24",
        "summary": "고위드가 자회사 코인원 매각 이유 분석. 고위드 매출과 자산 급격히 감소, 코인원 대규모 적자로 IPO 준비 과정에서 부진 사업 정리 전략.",
        "entities": [
            {"type": "company", "name": "고위드", "role": "코인원 모회사, IPO 준비 중"},
            {"type": "company", "name": "코인원", "role": "암호화폐 거래소, 고위드 자회사"},
            {"type": "company", "name": "옐로모바일", "role": "고위드 과거 최대주주"},
            {"type": "company", "name": "알펜루트자산운용", "role": "고위드 현 최대주주"},
        ],
        "relations": [
            {"source": "고위드", "target": "코인원", "type": "ownership", "detail": "73% 지분 보유"},
            {"source": "알펜루트자산운용", "target": "고위드", "type": "ownership", "detail": "현재 최대주주"},
        ],
        "risks": [
            {"type": "financial", "description": "고위드 자산 2017년 5,000억원에서 2019년 1,700억원으로 급감", "severity": "critical"},
            {"type": "financial", "description": "코인원 대규모 적자 기록 중", "severity": "critical"},
            {"type": "market", "description": "코인원이 '적당한 사자를 만나지 못한 듯' 매각 지연", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/136",
        "title": "암호화폐 거래소편(2): 유동성 고갈 위기 코빗, 사활의 갈림길",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-06-19",
        "summary": "코빗은 2017년 호황 후 극심한 침체로 인력 대규모 감축, 자산 매각하며 생존 도모. 2019년 매출 37억원으로 인건비 60억원 충당 불가, 암호화폐 판매 60억원으로 운영비 충당.",
        "entities": [
            {"type": "company", "name": "코빗", "role": "암호화폐 거래소"},
            {"type": "person", "name": "김정주", "role": "회장"},
        ],
        "relations": [
            {"source": "김정주", "target": "코빗", "type": "ownership", "detail": "회장으로서 회사 매각 검토 중"},
        ],
        "risks": [
            {"type": "financial", "description": "회사 가용 현금 13억원, 암호화폐 침체 시 운영비 125억원 충당 불가", "severity": "critical"},
            {"type": "operational", "description": "극심한 인력 감축과 시설 축소로 '장사 접겠다'는 의심 정도의 운영 악화", "severity": "critical"},
            {"type": "governance", "description": "회장의 매각 의도로 증자 등 경영 정상화 지원 불가", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/135",
        "title": "암호화폐 거래소편(1) - 코빗, 고객을 잃다",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-06-17",
        "summary": "코빗은 2017년 김정주 회장의 NXC가 912억5000만원에 인수한 국내 최초 암호화폐 거래소. 2017년 697억원 순이익에서 2018년 458억원, 2019년 129억원 순손실로 전환.",
        "entities": [
            {"type": "company", "name": "코빗", "role": "암호화폐 거래소"},
            {"type": "company", "name": "NXC", "role": "코빗 인수사"},
            {"type": "person", "name": "김정주", "role": "NXC 회장"},
            {"type": "person", "name": "유영석", "role": "코빗 공동창업자"},
            {"type": "person", "name": "김진화", "role": "코빗 공동창업자"},
        ],
        "relations": [
            {"source": "NXC", "target": "코빗", "type": "ownership", "detail": "2017년 912억5000만원에 지분 83% 인수"},
            {"source": "유영석", "target": "코빗", "type": "ownership", "detail": "16% 지분 보유"},
            {"source": "김정주", "target": "코빗", "type": "investment", "detail": "2019년 초 지분 99% 매각 시도"},
        ],
        "risks": [
            {"type": "financial", "description": "고객예탁금 2017년 3118억원에서 2019년 437억원으로 급락", "severity": "critical"},
            {"type": "operational", "description": "영업수익 2018년 754억원에서 2019년 38억원으로 95% 감소", "severity": "critical"},
            {"type": "market", "description": "암호화폐 시장 침체로 거래량 급감 및 고객 대량 이탈", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/134",
        "title": "두산중공업 유동성 위기(완결)",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-06-10",
        "summary": "두산중공업은 석탄화력발전 축소와 LNG·신재생에너지 전환이 필요하나 수년 소요로 당분간 현금흐름 악화 불가피. 두산건설이 주요 부담.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "주요 피분석 대상"},
            {"type": "company", "name": "두산건설", "role": "자회사, 유동성 위기 원인"},
            {"type": "company", "name": "두산밥콕", "role": "자회사, 원전해체 사업"},
            {"type": "company", "name": "두산인프라코어", "role": "우량 자회사"},
            {"type": "company", "name": "두산밥캣", "role": "우량 자회사"},
        ],
        "relations": [
            {"source": "두산중공업", "target": "두산건설", "type": "financial_support", "detail": "10년간 2조700억원 지원"},
            {"source": "두산중공업", "target": "두산건설", "type": "loan_exposure", "detail": "1조3000억원 대여금, 7850억원 대손충당금"},
        ],
        "risks": [
            {"type": "financial", "description": "LNG발전 본격 현금흐름 창출 2022년 이후, 당분간 연 3000~4000억원 EBITDA로 1000억원 이상 이자비용 감당 어려움", "severity": "critical"},
            {"type": "operational", "description": "석탄화력 매출 축소, 신규 사업 본격화까지 3~4년 필요", "severity": "high"},
            {"type": "governance", "description": "두산건설 보유로 '예상치 못한 현금 유출' 위험, 지속적 자본 지원 필요", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/133",
        "title": "두산중공업 유동성 위기(18)",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-06-05",
        "summary": "두산중공업 2020년 1분기 재무상황 분석. 3000억원대 순손실의 주요 원인은 환율 변동 파생상품 평가손실 1800억원. 정부와 채권단 유동성 지원 긴급 필요.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "대상 기업"},
            {"type": "company", "name": "산업은행", "role": "채권자/지원자"},
            {"type": "company", "name": "수출입은행", "role": "채권자/지원자"},
            {"type": "company", "name": "두산그룹", "role": "모기업"},
        ],
        "relations": [
            {"source": "두산중공업", "target": "두산그룹", "type": "subsidiary", "detail": "두산중공업은 두산그룹의 몸통"},
            {"source": "산업은행", "target": "두산중공업", "type": "financial_support", "detail": "1조8000억원 크레디트라인 제공"},
        ],
        "risks": [
            {"type": "financial", "description": "1분기 현금 보유액 3458억원에서 163억원으로 급감", "severity": "critical"},
            {"type": "financial", "description": "분기 약 1조원 수익 대비 9000억원 이상 비용 지출로 영업현금흐름 악화", "severity": "critical"},
            {"type": "operational", "description": "환율 변동 파생상품 평가손실 1800억원", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/132",
        "title": "두산중공업 유동성 위기(17)",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-06-03",
        "summary": "두산중공업 3조원 유동성 목표 달성에 대한 언론 비관론에 반론. 자산 매각뿐 아니라 유상증자가 필수. 자회사 지분을 모회사에 매각하면 상당한 가치 창출 가능.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "유동성 위기 기업"},
            {"type": "company", "name": "㈜두산", "role": "모회사 지주회사"},
            {"type": "company", "name": "두산인프라코어", "role": "주요 자회사 자산"},
            {"type": "company", "name": "두산밥캣", "role": "인프라코어 보유 자회사"},
            {"type": "company", "name": "두산건설", "role": "100% 자회사"},
        ],
        "relations": [
            {"source": "두산중공업", "target": "두산인프라코어", "type": "ownership", "detail": "자회사 상당 지분 보유"},
            {"source": "두산인프라코어", "target": "두산밥캣", "type": "ownership", "detail": "밥캣 51% 지분 보유"},
            {"source": "두산중공업", "target": "두산건설", "type": "ownership", "detail": "100% 보유, 약 1.29조원 가치"},
        ],
        "risks": [
            {"type": "financial", "description": "자산 매각만으로 3조원 유동성 목표 달성 불가, 유상증자 필요", "severity": "high"},
            {"type": "operational", "description": "밥캣이나 인프라코어 같은 주요 자회사 매각 시 그룹 운영과 경쟁력 저하", "severity": "high"},
            {"type": "market", "description": "자산 매각 목표 가격 달성에 타이밍과 시장 상황이 중요", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/131",
        "title": "두산중공업 유동성 위기(16)",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-05-29",
        "summary": "두산중공업 인적분할을 통한 기업 구조조정 논의. 분할하면 계열사 지원으로 누적된 부채가 모회사 ㈜두산으로 이전되어 두산중공업 재무구조 대폭 개선 가능.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "잠재적 인적분할 대상"},
            {"type": "company", "name": "㈜두산", "role": "모회사 지주회사"},
            {"type": "company", "name": "두산건설", "role": "자회사, 잠재적 매각 대상"},
            {"type": "company", "name": "두산인프라코어", "role": "자회사, 핵심 자산"},
        ],
        "relations": [
            {"source": "두산중공업", "target": "㈜두산", "type": "ownership", "detail": "두산중공업은 ㈜두산의 자회사"},
            {"source": "두산중공업", "target": "계열사 지원", "type": "financial_support", "detail": "2005년 이후 계열사 지분 매입에 3조9000억원 지출"},
        ],
        "risks": [
            {"type": "financial", "description": "두산중공업 2005년 이후 계열사 지원으로 3조9000억원 지출하여 4조3000억원 부채 누적", "severity": "critical"},
            {"type": "governance", "description": "인적분할로 부채 부담이 자회사에서 지주회사로 이전, 지주회사에 위험 집중 가능", "severity": "high"},
            {"type": "operational", "description": "매각 가능한 자산 제한적, 인프라코어 같은 핵심 자회사는 매각 불가", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/130",
        "title": "두산중공업 유동성 위기(15) - ㈜두산에 큰 돈이 필요한 이유",
        "author": "강종구",
        "publisher": "DRCR",
        "publish_date": "2020-05-27",
        "summary": "두산그룹이 두산중공업 회생을 위해 3조원 유동성 확보 목표. 두산퓨얼셀과 두산솔루스 매각으로 약 1조4500억원 유동성 창출 예상. 오너 일가 사재 출연과 계열사 구조 개편 계획.",
        "entities": [
            {"type": "company", "name": "두산중공업", "role": "회생 대상 기업"},
            {"type": "company", "name": "㈜두산", "role": "지주회사, 자금 투입 주체"},
            {"type": "company", "name": "두산퓨얼셀", "role": "매각 대상 계열사"},
            {"type": "company", "name": "두산솔루스", "role": "매각 대상 계열사"},
            {"type": "company", "name": "두산인프라코어", "role": "구조 개편 대상"},
            {"type": "company", "name": "두산밥캣", "role": "구조 개편 대상"},
            {"type": "person", "name": "박정원", "role": "회장, 오너 일가 대표"},
        ],
        "relations": [
            {"source": "㈜두산", "target": "두산중공업", "type": "parent_subsidiary", "detail": "모자회사 관계로 유동성 투입 예정"},
            {"source": "박정원", "target": "두산퓨얼셀", "type": "ownership", "detail": "61.27% 보유(우선주 포함), 매각으로 약 1조원 유동성 창출"},
        ],
        "risks": [
            {"type": "financial", "description": "두산중공업 심각한 유동성 위기에서 3조원 확보 목표 달성 실현 가능성 불확실", "severity": "critical"},
            {"type": "financial", "description": "㈜두산 부채비율 2017년 80% 이하에서 2019년 122%로 급증, 단기차입금 비중 62%", "severity": "critical"},
            {"type": "governance", "description": "오너 일가 주식 대부분 담보로 잡혀 자산 매각 시 빚 상환 우선 가능", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (34차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}... ({result.get('error', 'Unknown error')[:50]})")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
