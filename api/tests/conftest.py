"""
تركيبات الاختبار: بذرة نظيفة لكل اختبار.

TRUNCATE ... RESTART IDENTITY يجعل المعرّفات حتمية، فيمكن كتابة توقّعات صريحة
بدل تمرير معرّفات مجهولة. وهو **لا يُطلق مشغّل ث-٢** — مُختبَرًا في
`test_invariants.py::test_truncate_bypasses_append_only_trigger`.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

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

TABLES = [
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


@pytest.fixture
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        db.session.execute(
            db.text("""
            CREATE OR REPLACE FUNCTION point_events_append_only() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'point_events سجلّ إلحاق فقط'; END $$ LANGUAGE plpgsql;
        """)
        )
        db.session.execute(
            db.text("DROP TRIGGER IF EXISTS point_events_no_mutation ON point_events")
        )
        db.session.execute(
            db.text("""
            CREATE TRIGGER point_events_no_mutation BEFORE UPDATE OR DELETE ON point_events
            FOR EACH ROW EXECUTE FUNCTION point_events_append_only();
        """)
        )

        # و-٧ · ث-١٣أ — سُلّم متّسق: tier أعلى ⇔ at_hours أعلى، على كل صفوف المنظمة.
        db.session.execute(
            db.text("""
            CREATE OR REPLACE FUNCTION rank_thresholds_ladder_consistent() RETURNS trigger AS $$
            DECLARE bad_tier SMALLINT;
            BEGIN
              SELECT tier INTO bad_tier FROM (
                SELECT tier, at_hours, LAG(at_hours) OVER (ORDER BY tier) AS prev_hours
                FROM rank_thresholds WHERE org_id = COALESCE(NEW.org_id, OLD.org_id)
              ) ladder WHERE prev_hours IS NOT NULL AND at_hours <= prev_hours LIMIT 1;
              IF bad_tier IS NOT NULL THEN
                RAISE EXCEPTION 'سُلّم الرتب غير متّسق: تدرّج tier يجب أن يوافقه تدرّج at_hours';
              END IF;
              RETURN NULL;
            END $$ LANGUAGE plpgsql;
        """)
        )
        db.session.execute(
            db.text("DROP TRIGGER IF EXISTS rank_thresholds_ladder_consistent ON rank_thresholds")
        )
        db.session.execute(
            db.text("""
            CREATE TRIGGER rank_thresholds_ladder_consistent
              AFTER INSERT OR UPDATE OR DELETE ON rank_thresholds
              FOR EACH ROW EXECUTE FUNCTION rank_thresholds_ladder_consistent();
        """)
        )

        # و-٧ · ث-١٣ب — الرتبة المعروضة لا تنخفض: دفاعٌ ثانٍ خلف الخدمة.
        db.session.execute(
            db.text("""
            CREATE OR REPLACE FUNCTION users_tier_never_decreases() RETURNS trigger AS $$
            BEGIN
              IF NEW.highest_achieved_tier < OLD.highest_achieved_tier THEN
                RAISE EXCEPTION 'الرتبة المكتسَبة لا تنخفض: % أقلّ من %',
                  NEW.highest_achieved_tier, OLD.highest_achieved_tier;
              END IF;
              RETURN NEW;
            END $$ LANGUAGE plpgsql;
        """)
        )
        db.session.execute(db.text("DROP TRIGGER IF EXISTS users_tier_never_decreases ON users"))
        db.session.execute(
            db.text("""
            CREATE TRIGGER users_tier_never_decreases BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION users_tier_never_decreases();
        """)
        )
        db.session.commit()
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
