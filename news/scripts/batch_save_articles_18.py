#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 18차 (479-458)
그로우스앤밸류, CBI/KINETA, 대양금속/영풍제지, 에스엘에너지 시리즈
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/479",
        "title": "이호준•오경원 콤비의 그로우스앤밸류, 스몰캡시장 황금손?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-12-11",
        "summary": "그로우스앤밸류는 이호준·오경원 콤비가 주도. 자본잠식 상태이면서도 스몰캡 기업들에 높은 수익률. 재무정보 신뢰성 문제 제기.",
        "entities": [
            {"type": "company", "name": "그로우스앤밸류디벨로프먼트", "role": "투자회사"},
            {"type": "company", "name": "비덴트", "role": "상장사 (구 티브이로직)"},
            {"type": "company", "name": "에이프로젠KIC", "role": "상장사"},
            {"type": "company", "name": "CBI", "role": "상장사"},
            {"type": "company", "name": "DGP", "role": "상장사"},
            {"type": "person", "name": "이호준", "role": "그로우스앤밸류 대표"},
            {"type": "person", "name": "오경원", "role": "그로우스앤밸류 부회장"},
            {"type": "person", "name": "성봉두", "role": "CBI 부사장"},
            {"type": "person", "name": "김재섭", "role": "에이프로젠그룹 회장"},
        ],
        "relations": [
            {"source": "이호준", "target": "그로우스앤밸류디벨로프먼트", "type": "management", "detail": "대표"},
            {"source": "그로우스앤밸류", "target": "비덴트", "type": "ownership", "detail": "2015년 최대주주"},
        ],
        "risks": [
            {"type": "regulatory", "description": "5% 이상 대량보유자 공시 부실", "severity": "high"},
            {"type": "financial", "description": "자산 83억원 대비 부채 85억원, 완전 자본잠식", "severity": "high"},
            {"type": "market", "description": "투자처 기업들 중 시세조정 의혹 다수", "severity": "medium"},
            {"type": "governance", "description": "투자 시점에 상호변경, 최대주주변경 빈번", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/478",
        "title": "광산업체 구보와 김용우 대표이사, 누구세요?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-12-07",
        "summary": "신발도매업 구보가 광산업체로 변신, 쌍전광산 광업권 확보. CBI가 100억원 투자하며 주목.",
        "entities": [
            {"type": "company", "name": "CBI", "role": "투자사"},
            {"type": "company", "name": "구보", "role": "광업권 보유사"},
            {"type": "company", "name": "알몬티코리아", "role": "상동광산 관련"},
            {"type": "company", "name": "크리트민", "role": "싱가포르 전 광업권 보유"},
            {"type": "person", "name": "김용우", "role": "구보 공동대표, 알몬티 대표"},
            {"type": "person", "name": "이호준", "role": "CBI 사장, 구보 사내이사"},
        ],
        "relations": [
            {"source": "구보", "target": "CBI", "type": "investment", "detail": "전환사채-우선주 교환"},
            {"source": "김용우", "target": "구보", "type": "management", "detail": "2023년 4월 임원 진입"},
            {"source": "크리트민코리아", "target": "구보", "type": "sale", "detail": "2023년 10월 광업권 매각"},
        ],
        "risks": [
            {"type": "governance", "description": "현금 아닌 채권/우선주 교환으로 실제 자금흐름 불명확", "severity": "high"},
            {"type": "governance", "description": "자본금 1억원 신발도매업체가 광산업체로 급변신", "severity": "high"},
            {"type": "governance", "description": "김용우가 구보/알몬티코리아 동시 대표, 관계 불명확", "severity": "medium"},
            {"type": "regulatory", "description": "14.2% 지분으로 최대주주 추월하나 변경 공시 미발표", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/477",
        "title": "배보다 배꼽이 큰 CBI 실적",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-12-04",
        "summary": "CBI(구 청보산업) 매출 360억원 사상 최고이나 영업이익 4억원. 금융자산 평가손실 216억원 등 영업외 손실로 297억원 순손실.",
        "entities": [
            {"type": "company", "name": "CBI", "role": "자동차부품/신약개발 투자"},
            {"type": "company", "name": "그로우스앤밸류디벨로프먼트", "role": "2020년 경영권 인수"},
            {"type": "company", "name": "KINETA", "role": "투자대상"},
            {"type": "company", "name": "SBW생명과학", "role": "투자대상"},
        ],
        "relations": [
            {"source": "CBI", "target": "그로우스앤밸류디벨로프먼트", "type": "acquisition", "detail": "경영권 인수"},
            {"source": "CBI", "target": "KINETA", "type": "investment", "detail": "투자"},
        ],
        "risks": [
            {"type": "financial", "description": "384억원 연결기준 영업손실, 297억원 순손실", "severity": "high"},
            {"type": "financial", "description": "KINETA 172억원→54억원, SBW 50억원→9억원 평가손", "severity": "high"},
            {"type": "operational", "description": "신사업(ESG,ECV,UAM)은 구호뿐, 매출은 기존 부품에만 의존", "severity": "medium"},
            {"type": "governance", "description": "직원 104→45명 감소에도 급여 40→62억원 증가", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/476",
        "title": "CBI는 어떻게 전환사채 공장이 되었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-11-30",
        "summary": "청보산업이 2021년 경영권 인수 후 CBI로 변모, 대규모 전환사채 발행. KINETA 등 바이오벤처 투자. 60년 자동차부품 사업 포기.",
        "entities": [
            {"type": "company", "name": "CBI", "role": "전환사채 발행/투자"},
            {"type": "company", "name": "청보산업", "role": "CBI 전신"},
            {"type": "company", "name": "그로우스앤밸류", "role": "최대주주, 경영권 인수"},
            {"type": "company", "name": "KINETA", "role": "미국 항암 신약개발"},
            {"type": "company", "name": "인트로메딕", "role": "의료기기 상장사"},
            {"type": "company", "name": "구보", "role": "광업권 보유"},
            {"type": "person", "name": "오경원", "role": "그로우스앤밸류 부회장"},
            {"type": "person", "name": "이호준", "role": "그로우스앤밸류 대표"},
        ],
        "relations": [
            {"source": "그로우스앤밸류", "target": "CBI", "type": "acquisition", "detail": "경영권 인수"},
            {"source": "CBI", "target": "KINETA", "type": "investment", "detail": "투자"},
        ],
        "risks": [
            {"type": "financial", "description": "전환사채 170억원 + BW 발행으로 희석 위험", "severity": "high"},
            {"type": "financial", "description": "KINETA 등 해외 바이오벤처 투자로 연 177억원 손실", "severity": "high"},
            {"type": "governance", "description": "경영진 전원 교체 후 무자본 M&A 전략으로 기존 사업 포기", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/475",
        "title": "KINETA로 엮인 관계 정리하고 새판 짜는 중?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-11-27",
        "summary": "CBI와 율호가 KINETA 투자 관련 지분 매각 추진. 제이제이더웰 등 의심스러운 투자조합 개입. 쌍방울그룹 위기 이후 경영권 변경.",
        "entities": [
            {"type": "company", "name": "씨비아이", "role": "KINETA 투자 주도"},
            {"type": "company", "name": "율호", "role": "KINETA 공동 투자"},
            {"type": "company", "name": "디지피", "role": "CBI 최대주주"},
            {"type": "company", "name": "제이제이더웰", "role": "DGP/투자조합 양수인"},
            {"type": "company", "name": "SBW생명과학", "role": "지브이비티4호조합 보유"},
            {"type": "company", "name": "미래산업", "role": "쌍방울그룹 계열사"},
            {"type": "company", "name": "이엔플러스", "role": "율호 최대주주 예정"},
            {"type": "person", "name": "이호준", "role": "CBI 사장"},
            {"type": "person", "name": "김성태", "role": "쌍방울그룹 회장 (구속)"},
        ],
        "relations": [
            {"source": "이호준", "target": "CBI", "type": "management", "detail": "사장"},
            {"source": "CBI", "target": "KINETA", "type": "investment", "detail": "투자"},
            {"source": "제이제이더웰", "target": "DGP", "type": "acquisition", "detail": "매수계약 (미이행)"},
            {"source": "이엔플러스", "target": "율호", "type": "ownership", "detail": "최대주주 변경 예정"},
        ],
        "risks": [
            {"type": "governance", "description": "제이제이더웰 실제 주소 간판 없음, 서류상 회사 가능성", "severity": "high"},
            {"type": "governance", "description": "DGP 지분 매각 3차례 연기, 계약금만 오가고 잔금 지연", "severity": "high"},
            {"type": "governance", "description": "김성태 구속 이후 쌍방울그룹 위기로 거래 중단", "severity": "high"},
            {"type": "financial", "description": "이엔플러스 6개월간 약 900억원 대규모 자금 조달", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/474",
        "title": "KINETA에 홀린 기업들, 접점이 씨비아이?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-11-24",
        "summary": "CBI가 미국 바이오벤처 KINETA에 투자하면서 국내 여러 기업 연쇄 투자. 지브이비티 투자조합 통한 교차투자 네트워크.",
        "entities": [
            {"type": "company", "name": "CBI", "role": "KINETA 주요 투자자"},
            {"type": "company", "name": "KINETA", "role": "미국 면역항암제 개발"},
            {"type": "company", "name": "미래산업", "role": "쌍방울그룹, CBI CB 인수"},
            {"type": "company", "name": "율호", "role": "KINETA 투자"},
            {"type": "company", "name": "SBW생명과학", "role": "CBI와 자금관계"},
            {"type": "company", "name": "휴메딕스", "role": "휴온스그룹, KINETA 투자"},
            {"type": "company", "name": "제네톡스", "role": "KINETA 공동개발"},
            {"type": "company", "name": "DGP", "role": "최대주주 CBI"},
            {"type": "person", "name": "이호준", "role": "CBI 사장"},
            {"type": "person", "name": "안종덕", "role": "제네톡스 최대주주/대표"},
        ],
        "relations": [
            {"source": "CBI", "target": "KINETA", "type": "investment", "detail": "주식/CB 인수"},
            {"source": "미래산업", "target": "CBI", "type": "investment", "detail": "지브이비티2호조합 통해 CB 인수"},
            {"source": "율호", "target": "KINETA", "type": "investment", "detail": "300만 달러 투자"},
            {"source": "휴메딕스", "target": "KINETA", "type": "investment", "detail": "200만 달러 투자"},
        ],
        "risks": [
            {"type": "financial", "description": "CBI KINETA 투자 172억원→30억원 급락", "severity": "high"},
            {"type": "operational", "description": "제넨텍 라이선스 종료로 수익 790만→100만 달러 급감", "severity": "high"},
            {"type": "operational", "description": "핵심 KVA12123이 2023년 11월 FDA IND 승인, 초기 단계", "severity": "high"},
            {"type": "financial", "description": "KINETA 연간 1500만 달러 R&D 필요하나 수익 창출 부족", "severity": "high"},
            {"type": "governance", "description": "CBI-미래산업-율호-SBW 지브이비티 통해 교차투자, 자금 투명성 문제", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/473",
        "title": "코스닥 3사가 투자한 KINETA의 상장 스토리와 올해 실적",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-11-20",
        "summary": "미국 키네타가 유매니티 테라퓨틱스와 합병해 나스닥 상장. 부채비율 300% 이상 고부담. 국내 3사(CBI, 율호, 휴메딕스) 총 1500만 달러 투자.",
        "entities": [
            {"type": "company", "name": "Kineta", "role": "미국 신약개발"},
            {"type": "company", "name": "씨바아이", "role": "코스닥 상장, 키네타 2대주주"},
            {"type": "company", "name": "율호", "role": "코스닥 상장, 키네타 투자"},
            {"type": "company", "name": "휴메딕스", "role": "휴온스 계열, 키네타 투자"},
            {"type": "company", "name": "유매니티테라퓨틱스", "role": "키네타 합병 대상"},
        ],
        "relations": [
            {"source": "씨바아이", "target": "Kineta", "type": "investment", "detail": "1000만 달러"},
            {"source": "율호", "target": "Kineta", "type": "investment", "detail": "300만 달러"},
            {"source": "휴메딕스", "target": "Kineta", "type": "investment", "detail": "200만 달러"},
            {"source": "Kineta", "target": "유매니티테라퓨틱스", "type": "merger", "detail": "합병"},
        ],
        "risks": [
            {"type": "financial", "description": "부채비율 300% 초과, 누적손실 1631만 달러", "severity": "high"},
            {"type": "financial", "description": "3분기 매출 없음, 9개월 영업적자 1142만 달러", "severity": "high"},
            {"type": "operational", "description": "바이오벤처 성공 확률 매우 낮음", "severity": "high"},
            {"type": "operational", "description": "파트너 Fair Therapeutics 2023년 파산/상장폐지", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/472",
        "title": "최대주주에게 전환사채 콜옵션을 공짜로 준다고?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-11-16",
        "summary": "상장사 전환사채 콜옵션이 최대주주에게 부당한 이득 제공. 정당한 행사대가 없이 콜옵션 부여가 소수주주 부를 경영진으로 이전.",
        "entities": [
            {"type": "company", "name": "뷰노", "role": "코스닥 상장"},
            {"type": "company", "name": "티사이언티픽", "role": "코스닥 상장"},
            {"type": "company", "name": "감성코퍼레이션", "role": "코스닥 상장"},
            {"type": "company", "name": "나인테크", "role": "코스닥 상장"},
            {"type": "person", "name": "이예하", "role": "뷰노 최대주주/대표"},
            {"type": "person", "name": "위지트", "role": "티사이언티픽 최대주주"},
            {"type": "person", "name": "김호선", "role": "감성코퍼레이션 최대주주/대표"},
            {"type": "person", "name": "박근노", "role": "나인테크 최대주주/대표"},
        ],
        "relations": [
            {"source": "이예하", "target": "뷰노", "type": "call_option", "detail": "콜옵션 행사"},
            {"source": "위지트", "target": "티사이언티픽", "type": "call_option", "detail": "콜옵션 행사"},
            {"source": "김호선", "target": "감성코퍼레이션", "type": "call_option", "detail": "콜옵션 행사"},
        ],
        "risks": [
            {"type": "governance", "description": "콜옵션 행사 후 주가 급락시 저가 매수로 지분율 부당 인상", "severity": "high"},
            {"type": "governance", "description": "정당한 행사대가 없이 콜옵션 제공", "severity": "high"},
            {"type": "market", "description": "최대주주 저가 전환으로 주가 급락, 일반 주주 손해", "severity": "medium"},
            {"type": "governance", "description": "경영권 분쟁시 콜옵션 악용해 지배력 강화", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/471",
        "title": "코스닥 상장사 전환사채 콜옵션, 어떻게 쓰였나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-11-13",
        "summary": "코스닥 상장사 전환사채 콜옵션이 최대주주/특수관계인에게 부여되어 시세차익 수단으로 활용. 2021년 규제 개정 이후에도 지분율 제한 내 활용.",
        "entities": [
            {"type": "company", "name": "대한광통신", "role": "CB 발행사"},
            {"type": "company", "name": "와이오엠", "role": "CB 발행사"},
            {"type": "company", "name": "나인테크", "role": "CB 발행사"},
            {"type": "company", "name": "티사이언티픽", "role": "CB 발행사"},
            {"type": "company", "name": "바이브컴퍼니", "role": "CB 발행사"},
            {"type": "company", "name": "디케이티", "role": "CB 발행사"},
            {"type": "company", "name": "감성코퍼레이션", "role": "CB 발행사"},
            {"type": "company", "name": "뷰노", "role": "AI 의료 CB 발행"},
            {"type": "person", "name": "황성일", "role": "나인테크 콜옵션 행사자"},
            {"type": "person", "name": "이예하", "role": "뷰노 최대주주"},
        ],
        "relations": [
            {"source": "나인테크", "target": "황성일", "type": "call_option", "detail": "콜옵션 행사자 지정"},
            {"source": "뷰노", "target": "이예하", "type": "call_option", "detail": "콜옵션 행사"},
        ],
        "risks": [
            {"type": "governance", "description": "디케이티 최대주주 등 3인 지분율 54.63% 지분 집중", "severity": "high"},
            {"type": "governance", "description": "콜옵션 통해 최대주주가 시세차익/지분율 제고", "severity": "high"},
            {"type": "financial", "description": "뷰노 3년간 4533억원 적자 결손기업이 CB 발행", "severity": "high"},
            {"type": "governance", "description": "김호선-김병진 다수 회사 대표 역임, 복잡한 지분이동", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/470",
        "title": "10배 늘어난 대양금속 차입금, 영풍제지 인수가 결정적",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-11-09",
        "summary": "대양금속 차입금 80억→821억원 급증. 영풍제지 인수가 주요 원인. 최대주주 담보권 실행과 시세조정 의혹으로 경영난 심화.",
        "entities": [
            {"type": "company", "name": "대양금속", "role": "영풍제지 인수 기업"},
            {"type": "company", "name": "영풍제지", "role": "인수 대상"},
            {"type": "company", "name": "대양홀딩스컴퍼니", "role": "대양금속 최대주주"},
            {"type": "company", "name": "에프앤디컨소시엄", "role": "경영권 인수 중개"},
            {"type": "person", "name": "공현철", "role": "대양홀딩스 최대주주"},
        ],
        "relations": [
            {"source": "공현철", "target": "대양홀딩스컴퍼니", "type": "ownership", "detail": "소유"},
            {"source": "대양홀딩스컴퍼니", "target": "대양금속", "type": "ownership", "detail": "최대주주"},
            {"source": "대양금속", "target": "영풍제지", "type": "acquisition", "detail": "인수"},
        ],
        "risks": [
            {"type": "financial", "description": "차입금 10배 증가, 대부분 1개월 이내 단기차입", "severity": "high"},
            {"type": "operational", "description": "상반기 매출 23% 감소, 영업이익 98% 하락", "severity": "high"},
            {"type": "legal", "description": "검찰 수사로 최대주주 시세조정 혐의", "severity": "critical"},
            {"type": "financial", "description": "담보권 실행으로 주식 처분 진행, 추가 유동화 필요", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/469",
        "title": "코스닥 마당발 리미트리스홀딩스, 공현철과 어떤 관계?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-11-06",
        "summary": "리미트리스홀딩스가 협진(구 에이씨티) 인수 관여. 공현철과의 관계 추적. 페이퍼컴퍼니 통한 복잡한 지분 구조와 경영권 변동.",
        "entities": [
            {"type": "company", "name": "협진", "role": "코스닥 상장 (구 에이씨티)"},
            {"type": "company", "name": "리미트리스홀딩스", "role": "에이씨티 인수 주체"},
            {"type": "company", "name": "제이에스엔홀딩스", "role": "인수 페이퍼컴퍼니"},
            {"type": "company", "name": "씨아이테크", "role": "현 협진 최대주주"},
            {"type": "company", "name": "대양금속", "role": "공현철 관련"},
            {"type": "company", "name": "영풍제지", "role": "공현철 관련"},
            {"type": "person", "name": "공현철", "role": "기업사냥꾼"},
            {"type": "person", "name": "김태훈", "role": "리미트리스홀딩스 설립자"},
            {"type": "person", "name": "조경숙", "role": "오성첨단소재 실질주인"},
        ],
        "relations": [
            {"source": "공현철", "target": "제이에스앤파트너스", "type": "ownership", "detail": "회사 소유"},
            {"source": "리미트리스홀딩스", "target": "공현철", "type": "related", "detail": "특수관계"},
            {"source": "씨아이테크", "target": "협진", "type": "ownership", "detail": "최대주주"},
        ],
        "risks": [
            {"type": "regulatory", "description": "GeneSort 투자 거래 상대방/자금흐름 확보 불가로 의견거절", "severity": "high"},
            {"type": "governance", "description": "자본금 최소화 신설회사 통한 복합 지분구조", "severity": "high"},
            {"type": "regulatory", "description": "에이씨티 2018-2019 연속 의견거절로 상장폐지 위기", "severity": "high"},
            {"type": "legal", "description": "전 대표 횡령, 매출채권 손상차손 등 3가지 상폐사유", "severity": "high"},
            {"type": "governance", "description": "리미트리스 투자기업 중 성지건설, 지코, 인터불스 등 다수 상폐", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/468",
        "title": "공현철은 어떻게 코스닥시장 큰손이 되었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-11-02",
        "summary": "공현철이 2009년 고제 이사로 시작해 인네트, 에스에프씨 등 코스닥 상장사 투자로 성장. 분식회계, 횡령 의혹 수반.",
        "entities": [
            {"type": "company", "name": "고제", "role": "인삼제품 제조 (유가증권)"},
            {"type": "company", "name": "인네트", "role": "코스닥 상장"},
            {"type": "company", "name": "에스에프씨", "role": "합성수지 필름 (코스닥)"},
            {"type": "company", "name": "태가", "role": "에스에프씨 인수 법인"},
            {"type": "company", "name": "지엔씨파트너스", "role": "재무적 투자자"},
            {"type": "person", "name": "공현철", "role": "투자자/임원"},
            {"type": "person", "name": "이옥순", "role": "공현철 모친, 대양금속 실질 최대주주"},
            {"type": "person", "name": "이상필", "role": "인네트/핸디소프트 실질 사주"},
        ],
        "relations": [
            {"source": "공현철", "target": "고제", "type": "management", "detail": "미등기 이사"},
            {"source": "공현철", "target": "인네트", "type": "ownership", "detail": "5% 이상 대주주"},
            {"source": "공현철", "target": "에스에프씨", "type": "management", "detail": "인수 주도/이사"},
            {"source": "이옥순", "target": "공현철", "type": "family", "detail": "모자관계"},
        ],
        "risks": [
            {"type": "regulatory", "description": "에스에프씨 2019년 감사의견 거절, 수년간 분식회계 적발", "severity": "high"},
            {"type": "legal", "description": "이상필 인네트 200억원, 핸디소프트 290억원 횡령 혐의", "severity": "high"},
            {"type": "financial", "description": "인네트 2010년 9월 부도 처리", "severity": "high"},
            {"type": "financial", "description": "저축은행 차입금으로 기업 인수", "severity": "medium"},
            {"type": "governance", "description": "에스에프씨가 공현철 오디컴퍼니 70억원 인수, 95억원 제공", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/467",
        "title": "최대주주 대양금속의 자금줄이 된 영풍제지",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-10-30",
        "summary": "대양금속 인수 후 영풍제지 현금성자산 91억원으로 급감. 약 400억원이 유무형자산 매입, CB 매입, 금전대여로 최대주주에 이전.",
        "entities": [
            {"type": "company", "name": "영풍제지", "role": "피인수기업"},
            {"type": "company", "name": "대양금속", "role": "최대주주 (50.76%)"},
            {"type": "company", "name": "대양홀딩스컴퍼니", "role": "이옥선 개인회사"},
            {"type": "company", "name": "아이텍", "role": "시스템반도체 테스트 (코스닥)"},
            {"type": "company", "name": "제주벤처캐피탈", "role": "아이텍 CB 인수"},
            {"type": "person", "name": "이옥선", "role": "대양금속 최대주주"},
            {"type": "person", "name": "최현식", "role": "아이텍 회장"},
        ],
        "relations": [
            {"source": "대양금속", "target": "영풍제지", "type": "ownership", "detail": "지분율 50.76%"},
            {"source": "이옥선", "target": "대양금속", "type": "ownership", "detail": "최대주주"},
            {"source": "영풍제지", "target": "대양금속", "type": "fund_transfer", "detail": "약 400억원 자산/대여금/CB 투자"},
            {"source": "영풍제지", "target": "아이텍", "type": "investment", "detail": "CB 50억원 보유"},
        ],
        "risks": [
            {"type": "financial", "description": "현금성자산 549억→91억원 급감, 2000년 이후 최저", "severity": "high"},
            {"type": "governance", "description": "유무형자산 거래 별도 공시 없음", "severity": "high"},
            {"type": "financial", "description": "국민/신한은행 총 100억원 신규 차입", "severity": "medium"},
            {"type": "governance", "description": "금융자산 내역 미공개, 투명성 부족", "severity": "medium"},
            {"type": "financial", "description": "역대 최대 배당금 106억원, 영업현금흐름 악화와 모순", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/466",
        "title": "대양금속과 영풍제지, 인수세력의 시세차익",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-10-26",
        "summary": "대양금속 영풍제지 인수시부터 주가조작 계획. 실소유자와 사채업자, 명동 투자자 관여. 인수 후 단기간 주식 매각과 CB로 막대한 시세차익.",
        "entities": [
            {"type": "company", "name": "대양금속", "role": "인수자"},
            {"type": "company", "name": "영풍제지", "role": "피인수 대상"},
            {"type": "company", "name": "대양홀딩스컴퍼니", "role": "최대주주사"},
            {"type": "company", "name": "에프앤디조합", "role": "재무적 투자자"},
            {"type": "person", "name": "이옥순", "role": "대양홀딩스 96% 지분, 대양금속 사내이사"},
            {"type": "person", "name": "조성종", "role": "대양홀딩스 설립자, 양사 대표"},
            {"type": "person", "name": "노미정", "role": "영풍제지 창업주 배우자"},
        ],
        "relations": [
            {"source": "대양홀딩스컴퍼니", "target": "대양금속", "type": "ownership", "detail": "최대주주"},
            {"source": "대양금속", "target": "영풍제지", "type": "acquisition", "detail": "인수"},
            {"source": "이옥순", "target": "대양홀딩스컴퍼니", "type": "ownership", "detail": "96% 지분"},
        ],
        "risks": [
            {"type": "market", "description": "주가조작 사실이고 이옥순씨 실소유주면 주가조작 핵심", "severity": "high"},
            {"type": "governance", "description": "1300억 인수에 439억 자기자금+861억 차입금, 무자본 M&A", "severity": "high"},
            {"type": "financial", "description": "인수 1개월 내 50% 이상 회수, 일부 조합 1주일 내 72억 회수", "severity": "high"},
            {"type": "operational", "description": "이옥순 가족 기업 다수 상폐/회생절차 진입", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/465",
        "title": "넥스턴바이오사이언스 전환사채, 발행에서 재매각까지",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-10-23",
        "summary": "넥스턴바이오사이언스가 2021년 발행 CB 379억원을 최대주주 스튜디오산타클로스에 재매각. 이브이첨단소재 인수 관련 복잡한 자금이동.",
        "entities": [
            {"type": "company", "name": "넥스턴바이오사이언스", "role": "CB 발행/재매각"},
            {"type": "company", "name": "스튜디오산타클로스", "role": "최대주주, CB 매입"},
            {"type": "company", "name": "이브이첨단소재", "role": "인수 대상"},
            {"type": "company", "name": "에스엘에너지", "role": "이브이첨단 전 최대주주"},
            {"type": "company", "name": "메리디안홀딩스", "role": "이브이첨단 중간 경영권"},
            {"type": "company", "name": "헤븐", "role": "법적 분쟁 제기"},
            {"type": "company", "name": "리치몬드홀딩스", "role": "스튜디오산타 신규 최대주주 예정"},
            {"type": "person", "name": "배준오", "role": "스튜디오산타 대표, 리치몬드 설립자"},
        ],
        "relations": [
            {"source": "넥스턴바이오사이언스", "target": "스튜디오산타클로스", "type": "cb_sale", "detail": "CB 재매각"},
            {"source": "에스엘에너지", "target": "메리디안홀딩스", "type": "sale", "detail": "이브이첨단 최대주주권 이전"},
            {"source": "스튜디오산타클로스", "target": "리치몬드홀딩스", "type": "ownership", "detail": "최대주주 변경 예정"},
        ],
        "risks": [
            {"type": "market", "description": "헤븐/맘스아일랜드가 주가조작 및 배임횡령 목적 거래 주장", "severity": "high"},
            {"type": "legal", "description": "CB 매각/발행이 불법 목적으로 가처분 신청", "severity": "high"},
            {"type": "financial", "description": "유동성 확보 위한 지속적 자산 매각으로 지분 감소", "severity": "medium"},
            {"type": "market", "description": "이브이첨단 주가 4개월간 반토막에도 지분 보유", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/464",
        "title": "다이나믹 전환사채, 발행 후 행방은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-10-21",
        "summary": "이브이첨단소재가 다이나믹디자인 인수 후 대규모 CB 발행. 여러 투자자 상당한 차익. 니켈 프로젝트 관련 자금 흐름 추적.",
        "entities": [
            {"type": "company", "name": "우성코퍼레이션", "role": "에너지사업 분할/지분 매각"},
            {"type": "company", "name": "다이나믹디자인", "role": "CB 발행 기업"},
            {"type": "company", "name": "이브이첨단소재", "role": "다이나믹디자인 인수"},
            {"type": "company", "name": "에스엘에너지", "role": "우성인더스트리 인수"},
            {"type": "company", "name": "스튜디오산타클로스", "role": "지분 매각/투자 참여"},
            {"type": "company", "name": "미래산업", "role": "CB 인수/니켈 프로젝트 참여"},
            {"type": "person", "name": "온성준", "role": "에스엘홀딩스 실질주주, 대여금 수령"},
            {"type": "person", "name": "손오동", "role": "우성코퍼레이션 오너"},
            {"type": "person", "name": "류영길", "role": "티엘홀딩스 소유자, CB 인수"},
        ],
        "relations": [
            {"source": "우성코퍼레이션", "target": "다이나믹디자인", "type": "sale", "detail": "310억원 경영권 매각"},
            {"source": "이브이첨단소재", "target": "다이나믹디자인", "type": "acquisition", "detail": "인수 후 CB 발행"},
            {"source": "우성코퍼레이션", "target": "온성준", "type": "loan", "detail": "157억원 대여"},
        ],
        "risks": [
            {"type": "governance", "description": "대여금 324억원 유출되었으나 실제 사용처 불명확", "severity": "high"},
            {"type": "market", "description": "전환가액 대비 주가 급등으로 대량 차익 발생, 수익자 추적 곤란", "severity": "high"},
            {"type": "governance", "description": "최대주주 관련회사들이 CB 인수/매매에 참여", "severity": "medium"},
            {"type": "financial", "description": "인도네시아 법인 4% 지분에 출자자본 10배 프리미엄 지불", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/463",
        "title": "에스엘에너지 매각보다 중요한 승부처",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-10-16",
        "summary": "에스엘에너지가 상폐 위기 탈출 위해 경영권 지분 매각 추진. 복잡한 이해관계와 자금 거래망. 온성준/손오동 등 니켈/리튬 사업이 실제 승부처.",
        "entities": [
            {"type": "company", "name": "에스엘에너지", "role": "상폐 위기 기업"},
            {"type": "company", "name": "우성코퍼레이션", "role": "에너지사업 매각"},
            {"type": "company", "name": "다이나믹디자인", "role": "니켈/리튬 사업"},
            {"type": "company", "name": "하이드로리튬", "role": "니켈/리튬 사업"},
            {"type": "company", "name": "미래산업", "role": "다이나믹디자인 CB 투자"},
            {"type": "company", "name": "리튬플러스", "role": "전웅 계열"},
            {"type": "person", "name": "온성준", "role": "에스엘홀딩스 실질 주인"},
            {"type": "person", "name": "손오동", "role": "우성코퍼레이션 前 소유"},
            {"type": "person", "name": "전웅", "role": "리튬플러스 오너"},
            {"type": "person", "name": "류영길", "role": "티엘홀딩스 대표"},
            {"type": "person", "name": "황양호", "role": "에스엘홀딩스 채권자"},
        ],
        "relations": [
            {"source": "온성준", "target": "에스엘에너지", "type": "ownership", "detail": "에스엘홀딩스 통한 간접 지배"},
            {"source": "손오동", "target": "우성코퍼레이션", "type": "sale", "detail": "에스엘에너지로 에너지사업 매각"},
            {"source": "온성준", "target": "다이나믹디자인", "type": "investment", "detail": "매각자금으로 니켈/리튬 투자"},
            {"source": "미래산업", "target": "다이나믹디자인", "type": "investment", "detail": "100억원 CB 매입"},
        ],
        "risks": [
            {"type": "financial", "description": "손오동 부부 대여금 회수가능성 불확실, 외부감사 의견거절", "severity": "high"},
            {"type": "governance", "description": "실제 경영권자 불분명, 손오동 측에 통제권", "severity": "high"},
            {"type": "governance", "description": "매각자금이 온성준→다이나믹 복잡한 순환거래", "severity": "high"},
            {"type": "governance", "description": "공개매각 인수자가 자본금 5000만원 신설회사", "severity": "high"},
            {"type": "regulatory", "description": "불성실공시 벌점, 5년 연속 영업적자, 상장적격성 불확실", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/462",
        "title": "온성준•손오동•류영길의 다이나믹한 인연",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-10-05",
        "summary": "우성코퍼레이션이 에너지사업 매각 후 매각대금을 온성준/에스엘홀딩스에 대여. 온성준, 손오동, 류영길의 복잡한 자금거래와 지배구조 변화.",
        "entities": [
            {"type": "company", "name": "우성코퍼레이션", "role": "에너지사업 매각/대여금 제공"},
            {"type": "company", "name": "에스엘에너지", "role": "에너지사업 인수"},
            {"type": "company", "name": "에스엘홀딩스컴퍼니", "role": "대여금 수령"},
            {"type": "company", "name": "티엘홀딩스", "role": "에스엘에너지 인수"},
            {"type": "company", "name": "세화아이엠씨", "role": "다이나믹디자인 (우성 인수대상)"},
            {"type": "company", "name": "리튬플러스", "role": "하이드로리튬 경영권 인수"},
            {"type": "person", "name": "온성준", "role": "에스엘에너지 실질 매도자"},
            {"type": "person", "name": "손오동", "role": "우성코퍼레이션 실질 오너"},
            {"type": "person", "name": "류영길", "role": "티엘홀딩스 대표, 세화아이엠씨 CFO"},
            {"type": "person", "name": "신채림", "role": "우성코퍼레이션 최대주주, 손오동 배우자"},
            {"type": "person", "name": "전웅", "role": "리튬플러스 최대주주/대표"},
        ],
        "relations": [
            {"source": "우성코퍼레이션", "target": "온성준", "type": "loan", "detail": "157억원 이상 수차례 대여"},
            {"source": "우성코퍼레이션", "target": "에스엘홀딩스컴퍼니", "type": "loan", "detail": "88억원 대여"},
            {"source": "손오동", "target": "우성코퍼레이션", "type": "acquisition", "detail": "세화아이엠씨 인수 후 대표 취임"},
            {"source": "류영길", "target": "세화아이엠씨", "type": "management", "detail": "부사장/CFO"},
            {"source": "우성코퍼레이션", "target": "이브이첨단소재", "type": "sale", "detail": "다이나믹디자인 지분 159억→310억 매각"},
        ],
        "risks": [
            {"type": "financial", "description": "매각대금 거의 전부를 온성준에 대여, 회수 의심으로 의견거절", "severity": "high"},
            {"type": "financial", "description": "자산 358억 중 219억이 단기대여금, 회수 불확실", "severity": "high"},
            {"type": "governance", "description": "온성준/손오동/류영길/전웅이 리튬 사업에 복잡한 네트워크", "severity": "high"},
            {"type": "regulatory", "description": "에스엘에너지 최대주주 주식담보대출 공시위반, 공탁금 54억 묶임", "severity": "high"},
            {"type": "governance", "description": "투자조합 실제 투자자 식별 어려움", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/461",
        "title": "리튬사업으로 묶인 온성준•손오동•류영길•전웅의 관계",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-10-02",
        "summary": "온성준이 에스엘홀딩스로 에스엘에너지 지분 인수. 손오동, 류영길, 전웅과 리튬사업 복잡한 자금거래/투자 네트워크.",
        "entities": [
            {"type": "company", "name": "에스엘홀딩스", "role": "지주회사"},
            {"type": "company", "name": "에스엘에너지", "role": "상장사"},
            {"type": "company", "name": "우성코퍼레이션", "role": "투자회사"},
            {"type": "company", "name": "이브이첨단소재", "role": "상장사"},
            {"type": "company", "name": "다이나믹디자인", "role": "상장사"},
            {"type": "company", "name": "하이드로리튬", "role": "리튬사업"},
            {"type": "company", "name": "리튬플러스", "role": "리튬사업"},
            {"type": "company", "name": "티엘홀딩스", "role": "지주회사"},
            {"type": "person", "name": "온성준", "role": "에스엘홀딩스 설립자"},
            {"type": "person", "name": "손오동", "role": "우성코퍼레이션 최대주주"},
            {"type": "person", "name": "류영길", "role": "티엘홀딩스 대표"},
            {"type": "person", "name": "전웅", "role": "리튬플러스 최대주주/대표"},
            {"type": "person", "name": "온영두", "role": "에스엘홀딩스 100% 지분"},
            {"type": "person", "name": "신채림", "role": "우성코퍼레이션 최대주주 (손오동 배우자)"},
        ],
        "relations": [
            {"source": "온성준", "target": "에스엘홀딩스", "type": "ownership", "detail": "설립자/실질소유"},
            {"source": "에스엘홀딩스", "target": "에스엘에너지", "type": "ownership", "detail": "최대주주"},
            {"source": "손오동", "target": "우성코퍼레이션", "type": "ownership", "detail": "최대주주"},
            {"source": "우성코퍼레이션", "target": "다이나믹디자인", "type": "investment", "detail": "투자"},
            {"source": "리튬플러스", "target": "하이드로리튬", "type": "acquisition", "detail": "경영권 인수"},
            {"source": "우성코퍼레이션", "target": "에스엘홀딩스", "type": "loan", "detail": "대여"},
        ],
        "risks": [
            {"type": "financial", "description": "에스엘홀딩스 자본금 9200만원으로 140억 부채, 84억 투입", "severity": "high"},
            {"type": "governance", "description": "에스엘홀딩스→우성 157억 대여, 다시 47억 역대여 순환", "severity": "high"},
            {"type": "governance", "description": "에스엘홀딩스 상장사 아니고 외부감사 미실시, 투명성 부족", "severity": "medium"},
            {"type": "governance", "description": "4인이 다양한 회사 통해 리튬사업 복잡한 네트워크", "severity": "high"},
            {"type": "market", "description": "유엠기술개발투자조합1호 구주 인수 후 3~5배 가격 처분", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/460",
        "title": "루멘스와 에스엘에너지, 뒤바뀐 임대인과 임차인",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-09-25",
        "summary": "루멘스가 에스엘에너지에 본사/공장 부동산 417억원 매각, 임대인과 임차인 입장 역전. 온성준 형제 지분 매각 과정에서 복잡한 이해관계.",
        "entities": [
            {"type": "company", "name": "루멘스", "role": "LED 제조, 부동산 매각"},
            {"type": "company", "name": "에스엘에너지", "role": "LED칩 전문, 부동산 매수"},
            {"type": "company", "name": "세미콘라이트", "role": "경영권 변경 대상"},
            {"type": "company", "name": "지케이티팜", "role": "세미콘라이트 경영권 인수"},
            {"type": "company", "name": "갤럭시인베스트먼트", "role": "세미콘라이트 지분 확보"},
            {"type": "company", "name": "퓨전", "role": "세미콘라이트 인수"},
            {"type": "person", "name": "유태경", "role": "루멘스 대표, 세미콘 전 최대주주"},
            {"type": "person", "name": "온성준", "role": "에스엘에너지 실질 최대주주"},
            {"type": "person", "name": "김영진", "role": "플린스 설립자, 세미콘 대표"},
        ],
        "relations": [
            {"source": "유태경", "target": "루멘스", "type": "management", "detail": "경영권 보유"},
            {"source": "루멘스", "target": "에스엘에너지", "type": "sale", "detail": "2021년 417억 부동산 매각"},
            {"source": "온성준", "target": "에스엘에너지", "type": "ownership", "detail": "실질 최대주주"},
            {"source": "퓨전", "target": "세미콘라이트", "type": "acquisition", "detail": "2019년 6월 197억 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "루멘스 자산 3000억→1443억, 매출 4000억→1663억 축소", "severity": "high"},
            {"type": "financial", "description": "루멘스 2019년부터 4년 연속 영업적자, LED 경쟁력 훼손", "severity": "high"},
            {"type": "financial", "description": "에스엘에너지 4년 연속 영업손실, 6년 연속 순손실", "severity": "high"},
            {"type": "governance", "description": "지케이티팜 자기자금 인수 거짓 보도, 지분 인출 사고", "severity": "high"},
            {"type": "governance", "description": "에스엘에너지 LED공장 매입 4개월 후 LED사업 영업중단", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/459",
        "title": "주인 바뀌는 스튜디오산타클로스의 숙제",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-09-21",
        "summary": "에스엘에너지 공개매각과 스튜디오산타클로스 유상증자로 두 회사 최대주주 변경 예정. 온씨 형제 지분 정리 과정에서 경영 이슈.",
        "entities": [
            {"type": "company", "name": "스튜디오산타클로스", "role": "상장사"},
            {"type": "company", "name": "에스엘에너지", "role": "상장사"},
            {"type": "company", "name": "리치몬드홀딩스", "role": "홀딩스"},
            {"type": "company", "name": "루시드홀딩스", "role": "홀딩스"},
            {"type": "company", "name": "이브이첨단소재", "role": "계열사"},
            {"type": "company", "name": "넥스턴바이오사이언스", "role": "계열사"},
            {"type": "company", "name": "유에이치산업개발", "role": "부동산개발"},
            {"type": "person", "name": "온성준", "role": "전 지배인"},
            {"type": "person", "name": "온영두", "role": "전 지배인"},
            {"type": "person", "name": "배준오", "role": "스튜디오산타 대표"},
            {"type": "person", "name": "류영길", "role": "티엘홀딩스 대표"},
        ],
        "relations": [
            {"source": "온성준", "target": "스튜디오산타클로스", "type": "ownership", "detail": "실질지배"},
            {"source": "배준오", "target": "리치몬드홀딩스", "type": "ownership", "detail": "소유"},
            {"source": "에스엘에너지", "target": "스튜디오산타클로스", "type": "ownership", "detail": "11.35%→10.19%"},
            {"source": "루시드홀딩스", "target": "에스엘에너지", "type": "ownership", "detail": "10.52%"},
        ],
        "risks": [
            {"type": "governance", "description": "리치몬드와 에스엘에너지 지분율 격차 미미(10.21% vs 10.19%), 경영권 경쟁 가능", "severity": "high"},
            {"type": "financial", "description": "리치몬드홀딩스 자본금 5000만원으로 56억 유상증자 인수시 차입금 의존", "severity": "high"},
            {"type": "regulatory", "description": "투자주의 환기종목 지정, 내부회계 비적정으로 상폐 위험", "severity": "high"},
            {"type": "financial", "description": "유에이치상천 42.7억원 손상처리 회수 불확실", "severity": "medium"},
            {"type": "governance", "description": "자금운용/특수관계자 거래 적정성 통제활동 미흡", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/458",
        "title": "에스엘에너지 빚청산 여파, 어디까지?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2023-09-18",
        "summary": "에스엘에너지 공개매각 추진, 티엘홀딩스 우선협상대상자 선정. 5년 연속 영업적자로 상폐 위기, 최대주주 변경과 빚청산 필수.",
        "entities": [
            {"type": "company", "name": "에스엘에너지", "role": "상장사 (코스닥)"},
            {"type": "company", "name": "티엘홀딩스", "role": "인수자"},
            {"type": "company", "name": "에스엘홀딩스", "role": "기존 최대주주"},
            {"type": "company", "name": "스튜디오산타클로스", "role": "피인수사"},
            {"type": "company", "name": "우성인더스트리", "role": "인수대상"},
            {"type": "company", "name": "상상인저축은행", "role": "차입금 제공"},
            {"type": "person", "name": "류영길", "role": "티엘홀딩스 최대주주/대표"},
            {"type": "person", "name": "온성준", "role": "에스엘에너지 최대주주"},
            {"type": "person", "name": "배준오", "role": "스튜디오산타 대표"},
        ],
        "relations": [
            {"source": "티엘홀딩스", "target": "에스엘에너지", "type": "acquisition", "detail": "구주 15.42% 인수/유상증자 참여"},
            {"source": "에스엘에너지", "target": "우성인더스트리", "type": "acquisition", "detail": "280억 차입금+70억 CB로 인수"},
            {"source": "에스엘에너지", "target": "스튜디오산타클로스", "type": "ownership", "detail": "주식 장내매도 현금화"},
        ],
        "risks": [
            {"type": "regulatory", "description": "5년 연속 영업적자로 상폐 요건 충족, 코스닥위 심의 중", "severity": "high"},
            {"type": "financial", "description": "상상인저축은행 차입금 33억원에 연 13% 이자 부담", "severity": "medium"},
            {"type": "financial", "description": "스튜디오산타 전량 주식 담보, 담보권 실행시 지분 상실", "severity": "high"},
            {"type": "regulatory", "description": "최대주주 주식담보대출 등 공시 위반 벌점 누적", "severity": "medium"},
            {"type": "financial", "description": "우성인더스트리 인수 관련 250억 대주단 차입금, 연 9~10%", "severity": "high"},
            {"type": "governance", "description": "류영길 과거 우회상장 시도 이력으로 거래 투명성 의문", "severity": "medium"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (18차) ===\n")

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
