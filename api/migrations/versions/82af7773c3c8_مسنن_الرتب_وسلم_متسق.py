"""مِسنَن الرتب وسُلّم متّسق — و-٧ · ث-١٣أ · ث-١٣ب

Revision ID: 82af7773c3c8
Revises: 4f30424304cb
Create Date: 2026-09-01 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '82af7773c3c8'
down_revision = '4f30424304cb'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column(
            'highest_achieved_tier',
            sa.SmallInteger(),
            nullable=False,
            server_default='0',
        ),
    )

    # ═══════════════════════════════════════════════════════════════════════
    # ث-١٣أ — سُلّم العتبات متّسق: tier أعلى ⇔ at_hours أعلى.
    #
    # لا CHECK صفّي: الادّعاء يمتدّ على كل صفوف المنظمة نفسها (نفس علّة استعمال
    # مشغّل لا قيد في نموذج ث-٢). AFTER لا BEFORE — يفحص الحالة بعد الكتابة
    # فيرى الصفوف الأخرى في نفس المعاملة، ويرفع استثناءً يُرجع المعاملة كلّها.
    # ═══════════════════════════════════════════════════════════════════════
    op.execute("""
        CREATE OR REPLACE FUNCTION rank_thresholds_ladder_consistent() RETURNS trigger AS $$
        DECLARE
          bad_tier SMALLINT;
        BEGIN
          SELECT tier INTO bad_tier
          FROM (
            SELECT tier, at_hours,
                   LAG(at_hours) OVER (ORDER BY tier) AS prev_hours
            FROM rank_thresholds
            WHERE org_id = COALESCE(NEW.org_id, OLD.org_id)
          ) ladder
          WHERE prev_hours IS NOT NULL AND at_hours <= prev_hours
          LIMIT 1;

          IF bad_tier IS NOT NULL THEN
            RAISE EXCEPTION
              'سُلّم الرتب غير متّسق: تدرّج tier يجب أن يوافقه تدرّج at_hours';
          END IF;
          RETURN NULL;
        END $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER rank_thresholds_ladder_consistent
          AFTER INSERT OR UPDATE OR DELETE ON rank_thresholds
          FOR EACH ROW EXECUTE FUNCTION rank_thresholds_ladder_consistent();
    """)

    # ═══════════════════════════════════════════════════════════════════════
    # ث-١٣ب — الرتبة المعروضة لا تنخفض: دفاعٌ ثانٍ خلف خدمة rules_admin التي
    # لا ترفع القيمة إلا صعودًا. لو نسيَ كودٌ مستقبليّ هذا الشرط، القاعدة ترفضه.
    # ═══════════════════════════════════════════════════════════════════════
    op.execute("""
        CREATE OR REPLACE FUNCTION users_tier_never_decreases() RETURNS trigger AS $$
        BEGIN
          IF NEW.highest_achieved_tier < OLD.highest_achieved_tier THEN
            RAISE EXCEPTION
              'الرتبة المكتسَبة لا تنخفض: % أقلّ من %',
              NEW.highest_achieved_tier, OLD.highest_achieved_tier;
          END IF;
          RETURN NEW;
        END $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER users_tier_never_decreases
          BEFORE UPDATE ON users
          FOR EACH ROW EXECUTE FUNCTION users_tier_never_decreases();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS users_tier_never_decreases ON users;")
    op.execute("DROP FUNCTION IF EXISTS users_tier_never_decreases();")
    op.execute("DROP TRIGGER IF EXISTS rank_thresholds_ladder_consistent ON rank_thresholds;")
    op.execute("DROP FUNCTION IF EXISTS rank_thresholds_ladder_consistent();")
    op.drop_column('users', 'highest_achieved_tier')
