"""
التصحيح والتعديل القرآني — و-٦ · FR-035 · FR-036 · FR-037 · FR-080.

**راصد قاعدة، والتعديل اليدوي استثناء** (`ADR-004`): كلا المسارين بسبب
إلزاميّ، وكلاهما يكتب `audit_log` ذرّيًّا مع الحدث نفسه (نمط ث-١٧).
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import AuditEntry, Membership, Org, PointEvent, User
from app.services import ledger
from app.services import quran as quran_service

ORIGIN = {"Origin": "http://localhost:5173"}
PIN = "1234"
REVERSE = "/api/admin/events/{}/reverse"
ENTRY = "/api/admin/quran/entry"
STUDENTS = "/api/admin/quran/students"
EVENTS = "/api/admin/quran/events"
NEW_VERSION_DAY = date(2026, 8, 1)  # داخل سريان إصدار "new" (٢٠٢٦-٠٦-٠١ فصاعدًا)


def _login(client, student_no="1001", pin=PIN):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": pin}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _seed_event(seeded, kind="quran", delta="40", user_key="1001"):
    return ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind=kind,
                delta=Decimal(delta),
                user_id=seeded["users"][user_key],
                occurred_at=datetime(2026, 8, 1, tzinfo=UTC),
            )
        ]
    )[0]


# ═══ ق-١٣٩ — تصحيح صالح ينشئ حدثًا معاكسًا ═══


def test_reverse_creates_opposite_event(client, seeded):
    """@covers ق-١٣٩"""
    admin = seeded["users"]["1001"]
    original = _seed_event(seeded, delta="40")
    _make_admin(admin)
    _login(client)

    r = client.post(
        REVERSE.format(original.id), json={"reason": "خطأ في تصدير راصد"}, headers=ORIGIN
    )
    assert r.status_code == 201
    assert r.json["delta"] == "-40.00"
    assert r.json["kind"] == "correction"


# ═══ ق-١٤٠ — بلا سبب ⇒ ٤٢٢، ولا حدث جديد ═══


def test_reverse_without_reason_is_422(client, seeded):
    """@covers ق-١٤٠"""
    admin = seeded["users"]["1001"]
    original = _seed_event(seeded)
    _make_admin(admin)
    _login(client)

    # مسافات لا فراغ محض: يجتاز `validate.Length(min=1)` في المخطّط فيصل
    # فحص `ledger._reverse_spec` تحديدًا (نفس منطق ق-١٤٦).
    r = client.post(REVERSE.format(original.id), json={"reason": "   "}, headers=ORIGIN)
    assert r.status_code == 422
    assert db.session.scalar(db.select(db.func.count(PointEvent.id))) == 1


# ═══ ق-١٤١ — حدث غير موجود أو من منظمة أخرى ⇒ ٤٠٤ ═══


def test_reverse_unknown_event_is_404(client, seeded):
    """@covers ق-١٤١"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post(REVERSE.format(99999), json={"reason": "سبب"}, headers=ORIGIN)
    assert r.status_code == 404


def test_reverse_event_from_another_org_is_404(client, seeded):
    """@covers ق-١٤١ — نفس منطق `ResetPin`: رسالة واحدة لغير الموجود وللخارج عن المنظمة."""
    other = Org(name="جمعية أخرى")
    db.session.add(other)
    db.session.flush()
    other_user = User(org_id=other.id, full_name="غريب", student_no="9001", pin_hash="x")
    db.session.add(other_user)
    db.session.flush()
    foreign_event = ledger.append(
        [
            ledger.EventSpec(
                org_id=other.id,
                kind="quran",
                delta=Decimal("10"),
                user_id=other_user.id,
                occurred_at=datetime(2026, 8, 1, tzinfo=UTC),
            )
        ]
    )[0]

    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post(REVERSE.format(foreign_event.id), json={"reason": "سبب"}, headers=ORIGIN)
    assert r.status_code == 404


# ═══ ق-١٤٢ — تصحيح حدث تصحيح مسموح (سابقة قائمة منذ و-١) ═══


