#!/usr/bin/env python3
"""
스케줄러 작업 수동 실행 스크립트

배치 작업을 즉시 실행하여 테스트
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scheduler import run_job_now
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="스케줄러 작업 수동 실행")
    parser.add_argument(
        "job",
        choices=['daily_risk_analysis', 'daily_financial_update', 'weekly_data_collection', 'monthly_cleanup'],
        help="실행할 작업"
    )
    args = parser.parse_args()

    await run_job_now(args.job)


if __name__ == "__main__":
    asyncio.run(main())
