"""add news tables for relationship analysis

Revision ID: 20260113_news_tables
Revises: 20260113_pipeline_runs
Create Date: 2026-01-13

뉴스 기사 기반 관계 분석 시스템 테이블입니다.

⚠️ 안전 설계:
- 기존 테이블 수정 없음 (신규 테이블만 추가)
- FK 제약 없음 (소프트 참조) - companies 삭제 시 영향 없음
- 완전 롤백 가능 (DROP TABLE만으로 제거)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260113_news_tables'
down_revision = '20260113_pipeline_runs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    News 테이블 생성

    ⚠️ 주의: 기존 테이블 수정 없음, 신규 테이블만 추가
    """

    # 1. news_articles (뉴스 기사)
    op.create_table(
        'news_articles',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),

        # 기사 정보
        sa.Column('url', sa.String(500), nullable=False, unique=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('publisher', sa.String(100), nullable=True),
        sa.Column('publish_date', sa.Date(), nullable=True),
        sa.Column('author', sa.String(100), nullable=True),

        # Claude 분석 결과
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=True),

        # 메타데이터
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('parse_version', sa.String(10), nullable=True, server_default='v4'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_news_articles_url', 'news_articles', ['url'])
    op.create_index('idx_news_articles_status', 'news_articles', ['status'])
    op.create_index('idx_news_articles_publish_date', 'news_articles', ['publish_date'])


    # 2. news_entities (기사에서 추출된 엔티티)
    op.create_table(
        'news_entities',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('article_id', sa.UUID(), nullable=False),

        # 엔티티 정보
        sa.Column('entity_type', sa.String(30), nullable=False),  # company, person, fund, spc
        sa.Column('entity_name', sa.String(200), nullable=False),
        sa.Column('entity_role', sa.String(300), nullable=True),

        # 기존 DB 매칭 (⚠️ FK 없음 - 소프트 참조)
        sa.Column('matched_company_id', sa.UUID(), nullable=True),
        sa.Column('matched_officer_id', sa.UUID(), nullable=True),
        sa.Column('matched_corp_code', sa.String(20), nullable=True),
        sa.Column('match_confidence', sa.Numeric(3, 2), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['article_id'], ['news_articles.id'], ondelete='CASCADE')
    )

    op.create_index('idx_news_entities_article', 'news_entities', ['article_id'])
    op.create_index('idx_news_entities_company', 'news_entities', ['matched_company_id'])
    op.create_index('idx_news_entities_name', 'news_entities', ['entity_name'])
    op.create_index('idx_news_entities_type', 'news_entities', ['entity_type'])


    # 3. news_relations (엔티티 간 관계)
    op.create_table(
        'news_relations',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('article_id', sa.UUID(), nullable=False),

        # 관계 주체
        sa.Column('source_entity_id', sa.UUID(), nullable=False),
        sa.Column('target_entity_id', sa.UUID(), nullable=False),

        # 관계 정보
        sa.Column('relation_type', sa.String(50), nullable=False),
        sa.Column('relation_detail', sa.String(500), nullable=True),
        sa.Column('relation_period', sa.String(100), nullable=True),
        sa.Column('risk_weight', sa.Numeric(3, 2), nullable=False, server_default='1.0'),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['article_id'], ['news_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_entity_id'], ['news_entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_entity_id'], ['news_entities.id'], ondelete='CASCADE')
    )

    op.create_index('idx_news_relations_article', 'news_relations', ['article_id'])
    op.create_index('idx_news_relations_type', 'news_relations', ['relation_type'])
    op.create_index('idx_news_relations_source', 'news_relations', ['source_entity_id'])
    op.create_index('idx_news_relations_target', 'news_relations', ['target_entity_id'])


    # 4. news_risks (위험 요소)
    op.create_table(
        'news_risks',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('article_id', sa.UUID(), nullable=False),

        sa.Column('risk_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='medium'),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['article_id'], ['news_articles.id'], ondelete='CASCADE')
    )

    op.create_index('idx_news_risks_article', 'news_risks', ['article_id'])
    op.create_index('idx_news_risks_type', 'news_risks', ['risk_type'])
    op.create_index('idx_news_risks_severity', 'news_risks', ['severity'])


    # 5. news_company_complexity (기업별 복잡도)
    op.create_table(
        'news_company_complexity',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),

        # ⚠️ 소프트 참조 (FK 없음) - companies 삭제 시 영향 없음
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('corp_code', sa.String(20), nullable=False),

        # 스코어
        sa.Column('complexity_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('complexity_grade', sa.String(5), nullable=False, server_default='A'),

        # 통계
        sa.Column('entity_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('relation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('high_risk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('article_count', sa.Integer(), nullable=False, server_default='0'),

        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', name='uq_news_company_complexity_company_id')
    )

    op.create_index('idx_news_complexity_company', 'news_company_complexity', ['company_id'])
    op.create_index('idx_news_complexity_corp', 'news_company_complexity', ['corp_code'])
    op.create_index('idx_news_complexity_grade', 'news_company_complexity', ['complexity_grade'])


def downgrade() -> None:
    """
    완전 롤백 - news_* 테이블만 삭제
    ⚠️ 기존 테이블 영향 없음
    """
    # 인덱스 삭제는 테이블 삭제 시 자동으로 처리됨
    op.drop_table('news_company_complexity')
    op.drop_table('news_risks')
    op.drop_table('news_relations')
    op.drop_table('news_entities')
    op.drop_table('news_articles')
