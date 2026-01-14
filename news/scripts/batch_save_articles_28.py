#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 28차 (중앙디앤엠/상지카일룸/SK그룹 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/269",
        "title": "중앙디앤엠의 과거에 등장하는 놀라운 이름들",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-11-03",
        "summary": "중앙디앤엠의 경영권 변화 과정에서 인터림스, 제이엔케이 등 여러 투자조합이 최대주주로 등장. 임호, 서영우 등이 옵티머스펀드 사기와 라임자산운용 사태와 연루.",
        "entities": [
            {"type": "company", "name": "중앙디앤엠", "role": "피인수 대상기업"},
            {"type": "company", "name": "인터림스", "role": "최대주주(2015-2016)"},
            {"type": "company", "name": "제이엔케이인베스트먼트", "role": "최대주주(2016년 이후)"},
            {"type": "company", "name": "옵티머스자산운용", "role": "펀드사기 관련회사"},
            {"type": "person", "name": "임호", "role": "인터림스 관련 핵심인물"},
            {"type": "person", "name": "한상엽", "role": "기업사냥꾼"},
            {"type": "person", "name": "김봉현", "role": "라임자산운용 주인공"},
        ],
        "relations": [
            {"source": "임호", "target": "인터림스", "type": "지분보유", "detail": "35% 지분 보유"},
            {"source": "한상엽", "target": "옵티머스", "type": "연루", "detail": "옵티머스 홍동진과 관계"},
        ],
        "risks": [
            {"type": "governance", "description": "명목상 대표와 실제 의사결정자의 불일치", "severity": "high"},
            {"type": "legal", "description": "핵심인물들이 옵티머스펀드 사기, 주가조작 등 주요 사건과 연루", "severity": "critical"},
            {"type": "financial", "description": "인터림스코리아가 아이비팜홀딩스에 91억원 대여금 제공", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/268",
        "title": "자꾸만 겹치는 중앙디앤엠과 상지카일룸의 과거",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-10-27",
        "summary": "중앙디앤엠과 상지카일룸은 유상증자, 전환사채, Arena Global SK SPV 등 여러 접점 존재. 2019년 바른테크놀로지 인수부터 복잡한 지분 관계.",
        "entities": [
            {"type": "company", "name": "중앙디앤엠", "role": "상지카일룸 최대주주"},
            {"type": "company", "name": "상지카일룸", "role": "경영권 이전 대상사"},
            {"type": "company", "name": "Arena Global SK SPV", "role": "미국 투자회사"},
            {"type": "company", "name": "바른테크놀로지", "role": "중앙디앤엠 계열사"},
            {"type": "person", "name": "한종희", "role": "상지카일룸 회장"},
            {"type": "person", "name": "김태섭", "role": "바른전자 전 소유자"},
        ],
        "relations": [
            {"source": "중앙디앤엠", "target": "상지카일룸", "type": "경영권 인수", "detail": "160억원 유상증자 참여"},
            {"source": "Arena Global SK SPV", "target": "중앙디앤엠", "type": "투자", "detail": "전환사채 97억원 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "다층 구조로 실질 지배인이 불투명", "severity": "critical"},
            {"type": "legal", "description": "김태섭 바른전자 주가조작 혐의 구속", "severity": "critical"},
            {"type": "financial", "description": "미국 회사들의 자본금 출처 불명확", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/267",
        "title": "중앙디앤엠과 상지카일룸의 접점, 바른테크놀로지",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-11-01",
        "summary": "중앙디앤엠과 상지카일룸이 바른전자, 바른테크놀로지 인수를 통해 필룩스그룹과 얽혀있음. 경영권이 엔비알컴퍼니로 이동 후 심각한 분쟁 진행.",
        "entities": [
            {"type": "company", "name": "중앙디앤엠", "role": "바른테크놀로지 인수·매각"},
            {"type": "company", "name": "상지카일룸", "role": "바른전자 인수 주도"},
            {"type": "company", "name": "필룩스그룹", "role": "배경 투자자"},
            {"type": "company", "name": "엔비알컴퍼니", "role": "현 최대주주"},
            {"type": "company", "name": "리더스기술투자", "role": "반대매매 강행"},
            {"type": "person", "name": "배상윤", "role": "필룩스그룹 회장"},
        ],
        "relations": [
            {"source": "중앙디앤엠", "target": "바른테크놀로지", "type": "인수-매각", "detail": "주당 715원→600원 손실 매각"},
            {"source": "엔비알컴퍼니", "target": "리더스기술투자", "type": "채무-담보 분쟁", "detail": "반대매매로 지분 회수"},
        ],
        "risks": [
            {"type": "governance", "description": "경영권 이동 후 심각한 분쟁 발생", "severity": "critical"},
            {"type": "financial", "description": "담보 지분이 반대매매로 절반 이상 상실", "severity": "critical"},
            {"type": "legal", "description": "진흙탕 경영권 분쟁, 기업사냥꾼 의혹", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/266",
        "title": "중앙디앤엠과 상지카일룸의 상부상조",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-10-25",
        "summary": "무자본 M&A로 경영권이 여러 차례 바뀐 중앙디앤엠과 상지카일룸이 유상증자와 전환사채를 통해 상호 지원.",
        "entities": [
            {"type": "company", "name": "중앙디앤엠", "role": "주요 대상 기업"},
            {"type": "company", "name": "상지카일룸", "role": "주요 대상 기업"},
            {"type": "company", "name": "에이치에프네트웍스", "role": "중앙디앤엠 현 최대주주"},
            {"type": "company", "name": "바른테크놀로지", "role": "중앙디앤엠 피투자사"},
            {"type": "person", "name": "윤선애", "role": "에이치에프네트웍스 출자자"},
        ],
        "relations": [
            {"source": "중앙디앤엠", "target": "상지카일룸", "type": "투자", "detail": "160억원 투자로 최대주주"},
            {"source": "에이치에프네트웍스", "target": "중앙디앤엠", "type": "경영권인수", "detail": "62억원 출자"},
        ],
        "risks": [
            {"type": "governance", "description": "무자본 M&A를 통한 반복적 경영권 교체", "severity": "high"},
            {"type": "financial", "description": "중앙디앤엠 급격한 매출 감소, 상지카일룸 174억원 순손실", "severity": "critical"},
            {"type": "legal", "description": "바른전자, 스타모빌리티 주가조작 및 라임사태 연루 이력", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/265",
        "title": "상지카일룸의 신동걸 시대를 함께 한 조력자들",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-10-21",
        "summary": "상지카일룸 인수 과정에서 신동걸 회장을 지원한 투자조합 및 관련 기업들의 복잡한 지분 구조와 자금 흐름 분석.",
        "entities": [
            {"type": "person", "name": "신동걸", "role": "상지카일룸 대표"},
            {"type": "person", "name": "최기보", "role": "상지카일룸 전 대표"},
            {"type": "person", "name": "한종희", "role": "필룩스 대표"},
            {"type": "company", "name": "스카디홀딩스", "role": "유상증자 관리 투자사"},
            {"type": "company", "name": "카일룸파트너스", "role": "전환사채 담당"},
            {"type": "company", "name": "씨지아이홀딩스", "role": "최대주주 인수자"},
        ],
        "relations": [
            {"source": "신동걸", "target": "씨지아이홀딩스", "type": "소유", "detail": "상지카일룸 인수 주도"},
            {"source": "씨지아이홀딩스", "target": "상지카일룸", "type": "최대주주", "detail": "75억원 유상증자 참여"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 다층 지분 구조로 실제 경영진 파악 어려움", "severity": "high"},
            {"type": "financial", "description": "1,208억원 전환사채로 과도한 부채, 주가 920원까지 하락", "severity": "critical"},
            {"type": "regulatory", "description": "저축은행 담보 설정 및 특수목적법인 활용으로 투명성 결여", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/264",
        "title": "상지카일룸과 기가레인의 숨은 거래",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-10-18",
        "summary": "르네코(상지카일룸)가 신동걸씨 주도로 복수 펀드와 상장사를 통해 순환출자 구조 형성. 실질 투자자 은폐 의혹.",
        "entities": [
            {"type": "company", "name": "상지카일룸", "role": "중심 회사"},
            {"type": "company", "name": "기가레인", "role": "상장사 투자 대상"},
            {"type": "company", "name": "케플러밸류파트너스", "role": "펀드"},
            {"type": "person", "name": "신동걸", "role": "주요 의사결정자"},
            {"type": "person", "name": "김현제", "role": "기가레인 회장"},
        ],
        "relations": [
            {"source": "상지카일룸", "target": "케플러밸류파트너스", "type": "지배", "detail": "지분 51% 보유 후 판매"},
            {"source": "케플러밸류파트너스", "target": "기가레인", "type": "지배", "detail": "경영권 인수 및 유상증자 참여"},
        ],
        "risks": [
            {"type": "governance", "description": "다층 펀드 구조를 통한 실질 소유자 은폐", "severity": "critical"},
            {"type": "financial", "description": "차입금 의존 구조로 자본 실질성 부족", "severity": "high"},
            {"type": "legal", "description": "순환출자 및 증여세 회피 의혹", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/263",
        "title": "상지카일룸, 인수에서 매각까지(2)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-10-14",
        "summary": "신동걸 대표의 르네코 인수부터 상지카일룸 경영권 변화까지의 무자본 M&A 과정. 저축은행 고금리 담보 차입 구조.",
        "entities": [
            {"type": "person", "name": "신동걸", "role": "무자본 M&A 전문가"},
            {"type": "person", "name": "김재성", "role": "중앙디앤엠 전 최대주주"},
            {"type": "company", "name": "더슈퍼클래스젯", "role": "인수전용 투자사"},
            {"type": "company", "name": "씨지아이홀딩스", "role": "상지카일룸 최대주주"},
            {"type": "company", "name": "상상인저축은행", "role": "고금리 담보 차입처"},
        ],
        "relations": [
            {"source": "신동걸", "target": "더슈퍼클래스젯", "type": "경영", "detail": "42억원 차입으로 르네코 인수"},
            {"source": "씨지아이홀딩스", "target": "상상인저축은행", "type": "차입", "detail": "107.5억원 대출, 금리 19%"},
        ],
        "risks": [
            {"type": "financial", "description": "담보유지비율 200%로 주가 하락시 연쇄 담보권 실행 위험", "severity": "critical"},
            {"type": "financial", "description": "상상인저축은행 19% 초고금리 차입", "severity": "high"},
            {"type": "legal", "description": "비에이치100이 신동걸 측을 사기 혐의로 고소", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/262",
        "title": "상지카일룸, 인수에서 매각까지(1)",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-10-07",
        "summary": "필룩스의 상지건설 인수부터 포워드컴퍼니스의 상지카일룸 전환까지 복잡한 지분 이동 과정.",
        "entities": [
            {"type": "company", "name": "상지카일룸", "role": "분석 대상 기업"},
            {"type": "company", "name": "필룩스", "role": "상지건설 인수 주체"},
            {"type": "company", "name": "포워드컴퍼니스", "role": "상지카일룸으로 개명"},
            {"type": "person", "name": "한종희", "role": "상지건설 창립멤버"},
            {"type": "person", "name": "신동걸", "role": "르네코 대표"},
        ],
        "relations": [
            {"source": "필룩스", "target": "상지건설", "type": "인수", "detail": "2016년 7월 75.88% 지분 인수"},
            {"source": "신동걸", "target": "르네코", "type": "경영권", "detail": "씨지아이홀딩스 거쳐 간접 지배"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 계층적 지분 구조로 실제 경영권자 파악 어려움", "severity": "high"},
            {"type": "financial", "description": "스카디홀딩스 유상증자 자금 대부분 차입금, 3년째 순손실", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/261",
        "title": "중앙디앤엠과 상지카일룸의 얽히고 설킨 관계",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-09-30",
        "summary": "중앙디앤엠이 상지카일룸 160억원 유상증자에 참여해 최대주주. 제이앤에스컴퍼니의 김재성 등으로 연결된 복잡한 자금흐름.",
        "entities": [
            {"type": "company", "name": "중앙디앤엠", "role": "상지카일룸 최대주주"},
            {"type": "company", "name": "상지카일룸", "role": "고급 빌라 건설사"},
            {"type": "company", "name": "제이앤에스컴퍼니", "role": "중앙디앤엠 전 최대주주"},
            {"type": "company", "name": "일리아스", "role": "전환사채 인수 회사"},
            {"type": "person", "name": "김재성", "role": "제이앤에스컴퍼니 최대주주"},
            {"type": "person", "name": "한종희", "role": "상지건설 2대주주"},
        ],
        "relations": [
            {"source": "김재성", "target": "일리아스", "type": "소유", "detail": "500만원 출자로 설립"},
            {"source": "일리아스", "target": "중앙디앤엠", "type": "투자", "detail": "88억원 CB 인수 후 매도"},
        ],
        "risks": [
            {"type": "governance", "description": "최대주주 변경 직전 GS건설과 175억원 사업 협약, 경영진 교체로 추진 의도 불명확", "severity": "high"},
            {"type": "financial", "description": "중앙디앤엠 자본잠식, 감사인 검토의견 거절 상태로 생사기로", "severity": "critical"},
            {"type": "regulatory", "description": "일리아스가 88억원 전액 외부차입으로 CB 인수, 투명성 문제", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/260",
        "title": "SK㈜, 배당금 수입 늘려야 하지 않을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-09-23",
        "summary": "SK㈜가 SK머티리얼즈 홀딩스를 합병하여 첨단소재 분야 투자 활성화. 성숙 사업 중심의 배당금 극대화 전략 필요.",
        "entities": [
            {"type": "company", "name": "SK㈜", "role": "지주회사"},
            {"type": "company", "name": "SK머티리얼즈", "role": "첨단소재 투자사업"},
            {"type": "company", "name": "SK텔레콤", "role": "배당금 제공자"},
            {"type": "company", "name": "SK바이오팜", "role": "신약 개발 회사"},
        ],
        "relations": [
            {"source": "SK㈜", "target": "SK머티리얼즈", "type": "합병", "detail": "손자회사에서 자회사로 지위 변경"},
            {"source": "SK텔레콤", "target": "SK㈜", "type": "배당금 지급", "detail": "연간 약 7,000억원"},
        ],
        "risks": [
            {"type": "financial", "description": "SK바이오팜 현금흐름 적자 지속, SK㈜ 투자 부담 증가", "severity": "high"},
            {"type": "operational", "description": "SK머티리얼즈 차입금 부담 과다, 대규모 투자 재원 조달 어려움", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/259",
        "title": "자사주 매입을 이렇게까지? SK머티리얼즈의 이상한 선택",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-09-16",
        "summary": "SK머티리얼즈는 5년간 3,786억원 순이익에도 자본금 895억원 감소. 3,184억원 자사주 매입으로 6,000억원 차입금 증가.",
        "entities": [
            {"type": "company", "name": "SK머티리얼즈", "role": "피분석 기업"},
            {"type": "company", "name": "SK그룹", "role": "인수 기업"},
        ],
        "relations": [
            {"source": "SK그룹", "target": "SK머티리얼즈", "type": "인수", "detail": "2016년 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "부채비율 63%(2016년)에서 292%(2021년 6월)로 급증", "severity": "critical"},
            {"type": "financial", "description": "이자지급액 47억원→160억원으로 3배 이상 증가", "severity": "high"},
            {"type": "operational", "description": "영업활동 현금흐름 6,600억원 대비 1조 2,524억원 지출", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/258",
        "title": "SK머티리얼즈 자회사들, 위상이 달라진다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-09-13",
        "summary": "SK㈜가 SK머티리얼즈를 분할·합병하여 자회사들이 손자회사에서 직속 자회사로 승격. 소재사업 전략 재편.",
        "entities": [
            {"type": "company", "name": "SK㈜", "role": "그룹 지주회사"},
            {"type": "company", "name": "SK머티리얼즈", "role": "반도체·디스플레이 소재"},
            {"type": "company", "name": "SK머티리얼즈에어플러스", "role": "산업가스 자회사"},
            {"type": "company", "name": "SK트리켐", "role": "전구체 자회사"},
        ],
        "relations": [
            {"source": "SK㈜", "target": "SK머티리얼즈", "type": "분할·합병", "detail": "투자부문과 사업부문으로 분할"},
        ],
        "risks": [
            {"type": "financial", "description": "SK머티리얼즈 현금흐름 이상의 투자로 재무구조 악화", "severity": "high"},
            {"type": "operational", "description": "산업가스·전구체 자회사들 대규모 투자 역량 부족", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/257",
        "title": "SK머티리얼즈 합병이 불가피한 이유",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-09-09",
        "summary": "SK㈜가 SK머티리얼즈를 물적분할 후 100% 자회사로 전환. 재무적 어려움과 대규모 투자 필요성이 원인.",
        "entities": [
            {"type": "company", "name": "SK머티리얼즈", "role": "반도체·디스플레이 소재"},
            {"type": "company", "name": "SK㈜", "role": "그룹 지주회사"},
            {"type": "company", "name": "SKC", "role": "배터리 소재 담당"},
            {"type": "person", "name": "장동현", "role": "SK㈜ 사장"},
        ],
        "relations": [
            {"source": "SK㈜", "target": "SK머티리얼즈", "type": "소유", "detail": "49.1%→100% 자회사로 전환"},
        ],
        "risks": [
            {"type": "financial", "description": "부채비율 300% 초과, 차입금의존도 65%, 1년 내 만기도래분 58%", "severity": "critical"},
            {"type": "operational", "description": "연간 현금흐름 2000억원대로 대규모 투자 능력 부족", "severity": "high"},
            {"type": "governance", "description": "상장폐지로 소수주주 주식유동성 및 영향력 제한", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/256",
        "title": "SK하이닉스 가치 무시된 SK텔레콤 분할비율",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-09-06",
        "summary": "SK텔레콤 인적분할 시 분할비율이 SK하이닉스를 원가법으로 평가하여 왜곡. 지분법 평가 시 분할비율 크게 변경.",
        "entities": [
            {"type": "company", "name": "SK텔레콤", "role": "분할 존속회사"},
            {"type": "company", "name": "SK스퀘어", "role": "분할 신설회사"},
            {"type": "company", "name": "SK하이닉스", "role": "SK텔레콤 보유 지분"},
            {"type": "company", "name": "SK㈜", "role": "지주회사"},
        ],
        "relations": [
            {"source": "SK텔레콤", "target": "SK하이닉스", "type": "지분보유", "detail": "20.1% 지분, 원가 3조3747억원"},
            {"source": "SK텔레콤", "target": "SK스퀘어", "type": "인적분할", "detail": "분할비율 0.6073625:0.3926375"},
        ],
        "risks": [
            {"type": "financial", "description": "SK하이닉스 시장가치 19조원 대비 장부가 3.3조원으로 16조원 저평가", "severity": "critical"},
            {"type": "governance", "description": "원가법 사용으로 분할비율 왜곡, 공정성 훼손", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/255",
        "title": "SK스퀘어 75조로 가는 지름길, 자회사 IPO?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-09-02",
        "summary": "SK스퀘어는 2025년까지 순자산 26조원→75조원 확대 계획. 원스토어, ADT캡스 등 자회사 IPO 추진.",
        "entities": [
            {"type": "company", "name": "SK스퀘어", "role": "뉴ICT·반도체 지주사"},
            {"type": "company", "name": "SK하이닉스", "role": "핵심 자회사"},
            {"type": "company", "name": "ADT캡스", "role": "융합보안 서비스"},
            {"type": "company", "name": "원스토어", "role": "멀티OS 앱마켓"},
            {"type": "company", "name": "티맵모빌리티", "role": "모빌리티 서비스"},
        ],
        "relations": [
            {"source": "SK스퀘어", "target": "SK하이닉스", "type": "자산 구성", "detail": "자산의 대부분, 현금흐름 원천"},
            {"source": "SK스퀘어", "target": "원스토어", "type": "지분 보유", "detail": "47.5% 지분, IPO 추진"},
        ],
        "risks": [
            {"type": "financial", "description": "SK하이닉스 배당금 감소로 투자재원 부족 가능성", "severity": "high"},
            {"type": "operational", "description": "흑자 미달 자회사들의 IPO 시기 지연 가능성", "severity": "high"},
            {"type": "governance", "description": "대규모 유상증자 시 SK㈜ 지분희석 및 부채비율 규제 제약", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/254",
        "title": "SK그룹의 성장 축 담당할 SK스퀘어, 첫번째 과제는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-08-30",
        "summary": "SK텔레콤 인적분할로 SK스퀘어 출범. SK하이닉스 중심으로 글로벌 ICT 투자기업 성장 추진. 2025년까지 순자산 75조원 목표.",
        "entities": [
            {"type": "company", "name": "SK텔레콤", "role": "분할 존속회사"},
            {"type": "company", "name": "SK스퀘어", "role": "신설 중간지주회사"},
            {"type": "company", "name": "SK하이닉스", "role": "핵심 자회사"},
            {"type": "company", "name": "SK㈜", "role": "그룹 지주회사"},
            {"type": "person", "name": "최태원", "role": "SK 그룹 회장"},
        ],
        "relations": [
            {"source": "SK텔레콤", "target": "SK스퀘어", "type": "인적분할", "detail": "2021년 11월 1일 분할"},
            {"source": "SK㈜", "target": "SK텔레콤", "type": "지분보유", "detail": "30.01% 지분율"},
        ],
        "risks": [
            {"type": "governance", "description": "지주회사의 증손회사 지분 100% 의무가 SK하이닉스 M&A 제약", "severity": "high"},
            {"type": "financial", "description": "4년 내 순자산 50조원 증대를 위한 막대한 자금조달 필요", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/253",
        "title": "뚝 끊긴 엑세스바이오 매출, 어떻게 볼 것인가?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-08-26",
        "summary": "코비드19 진단키트 업체 엑세스바이오 2분기 어닝 쇼크. 매출 1억9900만 달러→1941만 달러 급감. 최대주주 팜젠사이언스 실적도 악화.",
        "entities": [
            {"type": "company", "name": "엑세스바이오", "role": "코비드19 진단키트 기업"},
            {"type": "company", "name": "팜젠사이언스", "role": "최대주주"},
            {"type": "company", "name": "지티지웰니스", "role": "안티에이징 미용기기"},
            {"type": "company", "name": "지나인제약", "role": "코비드19 관련 진출"},
            {"type": "person", "name": "한의상", "role": "팜젠사이언스 회장"},
        ],
        "relations": [
            {"source": "팜젠사이언스", "target": "엑세스바이오", "type": "소유", "detail": "2019년 9.82% 지분 인수, 최대주주"},
        ],
        "risks": [
            {"type": "operational", "description": "매출 1억9900만 달러→1941만 달러로 급감", "severity": "critical"},
            {"type": "market", "description": "백신 접종 확대, 경쟁사 자가진단 제품 출시로 수요 급락", "severity": "critical"},
            {"type": "financial", "description": "지나인제약·자안바이오 자본잠식 80-100%, 상장폐지 위험", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/252",
        "title": "SK이노베이션 분할, SK배터리에 현금 몰아주는 이유?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-08-23",
        "summary": "SK이노베이션이 배터리 부문 분할하면서 보유 현금 대부분을 SK배터리에 집중. 5년간 18조원 투자 및 LG 1조원 지급 대비.",
        "entities": [
            {"type": "company", "name": "SK이노베이션", "role": "모회사"},
            {"type": "company", "name": "SK배터리", "role": "신설 자회사"},
            {"type": "company", "name": "SK E&P", "role": "신설 자회사"},
            {"type": "company", "name": "LG그룹", "role": "1조원 지급 상대방"},
            {"type": "person", "name": "김준", "role": "SK이노베이션 총괄사장"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "SK배터리", "type": "자산분할", "detail": "약 2조원 이상 현금 배정"},
            {"source": "SK배터리", "target": "LG그룹", "type": "지급의무", "detail": "일시금 1조원"},
        ],
        "risks": [
            {"type": "financial", "description": "SK배터리 1분기 약 1,767억원, 2분기 약 1,000억원 영업적자", "severity": "high"},
            {"type": "financial", "description": "현금 2-3조원이 1년 이내 소진될 가능성", "severity": "high"},
            {"type": "operational", "description": "SK이노베이션 배당금 감소(연 2조원→감소)로 지원 능력 약화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/251",
        "title": "SK이노베이션의 자금조달, 이제 시작에 불과할 수도",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-08-19",
        "summary": "SK이노베이션이 계열사 상장과 자산 매각으로 대규모 자금 조달. LG 배터리 분쟁 합의금 최대 2조원 및 30조원 배터리 투자가 주요 수요.",
        "entities": [
            {"type": "company", "name": "SK이노베이션", "role": "주요 분석 대상"},
            {"type": "company", "name": "LG에너지솔루션", "role": "배터리 분쟁 상대방"},
            {"type": "company", "name": "SK에너지", "role": "자회사"},
            {"type": "company", "name": "SK종합화학", "role": "자회사"},
            {"type": "person", "name": "김준", "role": "SK이노베이션 사장"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "LG에너지솔루션", "type": "법적분쟁", "detail": "일시금 1조원 및 로열티 1조원 지급"},
        ],
        "risks": [
            {"type": "legal", "description": "LG와의 분쟁 합의로 최대 2조원 지급 부담", "severity": "critical"},
            {"type": "financial", "description": "연간 현금흐름 1.9조원으로 30조원 투자 자체 충당 불가능", "severity": "high"},
            {"type": "market", "description": "국내 배터리 시장 3등 위치 지속", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/250",
        "title": "SK이노베이션發 Big Deal, 왜 쏟아지나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2021-08-17",
        "summary": "SK이노베이션이 SKIET 상장, SK루브리컨츠 지분 매각, 페루 광구 매각 등으로 수조 원대 현금 확보. SK그룹 125개 비상장 계열사 활용 전략.",
        "entities": [
            {"type": "company", "name": "SK이노베이션", "role": "주요 주체사"},
            {"type": "company", "name": "SKIET", "role": "배터리 분리막 자회사"},
            {"type": "company", "name": "SK루브리컨츠", "role": "윤활유 자회사"},
            {"type": "company", "name": "SK에너지", "role": "정유 부문 자회사"},
            {"type": "company", "name": "SK㈜", "role": "최상위 지배회사"},
        ],
        "relations": [
            {"source": "SK㈜", "target": "SK이노베이션", "type": "지분보유", "detail": "33.4% 최대주주"},
            {"source": "SK이노베이션", "target": "SK루브리컨츠", "type": "지분매각", "detail": "40% 지분 1조1000억원에 매각"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 계열사 구조에서 지배권 유지와 현금화 사이의 긴장", "severity": "high"},
            {"type": "financial", "description": "SK루브리컨츠 지분 매각가가 평가 기준에 비해 낮을 수 있다는 지적", "severity": "medium"},
            {"type": "market", "description": "정유·윤활유 부문 성장성 제한으로 사업가치 하락 우려", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (28차) ===\n")

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
