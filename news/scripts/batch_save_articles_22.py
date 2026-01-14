#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 22차 (에이티세미콘/대양금속/부동산PF/신종자본증권 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/391",
        "title": "SK온의 프리IPO, 성공인가 실패인가",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-09",
        "summary": "SK이노베이션에서 분할된 SK온은 글로벌 배터리 톱3 목표로 공격적 투자 진행 중이나, 실적 부진과 시장 기대치 하락으로 3-5조원 프리IPO 계획이 8000억원 수준으로 축소. 차입금 급증과 현금 소진으로 재무구조 악화.",
        "entities": [
            {"type": "company", "name": "SK온", "role": "배터리 사업 분할 회사"},
            {"type": "company", "name": "SK이노베이션", "role": "모회사"},
            {"type": "company", "name": "블루오벌SK", "role": "포드와 합작법인"},
            {"type": "company", "name": "한국투자프라이빗에쿼티", "role": "프리IPO 주관사"},
            {"type": "person", "name": "김준", "role": "SK이노베이션 부회장"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "SK온", "type": "spin-off", "detail": "2021년 10월 배터리 사업부문 분할"},
        ],
        "risks": [
            {"type": "financial", "description": "차입금이 3조9000억원으로 급증, 부채비율 178.9%", "severity": "critical"},
            {"type": "financial", "description": "현금 소진 가속화: 9개월간 1조4500억원 사용", "severity": "high"},
            {"type": "market", "description": "기업가치 평가 하락: 예상 30-50조원에서 20조원으로 축소", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/390",
        "title": "카카오뱅크 FI는 왜 지분을 팔지 않았을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-06",
        "summary": "카카오뱅크 상장 후 주가 급락에도 외국계 사모펀드 IPB.ltd와 Keto Holdings가 지분 미매각. 앵커PE 자회사 IPB.ltd가 카카오뱅크 주식 담보로 3400억원 리캡 실행, 한국투자증권 주관 유동화사채로 국내 투자자에게 판매.",
        "entities": [
            {"type": "company", "name": "카카오뱅크", "role": "상장사"},
            {"type": "company", "name": "카카오", "role": "최대주주(27.26%)"},
            {"type": "company", "name": "한국투자금융그룹", "role": "2대주주(27.26%)"},
            {"type": "company", "name": "앵커에퀴티파트너스", "role": "Pre-IPO 재무적 투자자"},
            {"type": "company", "name": "IPB.ltd", "role": "앵커PE 100% 자회사"},
            {"type": "company", "name": "한국투자증권", "role": "유동화 주관사"},
        ],
        "relations": [
            {"source": "앵커PE", "target": "IPB.ltd", "type": "subsidiary", "detail": "100% 자회사, 카카오뱅크 1064만주 인수"},
            {"source": "한국투자증권", "target": "키스플러스제칠차", "type": "securitization", "detail": "2630억원 ABSTB 발행 주관"},
        ],
        "risks": [
            {"type": "financial", "description": "카카오뱅크 주가 하락으로 담보가치 저하, IPB.ltd 차입금 상환능력 약화", "severity": "high"},
            {"type": "financial", "description": "한국투자증권 유동화사채 인수확약 2700억원, 차환 실패 시 인수 의무", "severity": "critical"},
            {"type": "market", "description": "레고랜드 사태로 유동화시장 경색, 차환발행 실패 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/389",
        "title": "이옥순 일가 인수기업에서 벌어진 일들",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-05",
        "summary": "이옥순 일가 투자 조합들이 실적 악화 기업과 상장폐지 위기 기업 인수 후 자금 유출 패턴 반복. 크로바하이텍, 네오디안테크놀로지, 대양금속 등에서 대여금 명목 자금 유출, 담보 부실, 부실 투자 사례 확인.",
        "entities": [
            {"type": "person", "name": "이옥순", "role": "실질적 최대주주"},
            {"type": "person", "name": "공갑상", "role": "이옥순 남편"},
            {"type": "person", "name": "이민혁", "role": "지엔씨파트너스 최대주주"},
            {"type": "person", "name": "김봉현", "role": "라임자산운용 주역, 기업사냥꾼"},
            {"type": "company", "name": "대양금속", "role": "최대주주 변경 기업"},
            {"type": "company", "name": "크로바하이텍", "role": "인수 후 회생절차 진입 기업"},
            {"type": "company", "name": "에스에프씨", "role": "상장폐지 기업"},
            {"type": "company", "name": "영풍제지", "role": "인수 대상 기업"},
        ],
        "relations": [
            {"source": "이옥순", "target": "대양홀딩스컴퍼니", "type": "ownership", "detail": "실질적 최대주주"},
            {"source": "대양홀딩스컴퍼니", "target": "대양금속", "type": "acquisition", "detail": "유상증자를 통해 최대주주"},
        ],
        "risks": [
            {"type": "financial", "description": "부실 투자로 대규모 손상차손 발생. Z2터치 84억원 투자 시 회사 순자산 23억원에 불과", "severity": "critical"},
            {"type": "governance", "description": "경영권 인수 후 즉시 자금 유출(대여금 명목), 크로바하이텍 144억원 불법행위 미수금", "severity": "critical"},
            {"type": "legal", "description": "횡령 및 배임 의혹. 크로바하이텍 전 경영진 감사의견 거절", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/388",
        "title": "대양금속 이전에 에스에프씨 M&A, 선수들 총집합?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-01-02",
        "summary": "태양광 백시트 업체 에스에프씨 창업자 박원기 대표가 2016년 회사 매각 후, 신설법인 태가와 재무적 투자자들이 인수. 이후 분식회계로 상장폐지, 이옥순 가족이 실질적 주인으로 추정되는 투자조합과 연계.",
        "entities": [
            {"type": "person", "name": "박원기", "role": "에스에프씨 창업자"},
            {"type": "company", "name": "에스에프씨", "role": "태양광 백시트 제조, 상장폐지"},
            {"type": "company", "name": "㈜태가", "role": "에스에프씨 인수사"},
            {"type": "person", "name": "이옥순", "role": "대양홀딩스컴퍼니 대표"},
            {"type": "company", "name": "씨엘팜", "role": "에스에프씨 유상증자 80억원 투자"},
            {"type": "company", "name": "지엔씨파트너스", "role": "이옥순 계열사"},
        ],
        "relations": [
            {"source": "태가", "target": "에스에프씨", "type": "acquisition", "detail": "자본금 4억원의 신설법인이 40.17% 지분 인수"},
            {"source": "지엔씨파트너스", "target": "태가", "type": "acquisition", "detail": "2016년 11월 태가 전량 지분 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "자본금 4억원 신설회사가 대표이사 가수금 70억원으로 인수, 자금 출처 불분명", "severity": "critical"},
            {"type": "legal", "description": "에스에프씨 2019-2020년 분식회계 혐의로 과징금 및 상장폐지, 대표이사 검찰고발", "severity": "critical"},
            {"type": "financial", "description": "에스에프씨가 100억원 전환사채 발행해 경영진 최대주주 씨엘팜에 투자, 상호출자 우려", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/387",
        "title": "공격적 M&A 나선 대양금속의 실제 주인은 누구?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-29",
        "summary": "대양금속의 최대주주 대양홀딩스컴퍼니는 이옥순씨가 96% 지분을 보유한 경영컨설팅업체. 2019년 블랙홀컴퍼니로 설립되어 영풍제지 등을 인수. 옵티머스 사건 연루자들과의 관계 드러남.",
        "entities": [
            {"type": "company", "name": "대양금속", "role": "피인수 회사"},
            {"type": "company", "name": "대양홀딩스컴퍼니", "role": "대양금속 최대주주"},
            {"type": "person", "name": "이옥순", "role": "대양홀딩스컴퍼니 96% 주주, 대표이사"},
            {"type": "person", "name": "조상종", "role": "대양금속 대표이사"},
            {"type": "company", "name": "에프앤디조합", "role": "2019년 대양금속 인수 주체"},
            {"type": "company", "name": "좋은사람들", "role": "대양금속 인수 자금 대여"},
            {"type": "person", "name": "이종현", "role": "좋은사람들 대표, 삼성전자 부회장 아들"},
        ],
        "relations": [
            {"source": "이옥순", "target": "대양홀딩스컴퍼니", "type": "ownership", "detail": "96% 지분 보유 및 대표이사"},
            {"source": "좋은사람들", "target": "대양홀딩스컴퍼니", "type": "financing", "detail": "40억원 차입금 제공"},
            {"source": "에프앤디조합", "target": "대양금속", "type": "acquisition", "detail": "2019년 973억원에 채권단 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 순환 지분 구조로 실질적 주인 파악 어려움", "severity": "high"},
            {"type": "legal", "description": "옵티머스 사기 사건 연루자(이종현)가 대양금속 자금 조달에 관여", "severity": "critical"},
            {"type": "regulatory", "description": "대장동 사건 관련자 나석규씨의 30억원 대양금속 주식 매입 의혹", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/386",
        "title": "영풍제지 매각한 숨은 최대주주, 얼마나 벌었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-26",
        "summary": "대양금속이 영풍제지를 주당 11,488원에 인수. 기준시가보다 낮은 가격. 영풍제지 실질적 주인 노성현이 창업주로부터 지분 증여받아 그로쓰제일호투자목적회사를 통해 약 850억원대 수익 창출.",
        "entities": [
            {"type": "company", "name": "영풍제지", "role": "피인수 기업"},
            {"type": "company", "name": "대양금속", "role": "인수 기업"},
            {"type": "company", "name": "그로쓰제일호투자목적회사", "role": "중간 투자 목적 법인"},
            {"type": "person", "name": "노성현", "role": "실질적 주인"},
            {"type": "person", "name": "이무진", "role": "창업주"},
        ],
        "relations": [
            {"source": "이무진", "target": "노성현", "type": "gift", "detail": "2013년 51.28% 지분을 노미정에게 증여"},
            {"source": "그로쓰제일호투자목적회사", "target": "대양금속", "type": "share_sale", "detail": "경영권 지분 1,289억원 매각"},
        ],
        "risks": [
            {"type": "governance", "description": "지분 증여와 차액거래 구조 투명성 문제", "severity": "high"},
            {"type": "market", "description": "M&A 재료로 주가 상승 후 매각, 시장 조작 가능성", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/384",
        "title": "영풍제지 인수한 대양금속의 자금출처는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-22",
        "summary": "대양금속이 약 1,300억원 투입해 영풍제지 경영권 인수했으나, 공시된 자금조달은 380억원에 불과. 920억원 상당 자금출처 불명확. 인수 후 영풍제지가 역으로 대양금속에 170억원 전환사채 인수.",
        "entities": [
            {"type": "company", "name": "대양금속", "role": "인수자"},
            {"type": "company", "name": "영풍제지", "role": "인수대상"},
            {"type": "company", "name": "LJH투자1호조합", "role": "자금 제공자"},
            {"type": "company", "name": "조광ILI", "role": "무담보 차입금 제공자"},
            {"type": "company", "name": "앤디포스", "role": "전환사채 인수자"},
            {"type": "person", "name": "김우동", "role": "조광ILI, 대유, 앤디포스 실질 지배인"},
        ],
        "relations": [
            {"source": "대양금속", "target": "영풍제지", "type": "acquisition", "detail": "1,289억원에 50.55% 경영권 지분 취득"},
            {"source": "영풍제지", "target": "대양금속", "type": "financing", "detail": "170억원 규모 전환사채 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "1,300억원 중 공시된 자금조달 380억원, 920억원 자금출처 불명확", "severity": "critical"},
            {"type": "governance", "description": "사실상 무자본 M&A, 60억원 자기자금과 1,240억원 차입금 구성", "severity": "high"},
            {"type": "operational", "description": "인수 후 영풍제지가 역으로 인수자에게 자금 공급, 인수목적 실질성 의문", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/383",
        "title": "인적분할 기업, 왜 갑자기 늘었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-19",
        "summary": "2022년 인적분할 결의 기업 13곳으로 12년 만에 최다. 물적분할에 대한 개인투자자 여론 악화 대신 지주회사 전환을 위한 세제 이연 혜택이 주요 원인.",
        "entities": [
            {"type": "company", "name": "이수화학", "role": "인적분할 공시 기업"},
            {"type": "company", "name": "OCI", "role": "인적분할 공시 기업"},
            {"type": "company", "name": "현대그린푸드", "role": "인적분할 공시 기업"},
            {"type": "company", "name": "현대백화점", "role": "인적분할 공시 기업"},
            {"type": "company", "name": "LG화학", "role": "물적분할 사례"},
        ],
        "relations": [],
        "risks": [
            {"type": "governance", "description": "인적분할로 지주회사 체제 전환 시 오너 일가의 소수 지분으로 계열사 전체 지배 가능", "severity": "high"},
            {"type": "market", "description": "분할비율이 시장 기업가치 미반영으로 존속/신설회사 주가 차별화", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/382",
        "title": "리더스기술투자 최대주주 바뀔까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-15",
        "summary": "리더스기술투자는 115억원 규모의 제3자배정 유상증자 추진 중. 어센딩플로우조합 인수로 경영 구조 변화 임박. 에이티세미콘이 최대주주이나 신규 주주 지분 확대로 자회사 지위 변경 가능성.",
        "entities": [
            {"type": "company", "name": "리더스기술투자", "role": "대상회사"},
            {"type": "company", "name": "에이티세미콘", "role": "현재 최대주주"},
            {"type": "company", "name": "어센딩플로우조합", "role": "유상증자 인수자"},
            {"type": "person", "name": "김형준", "role": "에이티세미콘 대표"},
            {"type": "person", "name": "김환", "role": "어센딩플로우조합 출자자(60%)"},
        ],
        "relations": [
            {"source": "에이티세미콘", "target": "리더스기술투자", "type": "ownership", "detail": "지분율 18.04%, 전환사채 포함 25.49%"},
            {"source": "어센딩플로우조합", "target": "리더스기술투자", "type": "acquisition", "detail": "115억원 유상증자 2,300만주 인수 예정"},
        ],
        "risks": [
            {"type": "governance", "description": "경영권 변화로 회사 전략 및 지배구조 변동 가능성", "severity": "high"},
            {"type": "financial", "description": "외부감사인이 대규모 적자와 낮은 유동비율로 계속기업 존속능력에 의문 제기", "severity": "critical"},
            {"type": "financial", "description": "영업권 32억원 적정성 문제, 핵심감사사항 지정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/381",
        "title": "더블유아이와 에이티세미콘의 겹치는 행보, 우연일까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-12",
        "summary": "에이티세미콘과 더블유아이 경영진 김형준, 변익성이 유사한 패턴으로 자금 유입받고 신규 사업으로 전환. 양사 모두 기존 사업 매각하고 2차전지 사업 진출 선언, 의심스러운 구조적 유사성.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "반도체 패키징 및 2차전지 사업"},
            {"type": "company", "name": "더블유아이", "role": "휴대폰 액세서리 판매 후 어반리튬으로 변경"},
            {"type": "company", "name": "더에이치테크", "role": "에이티세미콘 최대주주"},
            {"type": "company", "name": "리튬인사이트", "role": "더블유아이 최대주주"},
            {"type": "person", "name": "김형준", "role": "에이티세미콘 대표"},
            {"type": "person", "name": "변익성", "role": "더블유아이 대표"},
        ],
        "relations": [
            {"source": "김형준", "target": "변익성", "type": "collaboration", "detail": "에이티테크놀러지에서 함께 경영, 유사한 자금 유입 및 사업 전환 패턴"},
            {"source": "리튬인사이트", "target": "더블유아이", "type": "investment", "detail": "300억원 규모 무자본 M&A로 신주 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "리튬인사이트는 자본금 미만 규모로 300억원 이상 무자본 조달 의심", "severity": "critical"},
            {"type": "financial", "description": "더에이치테크의 32억원 투자 전액 차입금, 에이티세미콘으로부터 15억원 추가 차입", "severity": "high"},
            {"type": "operational", "description": "두 회사 모두 기존 본업 완전 폐기 후 2차전지 사업 급속 전환, 사업 연관성 부재", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/380",
        "title": "에이티세미콘에 집결한 수상한 자금들",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-08",
        "summary": "에이티세미콘의 2000억원 자금조달 계획 연기, 자기 전환사채 재매각과 복잡한 자금 흐름. 아임존과 한수지가 중심이 되어 전환사채 매입·매도, 주식전환 차익 취득. 한수지는 스마트솔루션즈, 이노시스 등 여러 코스닥 상장사에서 유사 투자활동.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "전환사채 발행사"},
            {"type": "person", "name": "김형준", "role": "에이티세미콘 대표"},
            {"type": "company", "name": "㈜아임존", "role": "전환사채 매입·매도 중개"},
            {"type": "person", "name": "한수지", "role": "아임존 100% 주주 및 대표"},
            {"type": "company", "name": "스마트솔루션즈", "role": "경영권 변동 코스닥 상장사"},
            {"type": "company", "name": "이노시스", "role": "전환사채 발행 코스닥 상장사"},
            {"type": "company", "name": "파라텍", "role": "에이티세미콘 전환사채 인수"},
        ],
        "relations": [
            {"source": "한수지", "target": "아임존", "type": "ownership", "detail": "100% 주주, 약 5000만원 자본금 운영"},
            {"source": "아임존", "target": "에이티세미콘", "type": "transaction", "detail": "3월 300억원 전환사채 매입, 7월 17회차 10억원 추가 매입"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 투자조합 구조로 실질적 주인 파악 어려움", "severity": "high"},
            {"type": "legal", "description": "서류상 유령회사 제이앤리더스 등 실체 불명확 법인 연루", "severity": "critical"},
            {"type": "market", "description": "스마트솔루션즈 상장폐지 처지로 개인투자자 10만명 피해 발생", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/378",
        "title": "리더스기술투자에 남은 KH필룩스의 잔재",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-05",
        "summary": "리더스기술투자 투자 포트폴리오 분석. 경영권 인수 후에도 과거 KH필룩스 그룹과 연관성 지속. 전환사채와 신주인수권부사채 투자 주를 이루며, 관련 인물들 인사 이동과 복잡한 지분 구조.",
        "entities": [
            {"type": "company", "name": "리더스기술투자", "role": "주요 분석 대상 투자사"},
            {"type": "company", "name": "KH필룩스", "role": "과거 모회사 그룹"},
            {"type": "company", "name": "에이티세미콘", "role": "현재 최대주주"},
            {"type": "company", "name": "이엔플러스", "role": "과거 투자처"},
            {"type": "company", "name": "에이스바이오메드", "role": "단일기업 최대 투자처(80억원)"},
            {"type": "company", "name": "릭스솔루션", "role": "분쟁 관련 투자처, 현 광무"},
            {"type": "person", "name": "안영용", "role": "이엔플러스 대표, 전 필룩스 이사"},
        ],
        "relations": [
            {"source": "리더스기술투자", "target": "KH필룩스", "type": "historical", "detail": "경영권 인수 후에도 과거 관계자 및 투자처와 연관성 지속"},
        ],
        "risks": [
            {"type": "governance", "description": "경영권 변화 후에도 과거 KH필룩스 관련 인물들이 투자 대상사에서 핵심 역할", "severity": "high"},
            {"type": "financial", "description": "에이스바이오메드 신주인수권부사채 80억원 투자, 장부가 5억원으로 대규모 손상차손", "severity": "critical"},
            {"type": "legal", "description": "릭스솔루션 관련 주식담보대출 상환 거부 및 담보 주식 탈취 의혹, 특정경제범죄 가중처벌법 위반 고소", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/377",
        "title": "리더스기술투자의 실적 쇼크, 모회사 탓?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-12-01",
        "summary": "에이티세미콘 자회사 리더스기술투자가 매출액 급감(전년동기 대비 1/3 수준)으로 심각한 실적 부진. 모회사 유동성 문제와 구조조정이 자금조달 축소와 투자 위축으로 연결, 결손금 증가로 자본 잠식 진행.",
        "entities": [
            {"type": "company", "name": "리더스기술투자", "role": "에이티세미콘 자회사"},
            {"type": "company", "name": "에이티세미콘", "role": "모회사"},
            {"type": "person", "name": "김형준", "role": "리더스기술투자 대표"},
            {"type": "company", "name": "MG손해보험", "role": "부실기업 지정 대상"},
        ],
        "relations": [
            {"source": "에이티세미콘", "target": "리더스기술투자", "type": "ownership", "detail": "최대 자회사이자 연결 대상 자회사"},
            {"source": "리더스기술투자", "target": "MG손해보험", "type": "investment", "detail": "200억원을 JC어슈어런스 제2호 PEF에 출자"},
        ],
        "risks": [
            {"type": "financial", "description": "결손금 859억원 누적, 자본 잠식률 20~39% 진행, 대규모 자본확충 시급", "severity": "critical"},
            {"type": "operational", "description": "매출액 급감, 새로운 투자처 발굴 부진, 벤처캐피탈로서 경쟁력 약화", "severity": "critical"},
            {"type": "governance", "description": "모회사 에이티세미콘의 유동성 문제가 자금조달 제약으로 작용", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/376",
        "title": "에이티세미콘, 본업 매각은 빙산의 일각?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-11-28",
        "summary": "반도체 후공정업체 에이티세미콘이 본업인 패키징사업을 에이팩트에 720억원에 매각하고 2차전지사업으로 전환. 2,400억원 규모 대규모 자금조달과 함께 진행된 결정으로 신사업 성공 여부가 회사 미래 결정.",
        "entities": [
            {"type": "company", "name": "에이티세미콘", "role": "주요 대상사"},
            {"type": "company", "name": "에이팩트", "role": "패키징사업 인수자"},
            {"type": "person", "name": "김형준", "role": "에이티세미콘 대표"},
            {"type": "company", "name": "리더스기술투자", "role": "에이티세미콘 자회사(340억원 인수)"},
            {"type": "company", "name": "지피클럽", "role": "2대주주(75억원 유상증자)"},
        ],
        "relations": [
            {"source": "에이티세미콘", "target": "에이팩트", "type": "asset_sale", "detail": "패키징사업 매각(720억원)"},
            {"source": "김형준", "target": "에이티세미콘", "type": "control", "detail": "더에이티테크 보유분 포함 12.23% 지분 보유"},
        ],
        "risks": [
            {"type": "operational", "description": "본업 완전 매각 후 신사업 성공까지 사업 공백 불가피, 2차전지 진출 성공 미보장", "severity": "critical"},
            {"type": "financial", "description": "4년 연속 적자, 2022년 3분기 순손실 439억원, 리더스기술투자 순손실 198억원", "severity": "critical"},
            {"type": "governance", "description": "2,300억원 전환사채·신주인수권부사채 인수자 잠재적 의결권이 경영권 향방 결정", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/375",
        "title": "일반기업의 자본같지 않은 자본, 신종자본증권",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-11-24",
        "summary": "신종자본증권은 자본과 부채 특성 동시 보유. 일반기업이 2012년부터 발행 시작. 회계상 자본 분류되나 콜옵션 행사로 단기 채권 전환 특징. 투자자들은 구조 위험성 인식 필요.",
        "entities": [
            {"type": "company", "name": "두산인프라코어", "role": "신종자본증권 논란 중심사"},
            {"type": "company", "name": "CJ제일제당", "role": "일반기업 최초 발행사"},
            {"type": "company", "name": "대한항공", "role": "가장 많은 신종자본증권 발행"},
            {"type": "company", "name": "제주항공", "role": "코로나 중 대규모 발행사"},
        ],
        "relations": [
            {"source": "두산인프라코어", "target": "신종자본증권", "type": "issuance", "detail": "2012년 5억 달러 외화 신종자본증권 공모 발행"},
            {"source": "대한항공", "target": "신종자본증권", "type": "repeated_issuance", "detail": "2013년부터 2020년까지 거의 매년 발행, 2-3년 단위 차환"},
        ],
        "risks": [
            {"type": "financial", "description": "회계상 자본이나 실질 만기는 콜옵션 행사 시점, 조기상환 시 재무구조 급격히 악화 가능", "severity": "critical"},
            {"type": "governance", "description": "국내 일반기업 신종자본증권은 기관투자가 대상 사모로 발행, 공시 부족", "severity": "high"},
            {"type": "market", "description": "자본잠식 기업들이 신종자본증권으로 재무구조 개선 위장, 투자자 판단 오류 유발", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/374",
        "title": "신종자본증권 콜옵션 강제 행사, 시장의 관례로 인정해야 하나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-11-21",
        "summary": "흥국생명이 5억 달러 외화 신종자본증권 콜옵션 행사 연기 후 시장 압력으로 결국 조기상환 결정. 2009년 우리은행 이후 처음, 형식적 만기 30년 신종자본증권이 실질적으로 5년마다 상환되는 관례 조명.",
        "entities": [
            {"type": "company", "name": "흥국생명", "role": "신종자본증권 발행사"},
            {"type": "company", "name": "우리은행", "role": "2009년 후순위채 콜옵션 미행사 선례"},
        ],
        "relations": [
            {"source": "흥국생명", "target": "4개 은행", "type": "financing", "detail": "환매조건부채권(RP) 4000억원 매입 합의"},
        ],
        "risks": [
            {"type": "regulatory", "description": "신종자본증권 자본 인정 기준이 실제 운영 관례와 불일치, 바젤위원회 권고 미충족 가능성", "severity": "high"},
            {"type": "market", "description": "흥국생명 콜옵션 미행사가 국내 금융기관 외화 조달에 부정적 영향 우려", "severity": "high"},
            {"type": "financial", "description": "보험사들의 RBC가 150% 근처, 자본확충 시급", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/373",
        "title": "흥국생명이 외화유동성 위기 방아쇠 당겼나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-11-17",
        "summary": "흥국생명의 외화 신종자본증권 콜옵션 미행사가 2009년 우리은행 사례와 비교. 현재 외화유동성 상황은 당시와 다름. 국내 은행들 외화 LCR 100% 초과, 순대외채무 감소로 즉시적 위기 발전 가능성 낮음.",
        "entities": [
            {"type": "company", "name": "흥국생명", "role": "외화 신종자본증권 콜옵션 미행사"},
            {"type": "company", "name": "우리은행", "role": "2009년 외화 후순위채 콜옵션 미행사 선례"},
        ],
        "relations": [
            {"source": "흥국생명", "target": "우리은행", "type": "comparison", "detail": "2009년 외화채 콜옵션 미행사 사건과 비교"},
        ],
        "risks": [
            {"type": "financial", "description": "외화 유출 증가로 국내 금융기관 달러 공급 경색 가능성", "severity": "medium"},
            {"type": "market", "description": "부동산 PF 시장 경색이 금융시스템 전반으로 확대 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/372",
        "title": "PF ABCP 등 30조원, 3개월내 만기도래",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-11-14",
        "summary": "국내 부동산PF 유동화시장의 ABCP와 ABSTB 약 30조원이 2022년 11월부터 2023년 1월까지 만기 도래. 대부분 차환발행 필요, 금리 상승과 주택가격 하락으로 차환 실패 위험 증가.",
        "entities": [
            {"type": "company", "name": "현대건설", "role": "대형 건설사, 신용보강 제공"},
            {"type": "company", "name": "GS건설", "role": "대형 건설사, 신용보강 제공"},
            {"type": "company", "name": "롯데건설", "role": "신용보강 제공자"},
            {"type": "company", "name": "HDC현대산업개발", "role": "신용보강 제공자"},
        ],
        "relations": [
            {"source": "부동산PF 대출채권", "target": "ABCP/ABSTB", "type": "securitization", "detail": "PF대출채권 유동화하여 단기 증권 발행"},
        ],
        "risks": [
            {"type": "market", "description": "약 30조원의 ABCP/ABSTB가 3개월 내 만기도래, 차환발행 실패 위험", "severity": "critical"},
            {"type": "financial", "description": "금리 급등과 주택가격 하락으로 미분양 악화 시 차환 불가 연쇄 위험", "severity": "high"},
            {"type": "financial", "description": "대형 건설사 부도 시 금융시장에 미치는 영향 광범위", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/371",
        "title": "둔촌주공 재개발사업 PF리스크는 해소된 걸까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-11-10",
        "summary": "둔촌주공 재개발사업은 ABCP 차환 실패로 채권시장안정펀드 지원. 내년 1월 일반분양 성과에 따라 시공사들 유동성 위험 존재. 현대건설, 롯데건설, HDC현대산업개발, 대우건설이 연대보증.",
        "entities": [
            {"type": "company", "name": "현대건설", "role": "시공사 및 연대보증사"},
            {"type": "company", "name": "롯데건설", "role": "시공사 및 연대보증사"},
            {"type": "company", "name": "HDC현대산업개발", "role": "시공사 및 연대보증사"},
            {"type": "company", "name": "대우건설", "role": "시공사 및 연대보증사"},
            {"type": "company", "name": "KB증권", "role": "주관 증권사"},
        ],
        "relations": [
            {"source": "둔촌주공재개발조합", "target": "현대건설", "type": "guarantee", "detail": "ABCP 차입금 상환 보증"},
            {"source": "채권시장안정펀드", "target": "둔촌주공재개발조합", "type": "support", "detail": "ABCP 차환발행 지원"},
        ],
        "risks": [
            {"type": "financial", "description": "2023년 1월 일반분양 저조 시 시공사들의 ABCP 상환의무 및 공사비 미수금 동시 발생", "severity": "high"},
            {"type": "market", "description": "부동산 시장 약세로 자금시장 경색 지속 시 ABCP 재차환 실패 가능성", "severity": "high"},
            {"type": "financial", "description": "대구, 경상도 지역 미착공 사업장의 ABCP 동시다발 차환실패 연쇄 위험", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/370",
        "title": "부동산PF 위험이 높은 지역은 어디?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2022-11-07",
        "summary": "건설업계 부동산PF 위험 증가, 미분양 많은 지역에서 사고 가능성 높음. 대구, 울산, 포항, 경주 등이 낮은 분양율과 미분양 증가로 위험지역 분류.",
        "entities": [
            {"type": "company", "name": "롯데건설", "role": "부동산PF 위험노출 건설사"},
            {"type": "company", "name": "강원중도개발공사", "role": "레고랜드 개발사"},
        ],
        "relations": [
            {"source": "강원중도개발공사", "target": "건설사", "type": "risk_transfer", "detail": "레고랜드 회생신청으로 건설사 PF 우발채무 현실화 위험"},
        ],
        "risks": [
            {"type": "financial", "description": "미착공 및 저분양 사업장의 ABCP 차환발행 실패 위험", "severity": "critical"},
            {"type": "operational", "description": "건설사의 지속적 자금 투입 의무로 인한 유동성 리스크", "severity": "high"},
            {"type": "market", "description": "대구(18%), 울산(35.4%), 경북(71.1%), 강원도(64.6%) 등 저분양율 지역 확산", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (22차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}... - {result.get('error', 'Unknown error')}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
