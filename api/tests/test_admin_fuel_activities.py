"""
أنشطة الوقود وبنودها — و-٨ · بنية تحتية لـ FR-070.
"""

from sqlalchemy import select

from app.extensions import db
from app.models import FuelActivity, FuelCriterion, Membership

ORIGIN = {"Origin": "http://localhost:5173"}


def _login(client, student_no="1001", pin="1234"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": pin}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _create(client, key, criteria):
    return client.post(
        "/api/admin/fuel/activities",
        json={"key": key, "name": "نشاط", "litres_full": "50", "criteria": criteria},
        headers=ORIGIN,
    )


# ═══ ق-٦٥ — الأوزان تجمع ١٠٠٪ ═══


def test_activity_with_weights_not_summing_to_100_is_rejected(client, seeded):
    """@covers ق-٦٥"""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _create(
        client,
        "act1",
        [
            {"key": "a", "name": "أ", "weight_pct": "40"},
            {"key": "b", "name": "ب", "weight_pct": "50"},
        ],
    )
    assert r.status_code == 422
    assert db.session.scalars(select(FuelActivity)).all() == []


def test_activity_with_weights_summing_to_100_is_accepted(client, seeded):
    """@covers ق-٦٥ — الحدّ الآخر."""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _create(
        client,
        "act2",
        [
            {"key": "a", "name": "أ", "weight_pct": "40"},
            {"key": "b", "name": "ب", "weight_pct": "60"},
        ],
    )
    assert r.status_code == 201
    assert (
        db.session.scalar(select(db.func.count(FuelCriterion.id))) == 2
    )


def test_activities_list_includes_criteria(client, seeded):
    _make_admin(seeded["users"]["1001"])
    _login(client)
    _create(client, "act3", [{"key": "a", "name": "أ", "weight_pct": "100"}])

    body = client.get("/api/admin/fuel/activities", headers=ORIGIN).json
    assert body["activities"][0]["key"] == "act3"
    assert body["activities"][0]["criteria"][0]["weight_pct"] == "100.00"
