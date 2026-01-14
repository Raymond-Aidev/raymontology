#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 27차 (에이티세미콘/리더스기술투자/릭스솔루션 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/289",
        "title": "해성옵틱스, 최대주주 일가의 탈출기",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-01-13",
        "summary": "스마트폰 카메라 부품 제조사 해성옵틱스에서 32년간 경영해온 설립자 이을성이 2021년 7월 사임 후 2개월 만에 최대주주가 변경됐다.",
        "entities": [
            {"type": "company", "name": "해성옵틱스", "role": "스마트폰 카메라 부품 제조사"},
            {"type": "company", "name": "바이오그디바이스", "role": "이재선 인수 상장사"},
            {"type": "company", "name": "옵트론텍", "role": "조합 주요 출자자"},
            {"type": "person", "name": "이을성", "role": "해성옵틱스 설립자 및 전 최대주주"},
            {"type": "person", "name": "이재선", "role": "아들, 전 대표이사"},
            {"type": "person", "name": "임지윤", "role": "옵트론텍 최대주주"},
        ],
        "relations": [
            {"source": "이을성", "target": "해성옵틱스", "type": "설립", "detail": "1989년 창립 이후 32년간 경영"},
            {"source": "옵트론텍", "target": "해성옵틱스", "type": "투자", "detail": "조합 통해 27.96% 취득"},
        ],
        "risks": [
            {"type": "financial", "description": "2020년까지 4년 연속 적자, 카메라 모듈 매출 1500억원→349억원 급감", "severity": "critical"},
            {"type": "operational", "description": "삼성전기 매출 의존도 90% 이상", "severity": "critical"},
            {"type": "governance", "description": "2021년 한 해에 최대주주 3차례 변경", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/288",
        "title": "비케이탑스 지배하는 보이지 않는 손은 누구?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-01-10",
        "summary": "비케이탑스의 최대주주 변경 과정 추적. 와이퀸텟을 거쳐 정상용씨가 실질적 지배자로 부상하는 과정에서 복잡한 네트워크 존재.",
        "entities": [
            {"type": "company", "name": "비케이탑스", "role": "주요 상장사"},
            {"type": "company", "name": "와이퀸텟", "role": "구 최대주주"},
            {"type": "company", "name": "우진기전", "role": "관련 투자처"},
            {"type": "company", "name": "참테크", "role": "인수 대상"},
            {"type": "person", "name": "김봉겸", "role": "와이퀸텟 대표"},
            {"type": "person", "name": "정상용", "role": "현 대표이사"},
        ],
        "relations": [
            {"source": "정상용", "target": "비케이탑스", "type": "지배", "detail": "270억원 출자로 최대주주"},
            {"source": "비케이탑스", "target": "우진기전", "type": "투자", "detail": "450억원 투자 결정"},
        ],
        "risks": [
            {"type": "governance", "description": "최대주주의 최대주주 변경으로 실질 지배자 파악 어려움", "severity": "critical"},
            {"type": "financial", "description": "2019년말 300억원 이상 차입금 대비 현금 100억원 미만", "severity": "critical"},
            {"type": "financial", "description": "정상용 개인 150억원 무담보 차입, 차입원 불명확", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/287",
        "title": "매출 고속성장 프롬바이오, 이익은 왜 줄었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-01-03",
        "summary": "프롬바이오는 매년 30% 이상 매출 성장에도 올해 3분기 영업이익 32% 감소. 광고·판매수수료 확대가 이익 악화 원인.",
        "entities": [
            {"type": "company", "name": "프롬바이오", "role": "건강기능식품 제조사"},
            {"type": "company", "name": "노바렉스", "role": "외주생산업체"},
            {"type": "company", "name": "코스맥스바이오", "role": "외주생산업체"},
        ],
        "relations": [
            {"source": "프롬바이오", "target": "노바렉스", "type": "위탁제조", "detail": "보스웰리아 등 위탁 제조"},
        ],
        "risks": [
            {"type": "operational", "description": "주력 제품 매스틱 기세 약화, 신제품 빌베리 시장 정착 실패", "severity": "high"},
            {"type": "financial", "description": "광고선전비 81%, 판매수수료 60% 증가로 영업이익 32% 감소", "severity": "high"},
            {"type": "operational", "description": "TV홈쇼핑 의존도 60% 이상", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/286",
        "title": "인스코비, 매출 회복이 절실한 이유?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-30",
        "summary": "인스코비는 알뜰폰 사업 중심 통신 서비스 기업. 스마트그리드 사업 급락으로 실적 악화, 셀루메드 투자 손실까지 겹침.",
        "entities": [
            {"type": "company", "name": "인스코비", "role": "분석 대상 상장기업"},
            {"type": "company", "name": "프리텔레콤", "role": "알뜰폰 자회사"},
            {"type": "company", "name": "셀루메드", "role": "관계회사"},
            {"type": "person", "name": "유인수", "role": "대표이사"},
        ],
        "relations": [
            {"source": "인스코비", "target": "셀루메드", "type": "지분투자", "detail": "464억원 투자로 최대주주 22.17%"},
        ],
        "risks": [
            {"type": "financial", "description": "셀루메드 손상차손으로 순손실 기록", "severity": "critical"},
            {"type": "operational", "description": "스마트그리드 매출 270억원→33억원 급락", "severity": "high"},
            {"type": "financial", "description": "6차례 전환사채 발행, 미상환 잔액 241억원", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/285",
        "title": "현금 400억원 쌓아 둔 고바이오랩, 왜 대규모 자금조달?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-27",
        "summary": "마이크로바이옴 신약개발 업체 고바이오랩이 400억 현금 보유에도 445억 규모 대규모 자금조달. 연간 150억원 이상 현금 부족 예상.",
        "entities": [
            {"type": "company", "name": "고바이오랩", "role": "마이크로바이옴 신약개발 기업"},
            {"type": "company", "name": "한국콜마홀딩스", "role": "기술이전 계약 기업"},
        ],
        "relations": [
            {"source": "고바이오랩", "target": "한국콜마홀딩스", "type": "기술이전", "detail": "1840억원 규모 계약"},
        ],
        "risks": [
            {"type": "financial", "description": "매출 46억원 대비 연간 비용 170억원, 영업적자 100억원 초과", "severity": "high"},
            {"type": "operational", "description": "연간 100억원 이상 영업활동 현금유출", "severity": "high"},
            {"type": "regulatory", "description": "미국 임상 2상 실패 시 현금흐름 악화 심화", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/284",
        "title": "에이티세미콘, 유동성부족 어떻게 풀어갈까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-23",
        "summary": "에이티세미콘은 영업적자에도 현금흐름 양호했으나, 대규모 설비투자와 리더스기술투자 인수로 유동성 위기. 계속기업 불확실성 경고.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "분석 대상 상장기업"},
            {"type": "company", "name": "리더스기술투자", "role": "340억원에 인수된 종속기업"},
            {"type": "person", "name": "김형준", "role": "최대주주"},
        ],
        "relations": [
            {"source": "에이티세미콘", "target": "리더스기술투자", "type": "인수", "detail": "340억원에 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "누적결손 343억원, 유동부채 초과 827억원, 현금 1억원 수준", "severity": "critical"},
            {"type": "regulatory", "description": "외부감사인 계속기업 불확실성 경고, 상장폐지 위험", "severity": "critical"},
            {"type": "market", "description": "전환사채 상환액 500억원 규모", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/283",
        "title": "에이티세미콘, 자회사 통해 미상환 전환사채 매입한 까닭은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-22",
        "summary": "김형준이 에이티세미콘 실질적 최대주주로 등극하는 과정. 더에이치테크와 자회사를 통해 전환사채를 매입·매각하는 구조 구축.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "피인수회사"},
            {"type": "company", "name": "더에이치테크", "role": "지분·CB 인수 회사"},
            {"type": "company", "name": "에이티에이엠씨", "role": "100% 자회사"},
            {"type": "person", "name": "김형준", "role": "현 실질적 최대주주"},
            {"type": "person", "name": "변익성", "role": "전 최대주주"},
        ],
        "relations": [
            {"source": "김형준", "target": "에이티세미콘", "type": "지분인수", "detail": "유상증자 참여로 9.59% 확보"},
            {"source": "더에이치테크", "target": "에이티세미콘", "type": "전환사채 인수", "detail": "약 140억원 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "자회사가 모회사 CB 매입하는 구조로 투명성 우려", "severity": "high"},
            {"type": "financial", "description": "더에이치테크 자금 대부분이 차입금 약 172억원", "severity": "high"},
            {"type": "operational", "description": "2018년 경영진 갈등으로 경영 불안정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/282",
        "title": "변익성 일가의 돈으로 가능했던 더블우아이의 탈바꿈",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-16",
        "summary": "변익성 회장 중심 지배구조로 전환된 WI. 160억원 이상 가족 자금 투입으로 반도체장비에서 캐릭터 사업으로 전환.",
        "entities": [
            {"type": "person", "name": "변익성", "role": "WI 대표이사/최대주주"},
            {"type": "person", "name": "신은숙", "role": "변익성 배우자"},
            {"type": "company", "name": "WI", "role": "대상 회사"},
            {"type": "company", "name": "에이티테크놀러지", "role": "WI의 전신"},
            {"type": "company", "name": "코럴핑크", "role": "변익성 일가 자금 투입 회사"},
            {"type": "company", "name": "위드모바일", "role": "2018년 인수 대상"},
        ],
        "relations": [
            {"source": "변익성", "target": "WI", "type": "경영지배", "detail": "2017년 이후 대표이사로 경영권 장악"},
            {"source": "코럴핑크", "target": "WI", "type": "투자", "detail": "CB 및 유상증자에 31억원 투입"},
        ],
        "risks": [
            {"type": "financial", "description": "2021년 3분기 매출 66% 급락, 영업적자 전환, 순손실 70억원", "severity": "critical"},
            {"type": "financial", "description": "가족회사들이 차입금으로 인수자금 조달 가능성", "severity": "high"},
            {"type": "operational", "description": "인수 사업 실패로 각 47억원 손상차손 발생", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/281",
        "title": "김형준의 파트너 변익성, 에이티테크놀로지 주인으로",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-13",
        "summary": "에이티테크놀러지 경영권이 임광빈에서 변익성으로 이전되는 과정. 2015-2017년 유동성 위기 속 변익성이 최대주주로 부상.",
        "entities": [
            {"type": "person", "name": "김형준", "role": "에이티세미콘 이사"},
            {"type": "person", "name": "변익성", "role": "에이티테크놀로지 최대주주"},
            {"type": "person", "name": "임광빈", "role": "설립자, 원래 최대주주"},
            {"type": "company", "name": "에이티테크놀러지", "role": "에이티세미콘 최대주주"},
            {"type": "company", "name": "에이티세미콘", "role": "반도체 검사업체"},
            {"type": "company", "name": "머큐리아이피테크", "role": "투자자"},
        ],
        "relations": [
            {"source": "변익성", "target": "에이티테크놀러지", "type": "지분인수", "detail": "약 48억원 투입으로 22.27% 최대주주"},
            {"source": "김형준", "target": "변익성", "type": "협력", "detail": "함께 인수 및 구조조정 추진"},
        ],
        "risks": [
            {"type": "financial", "description": "2015년부터 반복적인 감자 및 유상증자", "severity": "critical"},
            {"type": "governance", "description": "정기현 경영지배인 횡령·배임으로 현금 8억원과 주식 무단 인출", "severity": "critical"},
            {"type": "legal", "description": "8차례 전환사채 발행으로 반복적 자금 압박", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/280",
        "title": "에이티세미콘은 어떻게 김형준씨 회사가 되었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-09",
        "summary": "김형준의 더에이치테크가 2017년 말 에이티세미콘 최대주주가 된 과정. 77억원 투입으로 재무 위기 극복.",
        "entities": [
            {"type": "person", "name": "김형준", "role": "더에이치테크 대표이사"},
            {"type": "person", "name": "김진주", "role": "에이티세미콘 대표이사"},
            {"type": "person", "name": "정윤호", "role": "에이티현대플러스 설립자"},
            {"type": "company", "name": "에이티세미콘", "role": "대상 기업"},
            {"type": "company", "name": "더에이치테크", "role": "2017년말 최대주주"},
            {"type": "company", "name": "에이티테크놀로지", "role": "이전 최대주주"},
        ],
        "relations": [
            {"source": "더에이치테크", "target": "에이티세미콘", "type": "유상증자 참여", "detail": "2017년말 11.77% 최대주주 확보"},
            {"source": "김형준", "target": "더에이치테크", "type": "소유지배", "detail": "30% 지분 보유, 자금 15억원 대출"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 자금 흐름으로 의사결정 투명성 부족", "severity": "high"},
            {"type": "financial", "description": "2016년 126억원 세전 순손실, 31% 자본잠식, 관리종목 지정", "severity": "critical"},
            {"type": "legal", "description": "에이티현대플러스 계약위반으로 20억원 회수 지연", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/279",
        "title": "에이티세미콘과 리더스기술투자의 무자본 인수, 김형준의 수완",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-06",
        "summary": "에이티세미콘이 부실기업임에도 약 400억원 조달해 리더스기술투자 인수. 김형준이 차입금과 전환사채로 무자본 M&A 전개.",
        "entities": [
            {"type": "person", "name": "김형준", "role": "에이티세미콘 실질적 최대주주"},
            {"type": "person", "name": "정윤호", "role": "에이티세미콘 부사장"},
            {"type": "company", "name": "에이티세미콘", "role": "인수대상 기업"},
            {"type": "company", "name": "리더스기술투자", "role": "피인수 기업"},
            {"type": "company", "name": "더에이치테크", "role": "김형준 개인회사"},
            {"type": "company", "name": "삼성코퍼레이션", "role": "정윤호 설립사"},
        ],
        "relations": [
            {"source": "에이티세미콘", "target": "리더스기술투자", "type": "인수", "detail": "전환사채 340억원으로 약 400억원 규모 인수"},
            {"source": "더에이치테크", "target": "에이티세미콘", "type": "투자", "detail": "차입금 55억원으로 주식 60억원 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "부분 자본잠식에다 2년 연속 대규모 세전 손실 부실기업", "severity": "critical"},
            {"type": "governance", "description": "차입금 통한 복잡한 자금 흐름으로 출처와 의도 불명확", "severity": "high"},
            {"type": "regulatory", "description": "관리종목 지정 우려", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/278",
        "title": "리더스기술투자 통해 MG손보 노리나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-12-06",
        "summary": "영세 신기술금융사 리더스기술투자가 전환사채로 조달한 자금으로 MG손해보험 유상증자 참여. 4조원대 손보사 인수 노리는지 의문.",
        "entities": [
            {"type": "company", "name": "리더스기술투자", "role": "MG손보 유상증자 참여"},
            {"type": "company", "name": "에이티세미콘", "role": "리더스기술투자 인수사"},
            {"type": "person", "name": "김형준", "role": "에이티세미콘 최대주주"},
            {"type": "company", "name": "MG손해보험", "role": "자본확충 대상사"},
            {"type": "company", "name": "새마을금고중앙회", "role": "MG손보 실질적 대주주"},
        ],
        "relations": [
            {"source": "에이티세미콘", "target": "리더스기술투자", "type": "인수", "detail": "전환사채로 전액 자금 조달"},
            {"source": "리더스기술투자", "target": "MG손해보험", "type": "유상증자 참여", "detail": "200억원 투자"},
        ],
        "risks": [
            {"type": "financial", "description": "자본 늘어나는데 들어온 돈 없다는 순환적 자본 조달 구조", "severity": "critical"},
            {"type": "governance", "description": "영세 신기술금융사로 4조원 손해보험사 인수는 비정상적 지배구조", "severity": "critical"},
            {"type": "regulatory", "description": "MG손보 RBC 97%로 재하락, 적기시정조치", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/277",
        "title": "리더스기술투자 품은 에이티세미콘, 꽃 길 걸을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-11-29",
        "summary": "에이티세미콘이 대규모 전환사채 발행과 무상감자 거쳐 리더스기술투자를 57.47% 프리미엄에 인수. 지속적 적자와 신사업 손실로 우려.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "반도체 테스트·패키징 기업"},
            {"type": "company", "name": "리더스기술투자", "role": "인수대상"},
            {"type": "company", "name": "SK하이닉스", "role": "주요 거래처"},
        ],
        "relations": [
            {"source": "에이티세미콘", "target": "리더스기술투자", "type": "인수", "detail": "주당 1450원에 경영권 취득"},
        ],
        "risks": [
            {"type": "financial", "description": "누적결손금 836억원, 자본잠식 상태, 9월까지 178억원 순손실", "severity": "critical"},
            {"type": "financial", "description": "460억원 미상환 전환사채가 발행주식 89% 규모", "severity": "critical"},
            {"type": "operational", "description": "신사업 모두 적자, 계열사 평가손실 80억원", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/276",
        "title": "10억원이 338억원으로, 리더스에셋홀딩스 다음 행보는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-11-25",
        "summary": "리더스에셋홀딩스가 약 128억원 투자해 리더스기술투자 지분을 338억원에 매각, 2년 만에 210억원 차익 확보.",
        "entities": [
            {"type": "company", "name": "리더스에셋홀딩스", "role": "투자회사"},
            {"type": "company", "name": "리더스기술투자", "role": "피투자회사"},
            {"type": "person", "name": "나용선", "role": "최대주주"},
            {"type": "company", "name": "필룩스그룹", "role": "배후투자자"},
            {"type": "company", "name": "에이티세미콘", "role": "인수사"},
        ],
        "relations": [
            {"source": "리더스에셋홀딩스", "target": "리더스기술투자", "type": "지분매각", "detail": "338억원에 매각"},
            {"source": "필룩스그룹", "target": "리더스에셋홀딩스", "type": "지원", "detail": "인수자금 조달 지원"},
        ],
        "risks": [
            {"type": "financial", "description": "무자본 M&A로 과도한 차입금 90억원 발생", "severity": "high"},
            {"type": "financial", "description": "10%대 후반 살인적 이자율로 연간 23억원 지출", "severity": "high"},
            {"type": "governance", "description": "복잡한 자금 네트워크와 특수관계자 거래 다수", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/275",
        "title": "리더스기술투자, 신기술사업 금융회사?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-11-22",
        "summary": "신기술사업금융회사 리더스기술투자는 벤처캐피탈 명목으로 주로 상장사 전환사채 인수와 관계기업 자금공급에 집중.",
        "entities": [
            {"type": "company", "name": "리더스기술투자", "role": "신기술사업금융회사"},
            {"type": "company", "name": "필룩스그룹", "role": "주요 투자대상"},
            {"type": "company", "name": "상지카일룸", "role": "전환사채 인수자"},
            {"type": "company", "name": "에이티세미콘", "role": "현 최대주주"},
            {"type": "person", "name": "나용선", "role": "전 대표이사"},
            {"type": "person", "name": "최기보", "role": "전 사내이사"},
            {"type": "company", "name": "삼부토건", "role": "전환사채 발행사"},
        ],
        "relations": [
            {"source": "리더스기술투자", "target": "필룩스그룹", "type": "투자·자금공급", "detail": "계열사 통해 지분 및 자금공급"},
            {"source": "리더스기술투자", "target": "상지카일룸", "type": "협력", "detail": "60억원 전환사채 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "나용선이 자본금 2000만원과 차입금으로만 설립", "severity": "high"},
            {"type": "legal", "description": "삼부토건 전환사채 80억원 차명 인수 의혹", "severity": "critical"},
            {"type": "market", "description": "전환사채 인수 후 주가 급등 시점 일치, 주가조작 의심", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/274",
        "title": "릭스솔루션의 대규모 조달자금, 어디에 쓰일까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-11-18",
        "summary": "릭스솔루션이 유상증자 265억원, 전환사채 500억원 등 873억원 규모 대규모 자금 조달. 실제 자금 용도는 M&A로 추정.",
        "entities": [
            {"type": "company", "name": "릭스솔루션", "role": "자금조달 회사"},
            {"type": "company", "name": "스트라타조합", "role": "유상증자 인수자"},
            {"type": "company", "name": "헤라파트너스", "role": "유상증자 인수자"},
            {"type": "company", "name": "리더스기술투자", "role": "전환사채 인수자"},
            {"type": "company", "name": "지트리홀딩스", "role": "투자대상 회사"},
            {"type": "person", "name": "임진환", "role": "스트라타조합 대표이사"},
        ],
        "relations": [
            {"source": "릭스솔루션", "target": "스트라타조합", "type": "유상증자", "detail": "64억9600만원 제3자 배정"},
            {"source": "리더스기술투자", "target": "릭스솔루션", "type": "전환사채 인수", "detail": "350억원 36회차 CB 주요 인수자"},
        ],
        "risks": [
            {"type": "governance", "description": "실질 소유자 불명확한 페이퍼컴퍼니 의심", "severity": "critical"},
            {"type": "financial", "description": "199억원 누적손실금, 3년 연속 영업적자, 상장폐지 위험", "severity": "critical"},
            {"type": "legal", "description": "전환사채 재매각 시 현저히 낮은 전환가액으로 특정인 특혜 의심", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/273",
        "title": "릭스솔루션은 왜 상장폐지 위기의 라이트론에 투자했나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-11-15",
        "summary": "경영난 릭스솔루션이 상장폐지 위기 라이트론에 100억원 대여. 복잡한 자회사 거래 구조와 의심스러운 네트워크 연계 추적.",
        "entities": [
            {"type": "company", "name": "릭스솔루션", "role": "라이트론 투자자"},
            {"type": "company", "name": "라이트론", "role": "투자 대상 회사"},
            {"type": "company", "name": "엔비알컴퍼니", "role": "릭스솔루션 최대주주"},
            {"type": "company", "name": "상지카일룸", "role": "관련 회사"},
            {"type": "company", "name": "바른네트웍스", "role": "100% 자회사"},
            {"type": "person", "name": "서의환", "role": "엔비알컴퍼니 추정 실질주주"},
        ],
        "relations": [
            {"source": "릭스솔루션", "target": "라이트론", "type": "금전대여", "detail": "100억원 대여 후 8.91% 지분 취득"},
            {"source": "엔비알컴퍼니", "target": "릭스솔루션", "type": "최대주주", "detail": "2019년 유상증자로 최대주주 등극"},
        ],
        "risks": [
            {"type": "governance", "description": "경영진 교체 후에도 중앙디앤엠 관련 인물 실질적 경영권 행사", "severity": "critical"},
            {"type": "financial", "description": "자본잠식 50% 수준에서 상장폐지 위기 회사에 100억원 투자", "severity": "critical"},
            {"type": "legal", "description": "라이트론 경영권 분쟁, 횡령 소송 등 법적 문제", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/272",
        "title": "릭스솔루션 경영권 분쟁의 결말은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-11-11",
        "summary": "중앙디앤엠이 바른테크놀로지 지분을 엔비알컴퍼니에 매각 후 복잡한 주주구조와 경영권 분쟁 발생. 담보권 실행으로 최대주주 지위 변동.",
        "entities": [
            {"type": "company", "name": "릭스솔루션", "role": "중심기업"},
            {"type": "company", "name": "중앙디앤엠", "role": "이전 최대주주"},
            {"type": "company", "name": "엔비알컴퍼니", "role": "신규 최대주주"},
            {"type": "company", "name": "리더스기술투자", "role": "차입처, 담보권 실행"},
            {"type": "company", "name": "상지카일룸", "role": "전환사채 인수자"},
            {"type": "person", "name": "한종희", "role": "상지카일룸 회장"},
            {"type": "company", "name": "스트라타조합", "role": "유상증자 인수자"},
        ],
        "relations": [
            {"source": "중앙디앤엠", "target": "엔비알컴퍼니", "type": "지분양수도", "detail": "2019년말 지분 매각"},
            {"source": "리더스기술투자", "target": "엔비알컴퍼니", "type": "담보권실행", "detail": "2021년 7월 반대매매로 주식 회수"},
        ],
        "risks": [
            {"type": "governance", "description": "최대주주 변동 반복으로 경영안정성 저하", "severity": "critical"},
            {"type": "legal", "description": "경영권 분쟁으로 신주발행금지 가처분신청 등 소송 진행", "severity": "high"},
            {"type": "financial", "description": "단기간 765억원 규모 대규모 자금조달, 자금흐름 추적 어려움", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/271",
        "title": "김병진 회장은 클라우드에어 매각으로 얼마나 벌었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-11-08",
        "summary": "김병진 회장과 플레이크는 클라우드에어를 약 500억원에 매각. 주당 1,300원→5,473원, 1년여 만에 4배 이상 차익 획득.",
        "entities": [
            {"type": "person", "name": "김병진", "role": "라이브플렉스·클라우드에어 회장"},
            {"type": "company", "name": "플레이크", "role": "김병진 개인회사"},
            {"type": "company", "name": "클라우드에어", "role": "매각 대상 회사"},
            {"type": "company", "name": "케이앤커", "role": "클라우드에어 인수자"},
            {"type": "company", "name": "경남제약", "role": "관련 계열사"},
        ],
        "relations": [
            {"source": "플레이크", "target": "클라우드에어", "type": "지분매각", "detail": "500억원에 매각"},
            {"source": "클라우드에어", "target": "케이앤커", "type": "경영권이전", "detail": "622억원 규모 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "누적손실 360억원 결손기업에 경영권 프리미엄 200% 이상 책정", "severity": "high"},
            {"type": "governance", "description": "무자본 M&A로 자산 8,200만원 회사가 622억원 인수", "severity": "high"},
            {"type": "market", "description": "계획적 지분 가격 상승 통한 차익 실현 의도 의심", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/270",
        "title": "상장폐지 위기 바른전자를 거쳐간 최대 주주들",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-11-05",
        "summary": "김태섭 회장 주가조작 혐의 구속 후 바른전자는 회생절차 진입. 국책은행과 다양한 투자조합 거쳐 에스맥이 최대주주.",
        "entities": [
            {"type": "company", "name": "바른전자", "role": "주대상 기업"},
            {"type": "company", "name": "산업은행", "role": "회생채권자"},
            {"type": "company", "name": "퀀텀제1호투자조합", "role": "초기 인수자"},
            {"type": "person", "name": "박경진", "role": "퀀텀제1호투자조합 대표"},
            {"type": "person", "name": "최기보", "role": "세이첨밸류아시아파트너스 설립자"},
            {"type": "company", "name": "이엔플러스", "role": "중간 경영권 인수"},
            {"type": "company", "name": "에스맥", "role": "최종 최대주주"},
            {"type": "person", "name": "나용선", "role": "리더스기술투자 대표"},
        ],
        "relations": [
            {"source": "산업은행", "target": "바른전자", "type": "출자전환", "detail": "944만주 배정 후 전량 소각"},
            {"source": "에스맥", "target": "바른전자", "type": "지분인수", "detail": "이엔플러스 구주 120억원에 매수, 38.75% 확보"},
        ],
        "risks": [
            {"type": "regulatory", "description": "코스닥시장위원회 상장폐지 의결, 이의신청 제출", "severity": "critical"},
            {"type": "financial", "description": "자본잠식으로 외부감사인 감사의견 거절, 회생절차 진입", "severity": "critical"},
            {"type": "legal", "description": "김태섭 회장 주가조작 혐의 구속, 지배주주 주식 무상소각", "severity": "critical"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (27차) ===\n")

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
