#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 20차 (435-414: 삼표/효성/LG디스플레이/롯데/SK/한온시스템/보험 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/435",
        "title": "정대현의 에스피네이처, ㈜삼표의 든든한 자금줄",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-22",
        "summary": "정대현 사장이 아버지로부터 ㈜대원 지분을 양도받고 삼표로지스틱스를 흡수합병하여 삼표그룹 승계의 기틀을 마련. 에스피네이처(신대원)는 10년간 자산 10.5배, 순자산 17배로 성장하며 삼표그룹 내 주요 지주회사로 위상을 높임.",
        "entities": [
            {"type": "person", "name": "정대현", "role": "사장, 에스피네이처 주요 주주"},
            {"type": "person", "name": "정도원", "role": "회장, 삼표그룹 창업자"},
            {"type": "company", "name": "에스피네이처", "role": "지주회사, 물류 및 시멘트 사업"},
            {"type": "company", "name": "삼표", "role": "지주회사"},
            {"type": "company", "name": "삼표시멘트", "role": "상장사, 삼표그룹 유일한 상장 자회사"},
        ],
        "relations": [
            {"source": "정대현", "target": "에스피네이처", "type": "ownership", "detail": "77.96% 지분 보유"},
            {"source": "에스피네이처", "target": "삼표", "type": "ownership", "detail": "지분 19.43% 보유"},
            {"source": "에스피네이처", "target": "삼표", "type": "financial_support", "detail": "2020년 600억원 유상증자 인수, 510억원 대여, 3050억원 보증 제공"},
        ],
        "risks": [
            {"type": "governance", "description": "삼표그룹의 물류자산을 순자산가치 이하의 가격으로 대주주 일가에 양도, 약 25억원 처분손실 발생", "severity": "high"},
            {"type": "governance", "description": "에스피네이처가 삼표 계열사에 3050억원 규모의 보증을 제공하여 재무 부담 증가 가능", "severity": "high"},
            {"type": "financial", "description": "최근 2년간 에스피네이처의 삼표그룹 계열사 매입액(1712억원)이 매출액(1292억원)을 초과", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/434",
        "title": "승계의 발판 에스피네이처, 성장의 역사",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-19",
        "summary": "삼표그룹이 10년 유지한 지주회사 체제를 역합병하며 3세 승계 작업을 진행 중. 정대현 사장의 회사 에스피네이처가 아버지 정도원 회장의 계열사들을 차례로 합병하며 그룹 지배구조 내 중요 위치를 확보.",
        "entities": [
            {"type": "company", "name": "삼표그룹", "role": "대상 그룹"},
            {"type": "company", "name": "삼표", "role": "지주회사"},
            {"type": "company", "name": "삼표산업", "role": "주력 사업 회사"},
            {"type": "company", "name": "에스피네이처", "role": "3세 기업"},
            {"type": "person", "name": "정도원", "role": "회장 (2세)"},
            {"type": "person", "name": "정대현", "role": "사장 (3세)"},
        ],
        "relations": [
            {"source": "정대현", "target": "에스피네이처", "type": "ownership", "detail": "대부분 지분 보유"},
            {"source": "삼표로지스틱스", "target": "에스피네이처", "type": "merger", "detail": "2013년 대원 합병으로 통합"},
        ],
        "risks": [
            {"type": "governance", "description": "역합병으로 생성되는 막대한 자사주(약 48.9%)의 처분 방식이 3세의 경영권 확보에 영향", "severity": "high"},
            {"type": "governance", "description": "지주회사 역합병이 승계의 유용한 수단으로 입증될 경우 다른 그룹들이 참고할 수 있음", "severity": "medium"},
            {"type": "financial", "description": "2007년 삼표산업이 장부가 43억원의 주식을 18억원에 처분하며 25억원 손실 발생", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/433",
        "title": "1억원짜리 페이퍼컴퍼니 ASC, 자동차딜러 지주회사로",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-15",
        "summary": "조현상 부회장이 100% 소유한 에이에스씨(ASC)는 원래 1억원 자본금의 페이퍼컴퍼니에서 시작해 더클래스효성과 신성자동차를 현물출자받아 1조8000억원대 매출의 지주회사로 성장. 디베스트파트너스라는 조세회피처 관련 회사를 거쳐 수익성 높은 자동차딜러사업을 장악.",
        "entities": [
            {"type": "person", "name": "조현상", "role": "효성그룹 부회장, ASC 100% 주주"},
            {"type": "person", "name": "조현준", "role": "효성그룹 회장"},
            {"type": "company", "name": "더클래스효성", "role": "메르세데스 벤츠 딜러"},
            {"type": "company", "name": "ASC", "role": "자동차딜러 지주회사"},
            {"type": "company", "name": "디베스트파트너스", "role": "조세회피처 관련 페이퍼컴퍼니"},
        ],
        "relations": [
            {"source": "조현상", "target": "ASC", "type": "ownership", "detail": "100% 지분 소유"},
            {"source": "ASC", "target": "더클래스효성", "type": "ownership", "detail": "93.04% 지분 보유"},
            {"source": "디베스트파트너스", "target": "더클래스효성", "type": "ownership", "detail": "2007년 31.54% 우선주 투자, 2014년 보통주 전환"},
        ],
        "risks": [
            {"type": "governance", "description": "조세회피처 관련 페이퍼컴퍼니인 디베스트파트너스가 더클래스효성 지분을 장기 보유, 차입금 30억원 출처 불명확", "severity": "high"},
            {"type": "financial", "description": "ASC 인수 당시 자본잠식 상태(부채 32억원 vs 자본금 1억원)였으나 현물출자 후 급성장", "severity": "high"},
            {"type": "regulatory", "description": "영국령 버진아일랜드에 설립된 페이퍼컴퍼니 디베스트 인베스트먼트 그룹과의 관계, 조세 회피 가능성", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/432",
        "title": "아직은 돈 못 버는 ㈜신동진의 자동차딜러 자회사들",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-12",
        "summary": "신동진이 보유한 자동차 딜러 자회사들(더프리미엄효성, 효성프리미어모터스, 아승오토모티브그룹)은 2019년 이후 매출 부진과 적자로 안정적 수익구조를 구축하지 못하고 있음. 신동진의 이익 대부분은 임대료에서 발생하며, 자동차 딜러 사업은 오히려 연결 기준 영업이익을 크게 감소시킴.",
        "entities": [
            {"type": "person", "name": "조현상", "role": "㈜신동진 최대주주"},
            {"type": "company", "name": "㈜신동진", "role": "지주회사"},
            {"type": "company", "name": "더프리미엄효성", "role": "토요타 자동차 딜러"},
            {"type": "company", "name": "효성프리미어모터스", "role": "재규어랜드로버 딜러"},
            {"type": "company", "name": "아승오토모티브그룹", "role": "자동차 관련 자회사"},
        ],
        "relations": [
            {"source": "조현상", "target": "㈜신동진", "type": "ownership", "detail": "2005년 최대주주 지위 획득"},
            {"source": "㈜신동진", "target": "더프리미엄효성", "type": "ownership", "detail": "2016년 효성토요타로부터 70% 지분 매입"},
        ],
        "risks": [
            {"type": "financial", "description": "더프리미엄효성 2023년 매출 429억원으로 2018년 대비 60% 수준 하락", "severity": "high"},
            {"type": "financial", "description": "효성프리미어모터스 2019년 이후 완전 자본잠식 상태 지속", "severity": "high"},
            {"type": "financial", "description": "아승오토모티브그룹 2022년 매출 8억5,000만원, 순손실 9억1,000만원으로 자본잠식 악화", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/431",
        "title": "조현준 회장은 갤럭시아그룹을 어떻게 일구었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-05",
        "summary": "조현준 회장은 1976년 설립된 트리니티에셋매니지먼트를 통해 효성그룹의 자산과 금융 지원을 활용하여 갤럭시아그룹을 성장시킴. 효성캐피탈의 대출금과 유상증자를 통해 갤럭시아일렉트로닉스, 갤럭시아머니트리, 갤럭시아에스엠 등 계열사를 확장.",
        "entities": [
            {"type": "person", "name": "조현준", "role": "회장, 갤럭시아그룹 총수"},
            {"type": "person", "name": "조현문", "role": "전부사장"},
            {"type": "person", "name": "조현상", "role": "부회장"},
            {"type": "company", "name": "트리니티에셋매니지먼트", "role": "조현준 회장 개인회사"},
            {"type": "company", "name": "갤럭시아그룹", "role": "조현준 회장 최대주주 그룹"},
            {"type": "company", "name": "효성캐피탈", "role": "금융 지원"},
        ],
        "relations": [
            {"source": "조현준", "target": "트리니티에셋매니지먼트", "type": "ownership", "detail": "2005년 이후 80% 대주주"},
            {"source": "트리니티에셋매니지먼트", "target": "갤럭시아일렉트로닉스", "type": "investment", "detail": "2009년 100억원 유상증자 참여, 18.18% 지분 취득"},
            {"source": "효성캐피탈", "target": "트리니티에셋매니지먼트", "type": "lending", "detail": "2009년 100억원 차입"},
        ],
        "risks": [
            {"type": "governance", "description": "조현준 회장이 효성그룹과 갤럭시아그룹의 동시 지배로 인한 이해관계 충돌 가능성", "severity": "high"},
            {"type": "financial", "description": "개인회사들의 대규모 차입을 통한 자산 증가로 재무 건전성 악화 우려", "severity": "high"},
            {"type": "governance", "description": "효성 계열사 자금을 활용한 갤럭시아그룹 확장으로 소수주주 이익 침해 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/430",
        "title": "조현준•현상 형제는 어떻게 효성그룹 최대주주 되었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-06-01",
        "summary": "조현준 회장과 조현상 부회장은 2018년 효성의 인적분할을 통해 각각 21.94%, 21.92%의 지분을 확보하여 최대주주가 됨. 두 형제는 2003년부터 15년간 2,300억원 이상을 투자하여 주식을 매입했으며, 2013년 이후 증권사 차입금을 활용.",
        "entities": [
            {"type": "person", "name": "조현준", "role": "효성 회장, 1대주주"},
            {"type": "person", "name": "조현상", "role": "효성 부회장, 2대주주"},
            {"type": "person", "name": "조석래", "role": "효성 명예회장"},
            {"type": "company", "name": "㈜효성", "role": "지주회사"},
            {"type": "company", "name": "효성화학", "role": "분할 신설사"},
            {"type": "company", "name": "효성중공업", "role": "분할 신설사"},
        ],
        "relations": [
            {"source": "조현준", "target": "㈜효성", "type": "ownership", "detail": "21.94% 지분 보유(2022년말 기준)"},
            {"source": "조현상", "target": "㈜효성", "type": "ownership", "detail": "21.92% 지분 보유(2022년말 기준)"},
        ],
        "risks": [
            {"type": "financial", "description": "2020년 3월 기준 조현준 회장 462만주 중 428만주, 조현상 부회장 451만주 중 363만주가 담보로 제공, 2,000억원 이상 미상환 차입금 가능", "severity": "high"},
            {"type": "governance", "description": "개인회사 3곳이 배당 수익을 받지 않으면서 지분 승계 구조 투명성 부족", "severity": "medium"},
            {"type": "regulatory", "description": "담보계약 관련 2020년 3월 이후 공시 누락", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/429",
        "title": "효성 계열사를 세입자로 둔 건물주",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-05-30",
        "summary": "효성그룹의 3형제(조현준, 조현문, 조현상)가 소유한 부동산임대업체들이 그룹 계열사를 세입자로 확보하고 있음. 트리니티에셋매니지먼트와 신동진은 각각 효성 계열사로부터 수십억원대의 임대수입을 올리고 있으며, 조현상 부회장은 2015~2016년 수입자동차 사업을 개인소유로 전환.",
        "entities": [
            {"type": "person", "name": "조현준", "role": "효성 회장"},
            {"type": "person", "name": "조현상", "role": "효성 부회장"},
            {"type": "person", "name": "조현문", "role": "효성 전 부사장"},
            {"type": "company", "name": "트리니티에셋매니지먼트", "role": "부동산임대업(조현준 소유)"},
            {"type": "company", "name": "신동진", "role": "부동산임대업(조현상 소유)"},
            {"type": "company", "name": "동륭실업", "role": "부동산임대업(조현문 소유)"},
        ],
        "relations": [
            {"source": "조현준", "target": "트리니티에셋매니지먼트", "type": "ownership", "detail": "100% 소유"},
            {"source": "트리니티에셋매니지먼트", "target": "효성 계열사", "type": "landlord_tenant", "detail": "연 28억원 임대수입"},
            {"source": "신동진", "target": "효성 계열사", "type": "landlord_tenant", "detail": "연 92억원 임대수입"},
        ],
        "risks": [
            {"type": "governance", "description": "형제간 승계 경쟁으로 인한 지배구조 불안정. 조현문의 '효성 형제의 난' 이후 경영진 갈등 존재", "severity": "high"},
            {"type": "regulatory", "description": "신동진, 트리니티에셋매니지먼트, 동륭실업이 2010년 공정거래위원회에 위장계열사로 고발됨", "severity": "medium"},
            {"type": "financial", "description": "신동진과 트리니티에셋매니지먼트의 50% 이상 매출이 관계사 임대료에 의존", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/428",
        "title": "눈덩이처럼 불어나는 차입금을 어찌할까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-05-25",
        "summary": "LG디스플레이의 차입금이 2017년 말 대비 3배 증가한 17조원을 넘어섰으며, 영업활동 현금흐름 악화로 인한 심각한 재무 부담에 직면. 신용평가사들은 신용등급을 하향 조정하거나 부정적 전망을 부여.",
        "entities": [
            {"type": "company", "name": "LG디스플레이", "role": "주요 피분석 기업"},
            {"type": "company", "name": "LG전자", "role": "최대주주"},
            {"type": "company", "name": "삼성디스플레이", "role": "경쟁사"},
            {"type": "company", "name": "BOE", "role": "중국 경쟁사"},
        ],
        "relations": [
            {"source": "LG디스플레이", "target": "LG전자", "type": "ownership", "detail": "최대주주로서 2023년 총 1조원 차입 제공"},
            {"source": "LG디스플레이", "target": "삼성디스플레이", "type": "competition", "detail": "중소형 OLED 시장에서 경쟁"},
        ],
        "risks": [
            {"type": "financial", "description": "차입금의존도가 2017년말 19%에서 2023년 3월말 47%로 급증", "severity": "critical"},
            {"type": "operational", "description": "2023년 1분기 EBITDA 적자(802억원) 및 영업활동 현금흐름 순유출(약 6000억원)", "severity": "critical"},
            {"type": "market", "description": "글로벌 경기침체로 대형 OLED TV 수요 둔화, 중소형 OLED에서 중국업체 추격 가속화", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/427",
        "title": "2019년의 재판? 극적인 회복?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-05-22",
        "summary": "LG디스플레이는 2021년 역대 최고 실적 이후 급격한 추락을 겪고 있으며, 지난해 3조원 이상의 적자에 이어 올해 1분기에 1조1000억원 이상의 손실을 기록. 전방산업 위축과 중국 경쟁업체의 추격으로 인한 것.",
        "entities": [
            {"type": "company", "name": "LG디스플레이", "role": "주요 대상기업"},
            {"type": "company", "name": "AU옵트로닉스", "role": "경쟁사"},
            {"type": "company", "name": "BOE", "role": "경쟁사"},
            {"type": "company", "name": "삼성디스플레이", "role": "경쟁사"},
        ],
        "relations": [
            {"source": "LG디스플레이", "target": "삼성디스플레이", "type": "competition", "detail": "중소형 OLED 패널 시장에서 경쟁, 차량용 OLED 패널 시장 양분"},
        ],
        "risks": [
            {"type": "financial", "description": "차입금 17조원 초과로 인한 상환 부담, 영업현금흐름 부재 상황에서 빚 상환 어려움", "severity": "critical"},
            {"type": "market", "description": "전방산업 위축과 고정비 회수 불가능한 매출 수준(손익분기점 이하)", "severity": "critical"},
            {"type": "operational", "description": "4분기 연속 적자, 올해 1분기 매출 31.8% 급감", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/426",
        "title": "그룹 신용도의 우산, 롯데케미칼이 흔들린다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-05-18",
        "summary": "롯데케미칼은 2022년 7000억원대의 영업적자를 기록하며 그룹 전체 실적을 악화시켰으며, 신용평가사들이 신용등급에 '부정적' 전망을 붙임. 차입금이 3.6조에서 6조원을 넘어섰고, 대규모 M&A와 투자로 인해 재무구조가 악화.",
        "entities": [
            {"type": "company", "name": "롯데케미칼", "role": "롯데그룹의 주력 계열사"},
            {"type": "company", "name": "롯데지주", "role": "롯데그룹의 지주회사"},
            {"type": "company", "name": "일진머티리얼즈", "role": "롯데케미칼의 인수 대상"},
            {"type": "company", "name": "롯데건설", "role": "유동성 위기 계열사"},
        ],
        "relations": [
            {"source": "롯데케미칼", "target": "롯데지주", "type": "group_subsidiary", "detail": "롯데그룹의 주력 계열사로서 그룹 신용도에 영향"},
            {"source": "롯데케미칼", "target": "일진머티리얼즈", "type": "acquisition", "detail": "2조7000억원에 인수"},
            {"source": "롯데케미칼", "target": "롯데건설", "type": "financial_support", "detail": "5000억원 대여금 및 876억원 유상증자 참여"},
        ],
        "risks": [
            {"type": "financial", "description": "차입금이 3.6조에서 6조원을 초과로 급증, 순차입금/EBITDA 배율이 16.7배에 달함", "severity": "critical"},
            {"type": "financial", "description": "EBITDA마진 0.8%, 총차입금/EBITDA 34배로 신용평가사의 하향 가이드라인 기준 크게 하회", "severity": "critical"},
            {"type": "governance", "description": "롯데케미칼의 신용등급 하락 시 롯데지주, 롯데물산, 롯데렌탈 등 계열사도 연쇄적 영향", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/425",
        "title": "주력 계열사 줄줄이 볼모 만든 롯데건설",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-05-15",
        "summary": "롯데건설의 부동산PF 유동성위기 해결 과정에서 롯데케미칼, 호텔롯데, 롯데물산 등 주력 계열사들이 총동원되어 지원. 메리츠금융그룹과의 투자협약을 통해 1조5000억원을 조달했으나 13% 고금리 차입금이 크게 증가하여 재무구조가 훼손.",
        "entities": [
            {"type": "company", "name": "롯데건설", "role": "주요 관심 대상사"},
            {"type": "company", "name": "롯데케미칼", "role": "최대주주"},
            {"type": "company", "name": "호텔롯데", "role": "2대 주주"},
            {"type": "company", "name": "롯데물산", "role": "지원 계열사"},
            {"type": "company", "name": "메리츠금융그룹", "role": "채권자"},
        ],
        "relations": [
            {"source": "롯데케미칼", "target": "롯데건설", "type": "financial_support", "detail": "유상증자 참여, 2500억원 공모사채 보증"},
            {"source": "메리츠금융그룹", "target": "롯데건설", "type": "creditor_relationship", "detail": "9000억원 선순위 대출(13% 이자)"},
        ],
        "risks": [
            {"type": "financial", "description": "롯데건설의 지난해 외부자금 조달(차입)이 3조원에 육박하며 대부분 단기차입금으로 구성", "severity": "critical"},
            {"type": "financial", "description": "부동산PF 유동화증권 회수금이 메리츠금융그룹 선순위 대출 상환 후에야 계열사 후순위 대여금 상환 가능", "severity": "high"},
            {"type": "governance", "description": "롯데건설 지원을 위해 부정적 등급 전망 중인 롯데케미칼, 롯데물산, 롯데지주 등이 동원됨", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/424",
        "title": "SK온의 신용 공동체 SK이노베이션, 다시 기로에",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-05-08",
        "summary": "SK이노베이션의 신용등급이 2020-2021년 AA+에서 AA로 하락했으며, SK온의 대규모 차입금 증가(약 12조원)가 모회사의 재무 부담을 가중. SK온은 영업활동 현금흐름이 음수(―2조원)이면서도 설비투자에 4조9000억원을 소비하여 외부차입에 의존.",
        "entities": [
            {"type": "company", "name": "SK이노베이션", "role": "모회사, 신용등급 AA로 하향조정"},
            {"type": "company", "name": "SK온", "role": "자회사, 대규모 차입금 증가 주도"},
            {"type": "company", "name": "SK루브리컨츠", "role": "자회사, 지분 40% 매각"},
        ],
        "relations": [
            {"source": "SK이노베이션", "target": "SK온", "type": "parent-subsidiary", "detail": "2021년 10월 분할설립, 차입금 의존성 증가"},
            {"source": "SK온", "target": "SK이노베이션", "type": "financial_burden", "detail": "연결 차입금 67% 비중, 신용등급 하향 위험 초래"},
        ],
        "risks": [
            {"type": "financial", "description": "SK온 차입금의존도 50.8%, 전체 차입금의 53%가 단기성(올해 상환기한)", "severity": "critical"},
            {"type": "operational", "description": "EBITDA 6조원 대비 영업현금흐름 4000억원으로 괴리, 매출채권·재고자산 급증", "severity": "critical"},
            {"type": "financial", "description": "SK온 현금부족 7조원, 영업현금흐름 마이너스(―2조원) 지속 예상", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/423",
        "title": "SK온의 수율 이슈, 그룹 신용등급 위협할지도",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-05-04",
        "summary": "SK온의 낮은 수율(70% 이하)이 영업적자 지속의 주요 원인으로 지적. LG에너지솔루션과 삼성SDI의 수율이 90% 이상인 반면, SK온의 매출원가율은 99.9%에 달해 수익성이 심각. 수율 개선 실패 시 SK온의 차입금 증가가 모회사와 지배회사의 신용등급까지 위협할 수 있음.",
        "entities": [
            {"type": "company", "name": "SK온", "role": "전기차 배터리 제조업체"},
            {"type": "company", "name": "LG에너지솔루션", "role": "경쟁사"},
            {"type": "company", "name": "삼성SDI", "role": "경쟁사"},
            {"type": "company", "name": "SK이노베이션", "role": "SK온의 모회사"},
            {"type": "company", "name": "SK㈜", "role": "SK그룹 지배회사"},
        ],
        "relations": [
            {"source": "SK온", "target": "SK이노베이션", "type": "subsidiary", "detail": "자금지원 의존, 차입금 증가 예상"},
            {"source": "SK온", "target": "LG에너지솔루션", "type": "competitor", "detail": "수율 70% vs 90% 이상, 매출원가율 99.9% vs 83.2%"},
        ],
        "risks": [
            {"type": "operational", "description": "SK온의 헝가리·미국 공장 수율이 70% 이하로 경쟁사 대비 현저히 낮음", "severity": "critical"},
            {"type": "financial", "description": "2023년 영업적자 1조원 초과, 누적손실 3조3000억원. 매출원가율 99.9%로 수익 구조 붕괴 상태", "severity": "critical"},
            {"type": "governance", "description": "SK온의 신용등급 하락 시 모회사 SK이노베이션, 지배회사 SK㈜의 신용등급도 위협 받을 수 있음", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/422",
        "title": "SK하이닉스, 어쩌다 그룹의 약한 고리 되었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-05-01",
        "summary": "SK하이닉스는 호황기 막대한 차입금으로 대규모 투자를 진행했으나, 메모리반도체 업황 악화로 현금흐름이 악화되어 신용도가 흔들리고 있음. 해외 교환사채 발행(2조2377억원)은 추가 차입금 증가를 회피하려는 의도.",
        "entities": [
            {"type": "company", "name": "SK하이닉스", "role": "메모리반도체 제조업체"},
            {"type": "company", "name": "SK㈜", "role": "SK그룹 최상위 지주회사"},
            {"type": "company", "name": "SK이노베이션", "role": "배터리·에너지 사업"},
            {"type": "person", "name": "최태원", "role": "SK그룹 회장"},
        ],
        "relations": [
            {"source": "SK하이닉스", "target": "SK㈜", "type": "subsidiary", "detail": "SK그룹 최상위 지주회사의 계열사"},
            {"source": "SK하이닉스", "target": "인텔", "type": "acquisition", "detail": "중국 낸드플래시 사업부 인수(90억 달러, 약 11조원, 2021년)"},
        ],
        "risks": [
            {"type": "financial", "description": "부채비율 36%에서 64%로 상승(2019년 말~2022년 말), 3년간 순차입 10조7000억원", "severity": "critical"},
            {"type": "financial", "description": "단기차입금 비중 31%로 상승, 올해 상환해야 할 차입금 7조4000억원", "severity": "critical"},
            {"type": "regulatory", "description": "미국의 대중 반도체 규제 강화로 중국 공장 설비투자 제약, 사양화 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/421",
        "title": "시장은 왜 SK그룹의 신용을 걱정하나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-04-27",
        "summary": "SK그룹의 차입금이 100조원을 넘어 4년 만에 2.5배 증가하면서 신용 우려가 커지고 있음. 영업활동 현금흐름은 감소했으나 설비투자와 지분투자는 지속적으로 증가하여 잉여현금흐름이 음수(−13조원 이상)를 기록.",
        "entities": [
            {"type": "company", "name": "SK그룹", "role": "주요 대상"},
            {"type": "company", "name": "SK하이닉스", "role": "그룹 최대 자산 회사"},
            {"type": "company", "name": "SK이노베이션", "role": "에너지·화학 부문 계열사"},
            {"type": "company", "name": "SK E&S", "role": "에너지·화학 부문 계열사"},
        ],
        "relations": [
            {"source": "SK그룹", "target": "SK하이닉스", "type": "subsidiary", "detail": "관계회사로 분류되며 자산규모 104조원"},
        ],
        "risks": [
            {"type": "financial", "description": "계열 통합 차입금이 100조원을 넘어섰으며 부채비율 120.9% 도달", "severity": "critical"},
            {"type": "financial", "description": "단기성차입금 비중 36.1%로 높아 단기 상환부담 증가", "severity": "high"},
            {"type": "operational", "description": "잉여현금흐름이 (-)13조원 이상 - 영업활동 현금흐름 감소로 투자 자금 조달 곤란", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/420",
        "title": "SK쉴더스 매각은 '성과'인가",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-04-24",
        "summary": "SK스퀘어가 SK쉴더스 지분을 스웨덴 사모펀드 EQT파트너스에 약 2조원에 매각하기로 결정. 순자산가치 75조원 목표 달성을 위한 전략적 선택으로 평가되나, 단기적으로는 최대 종속회사 상실과 현금 확보 부족으로 인한 일보 후퇴로 보임.",
        "entities": [
            {"type": "company", "name": "SK스퀘어", "role": "SK쉴더스 지분 매각사"},
            {"type": "company", "name": "EQT파트너스", "role": "인수사, 최대주주"},
            {"type": "company", "name": "SK쉴더스", "role": "매각 대상"},
            {"type": "company", "name": "SK하이닉스", "role": "SK스퀘어의 주요 관계회사"},
            {"type": "person", "name": "박정호", "role": "SK스퀘어 부회장"},
        ],
        "relations": [
            {"source": "SK스퀘어", "target": "SK쉴더스", "type": "ownership_change", "detail": "지분율 63.1%에서 32%로 감소, 최대주주에서 2대주주로 변경"},
            {"source": "EQT파트너스", "target": "SK쉴더스", "type": "investment", "detail": "약 2조원에 68% 지분 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "SK쉴더스 매각으로 SK스퀘어의 최대 종속회사 상실, 매출 공백 약 1조7377억원 발생", "severity": "high"},
            {"type": "financial", "description": "매각대금 8646억원 중 4000억원을 인수자에게 대출하여 실질 현금 확보 제한적", "severity": "high"},
            {"type": "governance", "description": "SK그룹이라는 우산이 사라지면서 신용등급 하락 가능성 - A등급에서 A-로 강등 위험", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/419",
        "title": "2대 주주 한국타이어에게 한온시스템이란?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-04-20",
        "summary": "한온시스템의 배당금은 한국타이어에게 연평균 890억원의 중요한 현금흐름 원천이 되어왔으며, 지난 7년간 수취한 배당금 총액 2764억원 중 87%를 한온시스템에서 받음. 현재 한국타이어는 경영진 구속, 본업 부진, 대규모 설비투자 계획으로 인해 유동성 압박이 심화.",
        "entities": [
            {"type": "company", "name": "한온시스템", "role": "피인수 회사, 배당금 지급사"},
            {"type": "company", "name": "한국타이어앤테크놀로지", "role": "2대 주주, 19.49% 지분 보유"},
            {"type": "company", "name": "한앤컴퍼니", "role": "최대주주, 인수사"},
            {"type": "person", "name": "조현범", "role": "한국타이어 회장, 횡령·배임 혐의 구속 기소"},
        ],
        "relations": [
            {"source": "한앤컴퍼니", "target": "한온시스템", "type": "acquisition", "detail": "2015년 6월 인수 완료, 현재 경영권 지분 매각 추진 중"},
            {"source": "한국타이어", "target": "한온시스템", "type": "investment", "detail": "1조819억원 투입하여 19.49% 지분 취득"},
        ],
        "risks": [
            {"type": "financial", "description": "한국타이어 본사의 영업이익이 2년 연속 적자 기록 중이며, 현금부족액이 1200억원 초과", "severity": "critical"},
            {"type": "financial", "description": "차입금 1조9365억원 중 70%인 1조3514억원이 올해 만기 도래", "severity": "critical"},
            {"type": "governance", "description": "회장 조현범이 200억원대 횡령·배임 혐의로 구속 기소되어 경영 공백 및 신뢰 하락", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/418",
        "title": "한온시스템, 실적 부진에도 배당금 줄일 수 없는 이유",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-04-17",
        "summary": "한앤컴퍼니가 2015년 2조8400억원에 인수한 한온시스템은 대형 M&A와 설비투자로 매출을 키웠으나, 배당금과 이자부담으로 순차입금이 2조8384억원까지 증가. 인수금융 이자 부담으로 인해 배당금을 줄이기 어려운 구조.",
        "entities": [
            {"type": "company", "name": "한온시스템", "role": "인수 대상 기업"},
            {"type": "company", "name": "한앤컴퍼니", "role": "사모펀드, 인수 주체"},
            {"type": "company", "name": "한앤코오토홀딩스", "role": "특수목적회사"},
            {"type": "company", "name": "마그나", "role": "인수 대상 (유압제어장치부문)"},
        ],
        "relations": [
            {"source": "한앤컴퍼니", "target": "한온시스템", "type": "acquisition", "detail": "2015년 2조8400억원에 인수, 인수금융 1조7000억원 + 출자금 1조1400억원"},
            {"source": "한온시스템", "target": "마그나", "type": "acquisition", "detail": "2019년 유압제어장치부문 약 1조4000억원 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "순차입금 2조8384억원으로 증가, 배당금 부담(연 2000억원)으로 인해 현금흐름 악화", "severity": "high"},
            {"type": "operational", "description": "배당금을 주지 않으면 인수금융 이자를 밀리게 된다는 악순환 구조로 배당금 감액 곤란", "severity": "critical"},
            {"type": "financial", "description": "현재 역사적 고금리 환경에서 재파이낸싱 시 금리 4% 이상으로 이자부담 증가 우려", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/417",
        "title": "한온시스템은 왜 대규모 현금부족에 빠졌나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-04-13",
        "summary": "한온시스템이 2022년 영업이익 2566억원으로 전년 대비 21.2% 감소하며 실적 부진을 기록. 매출은 8조원대로 증가했으나 마그나 유압제어부문 인수 이후 영업이익은 악화되었으며, 특히 과도한 배당금 지급으로 인한 현금흐름 부족이 심각.",
        "entities": [
            {"type": "company", "name": "한온시스템", "role": "피인수기업"},
            {"type": "company", "name": "한앤컴퍼니", "role": "사모펀드 운영사 (50.5% 지분 보유)"},
            {"type": "company", "name": "한국타이어앤테크놀로지", "role": "투자자 (19.49% 지분 보유)"},
            {"type": "company", "name": "마그나", "role": "유압제어부문 매각사"},
        ],
        "relations": [
            {"source": "한앤컴퍼니", "target": "한온시스템", "type": "ownership", "detail": "2015년 3조9400억원으로 69.99% 인수"},
            {"source": "한온시스템", "target": "마그나 유압제어부문", "type": "acquisition", "detail": "2019년 약 1조4000억원으로 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "현금흐름 부족: 영업활동 현금이 자본적지출과 배당을 감당하지 못함", "severity": "critical"},
            {"type": "financial", "description": "차입금 급증: 3조원대에 육박하며 기업가치 평가 시 차감 요인", "severity": "critical"},
            {"type": "operational", "description": "마그나 유압제어부문 가동률 저조: 아시아 35%, 미주 52%, 유럽 48%", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/416",
        "title": "불거진 보험사 유동성위험, 아직 안 끝났다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-04-10",
        "summary": "국내 보험사들이 IFRS17 회계기준 전환과 K-ICS 신지급여력제도 도입으로 자본부담이 증가하면서 신종자본증권 발행에 어려움을 겪고 있음. 올해 약 4조원 규모의 신종자본증권 만기도래로 유동성 위험이 재발될 수 있음.",
        "entities": [
            {"type": "company", "name": "삼성생명", "role": "국내 최대 보험사"},
            {"type": "company", "name": "농협생명보험", "role": "신종자본증권 발행사"},
            {"type": "company", "name": "흥국생명", "role": "신종자본증권 조기상환 사례"},
            {"type": "company", "name": "크레디스위스", "role": "코코본드 전액상각 사례사"},
        ],
        "relations": [
            {"source": "IFRS17", "target": "보험사 자본부담", "type": "causes_increase", "detail": "자산·부채 시가평가 의무화로 순자산 변동성 확대"},
            {"source": "크레디스위스 코코본드 상각", "target": "보험사 코코본드 발행 회피", "type": "causes", "detail": "시장 투자심리 악화로 신종자본증권으로 회귀"},
        ],
        "risks": [
            {"type": "financial", "description": "올해 4조원 규모 신종자본증권 만기도래로 유동성 위기 재발 가능성", "severity": "high"},
            {"type": "regulatory", "description": "스텝업 조항 있는 신종자본증권이 K-ICS 기본자본으로 불인정되면서 자본 충당의 어려움", "severity": "high"},
            {"type": "operational", "description": "콜옵션 행사 기한 도래 시 신규 자금조달 없이는 조기상환 불가능", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/415",
        "title": "국내 보험사들, 돈 없어 쩔쩔맸다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-04-06",
        "summary": "국내 보험사들이 2022년 금리 급등으로 인한 심각한 유동성 위기에 직면. 저축성보험 의존도가 높은 생보사들은 '들어오는 보험료는 줄고 지급하는 보험금은 늘고, 보유자산의 가치는 하락'하는 3중고를 겪음.",
        "entities": [
            {"type": "company", "name": "흥국생명", "role": "유동성 위기 사례"},
            {"type": "company", "name": "KB생명", "role": "KB라이프생명에 흡수, 음수 수지차비율"},
            {"type": "company", "name": "DGB생명", "role": "유상증자 실시"},
            {"type": "company", "name": "농협생명", "role": "유상증자 후 자본금 전액잠식"},
        ],
        "relations": [
            {"source": "금리 급등", "target": "보유 유가증권 가치 하락", "type": "causation", "detail": "2022년 하반기 금리 급등으로 인해 보유 채권 가치 급감"},
        ],
        "risks": [
            {"type": "financial", "description": "생보사 수지차비율이 음(-)의 값 기록, 평균지급보험금 79조원 도달", "severity": "critical"},
            {"type": "operational", "description": "초단기 RP매도에 의존한 유동성 확보로 근본적 개선 미흡", "severity": "high"},
            {"type": "regulatory", "description": "기존 지급여력비율(RBC)제도가 실제 유동성 위기 상황에서 실효성 부재", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/414",
        "title": "국내은행 코코본드에도 위기 올까",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-04-03",
        "summary": "크레디트스위스의 코코본드 전액 상각으로 조건부자본증권 위기 가능성이 제기. 국내 은행들은 기본자본에서 신종자본증권 비중이 낮고 BIS자기자본비율이 충분해 즉각적 위험은 낮으나, 향후 신종자본증권 발행 환경이 악화될 것으로 예상.",
        "entities": [
            {"type": "company", "name": "크레디트스위스", "role": "코코본드 상각으로 위기 촉발"},
            {"type": "company", "name": "UBS", "role": "크레디트스위스 인수"},
            {"type": "company", "name": "도이치뱅크", "role": "위기설 영향을 받은 은행"},
            {"type": "company", "name": "흥국생명", "role": "신종자본증권 조기상환 사례"},
        ],
        "relations": [
            {"source": "크레디트스위스", "target": "코코본드", "type": "발행", "detail": "금융위기 상황에서 전액 상각됨"},
        ],
        "risks": [
            {"type": "market", "description": "코코본드 전액 상각으로 국내 채권 투자자의 신종자본증권 신뢰도 하락 우려", "severity": "high"},
            {"type": "operational", "description": "부동산PF 문제 악화 시 신종자본증권 상각 가능성", "severity": "high"},
            {"type": "financial", "description": "보험사 지급여력비율 마지노선 근처 상황으로 자본확충 필요 증가", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (20차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:40]}...")
        else:
            print(f"[FAIL] {article['title'][:40]}... - {result.get('error', 'Unknown error')}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
