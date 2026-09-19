"""
تركيبات الاختبار: مخطّط من الهجرات، وبيانات نظيفة لكل اختبار.

**المخطّط يُبنى من الهجرات وحدها** (`ARCHITECTURE.md:257`) مرّةً واحدة لكل جلسة
اختبار — لا بـ`create_all`، ولا بنسخٍ يدويّ لمشغّلات الهجرات. قبل و-١٢ كان
العكس: `create_all` + ~١٢٠ سطر SQL منسوخًا لخمسة مشغّلات، فكان **قيدٌ يعيش في
هجرة ولا يُنسَخ لا يراه أي اختبار**. والقياس الذي أثبت الحاجة (و-١٢ §١.١):
الأعمدة ١٥٧ ↔ ١٥٧ متطابقة وقيود `CHECK` ١٧ ↔ ١٧ متطابقة، **والمشغّلات ٥ ↔ ٠**.

وعزل الاختبارات يبقى على البيانات لا المخطّط: `TRUNCATE ... RESTART IDENTITY`
يجعل المعرّفات حتمية، فتُكتب توقّعات صريحة بدل تمرير معرّفات مجهولة. وهو **لا
يُطلق مشغّل ث-٢** — مُختبَرًا في
`test_invariants.py::test_truncate_bypasses_append_only_trigger`.

@covers ق-١٩٧, ق-٢٠٠
"""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from flask_migrate import upgrade as alembic_upgrade

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import (
    MasteryMultiplier,
    Membership,
    Org,
    RankThreshold,
    Team,
    User,
    Weight,
    WeightVersion,
)
from app.services.auth import hash_pin

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

TABLES = [
    "reading_submissions",
    "audit_log",
    "raw_rows",
    "entry_defaults",
    "fuel_scores",
    "fuel_assessments",
    "fuel_criteria",
    "fuel_activities",
    "answers",
    "daily_questions",
    "notes",
    "pilot_of_week",
    "point_events",
    "login_attempts",
    "sessions",
    "memberships",
    "weights",
    "mastery_multipliers",
    "weight_versions",
    "rank_thresholds",
    "users",
    "teams",
    "orgs",
]

PIN = "1234"
RANKS = [
    ("trainee", "طيار", 1, 0),
    ("pilot1", "طيار أول", 2, 400),
    ("squadron", "رائد سرب", 3, 900),
    ("commander", "قائد", 4, 1500),
]


@pytest.fixture(scope="session")
def _schema():
    """
    المخطّط من `alembic upgrade head` من الصفر — **مرّة واحدة لكل جلسة**.

    ما كان غاليًا في النسخة القديمة هو `create_all` + خمس كتل مشغّلات لكل اختبار
    من ٣٥٦، لا `create_app`. فالمخطّط وحده يُرفَع إلى نطاق الجلسة، **ويبقى
    التطبيق دالّيًّا** (أدناه) — والفصل ليس تحسينًا للأداء بل شرطُ صحّة:
    `test_authorization.py` يسجّل مسارات اختبارية على التطبيق داخل الاختبار،
    وFlask يرفض التسجيل بعد أوّل طلب، فتطبيقٌ واحد للجلسة يكسر ستّة اختبارات
    (مُقاسًا: وقع فعلًا قبل هذا الفصل).

    وإسقاطُ `public` ثم بناؤه من الصفر يجعل **كل تشغيلة جلسة إثباتًا لـق-٢٠٠**:
    سلسلة هجرات لا تعمل إلا تراكميًّا على قاعدة قائمة تسقط هنا صاخبةً، لا يوم النشر.
    """
    application = create_app(TestConfig)

    # حارسٌ قبل الإسقاط: اسم القاعدة يجب أن يُعلن أنها اختبارية. الكلفة سطران،
    # والبديل أن خطأً في `TEST_DATABASE_URL` يمحو قاعدة تطوير أو إنتاج بلا سؤال.
    uri = application.config["SQLALCHEMY_DATABASE_URI"]
    db_name = uri.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in db_name:
        raise RuntimeError(
            f"رفض الإسقاط: قاعدة الاختبار «{db_name}» لا يحمل اسمها كلمة test. "
            "اضبط TEST_DATABASE_URL على قاعدة اختبارية صريحة."
        )

    with application.app_context():
        db.session.execute(db.text("DROP SCHEMA public CASCADE"))
        db.session.execute(db.text("CREATE SCHEMA public"))
        db.session.commit()
        db.session.remove()
        alembic_upgrade(directory=str(MIGRATIONS_DIR))
        db.session.remove()


@pytest.fixture
def app(_schema):
    """تطبيقٌ جديد لكل اختبار على مخطّطٍ مبنيّ مرّة — نفس دلالة ما قبل و-١٢."""
    application = create_app(TestConfig)
    with application.app_context():
        yield application
        db.session.remove()


@pytest.fixture
def seeded(app):
    """منظمة وسرب وإصدار أوزان وطالبان. يُرجع القاموس بالمعرّفات الحتمية."""
    db.session.execute(db.text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
    db.session.commit()

    org = Org(name="جمعية الاختبار")
    db.session.add(org)
    db.session.flush()
    for key, name, tier, hours in RANKS:
        db.session.add(
            RankThreshold(org_id=org.id, key=key, name=name, tier=tier, at_hours=Decimal(hours))
        )
    team = Team(org_id=org.id, name="سرب الاختبار", code="TST")
    db.session.add(team)
    db.session.flush()

    # إصداران بتاريخَي سريان مختلفين — أساس اختبار ث-١١: حدثٌ ماضٍ يجب أن
    # يُحتسب بالوزن الذي كان ساريًا وقت وقوعه، لا بالوزن الحالي.
    versions = {}
    for label, effective, memorize, mastered in [
        ("old", datetime(2020, 1, 1, tzinfo=UTC), "1.0", "1.5"),
        ("new", datetime(2026, 6, 1, tzinfo=UTC), "2.5", "2.0"),
    ]:
        v = WeightVersion(org_id=org.id, effective_from=effective, note=label)
        db.session.add(v)
        db.session.flush()
        db.session.add(
            Weight(version_id=v.id, activity_type="memorize", hours_per_unit=Decimal(memorize))
        )
        # النسبة المئوية كنشاط: يثبت أن الوحدة لا تغيّر المخطط (ADR-005).
        db.session.add(
            Weight(version_id=v.id, activity_type="quran_progress", hours_per_unit=Decimal("0.2"))
        )
        # القراءة (و-٤): بالوزن المبذور نفسه في `seed.py` — فتُقاس الاختبارات
        # على ما يعمل به الإنتاج لا على رقم اختباري.
        db.session.add(
            Weight(version_id=v.id, activity_type="reading", hours_per_unit=Decimal("0.15"))
        )
        db.session.add(
            MasteryMultiplier(version_id=v.id, grade="mastered", multiplier=Decimal(mastered))
        )
        db.session.add(
            MasteryMultiplier(version_id=v.id, grade="accepted", multiplier=Decimal("1.0"))
        )
        versions[label] = v.id

    users = {}
    for name, no in [("طالب أول", "1001"), ("طالب ثانٍ", "1002")]:
        u = User(org_id=org.id, full_name=name, student_no=no, pin_hash=hash_pin(PIN))
        db.session.add(u)
        db.session.flush()
        db.session.add(Membership(org_id=org.id, user_id=u.id, team_id=team.id, role="pilot"))
        users[no] = u.id
    db.session.commit()
    return {
        "org_id": org.id,
        "team_id": team.id,
        "versions": versions,
        "users": users,
    }


@pytest.fixture
def client(app):
    return app.test_client()