def test_reversing_a_correction_is_allowed(client, seeded):
    """@covers ق-١٤٢ — لا حارس جديد يمنع تصحيح تصحيح؛ `ledger.reverse_pending` عامّ على أي `kind`."""
    admin = seeded["users"]["1001"]
    original = _seed_event(seeded, delta="40")
    _make_admin(admin)
    _login(client)

    first = client.post(
        REVERSE.format(original.id), json={"reason": "خطأ أوّل"}, headers=ORIGIN
    ).json
    r = client.post(
        REVERSE.format(first["id"]), json={"reason": "تراجعت عن تصحيحي"}, headers=ORIGIN
    )

    assert r.status_code == 201
    assert r.json["delta"] == "40.00"  # عكس التصحيح يعيد المبلغ الأصلي
    assert db.session.scalar(db.select(db.func.sum(PointEvent.delta))) == Decimal("40.00")


# ═══ ق-١٤٣ — سطر تدقيق منسوب للمشرف ومؤرَّخ ═══


def test_reverse_writes_attributed_audit_row(client, seeded):
    """@covers ق-١٤٣"""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    # الحدث الأصل **لطالب غير المشرف الفاعل** عمدًا — وإلا تصادف actor_id
    # وevent.user_id فيتساويان، ولا يميّز الاختبار الحقل الصحيح من الخطأ.
    original = _seed_event(seeded, delta="40", user_key="1002")
    _make_admin(admin)
    _login(client)

    client.post(REVERSE.format(original.id), json={"reason": "خطأ في التصدير"}, headers=ORIGIN)

    entry = db.session.scalar(select(AuditEntry))
    assert entry.kind == "quran_correction"
    assert entry.actor_id == admin
    assert entry.actor_id != target
    assert entry.at is not None


# ═══ ق-١٤٤ — المسار السالب الإلزامي ═══


def test_reverse_without_cookie_is_401(client, seeded):
    """@covers ق-١٤٤"""
    original = _seed_event(seeded)
    assert (
        client.post(REVERSE.format(original.id), json={"reason": "سبب"}, headers=ORIGIN).status_code
        == 401
    )


def test_pilot_cannot_reverse_events(client, seeded):
    """@covers ق-١٤٤"""
    original = _seed_event(seeded)
    _login(client)
    r = client.post(REVERSE.format(original.id), json={"reason": "سبب"}, headers=ORIGIN)
    assert r.status_code == 403
    assert db.session.scalars(select(AuditEntry)).all() == []


# ═══ ق-١٤٥ — إدخال يدويّ صالح: الساعات محسوبة عبر rules/engine ═══


