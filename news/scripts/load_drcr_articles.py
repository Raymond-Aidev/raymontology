#!/usr/bin/env python3
"""
DRCR 기사 일괄 적재 스크립트
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

# 파싱된 기사 데이터
ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/646",
        "title": "뉴롯데 전략의 실패, 신동빈 리더십 괜찮을까",
        "publisher": "재무제표를 읽는 사람들",
        "publish_date": "2025-12-22",
        "author": "강종구",
        "summary": "신동빈 회장의 뉴롯데 전략이 기대 성과를 내지 못하면서 롯데그룹의 재무 위기가 심화되고 있습니다. 핵심 계열사인 롯데쇼핑과 롯데케미칼의 연속 적자, 그리고 바이오·수소에너지 등 신사업 투자의 부진이 그룹 전체의 부채를 급증시켰습니다.",
        "entities": [
            {"type": "person", "name": "신동빈", "role": "롯데그룹 회장"},
            {"type": "company", "name": "롯데그룹", "role": "한국의 대형 복합기업"},
            {"type": "company", "name": "롯데지주", "role": "롯데그룹의 모회사"},
            {"type": "company", "name": "롯데쇼핑", "role": "핵심 유통 계열사"},
            {"type": "company", "name": "롯데케미칼", "role": "주력 화학 계열사"},
            {"type": "company", "name": "롯데웰푸드", "role": "식품 종속회사"},
            {"type": "company", "name": "롯데칠성음료", "role": "음료 종속회사"},
            {"type": "company", "name": "코리아세븐", "role": "편의점 종속회사"},
            {"type": "company", "name": "일진머티리얼즈", "role": "이차전지 소재업체"},
            {"type": "company", "name": "롯데바이오로직스", "role": "신설 바이오 계열사"},
            {"type": "company", "name": "롯데정보통신", "role": "메타버스·디지털 전환"}
        ],
        "relations": [
            {"source": "롯데지주", "target": "롯데쇼핑", "type": "subsidiary", "detail": "롯데지주는 롯데쇼핑을 관계회사로 보유 중"},
            {"source": "롯데지주", "target": "롯데케미칼", "type": "subsidiary", "detail": "롯데지주는 롯데케미칼을 관계회사로 보유 중"},
            {"source": "롯데지주", "target": "롯데웰푸드", "type": "subsidiary", "detail": "롯데웰푸드는 롯데지주의 종속회사"},
            {"source": "롯데지주", "target": "코리아세븐", "type": "subsidiary", "detail": "코리아세븐은 롯데지주의 종속회사"},
            {"source": "신동빈", "target": "롯데지주", "type": "board_member", "detail": "신동빈은 롯데지주의 회장으로 경영을 총괄"},
            {"source": "롯데케미칼", "target": "일진머티리얼즈", "type": "transaction", "detail": "2022년 10월 약 2조7000억원에 인수 완료"},
            {"source": "롯데지주", "target": "롯데바이오로직스", "type": "spc_related", "detail": "2022년 설립된 신설 계열사"}
        ],
        "risks": [
            {"type": "financial", "description": "롯데지주가 지난해 약 1조원의 대규모 적자 기록", "severity": "critical"},
            {"type": "financial", "description": "롯데케미칼의 순차입금이 2021년 296억원에서 2024년 7조원대로 급증", "severity": "critical"},
            {"type": "operational", "description": "롯데쇼핑의 백화점 점유율이 2017년 40%에서 2024년 31%로 하락", "severity": "high"},
            {"type": "operational", "description": "롯데케미칼이 3년 연속 영업적자", "severity": "critical"},
            {"type": "operational", "description": "신사업 투자(바이오, 수소에너지, 메타버스)에서 가시적 성과 미흡", "severity": "high"},
            {"type": "governance", "description": "신동빈 회장의 리더십이 중요 경영능력을 실적으로 입증하지 못함", "severity": "high"}
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/645",
        "title": "신동빈 회장의 경영권은 철옹성일까?",
        "publisher": "재무제표를 읽는 사람들",
        "publish_date": "2025-12-15",
        "author": "강종구",
        "summary": "롯데그룹 신동빈 회장의 경영권이 형 신동주 회장의 주주대표소송으로 위협받을 수 있다는 분석. 롯데케미칼과 롯데건설의 경영 악화로 신동빈 회장의 리더십에 균열 가능성.",
        "entities": [
            {"type": "person", "name": "신동빈", "role": "롯데그룹 회장"},
            {"type": "person", "name": "신동주", "role": "SDJ코퍼레이션 회장"},
            {"type": "company", "name": "롯데지주", "role": "한국 롯데그룹의 최상위 지배회사"},
            {"type": "company", "name": "롯데홀딩스", "role": "일본 기반 최상위 지배회사"},
            {"type": "company", "name": "광윤사", "role": "롯데홀딩스의 최대주주"},
            {"type": "company", "name": "롯데케미칼", "role": "롯데지주 산하 주력 기업"},
            {"type": "company", "name": "롯데건설", "role": "롯데지주 산하 주력 기업"},
            {"type": "company", "name": "호텔롯데", "role": "롯데그룹 핵심 계열사"}
        ],
        "relations": [
            {"source": "신동빈", "target": "롯데지주", "type": "major_shareholder", "detail": "최대주주"},
            {"source": "신동빈", "target": "롯데홀딩스", "type": "executive", "detail": "회장 겸 대표이사, 개인 지분 2.7%"},
            {"source": "신동주", "target": "광윤사", "type": "major_shareholder", "detail": "최대주주, 지분율 50.2%"},
            {"source": "광윤사", "target": "롯데홀딩스", "type": "major_shareholder", "detail": "최대주주, 지분율 28.1%"},
            {"source": "롯데홀딩스", "target": "롯데지주", "type": "major_shareholder", "detail": "지분율 24.5%"},
            {"source": "롯데지주", "target": "롯데케미칼", "type": "subsidiary", "detail": "산하 주요 상장사"},
            {"source": "롯데지주", "target": "롯데건설", "type": "subsidiary", "detail": "산하 주요 상장사"}
        ],
        "risks": [
            {"type": "governance", "description": "신동주 회장의 주주대표소송으로 인한 지배구조 불안정", "severity": "high"},
            {"type": "legal", "description": "형 신동주 회장이 롯데지주 주식 1만5000주 보유로 주주대표소송 권리 확보", "severity": "medium"},
            {"type": "operational", "description": "롯데케미칼과 롯데건설의 경영 악화로 신동빈 회장의 리더십 신뢰도 하락", "severity": "high"},
            {"type": "governance", "description": "롯데홀딩스 경영권 손실 시 롯데지주 지배권도 함께 위협", "severity": "critical"}
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/644",
        "title": "에이프로젠 자회사는 어떻게 상장 게임사를 인수했나",
        "publisher": "재무제표를 읽는 사람들",
        "publish_date": "2025-12-08",
        "author": "강종구",
        "summary": "에이프로젠 자회사 에이비에이바이오로직스가 2017년 로코조이인터내셔널의 상장주식을 600억원에 인수하는 과정을 분석. M&A 전문가 원영식의 더블루홀딩컴퍼니가 경영권 매각을 중개.",
        "entities": [
            {"type": "company", "name": "에이프로젠", "role": "모회사"},
            {"type": "company", "name": "에이비에이바이오로직스", "role": "에이프로젠 자회사"},
            {"type": "company", "name": "슈넬생명과학", "role": "에이프로젠 자회사"},
            {"type": "company", "name": "로코조이인터내셔널", "role": "인수 대상 상장사"},
            {"type": "company", "name": "더블유홀딩컴퍼니", "role": "M&A 중개사"},
            {"type": "company", "name": "로코조이홍콩", "role": "중국계 최대주주"},
            {"type": "company", "name": "에스맥", "role": "로코조이 신주인수 참여"},
            {"type": "company", "name": "지베이스", "role": "김재섭 회장의 개인회사"},
            {"type": "person", "name": "김재섭", "role": "에이프로젠 회장"},
            {"type": "person", "name": "원영식", "role": "M&A 전문가"},
            {"type": "person", "name": "조경숙", "role": "에스맥 대표이사"}
        ],
        "relations": [
            {"source": "에이프로젠", "target": "에이비에이바이오로직스", "type": "subsidiary", "detail": "에이프로젠이 에이비에이바이오로직스의 모회사"},
            {"source": "에이프로젠", "target": "슈넬생명과학", "type": "subsidiary", "detail": "에이프로젠 자회사"},
            {"source": "에이비에이바이오로직스", "target": "로코조이인터내셔널", "type": "transaction", "detail": "430억원 투자로 31.6% 지분 인수"},
            {"source": "슈넬생명과학", "target": "로코조이인터내셔널", "type": "transaction", "detail": "170억원 투자로 로코조이 인수 공동 참여"},
            {"source": "김재섭", "target": "에이프로젠", "type": "executive", "detail": "에이프로젠 회장"},
            {"source": "김재섭", "target": "지베이스", "type": "executive", "detail": "개인회사 대표"},
            {"source": "지베이스", "target": "에스맥", "type": "investor", "detail": "조경숙의 에스맥 인수 자금 지원"},
            {"source": "에스맥", "target": "로코조이인터내셔널", "type": "cb_subscriber", "detail": "로코조이 신주인수계약 150억원 참여"},
            {"source": "조경숙", "target": "에스맥", "type": "executive", "detail": "에스맥 대표이사"}
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 다층 구조의 M&A 과정에서 실제 경영권 인수 주체가 불명확", "severity": "high"},
            {"type": "financial", "description": "에이비에이바이오로직스가 매출 없이 1900억원 규모 자금을 투입", "severity": "high"},
            {"type": "operational", "description": "로코조이의 워짜오MT 국내 흥행 실패, 주가 급락", "severity": "high"},
            {"type": "governance", "description": "에이프로젠과 자회사들 간 자금 이동의 복잡성, 투명성 부족", "severity": "medium"}
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/643",
        "title": "에이프로젠 IPO 실패 이후 생긴 일",
        "publisher": "재무제표를 읽는 사람들",
        "publish_date": "2025-12-01",
        "author": "강종구",
        "summary": "에이프로젠의 2017년 실패한 IPO 이전과 이후의 복잡한 지배구조 변화를 추적. 조경숙 회장의 에린데알투자자문이 슈넬생명과학 지분을 취득하고 사실상 우회상장을 완성하는 과정을 분석.",
        "entities": [
            {"type": "company", "name": "에이프로젠", "role": "주요 대상 기업"},
            {"type": "company", "name": "슈넬생명과학", "role": "에이프로젠의 상장 자회사"},
            {"type": "company", "name": "에린데알투자자문", "role": "투자자 역할"},
            {"type": "company", "name": "에이프로젠바이오로직스", "role": "에이프로젠의 자회사"},
            {"type": "company", "name": "에이프로젠케이아이씨", "role": "상장사, 후에 에이프로젠과 합병"},
            {"type": "person", "name": "조경숙", "role": "에린데알투자자문 회장"},
            {"type": "person", "name": "김재섭", "role": "슈넬생명과학 전 회장"},
            {"type": "company", "name": "지베이스", "role": "슈넬생명과학 투자자"},
            {"type": "company", "name": "에스코넥", "role": "에린데알 전환사채 매입사"}
        ],
        "relations": [
            {"source": "에이프로젠", "target": "슈넬생명과학", "type": "subsidiary", "detail": "에이프로젠이 슈넬생명과학의 최대주주"},
            {"source": "에린데알투자자문", "target": "슈넬생명과학", "type": "major_shareholder", "detail": "2016년 김재섭 부부의 전량 지분 186억원 매입"},
            {"source": "조경숙", "target": "에린데알투자자문", "type": "executive", "detail": "에린데알투자자문 회장"},
            {"source": "에이프로젠", "target": "에이프로젠바이오로직스", "type": "subsidiary", "detail": "100% 자회사"},
            {"source": "슈넬생명과학", "target": "에이프로젠바이오로직스", "type": "investor", "detail": "2016년 80억원 유상증자 참여"},
            {"source": "에이프로젠케이아이씨", "target": "에이프로젠바이오로직스", "type": "investor", "detail": "2018년 49.37% 지분을 1,175억원에 인수"},
            {"source": "에이프로젠", "target": "에이프로젠케이아이씨", "type": "spc_related", "detail": "비상장사가 상장사 흡수합병으로 우회상장"},
            {"source": "에스코넥", "target": "에린데알투자자문", "type": "cb_subscriber", "detail": "2015년 30억원 규모 전환사채 매입"},
            {"source": "지베이스", "target": "슈넬생명과학", "type": "major_shareholder", "detail": "2014년 전환사채 발행 인수자"}
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 지배구조 변화와 우회상장 구조 활용", "severity": "high"},
            {"type": "financial", "description": "매출 53억원(전액 모회사 거래)에 불과한 회사에 1,175억원 투자", "severity": "critical"},
            {"type": "operational", "description": "에이프로젠의 자금 조달 및 투자 규모 - 특별 수익창출원 없이 IPO 준비", "severity": "high"},
            {"type": "legal", "description": "5% 미만 지분 취득으로 공시 회피 가능성", "severity": "medium"}
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/642",
        "title": "든든한 뒷배였던 닛코제약과의 결별",
        "publisher": "재무제표를 읽는 사람들",
        "publish_date": "2025-11-25",
        "author": "강종구",
        "summary": "에이프로젠의 주요 지원사였던 일본의 닛코제약이 제네릭 의약품 품질 문제로 경영악화를 겪으면서 2019년부터 발주가 중단되고 2024년 지분을 전량 매각하며 양사 관계가 종료.",
        "entities": [
            {"type": "company", "name": "에이프로젠", "role": "바이오시밀러 개발사"},
            {"type": "company", "name": "닛코제약", "role": "일본 제네릭 제약사"},
            {"type": "company", "name": "슈넬생명과학", "role": "에이프로젠의 모회사"},
            {"type": "person", "name": "김재섭", "role": "슈넬생명과학 회장"},
            {"type": "person", "name": "조경숙", "role": "에린데알투자자문 회장"},
            {"type": "person", "name": "김정출", "role": "슈넬생명과학 대표이사"}
        ],
        "relations": [
            {"source": "닛코제약", "target": "에이프로젠", "type": "major_shareholder", "detail": "지분 35.56% 보유"},
            {"source": "닛코제약", "target": "에이프로젠", "type": "transaction", "detail": "2014년 레미케이드 시밀러 세계시장 판권 계약금 100억원"},
            {"source": "에이프로젠", "target": "슈넬생명과학", "type": "subsidiary", "detail": "슈넬생명과학의 자회사"},
            {"source": "김재섭", "target": "슈넬생명과학", "type": "executive", "detail": "회장으로서 경영 주도"}
        ],
        "risks": [
            {"type": "financial", "description": "닛코제약의 품질 문제로 인한 2019년 이후 발주 완전 중단", "severity": "critical"},
            {"type": "governance", "description": "라이선스 계약금의 부적절한 매출 인식으로 2015년 매출 196억원에서 18억원으로 정정", "severity": "high"},
            {"type": "legal", "description": "금융감독원의 2017년 감리로 재무제표 수정 강제, 기업공개 무산", "severity": "high"},
            {"type": "operational", "description": "닛코제약의 2023년 도쿄증권거래소 퇴출 및 2024년 에이프로젠 지분 전량 매각", "severity": "critical"}
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/641",
        "title": "김재섭과 One Team, 조경숙의 등장",
        "publisher": "재무제표를 읽는 사람들",
        "publish_date": "2025-11-17",
        "author": "강종구",
        "summary": "김재섭 회장과 조경숙 대표가 슈넬생명과학 주가 급등 과정에서 협력하며 원 팀으로 활동한 내역을 분석. 두 인물은 여러 기업의 M&A에서 밀접하게 협력하며 복잡한 지분관계 네트워크를 형성.",
        "entities": [
            {"type": "person", "name": "김재섭", "role": "회장, 에이프로젠 지배인"},
            {"type": "person", "name": "조경숙", "role": "대표, 에린데알투자자문 설립자"},
            {"type": "person", "name": "유원형", "role": "넥스코닉스 대표"},
            {"type": "person", "name": "강선주", "role": "지베이스 대표"},
            {"type": "company", "name": "슈넬생명과학", "role": "주가 급등 후 주요 거래 대상"},
            {"type": "company", "name": "에이프로젠", "role": "김재섭 최대주주 회사"},
            {"type": "company", "name": "에린데알투자자문", "role": "슈넬생명과학 지분 매입"},
            {"type": "company", "name": "에스맥", "role": "조경숙이 지배하는 회사"},
            {"type": "company", "name": "에스씨엠생명과학", "role": "조경숙 회장 회사"},
            {"type": "company", "name": "지베이스", "role": "에이프로젠그룹 지배구조 정점"},
            {"type": "company", "name": "넥스코닉스", "role": "에이프로젠 지분 보유"},
            {"type": "company", "name": "케이포르투나인베스트먼트", "role": "넥스코닉스 최대주주"}
        ],
        "relations": [
            {"source": "김재섭", "target": "에이프로젠", "type": "executive", "detail": "대표로 경영 중"},
            {"source": "조경숙", "target": "에린데알투자자문", "type": "executive", "detail": "2012년 11월 설립, 대표"},
            {"source": "에린데알투자자문", "target": "슈넬생명과학", "type": "major_shareholder", "detail": "김재섭 부부로부터 4.62% 지분 186억원에 인수"},
            {"source": "에이프로젠", "target": "슈넬생명과학", "type": "major_shareholder", "detail": "지분율 7.74% 최대주주"},
            {"source": "김재섭", "target": "조경숙", "type": "spc_related", "detail": "원 팀으로 불리는 밀접한 협력 관계"},
            {"source": "에스맥", "target": "에이프로젠", "type": "transaction", "detail": "다이노 인수에 함께 참여"},
            {"source": "넥스코닉스", "target": "에이프로젠", "type": "major_shareholder", "detail": "지분 공동 보유"},
            {"source": "케이포르투나인베스트먼트", "target": "넥스코닉스", "type": "major_shareholder", "detail": "100% 지분 보유"},
            {"source": "강선주", "target": "지베이스", "type": "executive", "detail": "대표, 김재섭 100% 지분 보유 회사"}
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 다층 지분구조를 통한 간접 지배로 투명성 저하", "severity": "high"},
            {"type": "legal", "description": "주가 급등 후 최대주주의 지분 매각이 정보 비대칭 의혹 제기", "severity": "high"},
            {"type": "operational", "description": "조경숙이 인수한 회사들이 연쇄적 위기 겪음", "severity": "medium"},
            {"type": "governance", "description": "개인회사를 통한 그룹 지배구조로 이해상충 위험", "severity": "high"}
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/640",
        "title": "적자회사 슈넬생명과학의 식솔들",
        "publisher": "재무제표를 읽는 사람들",
        "publish_date": "2025-11-10",
        "author": "강종구",
        "summary": "슈넬생명과학은 연 200억원대 매출에도 지속적인 적자를 기록했으며, 101억원 규모의 자금을 비상장사 에이프로젠에 대여. 2024년 결손금이 2346억원에 달함.",
        "entities": [
            {"type": "company", "name": "슈넬생명과학", "role": "코스피 상장사로 지속적 적자 기록"},
            {"type": "company", "name": "에이프로젠", "role": "신약개발업체"},
            {"type": "person", "name": "김재섭", "role": "에이프로젠 최대주주 및 회장"},
            {"type": "company", "name": "지베이스", "role": "2015년 에이프로젠 지분 인수"},
            {"type": "company", "name": "청계제약", "role": "슈넬생명과학 자회사"},
            {"type": "company", "name": "한국슈넬", "role": "슈넬생명과학 종속기업"},
            {"type": "company", "name": "이앤엠레볼루션", "role": "신재생에너지개발회사"},
            {"type": "company", "name": "그랑비즈", "role": "컨설팅업체"},
            {"type": "person", "name": "김정출", "role": "김재섭 회장의 형"}
        ],
        "relations": [
            {"source": "슈넬생명과학", "target": "에이프로젠", "type": "investor", "detail": "2014년 101억원 규모 대여금 제공"},
            {"source": "에이프로젠", "target": "슈넬생명과학", "type": "major_shareholder", "detail": "2014년말 지분 9.33% 보유"},
            {"source": "슈넬생명과학", "target": "에이프로젠", "type": "major_shareholder", "detail": "지분 6.61% 보유"},
            {"source": "김재섭", "target": "에이프로젠", "type": "major_shareholder", "detail": "부부 합산 최대주주 44.9%"},
            {"source": "슈넬생명과학", "target": "청계제약", "type": "subsidiary", "detail": "2013년 124억원 자금 지원"},
            {"source": "청계제약", "target": "이앤엠레볼루션", "type": "investor", "detail": "신주인수권부사채 36억원 인수"},
            {"source": "슈넬생명과학", "target": "한국슈넬", "type": "subsidiary", "detail": "에이프로젠 지분 3.3% 매각 후 매입"},
            {"source": "한국슈넬", "target": "지베이스", "type": "transaction", "detail": "2015년 에이프로젠 지분 3.3% 약 27억원에 매각"},
            {"source": "김정출", "target": "그랑비즈", "type": "board_member", "detail": "이사 직책 보유"}
        ],
        "risks": [
            {"type": "financial", "description": "결손금이 2024년말 현재 2346억원에 달하며 자본총계의 64%", "severity": "critical"},
            {"type": "governance", "description": "최대주주 에이프로젠이 자금 수혜자로 이해상충 존재", "severity": "high"},
            {"type": "operational", "description": "영업활동으로 현금을 창출하지 못해 지속적으로 자산 매각과 유상증자 의존", "severity": "high"},
            {"type": "governance", "description": "관계자 컨설팅회사를 통한 신재생에너지사업 진출로 계열사 간 부실거래 우려", "severity": "medium"},
            {"type": "financial", "description": "이앤엠레볼루션이 완전 자본잠식 상태", "severity": "high"}
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/638",
        "title": "지배구조의 변곡점, 지베이스의 등장",
        "publisher": "재무제표를 읽는 사람들",
        "publish_date": "2025-10-20",
        "author": "강종구",
        "summary": "에이프로젠그룹의 지배구조 변화를 추적. 2014년 김재섭 회장의 개인회사 지베이스 설립으로 인한 복잡한 자금거래 구조를 분석.",
        "entities": [
            {"type": "person", "name": "김재섭", "role": "에이프로젠그룹 회장"},
            {"type": "company", "name": "에이프로젠", "role": "신약개발업체"},
            {"type": "company", "name": "슈넬생명과학", "role": "에이프로젠 모회사 역할"},
            {"type": "company", "name": "지베이스", "role": "김재섭 회장의 개인회사"},
            {"type": "company", "name": "제넥셀세인", "role": "초기 지배 구조상 중간 계열사"},
            {"type": "company", "name": "푸른저축은행", "role": "전환사채 명목상 인수사"},
            {"type": "company", "name": "우리캐피탈", "role": "주식담보차입 제공 금융회사"}
        ],
        "relations": [
            {"source": "김재섭", "target": "지베이스", "type": "executive", "detail": "지베이스 설립자이자 주요 차입금 공급처"},
            {"source": "지베이스", "target": "슈넬생명과학", "type": "transaction", "detail": "전환사채 50억원 인수 및 중도해지"},
            {"source": "지베이스", "target": "에이프로젠", "type": "transaction", "detail": "전환사채 30억원 상당 매각, 지분율 12.91% 확보"},
            {"source": "슈넬생명과학", "target": "에이프로젠", "type": "subsidiary", "detail": "초기 모회사 역할, 후에 자회사로 전환"},
            {"source": "김재섭", "target": "에이프로젠", "type": "major_shareholder", "detail": "직접 지분 9.93%, 지베이스를 통한 간접 지배"},
            {"source": "우리캐피탈", "target": "슈넬생명과학", "type": "transaction", "detail": "주식담보차입 제공, 700만주 담보 처리"},
            {"source": "푸른저축은행", "target": "슈넬생명과학", "type": "cb_subscriber", "detail": "전환사채 50억원 명목상 인수"}
        ],
        "risks": [
            {"type": "governance", "description": "지베이스-에이프로젠-슈넬생명과학 간 숨겨진 지분 구조", "severity": "critical"},
            {"type": "financial", "description": "지베이스 조달자금 전액이 김재섭 회장의 차입금", "severity": "critical"},
            {"type": "legal", "description": "주식담보차입 자금의 지베이스 유입, 전환사채 중도해지 등 회계처리 이상 가능성", "severity": "high"},
            {"type": "operational", "description": "슈넬생명과학 지분 매각 시도 실패로 인한 주가 변동성", "severity": "medium"}
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/637",
        "title": "두 차례의 매각 시도, 김재섭 회장은 진심이었을까?",
        "publisher": "재무제표를 읽는 사람들",
        "publish_date": "2025-10-13",
        "author": "강종구",
        "summary": "김재섭 회장이 슈넬생명과학의 경영권 지분을 두 번에 걸쳐 매각하려다 실패한 사건을 추적. 증여세 부과, 자회사 에이프로젠 지분 매각, 실패한 인수합병 계약들을 분석.",
        "entities": [
            {"type": "person", "name": "김재섭", "role": "슈넬생명과학 회장"},
            {"type": "company", "name": "슈넬생명과학", "role": "주요 피사 기업"},
            {"type": "company", "name": "에이프로젠", "role": "슈넬생명과학 자회사"},
            {"type": "company", "name": "제넥셀세인", "role": "김재섭이 매각한 이전 회사"},
            {"type": "company", "name": "한국기술산업", "role": "제넥셀세인 인수자"},
            {"type": "company", "name": "청계제약", "role": "인수 대상 기업"},
            {"type": "company", "name": "바이넥스", "role": "에이프로젠 지분 인수자"},
            {"type": "company", "name": "닛코제약", "role": "에이프로젠 전략적 파트너"},
            {"type": "company", "name": "케이앤텍코리아", "role": "첫 번째 지분 매각 시도 인수자"},
            {"type": "person", "name": "탁병오", "role": "케이앤텍코리아 대표"},
            {"type": "company", "name": "지와이엠1호조합", "role": "두 번째 지분 매각 시도 인수자"},
            {"type": "company", "name": "팝인베스트먼트", "role": "신주인수권부사채 인수사"},
            {"type": "person", "name": "김정출", "role": "김재섭의 형"}
        ],
        "relations": [
            {"source": "김재섭", "target": "슈넬생명과학", "type": "major_shareholder", "detail": "2012년 6월 무상증자 후 약 23% 지분 보유"},
            {"source": "슈넬생명과학", "target": "에이프로젠", "type": "subsidiary", "detail": "2011년 닛코제약 투자 후 약 1200만주 중 800만주 매각"},
            {"source": "에이프로젠", "target": "슈넬생명과학", "type": "investor", "detail": "2013년 10월 제3자배정 유상증자로 최대주주 등극"},
            {"source": "김재섭", "target": "제넥셀세인", "type": "spc_related", "detail": "220억원에 경영권 지분 매각, 98억원 증여세 부과"},
            {"source": "슈넬생명과학", "target": "청계제약", "type": "transaction", "detail": "화성시 청계제약 공장 인수"},
            {"source": "김재섭", "target": "케이앤텍코리아", "type": "transaction", "detail": "2012년 12월 보통주 700만주와 경영권을 180억원에 양도계약, 이후 해지"},
            {"source": "김재섭", "target": "지와이엠1호조합", "type": "transaction", "detail": "2013년 2월 700만주와 경영권을 220억원에 매각계약, 이후 중도 해지"},
            {"source": "닛코제약", "target": "에이프로젠", "type": "major_shareholder", "detail": "44.9% 지분율로 전략적 파트너"},
            {"source": "팝인베스트먼트", "target": "슈넬생명과학", "type": "cb_subscriber", "detail": "신주인수권부사채 170억원 인수"}
        ],
        "risks": [
            {"type": "governance", "description": "최대주주의 지분 매각 시도가 두 차례 모두 실패, 구매자의 자금능력 사전 검증 안 함", "severity": "high"},
            {"type": "governance", "description": "지분매각 불발 소식에 주가가 급락하는 등 경영권 이동 추진이 주가에 심각한 영향", "severity": "high"},
            {"type": "legal", "description": "김재섭 회장 부부가 제넥셀세인 경영권 지분 매각 관련 98억원의 증여세 부과 처분", "severity": "high"},
            {"type": "financial", "description": "대규모 적자를 내고 있던 슈넬생명과학이 유동성 확보를 위해 자산 처분", "severity": "high"},
            {"type": "operational", "description": "에이프로젠이 바이오시밀러 연구개발 자금 117억원을 조달했으나 주로 유동성과 대여금으로 사용", "severity": "medium"}
        ]
    }
]


async def main():
    print("=== DRCR 기사 일괄 적재 시작 ===\n")

    # 적재 전 통계
    before_stats = await get_article_stats()
    print(f"적재 전 통계:")
    print(f"  - Articles: {before_stats['articles']}")
    print(f"  - Entities: {before_stats['entities']}")
    print(f"  - Relations: {before_stats['relations']}")
    print(f"  - Risks: {before_stats['risks']}")
    print()

    success_count = 0
    skip_count = 0
    error_count = 0

    for article in ARTICLES:
        result = await save_article(**article)

        if result.get("success"):
            print(f"✅ [{article['publish_date']}] {article['title']}")
            print(f"   - Entities: {result['stats']['entities']}, Relations: {result['stats']['relations']}, Risks: {result['stats']['risks']}")
            print(f"   - Matched: Companies={result['stats'].get('matched_companies', 0)}, Officers={result['stats'].get('matched_officers', 0)}")
            success_count += 1
        elif "already exists" in result.get("error", ""):
            print(f"⏭️  [{article['publish_date']}] {article['title']} (이미 존재)")
            skip_count += 1
        else:
            print(f"❌ [{article['publish_date']}] {article['title']}")
            print(f"   Error: {result.get('error')}")
            error_count += 1

    # 적재 후 통계
    after_stats = await get_article_stats()
    print(f"\n=== 적재 완료 ===")
    print(f"성공: {success_count}, 스킵: {skip_count}, 실패: {error_count}")
    print(f"\n적재 후 통계:")
    print(f"  - Articles: {before_stats['articles']} → {after_stats['articles']} (+{after_stats['articles'] - before_stats['articles']})")
    print(f"  - Entities: {before_stats['entities']} → {after_stats['entities']} (+{after_stats['entities'] - before_stats['entities']})")
    print(f"  - Relations: {before_stats['relations']} → {after_stats['relations']} (+{after_stats['relations'] - before_stats['relations']})")
    print(f"  - Risks: {before_stats['risks']} → {after_stats['risks']} (+{after_stats['risks'] - before_stats['risks']})")


if __name__ == "__main__":
    asyncio.run(main())
