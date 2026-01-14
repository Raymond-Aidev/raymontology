#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 17차 (501-480)
OCI-한미 통합, 엔케이맥스, 태영건설, 자동차부품업체, 그로우스앤밸류 시리즈
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/501",
        "title": "OCI와 한미, 초격차 주주환원정책도 통합될까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-03-04",
        "summary": "OCI홀딩스와 한미사이언스의 주주환원정책 비교 분석. OCI홀딩스 배당기준이 당기순이익에서 잉여현금흐름으로 변경되어 불확실성 증가.",
        "entities": [
            {"type": "company", "name": "OCI홀딩스", "role": "지주회사"},
            {"type": "company", "name": "한미사이언스", "role": "피인수 기업"},
            {"type": "company", "name": "임성기재단", "role": "한미 오너계열 재단"},
            {"type": "company", "name": "가현문화재단", "role": "한미 오너계열 재단"},
        ],
        "relations": [
            {"source": "OCI홀딩스", "target": "한미사이언스", "type": "acquisition", "detail": "인수"},
        ],
        "risks": [
            {"type": "governance", "description": "배당 기준 변경으로 투자자 기대 저버림", "severity": "medium"},
            {"type": "financial", "description": "10% 수준의 유상증자로 기존 주주 지분 희석", "severity": "medium"},
            {"type": "financial", "description": "잉여현금흐름 기준 채택으로 배당 변동성 증가", "severity": "medium"},
            {"type": "financial", "description": "영업현금흐름 대비 과도한 배당 (674억원 vs 410억원)", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/500",
        "title": "부광약품을 한미사이언스에 넘긴다면",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-02-29",
        "summary": "OCI홀딩스가 한미사이언스 인수 후 부광약품 지분을 이전할 가능성 분석. 제약·바이오 시너지 기회.",
        "entities": [
            {"type": "company", "name": "OCI홀딩스", "role": "지주회사"},
            {"type": "company", "name": "한미사이언스", "role": "피인수 기업"},
            {"type": "company", "name": "부광약품", "role": "OCI그룹 자회사"},
            {"type": "person", "name": "임종윤", "role": "한미사이언스 오너"},
            {"type": "person", "name": "임종훈", "role": "한미사이언스 사장"},
        ],
        "relations": [
            {"source": "OCI홀딩스", "target": "한미사이언스", "type": "acquisition", "detail": "인수"},
            {"source": "OCI홀딩스", "target": "부광약품", "type": "ownership", "detail": "자회사"},
            {"source": "한미사이언스", "target": "부광약품", "type": "potential_acquisition", "detail": "인수 예상"},
        ],
        "risks": [
            {"type": "governance", "description": "신재생에너지에서 제약·바이오로 갑작스러운 전략 변화", "severity": "high"},
            {"type": "financial", "description": "부광약품 시너지 불명확", "severity": "high"},
            {"type": "financial", "description": "부광약품 9월까지 200억원 이상 순손실", "severity": "high"},
            {"type": "financial", "description": "부광약품 추가 지분 취득에 1000억원 이상 소요", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/499",
        "title": "급조된 통합의 명분, 선진 지배구조 구상이란?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-02-23",
        "summary": "한미그룹과 OCI그룹 통합이 상속세 절감 명분으로 추진. 라데팡스파트너스 중개로 초고속 진행.",
        "entities": [
            {"type": "company", "name": "한미그룹", "role": "통합 대상"},
            {"type": "company", "name": "OCI그룹", "role": "인수 주도"},
            {"type": "company", "name": "라데팡스파트너스", "role": "중개 사모펀드"},
            {"type": "company", "name": "한미사이언스", "role": "지주회사"},
            {"type": "person", "name": "송영숙", "role": "한미그룹 회장"},
            {"type": "person", "name": "임주현", "role": "한미그룹 사장"},
            {"type": "person", "name": "김남규", "role": "라데팡스 대표"},
            {"type": "person", "name": "이우현", "role": "OCI홀딩스 회장"},
        ],
        "relations": [
            {"source": "라데팡스파트너스", "target": "한미그룹", "type": "brokerage", "detail": "M&A 중개"},
            {"source": "한미그룹", "target": "OCI그룹", "type": "merger", "detail": "통합"},
            {"source": "송영숙", "target": "라데팡스파트너스", "type": "sale", "detail": "지분매각"},
        ],
        "risks": [
            {"type": "governance", "description": "IMM 협의 결렬 후 2개월 내 초고속 OCI통합 추진", "severity": "high"},
            {"type": "governance", "description": "파킹 거래로 보이는 주식스왑과 풋옵션 구조", "severity": "high"},
            {"type": "governance", "description": "사외이사 거수기 현실에서 선진 지배구조 실현 불확실", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/498",
        "title": "최대주주 사라진 엔케이맥스, 자금은 충분한가",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-02-19",
        "summary": "엔케이맥스는 NK세포 치료제 개발 기업이나 매출 감소와 적자로 자본잠식. 최대주주 박상우 지분 상실로 경영 위기.",
        "entities": [
            {"type": "company", "name": "엔케이맥스", "role": "NK세포치료제 개발사"},
            {"type": "company", "name": "슈캉그룹", "role": "신규 투자자"},
            {"type": "company", "name": "KB증권", "role": "증권사"},
            {"type": "person", "name": "박상우", "role": "전 최대주주, 대표"},
        ],
        "relations": [
            {"source": "박상우", "target": "엔케이맥스", "type": "loss_of_control", "detail": "지분 상실"},
            {"source": "슈캉그룹", "target": "엔케이맥스", "type": "investment", "detail": "유상증자 참여"},
        ],
        "risks": [
            {"type": "financial", "description": "자본잠식 상태, 총자본 204억원이 자본금 206억원 미만", "severity": "high"},
            {"type": "financial", "description": "미상환 전환사채 474억원, 상환압력 증가", "severity": "high"},
            {"type": "operational", "description": "주력 상품 NK365 판매량 급감, 중국 판매 계약 해지", "severity": "high"},
            {"type": "governance", "description": "최대주주 지분 상실로 경영 안정성 약화", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/497",
        "title": "엔케이맥스 최대주주 지분상실의 미스터리",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-02-15",
        "summary": "엔케이맥스 최대주주 박상우의 지분이 하루만에 사라짐. 회사 공시가 거짓으로 드러나고 사채업자 담보대출 미공시.",
        "entities": [
            {"type": "company", "name": "엔케이맥스", "role": "코스닥 상장사"},
            {"type": "company", "name": "KB증권", "role": "주식담보대출 제공"},
            {"type": "company", "name": "이베스트투자증권", "role": "주식담보대출 제공"},
            {"type": "person", "name": "박상우", "role": "전 최대주주, 대표"},
            {"type": "person", "name": "진홍자", "role": "박상우 모친"},
        ],
        "relations": [
            {"source": "박상우", "target": "엔케이맥스", "type": "loss_of_control", "detail": "지분 전량 매각"},
            {"source": "박상우", "target": "KB증권", "type": "debt", "detail": "주식담보대출"},
        ],
        "risks": [
            {"type": "regulatory", "description": "KB증권 대출 상태를 반복적으로 거짓 공시", "severity": "high"},
            {"type": "regulatory", "description": "사채업자 주식담보대출 미공시", "severity": "high"},
            {"type": "governance", "description": "지분 전량 매각으로 최대주주 지위 상실", "severity": "high"},
            {"type": "market", "description": "주가 폭락으로 일반 투자자 손실", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/496",
        "title": "현대차그룹 매출 고속 질주에 동승한 부품사는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-02-08",
        "summary": "현대차그룹 최대 외부 납품업체 한온시스템, 에이치엘만도 매출 각각 13%, 16% 성장. 에스엘, 성우하이텍 등도 강한 성장.",
        "entities": [
            {"type": "company", "name": "한온시스템", "role": "공조장치 부품사"},
            {"type": "company", "name": "에이치엘만도", "role": "제동/조향 부품사"},
            {"type": "company", "name": "에스엘", "role": "램프/전동화 부품사"},
            {"type": "company", "name": "성우하이텍", "role": "현대차 1차 협력사"},
            {"type": "company", "name": "서연이화", "role": "내외장 부품사"},
            {"type": "company", "name": "명신산업", "role": "핫스탬핑 부품사"},
            {"type": "company", "name": "대유에이텍", "role": "자동차부품 제조사"},
        ],
        "relations": [
            {"source": "한온시스템", "target": "현대자동차", "type": "supply", "detail": "납품"},
            {"source": "에이치엘만도", "target": "현대차그룹", "type": "supply", "detail": "납품"},
        ],
        "risks": [
            {"type": "operational", "description": "서연이화 매출 80% 이상 현대차그룹 의존", "severity": "high"},
            {"type": "financial", "description": "대유에이텍 계열사 위니아전자, 대유플러스 연쇄 부도", "severity": "high"},
            {"type": "market", "description": "핸즈코퍼레이션 매출 변동 심함, 감소세", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/495",
        "title": "상장 자동차부품업체 현금흐름 왜 좋아졌나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-02-05",
        "summary": "현대차/기아 실적 호조로 협력업체 영업현금흐름 전년대비 3배 개선. 2022년 악화된 매입채무 상황 개선.",
        "entities": [
            {"type": "company", "name": "현대자동차", "role": "완성차업체"},
            {"type": "company", "name": "기아", "role": "완성차업체"},
            {"type": "company", "name": "모비스", "role": "자동차부품업체"},
            {"type": "company", "name": "한온시스템", "role": "글로벌 부품업체"},
            {"type": "company", "name": "현대위아", "role": "자동차부품업체"},
        ],
        "relations": [
            {"source": "현대자동차", "target": "자동차부품업체", "type": "supply_chain", "detail": "주요 거래처"},
            {"source": "한온시스템", "target": "현대자동차", "type": "revenue_dependency", "detail": "매출 48.4% 의존"},
        ],
        "risks": [
            {"type": "operational", "description": "부품업체 현대차그룹 매출 의존도 높음", "severity": "high"},
            {"type": "market", "description": "완성차 실적에 직접 의존하는 구조", "severity": "high"},
            {"type": "financial", "description": "2022년처럼 매입채무 증가시 현금흐름 악화 가능", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/494",
        "title": "아들 형제 외 친인척도 통합 논의에서 배제되었을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-02-01",
        "summary": "임종윤·임종훈 형제가 한미사이언스 신주발행 금지 가처분 신청으로 경영권 분쟁 공식화. 제3 친인척 입장이 변곡점.",
        "entities": [
            {"type": "company", "name": "한미사이언스", "role": "지주회사"},
            {"type": "person", "name": "임종윤", "role": "한미사이언스 사장"},
            {"type": "person", "name": "임종훈", "role": "임종윤 형제"},
            {"type": "person", "name": "송영숙", "role": "회장"},
            {"type": "person", "name": "임주현", "role": "사장, 송영숙 딸"},
            {"type": "person", "name": "신동국", "role": "한양정밀 회장, 최대 지분보유자"},
            {"type": "person", "name": "이관순", "role": "임성기재단 이사장"},
        ],
        "relations": [
            {"source": "송영숙", "target": "OCI그룹", "type": "negotiation", "detail": "통합협상"},
            {"source": "임종윤", "target": "한미사이언스", "type": "dispute", "detail": "지분공시"},
        ],
        "risks": [
            {"type": "governance", "description": "모녀와 형제 간 지분 경쟁으로 경영 불안정", "severity": "high"},
            {"type": "operational", "description": "제3 친인척 입장 불명확으로 통합 지연", "severity": "medium"},
            {"type": "governance", "description": "OCI 통합 협상이 일부 오너만 참여", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/493",
        "title": "사상 초유의 그룹 통합, 대가는 가족의 해체?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-01-29",
        "summary": "OCI그룹과 한미그룹 통합 구조 분석. '평등한 통합' 주장과 실제 지배 구조 불일치. OCI홀딩스가 사실상 최대주주.",
        "entities": [
            {"type": "company", "name": "OCI그룹", "role": "인수 주도"},
            {"type": "company", "name": "한미그룹", "role": "통합 대상"},
            {"type": "company", "name": "OCI홀딩스", "role": "지주회사"},
            {"type": "company", "name": "한미사이언스", "role": "지주회사"},
            {"type": "company", "name": "에쿼티스퍼스트홀딩스", "role": "주식 인수 회사"},
            {"type": "person", "name": "송영숙", "role": "한미사이언스 회장"},
            {"type": "person", "name": "임주현", "role": "한미사이언스 사장"},
            {"type": "person", "name": "임종윤", "role": "한미사이언스 사장(상근)"},
            {"type": "person", "name": "임종훈", "role": "한미식품 사장"},
            {"type": "person", "name": "이우현", "role": "OCI홀딩스 회장"},
        ],
        "relations": [
            {"source": "OCI홀딩스", "target": "한미사이언스", "type": "acquisition", "detail": "자회사 편입"},
        ],
        "risks": [
            {"type": "financial", "description": "송영숙/임주현 1000억원 이상 주식담보대출, 2~5월 상환 예정", "severity": "high"},
            {"type": "governance", "description": "임종윤 경영권 경쟁에서 불리, 소송/주총 발목 우려", "severity": "high"},
            {"type": "governance", "description": "오너 일가 내부 분열 심화", "severity": "high"},
            {"type": "governance", "description": "신사협정 공동경영 구조 붕괴 가능성", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/492",
        "title": "한미사이언스 유상증자가 왜 두달 빨라야 할까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-01-25",
        "summary": "OCI홀딩스가 한미사이언스 주요주주 지분 인수하고 2400억원 현금 출자. 현금출자 완료일이 구주 거래보다 2개월 빠른 이유 분석.",
        "entities": [
            {"type": "company", "name": "OCI홀딩스", "role": "인수자"},
            {"type": "company", "name": "한미사이언스", "role": "피인수자"},
            {"type": "company", "name": "한미약품", "role": "한미사이언스 자회사"},
            {"type": "company", "name": "부광약품", "role": "OCI그룹 계열사"},
            {"type": "person", "name": "송영숙", "role": "한미사이언스 회장"},
            {"type": "person", "name": "임주현", "role": "한미사이언스 사장"},
        ],
        "relations": [
            {"source": "OCI홀딩스", "target": "한미사이언스", "type": "acquisition", "detail": "지분인수"},
        ],
        "risks": [
            {"type": "legal", "description": "임종윤/임종훈 신주발행금지 가처분 신청, 통합 반대 소송 가능", "severity": "high"},
            {"type": "governance", "description": "현금출자 완료가 구주거래보다 2개월 빠른 조건부 구조", "severity": "medium"},
            {"type": "financial", "description": "한미사이언스 단기차입금이 전체의 90% 이상", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/491",
        "title": "피씨엘에게 수확의 계절은 없었다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-01-22",
        "summary": "코로나 팬데믹으로 537억원 매출 기록한 피씨엘이 이후 급격한 매출 감소. 재고 적체와 회수 부진으로 현금흐름 악화.",
        "entities": [
            {"type": "company", "name": "피씨엘", "role": "체외진단기 코스닥 상장사"},
            {"type": "company", "name": "올릭스", "role": "엠큐렉스 설립사"},
            {"type": "company", "name": "엠큐렉스", "role": "mRNA 백신 개발사"},
            {"type": "company", "name": "GEM", "role": "미국 대체투자그룹"},
            {"type": "person", "name": "김소연", "role": "피씨엘 최대주주, 대표"},
            {"type": "person", "name": "이동기", "role": "올릭스 최대주주, 대표"},
        ],
        "relations": [
            {"source": "피씨엘", "target": "엠큐렉스", "type": "investment", "detail": "36.9% 지분 취득"},
            {"source": "김소연", "target": "이동기", "type": "family", "detail": "부부 관계"},
            {"source": "GEM", "target": "피씨엘", "type": "investment", "detail": "18.4% 지분 취득"},
        ],
        "risks": [
            {"type": "financial", "description": "9월말 유동성 145억원으로 1년 운영자금도 부족", "severity": "high"},
            {"type": "operational", "description": "신속진단키트 매출 489억→15억 미만 급감", "severity": "high"},
            {"type": "financial", "description": "2020년 274억원 재고자산 적체", "severity": "high"},
            {"type": "governance", "description": "최대주주 부부와 올릭스 간 특수관계거래로 금감원 제지", "severity": "medium"},
            {"type": "financial", "description": "183억원 생산설비가 차입금 담보로 잡힘", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/490",
        "title": "다시 보는 태영건설•티와이홀딩스 인적분할",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-01-18",
        "summary": "태영건설 2020년 인적분할로 지주회사 티와이홀딩스 설립. 오너 일가 최대 수혜, 우량 자회사는 티와이홀딩스로, 부실 자회사는 태영건설에.",
        "entities": [
            {"type": "company", "name": "태영건설", "role": "분할 전 지배회사"},
            {"type": "company", "name": "티와이홀딩스", "role": "신설 지주회사"},
            {"type": "company", "name": "에코비트", "role": "환경사업 회사"},
            {"type": "company", "name": "블루원", "role": "레저사업 자회사"},
            {"type": "company", "name": "태영인더스트리", "role": "창고업 자회사"},
            {"type": "company", "name": "인제스피디움", "role": "부실 자회사"},
            {"type": "company", "name": "SBS", "role": "방송사업 자회사"},
            {"type": "person", "name": "윤석민", "role": "태영그룹 회장"},
        ],
        "relations": [
            {"source": "태영건설", "target": "티와이홀딩스", "type": "spin_off", "detail": "인적분할로 우량자회사 이관"},
            {"source": "윤석민", "target": "티와이홀딩스", "type": "acquisition", "detail": "공개매수 통한 지분 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "인적분할로 자본 절반 감소, 부채는 그대로 재무구조 훼손", "severity": "high"},
            {"type": "financial", "description": "2012-2018년 영업현금 3800억 대비 자산취득 5600억 지출", "severity": "high"},
            {"type": "financial", "description": "인제스피디움 자본잠식으로 매년 추가 출자/보증 필요", "severity": "medium"},
            {"type": "governance", "description": "공개매수가 사실상 오너 일가를 위한 것으로 소수주주 이익 침해", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/489",
        "title": "오너를 살릴 것인가, 기업을 살릴 것인가",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-01-15",
        "summary": "태영건설 워크아웃 신청 과정에서 신용평가사 미흡 대응과 오너 자구안 논쟁. 채권단은 경영책임 요구, 오너는 지배구조 유지 우선.",
        "entities": [
            {"type": "company", "name": "태영건설", "role": "워크아웃 신청 회사"},
            {"type": "company", "name": "태영그룹", "role": "모회사"},
            {"type": "company", "name": "티와이홀딩스", "role": "오너 지주회사"},
            {"type": "company", "name": "SBS", "role": "그룹 계열사"},
            {"type": "company", "name": "태영인더스트리", "role": "물류터미널 회사"},
            {"type": "person", "name": "윤석민", "role": "태영그룹 회장"},
            {"type": "person", "name": "이복현", "role": "금융감독원장"},
        ],
        "relations": [
            {"source": "태영그룹", "target": "태영건설", "type": "ownership", "detail": "모자관계"},
            {"source": "윤석민", "target": "티와이홀딩스", "type": "ownership", "detail": "소유"},
        ],
        "risks": [
            {"type": "financial", "description": "PF채무 만기연장/차환 불가능 상태로 워크아웃", "severity": "high"},
            {"type": "governance", "description": "오너 일가가 회생절차에서도 티와이홀딩스/SBS 보유 의도", "severity": "high"},
            {"type": "governance", "description": "연대보증 채무 해소를 최우선으로 경영권 유지 추구", "severity": "high"},
            {"type": "regulatory", "description": "워크아웃 1개월 전 신용등급 하향 미실행", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/488",
        "title": "역대급 보유현금으로도 PF 쓰나미 막을 수 없었다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-01-11",
        "summary": "태영건설이 역사적 수준 현금 3650억원 보유에도 PF 위기로 워크아웃. 금리 인상 이자 부담과 유동화증권 매입으로 유동성 악화.",
        "entities": [
            {"type": "company", "name": "태영건설", "role": "주요 기업"},
            {"type": "company", "name": "티와이홀딩스", "role": "모회사"},
        ],
        "relations": [
            {"source": "티와이홀딩스", "target": "태영건설", "type": "loan", "detail": "13% 금리 4000억원 긴급 차입"},
        ],
        "risks": [
            {"type": "financial", "description": "본업 현금유출 330억원, 이자 부담 증가, 공사미수금 확대", "severity": "critical"},
            {"type": "financial", "description": "차입금 5300억→9000억 증가, 고금리 차입 급증", "severity": "critical"},
            {"type": "financial", "description": "10월 이후 곳곳에서 PF사고 발생, 유동화증권 매입 의무 증가", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/487",
        "title": "태영건설 워크아웃 신청 막전막후",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-01-08",
        "summary": "태영건설 워크아웃은 성수동 오피스2 PF 400억이 직접 원인 아님. 부천 오정동 등 다수 지연 사업과 PF보증채무 5.5조가 실질 위기 요인.",
        "entities": [
            {"type": "company", "name": "태영건설", "role": "시공사, 채무보증자"},
            {"type": "company", "name": "성수티에스2차피에프브이", "role": "성수동 시행사"},
            {"type": "company", "name": "에이블성수제일차", "role": "유동화회사"},
            {"type": "company", "name": "KB증권", "role": "사모사채 인수확약"},
            {"type": "company", "name": "네오시티", "role": "태영건설 자회사"},
        ],
        "relations": [
            {"source": "태영건설", "target": "성수티에스2차피에프브이", "type": "guarantee", "detail": "채무보증"},
            {"source": "태영건설", "target": "네오시티", "type": "ownership", "detail": "자회사"},
        ],
        "risks": [
            {"type": "financial", "description": "PF보증채무 5.5조 중 차입잔액 1.2조, 다수 사업 지연", "severity": "high"},
            {"type": "financial", "description": "비계열 4.5조 PF로 대우건설/호반건설 등 공동시공사 불똥", "severity": "high"},
            {"type": "financial", "description": "공모사채 1000억 기한이익 상실 선언으로 채무조정 복잡화", "severity": "high"},
            {"type": "market", "description": "금리상승과 PF시장 신용경색으로 유동화증권 재발행 실패", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/486",
        "title": "태영건설을 유동성 위기로 몰고 간 PF 유동화증권",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-01-04",
        "summary": "태영건설이 PF 유동화증권 매입으로 심각한 유동성 위기. 11월부터 29차례 5991억원 규모 유동화증권 매입.",
        "entities": [
            {"type": "company", "name": "태영건설", "role": "주요 피해 건설사"},
            {"type": "company", "name": "티와이홀딩스", "role": "최대주주"},
            {"type": "company", "name": "롯데건설", "role": "유사 위기 건설사"},
            {"type": "company", "name": "네오시티", "role": "부천 시행사"},
            {"type": "company", "name": "인제스피디움", "role": "테마파크 자회사"},
        ],
        "relations": [
            {"source": "태영건설", "target": "티와이홀딩스", "type": "loan", "detail": "연 13% 4000억원 차입"},
            {"source": "태영건설", "target": "네오시티", "type": "ownership", "detail": "69% 출자"},
            {"source": "태영건설", "target": "인제스피디움", "type": "ownership", "detail": "100% 자회사"},
        ],
        "risks": [
            {"type": "financial", "description": "5991억원 유동화증권 매입으로 현금 고갈", "severity": "critical"},
            {"type": "financial", "description": "연 13~15% 고금리 유동화증권 이자 부담", "severity": "high"},
            {"type": "operational", "description": "부천 군부대 이전사업 2028년으로 지연", "severity": "high"},
            {"type": "financial", "description": "인제스피디움 자산 142억 vs 부채 1412억 심각한 불균형", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/485",
        "title": "씨비아이 CB와 BW, 어떻게 손바뀜되었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-01-02",
        "summary": "2021년 그로우스앤밸류가 인수한 씨비아이(CBI)는 본업 61억 영업이익에도 종속기업 투자손실 300억 등으로 누적 결손. 740억 CB/BW 복잡한 거래.",
        "entities": [
            {"type": "company", "name": "씨비아이", "role": "피인수 회사"},
            {"type": "company", "name": "그로우스앤밸류디벨로프먼트", "role": "인수자"},
            {"type": "company", "name": "키네타", "role": "신약개발사 투자대상"},
            {"type": "company", "name": "엑시큐어", "role": "신약개발사 투자대상"},
            {"type": "company", "name": "SBW생명과학", "role": "투자대상"},
            {"type": "company", "name": "제이씨에셋자산운용", "role": "CB 인수자"},
            {"type": "person", "name": "오경원", "role": "CBI 실질주주/임원"},
            {"type": "person", "name": "이호준", "role": "CBI 실질주주/임원"},
            {"type": "person", "name": "성봉두", "role": "CBI 실질주주/임원"},
            {"type": "person", "name": "장육", "role": "CBI 실질주주/임원"},
        ],
        "relations": [
            {"source": "그로우스앤밸류디벨로프먼트", "target": "씨비아이", "type": "acquisition", "detail": "경영권 인수"},
            {"source": "씨비아이", "target": "키네타", "type": "investment", "detail": "투자"},
            {"source": "제이씨에셋자산운용", "target": "오경원", "type": "resale", "detail": "CB 재매각"},
        ],
        "risks": [
            {"type": "financial", "description": "2020년 100억 이익잉여금에서 누적 결손법인 전락", "severity": "high"},
            {"type": "financial", "description": "종속기업/관계기업 투자손실 약 300억원", "severity": "high"},
            {"type": "regulatory", "description": "전환청구/만기전 취득 관련 공시 누락", "severity": "medium"},
            {"type": "governance", "description": "임원들의 CB 매입 및 콜옵션 행사, 간접 인수 의혹", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/484",
        "title": "CBI 때문에••• 손해 본 DGP, 이득 본 김성태",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-12-28",
        "summary": "그로우스앤밸류의 CBI 인수에 율호가 깊게 관여. CBI가 DGP 경영권 장악 후 바이오 투자로 손실. 김성태는 SBW생명과학 투자로 시세차익.",
        "entities": [
            {"type": "company", "name": "CBI", "role": "생명공학 투자회사"},
            {"type": "company", "name": "그로우스앤밸류", "role": "투자회사"},
            {"type": "company", "name": "DGP", "role": "에너지 관련 회사"},
            {"type": "company", "name": "율호", "role": "투자회사"},
            {"type": "company", "name": "SBW생명과학", "role": "바이오 회사"},
            {"type": "company", "name": "키네타", "role": "바이오 벤처"},
            {"type": "person", "name": "이호준", "role": "그로우스앤밸류 대표/CBI 사장"},
            {"type": "person", "name": "오경원", "role": "그로우스앤밸류 부회장/CBI 대표"},
            {"type": "person", "name": "김성태", "role": "베스트마스터1호 최대출자자"},
        ],
        "relations": [
            {"source": "그로우스앤밸류", "target": "CBI", "type": "acquisition", "detail": "인수"},
            {"source": "율호", "target": "CBI", "type": "investment", "detail": "투자조합 참여"},
            {"source": "CBI", "target": "DGP", "type": "control", "detail": "경영권 장악"},
            {"source": "김성태", "target": "SBW생명과학", "type": "investment", "detail": "투자"},
        ],
        "risks": [
            {"type": "financial", "description": "DGP가 CBI 경영진 후 키네타/엑시큐어 투자 손실", "severity": "high"},
            {"type": "governance", "description": "CBI와 그로우스앤밸류 간 복잡한 CB/지분 거래 구조", "severity": "high"},
            {"type": "regulatory", "description": "베스트마스터1호 2017년 12월 이후 지분율 변동 보고 미실시", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/483",
        "title": "그로우스앤밸류는 왜 상폐 기로에 선 회사를 인수하려고 했을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-12-26",
        "summary": "그로우스앤밸류 이호준·오경원이 2021년 상장폐지된 에스제이케이 인수 시도 후 실패. 400억 차입금, 누적 1000억 적자 회사의 인수 의도 분석.",
        "entities": [
            {"type": "company", "name": "그로우스앤밸류", "role": "투자회사"},
            {"type": "company", "name": "에스제이케이", "role": "인수 대상 (상장폐지)"},
            {"type": "company", "name": "이스트아시아인베스트먼트", "role": "유상증자 예정 투자사"},
            {"type": "company", "name": "세진전자", "role": "에스제이케이와 합병"},
            {"type": "company", "name": "파로스인베스트먼트", "role": "오경원 전직 회사"},
            {"type": "person", "name": "이호준", "role": "그로우스앤밸류 대표"},
            {"type": "person", "name": "오경원", "role": "그로우스앤밸류 부회장"},
        ],
        "relations": [
            {"source": "이호준", "target": "그로우스앤밸류", "type": "management", "detail": "대표"},
            {"source": "오경원", "target": "이스트아시아인베스트먼트", "type": "ownership", "detail": "100% 지분"},
            {"source": "그로우스앤밸류", "target": "에스제이케이", "type": "attempted_acquisition", "detail": "인수 시도"},
        ],
        "risks": [
            {"type": "financial", "description": "에스제이케이 누적 적자 1000억 초과, 매출 38억 대비 100억 적자", "severity": "high"},
            {"type": "governance", "description": "2020년 파산선고로 상장폐지, 회생전 M&A 입찰자 없음", "severity": "high"},
            {"type": "governance", "description": "상근직 3명 대비 등기임원 13명, 내부 승진자 무", "severity": "medium"},
            {"type": "financial", "description": "400억원 차입금, 현금 바닥 상태", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/482",
        "title": "율호의 기구한 5년, 공현철에서 이호준까지",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-12-21",
        "summary": "코스닥 율호는 2018년 이후 5년간 최대주주 4번 변경. 공현철→태영이엔지→이호준 그로우스앤밸류로 이어진 복잡한 소유권 변동.",
        "entities": [
            {"type": "company", "name": "율호", "role": "코스닥 상장사"},
            {"type": "company", "name": "제이에스앤파트너스", "role": "경영권 인수"},
            {"type": "company", "name": "태영이엔지", "role": "경영권 인수"},
            {"type": "company", "name": "그로우스앤밸류", "role": "CB 인수"},
            {"type": "company", "name": "CBI", "role": "율호 출자 대상"},
            {"type": "person", "name": "공현철", "role": "대양금속 실소유주"},
            {"type": "person", "name": "이호준", "role": "그로우스앤밸류 대표"},
            {"type": "person", "name": "이현진", "role": "전 최대주주"},
            {"type": "person", "name": "박정희", "role": "태영이엔지 대표"},
        ],
        "relations": [
            {"source": "공현철", "target": "제이에스앤파트너스", "type": "control", "detail": "실질소유"},
            {"source": "제이에스앤파트너스", "target": "율호", "type": "acquisition", "detail": "경영권인수"},
            {"source": "태영이엔지", "target": "율호", "type": "acquisition", "detail": "경영권인수"},
            {"source": "그로우스앤밸류", "target": "율호", "type": "investment", "detail": "CB 인수"},
            {"source": "율호", "target": "CBI", "type": "investment", "detail": "출자"},
        ],
        "risks": [
            {"type": "governance", "description": "경영권 분쟁, 반복되는 최대주주 변경, 복잡한 자금흐름", "severity": "high"},
            {"type": "financial", "description": "상호변경 후 매출정체, 적자 반복, 자본잠식", "severity": "high"},
            {"type": "regulatory", "description": "외부감사 의견거절로 재무제표 신뢰도 결여", "severity": "high"},
            {"type": "operational", "description": "미지원 신사업 추진, 관련 없는 다양한 M&A 시도", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/481",
        "title": "스튜디오드래곤의 영업현금흐름, 왜 이렇게 적을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-12-15",
        "summary": "스튜디오드래곤 3분기 순이익 461억원이나 영업현금흐름은 76억원(16%). 판권 취득과 무형자산 상각 회계처리 구조가 괴리 원인.",
        "entities": [
            {"type": "company", "name": "스튜디오드래곤", "role": "드라마 제작사"},
            {"type": "company", "name": "CJ E&M", "role": "모기업"},
        ],
        "relations": [
            {"source": "CJ E&M", "target": "스튜디오드래곤", "type": "spin_off", "detail": "물적분할"},
        ],
        "risks": [
            {"type": "financial", "description": "영업현금흐름이 음수, 영업활동 지출이 수입 초과", "severity": "high"},
            {"type": "financial", "description": "판권 취득원가 1조원 중 90% 상각/손상, 장부가액 550억원", "severity": "medium"},
            {"type": "operational", "description": "판권 추가 수익 발생 규모와 기간에 대한 낮은 기대", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/480",
        "title": "그로우스앤밸류의 과거, 홈캐스트와 마제스타",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-12-18",
        "summary": "그로우스앤밸류 투자 기업 중 분식회계/횡령/주가조작 문제의 마제스타, 홈캐스트 중심 분석. 이호준, 오경원 등 복잡한 지분거래 네트워크.",
        "entities": [
            {"type": "company", "name": "그로우스앤밸류디벨로프먼트", "role": "소형주 투자사"},
            {"type": "company", "name": "마제스타", "role": "카지노 운영사 (상장폐지)"},
            {"type": "company", "name": "홈캐스트", "role": "코스닥 상장사"},
            {"type": "company", "name": "현대디지탈테크", "role": "제이비어뮤즈먼트 전신"},
            {"type": "company", "name": "제이비어뮤즈먼트", "role": "마제스타 전신"},
            {"type": "company", "name": "CBI", "role": "이호준/오경원 지배 회사"},
            {"type": "company", "name": "DGP", "role": "이호준 지배 회사"},
            {"type": "company", "name": "두올산업", "role": "마제스타 경영위임"},
            {"type": "person", "name": "이호준", "role": "그로우스앤밸류 주인"},
            {"type": "person", "name": "오경원", "role": "그로우스앤밸류 공동운영"},
            {"type": "person", "name": "서준성", "role": "마제스타 대표 (횡령/주가조작)"},
            {"type": "person", "name": "장병권", "role": "현대디지탈테크 대표"},
            {"type": "person", "name": "신재호", "role": "두올산업 실질 최대주주 (주가조작)"},
        ],
        "relations": [
            {"source": "이호준", "target": "그로우스앤밸류", "type": "management", "detail": "설립/운영"},
            {"source": "그로우스앤밸류", "target": "마제스타", "type": "investment", "detail": "75만주 약 24억원 매입"},
            {"source": "서준성", "target": "제이비어뮤즈먼트", "type": "control", "detail": "최대주주/대표"},
            {"source": "신재호", "target": "두올산업", "type": "control", "detail": "실질적 최대주주"},
        ],
        "risks": [
            {"type": "legal", "description": "서준성 마제스타 인수 과정 180억원 횡령 혐의", "severity": "critical"},
            {"type": "market", "description": "마제스타/홈캐스트 관련 주가조작, 신재호 테마주 주가조작", "severity": "critical"},
            {"type": "regulatory", "description": "마제스타/홈캐스트 분식회계 혐의", "severity": "critical"},
            {"type": "governance", "description": "이호준이 홈캐스트 사외이사 후보이면서 마제스타 지분 매수", "severity": "high"},
            {"type": "governance", "description": "무자본 M&A 대상, 분식회계/배임/횡령 기업이 투자 대상", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (17차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}... - {result.get('error', 'unknown')}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
