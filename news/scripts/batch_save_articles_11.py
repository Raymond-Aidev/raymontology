#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 11차 (초전도체 테마주 시리즈 515-502)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/515",
        "title": "다보링크, 씨씨에스 직접투자 나설까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-04-22",
        "summary": "다보링크가 씨씨에스 인수 자금 공급을 통해 초전도체 사업 진출 추진. 최대주주 테라사이언스 감사의견 거절로 경영 불안정.",
        "entities": [
            {"type": "company", "name": "다보링크", "role": "투자회사"},
            {"type": "company", "name": "씨씨에스", "role": "피인수회사"},
            {"type": "company", "name": "테라사이언스", "role": "최대주주"},
            {"type": "company", "name": "웰바이오텍", "role": "관련회사"},
            {"type": "company", "name": "아센디오", "role": "관련회사"},
            {"type": "company", "name": "엠아이스퀘어", "role": "CB 투자자"},
            {"type": "person", "name": "소병민", "role": "엠아이스퀘어 대표"},
        ],
        "relations": [
            {"source": "다보링크", "target": "씨씨에스", "type": "investment", "detail": "인수 자금 공급"},
            {"source": "테라사이언스", "target": "다보링크", "type": "ownership", "detail": "최대주주"},
        ],
        "risks": [
            {"type": "governance", "description": "최대주주 테라사이언스 감사의견 거절", "severity": "critical"},
            {"type": "governance", "description": "씨씨에스 경영권 분쟁으로 경영 불안정", "severity": "high"},
            {"type": "financial", "description": "웰바이오텍 자본잠식, 상장폐지 위기", "severity": "critical"},
            {"type": "regulatory", "description": "퀀텀포트/그린비티에스 최대주주 지위 미인정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/514",
        "title": "테라사이언스의 상식적이지 않은 교환사채 거래",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-04-18",
        "summary": "테라사이언스가 자본금 1억원 제이비제이파트너스에 148억원 교환사채 발행. 감사인 의견거절로 상장폐지 위기.",
        "entities": [
            {"type": "company", "name": "테라사이언스", "role": "교환사채 발행"},
            {"type": "company", "name": "제이비제이파트너스", "role": "교환사채 인수"},
            {"type": "company", "name": "씨디에스홀딩스", "role": "최대주주"},
            {"type": "company", "name": "다보링크", "role": "인수 대상"},
        ],
        "relations": [
            {"source": "테라사이언스", "target": "제이비제이파트너스", "type": "bond_issuance", "detail": "148억원 교환사채"},
            {"source": "씨디에스홀딩스", "target": "테라사이언스", "type": "ownership", "detail": "최대주주"},
        ],
        "risks": [
            {"type": "governance", "description": "법인인감 무단 사용, 부외부채 가능성", "severity": "critical"},
            {"type": "financial", "description": "자본금 1억원 회사가 148억원 전액 차입 투자", "severity": "critical"},
            {"type": "regulatory", "description": "감사의견 거절로 상장폐지 위기", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/513",
        "title": "현금 없는 디와이디, 삼부토건 증자대금 어떻게 마련할까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-04-15",
        "summary": "삼부토건 150억원 유상증자 계획. 자본잠식률 46%의 심각한 재무상태. 최대주주 디와이디는 현금 6억원 수준.",
        "entities": [
            {"type": "company", "name": "삼부토건", "role": "유상증자 실시"},
            {"type": "company", "name": "디와이디", "role": "최대주주"},
            {"type": "company", "name": "상상인저축은행", "role": "CB 보유자"},
            {"type": "company", "name": "상상인증권", "role": "담보대출 제공"},
        ],
        "relations": [
            {"source": "디와이디", "target": "삼부토건", "type": "ownership", "detail": "최대주주, 자산 769억원 중 567억원 삼부토건 주식"},
        ],
        "risks": [
            {"type": "financial", "description": "삼부토건 결손금 738억→1935억원 급증, 자본잠식률 46%", "severity": "critical"},
            {"type": "financial", "description": "단기차입금 1500억원 vs 현금 193억원", "severity": "critical"},
            {"type": "financial", "description": "디와이디 현금 6억원으로 150억 증자 참여 불가능", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/512",
        "title": "위험에 직면한 디와이디·웰바이오텍·삼부토건",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-04-11",
        "summary": "이일준 회장 영향력 아래 세 상장사 사업보고서 미제출. 삼부토건 1080억원 적자, 2058억원 결손금.",
        "entities": [
            {"type": "company", "name": "디와이디", "role": "코스닥 상장"},
            {"type": "company", "name": "웰바이오텍", "role": "유가증권 상장"},
            {"type": "company", "name": "삼부토건", "role": "건설사"},
            {"type": "company", "name": "대양산업개발", "role": "지주회사"},
            {"type": "company", "name": "와이즈퍼시픽홀딩스", "role": "CB 매입사"},
            {"type": "person", "name": "이일준", "role": "회장"},
        ],
        "relations": [
            {"source": "이일준", "target": "대양산업개발", "type": "ownership", "detail": "소유"},
            {"source": "대양산업개발", "target": "디와이디", "type": "ownership", "detail": "최대주주"},
            {"source": "디와이디", "target": "삼부토건", "type": "ownership", "detail": "최대주주"},
        ],
        "risks": [
            {"type": "regulatory", "description": "세 상장사 사업보고서 제출기한 미준수", "severity": "critical"},
            {"type": "regulatory", "description": "감사자료 미입수로 의견거절, 상장폐지 위험", "severity": "critical"},
            {"type": "financial", "description": "삼부토건 1080억 적자, 2058억 결손금, 자본잠식", "severity": "critical"},
            {"type": "governance", "description": "와이즈퍼시픽홀딩스 30%이상 지분 취득 후 5% 미만 유지로 공시 회피", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/511",
        "title": "주인 없는 테라사이언스, 다보링크 인수 전선 이상 무?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-04-08",
        "summary": "최대주주 사라진 테라사이언스가 다보링크 인수 진행. 인수 대금 반복 연기, 지분 대량 처분 계획.",
        "entities": [
            {"type": "company", "name": "테라사이언스", "role": "인수 주체"},
            {"type": "company", "name": "다보링크", "role": "인수 대상"},
            {"type": "company", "name": "씨디에스홀딩스", "role": "전 최대주주"},
            {"type": "person", "name": "지서현", "role": "씨디에스홀딩스 대표"},
        ],
        "relations": [
            {"source": "테라사이언스", "target": "다보링크", "type": "acquisition", "detail": "인수 진행 중"},
            {"source": "씨디에스홀딩스", "target": "테라사이언스", "type": "ownership", "detail": "전 최대주주"},
        ],
        "risks": [
            {"type": "governance", "description": "최대주주 실질 부재로 경영권 불안정", "severity": "critical"},
            {"type": "financial", "description": "인수 대금 218억원 지급 후 잔금 미이행", "severity": "high"},
            {"type": "regulatory", "description": "상장적격성 실질심사 대상, 감사보고서 미제출", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/510",
        "title": "테라사이언스 인수 주역의 화려한 과거",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-04-04",
        "summary": "테라사이언스 인수한 씨디에스홀딩스는 자산 3억원의 초미니 회사. 황봉하, 지서현의 의심스러운 M&A 패턴.",
        "entities": [
            {"type": "company", "name": "씨디에스홀딩스", "role": "인수자"},
            {"type": "company", "name": "테라사이언스", "role": "피인수회사"},
            {"type": "company", "name": "이화그룹", "role": "배경 세력"},
            {"type": "company", "name": "유니맥스글로벌", "role": "유사 패턴 회사"},
            {"type": "person", "name": "황봉하", "role": "대표이사"},
            {"type": "person", "name": "지서현", "role": "최대주주"},
        ],
        "relations": [
            {"source": "지서현", "target": "씨디에스홀딩스", "type": "ownership", "detail": "최대주주"},
            {"source": "씨디에스홀딩스", "target": "테라사이언스", "type": "acquisition", "detail": "무자본 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "자산 3억원 회사의 195억원 차입 무자본 인수", "severity": "critical"},
            {"type": "governance", "description": "대표이사, 최대주주 빈번한 변경으로 실소유권 불명확", "severity": "high"},
            {"type": "legal", "description": "이화그룹 관련 인물들 배임/횡령 혐의", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/509",
        "title": "처분명령 받은 최대주주 지분, 씨씨에스 경영권 향방은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-04-01",
        "summary": "과기정통부가 그린비티에스/퀀텀포트에 씨씨에스 주식 처분 명령. 의결권 제한으로 경영권 기반 약화.",
        "entities": [
            {"type": "company", "name": "씨씨에스", "role": "주요 기업"},
            {"type": "company", "name": "그린비티에스", "role": "최대주주 후보"},
            {"type": "company", "name": "퀀텀포트", "role": "최대주주 후보"},
            {"type": "company", "name": "아센디오", "role": "지분 인수 예정"},
            {"type": "company", "name": "다보링크", "role": "지분 인수 예정"},
            {"type": "person", "name": "정평영", "role": "관련인물"},
            {"type": "person", "name": "권영완", "role": "관련인물"},
            {"type": "person", "name": "김영우", "role": "현 이사"},
        ],
        "relations": [
            {"source": "그린비티에스", "target": "씨씨에스", "type": "ownership", "detail": "7.05% 보유"},
            {"source": "퀀텀포트", "target": "씨씨에스", "type": "ownership", "detail": "6.96% 보유"},
        ],
        "risks": [
            {"type": "regulatory", "description": "과기정통부 6월 21일까지 주식 처분 명령", "severity": "critical"},
            {"type": "governance", "description": "의결권 제한으로 경영권 기반 약화", "severity": "high"},
            {"type": "financial", "description": "아센디오, 다보링크 2년 연속 적자, 결손법인", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/508",
        "title": "테라사이언스 반대매매, 못 막았나 안 막았나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-03-28",
        "summary": "테라사이언스 최대주주 씨디에스홀딩스가 인수 1년 미만에 반대매매로 지위 상실. 의도적 지배권 이전 의혹.",
        "entities": [
            {"type": "company", "name": "테라사이언스", "role": "주요 기업"},
            {"type": "company", "name": "씨디에스홀딩스", "role": "전 최대주주"},
            {"type": "company", "name": "다보링크", "role": "인수 대상"},
            {"type": "company", "name": "그린비티에스", "role": "씨씨에스 인수"},
            {"type": "company", "name": "엠아이스퀘어", "role": "CB 인수"},
            {"type": "person", "name": "지서현", "role": "씨디에스홀딩스 지분 61.5%"},
        ],
        "relations": [
            {"source": "씨디에스홀딩스", "target": "테라사이언스", "type": "ownership", "detail": "전 최대주주, 반대매매로 상실"},
            {"source": "테라사이언스", "target": "다보링크", "type": "acquisition", "detail": "219억원, 24.64% 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "추가 담보 제공 가능에도 반대매매 진행, 의도적 지배권 이전 의혹", "severity": "high"},
            {"type": "financial", "description": "400억원 인수대금 중 195억원 담보대출 차입", "severity": "high"},
            {"type": "regulatory", "description": "상장적격성심사 대상 지정, 주식매매 정지", "severity": "high"},
            {"type": "governance", "description": "자산 5억원 엠아이스퀘어가 150억원 CB 인수, 자금 출처 의문", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/507",
        "title": "씨씨에스, 새로운 전환사채 공장 예고?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-03-25",
        "summary": "씨씨에스 이사회가 김영우 등 4명 이사 해임안 상정. 전환사채 발행한도 1500억→9000억원 확대 계획.",
        "entities": [
            {"type": "company", "name": "씨씨에스", "role": "주요 기업"},
            {"type": "company", "name": "그린비티에스", "role": "최대주주 후보"},
            {"type": "company", "name": "W컨트롤조합", "role": "CB 인수자"},
            {"type": "person", "name": "정평영", "role": "대표이사"},
            {"type": "person", "name": "김영우", "role": "해임 대상 이사"},
        ],
        "relations": [
            {"source": "W컨트롤조합", "target": "씨씨에스", "type": "bond_purchase", "detail": "200억원 CB 인수 예정"},
        ],
        "risks": [
            {"type": "governance", "description": "이사회 참석 방해를 위한 소집통지 기간 단축", "severity": "critical"},
            {"type": "legal", "description": "신주발행 정지 가처분, 정부 최대주주 승인 미결", "severity": "critical"},
            {"type": "financial", "description": "CB 발행한도 9000억원 vs 자본금 278억원 (30배 레버리지)", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/506",
        "title": "씨씨에스 경영권 분쟁, 최후의 승자는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-03-21",
        "summary": "씨씨에스 경영권 분쟁. 정평영 대표가 김영우 대표 해임 추진, 김영우측 가처분 대응. 정부 승인 여부가 관건.",
        "entities": [
            {"type": "company", "name": "씨씨에스", "role": "케이블 방송사"},
            {"type": "company", "name": "그린비티에스", "role": "최대주주"},
            {"type": "company", "name": "퀀텀포트", "role": "공동 최대주주"},
            {"type": "company", "name": "컨텐츠하우스210", "role": "전 최대주주"},
            {"type": "company", "name": "W컨트롤조합", "role": "CB 인수 예정"},
            {"type": "person", "name": "정평영", "role": "현 대표이사"},
            {"type": "person", "name": "김영우", "role": "전 대표이사"},
            {"type": "person", "name": "권영완", "role": "사내이사"},
            {"type": "person", "name": "김지훈", "role": "사내이사"},
        ],
        "relations": [
            {"source": "그린비티에스", "target": "씨씨에스", "type": "ownership", "detail": "80.5억원 유증 참여"},
        ],
        "risks": [
            {"type": "regulatory", "description": "최대주주 변경 승인 미획득, 방송법 기한 미충족", "severity": "critical"},
            {"type": "governance", "description": "이사회 5명 vs 4명 분열, 의결권 제한 가능", "severity": "critical"},
            {"type": "legal", "description": "이사회 효력정지, 직무집행정지, 신주상장 금지 가처분 다건", "severity": "high"},
            {"type": "financial", "description": "무자본 M&A, 담보유지비율 190%", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/505",
        "title": "씨씨에스 배후 웰바이오텍의 새 주인",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-03-18",
        "summary": "온세텔링크(더엘텔링크)가 웰바이오텍 최대주주 등극. 자본금 3억원 회사가 80억원 자기자금 공시는 불가능한 주장.",
        "entities": [
            {"type": "company", "name": "웰바이오텍", "role": "주요 기업"},
            {"type": "company", "name": "더엘텔링크", "role": "신규 최대주주"},
            {"type": "company", "name": "모자이크랩스", "role": "공시업무 대행"},
            {"type": "company", "name": "헬레나투자조합", "role": "관련 투자조합"},
            {"type": "person", "name": "심동민", "role": "전 대표이사"},
            {"type": "person", "name": "이선영", "role": "최대주주 40%"},
            {"type": "person", "name": "구세현", "role": "웰바이오텍 대표"},
        ],
        "relations": [
            {"source": "더엘텔링크", "target": "웰바이오텍", "type": "ownership", "detail": "유상증자 참여 최대주주"},
        ],
        "risks": [
            {"type": "governance", "description": "자본금 3억원 회사가 80억원 자기자금 공시 (불가능)", "severity": "critical"},
            {"type": "governance", "description": "경영진 1개월 미만 재직 후 연쇄 해임", "severity": "critical"},
            {"type": "governance", "description": "실질 주인 불명확, 명의인 구조 의심", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/504",
        "title": "씨씨에스와 아센디오 뒤에 숨은 M&A 세력",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-03-14",
        "summary": "웰바이오텍이 티디엠투자조합2호 통해 아센디오 최대주주. 씨씨에스 경영권 인수와 동시점 진행.",
        "entities": [
            {"type": "company", "name": "웰바이오텍", "role": "실질적 인수자"},
            {"type": "company", "name": "아센디오", "role": "피인수회사"},
            {"type": "company", "name": "티디엠투자조합2호", "role": "형식상 최대주주"},
            {"type": "company", "name": "씨씨에스", "role": "동시 인수"},
            {"type": "company", "name": "퍼시픽산업", "role": "전 최대주주"},
            {"type": "person", "name": "한승일", "role": "웰바이오텍/아센디오 대표"},
            {"type": "person", "name": "어영훈", "role": "신임 사내이사"},
            {"type": "person", "name": "이유훈", "role": "신임 사외이사"},
        ],
        "relations": [
            {"source": "웰바이오텍", "target": "티디엠투자조합2호", "type": "investment", "detail": "120억원 투자"},
            {"source": "티디엠투자조합2호", "target": "아센디오", "type": "ownership", "detail": "11.44% 최대주주"},
        ],
        "risks": [
            {"type": "governance", "description": "인수계약과 유상증자 결정 동일 날짜, 의도적 조율", "severity": "critical"},
            {"type": "financial", "description": "83억원 필요 중 실제 보유 11억원, 58.9% 자본잠식 회사 출연", "severity": "critical"},
            {"type": "governance", "description": "무자본 M&A 전력 웰바이오텍의 반복적 경영권 확보", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/503",
        "title": "씨씨에스 반대매매, 수순일까 전화위복일까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-03-11",
        "summary": "컨텐츠하우스210이 초전도체 테마주 씨씨에스 200억원 인수. LK-99 실패로 주가 급락, 담보주식 반대매매.",
        "entities": [
            {"type": "company", "name": "씨씨에스", "role": "케이블 방송사"},
            {"type": "company", "name": "컨텐츠하우스210", "role": "인수자"},
            {"type": "company", "name": "그린비티에스", "role": "신주 인수"},
            {"type": "company", "name": "퀀텀포트", "role": "신주 인수"},
            {"type": "company", "name": "WF컨트롤조합", "role": "CB 인수 예정"},
            {"type": "person", "name": "정평영", "role": "경영진"},
            {"type": "person", "name": "권영완", "role": "경영진"},
            {"type": "person", "name": "김영우", "role": "경영진"},
            {"type": "person", "name": "이현삼", "role": "전 최대주주"},
        ],
        "relations": [
            {"source": "컨텐츠하우스210", "target": "씨씨에스", "type": "acquisition", "detail": "200억원 인수"},
            {"source": "그린비티에스", "target": "씨씨에스", "type": "investment", "detail": "80.5억원 신주 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "160억원 대부업체 차입, 담보유지비율 180-190% 과도", "severity": "critical"},
            {"type": "governance", "description": "이사회 전원 교체, 기존 임원 전무", "severity": "high"},
            {"type": "market", "description": "초전도체 테마주 거품 붕괴, 담보주식 1350만주 중 1315만주 반대매매 손실", "severity": "critical"},
            {"type": "regulatory", "description": "과기정통부 최대주주 변경 승인 불허, 원상복구 명령", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/502",
        "title": "씨씨에스, 이상한 무자본 M&A",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-03-07",
        "summary": "그린비티에스/퀀텀포트가 씨씨에스 신주 80.5억원 전액 차입 인수. CB 원리금 50% 주식상환 특약.",
        "entities": [
            {"type": "company", "name": "씨씨에스", "role": "케이블 방송사"},
            {"type": "company", "name": "그린비티에스", "role": "인수자"},
            {"type": "company", "name": "퀀텀포트", "role": "공동 인수자"},
            {"type": "company", "name": "아센디오", "role": "CB 보유자"},
            {"type": "company", "name": "다보링크", "role": "CB 보유자"},
            {"type": "company", "name": "광명길", "role": "CB 보유자"},
            {"type": "person", "name": "정평영", "role": "씨씨에스 공동대표, 그린비티에스 40%"},
            {"type": "person", "name": "권영완", "role": "씨씨에스 공동대표, 그린비티에스 25%, 퀀텀포트 70%"},
            {"type": "person", "name": "김지훈", "role": "씨씨에스 사내이사"},
        ],
        "relations": [
            {"source": "그린비티에스", "target": "씨씨에스", "type": "acquisition", "detail": "14.01% 지분"},
            {"source": "퀀텀포트", "target": "씨씨에스", "type": "acquisition", "detail": "14.01% 지분"},
            {"source": "아센디오", "target": "씨씨에스", "type": "bond_purchase", "detail": "45억원 CB"},
        ],
        "risks": [
            {"type": "governance", "description": "인수 회사 이사들이 자기 인수 결정 (자기거래)", "severity": "critical"},
            {"type": "financial", "description": "100% 차입 M&A, 인수자 자본금 8억원 vs 80.5억원 인수대금", "severity": "high"},
            {"type": "financial", "description": "CB 50% 주식상환 특약으로 기존주주 희석", "severity": "high"},
            {"type": "governance", "description": "CB 보유자 아센디오가 3년 내 최대주주 가능", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (11차 - 초전도체 테마주) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}...")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
