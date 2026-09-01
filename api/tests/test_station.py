"""
محطة التزوّد — و-٨ · FR-072. شاشة طيّار لا مشرف.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models import Membership
from app.services import ledger

ORIGIN = {"Origin": "http://localhost:5173"}
NOW = datetime(2026, 8, 1, tzinfo=UTC)
STATION = "/api/station"


def _login(client, student_no="1001", pin="1234"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": pin}, headers=ORIGIN
    )


# ═══ ق-٧٢ — وقود السرب لا الفرد، تراكميّ ═══


def test_station_shows_team_fuel_total_not_individual(client, seeded):
    """@covers ق-٧٢"""
    org_id, team_id = seeded["org_id"], seeded["team_id"]
    ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id, kind="fuel", delta=Decimal("30"), team_id=team_id, occurred_at=NOW
            )
        ]
    )
    ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id, kind="fuel", delta=Decimal("17"), team_id=team_id, occurred_at=NOW
            )
        ]
    )
    # حدث فردي (ساعات) للطالب نفسه — يجب ألّا يختلط بالوقود إطلاقًا (ث-١).
    ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id,
                kind="quran",
                delta=Decimal("500"),
                user_id=seeded["users"]["1001"],
                occurred_at=NOW,
            )
        ]
    )

    _login(client)
    body = client.get(STATION, headers=ORIGIN).json
    assert body["team"]["litres"] == "47.00"


def test_station_total_is_cumulative_not_windowed(client, seeded):
    """@covers ق-٧٢ — الحدّ الآخر: تراكميّ لا نافذة أسبوع."""
    org_id, team_id = seeded["org_id"], seeded["team_id"]
    old = datetime(2020, 1, 1, tzinfo=UTC)
    ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id, kind="fuel", delta=Decimal("12"), team_id=team_id, occurred_at=old
            )
        ]
    )
    _login(client)
    body = client.get(STATION, headers=ORIGIN).json
    assert body["team"]["litres"] == "12.00"


# ═══ ق-٧٣ — حالة بلا سرب مصمَّمة ═══


def test_station_without_team_is_a_designed_state_not_a_crash(client, seeded):
    """@covers ق-٧٣"""
    _login(client)
    db.session.execute(db.text("DELETE FROM memberships"))
    db.session.commit()

    r = client.get(STATION, headers=ORIGIN)
    assert r.status_code == 200
    assert r.json["team"] is None
    assert r.json["recent"] == []


def test_tank_capacity_is_always_present_even_without_a_team(client, seeded):
    """@covers ق-٧٣ — الحدّ الآخر: السعة المرجعية تصل رغم غياب السرب."""
    from app.models import Org

    org = db.session.get(Org, seeded["org_id"])
    org.tank_capacity_l = Decimal("500.00")
    db.session.commit()

    _login(client)
    db.session.execute(db.text("DELETE FROM memberships"))
    db.session.commit()

    body = client.get(STATION, headers=ORIGIN).json
    assert body["tank_capacity_l"] == "500.00"


# ═══ ق-٧١ (شقّ إضافي) — التفصيل يصل عبر المحطة ═══


def test_recent_assessments_explain_the_number(client, seeded):
    """@covers ق-٧١ — تفصيلٌ يشرح الرقم لا مجموعٌ صامت."""
    from app.models import FuelActivity, FuelAssessment

    org_id, team_id = seeded["org_id"], seeded["team_id"]
    event = ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id, kind="fuel", delta=Decimal("47.00"), team_id=team_id, occurred_at=NOW
            )
        ]
    )[0]
    activity = FuelActivity(org_id=org_id, key="a", name="الحفظ الجماعي", litres_full=Decimal("50"))
    db.session.add(activity)
    db.session.flush()
    db.session.add(
        FuelAssessment(
            org_id=org_id,
            team_id=team_id,
            activity_id=activity.id,
            occurred_on=NOW.date(),
            total_pct=Decimal("94.00"),
            litres=Decimal("47.00"),
            actor_id=seeded["users"]["1001"],
            point_event_id=event.id,
        )
    )
    db.session.commit()

    _login(client)
    body = client.get(STATION, headers=ORIGIN).json
    assert body["recent"][0]["activity_name"] == "الحفظ الجماعي"
    assert body["recent"][0]["total_pct"] == "94.00"


# ═══ ق-٧٥ — بلا كوكي فقط (طيّار مسموح له هنا عمدًا) ═══


def test_no_cookie_is_401(client, seeded):
    """@covers ق-٧٥"""
    assert client.get(STATION, headers=ORIGIN).status_code == 401


def test_pilot_can_see_station_admin_required_does_not_apply(client, seeded):
    """
    @covers ق-٧٥ — الحدّ الآخر المتعمَّد: `/station` شاشة طيّار لا مشرف
    (`docs/slices/و-٨.md`) — طيّار غير مرفَّع يرى محطته بلا `403`.
    """
    assert db.session.scalar(
        select(Membership.role).where(Membership.user_id == seeded["users"]["1001"])
    ) == "pilot"
    _login(client)
    assert client.get(STATION, headers=ORIGIN).status_code == 200
