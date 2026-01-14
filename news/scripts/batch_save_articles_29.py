#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 29차 (셀트리온/에코프로/KH그룹/크래프톤/현대차그룹/코스닥 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/249",
        "title": "셀트리온과 셀트리온헬스케어, 배당정책에 변화 올까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-08-12",
        "summary": "셀트리온그룹 지주사 통합으로 인한 지배구조 변화를 분석. 순수 지주회사의 약점인 유동성 악화 문제 지적.",
        "entities": [
            {"type": "company", "name": "셀트리온홀딩스", "role": "지주회사"},
            {"type": "company", "name": "셀트리온헬스케어홀딩스", "role": "지주회사"},
            {"type": "company", "name": "셀트리온", "role": "제약 자회사"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "유통 자회사"},
            {"type": "company", "name": "셀트리온스킨큐어", "role": "화장품 자회사"},
            {"type": "person", "name": "서정진", "role": "회장"},
        ],
        "relations": [
            {"source": "셀트리온홀딩스", "target": "셀트리온", "type": "ownership", "detail": "지주회사가 자회사 지분 소유"},
            {"source": "서정진", "target": "셀트리온홀딩스", "type": "control", "detail": "실질적 개인회사"},
        ],
        "risks": [
            {"type": "financial", "description": "셀트리온홀딩스 부채비율 218.68%로 지주회사 행위제한 기준(200%) 초과", "severity": "high"},
            {"type": "financial", "description": "차입금 2016년말 2,951억원→2021년 5,817억원으로 2배 증가", "severity": "high"},
            {"type": "operational", "description": "순수 지주회사로서 자체 수입원 부재, 항상적 현금 유출 구조", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/248",
        "title": "셀트리온 3형제 합병의 진정한 조건은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-08-09",
        "summary": "셀트리온홀딩스와 셀트리온헬스케어홀딩스 지주사 합병 분석. 셀트리온 3형제 합병의 진정한 조건 제시.",
        "entities": [
            {"type": "company", "name": "셀트리온홀딩스", "role": "지주사"},
            {"type": "company", "name": "셀트리온헬스케어홀딩스", "role": "지주사"},
            {"type": "company", "name": "셀트리온", "role": "바이오시밀러 생산"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "바이오시밀러 판매"},
            {"type": "company", "name": "셀트리온제약", "role": "계열사"},
            {"type": "person", "name": "서정진", "role": "회장"},
        ],
        "relations": [
            {"source": "셀트리온홀딩스", "target": "셀트리온헬스케어홀딩스", "type": "merger", "detail": "세법개정 전 우대세제 적용을 위해 합병"},
            {"source": "셀트리온", "target": "셀트리온헬스케어", "type": "supply", "detail": "매출 대부분이 셀트리온헬스케어에 대한 것"},
        ],
        "risks": [
            {"type": "financial", "description": "매출채권 급증과 재고자산 증가로 실적 부풀리기 의심", "severity": "high"},
            {"type": "governance", "description": "소액주주 비율 64.29%, 55.37%로 합병 반대 가능성", "severity": "high"},
            {"type": "market", "description": "합병 후 시가총액 감소 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/247",
        "title": "지주사 합병, 셀트리온 3형제 합병의 약속일까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-08-05",
        "summary": "셀트리온 그룹이 지주회사 2곳과 셀트리온스킨큐어 합병 결정. 셀트리온 3형제 합병을 위한 첫 단계.",
        "entities": [
            {"type": "company", "name": "셀트리온", "role": "의약품 생산 기업"},
            {"type": "company", "name": "셀트리온헬스케어", "role": "의약품 판매 기업"},
            {"type": "company", "name": "셀트리온제약", "role": "3형제 합병 대상"},
            {"type": "company", "name": "셀트리온홀딩스", "role": "지주회사"},
            {"type": "company", "name": "셀트리온헬스케어홀딩스", "role": "지주회사"},
            {"type": "company", "name": "셀트리온스킨큐어", "role": "화장품 사업 회사"},
            {"type": "person", "name": "서정진", "role": "회장, 최대주주"},
        ],
        "relations": [
            {"source": "서정진", "target": "셀트리온홀딩스", "type": "control", "detail": "압도적 지분 보유"},
            {"source": "셀트리온홀딩스", "target": "셀트리온헬스케어홀딩스", "type": "merger", "detail": "합병비율 1:0.5159638"},
        ],
        "risks": [
            {"type": "financial", "description": "합병 후 시가총액이 합병 전 개별 기업가치 합에 미치지 못할 수 있음", "severity": "high"},
            {"type": "governance", "description": "생산과 판매 기능의 인위적 분리를 통한 실적 관리 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/246",
        "title": "에코프로의 인적분할, 이동채 회장의 꽃놀이패",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-08-02",
        "summary": "에코프로가 투자부문(83%)과 환경부문(17%)으로 분할. 이동채 회장은 지분교환으로 지주회사 지분 13.11%→25.51% 확대.",
        "entities": [
            {"type": "company", "name": "에코프로", "role": "분할 전 모회사(투자부문 존속법인)"},
            {"type": "company", "name": "에코프로에이치엔", "role": "환경부문 신설회사"},
            {"type": "company", "name": "에코프로비엠", "role": "전지재료사업 계열사"},
            {"type": "company", "name": "에코프로지이엠", "role": "전지재료사업 계열사"},
            {"type": "person", "name": "이동채", "role": "최대주주 회장"},
        ],
        "relations": [
            {"source": "이동채", "target": "에코프로", "type": "share_swap", "detail": "에코프로에이치엔 지분 13.11% 교환으로 지분율 25.51%로 상향"},
        ],
        "risks": [
            {"type": "governance", "description": "이동채 회장이 돈 한 푼 들이지 않고 지주회사 지분 확대", "severity": "high"},
            {"type": "market", "description": "에코프로에이치엔 주가 급락 시 지분교환 조건 악화 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/245",
        "title": "에코프로의 인적분할, 분할비율 17%의 비밀",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-07-29",
        "summary": "에코프로가 환경사업부를 분할해 에코프로에이치엔을 설립. 순자산 장부가액 기준 17%만 배분했으나 시장가치는 거의 동등.",
        "entities": [
            {"type": "company", "name": "에코프로", "role": "분할회사(투자부문 담당)"},
            {"type": "company", "name": "에코프로에이치엔", "role": "신설회사(환경사업 담당)"},
            {"type": "company", "name": "에코프로비엠", "role": "자회사(전지재료사업)"},
            {"type": "person", "name": "이동채", "role": "최대주주(13.11%)"},
        ],
        "relations": [
            {"source": "에코프로", "target": "에코프로에이치엔", "type": "spin_off", "detail": "순자산의 17% 배분"},
        ],
        "risks": [
            {"type": "governance", "description": "인적분할을 통한 최대주주 지분율 강화로 소수주주 권익 침해 우려", "severity": "high"},
            {"type": "market", "description": "장부가액과 시가의 괴리로 인한 주식가치 평가 왜곡 가능성", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/244",
        "title": "KH그룹, 알펜시아리조트 인수자금 어떻게 조달할까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-07-26",
        "summary": "KH그룹이 7,100억원 규모 알펜시아리조트 인수 추진. 5개 상장 계열사 현금성자산 881억원으로 자금 조달 어려움.",
        "entities": [
            {"type": "company", "name": "KH그룹", "role": "알펜시아리조트 인수 추진 주체"},
            {"type": "company", "name": "알펜시아리조트", "role": "인수 대상 자산"},
            {"type": "company", "name": "KH필룩스", "role": "KH그룹 계열사"},
            {"type": "company", "name": "KH E&T", "role": "KH그룹 계열사"},
            {"type": "company", "name": "KH일렉트론", "role": "KH그룹 계열사"},
            {"type": "company", "name": "장원테크", "role": "KH그룹 계열사"},
            {"type": "company", "name": "아이에이치큐", "role": "KH그룹 계열사"},
            {"type": "company", "name": "인마크 제1호 PEF", "role": "하이얏트호텔 인수 담당 펀드"},
            {"type": "company", "name": "강원도개발공사", "role": "알펜시아리조트 매각주체"},
        ],
        "relations": [
            {"source": "KH그룹", "target": "알펜시아리조트", "type": "acquisition", "detail": "7,100억원 규모 인수 입찰 추진"},
        ],
        "risks": [
            {"type": "financial", "description": "5개 계열사 현금성자산 881억원으로 7,100억원 인수자금의 12.4%에 불과", "severity": "critical"},
            {"type": "financial", "description": "5개 계열사 모두 지난해 적자 기록, 대부분 2~3년 연속 적자", "severity": "high"},
            {"type": "financial", "description": "KH E&T 미상환 전환사채 650억원, KH일렉트론 전환가능 주식 발행주식의 36.4%", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/243",
        "title": "알펜시아리조트 인수에 IHQ 나서나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-07-22",
        "summary": "KH그룹이 1조6000억원 투입된 알펜시아리조트를 7100억원에 인수. KH필룩스와 IHQ 등 전 계열사 통한 자금조달 불가피.",
        "entities": [
            {"type": "company", "name": "KH그룹", "role": "알펜시아리조트 인수 주체"},
            {"type": "company", "name": "KH강원개발", "role": "알펜시아리조트 최종 낙찰자"},
            {"type": "company", "name": "KH필룩스", "role": "인수자금 조달 주체"},
            {"type": "company", "name": "아이에이치큐", "role": "자금조달 참여 계열사"},
            {"type": "company", "name": "알펜시아리조트", "role": "인수 대상"},
            {"type": "company", "name": "강원도개발공사", "role": "매각주체"},
        ],
        "relations": [
            {"source": "KH그룹", "target": "알펜시아리조트", "type": "acquisition", "detail": "KH강원개발을 통해 7100억원에 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "7100억원 인수자금이 미조달된 상태", "severity": "critical"},
            {"type": "governance", "description": "복합적인 계열사 구조를 통한 자금조달로 투명성 저하 우려", "severity": "high"},
            {"type": "legal", "description": "두 입찰자가 모두 KH 계열이라는 공정성 관련 의혹", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/242",
        "title": "본투비 M&A, 필룩스그룹이 사는 법",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-07-19",
        "summary": "필룩스그룹이 자산 규모에 비해 과도한 규모의 M&A를 연속으로 진행. 전환사채 발행과 주식 전환을 통한 자금 조달.",
        "entities": [
            {"type": "company", "name": "필룩스그룹", "role": "주요 피인수 기업 집단"},
            {"type": "company", "name": "필룩스", "role": "그룹 중심 계열사"},
            {"type": "company", "name": "알펜시아리조트", "role": "인수 대상(7100억원)"},
            {"type": "company", "name": "하이얏트 호텔", "role": "인수 대상(5000억원)"},
            {"type": "company", "name": "아이에이치큐", "role": "인수 대상(연예기획사)"},
            {"type": "company", "name": "삼본전자", "role": "그룹 계열사"},
            {"type": "company", "name": "장원테크", "role": "그룹 계열사"},
        ],
        "relations": [
            {"source": "필룩스그룹", "target": "알펜시아리조트", "type": "acquisition", "detail": "7100억원 규모 인수, 1조원 이상 추가 투자 계획"},
        ],
        "risks": [
            {"type": "financial", "description": "현금성자산 881억원 부족, 5개 상장사 지난해 2118억원 적자", "severity": "critical"},
            {"type": "operational", "description": "영업활동 현금흐름이 마이너스 상태로 본업에서 수익 창출 실패", "severity": "critical"},
            {"type": "market", "description": "전환사채의 끝없는 발행으로 주가 추세적 하락 악순환", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/241",
        "title": "크래프톤발 M&A, 큰 시장 열리나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-07-15",
        "summary": "크래프톤의 IPO 공모가 결정 방식과 신주발행에 따른 기존주주의 가치 희석 문제 분석.",
        "entities": [
            {"type": "company", "name": "크래프톤", "role": "IPO 대상 게임사"},
            {"type": "company", "name": "엔씨소프트", "role": "비교기업"},
            {"type": "company", "name": "넷마블", "role": "비교기업"},
            {"type": "company", "name": "카카오게임즈", "role": "비교기업"},
            {"type": "company", "name": "펄어비스", "role": "비교기업"},
            {"type": "company", "name": "펍지랩스", "role": "크래프톤 인수 회사"},
        ],
        "relations": [
            {"source": "크래프톤", "target": "펍지랩스", "type": "acquisition", "detail": "2018년 이후 게임개발사 인수를 통해 성장"},
        ],
        "risks": [
            {"type": "financial", "description": "신주발행으로 인한 기존주주의 주당 가치 희석(약 7만원 손실)", "severity": "high"},
            {"type": "operational", "description": "M&A 성공 불확실성, 흥행게임 출시 보장 불가", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/240",
        "title": "크래프톤 공모가, 비교기업 바꿔 하락했나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-07-12",
        "summary": "크래프톤 공모가가 비교기업 변경으로 하향 조정. 금융감독원 지적으로 월트 디즈니 등 제외, 기업가치 35조→29조원.",
        "entities": [
            {"type": "company", "name": "크래프톤", "role": "IPO 대상사"},
            {"type": "company", "name": "엔씨소프트", "role": "비교기업"},
            {"type": "company", "name": "넷마블", "role": "비교기업"},
            {"type": "company", "name": "카카오게임즈", "role": "비교기업"},
            {"type": "company", "name": "펄어비스", "role": "비교기업"},
            {"type": "company", "name": "월트 디즈니", "role": "제외된 비교기업"},
            {"type": "company", "name": "워너 뮤직 그룹", "role": "제외된 비교기업"},
        ],
        "relations": [
            {"source": "금융감독원", "target": "크래프톤", "type": "regulation", "detail": "공모가 산정 근거 부실로 정정신고서 제출 요구"},
        ],
        "risks": [
            {"type": "governance", "description": "비교기업 선정 기준이 자의적", "severity": "high"},
            {"type": "financial", "description": "분기 집중도가 높은 순이익을 단순 연환산하여 과대평가 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/239",
        "title": "크래프톤의 적정 기업가치, 22만원? 68만원?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-07-09",
        "summary": "크래프톤 IPO 기업가치 평가 분석. 인수증권사의 67만7539원 평가는 글로벌 엔터테인먼트사를 과도하게 비교기업으로 포함.",
        "entities": [
            {"type": "company", "name": "크래프톤", "role": "IPO 대상사"},
            {"type": "company", "name": "엔씨소프트", "role": "비교기업"},
            {"type": "company", "name": "넷마블", "role": "비교기업"},
            {"type": "company", "name": "월트 디즈니", "role": "비교기업"},
            {"type": "company", "name": "워너 뮤직 그룹", "role": "비교기업"},
        ],
        "relations": [
            {"source": "크래프톤", "target": "배틀그라운드", "type": "product", "detail": "글로벌 히트작 IP로 매출의 대부분 담당"},
        ],
        "risks": [
            {"type": "operational", "description": "후속작 개발 실패: 신작 엘리온 부진, 미스트오버 흥행 실패", "severity": "high"},
            {"type": "market", "description": "중국 등 해외시장 규제 리스크: 인도에서 게임판매 중단 사례", "severity": "high"},
            {"type": "operational", "description": "단일 게임 의존도: 배틀그라운드에 대한 과도한 의존성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/238",
        "title": "국내 신화의 엔씨소프트, 글로벌 신화의 크래프톤",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-07-05",
        "summary": "크래프톤은 배틀그라운드의 글로벌 성공으로 2020년 매출 1조6704억원 기록. 엔씨소프트를 넘어섬.",
        "entities": [
            {"type": "company", "name": "크래프톤", "role": "배틀그라운드 개발사"},
            {"type": "company", "name": "엔씨소프트", "role": "리니지 개발사"},
            {"type": "company", "name": "넷마블", "role": "게임 회사"},
            {"type": "company", "name": "PUBG Entertainment", "role": "크래프톤 엔터테인먼트 자회사"},
        ],
        "relations": [
            {"source": "크래프톤", "target": "배틀그라운드", "type": "development", "detail": "2017년부터 개발하여 글로벌 성공"},
        ],
        "risks": [
            {"type": "market", "description": "배틀그라운드 의존도 과다로 IP의 수명 불확실성", "severity": "high"},
            {"type": "operational", "description": "차기작 개발 성공 가능성 미정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/237",
        "title": "크래프톤의 기업가치가 엔씨소프트보다 높다?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-07-01",
        "summary": "크래프톤 IPO 추진 시 기업가치 20~30조원 평가. 배틀그라운드 성장세를 바탕으로 높은 기업가치 책정.",
        "entities": [
            {"type": "company", "name": "크래프톤", "role": "IPO 추진 게임개발사"},
            {"type": "company", "name": "엔씨소프트", "role": "리니지 개발 게임사"},
            {"type": "company", "name": "넥슨", "role": "3N 게임사 중 하나"},
            {"type": "company", "name": "넷마블", "role": "3N 게임사 중 하나"},
            {"type": "company", "name": "미래에셋증권", "role": "크래프톤 IPO 주관사"},
            {"type": "person", "name": "김택진", "role": "엔씨소프트 최대주주"},
        ],
        "relations": [
            {"source": "크래프톤", "target": "엔씨소프트", "type": "competition", "detail": "엔씨소프트 핵심 개발자들이 설립한 회사"},
        ],
        "risks": [
            {"type": "market", "description": "현재 매출과 영업이익으로는 높은 기업가치 정당화 어려움", "severity": "high"},
            {"type": "operational", "description": "배틀그라운드에 과도하게 의존한 수익구조", "severity": "high"},
            {"type": "legal", "description": "엔씨소프트와의 영업비밀 관련 소송 이력", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/236",
        "title": "현대차그룹의 선택지 vs. 정의선 회장의 선택지",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-06-28",
        "summary": "현대차그룹 지배구조 개편 논의에서 그룹 이익과 정의선 회장 개인 이익 상충 분석.",
        "entities": [
            {"type": "company", "name": "현대차그룹", "role": "지배구조 재편 대상"},
            {"type": "company", "name": "현대차", "role": "완성차 제조"},
            {"type": "company", "name": "기아", "role": "완성차 제조"},
            {"type": "company", "name": "현대모비스", "role": "부품/서비스 회사"},
            {"type": "company", "name": "현대글로비스", "role": "물류 회사"},
            {"type": "person", "name": "정의선", "role": "회장, 지배주주"},
            {"type": "person", "name": "정몽구", "role": "명예회장"},
        ],
        "relations": [
            {"source": "정의선", "target": "현대글로비스", "type": "ownership", "detail": "주요 지분 보유 (정몽구와 합산 29.9%)"},
            {"source": "현대모비스", "target": "현대글로비스", "type": "merger_plan", "detail": "AS부품 부문 분할 후 합병 계획"},
        ],
        "risks": [
            {"type": "governance", "description": "순환출자 구조 지속으로 지배구조 투명성 부족", "severity": "high"},
            {"type": "regulatory", "description": "사익편취 규제 기준(20% 지분율) 초과로 거래 제약", "severity": "high"},
            {"type": "governance", "description": "총수일가와 그룹 주주의 이해관계 충돌 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/235",
        "title": "분할합병 보다 분할 후 스왑이 나을 수 있다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-06-24",
        "summary": "현대모비스를 투자회사와 사업회사로 분할 후 현대글로비스 지분을 활용해 스왑하는 방식이 효율적일 수 있음.",
        "entities": [
            {"type": "company", "name": "현대모비스", "role": "분할 대상 회사"},
            {"type": "company", "name": "현대글로비스", "role": "지분 스왑 대상"},
            {"type": "company", "name": "현대차", "role": "지분 보유 회사"},
            {"type": "company", "name": "기아", "role": "지분 보유 회사"},
            {"type": "person", "name": "정몽구", "role": "명예회장"},
            {"type": "person", "name": "정의선", "role": "회장"},
        ],
        "relations": [
            {"source": "정몽구-정의선", "target": "현대글로비스", "type": "share_swap", "detail": "현물출자를 통해 기아에 양도 예정"},
        ],
        "risks": [
            {"type": "governance", "description": "분할 후 복잡한 거래 구조가 지배력 강화를 위한 꼼수로 인식될 우려", "severity": "high"},
            {"type": "regulatory", "description": "다단계 현물출자와 스왑 거래가 공정거래 심사 대상 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/234",
        "title": "현대모비스 분할로 충분, 합병은 누구를 위한 선택?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-06-21",
        "summary": "현대차그룹의 현대모비스-현대글로비스 분할합병 추진이 총수 일가의 지배력 강화를 위한 것이라는 분석.",
        "entities": [
            {"type": "company", "name": "현대모비스", "role": "분할 대상 계열사"},
            {"type": "company", "name": "현대글로비스", "role": "합병 대상 계열사"},
            {"type": "company", "name": "현대차", "role": "그룹 핵심 사업회사"},
            {"type": "company", "name": "기아차", "role": "그룹 사업회사"},
            {"type": "company", "name": "현대제철", "role": "그룹 사업회사"},
            {"type": "person", "name": "정몽구", "role": "총수(부)"},
            {"type": "person", "name": "정의선", "role": "총수(자)"},
        ],
        "relations": [
            {"source": "정몽구-정의선", "target": "현대글로비스", "type": "ownership", "detail": "34.45% 보유(정몽구재단 포함)"},
        ],
        "risks": [
            {"type": "governance", "description": "분할합병을 통한 순환출자 고리 해소와 총수 일가 지배력 강화의 정당성 부족", "severity": "critical"},
            {"type": "regulatory", "description": "현대글로비스의 일감 몰아주기 규제 회피 목적으로 보이는 거래 구조", "severity": "high"},
            {"type": "market", "description": "투자회사 분할 시 지주회사 할인(30~50%)으로 인한 기업가치 평가 하락", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/233",
        "title": "현대차그룹이 지주회사 체제를 피하는 이유는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-06-17",
        "summary": "현대차그룹이 지주회사 체제를 선택하지 않은 이유 분석. 총수 일가의 지배력 강화를 추구하기 때문이라고 주장.",
        "entities": [
            {"type": "company", "name": "현대차그룹", "role": "주요 분석 대상"},
            {"type": "company", "name": "현대모비스", "role": "부품제조 및 AS부품 사업"},
            {"type": "company", "name": "현대글로비스", "role": "물류, 유통, 해운 사업"},
            {"type": "company", "name": "현대자동차", "role": "완성차 제조"},
            {"type": "company", "name": "기아", "role": "완성차 제조"},
            {"type": "company", "name": "엘리어트", "role": "행동주의 펀드"},
        ],
        "relations": [
            {"source": "현대모비스", "target": "현대글로비스", "type": "merger_plan", "detail": "AS부품 사업 부문 이전을 통한 구조 개편"},
            {"source": "엘리어트", "target": "현대차", "type": "proposal", "detail": "현대모비스와 현대차 합병 후 물적분할을 통한 지주회사 구조 제안"},
        ],
        "risks": [
            {"type": "governance", "description": "순환출자 구조 미해소로 인한 지배구조 투명성 문제 지속", "severity": "high"},
            {"type": "regulatory", "description": "현대글로비스의 일감 몰아주기 규제 대상 지속으로 총수 일가 지분 매각 강제 가능성", "severity": "high"},
            {"type": "financial", "description": "분할합병 시 최대 1조원 이상의 양도세 부담", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/232",
        "title": "정의선 회장의 필요자금은 그리 크지 않을 수 있다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-06-14",
        "summary": "현대모비스와 현대글로비스의 분할합병을 통해 순환출자 고리를 해소하려는 현대차그룹의 구조조정 계획 분석.",
        "entities": [
            {"type": "person", "name": "정의선", "role": "현대차그룹 회장"},
            {"type": "person", "name": "정몽구", "role": "명예회장"},
            {"type": "company", "name": "현대모비스", "role": "최상위 지배회사 예정"},
            {"type": "company", "name": "현대글로비스", "role": "분할법인 흡수 예정"},
            {"type": "company", "name": "현대자동차", "role": "계열사"},
            {"type": "company", "name": "기아차", "role": "계열사"},
        ],
        "relations": [
            {"source": "현대모비스", "target": "현대자동차", "type": "control", "detail": "현대모비스가 현대자동차를 거느림"},
            {"source": "기아차, 현대제철, 현대글로비스", "target": "현대모비스", "type": "circular_ownership", "detail": "세 회사가 현대모비스 지분 23.83% 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "순환출자 구조로 인한 지배구조의 복잡성 및 소수주주 보호 문제", "severity": "high"},
            {"type": "regulatory", "description": "사익편취 규제 대상 여부 판단 및 규제당국의 구조조정 승인 불확실성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/231",
        "title": "코스닥기업, 영업으로 돈을 벌지 못한다면?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-06-10",
        "summary": "코스닥 1,242개 기업 중 60개(4.8%)가 5년 연속 영업적자. 69개사가 5년 내내 현금 순사용 상태.",
        "entities": [
            {"type": "company", "name": "대창솔루션", "role": "3년 연속 영업적자 후 흑자 전환 사례"},
            {"type": "company", "name": "차바이오텍", "role": "관리종목 해제 후 흑자전환 기업"},
            {"type": "company", "name": "픽셀플러스", "role": "적자 후 흑자전환 사례"},
            {"type": "company", "name": "나노브릭", "role": "상장폐지 위기 극복 기업"},
            {"type": "company", "name": "에이비엘바이오", "role": "5년 연속 적자·현금 순사용 바이오 기업"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "5년 연속 영업현금흐름 마이너스 기업 69개사 존재", "severity": "critical"},
            {"type": "financial", "description": "유상증자 불가능 시 자산매각이나 대출에 의존하게 되어 유동성 악화", "severity": "high"},
            {"type": "operational", "description": "신약개발 성공률 약 10% 수준으로 바이오 기업 생존성 불확실", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/230",
        "title": "코스닥 기업, 얼마나 벌어 어디에 썼나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-06-07",
        "summary": "코스닥 1,242개 기업이 지난해 영업활동으로 14조원을 벌었으나, 종속/관계기업 투자에 8조원 지출.",
        "entities": [
            {"type": "company", "name": "삼성전자", "role": "비교 대상 기업"},
        ],
        "relations": [
            {"source": "코스닥 기업", "target": "종속/관계기업", "type": "investment", "detail": "평균 65억원 중 30억원(46%) 투자"},
        ],
        "risks": [
            {"type": "financial", "description": "영업활동 현금흐름(14조원) 이상을 투자(16조원) 중이며, 적자 상태의 기업도 본업 외 투자 지속", "severity": "high"},
            {"type": "operational", "description": "성장 초기 기업들이 본업과 무관한 영역에 과도한 투자로 한눈팔기", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (29차) ===\n")

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
