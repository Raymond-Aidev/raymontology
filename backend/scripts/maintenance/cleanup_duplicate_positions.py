#!/usr/bin/env python3
"""
Phase 3: Remove duplicate officer_positions records
- Removes duplicates created by NULL constraint issue
- Keeps the most recent record for each duplicate group
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
    """Remove duplicate officer_positions"""

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
        logger.info("Phase 3: Duplicate Officer Positions Cleanup")
        logger.info("=" * 80)

        # Step 1: Check current state
        logger.info("\n[Step 1] Analyzing current state...")
        total = await conn.fetchval('SELECT COUNT(*) FROM officer_positions')
        logger.info(f"Total officer_positions: {total:,}")

        # Count duplicate groups
        dup_groups_query = """
            SELECT COUNT(*) as duplicate_groups
            FROM (
                SELECT officer_id, company_id, term_start_date, source_disclosure_id
                FROM officer_positions
                GROUP BY officer_id, company_id, term_start_date, source_disclosure_id
                HAVING COUNT(*) > 1
            ) sub
        """
        dup_groups = await conn.fetchval(dup_groups_query)
        logger.info(f"Duplicate groups found: {dup_groups:,}")

        # Count total records in duplicate groups
        dup_records_query = """
            SELECT SUM(cnt) as total
            FROM (
                SELECT COUNT(*) as cnt
                FROM officer_positions
                GROUP BY officer_id, company_id, term_start_date, source_disclosure_id
                HAVING COUNT(*) > 1
            ) sub
        """
        dup_records = await conn.fetchval(dup_records_query)

        if dup_records:
            logger.info(f"Total records in duplicate groups: {dup_records:,}")
            records_to_delete = dup_records - dup_groups
            logger.info(f"Records to delete: {records_to_delete:,}")
        else:
            logger.info("No duplicate records found")
            return

        # Step 2: Show sample duplicates
        logger.info("\n[Step 2] Sample duplicate groups:")
        sample_dups = await conn.fetch("""
            SELECT
                op.officer_id,
                o.name as officer_name,
                op.company_id,
                c.name as company_name,
                op.position,
                op.term_start_date,
                op.source_disclosure_id,
                COUNT(*) as count
            FROM officer_positions op
            LEFT JOIN officers o ON op.officer_id = o.id
            LEFT JOIN companies c ON op.company_id = c.id
            GROUP BY op.officer_id, o.name, op.company_id, c.name,
                     op.position, op.term_start_date, op.source_disclosure_id
            HAVING COUNT(*) > 1
            LIMIT 5
        """)

        for row in sample_dups:
            logger.info(
                f"  {row['officer_name']} @ {row['company_name']} - "
                f"{row['position']} ({row['term_start_date']}) - "
                f"{row['count']} duplicates"
            )

        # Step 3: Delete duplicates (keep newest based on created_at)
        logger.info("\n[Step 3] Deleting duplicate records...")

        delete_query = """
            DELETE FROM officer_positions
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY officer_id, company_id, term_start_date, source_disclosure_id
                            ORDER BY created_at DESC, id DESC
                        ) as rn
                    FROM officer_positions
                ) sub
                WHERE rn > 1
            )
        """

        deleted_count = await conn.execute(delete_query)
        # Extract number from "DELETE N" response
        deleted_num = int(deleted_count.split()[1]) if deleted_count else 0
        logger.info(f"Deleted {deleted_num:,} duplicate records")

        # Step 4: Verify results
        logger.info("\n[Step 4] Verifying cleanup...")

        final_total = await conn.fetchval('SELECT COUNT(*) FROM officer_positions')
        logger.info(f"Remaining officer_positions: {final_total:,}")

        remaining_dups = await conn.fetchval(dup_groups_query)
        logger.info(f"Remaining duplicate groups: {remaining_dups:,}")

        if remaining_dups == 0:
            logger.info("✅ All duplicates successfully removed")
        else:
            logger.warning(f"⚠️  Still have {remaining_dups:,} duplicate groups")

        # Step 5: Statistics
        logger.info("\n[Step 5] Final statistics:")

        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_positions,
                COUNT(DISTINCT officer_id) as unique_officers,
                COUNT(DISTINCT company_id) as unique_companies,
                COUNT(*) FILTER (WHERE term_start_date IS NOT NULL) as with_start_date,
                COUNT(*) FILTER (WHERE term_end_date IS NOT NULL) as with_end_date,
                COUNT(*) FILTER (WHERE source_disclosure_id IS NOT NULL) as with_source,
                COUNT(*) FILTER (WHERE is_current = TRUE) as current_positions
            FROM officer_positions
        """)

        logger.info(f"  Total positions: {stats['total_positions']:,}")
        logger.info(f"  Unique officers: {stats['unique_officers']:,}")
        logger.info(f"  Unique companies: {stats['unique_companies']:,}")
        logger.info(f"  With start date: {stats['with_start_date']:,} ({stats['with_start_date']/stats['total_positions']*100:.1f}%)")
        logger.info(f"  With end date: {stats['with_end_date']:,} ({stats['with_end_date']/stats['total_positions']*100:.1f}%)")
        logger.info(f"  With source: {stats['with_source']:,} ({stats['with_source']/stats['total_positions']*100:.1f}%)")
        logger.info(f"  Current positions: {stats['current_positions']:,} ({stats['current_positions']/stats['total_positions']*100:.1f}%)")

        logger.info("\n" + "=" * 80)
        logger.info("Phase 3 Complete")
        logger.info("=" * 80)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
