"""
العتبات ومعاينة أثرها — و-٧ · FR-082 · ت-٢ (الرتبة لا تنخفض).

السُّلّم المبذور: طيار٠ · طيار أول٤٠٠ · رائد سرب٩٠٠ · قائد١٥٠٠ (`conftest.py`).
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models import AuditEntry, Membership, RankThreshold
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


def _award(org_id, user_id, hours):
    ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id, kind="quran", delta=Decimal(hours), user_id=user_id, occurred_at=NOW
            )
        ]
    )


ORIGINAL_LADDER = [
    {"key": "trainee", "name": "طيار", "tier": 1, "at_hours": "0"},
    {"key": "pilot1", "name": "طيار أول", "tier": 2, "at_hours": "400"},
    {"key": "squadron", "name": "رائد سرب", "tier": 3, "at_hours": "900"},
    {"key": "commander", "name": "قائد", "tier": 4, "at_hours": "1500"},
]


def _submit(client, thresholds, path="/api/admin/thresholds"):
    return client.post(path, json={"thresholds": thresholds}, headers=ORIGIN)


# ═══ ق-٥٠ · ت-٢ — الرتبة لا تنخفض ═══


def test_preview_shows_no_demotion_when_raising_a_threshold_above_a_reached_rank(client, seeded):
    """
    @covers ق-٥٠

    ١٠٠٢ يبلغ «طيار أول» (٤٠٠) بالضبط. رفع عتبتها إلى ٥٠٠ يجعل رتبتها الحيّة
    تحت السُّلّم الجديد «طيار» — والمعاينة يجب ألّا تُظهر هذا كتراجع.
    """
    _award(seeded["org_id"], seeded["users"]["1002"], "400.00")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    raised = [dict(r) for r in ORIGINAL_LADDER]
    raised[1] = {**raised[1], "at_hours": "500"}
    body = _submit(client, raised, path="/api/admin/thresholds/preview").json

    assert body["demoted"] == []


def test_saved_threshold_change_still_shows_prior_rank_on_the_deck(client, seeded):
    """
    @covers ق-٥٢

    الإثبات الحاسم: ليس نصًّا في وثيقة — `GET /me/deck` الفعلي بعد الحفظ.
    """
    _award(seeded["org_id"], seeded["users"]["1002"], "400.00")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    raised = [dict(r) for r in ORIGINAL_LADDER]
    raised[1] = {**raised[1], "at_hours": "500"}
    assert _submit(client, raised).status_code == 200

    client.post("/api/auth/logout", headers=ORIGIN)
    _login(client, "1002")
    deck = client.get("/api/me/deck", headers=ORIGIN).json
    assert deck["rank"] == {"name": "طيار أول", "tier": 2}


def test_promotion_still_works_normally(client, seeded):
    """@covers ق-٥٠ — الحدّ الآخر: خفض عتبة يرفع رتبة طالب فعليًّا (promoted)."""
    _award(seeded["org_id"], seeded["users"]["1002"], "350.00")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    lowered = [dict(r) for r in ORIGINAL_LADDER]
    lowered[1] = {**lowered[1], "at_hours": "300"}
    body = _submit(client, lowered, path="/api/admin/thresholds/preview").json

    assert any(p["user_id"] == seeded["users"]["1002"] for p in body["promoted"])
    assert body["demoted"] == []


# ═══ ق-٥١ · ث-١٣أ — سُلّم متّسق ═══


def test_inconsistent_ladder_is_rejected_by_preview(client, seeded):
    """@covers ق-٥١"""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    broken = [dict(r) for r in ORIGINAL_LADDER]
    broken[2] = {**broken[2], "at_hours": "200"}  # رائد سرب أقلّ من طيار أول
    assert _submit(client, broken, path="/api/admin/thresholds/preview").status_code == 422


def test_inconsistent_ladder_is_rejected_by_save_too(client, seeded):
    """@covers ق-٥١ — لا تكذب المعاينة على المشرف: نفس الفحص في الحفظ."""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    broken = [dict(r) for r in ORIGINAL_LADDER]
    broken[2] = {**broken[2], "at_hours": "200"}
    assert _submit(client, broken).status_code == 422
    # ولم يتغيّر شيء في القاعدة.
    assert (
        db.session.scalar(
            select(RankThreshold.at_hours).where(RankThreshold.key == "squadron")
        )
        == Decimal("900.00")
    )


def test_consistent_ladder_is_accepted(client, seeded):
    """@covers ق-٥١ — الحدّ الآخر."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    assert _submit(client, ORIGINAL_LADDER).status_code == 200


# ═══ ق-٥٣ — لا حذف رتبة ═══


def test_removing_an_existing_key_is_rejected(client, seeded):
    """@covers ق-٥٣"""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    without_squadron = [r for r in ORIGINAL_LADDER if r["key"] != "squadron"]
    assert _submit(client, without_squadron).status_code == 422
    assert (
        db.session.scalar(select(RankThreshold).where(RankThreshold.key == "squadron"))
        is not None
    )


def test_adding_a_new_rank_is_accepted(client, seeded):
    """@covers ق-٥٣ — الحدّ الآخر: الإضافة مسموحة، الحذف وحده ممنوع."""
    with_new = [*ORIGINAL_LADDER, {"key": "ace", "name": "صقر", "tier": 5, "at_hours": "2000"}]
    _make_admin(seeded["users"]["1001"])
    _login(client)
    assert _submit(client, with_new).status_code == 200
    assert db.session.scalar(select(RankThreshold).where(RankThreshold.key == "ace")) is not None


# ═══ ق-٥٤ — سطر التدقيق ═══


def test_threshold_save_is_audited(client, seeded):
    """@covers ق-٥٤"""
    admin = seeded["users"]["1001"]
    _make_admin(admin)
    _login(client)
    _submit(client, ORIGINAL_LADDER)

    entry = db.session.scalar(select(AuditEntry))
    assert entry.kind == "thresholds_update"
    assert entry.actor_id == admin
