#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 24차 (이일준/코디엠/삼부토건/휴림로봇/더에이치큐 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/349",
        "title": "시행업자 이일준 회장은 어떻게 기업인수 투자자로 변신했나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-08-25",
        "summary": "이일준 회장은 2009년 금융위기 이후 위시티 사업 부도로 약 800억원을 상환하며 어려움을 겪었으나, 곧바로 기업 인수합병에 뛰어들어 재기. 웰바이오텍 주식 거래와 폴루스바이오팜 지분 처분으로 자금을 조성.",
        "entities": [
            {"type": "person", "name": "이일준", "role": "회장, 기업인수 투자자"},
            {"type": "company", "name": "씨엔아이", "role": "이일준 투자회사"},
            {"type": "company", "name": "대양디엔아이", "role": "이일준 투자회사"},
            {"type": "company", "name": "웰바이오텍", "role": "인수 대상 기업"},
            {"type": "company", "name": "더우주", "role": "웰바이오텍 경영권 인수 회사"},
            {"type": "company", "name": "폴루스바이오팜", "role": "지분 거래 대상"},
            {"type": "person", "name": "박일홍", "role": "라움자산관리 대표이사"},
        ],
        "relations": [
            {"source": "이일준", "target": "씨엔아이", "type": "ownership", "detail": "100% 지분 소유"},
            {"source": "이일준", "target": "웰바이오텍", "type": "investment", "detail": "2018년부터 약 160억원 투자"},
        ],
        "risks": [
            {"type": "financial", "description": "씨엔아이와 대양디엔아이의 인수자금이 대부분 외부 차입금으로 조성, 높은 레버리지", "severity": "high"},
            {"type": "governance", "description": "더우주의 실질적 경영진이 불명확하고 사원 2명뿐인 실체 불분명한 기업 구조", "severity": "high"},
            {"type": "market", "description": "대양디엔아이의 자산총액(67억원) 대비 투자 규모(100억원)의 불균형", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/348",
        "title": "적자투성이 고양CC, 어떻게 흑자 골프장이 됐나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-08-22",
        "summary": "고양CC는 2012년 누적 적자 116억원에서 2021년 영업이익 59억원으로 전환. 오종택 회장의 220억원 자산 증여와 운영 효율화로 회생.",
        "entities": [
            {"type": "person", "name": "오종택", "role": "대주주, 인셀렉트그룹 창업자"},
            {"type": "person", "name": "김기자", "role": "공동주주, 오종택 배우자"},
            {"type": "person", "name": "이일준", "role": "前 대표이사 (2010-2011)"},
            {"type": "company", "name": "고양CC", "role": "9홀 대중골프장"},
            {"type": "company", "name": "인셀렉이티", "role": "코스닥 상장 폐기물 회사"},
            {"type": "company", "name": "우리은행", "role": "주채권은행"},
        ],
        "relations": [
            {"source": "오종택", "target": "고양CC", "type": "support", "detail": "2016년 220억원 자산 증여"},
            {"source": "이일준", "target": "고양CC", "type": "management", "detail": "2010-2011년 대표이사 역임"},
        ],
        "risks": [
            {"type": "financial", "description": "2012년 자본잠식 106억원, 2013년 우리은행 부실기업 지정 이력", "severity": "critical"},
            {"type": "financial", "description": "우리은행 장기부채 308억원 여전히 존재", "severity": "high"},
            {"type": "market", "description": "코로나 기간 골프장 수요 급증, 팬데믹 이후 지속 여부 불확실", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/347",
        "title": "웰바이오텍, 녹원씨엔아이, 디와이디의 닮은 점",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-08-18",
        "summary": "대양산업개발의 이일준 회장이 인수한 웰바이오텍, 녹원씨엔아이, 디와이디 등 3개 상장사의 공통점. 경영권 교체, 상호 변경, 상장폐지 위기 등.",
        "entities": [
            {"type": "person", "name": "이일준", "role": "대양산업개발 회장"},
            {"type": "company", "name": "웰바이오텍", "role": "상장사 (구 영창실업)"},
            {"type": "company", "name": "녹원씨엔아이", "role": "상장사 (구 캐드랜드)"},
            {"type": "company", "name": "디와이디", "role": "상장사 (구 자안코스메틱)"},
            {"type": "company", "name": "삼부토건", "role": "인수 대상 회사"},
        ],
        "relations": [
            {"source": "이일준", "target": "웰바이오텍", "type": "ownership", "detail": "2019년 경영권 장악"},
            {"source": "이일준", "target": "녹원씨엔아이", "type": "ownership", "detail": "웰바이오텍을 통해 지분 취득"},
            {"source": "디와이디", "target": "삼부토건", "type": "acquisition", "detail": "인수 진행 중"},
        ],
        "risks": [
            {"type": "financial", "description": "웰바이오텍의 누적결손 1,675억원, 자본잠식 상태", "severity": "critical"},
            {"type": "regulatory", "description": "녹원씨엔아이 기업심사위원회로부터 상장폐지 결정", "severity": "critical"},
            {"type": "governance", "description": "최대주주가 8번 바뀌었고 잦은 경영권 교체로 안정성 부족", "severity": "high"},
            {"type": "financial", "description": "디와이디 2년 연속 자기자본의 50% 초과 순손실, 50% 이상 자본잠식", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/346",
        "title": "최대주주 이일준 회장의 회사들",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-08-16",
        "summary": "이일준 회장은 대양건설과 대양산업개발을 기반으로 2018년부터 상장사 인수를 본격화. 원모사인 대양산업개발과 대양건설은 2016년 이후 영업활동이 중단된 상태.",
        "entities": [
            {"type": "person", "name": "이일준", "role": "회장"},
            {"type": "company", "name": "대양산업개발", "role": "부동산개발사"},
            {"type": "company", "name": "대양건설", "role": "건설사"},
            {"type": "company", "name": "디와이디", "role": "코스닥 상장사"},
            {"type": "company", "name": "씨엔아이", "role": "투자회사"},
            {"type": "company", "name": "더누림", "role": "부동산개발사"},
        ],
        "relations": [
            {"source": "이일준", "target": "대양산업개발", "type": "ownership", "detail": "50% 지분 소유, 24년간 회장직 유지"},
            {"source": "이일준", "target": "대양건설", "type": "ownership", "detail": "40% 지분 소유"},
            {"source": "이일준", "target": "디와이디", "type": "ownership", "detail": "2021년 경영권 지분 21.39% 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "대양산업개발 순자산 67억원 중 대손충당금 148억원, 대여금 217억원 중 150억원 충당처리", "severity": "high"},
            {"type": "governance", "description": "대양산업개발과 대양건설이 실질적 영업 없이 지주회사 역할, 순환적 자금이동", "severity": "high"},
            {"type": "market", "description": "위시티 블루밍 아파트 사업 실패로 2012-2013년 468억원 손실, 시공사 벽산건설 2014년 파산", "severity": "critical"},
            {"type": "financial", "description": "더누림 순자산 마이너스 234억원의 완전 자본잠식 상태", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/343",
        "title": "'고래' 삼부토건 삼키는 '새우' 디와이디",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-08-08",
        "summary": "소형 화장품 유통사 디와이디가 건설사 삼부토건의 경영권 지분을 700억원에 인수. 디와이디의 재무 불안정성과 자본잠식 우려.",
        "entities": [
            {"type": "company", "name": "디와이디", "role": "인수자"},
            {"type": "company", "name": "삼부토건", "role": "피인수회사"},
            {"type": "company", "name": "대양산업개발", "role": "디와이디 대주주"},
            {"type": "person", "name": "이일준", "role": "대양산업개발 회장"},
            {"type": "company", "name": "대양디엔아이", "role": "삼부토건 공동인수자"},
            {"type": "company", "name": "씨엔아이", "role": "삼부토건 공동인수자"},
            {"type": "company", "name": "웰바이오텍", "role": "대양디엔아이/씨엔아이 보유 지분"},
        ],
        "relations": [
            {"source": "디와이디", "target": "삼부토건", "type": "acquisition", "detail": "9.32% 지분(175만주) 700억원에 인수"},
            {"source": "이일준", "target": "디와이디", "type": "investment", "detail": "1월 50억원, 6월 100억원 자본 투입"},
        ],
        "risks": [
            {"type": "financial", "description": "디와이디 57.2% 자본잠식, 2021년 세전손실 397억원, 자본금 80% 감소", "severity": "critical"},
            {"type": "governance", "description": "대양디엔아이/씨엔아이 현금 부족(200억~180억원 필요), 차입 자금에 의존", "severity": "critical"},
            {"type": "operational", "description": "대양디엔아이/씨엔아이 모두 영업수익 0원의 투자기구로만 기능", "severity": "high"},
            {"type": "regulatory", "description": "디와이디 3개 회계연도 중 2개에서 자본잠식 50% 초과로 관리종목 지정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/342",
        "title": "코디엠 최대주주 6년간 7회나 바뀌었지만",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-08-04",
        "summary": "코디엠의 최대주주가 2016-2022년 7차례 변경. 표면상의 주주 변화 뒤에 조성옥 회장 등 실질 주주집단의 지배구조 연속성 의혹.",
        "entities": [
            {"type": "company", "name": "코디엠", "role": "대상 기업"},
            {"type": "person", "name": "조성옥", "role": "실질 지배주주 추정"},
            {"type": "person", "name": "문용배", "role": "대표이사, 컨소시엄 멤버"},
            {"type": "company", "name": "아이리스1호 투자조합", "role": "최대주주 (2016.09)"},
            {"type": "company", "name": "코디엠바이오컨소시엄", "role": "최대주주 (2018.03)"},
            {"type": "company", "name": "이석산업개발", "role": "현재 최대주주 (2022.05)"},
            {"type": "company", "name": "삼부토건", "role": "관련 기업"},
        ],
        "relations": [
            {"source": "아이리스1호 투자조합", "target": "코디엠", "type": "ownership_transfer", "detail": "2016년 225억원에 40% 지분 취득"},
            {"source": "이석산업개발", "target": "코디엠", "type": "ownership_transfer", "detail": "삼부토건 지분 매각 자금으로 인수"},
            {"source": "조성옥", "target": "코디엠", "type": "indirect_control", "detail": "삼부토건 등 관계사 아우르는 실질 지배"},
        ],
        "risks": [
            {"type": "governance", "description": "최대주주 6년간 7회 변경되었으나 실질적 지배구조 연속성 의심, 투명성 결여", "severity": "critical"},
            {"type": "governance", "description": "투자조합 및 관계사를 통한 간접 지배 구조로 실제 의결권 행사자 파악 어려움", "severity": "high"},
            {"type": "financial", "description": "담보주식의 반대매매로 인한 주주권 변동으로 자본구조 불안정성", "severity": "high"},
            {"type": "operational", "description": "최대주주 변경 이후 3년 연속 적자 및 매출 반감", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/341",
        "title": "대박 친 이석산업개발, 코디엠 전환사채 왜 덜 사나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-08-01",
        "summary": "이석산업개발이 코디엠의 새로운 최대주주로 등장한 배경. 삼부토건 지분 매각 자금 흐름과 조성옥과의 관계 추적.",
        "entities": [
            {"type": "company", "name": "이석산업개발", "role": "코디엠 신규 최대주주"},
            {"type": "company", "name": "코디엠", "role": "전환사채 발행사"},
            {"type": "company", "name": "삼부토건", "role": "지분 매각 대상"},
            {"type": "person", "name": "조성옥", "role": "삼부토건 전 회장, 실질 영향력자"},
            {"type": "person", "name": "박란희", "role": "조성옥 배우자, 마린원개발 최대주주"},
            {"type": "company", "name": "휴림로봇", "role": "삼부토건 투자 회수"},
            {"type": "company", "name": "디와이디", "role": "삼부토건 인수자"},
        ],
        "relations": [
            {"source": "이석산업개발", "target": "코디엠", "type": "ownership", "detail": "전환사채 25억원 매입 후 주식 전환으로 최대주주"},
            {"source": "이석산업개발", "target": "삼부토건", "type": "investment", "detail": "신주인수권부사채 260억원 보유, 매각으로 120억원 회수"},
            {"source": "조성옥", "target": "이석산업개발", "type": "control", "detail": "실질 주인으로 추정"},
        ],
        "risks": [
            {"type": "governance", "description": "이석산업개발의 실질 주인이 불명확하며 조성옥 등과의 관계가 명확히 드러나지 않음", "severity": "high"},
            {"type": "financial", "description": "이석산업개발이 저축은행 6곳에서 250억원 단기차입, 추가 50억원 차입으로 자금 조달 의존도 높음", "severity": "high"},
            {"type": "operational", "description": "이석산업개발은 매출 0원인 명목회사로, 실질 영업 기반 없이 자산 중개만 수행", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/340",
        "title": "삼부토건에서 엑시트하고 코디엠 인수?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-07-28",
        "summary": "이석산업개발이 삼부토건의 신주인수권부사채를 인수한 후 최대주주로 부상하는 과정 추적. 코디엠과 조성옥 회장의 관계망 분석.",
        "entities": [
            {"type": "company", "name": "이석산업개발", "role": "신주인수권부사채 인수자"},
            {"type": "company", "name": "코디엠", "role": "마린원개발 지배회사"},
            {"type": "person", "name": "조성옥", "role": "삼부토건 회장"},
            {"type": "person", "name": "이창용", "role": "이석산업개발 50% 출자자"},
            {"type": "person", "name": "박란희", "role": "마린원개발 최대주주, 조성옥 부인"},
            {"type": "company", "name": "삼부토건", "role": "신주인수권부사채 발행사"},
            {"type": "company", "name": "디와이디", "role": "삼부토건 신규 인수자"},
            {"type": "company", "name": "마린원개발", "role": "코디엠 자회사"},
        ],
        "relations": [
            {"source": "이석산업개발", "target": "삼부토건", "type": "acquisition", "detail": "신주인수권부사채 250억원 인수"},
            {"source": "코디엠", "target": "마린원개발", "type": "control", "detail": "전환사채 195억원 보유로 지배력 행사"},
            {"source": "박란희", "target": "마린원개발", "type": "ownership", "detail": "50% 최대주주"},
            {"source": "디와이디", "target": "삼부토건", "type": "acquisition", "detail": "보통주 750만주 300억원 인수 계약"},
        ],
        "risks": [
            {"type": "governance", "description": "조성옥과 코디엠의 끈이 계속 연결된 것으로 보이며, 명목회사들을 통한 간접 지배 구조", "severity": "high"},
            {"type": "financial", "description": "마린원개발과 킹덤포레가 완전 자본잠식 상태이며, 외부 차입으로만 사업자금 조달", "severity": "critical"},
            {"type": "financial", "description": "인수자인 디와이디, 대양디엔아이, 씨엔아이 모두 결손기업으로 현금이 10억원 남짓", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/339",
        "title": "코디엠바이오컨소시엄에서 이석산업개발로: 코디엠의 최대주주 변경",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-07-25",
        "summary": "코디엠의 최대주주가 이석산업개발로 변경된 과정. 2020년 이후 4차례 최대주주 변경, 불안정한 지배구조와 과거 실패한 투자 이력.",
        "entities": [
            {"type": "company", "name": "코디엠", "role": "코스닥 상장사"},
            {"type": "company", "name": "이석산업개발", "role": "현재 최대주주 (명목회사)"},
            {"type": "company", "name": "코디엠바이오컨소시엄", "role": "전 최대주주 (2018-2020)"},
            {"type": "person", "name": "문용배", "role": "코디엠바이오컨소시엄 대표 (50%)"},
            {"type": "person", "name": "이창용", "role": "이석산업개발 공동설립자 (50%)"},
            {"type": "company", "name": "에이치엔티일렉트로닉스", "role": "실패한 투자 자회사"},
            {"type": "company", "name": "삼부토건", "role": "코디엠 지배구조 내 관련 기업"},
        ],
        "relations": [
            {"source": "이석산업개발", "target": "코디엠", "type": "ownership", "detail": "전환사채 전환으로 5.07% → 7.10% 지분 취득"},
            {"source": "코디엠바이오컨소시엄", "target": "코디엠", "type": "former_ownership", "detail": "2020년 담보주식 반대매매로 지배력 상실"},
            {"source": "코디엠", "target": "에이치엔티일렉트로닉스", "type": "investment", "detail": "372억원 투자 후 2022년 상장폐지"},
        ],
        "risks": [
            {"type": "governance", "description": "명목회사 소유 구조: 이석산업개발은 자본금 1000만원, 2명 출자자로 최대주주 지배력 확보", "severity": "critical"},
            {"type": "financial", "description": "이석산업개발 고금리 대출(기관 7%, HB은행 17%)로 302.5억원 부채 누적", "severity": "critical"},
            {"type": "operational", "description": "에이치엔티일렉트로닉스(372억원 손실), ESA엔터테인먼트(50억원 손실) 등 실패한 인수 패턴", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/338",
        "title": "휴림로봇에서 만난 복잡한 인연들",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-07-21",
        "summary": "휴림로봇과 제이앤리더스, 코디엠, 바이오기업들 간의 복잡한 관계망 추적. 지분과 전환사채를 통한 상호 연결 구조.",
        "entities": [
            {"type": "company", "name": "휴림로봇", "role": "로봇/장비 제조사"},
            {"type": "company", "name": "제이앤리더스", "role": "휴림로봇 최상위 지배회사"},
            {"type": "company", "name": "코디엠", "role": "반도체/디스플레이 장비사"},
            {"type": "company", "name": "더에이치큐", "role": "휴림로봇 인수 대상"},
            {"type": "company", "name": "디아크", "role": "휴림로봇 인수 대상"},
            {"type": "person", "name": "우성덕", "role": "중국인 실질주주"},
            {"type": "person", "name": "최해선", "role": "가우스캐피탈 대표"},
            {"type": "person", "name": "이준민", "role": "신우 대표이사"},
        ],
        "relations": [
            {"source": "제이앤리더스", "target": "휴림로봇", "type": "ownership", "detail": "휴림홀딩스 100% 소유로 지배"},
            {"source": "코디엠", "target": "베이징링크선테크놀로지", "type": "influence", "detail": "ENK컨소시엄 99% 주주로서 HNT일렉트로닉스 지배"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 교차 지분과 불투명한 투자기구로 실질 지배권 파악 어려움", "severity": "critical"},
            {"type": "governance", "description": "2016-2018년 이사 해임, 주주 분쟁 등 경영 분쟁 이력", "severity": "high"},
            {"type": "financial", "description": "관계사간 대출 및 지분투자로 인한 가치평가 및 투명성 우려", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/337",
        "title": "휴림로봇 최상위 지배회사 제이앤리더스의 흔적",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-07-18",
        "summary": "제이앤리더스는 2014년 설립된 장부상 회사로, 2020년 휴림홀딩스를 통해 휴림로봇의 최상위 지배회사가 됨. 40억원 차입하여 투자.",
        "entities": [
            {"type": "company", "name": "제이앤리더스", "role": "최상위 지배회사"},
            {"type": "company", "name": "휴림로봇", "role": "피투자회사"},
            {"type": "person", "name": "김지영", "role": "제이앤리더스 100% 지분 보유자"},
            {"type": "company", "name": "바이오싸인", "role": "초기 투자 대상"},
            {"type": "company", "name": "신우", "role": "바이오싸인 손자회사"},
            {"type": "person", "name": "이준민", "role": "신우 대표이사"},
            {"type": "company", "name": "위드윈인베스트먼트", "role": "신우 최대주주 변경"},
        ],
        "relations": [
            {"source": "제이앤리더스", "target": "휴림로봇", "type": "investment", "detail": "휴림홀딩스 통해 2020년 유상증자 40억원 참여"},
            {"source": "제이앤리더스", "target": "바이오싸인", "type": "investment", "detail": "2014년 11월 10억원 규모 유상증자 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "제이앤리더스는 사원 1명의 장부상 회사로, 김지영이 100% 지분을 보유하나 실질 주인 불명확", "severity": "high"},
            {"type": "financial", "description": "제이앤리더스 총자산 85억원 중 부채가 72억원(84%)으로 극도로 높은 레버리지", "severity": "high"},
            {"type": "regulatory", "description": "바이오싸인(위드윈네트웍)이 매출/원가 과대계상, 신주인수권부사채 부당 분류 등 감리 지적", "severity": "critical"},
            {"type": "legal", "description": "신우는 대출원리금 연체와 감사인 의견거절로 회생절차 개시", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/336",
        "title": "제이앤리더스가 휴림로봇보다 먼저 투자했던 회사는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-07-14",
        "summary": "제이앤리더스가 휴림로봇 인수 이전에 경원산업(바이오싸인, 위드윈네트웍, 현 티에스넥스젠)에 투자한 경과 추적. 더에이치큐와 디아크 사이의 숨겨진 연결고리.",
        "entities": [
            {"type": "company", "name": "제이앤리더스", "role": "최상위 지배회사, 투자자"},
            {"type": "company", "name": "휴림로봇", "role": "인수회사"},
            {"type": "company", "name": "경원산업", "role": "투자 대상 (바이오싸인)"},
            {"type": "person", "name": "김지영", "role": "제이앤리더스 100% 출자자"},
            {"type": "person", "name": "변태웅", "role": "위드윈인베스트먼트/위드윈네트웍 대표"},
            {"type": "person", "name": "최해선", "role": "해라즈인베스터 100% 지분보유자"},
            {"type": "company", "name": "휴림홀딩스", "role": "휴림로봇 지분 보유"},
        ],
        "relations": [
            {"source": "제이앤리더스", "target": "경원산업", "type": "investment", "detail": "2014년 신주인수권부사채 20억원 인수"},
            {"source": "제이앤리더스", "target": "휴림홀딩스", "type": "ownership", "detail": "100% 지분 보유 (2020년부터)"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 지배구조와 다층적 투자조합을 통한 경영권 확보 과정에서 투명성 부재", "severity": "high"},
            {"type": "operational", "description": "관련 인물들이 다양한 회사에서 동시에 경영진으로 활동하며 이해상충 가능", "severity": "high"},
            {"type": "governance", "description": "회사 상호 변경 빈번으로 과거 이력 추적 어려움", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/335",
        "title": "위드윈과 조호걸, 더에이치큐 인수의 특급 조연",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-07-11",
        "summary": "중국 출신의 위성덕이 더에이치큐를 인수할 때 국내 투자 세력인 위드윈인베스트먼트와 조호걸이 결정적인 역할 수행. 2015년부터 밀접한 관계 유지.",
        "entities": [
            {"type": "person", "name": "위성덕", "role": "더에이치큐 실질 최대주주, 중국인 투자자"},
            {"type": "person", "name": "안성민", "role": "위드윈인베스트먼트 창업자"},
            {"type": "person", "name": "조호걸", "role": "기업사냥꾼, 경영권 거래 주역"},
            {"type": "person", "name": "최해선", "role": "가우스캐피탈 대표"},
            {"type": "company", "name": "위드윈인베스트먼트", "role": "벤처캐피탈"},
            {"type": "company", "name": "더에이치큐", "role": "인수 대상 상장사"},
            {"type": "company", "name": "세미콘라이트", "role": "마제스타 인수 컨소시엄 참여사"},
            {"type": "company", "name": "마제스타", "role": "카지노 회사"},
        ],
        "relations": [
            {"source": "위드윈인베스트먼트", "target": "더에이치큐", "type": "investment", "detail": "신주인수권부사채 100억원 인수로 위성덕의 경영권 확보 지원"},
            {"source": "안성민", "target": "조호걸", "type": "business_relationship", "detail": "2015년부터 밀접한 관계 유지, 투자 조합 및 경영진 참여"},
        ],
        "risks": [
            {"type": "governance", "description": "중국 출신 실질 주주가 국내 상장사를 지배하는 구조에서 이해관계 상충 및 투명성 부족", "severity": "high"},
            {"type": "legal", "description": "마제스타 인수 시 실제 인수대금 제공자와 표기 주체가 다른 점에서 공시 적절성 문제", "severity": "high"},
            {"type": "operational", "description": "조호걸이 여러 회사의 경영권을 사고판 이력이 있어 단기 수익 창출 목적 위험", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/334",
        "title": "휴림로봇이 인수한 더에이치큐와 디아크, 의외의 접점",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-07-07",
        "summary": "휴림로봇이 더에이치큐와 디아크 두 코스닥 상장사를 인수. 중국계 자본과 동일 투자자를 통한 깊은 연관성 발견.",
        "entities": [
            {"type": "company", "name": "휴림로봇", "role": "인수자"},
            {"type": "company", "name": "더에이치큐", "role": "이동통신용 안테나 제조사"},
            {"type": "company", "name": "디아크", "role": "자동차용 카페트 납품업체"},
            {"type": "company", "name": "위드윈투자조합 38호", "role": "디아크의 최대주주"},
            {"type": "person", "name": "우성덕", "role": "중국인 실질주주"},
            {"type": "person", "name": "최해선", "role": "가우스캐피탈 대표"},
            {"type": "company", "name": "마제스타", "role": "카지노 및 반도체 유통사"},
            {"type": "company", "name": "휴림홀딩스", "role": "휴림로봇의 최대주주"},
        ],
        "relations": [
            {"source": "휴림로봇", "target": "더에이치큐", "type": "acquisition", "detail": "250억원 투입해 경영권 인수"},
            {"source": "휴림로봇", "target": "디아크", "type": "acquisition", "detail": "100억원 규모 유상증자 참여로 경영권 확보"},
            {"source": "위드윈투자조합 38호", "target": "디아크", "type": "ownership", "detail": "2018년 유상증자로 최대주주 지위 획득"},
        ],
        "risks": [
            {"type": "governance", "description": "휴림홀딩스가 6.34% 지분만 보유하고 있으며, 실제 주인이 불분명한 상태에서 경영권 인수 진행", "severity": "critical"},
            {"type": "legal", "description": "두올산업을 통한 제이테크놀로지의 마제스타 양수도가 상장폐지 회피 목적의 우회거래로 보일 소지", "severity": "high"},
            {"type": "financial", "description": "디아크가 2020년 재무제표에 대해 감사의견 거절을 받았으며, 상장폐지 사유 발생", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/333",
        "title": "휴림로봇의 더에이치큐 인수구조는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-07-04",
        "summary": "휴림로봇이 더에이치큐의 최대주주를 중국계 자본에서 인수받으며, 구주 100억원과 유상신주 150억원에 투자. 석림관광개발 등 재무적 투자자들이 저가에 주식 취득.",
        "entities": [
            {"type": "company", "name": "휴림로봇", "role": "새로운 최대주주"},
            {"type": "company", "name": "더에이치큐", "role": "인수 대상 기업"},
            {"type": "company", "name": "SMV홀딩스", "role": "기존 최대주주 (우성덕 실질 주인)"},
            {"type": "company", "name": "WSD홀딩스", "role": "기존 최대주주 (우성덕 실질 주인)"},
            {"type": "company", "name": "석림관광개발", "role": "재무적 투자자"},
            {"type": "person", "name": "우성덕", "role": "SMV·WSD홀딩스 실질 주인"},
        ],
        "relations": [
            {"source": "휴림로봇", "target": "더에이치큐", "type": "acquisition", "detail": "구주 80만주 100억원, 유상신주 150억원으로 경영권 획득"},
            {"source": "석림관광개발", "target": "더에이치큐", "type": "investment", "detail": "664만주 취득, 주당 3,871원으로 5% 미만 지분 확보"},
        ],
        "risks": [
            {"type": "financial", "description": "더에이치큐는 최근 2년간 영업활동에서 188억원 현금 손실, 분기별 56억원 순유출", "severity": "high"},
            {"type": "governance", "description": "250억원 전환사채 전부 주식 전환 시 새로운 주인의 경영권 위협 가능성", "severity": "high"},
            {"type": "market", "description": "구주 매입가(12,500원)와 다른 투자자 매입가(3,871원)의 3배 이상 가격 차이로 공정성 의문", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/332",
        "title": "우성덕은 어떻게 마제스타와 더에이치큐를 인수했나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-06-30",
        "summary": "우성덕은 NHT컨소시엄을 통해 2016년 마제스타의 경영권을 확보한 후, 2017년 감마누(현 더에이치큐)를 인수. 분식회계 적발과 상장폐지 위기를 겪은 후 2022년 휴림로봇에 지분 양도.",
        "entities": [
            {"type": "person", "name": "우성덕", "role": "뉴화청국제여행사 대표, 실질 소유주"},
            {"type": "person", "name": "이준민", "role": "제이스테판홀딩스 실질 소유자, 마제스타 대표이사"},
            {"type": "company", "name": "마제스타", "role": "카지노업체"},
            {"type": "company", "name": "감마누", "role": "여행사 (현 더에이치큐)"},
            {"type": "company", "name": "NHT컨소시엄", "role": "마제스타 경영권 인수주체"},
            {"type": "company", "name": "휴림로봇", "role": "더에이치큐 신규 최대주주"},
            {"type": "company", "name": "뉴화청국제여행사", "role": "우성덕 소유 중국인 인바운드 여행사"},
        ],
        "relations": [
            {"source": "우성덕", "target": "마제스타", "type": "ownership", "detail": "NHT컨소시엄을 통해 110억원 규모 유상증자로 경영권 확보"},
            {"source": "우성덕", "target": "감마누", "type": "acquisition", "detail": "WSD홀딩스와 SMV를 통해 95억원 기존주 인수, 100억원 신주 취득"},
            {"source": "휴림로봇", "target": "더에이치큐", "type": "acquisition", "detail": "우성덕 보유 지분 20.10%를 357억원에 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "마제스타의 무형자산 과대계상, 매출채권 과대계상, 차입금 과소계상 등 분식회계 적발", "severity": "critical"},
            {"type": "governance", "description": "이준민이 마제스타 회사 자금으로 NHT컨소시엄 출자자에 300억원 이상 부정 신용공여", "severity": "critical"},
            {"type": "legal", "description": "서준성 전 대표이사 180억원 횡령, 이준민 200억원 업무상 배임 혐의로 검찰 고발", "severity": "critical"},
            {"type": "regulatory", "description": "감마누 2017년 외부감사인 의견거절로 상장폐지 대상 지정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/331",
        "title": "더에이치큐에 드리운 '마제스타'의 그림자",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-06-27",
        "summary": "더에이치큐와 마제스타의 복잡한 관계 추적. 우성덕, 이준민, 서준성이 다수의 페이퍼컴퍼니와 순환 부채 구조를 통해 기업 지배권 이동을 조율.",
        "entities": [
            {"type": "company", "name": "더에이치큐", "role": "조사 대상 기업"},
            {"type": "person", "name": "우성덕", "role": "실질 지배자, 중국인 사업가"},
            {"type": "company", "name": "마제스타", "role": "카지노 운영사"},
            {"type": "company", "name": "제이비어뮤즈먼트", "role": "모회사"},
            {"type": "person", "name": "이준민", "role": "복수 회사 CEO"},
            {"type": "person", "name": "서준성", "role": "현대디지탈테크 인수자"},
            {"type": "company", "name": "SMV홀딩스", "role": "우성덕 투자기구"},
            {"type": "company", "name": "제이스테판", "role": "NHT컨소시엄 멤버"},
        ],
        "relations": [
            {"source": "우성덕", "target": "더에이치큐", "type": "control", "detail": "SMV홀딩스와 WSD홀딩스를 통해 실질 지배"},
            {"source": "마제스타", "target": "제이비어뮤즈먼트", "type": "debt", "detail": "총 437억7500만원 차입, 순환 부채 구조 형성"},
            {"source": "NHT컨소시엄", "target": "서준성", "type": "payment", "detail": "과반수 주주가 된 후에도 215억원 경영권 대가 지급"},
        ],
        "risks": [
            {"type": "financial", "description": "마제스타가 모회사에서 차입 후 자회사에서 다시 차입하여 상환하는 순환 부채 구조", "severity": "critical"},
            {"type": "governance", "description": "동일인(이준민)이 채권자와 채무자 회사의 CEO를 동시에 역임, 자기 거래 가능성", "severity": "critical"},
            {"type": "legal", "description": "관계회사 간 복잡한 자금 흐름이 실제 자본 출처와 소유 구조를 은폐하기 위한 것으로 추정", "severity": "high"},
            {"type": "regulatory", "description": "MJB가 2015년 감사의견 거절로 상장폐지, 자회사 거래 관련 회계 부정 시사", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/330",
        "title": "매물로 나온 더에이치큐, 최대주주는 누구?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-06-23",
        "summary": "더에이치큐(THQ)의 경영권 지분이 매물로 나왔으며, 현재 최대주주인 SMV홀딩스(32.99%)의 매각 진행 중. 과거 상장폐지 위기를 겪었던 회사.",
        "entities": [
            {"type": "company", "name": "더에이치큐", "role": "코스닥 상장사"},
            {"type": "company", "name": "SMV홀딩스", "role": "현재 최대주주 (32.99%)"},
            {"type": "person", "name": "우성덕", "role": "SMV홀딩스 실질 소유자"},
            {"type": "person", "name": "김상기", "role": "CEO 겸 전 최대주주"},
            {"type": "company", "name": "WSD홀딩스", "role": "관련 지주회사"},
            {"type": "company", "name": "감마누", "role": "더에이치큐 전신"},
        ],
        "relations": [
            {"source": "우성덕", "target": "SMV홀딩스", "type": "ownership", "detail": "55% 지분으로 인바운드 여행 플랫폼 인수 주도"},
            {"source": "SMV홀딩스", "target": "더에이치큐", "type": "control", "detail": "32.99% 지분으로 최대주주, 2017년 7월 인수"},
            {"source": "더에이치큐", "target": "7개 여행사", "type": "acquisition", "detail": "2020년 약 320억원 투자하여 여행사 흡수 합병"},
        ],
        "risks": [
            {"type": "governance", "description": "SMV홀딩스와 핵심 경영진 이탈로 인바운드 여행 사업 리더십 공백 우려", "severity": "high"},
            {"type": "operational", "description": "여행 사업이 매출의 40%를 차지하며 경영권 이전과 함께 퇴직하는 인력에 의존", "severity": "high"},
            {"type": "market", "description": "인바운드 여행 수익이 지정학적 긴장(사드 이슈)과 국제 관광 변동에 취약", "severity": "high"},
            {"type": "regulatory", "description": "2017년 감사의견 거절 및 상장폐지 심사 이력, 새 소유주에 대한 컴플라이언스 감시 예상", "severity": "medium"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (24차) ===\n")

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
