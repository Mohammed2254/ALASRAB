"""
تكافؤ الهجرات مع النماذج — و-١٢.

`ARCHITECTURE.md:257`: «**المخطط يُولَد من الهجرات وحدها**، لا من `create_all`،
وإلا اختلفت التطوير عن الإنتاج بصمت». و`conftest.py` صار يبني مخطّط الاختبار
بـ`alembic upgrade` من الصفر — فهذا الملفّ يحرس الضلع الآخر من نفس القاعدة:
أن **النماذج لم تسبق الهجرات ولا تأخّرت عنها**.

ولماذا يلزم حارسٌ صريح وقد صار المخطّط من الهجرات؟ لأن الاختبارات كلّها تتعامل
مع النماذج: عمودٌ يُضاف إلى نموذج بلا هجرة يجعل **كل اختبار يسقط** (العمود غير
موجود) — وهذا مكشوف. لكن العكس صامت: عمودٌ في هجرة لا يعرفه النموذج لا يُسقط
شيئًا، ويظهر يوم يعتمد عليه الإنتاج. وكذلك فارق **قابلية العدم**: عمودٌ
`nullable=True` في النموذج و`NOT NULL` في الهجرة يمرّ كل اختبار لا يُدخل عدمًا،
ثم يسقط على أوّل صفٍّ حقيقيّ ناقص.

القياس الذي أسّس هذه الوحدة (و-١٢ §١.١)، مأخوذًا من قاعدتين حقيقيّتين:
الأعمدة ١٥٧ ↔ ١٥٧ · قيود `CHECK` ١٧ ↔ ١٧ · **المشغّلات ٥ ↔ ٠**.
"""

from sqlalchemy import inspect

from app.extensions import db

# المشغّلات الخمسة تعيش في الهجرات وحدها — `create_all` لا يُنشئ أيًّا منها.
# كانت منسوخة يدويًّا في `conftest.py` قبل و-١٢، وحذفُ النسخة هو ما يجعل
# وجودَها هنا دليلًا على أن المصدر صار الهجرات فعلًا.
MIGRATION_ONLY_TRIGGERS = {
    "point_events_no_mutation",  # ث-٢
    "rank_thresholds_ladder_consistent",  # ث-١٣أ
    "users_tier_never_decreases",  # ث-١٣ب
    "fuel_criteria_sum_100",  # ث-١٠أ
    "fuel_scores_sum_100",  # ث-١٠ب
}


def test_migrations_and_models_declare_the_same_tables(app):
    """@covers ق-١٩٨ — جدولٌ في أحد الطرفين دون الآخر."""
    live = set(inspect(db.engine).get_table_names()) - {"alembic_version"}
    declared = set(db.metadata.tables)
    assert live == declared, (
        f"في الهجرات وحدها: {sorted(live - declared)} · "
        f"في النماذج وحدها: {sorted(declared - live)}"
    )


def test_migrations_and_models_declare_the_same_columns(app):
    """@covers ق-١٩٨ — عمودٌ في أحد الطرفين دون الآخر."""
    inspector = inspect(db.engine)
    drift = {}
    for table in sorted(db.metadata.tables):
        live = {c["name"] for c in inspector.get_columns(table)}
        declared = {c.name for c in db.metadata.tables[table].columns}
        if live != declared:
            drift[table] = {
                "في الهجرة وحدها": sorted(live - declared),
                "في النموذج وحده": sorted(declared - live),
            }
    assert not drift, drift


def test_nullability_agrees_between_migrations_and_models(app):
    """
    @covers ق-١٩٨

    الفارق الصامت الأخطر: النموذج يسمح بالعدم والقاعدة تمنعه (أو العكس). لا
    يُسقط اختبارًا لا يُدخل عدمًا، ويسقط على أوّل صفٍّ حقيقيّ ناقص في الإنتاج.
    """
    inspector = inspect(db.engine)
    mismatches = []
    for table in sorted(db.metadata.tables):
        live = {c["name"]: c["nullable"] for c in inspector.get_columns(table)}
        for col in db.metadata.tables[table].columns:
            if live[col.name] != col.nullable:
                mismatches.append(
                    f"{table}.{col.name}: الهجرة nullable={live[col.name]} · "
                    f"النموذج nullable={col.nullable}"
                )
    assert not mismatches, mismatches


def test_migration_only_triggers_exist_in_the_test_schema(app):
    """
    @covers ق-١٩٧

    الدليل البنيويّ على أن المخطّط من الهجرات: هذه الخمسة لا يُنشئها
    `create_all` إطلاقًا، وكانت تُنسَخ يدويًّا. وجودُها بعد حذف النسخة يعني أن
    المصدر تغيّر فعلًا لا أن النسخة بقيت مخفيّة.

    ولا يُغني هذا عن `test_invariants.py`: هنا نتحقّق أن المشغّل **موجود**،
    وهناك يُتحقَّق أنه **يمنع** — والفرق هو فرق الدرس ٢ (وجود العنصر ليس دليل
    عمله).
    """
    rows = db.session.execute(
        db.text("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal")
    ).scalars()
    assert set(rows) >= MIGRATION_ONLY_TRIGGERS
