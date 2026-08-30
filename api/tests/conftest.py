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

    version = WeightVersion(org_id=org.id, effective_from=datetime(2020, 1, 1, tzinfo=UTC))
    db.session.add(version)
    db.session.flush()
    db.session.add(
        Weight(version_id=version.id, activity_type="memorize", hours_per_unit=Decimal("2.5"))
    )
    db.session.add(
        MasteryMultiplier(version_id=version.id, grade="accepted", multiplier=Decimal("1.0"))
    )

    users = {}
    for name, no in [("طالب أول", "1001"), ("طالب ثانٍ", "1002")]:
        u = User(org_id=org.id, full_name=name, student_no=no, pin_hash=hash_pin(PIN))
        db.session.add(u)
        db.session.flush()
        db.session.add(Membership(org_id=org.id, user_id=u.id, team_id=team.id, role="pilot"))
        users[no] = u.id
    db.session.commit()
    return {"org_id": org.id, "team_id": team.id, "version_id": version.id, "users": users}


@pytest.fixture
def client(app):
    return app.test_client()
