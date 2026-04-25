"""
数据库迁移：第一阶段板块扩展
- 添加 sectors / sub_sectors / concepts / stock_concept_map 表
- 添加 stock_price_snapshots 表
- 扩展 companies 表（gics_sector, tier, market_cap）
- 扩展 news 表（sector_id, concept_ids）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "001_sector_expansion"
down_revision = "b2c94e8565bf"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. 大板块 ──────────────────────────────────────────────────────────────
    op.create_table(
        "sectors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("gics_code", sa.String(10), nullable=True),
        sa.Column("etf_ticker", sa.String(10), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
    )

    # ── 2. 细分行业 ────────────────────────────────────────────────────────────
    op.create_table(
        "sub_sectors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sector_id", sa.Integer(), sa.ForeignKey("sectors.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(100), nullable=False),
    )

    # ── 3. 主题概念 ────────────────────────────────────────────────────────────
    op.create_table(
        "concepts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("related_tickers", postgresql.ARRAY(sa.String(10)), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )

    # ── 4. 股票-概念映射 ───────────────────────────────────────────────────────
    op.create_table(
        "stock_concept_map",
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("concept_id", sa.Integer(), sa.ForeignKey("concepts.id"), nullable=False),
        sa.Column("weight", sa.Float(), server_default="1.0"),
        sa.PrimaryKeyConstraint("ticker", "concept_id"),
    )

    # ── 5. 行情日快照 ──────────────────────────────────────────────────────────
    op.create_table(
        "stock_price_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("open_price", sa.Float(), nullable=True),
        sa.Column("close_price", sa.Float(), nullable=True),
        sa.Column("high_price", sa.Float(), nullable=True),
        sa.Column("low_price", sa.Float(), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("change_pct", sa.Float(), nullable=True),
        sa.Column("avg_volume_20d", sa.Float(), nullable=True),
        sa.Column("volume_ratio", sa.Float(), nullable=True),
        sa.Column("market_cap", sa.BigInteger(), nullable=True),
        sa.UniqueConstraint("ticker", "snapshot_date", name="uq_ticker_date"),
    )
    op.create_index("ix_snapshots_ticker", "stock_price_snapshots", ["ticker"])

    # ── 6. 扩展 companies 表 ───────────────────────────────────────────────────
    op.add_column("companies", sa.Column("gics_sector",     sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("gics_sub_sector", sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("sp500_rank",      sa.Integer(),   nullable=True))
    op.add_column("companies", sa.Column("market_cap",      sa.BigInteger(),nullable=True))
    op.add_column("companies", sa.Column("tier",            sa.String(1),   server_default="B"))

    # ── 7. 扩展 news 表 ────────────────────────────────────────────────────────
    op.add_column("news", sa.Column(
        "sector_id", sa.Integer(),
        sa.ForeignKey("sectors.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.add_column("news", sa.Column(
        "concept_ids", postgresql.ARRAY(sa.Integer()), nullable=True
    ))
    op.create_index("ix_news_sector_id", "news", ["sector_id"])


def downgrade():
    op.drop_index("ix_news_sector_id", "news")
    op.drop_column("news", "concept_ids")
    op.drop_column("news", "sector_id")
    op.drop_column("companies", "tier")
    op.drop_column("companies", "market_cap")
    op.drop_column("companies", "sp500_rank")
    op.drop_column("companies", "gics_sub_sector")
    op.drop_column("companies", "gics_sector")
    op.drop_index("ix_snapshots_ticker", "stock_price_snapshots")
    op.drop_table("stock_price_snapshots")
    op.drop_table("stock_concept_map")
    op.drop_table("concepts")
    op.drop_table("sub_sectors")
    op.drop_table("sectors")
