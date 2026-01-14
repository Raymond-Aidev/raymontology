#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 15차 (누락 기사: SK쉴더스/삼성바이오에피스/더이앤엠/홈플러스/한온시스템)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/639",
        "title": "인수금융 리파이낸싱은 SK쉴더스 몸값 하락",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-10-27",
        "summary": "EQT파트너스가 SK쉴더스 3.3조원 리파이낸싱 완료. 지주사 KSH 인수부채 2.4조원을 운영회사로 이전, 금리는 7%→5.1%로 하락했으나 재무지표 악화.",
        "entities": [
            {"type": "company", "name": "SK쉴더스", "role": "보안회사/운영법인"},
            {"type": "company", "name": "EQT파트너스", "role": "스웨덴 PE/지배주주"},
            {"type": "company", "name": "코리아시큐리티홀딩스", "role": "지주회사/SPC"},
            {"type": "company", "name": "SK그룹", "role": "전 소유주"},
            {"type": "company", "name": "맥쿼리PE", "role": "ADT캡스 공동투자자"},
        ],
        "relations": [
            {"source": "EQT파트너스", "target": "SK쉴더스", "type": "control", "detail": "지배주주"},
        ],
        "risks": [
            {"type": "financial", "description": "부채비율 873%로 급등, SK쉴더스가 2.4조원 부채 부담", "severity": "high"},
            {"type": "governance", "description": "담보권 채권자 이전, 사업 시너지 없는 최대주주 변경", "severity": "high"},
            {"type": "operational", "description": "신용등급 하락 위험으로 신규 계약/고객 조건 제약", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/624",
        "title": "급성장한 실적, 기업가치는 그대로?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-07-14",
        "summary": "삼성바이오에피스 2018-2022년 매출 3.7조→9.5조, 영업손실→2.3조 흑자 전환. 바이오젠 50.01% 지분 약 2.75조원에 인수, 2018년 가치와 거의 동일.",
        "entities": [
            {"type": "company", "name": "삼성바이오에피스", "role": "자회사/합작사"},
            {"type": "company", "name": "삼성바이오로직스", "role": "모회사/인수자"},
            {"type": "company", "name": "바이오젠", "role": "합작파트너/매도자"},
        ],
        "relations": [
            {"source": "삼성바이오로직스", "target": "삼성바이오에피스", "type": "acquisition", "detail": "바이오젠 지분 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "156% 매출성장에도 자산가치 동일 유지 - 밸류에이션 괴리", "severity": "high"},
            {"type": "governance", "description": "인수 가격/조건 관련 특수관계 거래 우려", "severity": "high"},
            {"type": "market", "description": "바이오젠의 지분 처분은 장기 가치창출 불신 시사", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/623",
        "title": "2.7조원이 5170억원으로…그럴 듯한 이유는 늘 있다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-07-07",
        "summary": "삼성바이오로직스가 2020년 삼성바이오에피스 장부가치를 2.65조→5170억원으로 감소. 개별→별도재무제표, 지분법→원가법 변경으로 회계적 감액.",
        "entities": [
            {"type": "company", "name": "삼성바이오로직스", "role": "모회사"},
            {"type": "company", "name": "삼성바이오에피스", "role": "자회사/합작사"},
            {"type": "company", "name": "바이오젠", "role": "콜옵션 보유"},
        ],
        "relations": [
            {"source": "삼성바이오로직스", "target": "삼성바이오에피스", "type": "ownership", "detail": "50%+1주 보유"},
        ],
        "risks": [
            {"type": "governance", "description": "영업상 변화 없이 회계정책 변경(지분법→원가법) - 투명성 저하", "severity": "high"},
            {"type": "financial", "description": "회계 재분류로 2.13조원 자산손상 - 경제적 하락 아닌 회계처리", "severity": "critical"},
            {"type": "regulatory", "description": "회계처리 기준 준수 여부 우려", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/622",
        "title": "삼성바이오에피스 기업가치, 2015년 그때",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-06-30",
        "summary": "2012년 설립 삼성바이오에피스가 2015년 매출 2390억원, 순손실 1666억원에도 기업가치 5.27조원 평가. 낙관적 미래현금흐름 가정, 이재용 승계와 연결된 분식회계 의혹.",
        "entities": [
            {"type": "company", "name": "삼성바이오에피스", "role": "합작사"},
            {"type": "company", "name": "삼성바이오로직스", "role": "모회사 (91.2% 보유)"},
            {"type": "company", "name": "바이오젠", "role": "공동창업자/콜옵션 보유"},
            {"type": "company", "name": "삼성물산", "role": "합병 관련"},
            {"type": "company", "name": "삼성전자", "role": "모그룹"},
            {"type": "person", "name": "이재용", "role": "부회장/승계 수혜자"},
        ],
        "relations": [
            {"source": "삼성바이오로직스", "target": "삼성바이오에피스", "type": "ownership", "detail": "91.2% 지분 보유 (2015)"},
        ],
        "risks": [
            {"type": "governance", "description": "자회사→관계사 재분류 투명한 공시 부족", "severity": "high"},
            {"type": "financial", "description": "105.3% 매출성장, 57.4% 영업이익률 가정 - 실제 2020년까지 마이너스 현금흐름", "severity": "high"},
            {"type": "legal", "description": "2024년 행정법원 '고의적 사기'로 분류하기 어렵다 판결에도 합병 관련 의도 인정", "severity": "critical"},
            {"type": "regulatory", "description": "금융당국/검찰이 '과도하게 낙관적' 밸류에이션 문제제기", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/621",
        "title": "삼성바이오에피스 기업가치 26조원?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-06-23",
        "summary": "삼성바이오로직스 바이오시밀러 사업 분할 분석. 34.96% 지분 교환 시가 기준 삼성바이오에피스 약 25.4조원 암묵적 가치평가.",
        "entities": [
            {"type": "company", "name": "삼성바이오로직스", "role": "분할 주체"},
            {"type": "company", "name": "삼성바이오에피스", "role": "분할 대상 바이오시밀러"},
            {"type": "company", "name": "삼성물산", "role": "분할 지분 수령"},
            {"type": "company", "name": "삼성전자", "role": "분할 지분 수령"},
            {"type": "company", "name": "삼성에피스홀딩스", "role": "신설 지주회사"},
        ],
        "relations": [
            {"source": "삼성바이오로직스", "target": "삼성바이오에피스", "type": "spin-off", "detail": "바이오시밀러 사업 분할"},
        ],
        "risks": [
            {"type": "governance", "description": "장부가 3.36조 vs 시가 25.5조 암묵적 가치평가 괴리 - 공정성/주주정렬 의문", "severity": "high"},
            {"type": "financial", "description": "EV/EBITDA 52배, P/E 67배 극단적 멀티플 - 고평가 가능성", "severity": "high"},
            {"type": "regulatory", "description": "분할/세금이연 요건 충족 위한 자산/부채 배분, 현금 제한", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/620",
        "title": "바이오에피스 저평가가 인적분할의 이유?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-06-16",
        "summary": "삼성바이오로직스가 CDMO와 바이오에피스(바이오시밀러) 분리 인적분할 발표. 고객 이해충돌 해소, 공정 시장가치 평가, 투자 유연성이 명분이나 저평가 주장과 모순.",
        "entities": [
            {"type": "company", "name": "삼성바이오로직스", "role": "기존 회사 (분할 후 CDMO)"},
            {"type": "company", "name": "삼성바이오에피스", "role": "바이오시밀러 (삼성에피스홀딩스 자회사)"},
            {"type": "company", "name": "삼성에피스홀딩스", "role": "신설 지주회사"},
            {"type": "company", "name": "셀트리온", "role": "밸류에이션 비교대상"},
            {"type": "company", "name": "바이오젠", "role": "밸류에이션 비교대상"},
        ],
        "relations": [],
        "risks": [
            {"type": "market", "description": "바이오에피스 저평가 주장이 EV/EBITDA 지표와 불일치 - 프리미엄 밸류에이션", "severity": "high"},
            {"type": "governance", "description": "명시된 운영 근거 외 그룹 구조조정 동기 의문", "severity": "high"},
            {"type": "operational", "description": "분리로 통합 운영 분절, 성공은 상장 후 시장 재평가에 의존", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/619",
        "title": "더이앤엠 인수파트너 나비스피델리스의 활약상",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-06-09",
        "summary": "2016년 설립 경영컨설팅 나비스피델리스가 더이앤엠 인수 파트너로 활동. 다수 코스닥 상장사에 걸친 투자활동 네트워크와 특수관계 거래 추적.",
        "entities": [
            {"type": "company", "name": "나비스피델리스", "role": "경영컨설팅/인수파트너"},
            {"type": "company", "name": "더이앤엠", "role": "인수대상"},
            {"type": "company", "name": "마제스타", "role": "카지노 사업"},
            {"type": "company", "name": "감마누", "role": "코스닥 상장사"},
            {"type": "company", "name": "에이루트", "role": "전 제이스테판"},
            {"type": "company", "name": "에스엠브이홀딩스", "role": "관련회사"},
            {"type": "company", "name": "휴림로봇", "role": "관련회사"},
            {"type": "company", "name": "에이프로젠", "role": "제약"},
            {"type": "company", "name": "지베이스", "role": "에이프로젠 회장 회사"},
            {"type": "person", "name": "신환율", "role": "더이앤엠 최대주주"},
            {"type": "person", "name": "이승환", "role": "나비스피델리스 창업 대표"},
            {"type": "person", "name": "서수경", "role": "나비스피델리스 현 대표"},
            {"type": "person", "name": "김재섭", "role": "에이프로젠 회장"},
            {"type": "person", "name": "배상윤", "role": "KH그룹 회장"},
        ],
        "relations": [
            {"source": "나비스피델리스", "target": "더이앤엠", "type": "acquisition", "detail": "인수 파트너"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 다층 소유구조로 실소유권 불명확", "severity": "high"},
            {"type": "financial", "description": "6,000원 고평가 인수 후 전략적 저가 유상증자 - 가치이전 구조 의심", "severity": "high"},
            {"type": "regulatory", "description": "반복적 특수관계 거래와 연계 투자조합 - 공시/공정거래 규정 위반 가능성", "severity": "high"},
            {"type": "legal", "description": "회생절차/상장폐지 기업들의 지속적 소유권 이전, 미해결 소송", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/618",
        "title": "벼랑 끝에서 살아난 인터로조",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-06-02",
        "summary": "콘택트렌즈 제조사 인터로조가 2023년 감사의견거절 후 상장폐지 위기에서 회복. 2024년 적정의견으로 실질심사 제외, 즉시 거래재개.",
        "entities": [
            {"type": "company", "name": "인터로조", "role": "콘택트렌즈 제조"},
            {"type": "company", "name": "신한투자증권", "role": "금융지원/CB 인수"},
            {"type": "company", "name": "삼일회계법인", "role": "2023년 외부감사"},
            {"type": "company", "name": "법무법인세종", "role": "지배구조 자문"},
            {"type": "person", "name": "노시철", "role": "회장/최대주주"},
        ],
        "relations": [
            {"source": "신한투자증권", "target": "인터로조", "type": "investment", "detail": "100억원 CB 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "재고관리/매출인식 내부통제 미흡, 계약문서 절차 부재", "severity": "critical"},
            {"type": "financial", "description": "전기 재무제표 재작성으로 이익 70% 감소, 고부채 담보주식 소유권 상실 위험", "severity": "high"},
            {"type": "operational", "description": "감사인 교체 후에야 회계시스템 결함 발견, OEM/ODM 수출 단일 카테고리 의존", "severity": "high"},
            {"type": "regulatory", "description": "감사의견거절로 상장적격성 위협, 조건부 시장 복귀 상태", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/617",
        "title": "더이앤엠 인수 배후였던 중국 자본의 행보",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-05-26",
        "summary": "더이앤엠(전 용현비엠) 인수 배후 중국 자본 추적. 미동전자(2016년 인수자금 지원) 상장폐지 후 복잡한 지분거래로 지배권 이전.",
        "entities": [
            {"type": "company", "name": "더이앤엠", "role": "대상회사/블랙박스/관광"},
            {"type": "company", "name": "미동전자", "role": "상장폐지/전 자금지원"},
            {"type": "company", "name": "룽투코리아", "role": "2016년 용현비엠 인수"},
            {"type": "company", "name": "상해유평인베스트먼트", "role": "중국 투자사/전 최대주주"},
            {"type": "company", "name": "맥스스텝크리에이션", "role": "현 주요주주"},
            {"type": "company", "name": "넥스트아이", "role": "코스닥/CB 발행"},
            {"type": "person", "name": "천톈톈", "role": "대표/다수 법인 연결"},
        ],
        "relations": [
            {"source": "룽투코리아", "target": "더이앤엠", "type": "acquisition", "detail": "2016년 용현비엠 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 지분구조로 실소유권/지배권 불명확, 특수관계 거래 의심", "severity": "critical"},
            {"type": "financial", "description": "자산 80% 중국 자회사에 검증 불가 공정가치, 95억원 불확실 지분으로 회수", "severity": "high"},
            {"type": "regulatory", "description": "감사의견거절, 중요 특수관계 거래 공시 위반 가능성", "severity": "critical"},
            {"type": "operational", "description": "핵심사업 매출 2021년 이후 붕괴, 2022년 이후 수출 중단", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/616",
        "title": "팝콘TV 운영사, 어떻게 상장사가 되었나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-05-19",
        "summary": "더이앤엠이 금속소재 회사에서 스트리밍 플랫폼으로 전환한 과정. 2006년 용현비엠으로 상장 후 룽투코리아가 2015년 인수, 홍연(개인방송플랫폼) 합병으로 우회상장.",
        "entities": [
            {"type": "company", "name": "더이앤엠", "role": "스트리밍 플랫폼 운영"},
            {"type": "company", "name": "현진소재", "role": "전 모회사"},
            {"type": "company", "name": "룽투코리아", "role": "중국 모바일게임/인수자"},
            {"type": "company", "name": "홍연", "role": "개인방송 플랫폼/합병"},
            {"type": "company", "name": "나비스피델리스", "role": "투자기구/경영권 취득"},
            {"type": "company", "name": "폴라리스세원", "role": "코스닥 관련사"},
            {"type": "company", "name": "아이에이", "role": "자동차부품/일시 투자자"},
            {"type": "person", "name": "김대권", "role": "홍연 창업자/더이앤엠 이사"},
            {"type": "person", "name": "이승환", "role": "나비스피델리스 대표/더이앤엠 공동대표"},
            {"type": "person", "name": "신환율", "role": "폴라리스세원 전 대표/더이앤엠 공동대표/현 최대주주"},
        ],
        "relations": [
            {"source": "룽투코리아", "target": "더이앤엠", "type": "acquisition", "detail": "2015년 지배권 인수"},
            {"source": "나비스피델리스", "target": "더이앤엠", "type": "control", "detail": "2019년 경영권 취득"},
        ],
        "risks": [
            {"type": "governance", "description": "잦은 경영진 교체와 순환 소유구조 - 취약한 지배구조. 4-5년 내 룽투→나비스→개인 지배권 이전", "severity": "high"},
            {"type": "financial", "description": "241억원 투자로 두 회사 인수 후 수 주 내 밸류에이션 3배 - 고평가 우려", "severity": "high"},
            {"type": "operational", "description": "핵심사업(금속소재) 완전 포기, 모회사가 더이앤엠에서 모든 기계 철수 - 자산박리", "severity": "medium"},
            {"type": "market", "description": "특수관계 거래와 복잡한 투자기구(다수 PEF 조합)로 실소유권 불명확", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/615",
        "title": "자기전환사채 잇따른 취득, 그 다음엔?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-05-12",
        "summary": "코스닥 더앤엠이 자기전환사채를 반복 취득 후 소각 대신 재매각 가능성. 영업손실과 마이너스 현금흐름에도 2025년만 75억원 조기상환 지출.",
        "entities": [
            {"type": "company", "name": "더앤엠", "role": "인터넷방송 (팝콘TV)"},
            {"type": "company", "name": "아이씨엔엔터테인먼트", "role": "더앤엠 자회사"},
            {"type": "company", "name": "씨엘앤엔컴퍼니", "role": "엔터 자회사"},
            {"type": "company", "name": "베셀", "role": "디스플레이장비/더앤엠 지배력 상실"},
            {"type": "person", "name": "오대강", "role": "에이지엘컴퍼니/베셀 신규 지배주주"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "CB 약 95억원 2025년 6월 만기, 3년 연속 영업손실과 마이너스 현금흐름으로 정상상환 불가능 전망", "severity": "critical"},
            {"type": "operational", "description": "연결/개별 모두 반복적 손실, 자산투자에도 현금 고갈", "severity": "high"},
            {"type": "governance", "description": "반복적 CB 만기연장과 잠재적 재매각 - 전략적 상환이 아닌 부채관리 불안정", "severity": "high"},
            {"type": "market", "description": "주가(800원)가 최저 전환가(1,000원) 하회 - 투자자 회복 전망 불신", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/614",
        "title": "홈플러스, 6.5조원을 갚았지만 빚은 그대로",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-05-06",
        "summary": "홈플러스가 9년간 6.57조원 상환에도 2024년 2월 순차입금 6.16조원으로 증가. 자산매각/영업현금이 거의 전액 부채상환과 이자에 소진.",
        "entities": [
            {"type": "company", "name": "홈플러스", "role": "소매회사/세일앤리스백 운영"},
            {"type": "company", "name": "MBK파트너스", "role": "PE 인수자/지배주주"},
            {"type": "company", "name": "홈플러스스토어스", "role": "배당 수령 자회사"},
        ],
        "relations": [
            {"source": "MBK파트너스", "target": "홈플러스", "type": "control", "detail": "PE 인수자/지배주주"},
        ],
        "risks": [
            {"type": "financial", "description": "6.57조원 상환에도 순부채 증가 - 부채부담이 영업현금 초과", "severity": "critical"},
            {"type": "operational", "description": "점포 확장/현대화 자본지출 제로 - 저투자로 경쟁력 약화", "severity": "high"},
            {"type": "governance", "description": "연속 손실에도 지배주주 MBK파트너스 자본지원 없음", "severity": "high"},
            {"type": "market", "description": "세일앤리스백 구조로 일반금융 대비 연간 40-50억원 추가비용 발생", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/613",
        "title": "너무 비쌌던 몸값 : 빚더미에 갇힌 홈플러스",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-04-28",
        "summary": "MBK파트너스가 2015-2016년 홈플러스를 약 5.8조원에 인수, 미실현 EV/EBITDA 멀티플 기준. 홈플러스테스코 합병으로 약 7.9조원 부채 승계, 부채비율 69%→859%.",
        "entities": [
            {"type": "company", "name": "MBK파트너스", "role": "인수 스폰서/PE"},
            {"type": "company", "name": "홈플러스", "role": "대상회사/인수부채 부담"},
            {"type": "company", "name": "테스코그룹", "role": "전 소유주/매도자"},
            {"type": "company", "name": "홈플러스테스코", "role": "합병 자회사"},
            {"type": "company", "name": "홈플러스스토어스", "role": "자회사"},
            {"type": "company", "name": "홈플러스홀딩스", "role": "합병구조 자회사"},
        ],
        "relations": [
            {"source": "MBK파트너스", "target": "홈플러스", "type": "acquisition", "detail": "5.8조원 LBO 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "부채상환능력 붕괴 - EBITDA(2700억원)가 이자비용(3000억원) 미달", "severity": "critical"},
            {"type": "operational", "description": "온라인 유통 경쟁 속 점포개선/이커머스 투자 불가", "severity": "high"},
            {"type": "market", "description": "이커머스 파괴로 할인점 매출 지속 하락", "severity": "high"},
            {"type": "governance", "description": "인수금융 부담을 인수자가 아닌 운영회사에 전가한 부채배분 구조", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/612",
        "title": "배임의 모호한 조건, MBK파트너스의 홈플러스 인수",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-04-21",
        "summary": "MBK파트너스가 2016년 대상회사가 인수자금 절반을 조달하는 LBO 구조로 홈플러스 인수. 합병형 LBO와 전통 LBO 구분 판례가 법적 결과 없이 배임 가능성 허용 논쟁.",
        "entities": [
            {"type": "company", "name": "MBK파트너스", "role": "인수 컨소시엄/PE"},
            {"type": "company", "name": "홈플러스", "role": "인수대상"},
            {"type": "company", "name": "테스코그룹", "role": "전 소유주 (5.825조원 수령)"},
            {"type": "company", "name": "홈플러스베이커리", "role": "홈플러스 자회사 (120억원 인수)"},
            {"type": "company", "name": "홈플러스테스코", "role": "인수구조 활용 자회사"},
            {"type": "company", "name": "코리아리테일인베스트먼트", "role": "MBK 설립 SPC"},
        ],
        "relations": [
            {"source": "MBK파트너스", "target": "홈플러스", "type": "acquisition", "detail": "LBO 인수"},
        ],
        "risks": [
            {"type": "legal", "description": "대상회사 자산을 명시적 공시 없이 담보로 활용 - 사기혐의 노출", "severity": "critical"},
            {"type": "governance", "description": "인수 SPC와 대상회사 비합병으로 부채가 대상회사 장부 외 유지하면서 지배권 유지", "severity": "high"},
            {"type": "regulatory", "description": "불명확한 LBO 프레임워크로 일관성 없는 집행, '구속적 의도' 해석 법원마다 상이", "severity": "high"},
            {"type": "financial", "description": "자금난 인수자가 대상회사 이익잉여금으로 인수부채 상환 - 운영자본 고갈", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/611",
        "title": "바이아웃펀드 레버리지 규제, 실효성 있나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-04-14",
        "summary": "바이아웃펀드 레버리지 규제 실효성 분석. SPC 부채비율 규제가 핵심 리스크 간과 - 인수가격이 장부가 크게 초과 시 영업권이 실제 재무취약성 은폐.",
        "entities": [
            {"type": "company", "name": "MBK파트너스", "role": "바이아웃펀드 (홈플러스 7.2조원 가치평가 인수)"},
            {"type": "company", "name": "한앤컴퍼니", "role": "바이아웃펀드"},
            {"type": "company", "name": "홈플러스", "role": "피인수회사/부채위기 리스크"},
            {"type": "company", "name": "롯데하이마트", "role": "영업권 자산 50%+ 초과 기업"},
            {"type": "company", "name": "AEP", "role": "홍콩 PE (전 홈플러스 인수자)"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "부채비율이 합병 전 양호해 보여도 영업권이 합병 후 대차대조표 지배 시 지급불능 리스크 은폐", "severity": "high"},
            {"type": "regulatory", "description": "현행 400% 부채비율 상한 부적절 - 고평가 기반 레버리지 노출 미규제", "severity": "high"},
            {"type": "governance", "description": "인수 후 경영판단으로 위장한 사전계획 부채이전으로 신인의무 보호 우회", "severity": "critical"},
            {"type": "operational", "description": "부채 증가에도 자산기반 미성장으로 현금창출 능력 제한", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/610",
        "title": "차입인수(LBO), 합법과 불법 사이",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-04-07",
        "summary": "한국 LBO 합법/불법 경계를 정립한 두 판례 분석. SK앤드케이월드코리아의 신한건설 인수와 동양메이저의 한일합섬 인수가 서로 다른 법적 결과로 선례 확립.",
        "entities": [
            {"type": "company", "name": "SK앤드케이월드코리아", "role": "SPC/신한건설 인수"},
            {"type": "company", "name": "신한건설", "role": "2001년 인수대상"},
            {"type": "company", "name": "동양메이저", "role": "한일합섬 2007년 인수 지주회사"},
            {"type": "company", "name": "한일합섬", "role": "대상회사/인수 전 회생절차"},
            {"type": "company", "name": "MBK파트너스", "role": "PE (홈플러스 인수자 참조)"},
            {"type": "person", "name": "김춘환", "role": "사업가/SK앤드케이월드코리아 대표/배임 유죄"},
        ],
        "relations": [
            {"source": "SK앤드케이월드코리아", "target": "신한건설", "type": "acquisition", "detail": "2001년 LBO 인수"},
            {"source": "동양메이저", "target": "한일합섬", "type": "acquisition", "detail": "2007년 회생절차 기업 인수"},
        ],
        "risks": [
            {"type": "legal", "description": "명시적 공시 없이 인수대상 자산 담보 활용 시 사기혐의 노출", "severity": "critical"},
            {"type": "governance", "description": "인수 SPC와 대상회사 비합병으로 지배권 유지하면서 부채 장부 외 유지", "severity": "high"},
            {"type": "regulatory", "description": "불명확한 LBO 프레임워크로 일관성 없는 집행, 법원별 '구속적 의도' 해석 상이", "severity": "high"},
            {"type": "financial", "description": "자금난 인수자가 대상회사 이익잉여금으로 인수부채 상환 - 운영자본 고갈", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/602",
        "title": "한국 배터리 3사는 왜 이리 실적이 안 좋을까?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-02-18",
        "summary": "LG에너지솔루션/삼성SDI/SK온 2024년 IRA 세액공제에도 영업이익/순이익 70%+ 급감. 글로벌 EV배터리 수요 13.3% 성장에도 매출 급감.",
        "entities": [
            {"type": "company", "name": "LG에너지솔루션", "role": "배터리 제조"},
            {"type": "company", "name": "삼성SDI", "role": "배터리 제조"},
            {"type": "company", "name": "SK온", "role": "배터리 제조"},
            {"type": "company", "name": "CATL", "role": "중국 경쟁사"},
            {"type": "company", "name": "파나소닉", "role": "일본 경쟁사"},
            {"type": "company", "name": "SK트레이딩인터내셔널", "role": "SK온 합병 파트너"},
        ],
        "relations": [],
        "risks": [
            {"type": "market", "description": "심각한 수급 불균형 - SK온 가동률 46.2%로 하락에도 산업 성장", "severity": "critical"},
            {"type": "financial", "description": "고비용 구조(매출원가율 80%+)로 가격하락 시 마진 침식 증폭", "severity": "high"},
            {"type": "operational", "description": "SK온 Q1-Q3 생산 907만셀 vs 전년 1800만셀, Q4 추정 가동률 30%", "severity": "critical"},
            {"type": "financial", "description": "SK온 연간 금융비용 1조원+으로 손실 가중", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/597",
        "title": "한앤컴퍼니 인수금융과 한온시스템의 배당부담",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-02-04",
        "summary": "한온시스템이 2015년 이후 영업현금 대비 약 3조원 초과 지출, 전액 부채(3.2조원)로 조달. 한앤컴퍼니 인수 후 배당 2배 증가(연평균 1555억원), 1.7조원 인수금융 금리 5-10% 추정.",
        "entities": [
            {"type": "company", "name": "한온시스템", "role": "피인수 자회사"},
            {"type": "company", "name": "한앤컴퍼니", "role": "PE/SPC 통한 인수"},
            {"type": "company", "name": "한앤코오토홀딩스", "role": "SPC/50.5% 지분 보유, 1.7조원 신디케이트론"},
            {"type": "company", "name": "한국타이어앤테크놀로지", "role": "공동투자자/19.49% 보유"},
        ],
        "relations": [
            {"source": "한앤컴퍼니", "target": "한온시스템", "type": "acquisition", "detail": "SPC 통한 LBO 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "유동성 위기 - 부채 3.2조원에 현금 972억원만 보유", "severity": "critical"},
            {"type": "financial", "description": "악화되는 레버리지 - 영업현금이 설비투자/배당 충당 불가", "severity": "critical"},
            {"type": "governance", "description": "배당정책이 재무안정보다 PE 스폰서 인수금융 상환 우선", "severity": "high"},
            {"type": "operational", "description": "설비투자 증가와 수익성 하락 동시 발생으로 지속불가 현금소진", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/596",
        "title": "무차입에서 빚더미에 앉은 회사로",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-01-23",
        "summary": "한온시스템이 한국 1위/세계 2위 자동차 공조장치 업체로 비스테온→한앤컴퍼니→한국타이어앤테크놀로지 소유권 전환. 매출 거의 2배(~10조원)에도 수익성 급락, 2015년 무차입에서 2024년 9월 총차입금 4.44조원.",
        "entities": [
            {"type": "company", "name": "한온시스템", "role": "자동차부품 제조"},
            {"type": "company", "name": "한앤컴퍼니", "role": "PE/전 최대주주 (50.5%)"},
            {"type": "company", "name": "한국타이어앤테크놀로지", "role": "현 최대주주 (19.49%→지배적 위치)"},
            {"type": "company", "name": "비스테온", "role": "전 소유주 (2015년 매각)"},
            {"type": "company", "name": "마그나그룹", "role": "유압제어 사업부 인수 (2019)"},
        ],
        "relations": [
            {"source": "한앤컴퍼니", "target": "한온시스템", "type": "ownership", "detail": "2015년 인수, 이후 지분 감소"},
            {"source": "한국타이어앤테크놀로지", "target": "한온시스템", "type": "ownership", "detail": "현 지배적 주주"},
        ],
        "risks": [
            {"type": "financial", "description": "순부채 2015년 4011억원→2024년 9월 3.67조원, 부채비율 282%로 급증", "severity": "critical"},
            {"type": "financial", "description": "영업이익 목표 ~5000억원 vs 실제 2773억원(2023), 최근 순손실 기록", "severity": "critical"},
            {"type": "market", "description": "국내 점유율 52%→46%(2023) 하락, 경쟁사 두원공조 상당 점유율 확보", "severity": "high"},
            {"type": "operational", "description": "생산비용 상승분 고객 전가 불가, 매출 성장에도 수익성 침식", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (15차 - 누락기사: SK쉴더스/삼성바이오/더이앤엠/홈플러스/한온시스템) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}... - {result.get('error', '')[:50]}")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
