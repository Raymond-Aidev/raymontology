#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 26차 (휴림로봇/에이티세미콘/위메이드/클리노믹스/원티드랩 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/309",
        "title": "휴림로봇의 파라텍 인수에 배관업체들이 왜 나와?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-03-17",
        "summary": "휴림로봇과 파라텍 인수의 복잡한 소유구조 분석. 배관 공급 업체들과의 불명확한 연결 고리, 페이퍼컴퍼니 통한 자금 흐름 의혹.",
        "entities": [
            {"type": "company", "name": "휴림로봇", "role": "코스닥 상장사"},
            {"type": "company", "name": "파라텍", "role": "코스닥 상장 피인수사"},
            {"type": "company", "name": "삼부토건", "role": "경영권 분쟁 기업"},
            {"type": "company", "name": "휴림홀딩스", "role": "휴림로봇 최대주주"},
            {"type": "company", "name": "제이앤리더스", "role": "휴림홀딩스 최대주주"},
            {"type": "person", "name": "김지영", "role": "제이앤리더스 100% 소유자"},
            {"type": "person", "name": "정광원", "role": "휴림로봇/파라텍 CEO"},
            {"type": "person", "name": "황만회", "role": "휴림홀딩스 CEO"},
            {"type": "company", "name": "엔에스이앤지", "role": "배관업체"},
        ],
        "relations": [
            {"source": "김지영", "target": "제이앤리더스", "type": "ownership", "detail": "100% 주주"},
            {"source": "제이앤리더스", "target": "휴림홀딩스", "type": "ownership", "detail": "최대주주"},
            {"source": "휴림홀딩스", "target": "휴림로봇", "type": "ownership", "detail": "최대주주"},
            {"source": "휴림로봇", "target": "파라텍", "type": "ownership", "detail": "62.75% 지분"},
        ],
        "risks": [
            {"type": "governance", "description": "김지영 통한 다층 지배구조로 실소유 불명확", "severity": "critical"},
            {"type": "legal", "description": "배관업체 422억원 인수 시도 실패, 자본 미달", "severity": "high"},
            {"type": "financial", "description": "휴림로봇이 자기자본 -9800만원 업체에 42억 대출", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/308",
        "title": "전환사채가 금값에 거래될 때",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-03-04",
        "summary": "전환사채 거래에서 내재가치 초과 가격 책정 사례 분석. 리더스기술투자 삼부토건 CB, 오션브릿지 에이팩트 CB 프리미엄 거래.",
        "entities": [
            {"type": "company", "name": "리더스기술투자", "role": "CB 투자자"},
            {"type": "company", "name": "삼부토건", "role": "CB 발행사"},
            {"type": "company", "name": "오션브릿지", "role": "CB 투자자"},
            {"type": "company", "name": "에이팩트", "role": "CB 발행사"},
            {"type": "company", "name": "뮤추얼그로우쓰", "role": "CB 매수자"},
            {"type": "person", "name": "박병엽", "role": "판텍 전 부회장"},
        ],
        "relations": [
            {"source": "리더스기술투자", "target": "삼부토건", "type": "investment", "detail": "80억 CB 인수, 297억 평가"},
            {"source": "오션브릿지", "target": "에이팩트", "type": "investment", "detail": "50억 CB를 79.7억에 매각"},
        ],
        "risks": [
            {"type": "financial", "description": "350억 CB가 861억 평가, 일관성 없는 회계 처리", "severity": "high"},
            {"type": "governance", "description": "비공개 관련당사자 거래, 실질 지배 미반영", "severity": "critical"},
            {"type": "operational", "description": "자산 540만원 페이퍼컴퍼니가 150억 CB 배정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/307",
        "title": "휴림로봇은 삼부토건에 경영권을 행사했었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-04-04",
        "summary": "휴림로봇의 삼부토건 지분 9.67%로 최대주주 지위 유지. 그러나 삼부토건 경영진에 휴림로봇 흔적 없음. 실질 경영권 행사 여부 불명확.",
        "entities": [
            {"type": "company", "name": "휴림로봇", "role": "삼부토건 최대주주"},
            {"type": "company", "name": "삼부토건", "role": "피인수 기업"},
            {"type": "company", "name": "제이앤리더스", "role": "휴림로봇 최대주주"},
            {"type": "company", "name": "휴림홀딩스", "role": "지분 보유사"},
            {"type": "person", "name": "김지영", "role": "제이앤리더스 100% 소유자"},
        ],
        "relations": [
            {"source": "휴림로봇", "target": "삼부토건", "type": "ownership", "detail": "9.67% 지분, 최대주주"},
            {"source": "휴림홀딩스", "target": "휴림로봇", "type": "ownership", "detail": "6.34% 지분"},
        ],
        "risks": [
            {"type": "governance", "description": "9.67% 지분으로는 경영권 지분 부족, 삼부토건에 휴림로봇 흔적 없음", "severity": "high"},
            {"type": "financial", "description": "휴림홀딩스 자본 10억에 부채 30억으로 순자산 700억 회사 지배", "severity": "high"},
            {"type": "operational", "description": "휴림로봇 현금 유동성 확보 위해 장내 매도 추진", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/306",
        "title": "에이티세미콘 경영권 향방, 아직은 알 수 없다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-03-31",
        "summary": "에이티세미콘 대규모 자금조달(2,101억원) 주도하는 인플루언서랩 실체 불명확. 기존 CB 보유자 전환 시점에 따라 경영권 변동 가능.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "자본 재구성 대상"},
            {"type": "company", "name": "인플루언서랩", "role": "신규 최대주주 후보"},
            {"type": "person", "name": "김형준", "role": "현 대주주/CEO"},
            {"type": "company", "name": "더에이치테크", "role": "CB 보유 관계사"},
            {"type": "company", "name": "아임", "role": "300억 CB 인수자"},
        ],
        "relations": [
            {"source": "인플루언서랩", "target": "에이티세미콘", "type": "investment", "detail": "101억 유상증자로 20.07% 최대주주"},
        ],
        "risks": [
            {"type": "governance", "description": "인플루언서랩 실체 미확인, 실제 경영 주체 불명확", "severity": "critical"},
            {"type": "financial", "description": "2000억 CB 보유자 전환 시점에 따라 지분구조 급변 가능", "severity": "high"},
            {"type": "operational", "description": "영업실적 부진 중 300억 CB 선제 인수로 자금 부담 가중", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/305",
        "title": "에이티세미콘은 왜 복잡한 자금조달 구조를 짰을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-03-28",
        "summary": "에이티세미콘 2,101억 복합 자금조달로 최대주주 변경 예정. 신설회사 인플루언서랩이 유상증자/CB/BW 인수해 지배력 확보 시도.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "자금조달 대상"},
            {"type": "person", "name": "김형준", "role": "대표이사"},
            {"type": "company", "name": "인플루언서랩", "role": "신규 최대주주 후보"},
            {"type": "person", "name": "한진희", "role": "인플루언서랩 100% 출자자"},
        ],
        "relations": [
            {"source": "김형준", "target": "에이티세미콘", "type": "ownership", "detail": "8.01%→23.14% 증가 예정"},
            {"source": "인플루언서랩", "target": "에이티세미콘", "type": "investment", "detail": "101억 유상증자, 2000억 CB/BW 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "인플루언서랩 사채 전환 시 거의 전체 지분 확보 가능", "severity": "critical"},
            {"type": "financial", "description": "자본금 3000만원 신설회사가 2000억 자금조달 필요", "severity": "high"},
            {"type": "market", "description": "시총 718억 회사에 2000억 투자로 과도한 레버리지", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/304",
        "title": "에이티세미콘의 리더스기술투자 인수, 그 이후",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-03-21",
        "summary": "에이티세미콘 최대주주 변경과 101억 유상증자, 1000억 CB/BW 추진. 2021년 순손실 271억원에도 리더스기술투자 340억 인수.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "주요 기업"},
            {"type": "company", "name": "리더스기술투자", "role": "자회사"},
            {"type": "company", "name": "인플루언서랩", "role": "유상증자/CB/BW 인수자"},
            {"type": "person", "name": "김형준", "role": "대표/최대주주"},
        ],
        "relations": [
            {"source": "에이티세미콘", "target": "리더스기술투자", "type": "ownership", "detail": "23.96% 지분 340억 투입"},
            {"source": "인플루언서랩", "target": "에이티세미콘", "type": "investment", "detail": "101억 유상증자, 2000억 CB/BW"},
        ],
        "risks": [
            {"type": "financial", "description": "2021년 순손실 271억, 자회사 9곳 중 9곳 적자(합계 200억)", "severity": "critical"},
            {"type": "financial", "description": "2년간 600억 CB 발행으로 부채 급증, 상환능력 의문", "severity": "high"},
            {"type": "governance", "description": "최대주주 변경으로 경영권 불안정, 경영권 매각 추측", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/303",
        "title": "삼부토건 매각하는 휴림로봇의 주인은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-03-14",
        "summary": "휴림홀딩스가 제이앤리더스로부터 30억 차입해 삼부토건 지분 인수. 남산배관센타, 이트론, 이아이디, 이화전기 간 순환출자 구조.",
        "entities": [
            {"type": "company", "name": "삼부토건", "role": "매각 대상"},
            {"type": "company", "name": "휴림로봇", "role": "삼부토건 최대주주"},
            {"type": "company", "name": "휴림홀딩스", "role": "휴림로봇 최대주주"},
            {"type": "company", "name": "제이앤리더스", "role": "자금 공급처"},
            {"type": "company", "name": "남산배관센타", "role": "황만회 대표 회사"},
            {"type": "company", "name": "이트론", "role": "순환출자 참여"},
            {"type": "company", "name": "이아이디", "role": "순환출자 참여"},
            {"type": "company", "name": "이화전기", "role": "순환출자 참여"},
            {"type": "person", "name": "김지영", "role": "제이앤리더스 100% 주주"},
            {"type": "person", "name": "황만회", "role": "휴림홀딩스 대표"},
        ],
        "relations": [
            {"source": "제이앤리더스", "target": "휴림홀딩스", "type": "financing", "detail": "30억원 차입"},
            {"source": "휴림홀딩스", "target": "휴림로봇", "type": "ownership", "detail": "11.07% 최대주주"},
            {"source": "남산배관센타", "target": "이트론", "type": "investment", "detail": "CB 100억 매수 후 풋옵션"},
            {"source": "이화전기", "target": "이아이디", "type": "ownership", "detail": "최대주주"},
        ],
        "risks": [
            {"type": "governance", "description": "휴림로봇/삼부토건 실소유자 불명확, 명의 대여 의혹", "severity": "critical"},
            {"type": "financial", "description": "자본 15억 회사가 840억+4576억 상장사/건설사 지배", "severity": "high"},
            {"type": "operational", "description": "남산배관센타 2020년 10월 부도, 제이앤리더스 직원 1명", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/302",
        "title": "매물로 나온 삼부토건, 실제 주인은 누구?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-03-10",
        "summary": "삼부토건 경영권 지분 25% 매각 진행, 시가 2.5배(약 2000억) 제시. BW/CB로 최대주주 변동 가능성.",
        "entities": [
            {"type": "company", "name": "삼부토건", "role": "매각 대상"},
            {"type": "company", "name": "휴림로봇", "role": "현 최대주주 10.48%"},
            {"type": "company", "name": "아레나글로벌", "role": "CB 보유자"},
            {"type": "company", "name": "이석산업개발", "role": "BW 보유자"},
            {"type": "company", "name": "리더스기술투자", "role": "CB 보유자"},
            {"type": "person", "name": "조성옥", "role": "전 대교종합건설 회장"},
            {"type": "person", "name": "이창용", "role": "이석산업개발 50% 주주"},
        ],
        "relations": [
            {"source": "삼부토건", "target": "휴림로봇", "type": "ownership", "detail": "2017년 인수, 10.48% 최대주주"},
            {"source": "이석산업개발", "target": "삼부토건", "type": "securities", "detail": "BW 250억 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "BW/CB 통한 경영권 변동 가능, 실제 최대주주 불명확", "severity": "critical"},
            {"type": "legal", "description": "무자본 인수 의혹, 5% 공시 회피 위한 물량 분할 발행", "severity": "critical"},
            {"type": "market", "description": "시가 2.5배(150% 프리미엄) 요구로 적정가 논란", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/301",
        "title": "알파홀딩스의 한송네오텍 인수, 액면 그대로 믿어야 할까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-03-07",
        "summary": "알파홀딩스가 OLED 장비업체 한송네오텍 경영권 인수. 이미 지분 교차 보유, 자금 이동, 부동산 거래로 깊은 관계 형성.",
        "entities": [
            {"type": "company", "name": "알파홀딩스", "role": "인수자"},
            {"type": "company", "name": "한송네오텍", "role": "인수 대상"},
            {"type": "company", "name": "시너웍스", "role": "한송네오텍 최대주주"},
            {"type": "company", "name": "프리미어바이오", "role": "알파홀딩스 최대주주"},
            {"type": "company", "name": "신화아이티", "role": "2차전지 소재기업"},
            {"type": "person", "name": "손준혁", "role": "시너웍스 설립자"},
            {"type": "person", "name": "구희도", "role": "프리미어바이오 대표"},
        ],
        "relations": [
            {"source": "알파홀딩스", "target": "한송네오텍", "type": "acquisition", "detail": "13.40% 338억 인수, 90억 유상증자"},
            {"source": "한송네오텍", "target": "알파홀딩스", "type": "investment", "detail": "2020-21년 100억 투자"},
        ],
        "risks": [
            {"type": "governance", "description": "상호 지분 보유로 지배권 모호, 한송네오텍이 알파홀딩스 최대주주 될 가능성", "severity": "critical"},
            {"type": "financial", "description": "알파홀딩스 연간 적자 상황에서 270억 자금 흐름 목적 의문", "severity": "high"},
            {"type": "operational", "description": "2차전지 사업 명목이 실제 목적 은폐 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/300",
        "title": "위메이드 트리는 얼마짜리 회사일까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-02-28",
        "summary": "위메이드 트리의 위메이드 합병 가치평가 분석. 주당 389,373원 평가가 WEMIX 토큰 가치를 제대로 반영하는지 의문.",
        "entities": [
            {"type": "company", "name": "위메이드", "role": "합병 주체"},
            {"type": "company", "name": "위메이드 트리", "role": "합병 대상"},
            {"type": "company", "name": "위메이드트리 Pte", "role": "싱가포르 자회사"},
            {"type": "company", "name": "위메이드 이노베이션", "role": "선데이토즈 인수 주체"},
            {"type": "company", "name": "선데이토즈", "role": "피인수 게임사"},
        ],
        "relations": [
            {"source": "위메이드", "target": "위메이드 트리", "type": "merger", "detail": "합병비율 3.097 위메이드주"},
            {"source": "위메이드트리 Pte", "target": "위메이드 이노베이션", "type": "investment", "detail": "1800억 출자"},
            {"source": "위메이드 이노베이션", "target": "선데이토즈", "type": "acquisition", "detail": "1667억에 38.9% 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "위메이드 트리 가치평가가 투기적 매출 성장 예측에 의존(48억→6390억)", "severity": "critical"},
            {"type": "governance", "description": "합병비율에서 WEMIX 유동화/선데이토즈 인수 가치 제외, 소수주주 불이익", "severity": "high"},
            {"type": "market", "description": "사용자 성장 예측(26만→400만) 히트 게임 출시에 크게 의존", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/299",
        "title": "미르4 개발사 위메이드넥스트는 적정하게 평가되었나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-02-24",
        "summary": "위메이드맥스가 위메이드넥스트를 6,522억 기업가치로 인수. 자본잠식 상태에서 미르4 매출 추정에 크게 의존한 평가.",
        "entities": [
            {"type": "company", "name": "위메이드", "role": "최상위 지배회사"},
            {"type": "company", "name": "위메이드맥스", "role": "인수 주체"},
            {"type": "company", "name": "위메이드넥스트", "role": "피인수사"},
            {"type": "company", "name": "위메이드트리", "role": "위믹스 발행사"},
            {"type": "company", "name": "이촌회계법인", "role": "기업가치 평가 기관"},
        ],
        "relations": [
            {"source": "위메이드맥스", "target": "위메이드넥스트", "type": "acquisition", "detail": "100% 지분, 1750만주 발행"},
            {"source": "위메이드", "target": "위메이드트리", "type": "merger", "detail": "위믹스 암호화폐 보유"},
            {"source": "위메이드맥스", "target": "위메이드", "type": "ownership", "detail": "33.89%→55.21% 상승"},
        ],
        "risks": [
            {"type": "financial", "description": "위메이드넥스트 순자산 -67억 완전자본잠식에서 6522억 평가", "severity": "high"},
            {"type": "market", "description": "미르4 매출 추정 의존, 4분기 예상 836억 vs 실제 609억 괴리", "severity": "high"},
            {"type": "operational", "description": "주당 수익가치의 대부분이 2026년 이후 영구현금흐름에서 발생", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/298",
        "title": "위메이드 성장재원, 위믹스의 주인은 누구일까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-02-21",
        "summary": "위메이드가 위믹스 암호화폐로 2255억 유동화해 매출/이익 인식. 기존 회계원칙과 배치, 투자자 보호 문제 제기.",
        "entities": [
            {"type": "company", "name": "위메이드", "role": "위믹스 발행사"},
            {"type": "company", "name": "위메이드 트리", "role": "자회사"},
            {"type": "company", "name": "Wemade tree Pte", "role": "위믹스 보유사"},
            {"type": "company", "name": "선데이토즈", "role": "인수 대상"},
            {"type": "company", "name": "비덴트", "role": "투자 대상"},
        ],
        "relations": [
            {"source": "위메이드", "target": "위메이드 트리", "type": "ownership", "detail": "모자회사 관계"},
            {"source": "위메이드", "target": "선데이토즈", "type": "acquisition", "detail": "1667억 주식/BW 매입"},
            {"source": "위메이드", "target": "비덴트", "type": "investment", "detail": "800억 CB 매입"},
        ],
        "risks": [
            {"type": "financial", "description": "암호화폐 유동화 2255억이 실제 사업 수익 아님, 수익성 과대표시", "severity": "critical"},
            {"type": "governance", "description": "암호화폐 매출 인식이 전통 회계원칙과 상충, 공시 불충분", "severity": "high"},
            {"type": "regulatory", "description": "암호화폐 발행 자금조달이 부채 인식 안 됨, 적법성 문제", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/297",
        "title": "클리노믹스, 코로나19 특수 끝나면?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-02-17",
        "summary": "클리노믹스 코로나19 진단키트 판매로 폭발적 성장. 그러나 핵심 암진단 매출 54% 감소, 팬데믹 이후 지속가능성 우려.",
        "entities": [
            {"type": "company", "name": "클리노믹스", "role": "유전체 진단 기업"},
            {"type": "company", "name": "클리노믹스USA", "role": "미국 자회사"},
            {"type": "company", "name": "제로믹스", "role": "신규 자회사"},
        ],
        "relations": [
            {"source": "클리노믹스", "target": "클리노믹스USA", "type": "subsidiary", "detail": "2021년 9월까지 2375억 매출"},
        ],
        "risks": [
            {"type": "market", "description": "코로나 진단 매출이 일시적, 핵심 암진단 매출 54% 감소(34억)", "severity": "high"},
            {"type": "operational", "description": "영업이익 79억에도 영업현금흐름 -40억, 매출채권 150억 증가", "severity": "high"},
            {"type": "financial", "description": "신약개발 자금 필요, 2021년 7월 CB 300억 발행", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/296",
        "title": "적자행진 아이오케이컴퍼니, 부채비율 왜 낮을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-02-16",
        "summary": "아이오케이컴퍼니 5년 연속 적자에도 낮은 부채비율 유지. 대규모 유상증자/CB 전환으로 재무구조 개선, 실질 영업악화 은폐.",
        "entities": [
            {"type": "company", "name": "아이오케이컴퍼니", "role": "엔터테인먼트 기업"},
            {"type": "company", "name": "광림그룹", "role": "모회사"},
            {"type": "company", "name": "W홀딩컴퍼니", "role": "전 모회사"},
            {"type": "company", "name": "미래산업", "role": "CB 발행 계열사"},
            {"type": "company", "name": "비비안", "role": "CB 발행 계열사"},
            {"type": "company", "name": "쌍방울", "role": "광림그룹 계열사"},
            {"type": "person", "name": "원영식", "role": "전 회장"},
            {"type": "person", "name": "김성태", "role": "광림그룹 회장"},
        ],
        "relations": [
            {"source": "광림그룹", "target": "아이오케이컴퍼니", "type": "ownership", "detail": "2020년 9월 인수"},
            {"source": "아이오케이컴퍼니", "target": "미래산업", "type": "securities", "detail": "20억 CB 발행/매입"},
        ],
        "risks": [
            {"type": "financial", "description": "5년 연속 영업적자, CB 전환으로 낮은 부채비율 유지해 영업악화 은폐", "severity": "high"},
            {"type": "governance", "description": "계열사 간 CB 발행 순환구조로 재무 상호의존", "severity": "high"},
            {"type": "governance", "description": "18회차 CB 전환가 2171원 vs 현재 주가 1130원, 최대주주 지위 위협", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/295",
        "title": "에이티세미콘, 전환사채 조기상환 왜 하나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-02-10",
        "summary": "에이티세미콘 2021년 5월 발행 CB 130억 조기상환. 유동성 우려와 부채비율 개선 노력. 창업자 콜옵션 유지.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "CB 발행사"},
            {"type": "person", "name": "김형준", "role": "대주주/대표"},
            {"type": "company", "name": "유진에이티제일차", "role": "CB 인수 SPC"},
            {"type": "company", "name": "리더스기술투자", "role": "피인수 자회사"},
            {"type": "company", "name": "유진투자증권", "role": "구조화 에이전트"},
        ],
        "relations": [
            {"source": "에이티세미콘", "target": "리더스기술투자", "type": "acquisition", "detail": "23.96% 340억 인수"},
            {"source": "김형준", "target": "에이티세미콘", "type": "control", "detail": "대주주, CB 콜옵션 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "유동비율 23.8%로 극히 낮음, 단기 부채 커버 불가", "severity": "critical"},
            {"type": "financial", "description": "부채비율 396%, CB 346억이 단기부채 1086억 중 대부분", "severity": "high"},
            {"type": "governance", "description": "대주주 일방적 콜옵션 보유, 이사회 감독 없는 의사결정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/294",
        "title": "이엔드디, 매출 급증이냐 매출 공백이냐?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-02-07",
        "summary": "이엔드디 2018년 미세먼지 특별법으로 매연저감장치 수요 폭발. 2021년 3분기 매출 17% 감소, 2차전지 소재사업 전환 기로.",
        "entities": [
            {"type": "company", "name": "이엔드디", "role": "촉매소재/2차전지 소재 기업"},
            {"type": "company", "name": "LG화학", "role": "양극활물질 전구체 승인"},
            {"type": "company", "name": "유미코아", "role": "업무협약 체결"},
        ],
        "relations": [
            {"source": "이엔드디", "target": "LG화학", "type": "partnership", "detail": "2014년 양극활물질 전구체 승인"},
            {"source": "이엔드디", "target": "유미코아", "type": "partnership", "detail": "2021년 8월 업무협약"},
        ],
        "risks": [
            {"type": "market", "description": "매연저감장치 정부 예산 의존, 2024년 사업 종료 후 불확실", "severity": "critical"},
            {"type": "operational", "description": "매연저감장치 매출 410억→245억 40% 급락", "severity": "high"},
            {"type": "financial", "description": "2021년 3분기 영업이익 62억(전년 반토막), 순이익 70% 감소", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/293",
        "title": "잭팟 터뜨린 에이비엘바이오, 선순환 들어서나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-01-27",
        "summary": "에이비엘바이오가 사노피와 1.2조원 기술이전 계약. ABL301 뇌신경질환 치료제로 국내 최초. 계약금 900억원으로 흑자 전환 가능.",
        "entities": [
            {"type": "company", "name": "에이비엘바이오", "role": "신약개발 기업"},
            {"type": "company", "name": "사노피", "role": "글로벌 제약사"},
        ],
        "relations": [
            {"source": "에이비엘바이오", "target": "사노피", "type": "technology_transfer", "detail": "ABL301 1.2조원 계약"},
        ],
        "risks": [
            {"type": "financial", "description": "기술이전 수익에만 의존, 현금 몇 년 내 소진 가능", "severity": "high"},
            {"type": "operational", "description": "R&D 비용 급증(67억→423억), 제조 인프라 부재", "severity": "high"},
            {"type": "market", "description": "임상 진행에 따른 성공 여부 불확실, 라이선싱 딜 실패 전례", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/292",
        "title": "테스나 인수 재도전 vs. 유동성 확보, 와이팜의 선택은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-01-24",
        "summary": "와이팜 2020년 상장 후 테스나 4000억 인수 시도, 자금조달 실패로 포기. 유동성 악화 속 테스나 주식 매각 또는 인수 재도전 기로.",
        "entities": [
            {"type": "company", "name": "와이팜", "role": "코스닥 상장사"},
            {"type": "company", "name": "테스나", "role": "인수 대상"},
            {"type": "company", "name": "삼성전자", "role": "주요 고객"},
            {"type": "company", "name": "펜타스톤인베스트먼트", "role": "계열사"},
            {"type": "person", "name": "유대규", "role": "대표이사"},
        ],
        "relations": [
            {"source": "와이팜", "target": "삼성전자", "type": "customer", "detail": "매출 100% 의존"},
            {"source": "와이팜", "target": "테스나", "type": "investment", "detail": "3.75% 138억 취득, 장부가 286억"},
        ],
        "risks": [
            {"type": "financial", "description": "2020년 이후 296억 현금 유출, 2021년 9월 현금 44억으로 급감", "severity": "critical"},
            {"type": "operational", "description": "삼성전자 관계 개선 불가시 현금흐름 창출 불가능", "severity": "high"},
            {"type": "market", "description": "테스나 주식 평가이익 급감(360억→286억)", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/291",
        "title": "와이팜, 믿었던 삼성전자에 발등 찍혔나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-01-20",
        "summary": "와이팜 2019년 삼성전자 메인 공급사로 급성장, 2020년 코로나와 가격경쟁력 약화로 매출 70% 급락. 보급형 스마트폰 수주에서 경쟁사에 밀림.",
        "entities": [
            {"type": "company", "name": "와이팜", "role": "분석 대상"},
            {"type": "company", "name": "삼성전자", "role": "주요 고객 99%"},
            {"type": "company", "name": "Skyworks", "role": "경쟁사"},
            {"type": "company", "name": "Broadcom", "role": "경쟁사"},
            {"type": "company", "name": "Qorvo", "role": "경쟁사"},
        ],
        "relations": [
            {"source": "와이팜", "target": "삼성전자", "type": "supply", "detail": "2019년 MMMB PAM 메인 공급사"},
        ],
        "risks": [
            {"type": "market", "description": "고객 집중도 99% 삼성전자, 사업 변화에 극도로 취약", "severity": "critical"},
            {"type": "operational", "description": "팸리스 업체로 원가 절감 여력 제한, 가격 인하 압박 대응 곤란", "severity": "high"},
            {"type": "financial", "description": "2020년 매출 70% 감소, 영업적자 37억 기록", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/290",
        "title": "씽씽 달리는 원티드랩, FI들 왜 떠났을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-01-17",
        "summary": "원티드랩 AI 채용 매칭 플랫폼으로 2021년 코스닥 상장. 매출 100% 이상 성장, 흑자 전환. 그러나 상장 전 투자자들 이탈 중.",
        "entities": [
            {"type": "company", "name": "원티드랩", "role": "HR테크 기업"},
            {"type": "person", "name": "이복기", "role": "창업자/대표"},
            {"type": "company", "name": "에이티넘성장투자조합2018", "role": "재무적 투자자"},
            {"type": "company", "name": "케이티비엔7호벤처투자조합", "role": "재무적 투자자"},
        ],
        "relations": [
            {"source": "원티드랩", "target": "크레딧잡", "type": "acquisition", "detail": "2018년 HR 정보 서비스 인수"},
            {"source": "원티드랩", "target": "커먼스페이스", "type": "acquisition", "detail": "2021년 근태관리 솔루션 인수"},
        ],
        "risks": [
            {"type": "market", "description": "초기 FI 지분 이탈로 기관투자자 신뢰도 약화 가능", "severity": "medium"},
            {"type": "operational", "description": "M&A에 올해 100억원 투자 예정, 자금 소진 우려", "severity": "medium"},
            {"type": "market", "description": "구인/구직 시장 경기 민감, 경기 악화 시 채용공고 감소 리스크", "severity": "medium"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (26차) ===\n")

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
