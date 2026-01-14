#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 13차 (에이티세미콘/BYC/릭스솔루션 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/382",
        "title": "리더스기술투자 최대주주 바뀔까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-15",
        "summary": "리더스기술투자가 115억원 제3자배정 유증 예정. 어센딩플로우조합 인수로 에이티세미콘 최대주주 지위 흔들림.",
        "entities": [
            {"type": "company", "name": "리더스기술투자", "role": "여신전문금융회사"},
            {"type": "company", "name": "에이티세미콘", "role": "현재 최대주주"},
            {"type": "company", "name": "어센딩플로우조합", "role": "유증 인수자"},
            {"type": "company", "name": "더에이치테크", "role": "CB 인수"},
            {"type": "person", "name": "김형준", "role": "리더스기술투자 대표"},
            {"type": "person", "name": "김환", "role": "어센딩플로우조합 60%"},
        ],
        "relations": [
            {"source": "에이티세미콘", "target": "리더스기술투자", "type": "ownership", "detail": "25.49% 최대주주"},
        ],
        "risks": [
            {"type": "governance", "description": "최대주주 교체 임박, 경영권 변수", "severity": "high"},
            {"type": "financial", "description": "대규모 적자와 낮은 유동비율, 계속기업 존속 의문", "severity": "critical"},
            {"type": "operational", "description": "신규 투자 1년 이상 중단", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/381",
        "title": "더블유아이와 에이티세미콘의 겹치는 행보, 우연일까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-12",
        "summary": "프롬써어티에서 시작한 임광빈/김진주가 지분 상실 후 김형준/변익성이 에이티세미콘과 더블루아이 동시 장악.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "반도체 패키징"},
            {"type": "company", "name": "더블루아이", "role": "휴대폰 액세서리"},
            {"type": "company", "name": "더에이치테크", "role": "최대주주"},
            {"type": "company", "name": "리튬인사이트", "role": "신설 인수법인"},
            {"type": "person", "name": "임광빈", "role": "프롬써어티 창업자"},
            {"type": "person", "name": "김진주", "role": "전 대표"},
            {"type": "person", "name": "김형준", "role": "에이티세미콘 최대주주"},
            {"type": "person", "name": "변익성", "role": "더블루아이 관련인물"},
        ],
        "relations": [
            {"source": "김형준", "target": "에이티세미콘", "type": "acquisition", "detail": "유상증자 참여 최대주주"},
            {"source": "변익성", "target": "더블루아이", "type": "acquisition", "detail": "에이티테크놀러지 대표"},
        ],
        "risks": [
            {"type": "financial", "description": "리튬인사이트 자본금 6700만원으로 300억원 이상 신주 인수, 전액 차입 무자본 M&A", "severity": "high"},
            {"type": "governance", "description": "지분 상실 후 신설회사/담보권으로 두 회사 동시 장악", "severity": "high"},
            {"type": "market", "description": "에이티세미콘과 더블루아이 동시에 2차전지 사업 진출", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/380",
        "title": "에이티세미콘에 집결한 수상한 자금들",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-08",
        "summary": "에이티세미콘 2000억원 자금조달 과정에서 한수지 중심 투자조합들의 CB 차익거래 추적.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "반도체 회사"},
            {"type": "company", "name": "아임존", "role": "투자조합"},
            {"type": "company", "name": "스마트솔루션즈", "role": "코스닥 상장사"},
            {"type": "company", "name": "파라텍", "role": "CB 인수자"},
            {"type": "person", "name": "김형준", "role": "에이티세미콘 대표"},
            {"type": "person", "name": "한수지", "role": "아임존 대표, 차익거래자"},
            {"type": "person", "name": "정광원", "role": "파라텍 대표"},
        ],
        "relations": [
            {"source": "아임존", "target": "에이티세미콘", "type": "bond_purchase", "detail": "CB 395억원 매입"},
        ],
        "risks": [
            {"type": "governance", "description": "경영진과 투자자의 이해공동체 의심, 사전 합의 의혹", "severity": "critical"},
            {"type": "financial", "description": "2000억원 자금조달 반복 연기 및 규모 축소", "severity": "high"},
            {"type": "regulatory", "description": "관련 회사들 상장폐지 위기, 횡령/배임 혐의", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/359",
        "title": "금강공업은 왜 자회사 대신 빚더미 기업 인수했나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-09-29",
        "summary": "금강공업이 부실기업 삼미금속을 자회사 케이에스피 대신 직접 인수. 230억원 투입.",
        "entities": [
            {"type": "company", "name": "금강공업", "role": "인수자"},
            {"type": "company", "name": "삼미금속", "role": "피인수 부실기업"},
            {"type": "company", "name": "케이에스피", "role": "자회사"},
            {"type": "company", "name": "코에프씨밸류업PEF", "role": "전 최대주주"},
            {"type": "person", "name": "이범호", "role": "금강공업 대표"},
        ],
        "relations": [
            {"source": "금강공업", "target": "삼미금속", "type": "acquisition", "detail": "69.4% 직접 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "삼미금속 차입금의존도 51%, 현금 1억원 미만, 4년 연속 적자", "severity": "critical"},
            {"type": "regulatory", "description": "금융감독원이 케이에스피 증권신고서 반려, 교환비율 이의", "severity": "high"},
            {"type": "regulatory", "description": "주식교환→부분인수 방식 전환으로 외부평가 의무 회피", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/326",
        "title": "비와이씨의 내부거래, 줄고는 있는데…",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-06-07",
        "summary": "비와이씨 본업 매출 2011년 1760억→작년 1235억원 지속 감소. 오너일가 가족회사 간 우회적 내부거래 가능성.",
        "entities": [
            {"type": "company", "name": "비와이씨", "role": "내의 제조/판매"},
            {"type": "company", "name": "신한방", "role": "주요 관련사"},
            {"type": "company", "name": "트러스톤자산운용", "role": "경영 문제 제기"},
            {"type": "person", "name": "한석범", "role": "비와이씨 회장"},
        ],
        "relations": [],
        "risks": [
            {"type": "governance", "description": "오너일가 다수 봉제 회사 보유, 우회적 내부거래 가능성", "severity": "high"},
            {"type": "operational", "description": "본업 매출 지속 감소", "severity": "high"},
            {"type": "governance", "description": "상품 매출 비중 확대로 외주 의존도 심화", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/325",
        "title": "비와이씨 계열의 복잡한 부동산 임대차 거래",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-06-02",
        "summary": "비와이씨, 섬유 본업보다 부동산 임대에서 더 많은 영업이익. 자산의 70%가 투자부동산.",
        "entities": [
            {"type": "company", "name": "비와이씨", "role": "부동산 소유/임대"},
            {"type": "company", "name": "신한에디피스", "role": "오피스빌딩 소유"},
            {"type": "company", "name": "신한방", "role": "부동산 보유"},
            {"type": "company", "name": "제원기업", "role": "편의점/부동산 관리"},
            {"type": "person", "name": "한승우", "role": "신한에디피스 최대주주"},
            {"type": "person", "name": "한석범", "role": "신한방 100% 주주"},
        ],
        "relations": [
            {"source": "제원기업", "target": "비와이씨", "type": "lease", "detail": "임차보증금 50억원"},
        ],
        "risks": [
            {"type": "governance", "description": "오너일가 회사들이 비와이씨/신한에디피스 빌딩에 집중 입주", "severity": "high"},
            {"type": "financial", "description": "임차보증금 960억원 규모 부채 집중, 세부공시 부족", "severity": "high"},
            {"type": "operational", "description": "투자부동산-유형자산 간 용도변경 빈번, 회계분류 일관성 문제", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/324",
        "title": "판매담당 비비안마트도 한승우에게 승계될까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-05-30",
        "summary": "BYC 핵심 판매채널 비와이씨마트는 한석범 회장 일가 소유. 한승우 3세대 승계 가능성.",
        "entities": [
            {"type": "company", "name": "BYC", "role": "상장 모회사"},
            {"type": "company", "name": "비와이씨마트", "role": "판매채널"},
            {"type": "company", "name": "한승홀딩스", "role": "비비안마트 모회사"},
            {"type": "person", "name": "한석범", "role": "BYC 회장"},
            {"type": "person", "name": "한승우", "role": "차기 경영진"},
        ],
        "relations": [
            {"source": "BYC", "target": "비와이씨마트", "type": "business", "detail": "위수탁판매대행 거래"},
        ],
        "risks": [
            {"type": "governance", "description": "핵심 판매채널이 오너일가 회사로 독점, 투명성 저하", "severity": "high"},
            {"type": "financial", "description": "비와이씨마트 매출 52억원 중 50억원이 BYC 수수료, 모회사 의존도 96%", "severity": "high"},
            {"type": "governance", "description": "순환출자 구조로 소유권 추적 어려움", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/323",
        "title": "한승우의 신한에디피스를 키운 8할은 아버지 회사였다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-05-27",
        "summary": "한승우 상무가 신한에디피스와 한승홀딩스로 비와이씨 지분 32.6%(910억원) 직접 통제.",
        "entities": [
            {"type": "company", "name": "비와이씨", "role": "의류 제조"},
            {"type": "company", "name": "신한에디피스", "role": "한승우 최대주주"},
            {"type": "company", "name": "신한방", "role": "한석범 100% 소유"},
            {"type": "company", "name": "한승홀딩스", "role": "한승우 100% 소유"},
            {"type": "person", "name": "한석범", "role": "회장"},
            {"type": "person", "name": "한승우", "role": "상무"},
        ],
        "relations": [
            {"source": "신한방", "target": "신한에디피스", "type": "loan", "detail": "2020년 147.5억원 대여"},
        ],
        "risks": [
            {"type": "governance", "description": "부자간 지분 이동 과정에서 증여 여부 미공시", "severity": "high"},
            {"type": "financial", "description": "신한방에서 대여 후 16억원 미상환", "severity": "high"},
            {"type": "operational", "description": "상품매입 83% 비와이씨, 판매 절반 신한방 의존", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/322",
        "title": "BYC의 지분은 어떻게 3세에게 넘어갔나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-05-23",
        "summary": "BYC 최대주주 2021년 2월 남호섬유→신한에디피스 변경. 실질적으로 한석범→한승우 승계.",
        "entities": [
            {"type": "company", "name": "BYC", "role": "내의업체"},
            {"type": "company", "name": "신한에디피스", "role": "신규 최대주주"},
            {"type": "company", "name": "남호섬유", "role": "전 최대주주"},
            {"type": "company", "name": "트러스톤자산운용", "role": "행동주의펀드"},
            {"type": "person", "name": "한석범", "role": "회장"},
            {"type": "person", "name": "한승우", "role": "상무, 신규 지배주주"},
        ],
        "relations": [
            {"source": "남호섬유", "target": "신한에디피스", "type": "stock_transfer", "detail": "시간외매매로 지분 이전"},
        ],
        "risks": [
            {"type": "governance", "description": "소유와 경영 미분리, 60% 이상 일가 통제", "severity": "critical"},
            {"type": "governance", "description": "최대주주 변경 공시 실제 지분변동과 1년 이상 시차", "severity": "high"},
            {"type": "financial", "description": "시간외매매 통한 은폐적 지분 이전으로 정보비대칭", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/284",
        "title": "에이티세미콘, 유동성부족 어떻게 풀어갈까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-23",
        "summary": "에이티세미콘 심각한 유동성 위기. 누적손실 343억원, 유동부채가 유동자산 827억원 초과.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "유동성 위기"},
            {"type": "company", "name": "리더스기술투자", "role": "자회사"},
            {"type": "person", "name": "김형준", "role": "최대주주/인수자"},
        ],
        "relations": [
            {"source": "리더스기술투자", "target": "에이티세미콘", "type": "loan", "detail": "20억원 13% 이자 대출"},
        ],
        "risks": [
            {"type": "financial", "description": "누적 결손 343억원, 유동부채가 유동자산 827억원 초과", "severity": "critical"},
            {"type": "financial", "description": "9월말 현금성자산 1억원 수준 거의 소진", "severity": "critical"},
            {"type": "regulatory", "description": "외부감사인 계속기업 불확실성 경고", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/283",
        "title": "에이티세미콘, 자회사 통해 미상환 전환사채 매입한 까닭은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-22",
        "summary": "에이티세미콘 자회사 에이티에이엠씨가 만기 전 CB 장외매입 후 매각. 논란 가능성.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "CB 발행"},
            {"type": "company", "name": "에이티에이엠씨", "role": "100% 자회사"},
            {"type": "company", "name": "더에이치테크", "role": "최대주주"},
            {"type": "company", "name": "삼성코퍼레이션", "role": "CB 매입"},
            {"type": "person", "name": "김형준", "role": "실질적 최대주주"},
            {"type": "person", "name": "김진주", "role": "전 이사"},
        ],
        "relations": [
            {"source": "에이티에이엠씨", "target": "에이티세미콘", "type": "bond_purchase", "detail": "5·6회차 CB 40억원 장외매입"},
        ],
        "risks": [
            {"type": "governance", "description": "자회사가 모회사 CB 매입 후 즉시 매각, 이사회 미개최", "severity": "high"},
            {"type": "financial", "description": "에이티에이엠씨 33억원 차입으로 CB 매입 후 차익 창출", "severity": "high"},
            {"type": "governance", "description": "김진주 이사 스톡옵션 600만주 취소, 내부 갈등", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/282",
        "title": "변익성 일가의 돈으로 가능했던 더블유아이의 탈바꿈",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-16",
        "summary": "변익성이 2017년 에이티테크놀러지(현 WI) 경영권 인수 후 160억원 투입. 2021년 다시 경영난.",
        "entities": [
            {"type": "company", "name": "더블유아이", "role": "피인수회사"},
            {"type": "company", "name": "에버시버리", "role": "변익성 가족회사"},
            {"type": "company", "name": "코럴핑크", "role": "신은숙 설립"},
            {"type": "company", "name": "위드모바일", "role": "2018년 인수"},
            {"type": "person", "name": "변익성", "role": "경영권 인수자"},
            {"type": "person", "name": "신은숙", "role": "변익성 배우자"},
            {"type": "person", "name": "김형준", "role": "전 대표이사"},
        ],
        "relations": [
            {"source": "변익성", "target": "더블유아이", "type": "acquisition", "detail": "경영권 인수, 자금 투입"},
        ],
        "risks": [
            {"type": "financial", "description": "2021년 3분기 매출 전년동기 대비 66% 하락, 70억원 순손실", "severity": "critical"},
            {"type": "financial", "description": "150억원 CB 발행으로 재차 자금 조달", "severity": "high"},
            {"type": "governance", "description": "가족 회사 자산 대부분이 WI 지분, 높은 관련당사자 거래", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/281",
        "title": "김형준의 파트너 변익성, 에이티테크놀로지 주인으로",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-13",
        "summary": "에이티테크놀러지 2015년부터 경영난. 2017년 변익성이 35억원 유증 참여, 22.27% 최대주주.",
        "entities": [
            {"type": "company", "name": "에이티테크놀러지", "role": "피인수회사"},
            {"type": "company", "name": "머큐리아이피테크", "role": "인수 주체"},
            {"type": "person", "name": "김형준", "role": "이사→대표이사"},
            {"type": "person", "name": "변익성", "role": "최대주주 22.27%"},
            {"type": "person", "name": "김진주", "role": "경영 공동 행사"},
            {"type": "person", "name": "임광빈", "role": "설립자, 지분 상실"},
        ],
        "relations": [
            {"source": "변익성", "target": "에이티테크놀러지", "type": "acquisition", "detail": "35억원 유증, 22.27% 최대주주"},
        ],
        "risks": [
            {"type": "governance", "description": "빈번한 경영진 교체, 대표이사 다중 직책으로 견제 미흡", "severity": "high"},
            {"type": "financial", "description": "무상감자 80%, 누적손실, 관리종목 지정", "severity": "critical"},
            {"type": "legal", "description": "경영지배인 횡령 8억원 현금+14억원 주식 미반환", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/280",
        "title": "에이티세미콘은 어떻게 김형준씨 회사가 되었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-09",
        "summary": "에이티세미콘 최대주주 2017년 에이티테크놀로지→더에이치테크 변경. 77억원 자본 투입.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "반도체 기업"},
            {"type": "company", "name": "더에이치테크", "role": "최대주주"},
            {"type": "company", "name": "에이티테크놀로지", "role": "전 최대주주"},
            {"type": "company", "name": "에이티현대플러스", "role": "CB 발행"},
            {"type": "person", "name": "김형준", "role": "각자 대표이사"},
            {"type": "person", "name": "김진주", "role": "각자 대표이사"},
            {"type": "person", "name": "정윤호", "role": "부사장"},
        ],
        "relations": [
            {"source": "더에이치테크", "target": "에이티세미콘", "type": "ownership", "detail": "2017년~ 최대주주"},
        ],
        "risks": [
            {"type": "financial", "description": "2016년 126억원 세전 순손실, 자본잠식 31%, 관리종목", "severity": "critical"},
            {"type": "governance", "description": "설립 5일 된 에이티현대플러스와 거래", "severity": "high"},
            {"type": "legal", "description": "에이티현대플러스 CB 계약위반으로 20억원 회수 지연", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/261",
        "title": "중앙디앤엠과 상지카일룸의 얽히고 설킨 관계",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-09-30",
        "summary": "중앙디앤엠이 제3자배정 유증으로 상지카일룸 최대주주. 두 회사 주주들 CB 거래로 연결.",
        "entities": [
            {"type": "company", "name": "중앙디앤엠", "role": "건축자재 제조"},
            {"type": "company", "name": "상지카일룸", "role": "고급 빌라 건설"},
            {"type": "company", "name": "제이앤에스컴퍼니", "role": "전 최대주주"},
            {"type": "company", "name": "에이치에프네트웍스", "role": "현 최대주주"},
            {"type": "company", "name": "일리아스", "role": "CB 인수"},
            {"type": "person", "name": "김재성", "role": "제이앤에스 공동대표"},
            {"type": "person", "name": "최기보", "role": "상지카일룸 전 대표"},
        ],
        "relations": [
            {"source": "일리아스", "target": "중앙디앤엠", "type": "bond_purchase", "detail": "88억원 CB 인수"},
            {"source": "상지카일룸", "target": "일리아스", "type": "bond_purchase", "detail": "50억원 CB 취득"},
        ],
        "risks": [
            {"type": "governance", "description": "다층 구조 주주관계로 실제 경영진 파악 곤란", "severity": "high"},
            {"type": "financial", "description": "중앙디앤엠 3년 연속 영업적자, 자본금 잠식", "severity": "high"},
            {"type": "regulatory", "description": "감사인 검토의견 거절 상태에서 CB 차입", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (13차 - 에이티세미콘/BYC/릭스) ===\n")

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
