"""الوقود — أربعة جداول وث-١٠أ/ث-١٠ب — و-٨

Revision ID: 0f51d36d558b
Revises: 82af7773c3c8
Create Date: 2026-09-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0f51d36d558b'
down_revision = '82af7773c3c8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'fuel_activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('litres_full', sa.Numeric(8, 2), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('litres_full > 0', name='fuel_activities_litres_full_positive'),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id', 'key', name='uq_fuel_activity_key'),
    )

    op.create_table(
        'fuel_criteria',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('activity_id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('weight_pct', sa.Numeric(5, 2), nullable=False),
        sa.Column('position', sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            'weight_pct > 0 AND weight_pct <= 100', name='fuel_criteria_weight_range'
        ),
        sa.ForeignKeyConstraint(['activity_id'], ['fuel_activities.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('activity_id', 'key', name='uq_fuel_criterion_key'),
    )

    op.create_table(
        'fuel_assessments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('activity_id', sa.Integer(), nullable=False),
        sa.Column('occurred_on', sa.Date(), nullable=False),
        sa.Column('total_pct', sa.Numeric(6, 2), nullable=False),
        sa.Column('litres', sa.Numeric(8, 2), nullable=False),
        sa.Column('note', sa.String(), nullable=True),
        sa.Column('actor_id', sa.Integer(), nullable=False),
        sa.Column('point_event_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('total_pct >= 0', name='fuel_assessment_total_pct_non_negative'),
        sa.CheckConstraint('litres >= 0', name='fuel_assessment_litres_non_negative'),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['activity_id'], ['fuel_activities.id']),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id']),
        sa.ForeignKeyConstraint(['point_event_id'], ['point_events.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'activity_id', 'occurred_on', name='uq_fuel_assessment_per_day'),
    )
    with op.batch_alter_table('fuel_assessments', schema=None) as batch_op:
        batch_op.create_index(
            'ix_fuel_assessment_team_time', ['org_id', 'team_id', 'occurred_on'], unique=False
        )

    op.create_table(
        'fuel_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column('criterion_id', sa.Integer(), nullable=False),
        sa.Column('score_pct', sa.Numeric(5, 2), nullable=False),
        sa.CheckConstraint('score_pct >= 0 AND score_pct <= 100', name='fuel_scores_score_range'),
        sa.ForeignKeyConstraint(['assessment_id'], ['fuel_assessments.id']),
        sa.ForeignKeyConstraint(['criterion_id'], ['fuel_criteria.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', 'criterion_id', name='uq_fuel_score_per_criterion'),
    )

    # ═══════════════════════════════════════════════════════════════════════
    # ث-١٠أ — تعريف البنود: مجموع weight_pct لكل بنود نشاط واحد = ١٠٠ بالضبط.
    #
    # **مؤجَّل إلى نهاية المعاملة (DEFERRABLE INITIALLY DEFERRED) لا فوريّ**:
    # إنشاء نشاط جديد يُدرج بنوده صفًّا صفًّا، وفحصًا فوريًّا بعد كل صفّ يرفض
    # حتى الحالة الصحيحة (٤٠٪ وحدها ليست ١٠٠٪ قبل أن يُدرَج بند الـ٦٠٪ التالي).
    # **أُثبت هذا عمليًّا لا افتُرض**: مشغّل فوريّ أسقط إدراجًا صحيحًا بالكامل
    # (٤٠+٦٠) لأنه فحص بعد الصفّ الأوّل وحده. التأجيل يفحص مرّة واحدة، بعد أن
    # تستقرّ كل الصفوف، عند COMMIT — تمامًا كما يحتاج المستخدم فعليًّا.
    # ═══════════════════════════════════════════════════════════════════════
    op.execute("""
        CREATE OR REPLACE FUNCTION fuel_criteria_sum_100() RETURNS trigger AS $$
        DECLARE total NUMERIC;
        BEGIN
          SELECT COALESCE(SUM(weight_pct), 0) INTO total
          FROM fuel_criteria WHERE activity_id = COALESCE(NEW.activity_id, OLD.activity_id);
          IF total <> 100 THEN
            RAISE EXCEPTION 'أوزان بنود النشاط يجب أن تجمع 100%% بالضبط — المجموع الحالي %', total;
          END IF;
          RETURN NULL;
        END $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER fuel_criteria_sum_100
          AFTER INSERT OR UPDATE OR DELETE ON fuel_criteria
          DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION fuel_criteria_sum_100();
    """)

    # ═══════════════════════════════════════════════════════════════════════
    # ث-١٠ب — لحظة التقييم: مجموع weight_pct للبنود المُقيَّمة فعلًا (عبر
    # fuel_scores لهذا التقييم) = ١٠٠ بالضبط. يمسك انجرافًا بين تعريف النشاط
    # ولحظة استعماله — لا يكرّر ث-١٠أ، يفحص نقطة زمنية مختلفة تمامًا.
    # **مؤجَّل لنفس السبب**: تقييم يُدخل عدّة درجات صفًّا صفًّا.
    # ═══════════════════════════════════════════════════════════════════════
    op.execute("""
        CREATE OR REPLACE FUNCTION fuel_scores_sum_100() RETURNS trigger AS $$
        DECLARE total NUMERIC;
        BEGIN
          SELECT COALESCE(SUM(fc.weight_pct), 0) INTO total
          FROM fuel_scores fs JOIN fuel_criteria fc ON fc.id = fs.criterion_id
          WHERE fs.assessment_id = COALESCE(NEW.assessment_id, OLD.assessment_id);
          IF total <> 100 THEN
            RAISE EXCEPTION 'أوزان البنود المقيَّمة يجب أن تجمع 100%% بالضبط — المجموع الحالي %', total;
          END IF;
          RETURN NULL;
        END $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER fuel_scores_sum_100
          AFTER INSERT OR UPDATE OR DELETE ON fuel_scores
          DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION fuel_scores_sum_100();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS fuel_scores_sum_100 ON fuel_scores;")
    op.execute("DROP FUNCTION IF EXISTS fuel_scores_sum_100();")
    op.execute("DROP TRIGGER IF EXISTS fuel_criteria_sum_100 ON fuel_criteria;")
    op.execute("DROP FUNCTION IF EXISTS fuel_criteria_sum_100();")
    op.drop_table('fuel_scores')
    with op.batch_alter_table('fuel_assessments', schema=None) as batch_op:
        batch_op.drop_index('ix_fuel_assessment_team_time')
    op.drop_table('fuel_assessments')
    op.drop_table('fuel_criteria')
    op.drop_table('fuel_activities')