def test_add_entry_computes_hours_via_engine(client, seeded):
    """@covers ق-١٤٥ — ٣ صفحات × ٢.٥ (memorize) × ٢.٠ (mastered) = ١٥.٠٠، لا رقم مُدخَل."""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin)
    _login(client)

    r = client.post(
        ENTRY,
        json={
            "user_id": target,
            "occurred_on": NEW_VERSION_DAY.isoformat(),
            "activity_type": "memorize",
            "quantity": "3",
            "mastery": "mastered",
            "reason": "غاب عن تصدير راصد",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 201
    assert r.json["delta"] == "15.00"
    assert r.json["kind"] == "manual"


# ═══ ق-١٤٦ — بلا سبب ⇒ ٤٢٢، ولا حدث ═══


def test_add_entry_without_reason_is_422(client, seeded):
    """@covers ق-١٤٦"""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin)
    _login(client)

    # سببٌ من مسافات فقط: يجتاز `validate.Length(min=1)` في المخطّط (الطول
    # ٣ > ٠) فيصل فحص الخدمة تحديدًا — لا مخطّطًا سطحيًّا يُسقطه أوّلًا.
    r = client.post(
        ENTRY,
        json={
            "user_id": target,
            "occurred_on": NEW_VERSION_DAY.isoformat(),
            "activity_type": "memorize",
            "quantity": "3",
            "reason": "   ",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 422
    assert db.session.scalars(select(PointEvent)).all() == []


# ═══ ق-١٤٧ — نشاط بلا وزن ساري ⇒ ٤٢٢ لا ٥٠٠ ═══


def test_add_entry_unknown_activity_is_422_not_500(client, seeded):
    """@covers ق-١٤٧"""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin)
    _login(client)

    r = client.post(
        ENTRY,
        json={
            "user_id": target,
            "occurred_on": NEW_VERSION_DAY.isoformat(),
            "activity_type": "نشاط-لا-وزن-له",
            "quantity": "3",
            "reason": "سبب",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 422
    assert db.session.scalars(select(PointEvent)).all() == []


# ═══ ق-١٤٨ — طالب غير موجود أو من منظمة أخرى ⇒ ٤٠٤ ═══


def test_add_entry_unknown_student_is_404(client, seeded):
    """@covers ق-١٤٨"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post(
        ENTRY,
        json={
            "user_id": 99999,
            "occurred_on": NEW_VERSION_DAY.isoformat(),
            "activity_type": "memorize",
            "quantity": "3",
            "reason": "سبب",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 404


def test_add_entry_student_from_another_org_is_404(client, seeded):
    """@covers ق-١٤٨ — الشقّ الآخر: موجودٌ فعلًا لكن في منظمة أخرى."""
    other = Org(name="جمعية أخرى")
    db.session.add(other)
    db.session.flush()
    outsider = User(org_id=other.id, full_name="غريب", student_no="9001", pin_hash="x")
    db.session.add(outsider)
    db.session.commit()

    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post(
        ENTRY,
        json={
            "user_id": outsider.id,
            "occurred_on": NEW_VERSION_DAY.isoformat(),
            "activity_type": "memorize",
            "quantity": "3",
            "reason": "سبب",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 404


# ═══ ق-١٤٩ — تاريخ مستقبليّ يُرفض ═══


def test_add_entry_future_date_is_rejected(client, seeded):
    """@covers ق-١٤٩ — نفس قيد `SubmitReadingSchema.read_on`."""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin)
    _login(client)

    future = date(2099, 1, 1)
    r = client.post(
        ENTRY,
        json={
            "user_id": target,
            "occurred_on": future.isoformat(),
            "activity_type": "memorize",
            "quantity": "3",
            "reason": "سبب",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 422
    assert db.session.scalars(select(PointEvent)).all() == []


# ═══ ق-١٥٠ — الوزن يُختار بـoccurred_on المُدخَل لا اليوم الحالي (ث-١١) ═══


def test_add_entry_uses_weight_effective_at_occurred_on(client, seeded):
    """@covers ق-١٥٠ — تاريخ في إصدار قديم (٢٠٢٠) يستعمل وزنه ١.٠ لا وزن اليوم ٢.٥."""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin)
    _login(client)

    r = client.post(
        ENTRY,
        json={
            "user_id": target,
            "occurred_on": "2021-01-01",
            "activity_type": "memorize",
            "quantity": "3",
            "reason": "سبب",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 201
    assert r.json["delta"] == "3.00"  # ٣ × ١.٠ (وزن ٢٠٢٠) لا ٣ × ٢.٥ (وزن ٢٠٢٦)


# ═══ ق-١٥١ — سطر تدقيق منسوب ومؤرَّخ للإضافة اليدوية ═══


def test_add_entry_writes_attributed_audit_row(client, seeded):
    """@covers ق-١٥١"""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin)
    _login(client)

    client.post(
        ENTRY,
        json={
            "user_id": target,
            "occurred_on": NEW_VERSION_DAY.isoformat(),
            "activity_type": "memorize",
            "quantity": "3",
            "reason": "غاب عن تصدير راصد",
        },
        headers=ORIGIN,
    )
    entry = db.session.scalar(select(AuditEntry))
    assert entry.kind == "quran_correction"
    assert entry.actor_id == admin


# ═══ ق-١٥٢ — المسار السالب الإلزامي ═══


def test_add_entry_without_cookie_is_401(client, seeded):
    """@covers ق-١٥٢"""
    r = client.post(
        ENTRY,
        json={
            "user_id": seeded["users"]["1002"],
            "occurred_on": NEW_VERSION_DAY.isoformat(),
            "activity_type": "memorize",
            "quantity": "3",
            "reason": "سبب",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 401


def test_pilot_cannot_add_entry(client, seeded):
    """@covers ق-١٥٢"""
    _login(client)
    r = client.post(
        ENTRY,
        json={
            "user_id": seeded["users"]["1002"],
            "occurred_on": NEW_VERSION_DAY.isoformat(),
            "activity_type": "memorize",
            "quantity": "3",
            "reason": "سبب",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 403


# ═══ ق-١٥٣ — قائمة الطلاب: نشِطون فقط، على مستوى الجمعية ═══


def test_students_list_excludes_inactive_and_other_orgs(client, seeded):
    """@covers ق-١٥٣"""
    inactive = User(
        org_id=seeded["org_id"],
        full_name="غير نشِط",
        student_no="9002",
        pin_hash="x",
        is_active=False,
    )
    db.session.add(inactive)
    db.session.flush()
    db.session.add(
        Membership(
            org_id=seeded["org_id"], user_id=inactive.id, team_id=seeded["team_id"], role="pilot"
        )
    )
    db.session.commit()

    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.get(STUDENTS, headers=ORIGIN)

    assert r.status_code == 200
    ids = {s["id"] for s in r.json["students"]}
    assert ids == {seeded["users"]["1001"], seeded["users"]["1002"]}


# ═══ ق-١٥٤ — أحداث طالب: نفس ما يراه في بطاقته، وطالب من منظمة أخرى ⇒ ٤٠٤ ═══


def test_events_endpoint_lists_students_events(client, seeded):
    """@covers ق-١٥٤"""
    target = seeded["users"]["1002"]
    _seed_event(seeded, kind="quran", delta="10", user_key="1002")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = client.get(EVENTS, query_string={"user_id": target}, headers=ORIGIN)
    assert r.status_code == 200
    assert len(r.json["events"]) == 1
    assert r.json["events"][0]["delta"] == "10.00"


def test_events_endpoint_unknown_student_is_404(client, seeded):
    """@covers ق-١٥٤"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.get(EVENTS, query_string={"user_id": 99999}, headers=ORIGIN)
    assert r.status_code == 404


# ═══ ق-١٥٥ — ذرّية FR-037: فشل التدقيق لا يترك حدثًا يتيمًا ═══


def test_reverse_audit_failure_leaves_no_orphan_event(seeded, monkeypatch):
    """@covers ق-١٥٥"""
    org = db.session.get(Org, seeded["org_id"])
    original = _seed_event(seeded, delta="40")

    def boom(*_a, **_k):
        raise RuntimeError("محاكاة فشل الكتابة في audit_log")

    monkeypatch.setattr(quran_service.audit, "record", boom)

    with pytest.raises(RuntimeError):
        quran_service.reverse(org, original.id, "سبب", actor_id=seeded["users"]["1001"])
    db.session.rollback()

    assert (
        db.session.scalar(
            db.select(db.func.count(PointEvent.id)).where(PointEvent.kind == "correction")
        )
        == 0
    )


def test_add_entry_audit_failure_leaves_no_orphan_event(seeded, monkeypatch):
    """@covers ق-١٥٥"""
    org = db.session.get(Org, seeded["org_id"])
    target = seeded["users"]["1002"]

    def boom(*_a, **_k):
        raise RuntimeError("محاكاة فشل الكتابة في audit_log")

    monkeypatch.setattr(quran_service.audit, "record", boom)

    with pytest.raises(RuntimeError):
        quran_service.add_entry(
            org, target, NEW_VERSION_DAY, "memorize", Decimal("3"), None, "سبب", actor_id=1
        )
    db.session.rollback()

    assert db.session.scalars(select(PointEvent)).all() == []
