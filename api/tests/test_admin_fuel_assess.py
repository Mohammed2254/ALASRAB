"""
تقييم نشاط الوقود — و-٨ · FR-070 · FR-071.
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.extensions import db
from app.models import AuditEntry, Membership, Org, PointEvent

ORIGIN = {"Origin": "http://localhost:5173"}


def _login(client, student_no="1001", pin="1234"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": pin}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _create_activity(client, key="act", litres_full="50"):
    client.post(
        "/api/admin/fuel/activities",
        json={
            "key": key,
            "name": "الحفظ الجماعي",
            "litres_full": litres_full,
            "criteria": [
                {"key": "attendance", "name": "الحضور", "weight_pct": "40"},
                {"key": "quality", "name": "الجودة", "weight_pct": "60"},
            ],
        },
        headers=ORIGIN,
    )
    activity = client.get("/api/admin/fuel/activities", headers=ORIGIN).json["activities"][-1]
    return activity["id"], activity["criteria"][0]["id"], activity["criteria"][1]["id"]


def _assess(client, team_id, activity_id, occurred_on, scores, note=None):
    return client.post(
        "/api/admin/fuel/assess",
        json={
            "team_id": team_id,
            "activity_id": activity_id,
            "occurred_on": occurred_on,
            "scores": scores,
            "note": note,
        },
        headers=ORIGIN,
    )


# ═══ ق-٦٦ — تغطية جزئية ترفض (مسار HTTP) ═══


def test_partial_scoring_is_rejected(client, seeded):
    """@covers ق-٦٦"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    activity_id, attendance_id, _quality_id = _create_activity(client)

    r = _assess(
        client, seeded["team_id"], activity_id, "2026-08-20",
        [{"criterion_id": attendance_id, "score_pct": "100"}],
    )
    assert r.status_code == 422
    assert db.session.scalars(select(PointEvent).where(PointEvent.kind == "fuel")).all() == []


# ═══ ق-٦٨ — حدث الدفتر صحيح ومحسوب بالضبط ═══


def test_assessment_creates_a_correct_ledger_event(client, seeded):
    """@covers ق-٦٨ — ١٠٠×٤٠٪ + ٩٠×٦٠٪ = ٩٤٪ من ٥٠ لترًا = ٤٧.٠٠."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    activity_id, attendance_id, quality_id = _create_activity(client)

    r = _assess(
        client, seeded["team_id"], activity_id, "2026-08-20",
        [
            {"criterion_id": attendance_id, "score_pct": "100"},
            {"criterion_id": quality_id, "score_pct": "90"},
        ],
    )
    assert r.status_code == 201
    assert r.json["total_pct"] == "94.00"
    assert r.json["litres"] == "47.00"

    event = db.session.scalar(select(PointEvent).where(PointEvent.kind == "fuel"))
    assert event.scope == "team"
    assert event.currency == "fuel"
    assert event.team_id == seeded["team_id"]
    assert event.user_id is None
    assert event.delta == Decimal("47.00")


# ═══ ق-٦٩ — occurred_at من تاريخ الوقوع لا الإدخال ═══


def test_occurred_at_uses_occurred_on_not_submission_time(client, seeded):
    """@covers ق-٦٩"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    activity_id, attendance_id, quality_id = _create_activity(client)

    before_submission = datetime.now(UTC)
    _assess(
        client, seeded["team_id"], activity_id, "2026-01-01",
        [
            {"criterion_id": attendance_id, "score_pct": "100"},
            {"criterion_id": quality_id, "score_pct": "100"},
        ],
    )
    event = db.session.scalar(select(PointEvent).where(PointEvent.kind == "fuel"))
    org = db.session.get(Org, seeded["org_id"])
    expected = datetime.combine(
        date(2026, 1, 1), time.min, tzinfo=ZoneInfo(org.timezone)
    ).astimezone(UTC)
    assert event.occurred_at == expected
    assert event.occurred_at < before_submission


# ═══ ق-٧٠ — تكرار في نفس اليوم ═══


def test_duplicate_assessment_same_day_is_rejected(client, seeded):
    """@covers ق-٧٠"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    activity_id, attendance_id, quality_id = _create_activity(client)
    scores = [
        {"criterion_id": attendance_id, "score_pct": "100"},
        {"criterion_id": quality_id, "score_pct": "100"},
    ]
    assert _assess(client, seeded["team_id"], activity_id, "2026-08-20", scores).status_code == 201
    r = _assess(client, seeded["team_id"], activity_id, "2026-08-20", scores)
    assert r.status_code == 409


def test_same_activity_different_day_is_accepted(client, seeded):
    """@covers ق-٧٠ — الحدّ الآخر."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    activity_id, attendance_id, quality_id = _create_activity(client)
    scores = [
        {"criterion_id": attendance_id, "score_pct": "100"},
        {"criterion_id": quality_id, "score_pct": "100"},
    ]
    _assess(client, seeded["team_id"], activity_id, "2026-08-20", scores)
    r = _assess(client, seeded["team_id"], activity_id, "2026-08-21", scores)
    assert r.status_code == 201


# ═══ ق-٧١ — الدرجات محفوظة مفصّلة ═══


def test_scores_are_saved_in_detail(client, seeded):
    """@covers ق-٧١"""
    from app.models import FuelScore

    _make_admin(seeded["users"]["1001"])
    _login(client)
    activity_id, attendance_id, quality_id = _create_activity(client)
    _assess(
        client, seeded["team_id"], activity_id, "2026-08-20",
        [
            {"criterion_id": attendance_id, "score_pct": "100"},
            {"criterion_id": quality_id, "score_pct": "90"},
        ],
    )
    scores = {s.criterion_id: s.score_pct for s in db.session.scalars(select(FuelScore))}
    assert scores[attendance_id] == Decimal("100.00")
    assert scores[quality_id] == Decimal("90.00")


# ═══ ق-٧٤ — سطر التدقيق ═══


def test_assessment_is_audited(client, seeded):
    """@covers ق-٧٤"""
    admin = seeded["users"]["1001"]
    _make_admin(admin)
    _login(client)
    activity_id, attendance_id, quality_id = _create_activity(client)
    _assess(
        client, seeded["team_id"], activity_id, "2026-08-20",
        [
            {"criterion_id": attendance_id, "score_pct": "100"},
            {"criterion_id": quality_id, "score_pct": "100"},
        ],
    )
    entry = db.session.scalar(select(AuditEntry))
    assert entry.kind == "fuel_assessment"
    assert entry.actor_id == admin


# ═══ ق-٧٥ — المسار السالب ═══


def test_no_cookie_is_401_on_fuel_routes(client, seeded):
    """@covers ق-٧٥"""
    assert client.get("/api/admin/fuel/activities", headers=ORIGIN).status_code == 401
    assert client.post("/api/admin/fuel/activities", json={}, headers=ORIGIN).status_code == 401
    assert client.post("/api/admin/fuel/assess", json={}, headers=ORIGIN).status_code == 401


def test_pilot_is_403_on_fuel_routes(client, seeded):
    """@covers ق-٧٥"""
    _login(client)
    assert client.get("/api/admin/fuel/activities", headers=ORIGIN).status_code == 403
    assert client.post("/api/admin/fuel/activities", json={}, headers=ORIGIN).status_code == 403
    assert client.post("/api/admin/fuel/assess", json={}, headers=ORIGIN).status_code == 403
