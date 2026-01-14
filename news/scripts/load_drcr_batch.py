#!/usr/bin/env python3
"""
DRCR 기사 배치 적재 스크립트
WebFetch를 통해 기사를 파싱하고 DB에 적재
"""
import asyncio
import sys
import os
import json
import aiohttp
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

# 이미 적재된 기사 ID
LOADED_IDS = {637, 638, 640, 641, 642, 643, 644, 645, 646, 647}

# 적재 대상 기사 ID (최신순)
# 스크롤링으로 수집한 전체 ID 목록
ALL_ARTICLE_IDS = [
    636, 635, 634, 633, 632, 631, 629, 628, 627, 626, 625,  # 에이프로젠 연대기
    609, 608, 607, 606, 605, 604, 603, 601, 600, 599, 598,  # SK온, 바이오엑스
    595, 594, 593, 592, 591, 590, 589, 588, 587, 586, 585, 584, 583, 582, 578, 577, 576, 575,  # 무궁화신탁
    570, 569, 568, 567, 566, 565, 564, 563, 562, 561, 560, 559,  # 퀀타피아
    552, 543, 542, 541, 540, 539, 538,  # 위즈돔
    532, 531, 530, 529, 528, 527, 526, 525, 524, 523, 522, 520, 519, 518, 517, 516,  # 엔켐
    515, 514, 513, 512, 511, 510, 509, 508, 507, 506, 505, 504, 503, 502,  # 초전도체 테마주
    438, 437, 436, 435, 434,  # 삼표그룹
    397, 396, 393, 392,  # 롯데건설/롯데쇼핑
    382, 381, 380, 376, 364, 363, 359,  # 에이티세미콘, 금강공업
    326, 325, 324, 323, 322,  # BYC
    284, 283, 282, 281, 280, 279, 278, 277, 276, 275, 274, 273, 272, 271, 270, 269, 268, 267, 266, 265, 264, 263, 262, 261,  # 에이티세미콘, 릭스솔루션
    219, 217, 216, 215, 214, 213, 212, 211, 210, 209, 208,  # 경남제약, IHQ
    203, 202, 201, 200, 199, 198, 197, 196, 195, 194, 193, 192, 191, 190, 189, 188, 187, 186, 185,  # 필룩스
    178, 177, 176, 175, 174, 173,  # 아이오케이, 비덴트
]

# 신규 적재 대상 (이미 적재된 것 제외)
NEW_ARTICLE_IDS = [aid for aid in ALL_ARTICLE_IDS if aid not in LOADED_IDS]


async def fetch_article_content(session, article_id: int) -> dict | None:
    """DRCR 기사 내용 가져오기"""
    url = f"https://www.drcr.co.kr/articles/{article_id}"

    try:
        async with session.get(url, timeout=30) as response:
            if response.status != 200:
                return None
            html = await response.text()
            return {"url": url, "html": html, "id": article_id}
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


async def main():
    """메인 실행 함수"""
    print("=== DRCR 기사 배치 적재 ===\n")

    # 적재 전 통계
    before_stats = await get_article_stats()
    print(f"적재 전 통계:")
    print(f"  - Articles: {before_stats['articles']}")
    print(f"  - Entities: {before_stats['entities']}")
    print(f"  - Relations: {before_stats['relations']}")
    print(f"  - Risks: {before_stats['risks']}")
    print()

    print(f"적재 대상: {len(NEW_ARTICLE_IDS)}개 기사")
    print(f"이미 적재됨: {len(LOADED_IDS)}개 기사")
    print()

    # 기사 ID 목록 출력
    print("신규 적재 대상 기사 ID:")
    for i in range(0, len(NEW_ARTICLE_IDS), 20):
        chunk = NEW_ARTICLE_IDS[i:i+20]
        print(f"  {chunk}")
    print()

    print("적재를 시작하려면 별도의 파싱 작업이 필요합니다.")
    print("WebFetch 도구를 사용하여 각 기사를 파싱하고 엔티티/관계/리스크를 추출해야 합니다.")


if __name__ == "__main__":
    asyncio.run(main())
