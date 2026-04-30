"""consolidate_stock_lists_and_constraints

Revision ID: b7c9d4e1f2a3
Revises: 9799b31d992d
Create Date: 2026-04-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "b7c9d4e1f2a3"
down_revision = "9799b31d992d"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _unique_constraint_exists(inspector, table_name: str, constraint_name: str) -> bool:
    return constraint_name in {
        constraint["name"] for constraint in inspector.get_unique_constraints(table_name)
    }


def _check_constraint_exists(inspector, table_name: str, constraint_name: str) -> bool:
    return constraint_name in {
        constraint["name"] for constraint in inspector.get_check_constraints(table_name)
    }


def _add_check_constraint_not_valid(
    conn, inspector, table_name: str, constraint_name: str, expression: str
) -> None:
    if not _table_exists(inspector, table_name):
        return
    if _check_constraint_exists(inspector, table_name, constraint_name):
        return
    conn.execute(
        sa.text(
            f"ALTER TABLE {table_name} "
            f"ADD CONSTRAINT {constraint_name} CHECK ({expression}) NOT VALID"
        )
    )


def _merge_duplicate_stocks(conn, inspector) -> None:
    if not _table_exists(inspector, "stocks"):
        return

    conn.execute(
        sa.text(
            """
            CREATE TEMP TABLE stock_dedupe AS
            WITH ranked AS (
                SELECT id,
                       min(id) OVER (PARTITION BY symbol, market) AS keeper_id
                FROM stocks
            )
            SELECT id AS duplicate_id, keeper_id
            FROM ranked
            WHERE id <> keeper_id
            """
        )
    )

    duplicate_count = conn.execute(sa.text("SELECT count(*) FROM stock_dedupe")).scalar()
    if not duplicate_count:
        conn.execute(sa.text("DROP TABLE stock_dedupe"))
        return

    if _table_exists(inspector, "price_history"):
        conn.execute(
            sa.text(
                """
                DELETE FROM price_history d
                USING stock_dedupe m, price_history k
                WHERE d.stock_id = m.duplicate_id
                  AND k.stock_id = m.keeper_id
                  AND k.date = d.date
                """
            )
        )
        conn.execute(
            sa.text(
                """
                UPDATE price_history p
                SET stock_id = m.keeper_id
                FROM stock_dedupe m
                WHERE p.stock_id = m.duplicate_id
                """
            )
        )

    if _table_exists(inspector, "technical_indicators"):
        conn.execute(
            sa.text(
                """
                DELETE FROM technical_indicators d
                USING stock_dedupe m, technical_indicators k
                WHERE d.stock_id = m.duplicate_id
                  AND k.stock_id = m.keeper_id
                  AND k.date = d.date
                  AND k.indicator_type = d.indicator_type
                """
            )
        )
        conn.execute(
            sa.text(
                """
                UPDATE technical_indicators t
                SET stock_id = m.keeper_id
                FROM stock_dedupe m
                WHERE t.stock_id = m.duplicate_id
                """
            )
        )

    if _table_exists(inspector, "trading_signals"):
        conn.execute(
            sa.text(
                """
                UPDATE trading_signals t
                SET stock_id = m.keeper_id
                FROM stock_dedupe m
                WHERE t.stock_id = m.duplicate_id
                """
            )
        )

    if _table_exists(inspector, "strategy_signals"):
        conn.execute(
            sa.text(
                """
                UPDATE strategy_signals s
                SET stock_id = m.keeper_id
                FROM stock_dedupe m
                WHERE s.stock_id = m.duplicate_id
                """
            )
        )

    if _table_exists(inspector, "user_portfolios"):
        if _table_exists(inspector, "transactions"):
            conn.execute(
                sa.text(
                    """
                    UPDATE transactions t
                    SET portfolio_id = keeper.id
                    FROM user_portfolios duplicate
                    JOIN stock_dedupe m ON duplicate.stock_id = m.duplicate_id
                    JOIN user_portfolios keeper
                      ON keeper.user_id = duplicate.user_id
                     AND keeper.stock_id = m.keeper_id
                    WHERE t.portfolio_id = duplicate.id
                    """
                )
            )
        conn.execute(
            sa.text(
                """
                UPDATE user_portfolios keeper
                SET quantity = keeper.quantity + duplicate.quantity,
                    total_cost = keeper.total_cost + duplicate.total_cost,
                    avg_cost = CASE
                        WHEN keeper.quantity + duplicate.quantity > 0
                        THEN (keeper.total_cost + duplicate.total_cost)
                             / (keeper.quantity + duplicate.quantity)
                        ELSE 0
                    END
                FROM user_portfolios duplicate
                JOIN stock_dedupe m ON duplicate.stock_id = m.duplicate_id
                WHERE keeper.user_id = duplicate.user_id
                  AND keeper.stock_id = m.keeper_id
                """
            )
        )
        conn.execute(
            sa.text(
                """
                DELETE FROM user_portfolios duplicate
                USING stock_dedupe m, user_portfolios keeper
                WHERE duplicate.stock_id = m.duplicate_id
                  AND keeper.user_id = duplicate.user_id
                  AND keeper.stock_id = m.keeper_id
                """
            )
        )
        conn.execute(
            sa.text(
                """
                UPDATE user_portfolios p
                SET stock_id = m.keeper_id
                FROM stock_dedupe m
                WHERE p.stock_id = m.duplicate_id
                """
            )
        )

    if _table_exists(inspector, "transactions"):
        conn.execute(
            sa.text(
                """
                UPDATE transactions t
                SET stock_id = m.keeper_id
                FROM stock_dedupe m
                WHERE t.stock_id = m.duplicate_id
                """
            )
        )

    if _table_exists(inspector, "user_stock_list_items"):
        conn.execute(
            sa.text(
                """
                DELETE FROM user_stock_list_items d
                USING stock_dedupe m, user_stock_list_items k
                WHERE d.stock_id = m.duplicate_id
                  AND k.stock_id = m.keeper_id
                  AND k.list_id = d.list_id
                """
            )
        )
        conn.execute(
            sa.text(
                """
                UPDATE user_stock_list_items i
                SET stock_id = m.keeper_id
                FROM stock_dedupe m
                WHERE i.stock_id = m.duplicate_id
                """
            )
        )

    if _table_exists(inspector, "user_watchlists"):
        conn.execute(
            sa.text(
                """
                DELETE FROM user_watchlists d
                USING stock_dedupe m, user_watchlists k
                WHERE d.stock_id = m.duplicate_id
                  AND k.stock_id = m.keeper_id
                  AND k.user_id = d.user_id
                """
            )
        )
        conn.execute(
            sa.text(
                """
                UPDATE user_watchlists w
                SET stock_id = m.keeper_id
                FROM stock_dedupe m
                WHERE w.stock_id = m.duplicate_id
                """
            )
        )

    conn.execute(
        sa.text(
            """
            DELETE FROM stocks s
            USING stock_dedupe m
            WHERE s.id = m.duplicate_id
            """
        )
    )
    conn.execute(sa.text("DROP TABLE stock_dedupe"))


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if _table_exists(inspector, "stocks"):
        _merge_duplicate_stocks(conn, inspector)
        inspector = sa.inspect(conn)
        if not _unique_constraint_exists(inspector, "stocks", "uq_stocks_symbol_market"):
            op.create_unique_constraint(
                "uq_stocks_symbol_market", "stocks", ["symbol", "market"]
            )
        if not _index_exists(inspector, "stocks", "ix_stocks_market_is_active"):
            op.create_index(
                "ix_stocks_market_is_active", "stocks", ["market", "is_active"]
            )

    if _table_exists(inspector, "user_stock_lists"):
        conn.execute(
            sa.text(
                """
                WITH ranked_defaults AS (
                    SELECT id,
                           row_number() OVER (
                               PARTITION BY user_id
                               ORDER BY sort_order, created_at, id
                           ) AS rn
                    FROM user_stock_lists
                    WHERE is_default = true
                )
                UPDATE user_stock_lists
                SET is_default = false
                WHERE id IN (SELECT id FROM ranked_defaults WHERE rn > 1)
                """
            )
        )
        conn.execute(
            sa.text(
                """
                WITH ranked_lists AS (
                    SELECT id,
                           user_id,
                           row_number() OVER (
                               PARTITION BY user_id
                               ORDER BY sort_order, created_at, id
                           ) AS rn
                    FROM user_stock_lists
                )
                UPDATE user_stock_lists l
                SET is_default = true
                FROM ranked_lists r
                WHERE l.id = r.id
                  AND r.rn = 1
                  AND NOT EXISTS (
                      SELECT 1
                      FROM user_stock_lists d
                      WHERE d.user_id = l.user_id
                        AND d.is_default = true
                  )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO user_stock_lists (
                    user_id, name, description, is_default,
                    sort_order, created_at, updated_at
                )
                SELECT u.id,
                       '我的觀察清單',
                       '預設觀察清單',
                       true,
                       0,
                       now(),
                       now()
                FROM users u
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM user_stock_lists l
                    WHERE l.user_id = u.id
                )
                """
            )
        )

        if not _index_exists(
            inspector, "user_stock_lists", "uq_user_stock_lists_one_default_per_user"
        ):
            op.create_index(
                "uq_user_stock_lists_one_default_per_user",
                "user_stock_lists",
                ["user_id"],
                unique=True,
                postgresql_where=sa.text("is_default = true"),
            )

    if _table_exists(inspector, "user_stock_list_items"):
        if not _index_exists(
            inspector, "user_stock_list_items", "ix_user_stock_list_items_list_sort"
        ):
            op.create_index(
                "ix_user_stock_list_items_list_sort",
                "user_stock_list_items",
                ["list_id", "sort_order"],
            )

    if _table_exists(inspector, "user_watchlists") and _table_exists(
        inspector, "user_stock_list_items"
    ):
        conn.execute(
            sa.text(
                """
                INSERT INTO user_stock_list_items (
                    list_id, stock_id, note, sort_order, created_at, updated_at
                )
                SELECT default_list.id,
                       w.stock_id,
                       NULL,
                       0,
                       COALESCE(w.created_at, now()),
                       COALESCE(w.updated_at, w.created_at, now())
                FROM user_watchlists w
                JOIN LATERAL (
                    SELECT l.id
                    FROM user_stock_lists l
                    WHERE l.user_id = w.user_id
                      AND l.is_default = true
                    ORDER BY l.sort_order, l.created_at, l.id
                    LIMIT 1
                ) default_list ON true
                ON CONFLICT (list_id, stock_id) DO NOTHING
                """
            )
        )
        op.drop_table("user_watchlists")

    inspector = sa.inspect(conn)
    _add_check_constraint_not_valid(
        conn,
        inspector,
        "user_portfolios",
        "ck_user_portfolios_quantity_positive",
        "quantity > 0",
    )
    _add_check_constraint_not_valid(
        conn,
        inspector,
        "user_portfolios",
        "ck_user_portfolios_avg_cost_non_negative",
        "avg_cost >= 0",
    )
    _add_check_constraint_not_valid(
        conn,
        inspector,
        "user_portfolios",
        "ck_user_portfolios_total_cost_non_negative",
        "total_cost >= 0",
    )
    _add_check_constraint_not_valid(
        conn,
        inspector,
        "transactions",
        "ck_transactions_transaction_type",
        "transaction_type IN ('BUY', 'SELL')",
    )
    _add_check_constraint_not_valid(
        conn, inspector, "transactions", "ck_transactions_quantity_positive", "quantity > 0"
    )
    _add_check_constraint_not_valid(
        conn, inspector, "transactions", "ck_transactions_price_positive", "price > 0"
    )
    _add_check_constraint_not_valid(
        conn,
        inspector,
        "transactions",
        "ck_transactions_fee_non_negative",
        "fee >= 0",
    )
    _add_check_constraint_not_valid(
        conn,
        inspector,
        "transactions",
        "ck_transactions_tax_non_negative",
        "tax >= 0",
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table_name, constraint_name in [
        ("transactions", "ck_transactions_tax_non_negative"),
        ("transactions", "ck_transactions_fee_non_negative"),
        ("transactions", "ck_transactions_price_positive"),
        ("transactions", "ck_transactions_quantity_positive"),
        ("transactions", "ck_transactions_transaction_type"),
        ("user_portfolios", "ck_user_portfolios_total_cost_non_negative"),
        ("user_portfolios", "ck_user_portfolios_avg_cost_non_negative"),
        ("user_portfolios", "ck_user_portfolios_quantity_positive"),
    ]:
        if _table_exists(inspector, table_name) and _check_constraint_exists(
            inspector, table_name, constraint_name
        ):
            op.drop_constraint(constraint_name, table_name, type_="check")

    if _table_exists(inspector, "user_stock_list_items") and _index_exists(
        inspector, "user_stock_list_items", "ix_user_stock_list_items_list_sort"
    ):
        op.drop_index(
            "ix_user_stock_list_items_list_sort", table_name="user_stock_list_items"
        )

    if _table_exists(inspector, "user_stock_lists") and _index_exists(
        inspector, "user_stock_lists", "uq_user_stock_lists_one_default_per_user"
    ):
        op.drop_index(
            "uq_user_stock_lists_one_default_per_user", table_name="user_stock_lists"
        )

    if not _table_exists(inspector, "user_watchlists") and _table_exists(
        inspector, "users"
    ):
        op.create_table(
            "user_watchlists",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("stock_id", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id", "stock_id", name="uq_user_watchlists_user_id_stock_id"
            ),
            comment="用戶自選股表",
        )

    if _table_exists(inspector, "stocks"):
        if _index_exists(inspector, "stocks", "ix_stocks_market_is_active"):
            op.drop_index("ix_stocks_market_is_active", table_name="stocks")
        if _unique_constraint_exists(inspector, "stocks", "uq_stocks_symbol_market"):
            op.drop_constraint("uq_stocks_symbol_market", "stocks", type_="unique")
