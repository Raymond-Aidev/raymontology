#!/usr/bin/env python3
"""
Phase 4: Fix is_current flags in officer_positions
- Recalculate based on term_end_date (NULL = current, has value = past)
"""
import asyncio
import asyncpg
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Fix is_current flags"""

    # PostgreSQL connection
    import os
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:dev_password@postgres:5432/raymontology_dev'
    )
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        logger.info("=" * 80)
        logger.info("Phase 4: Fix is_current Flags")
        logger.info("=" * 80)

        # Step 1: Check current state
        logger.info("\n[Step 1] Analyzing current state...")

        stats_before = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_current = TRUE) as currently_true,
                COUNT(*) FILTER (WHERE is_current = FALSE) as currently_false,
                COUNT(*) FILTER (WHERE term_end_date IS NULL) as should_be_true,
                COUNT(*) FILTER (WHERE term_end_date IS NOT NULL) as should_be_false
            FROM officer_positions
        """)

        logger.info(f"Total positions: {stats_before['total']:,}")
        logger.info(f"Currently marked as current: {stats_before['currently_true']:,}")
        logger.info(f"Currently marked as past: {stats_before['currently_false']:,}")
        logger.info(f"Should be current (term_end_date IS NULL): {stats_before['should_be_true']:,}")
        logger.info(f"Should be past (term_end_date IS NOT NULL): {stats_before['should_be_false']:,}")

        # Count incorrect flags
        incorrect = await conn.fetchval("""
            SELECT COUNT(*)
            FROM officer_positions
            WHERE (is_current = TRUE AND term_end_date IS NOT NULL)
               OR (is_current = FALSE AND term_end_date IS NULL)
        """)
        logger.info(f"Incorrect flags: {incorrect:,}")

        # Step 2: Update flags
        logger.info("\n[Step 2] Updating is_current flags...")

        update_result = await conn.execute("""
            UPDATE officer_positions
            SET is_current = (term_end_date IS NULL),
                updated_at = NOW()
        """)

        # Extract number from "UPDATE N" response
        updated_num = int(update_result.split()[1]) if update_result else 0
        logger.info(f"Updated {updated_num:,} records")

        # Step 3: Verify results
        logger.info("\n[Step 3] Verifying results...")

        stats_after = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_current = TRUE) as currently_true,
                COUNT(*) FILTER (WHERE is_current = FALSE) as currently_false,
                COUNT(*) FILTER (WHERE term_end_date IS NULL) as should_be_true,
                COUNT(*) FILTER (WHERE term_end_date IS NOT NULL) as should_be_false
            FROM officer_positions
        """)

        logger.info(f"Total positions: {stats_after['total']:,}")
        logger.info(f"Marked as current: {stats_after['currently_true']:,}")
        logger.info(f"Marked as past: {stats_after['currently_false']:,}")

        # Check for any remaining inconsistencies
        incorrect_after = await conn.fetchval("""
            SELECT COUNT(*)
            FROM officer_positions
            WHERE (is_current = TRUE AND term_end_date IS NOT NULL)
               OR (is_current = FALSE AND term_end_date IS NULL)
        """)

        if incorrect_after == 0:
            logger.info("✅ All is_current flags are now correct")
        else:
            logger.warning(f"⚠️  Still have {incorrect_after:,} incorrect flags")

        # Step 4: Sample verification
        logger.info("\n[Step 4] Sample verification:")

        # Show some current positions
        current_samples = await conn.fetch("""
            SELECT
                o.name as officer_name,
                c.name as company_name,
                op.position,
                op.term_start_date,
                op.term_end_date,
                op.is_current
            FROM officer_positions op
            LEFT JOIN officers o ON op.officer_id = o.id
            LEFT JOIN companies c ON op.company_id = c.id
            WHERE op.is_current = TRUE AND op.term_start_date IS NOT NULL
            LIMIT 3
        """)

        logger.info("Sample current positions (is_current=TRUE, term_end_date=NULL):")
        for row in current_samples:
            logger.info(
                f"  {row['officer_name']} @ {row['company_name']} - "
                f"{row['position']} "
                f"(Start: {row['term_start_date']}, End: {row['term_end_date']})"
            )

        # Show any past positions (if exist)
        past_count = await conn.fetchval("""
            SELECT COUNT(*) FROM officer_positions WHERE is_current = FALSE
        """)

        if past_count > 0:
            past_samples = await conn.fetch("""
                SELECT
                    o.name as officer_name,
                    c.name as company_name,
                    op.position,
                    op.term_start_date,
                    op.term_end_date,
                    op.is_current
                FROM officer_positions op
                LEFT JOIN officers o ON op.officer_id = o.id
                LEFT JOIN companies c ON op.company_id = c.id
                WHERE op.is_current = FALSE
                LIMIT 3
            """)

            logger.info(f"\nSample past positions (is_current=FALSE, term_end_date set):")
            for row in past_samples:
                logger.info(
                    f"  {row['officer_name']} @ {row['company_name']} - "
                    f"{row['position']} "
                    f"(Start: {row['term_start_date']}, End: {row['term_end_date']})"
                )
        else:
            logger.info("\nNo past positions found (all positions are current)")

        logger.info("\n" + "=" * 80)
        logger.info("Phase 4 Complete")
        logger.info("=" * 80)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
