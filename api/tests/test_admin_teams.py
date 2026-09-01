"""
الأسراب والعضويات — و-٧ · FR-083.

**أرشفة لا حذف، ونقلٌ لا يزوّر التاريخ** (م-١٠).
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models import AuditEntry, Membership, PointEvent, Team
from app.services import ledger

ORIGIN = {"Origin": "http://localhost:5173"}
NOW = datetime(2026, 8, 1, tzinfo=UTC)


def _login(client, student_no="1001", pin="1234"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": pin}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


# ═══ ق-٥٥ — رمز مكرَّر ═══


def test_duplicate_team_code_in_same_org_is_rejected(client, seeded):
    """@covers ق-٥٥"""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = client.post(
        "/api/admin/teams", json={"name": "سرب آخر", "code": "TST"}, headers=ORIGIN
    )  # "TST" رمز السرب المبذور
    assert r.status_code == 409


def test_unique_code_is_accepted(client, seeded):
    """@covers ق-٥٥ — الحدّ الآخر."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post("/api/admin/teams", json={"name": "سرب الفجر", "code": "FJR"}, headers=ORIGIN)
    assert r.status_code == 201
    assert r.json["code"] == "FJR"


# ═══ ق-٥٦ — أرشفة سرب مأهول ═══


def test_archiving_a_team_with_active_members_is_rejected(client, seeded):
    """@covers ق-٥٦"""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = client.patch(
        f"/api/admin/teams/{seeded['team_id']}", json={"archived": True}, headers=ORIGIN
    )
    assert r.status_code == 422
    assert db.session.get(Team, seeded["team_id"]).archived_at is None


def test_archiving_an_empty_team_succeeds(client, seeded):
    """@covers ق-٥٦ — الحدّ الآخر."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    empty = client.post(
        "/api/admin/teams", json={"name": "سرب فارغ", "code": "EMP"}, headers=ORIGIN
    ).json

    r = client.patch(f"/api/admin/teams/{empty['id']}", json={"archived": True}, headers=ORIGIN)
    assert r.status_code == 200
    assert r.json["archived_at"] is not None


# ═══ ق-٥٧ — النقل لا يزوّر التاريخ ═══


def test_transfer_closes_old_membership_instead_of_deleting_it(client, seeded):
    """@covers ق-٥٧"""
    org_id, uid = seeded["org_id"], seeded["users"]["1002"]
    ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id, kind="quran", delta=Decimal("50"), user_id=uid, occurred_at=NOW
            )
        ]
    )
    old_membership_id = db.session.scalar(
        select(Membership.id).where(Membership.user_id == uid, Membership.left_at.is_(None))
    )

    _make_admin(seeded["users"]["1001"])
    _login(client)
    target = client.post(
        "/api/admin/teams", json={"name": "سرب الفجر", "code": "FJR"}, headers=ORIGIN
    ).json

    r = client.post(
        f"/api/admin/teams/{target['id']}/members", json={"user_id": uid}, headers=ORIGIN
    )
    assert r.status_code == 200

    old = db.session.get(Membership, old_membership_id)
    assert old.left_at is not None  # أُغلقت لا حُذفت

    new = db.session.scalar(
        select(Membership).where(Membership.user_id == uid, Membership.left_at.is_(None))
    )
    assert new.team_id == target["id"]

    # التاريخ لم يتحرّك: نفس الحدث بنفس team_id (NULL — فردي) ونفس occurred_at.
    event = db.session.scalar(select(PointEvent).where(PointEvent.user_id == uid))
    assert event.occurred_at == NOW
    assert event.team_id is None  # حدثٌ فردي أصلًا — النقل لا يعيد كتابته


# ═══ ق-٥٨ — نقل إلى سرب مؤرشَف ═══


def test_transfer_into_an_archived_team_is_rejected(client, seeded):
    """@covers ق-٥٨"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    empty = client.post(
        "/api/admin/teams", json={"name": "سرب مؤرشَف قريبًا", "code": "ARC"}, headers=ORIGIN
    ).json
    client.patch(f"/api/admin/teams/{empty['id']}", json={"archived": True}, headers=ORIGIN)

    r = client.post(
        f"/api/admin/teams/{empty['id']}/members",
        json={"user_id": seeded["users"]["1002"]},
        headers=ORIGIN,
    )
    assert r.status_code == 422


def test_transfer_into_an_active_team_is_accepted(client, seeded):
    """@covers ق-٥٨ — الحدّ الآخر."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    target = client.post(
        "/api/admin/teams", json={"name": "سرب الفجر", "code": "FJR"}, headers=ORIGIN
    ).json
    r = client.post(
        f"/api/admin/teams/{target['id']}/members",
        json={"user_id": seeded["users"]["1002"]},
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert r.json["team_id"] == target["id"]


# ═══ ق-٥٩ — سطر التدقيق لكل فعل ═══


def test_all_three_team_actions_are_audited(client, seeded):
    """@covers ق-٥٩"""
    admin = seeded["users"]["1001"]
    _make_admin(admin)
    _login(client)

    target = client.post(
        "/api/admin/teams", json={"name": "سرب الفجر", "code": "FJR"}, headers=ORIGIN
    ).json
    client.post(
        f"/api/admin/teams/{target['id']}/members",
        json={"user_id": seeded["users"]["1002"]},
        headers=ORIGIN,
    )
    empty = client.post(
        "/api/admin/teams", json={"name": "سرب سيُؤرشَف", "code": "OLD"}, headers=ORIGIN
    ).json
    client.patch(f"/api/admin/teams/{empty['id']}", json={"archived": True}, headers=ORIGIN)

    kinds = {
        e.kind for e in db.session.scalars(select(AuditEntry).where(AuditEntry.actor_id == admin))
    }
    assert kinds == {"team_created", "membership_transferred", "team_archived"}
