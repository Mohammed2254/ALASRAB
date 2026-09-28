"""
الحضور اليدويّ — و-٩هـ · FR-041/FR-042 (احتياطي، أولوية COULD).

**لا جدول جديد** — كل الإثبات على قيد `uq_event_external_ref` القائم في
`point_events` منذ الأساس، مُعاد استعماله لا مُكرَّرًا (`docs/slices/و-٩.md`).
`seeded` (`conftest.py`) **بلا وزن حضور مُعرَّف افتراضًا** — يُضاف هنا صراحةً
عند الحاجة، وغيابه عمدًا هو أساس إثبات ق-١٣٦.
"""

import io
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import Membership, Org, PointEvent, Weight
from app.services import entry, ledger, week

ORIGIN = {"Origin": "http://localhost:5173"}
ATTENDANCE = "/api/admin/attendance"
UNDO = "/api/admin/attendance/undo"


def _login(client, student_no="1001"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": "1234"}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _add_attendance_weight(seeded, hours="3.00"):
    db.session.add(
        Weight(
            version_id=seeded["versions"]["new"],
            activity_type="attendance",
            hours_per_unit=Decimal(hours),
        )
    )
    db.session.commit()


# ═══ ق-١٢٥ · ق-١٢٦ — GET /admin/attendance ═══


def test_get_attendance_returns_full_roster(client, seeded):
    """@covers ق-١٢٥ — كل الأعضاء النشطين، لا جزءًا منهم."""
    _add_attendance_weight(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)
    body = client.get(ATTENDANCE).json
    ids = {p["user_id"] for p in body["pilots"]}
    assert ids == {seeded["users"]["1001"], seeded["users"]["1002"]}


def test_week_status_before_recording(client, seeded):
    """@covers ق-١٢٦ — حالة مصمَّمة قبل أوّل تسجيل."""
    _add_attendance_weight(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)
    body = client.get(ATTENDANCE).json
    assert body["already_recorded"] is False
    assert body["undo_until"] is None
    assert body["absent_user_ids"] == []


# ═══ ق-١٢٧ · ق-١٢٨ — منح الساعات ═══


def test_recording_grants_hours_to_present_only(client, seeded):
    """@covers ق-١٢٧ — الغائب المذكور لا يُمنح، الباقي يُمنح."""
    _add_attendance_weight(seeded, hours="3.00")
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post(
        ATTENDANCE, json={"absent_user_ids": [seeded["users"]["1002"]]}, headers=ORIGIN
    )
    assert r.status_code == 201
    assert r.json["present"] == 1
    assert r.json["absent"] == 1
    assert r.json["hours_each"] == "3.00"

    events = db.session.scalars(select(PointEvent).where(PointEvent.kind == "attendance")).all()
    assert len(events) == 1
    assert events[0].user_id == seeded["users"]["1001"]
    assert events[0].delta == Decimal("3.00")


def test_hours_come_from_configured_weight_not_hardcoded(client, seeded):
    """@covers ق-١٢٨ — قيمة غير معتادة تكشف أي رقم مكتوب في الكود (ف-٦)."""
    _add_attendance_weight(seeded, hours="5.25")
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post(ATTENDANCE, json={"absent_user_ids": []}, headers=ORIGIN)
    assert r.json["hours_each"] == "5.25"


# ═══ ق-١٢٩ — idempotency بالقيد القائم ═══


def test_second_submission_same_week_is_409(client, seeded):
    """@covers ق-١٢٩"""
    _add_attendance_weight(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)
    client.post(ATTENDANCE, json={"absent_user_ids": []}, headers=ORIGIN)
    r = client.post(ATTENDANCE, json={"absent_user_ids": []}, headers=ORIGIN)
    assert r.status_code == 409


# ═══ ق-١٣٠ — ذرّية الدفعة ═══


def test_record_is_all_or_nothing_on_partial_conflict(client, seeded):
    """
    @covers ق-١٣٠ — طالبٌ واحد مسجَّل سلفًا لهذا الأسبوع (تعارض جزئيّ) يُسقط
    الدفعة **كاملةً**، فلا يُمنح حتى من لا تعارض في صفّه.
    """
    _add_attendance_weight(seeded)
    org = db.session.get(Org, seeded["org_id"])
    now = datetime.now(UTC)
    week_start = week.week_start_local(org, now)
    ledger.append(
        [
            ledger.EventSpec(
                org_id=org.id,
                kind="attendance",
                delta=Decimal("3.00"),
                user_id=seeded["users"]["1002"],
                occurred_at=now,
                external_ref=entry._ref(week_start, seeded["users"]["1002"]),
            )
        ]
    )

    with pytest.raises(entry.AttendanceError):
        entry.record(org, seeded["users"]["1001"], [], now=now)

    events_1001 = db.session.scalars(
        select(PointEvent).where(PointEvent.user_id == seeded["users"]["1001"])
    ).all()
    assert events_1001 == []


# ═══ ق-١٣١..١٣٤ — التراجع ═══


def test_undo_within_window_reverses_all_events(client, seeded):
    """@covers ق-١٣١"""
    _add_attendance_weight(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)
    client.post(ATTENDANCE, json={"absent_user_ids": []}, headers=ORIGIN)
    r = client.post(UNDO, headers=ORIGIN)
    assert r.status_code == 200
    assert r.json["reversed"] == 2

    total = db.session.scalar(
        select(func.coalesce(func.sum(PointEvent.delta), 0)).where(
            PointEvent.kind.in_(("attendance", "correction"))
        )
    )
    assert total == Decimal("0.00")


def test_undo_after_window_is_409(client, seeded):
    """
    @covers ق-١٣٢, ق-٢١٠

    **زمنٌ مثبَّت ظهرَ الغد بتوقيت المنظمة، لا `datetime.now(UTC)` عاريًا.**

    كان هذا الاختبار هشًّا زمنيًّا (`HANDOFF.md` §١٢): يسقط بـ`404` بدل `409`
    في نافذة دقائق حول عبور منتصف ليل `week_starts_on` — لأن `record` يحسب
    أسبوعه من `now` و`undo` من `now + 6min`، فإن عبر العبورُ بينهما صار
    الأسبوعان مختلفَين ولم يجد `undo` أحداثًا فأعطى «لا حضور مسجَّل».

    والظهرُ يحلّها من الجهتين معًا: بعيدٌ عن منتصف الليل بـ١٢ ساعة فإضافة ستّ
    دقائق لا تعبر حدّ الأسبوع، **والغدُ** يجعل الفارق عن `created_at` الحقيقيّ
    (زمن الإدراج، وهو ما يقيسه `undo` فعلًا لا `occurred_at`) أكبر من المهلة
    بيقين. وتثبيتُه في الماضي كان سيجعل الفارق **سالبًا** فلا يقع ٤٠٩ أصلًا.
    """
    _add_attendance_weight(seeded)
    org = db.session.get(Org, seeded["org_id"])
    tz = ZoneInfo(org.timezone)
    noon_tomorrow = datetime.combine(
        datetime.now(tz).date() + timedelta(days=1), time(12, 0), tzinfo=tz
    ).astimezone(UTC)
    entry.record(org, seeded["users"]["1001"], [], now=noon_tomorrow)

    with pytest.raises(entry.AttendanceError) as exc_info:
        entry.undo(org, seeded["users"]["1001"], now=noon_tomorrow + timedelta(minutes=6))
    assert exc_info.value.status == 409


def test_undo_without_any_recording_is_404(client, seeded):
    """@covers ق-١٣٣"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post(UNDO, headers=ORIGIN)
    assert r.status_code == 404


def test_double_undo_is_rejected(client, seeded):
    """@covers ق-١٣٤ — التصحيح نفسه محميّ بـ`external_ref` حتميّ خاصّ به."""
    _add_attendance_weight(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)
    client.post(ATTENDANCE, json={"absent_user_ids": []}, headers=ORIGIN)
    assert client.post(UNDO, headers=ORIGIN).status_code == 200
    assert client.post(UNDO, headers=ORIGIN).status_code == 409


# ═══ ق-١٣٥ — تخويل ═══


def test_attendance_routes_require_admin(client, seeded):
    """@covers ق-١٣٥"""
    body = {"absent_user_ids": []}
    assert client.get(ATTENDANCE).status_code == 401
    assert client.post(ATTENDANCE, json=body, headers=ORIGIN).status_code == 401
    assert client.post(UNDO, headers=ORIGIN).status_code == 401

    _login(client)
    assert client.get(ATTENDANCE).status_code == 403
    assert client.post(ATTENDANCE, json=body, headers=ORIGIN).status_code == 403
    assert client.post(UNDO, headers=ORIGIN).status_code == 403


# ═══ ق-١٣٦ — الحضور نشاط في جدول الأوزان (ف-٦) ═══


def test_missing_attendance_weight_is_422(client, seeded):
    """@covers ق-١٣٦ — لا وزن حضور مُعرَّف لهذه المنظمة؛ `seeded` بلا وزنه عمدًا."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post(ATTENDANCE, json={"absent_user_ids": []}, headers=ORIGIN)
    assert r.status_code == 422


# ═══ ق-٢٥٢ — الحضور للعرض من راصد (و-٢٠) ═══


def test_rasd_attendance_view_is_empty_before_any_import(client, seeded):
    """@covers ق-٢٥٢ — حالةٌ مصمَّمة لا عطل."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.get("/api/admin/attendance/rasd", headers=ORIGIN)
    assert r.status_code == 200
    assert r.json["imported_at"] is None
    assert r.json["rows"] == []


def test_rasd_attendance_view_reads_the_latest_import(client, seeded):
    """
    @covers ق-٢٥٢

    البيانات مستورَدة منذ و-٥؛ الناقص كان قراءتها. والحضور **عددٌ** لا
    حاضر/غائب — هكذا يصل من راصد فعلًا.
    """
    from pathlib import Path

    _make_admin(seeded["users"]["1001"])
    _login(client)
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "تقرير_الإنجاز_جميع_الحلقات_١٤٤٨-٠٣-٢٥.csv"
    )
    client.post(
        "/api/admin/paste/commit",
        data={
            "file": (io.BytesIO(fixture.read_bytes()), "rasd.csv"),
            "occurred_on": "2026-08-02",
        },
        content_type="multipart/form-data",
        headers=ORIGIN,
    )

    r = client.get("/api/admin/attendance/rasd", headers=ORIGIN)
    assert r.status_code == 200
    assert r.json["imported_at"] is not None
    assert len(r.json["rows"]) == 24, "صفوف الطلّاب وحدها — بلا صفّي التذييل"

    row = next(x for x in r.json["rows"] if x["name"] == "سلمان الغفيص")
    assert row["attendance"] == "2"
    assert row["tasmi3_days"] == "2"


def test_rasd_attendance_view_requires_admin(client, seeded):
    """@covers ق-٢٥٢"""
    _login(client)
    assert client.get("/api/admin/attendance/rasd", headers=ORIGIN).status_code == 403
