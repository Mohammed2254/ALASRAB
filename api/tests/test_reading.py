"""
طلبات القراءة — و-٤ · FR-020..024.

المسار الكامل: طلب معلَّق ← اعتماد المشرف ← حدث في السجلّ ← ساعات في البطاقة.
بلا محاكاة: تطبيق Flask حقيقي وقاعدة حقيقية.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models import Membership, PointEvent, ReadingSubmission, Team, User
from app.services import reading
from app.services.auth import hash_pin

ORIGIN = {"Origin": "http://localhost:5173"}
PIN = "1234"
MINE = "/api/me/readings"
QUEUE = "/api/admin/readings"
APPROVE = "/api/admin/readings/approve"


def _login(client, student_no="1001"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": PIN}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _submit(client, read_on="2026-08-20", pages=40, book="كتاب"):
    return client.post(
        MINE, json={"read_on": read_on, "pages": pages, "book_title": book}, headers=ORIGIN
    )


def _balance(user_id):
    return db.session.scalar(
        select(db.func.coalesce(db.func.sum(PointEvent.delta), 0)).where(
            PointEvent.user_id == user_id
        )
    )


def _yesterday():
    return (datetime.now(UTC) - timedelta(days=1)).date().isoformat()


# ═══ ق-١٧ — الطلب لا يمنح ساعات ═══


def test_submission_creates_pending_and_leaves_balance_untouched(client, seeded):
    """@covers ق-١٧"""
    uid = seeded["users"]["1001"]
    _login(client)
    before = _balance(uid)

    r = _submit(client, read_on=_yesterday())
    assert r.status_code == 201
    assert r.json["status"] == "pending"

    # ث-٥ من زاوية السلوك: معلَّق ⇒ لا حدث ⇒ لا ساعات.
    assert _balance(uid) == before
    assert db.session.scalar(select(ReadingSubmission.point_event_id)) is None


def test_submission_response_carries_no_hours(client, seeded):
    """@covers ق-١٧ — الردّ لا يوحي بأن شيئًا مُنح."""
    _login(client)
    body = _submit(client, read_on=_yesterday()).json
    assert set(body) == {"id", "status"}


# ═══ ق-١٨ — لا إرسال مزدوج ═══


def test_same_day_same_book_is_rejected(client, seeded):
    """@covers ق-١٨"""
    _login(client)
    day = _yesterday()
    assert _submit(client, read_on=day, book="الرحيق").status_code == 201
    assert _submit(client, read_on=day, book="الرحيق").status_code == 409


def test_same_day_different_book_is_allowed(client, seeded):
    """@covers ق-١٨ — القيد ليس مفرطًا: كتابان في يوم أمرٌ طبيعي."""
    _login(client)
    day = _yesterday()
    assert _submit(client, read_on=day, book="الرحيق").status_code == 201
    assert _submit(client, read_on=day, book="زاد المعاد").status_code == 201


def test_future_date_is_rejected_in_org_timezone(client, seeded):
    """
    @covers ق-١٨ — التاريخ المستقبلي يُقاس **بتوقيت المنظمة** (`RULES.md` §٩).
    """
    _login(client)
    tomorrow = (datetime.now(UTC) + timedelta(days=2)).date().isoformat()
    assert _submit(client, read_on=tomorrow).status_code == 422


# ═══ ق-٢١ — الحدث بتاريخ القراءة ═══


def test_approval_dates_event_by_read_on_not_review_time(client, seeded, app):
    """
    @covers ق-٢١

    قراءةٌ قبل سبعة أيام تُعتمد اليوم: الحدث يحمل **تاريخ القراءة**. لو حمل وقت
    الاعتماد لانتقل إنجاز الطالب إلى أسبوع لم يصنعه — ولظهر في الصدارة الخطأ.
    """
    from zoneinfo import ZoneInfo

    from app.models import Org

    uid = seeded["users"]["1001"]
    read_on = (datetime.now(UTC) - timedelta(days=7)).date()
    _login(client)
    sid = _submit(client, read_on=read_on.isoformat(), pages=40).json["id"]

    _make_admin(uid)
    client.post(APPROVE, json={"ids": [sid]}, headers=ORIGIN)

    event = db.session.scalar(select(PointEvent).where(PointEvent.kind == "reading"))
    org = db.session.get(Org, seeded["org_id"])
    expected = datetime.combine(
        read_on, datetime.min.time(), tzinfo=ZoneInfo(org.timezone)
    ).astimezone(UTC)

    assert event.occurred_at == expected
    assert event.occurred_at.date() != datetime.now(UTC).date()


def test_approval_creates_hours_from_the_engine(client, seeded):
    """
    @covers ق-٢١ — الساعات مشتقّة لا مكتوبة: ٤٠ صفحة × وزن `reading` من الإصدار
    الساري وقت القراءة.
    """
    uid = seeded["users"]["1001"]
    _login(client)
    sid = _submit(client, read_on=_yesterday(), pages=40).json["id"]
    _make_admin(uid)
    r = client.post(APPROVE, json={"ids": [sid]}, headers=ORIGIN)

    assert r.json["results"][0]["hours"] == "6.00"  # ٤٠ × ٠.١٥
    assert _balance(uid) == Decimal("6.00")


# ═══ ق-٢٢ — الطابور على مستوى الجمعية ═══


def test_admin_sees_and_approves_student_from_another_team(client, seeded):
    """
    @covers ق-٢٢

    مشرفٌ في سربٍ يعتمد طالبًا في سربٍ آخر. لو قُيّد بالسرب لتعطّل §٧.٣، ولاحتاج
    كل سرب مشرفًا — وهو ما لا تحتمله جمعية بمتطوّعين.
    """
    from app.models import Org

    other = Team(org_id=seeded["org_id"], name="سرب آخر", code="OTH")
    db.session.add(other)
    db.session.flush()
    outsider = User(
        org_id=seeded["org_id"], full_name="طالب بعيد", student_no="2001", pin_hash=hash_pin(PIN)
    )
    db.session.add(outsider)
    db.session.flush()
    db.session.add(
        Membership(org_id=seeded["org_id"], user_id=outsider.id, team_id=other.id, role="pilot")
    )
    db.session.commit()

    _login(client, student_no="2001")
    sid = _submit(client, read_on=_yesterday()).json["id"]
    client.post("/api/auth/logout", headers=ORIGIN)

    _make_admin(seeded["users"]["1001"])
    _login(client)
    queue = client.get(QUEUE).json["submissions"]
    assert [q["id"] for q in queue] == [sid]
    assert queue[0]["student_name"] == "طالب بعيد"

    assert client.post(APPROVE, json={"ids": [sid]}, headers=ORIGIN).status_code == 200
    assert _balance(outsider.id) == Decimal("6.00")
    assert db.session.get(Org, seeded["org_id"]) is not None


def test_queue_is_oldest_first(client, seeded):
    """@covers ق-٢٢ — من انتظر أطول يُبتّ فيه أوّلًا (م-٢)."""
    _login(client)
    ids = [_submit(client, read_on=_yesterday(), book=f"كتاب {i}").json["id"] for i in range(3)]
    _make_admin(seeded["users"]["1001"])
    assert [q["id"] for q in client.get(QUEUE).json["submissions"]] == ids


def test_pilot_cannot_open_the_queue(client, seeded):
    """@covers ق-٢٢ — الفشل مُغلق."""
    _login(client)
    assert client.get(QUEUE).status_code == 403


# ═══ ق-٢٣ — الطالب يرى حالته وسببها فقط ═══


def test_student_sees_rejection_reason(client, seeded):
    """@covers ق-٢٣ — رفضٌ صامت يقتل الثقة أسرع من غياب الميزة."""
    _login(client)
    sid = _submit(client, read_on=_yesterday()).json["id"]
    _make_admin(seeded["users"]["1001"])
    client.post(
        f"/api/admin/readings/{sid}/reject",
        json={"reason": "الكتاب خارج القائمة المعتمدة"},
        headers=ORIGIN,
    )

    mine = client.get(MINE).json["readings"]
    assert mine[0]["status"] == "rejected"
    assert mine[0]["review_reason"] == "الكتاب خارج القائمة المعتمدة"
    assert mine[0]["hours"] is None


def test_rejection_without_reason_is_refused(client, seeded):
    """@covers ق-٢٣ · ث-٦ من زاوية الـAPI."""
    _login(client)
    sid = _submit(client, read_on=_yesterday()).json["id"]
    _make_admin(seeded["users"]["1001"])
    r = client.post(f"/api/admin/readings/{sid}/reject", json={"reason": ""}, headers=ORIGIN)
    assert r.status_code == 422


def test_student_never_sees_another_students_readings(client, seeded):
    """
    @covers ق-٢٣

    لا معرّف في المسار ولا في الاستعلام — الهوية من الجلسة، **فلا يوجد ما
    يُتلاعب به أصلًا**.
    """
    _login(client, student_no="1002")
    _submit(client, read_on=_yesterday(), book="كتاب الثاني")
    client.post("/api/auth/logout", headers=ORIGIN)

    _login(client)
    assert client.get(MINE).json["readings"] == []
    assert client.get(f"{MINE}?user_id={seeded['users']['1002']}").json["readings"] == []


def test_pending_reading_has_null_hours(client, seeded):
    """@covers ق-٢٣ — ث-٥ من زاوية العقد."""
    _login(client)
    _submit(client, read_on=_yesterday())
    assert client.get(MINE).json["readings"][0]["hours"] is None


# ═══ ق-٢٤ — الاعتماد الجماعي ذرّي ═══


def test_bulk_approval_is_atomic_on_failure(client, seeded):
    """
    @covers ق-٢٤

    دفعةٌ فيها معرّف غير صالح ⇒ **لا شيء يُلحق**. الدفعة النصفية تترك المشرف لا
    يعرف أين توقّفت، فيعيد الاعتماد كلّه — وتتضاعف الساعات.
    """
    uid = seeded["users"]["1001"]
    _login(client)
    good = [_submit(client, read_on=_yesterday(), book=f"ك{i}").json["id"] for i in range(2)]
    _make_admin(uid)

    r = client.post(APPROVE, json={"ids": [*good, 9999]}, headers=ORIGIN)
    assert r.status_code == 409
    assert _balance(uid) == 0
    assert (
        db.session.scalar(select(db.func.count(PointEvent.id)).where(PointEvent.kind == "reading"))
        == 0
    )
    statuses = db.session.scalars(select(ReadingSubmission.status)).all()
    assert statuses == ["pending", "pending"]


def test_bulk_approval_succeeds_together(client, seeded):
    """@covers ق-٢٤ — الحدّ الآخر: الدفعة الصحيحة تمرّ كاملة."""
    uid = seeded["users"]["1001"]
    _login(client)
    ids = [
        _submit(client, read_on=_yesterday(), pages=20, book=f"ك{i}").json["id"] for i in range(3)
    ]
    _make_admin(uid)

    assert client.post(APPROVE, json={"ids": ids}, headers=ORIGIN).status_code == 200
    assert _balance(uid) == Decimal("9.00")  # ٣ × ٢٠ × ٠.١٥
    assert db.session.scalars(select(ReadingSubmission.status)).all() == ["approved"] * 3


def test_already_reviewed_cannot_be_approved_twice(client, seeded):
    """@covers ق-٢٤ — نقرة مزدوجة على «اعتماد» لا تضاعف الساعات."""
    uid = seeded["users"]["1001"]
    _login(client)
    sid = _submit(client, read_on=_yesterday()).json["id"]
    _make_admin(uid)
    client.post(APPROVE, json={"ids": [sid]}, headers=ORIGIN)

    assert client.post(APPROVE, json={"ids": [sid]}, headers=ORIGIN).status_code == 409
    assert _balance(uid) == Decimal("6.00")


# ═══ التكامل مع و-١ ═══


def test_approved_reading_lifts_the_plane(client, seeded):
    """
    القراءة تدخل حساب «أرضي» تلقائيًّا: `readiness.ACTIVITY_KINDS` يعرف
    `reading` منذ و-١، فأوّل اعتماد يُعيد الطائرة إلى الجوّ بلا كود جديد.
    """
    from app.services import ledger

    uid = seeded["users"]["1001"]

    # نشاط قديم ⇒ أرضي
    ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind="quran",
                delta=Decimal("10"),
                user_id=uid,
                occurred_at=datetime.now(UTC) - timedelta(days=30),
            )
        ]
    )
    _login(client)
    assert client.get("/api/me/deck").json["flight"]["grounded"] is True

    sid = _submit(client, read_on=_yesterday()).json["id"]
    _make_admin(uid)
    client.post(APPROVE, json={"ids": [sid]}, headers=ORIGIN)

    assert client.get("/api/me/deck").json["flight"]["grounded"] is False


def test_unauthenticated_access_is_refused(client, seeded):
    assert client.get(MINE).status_code == 401
    assert (
        client.post(
            MINE, json={"read_on": str(date.today()), "pages": 1, "book_title": "x"}, headers=ORIGIN
        ).status_code
        == 401
    )
    assert client.get(QUEUE).status_code == 401


# ═══ و-٢١ — حدّ الإرسال اليوميّ (ق-٢٧٨) ═══


def test_daily_submission_quota_is_enforced(client, seeded):
    """
    `API.md §١` يوثّق «٢٠/يوم» منذ و-٤، و**لم يكن منفَّذًا** حتى و-٢١ — وحدٌّ
    في وثيقةٍ لا يحدّ شيئًا.

    و`uq_reading_per_day` لا يكفي: يمنع تكرار **نفس العنوان** في نفس اليوم،
    فمئةُ عنوانٍ مختلف تُغرق طابور المشرف بلا أن تلمس القيد — فيتأخّر الاعتماد
    على الجميع (خ-١).

    @covers ق-٢٧٨
    """
    _login(client)
    for index in range(reading.MAX_SUBMISSIONS_PER_DAY):
        r = client.post(
            "/api/me/readings",
            json={"read_on": "2026-08-01", "pages": 3, "book_title": f"كتاب {index}"},
            headers=ORIGIN,
        )
        assert r.status_code == 201, (index, r.get_json())

    blocked = client.post(
        "/api/me/readings",
        json={"read_on": "2026-08-01", "pages": 3, "book_title": "الحادي والعشرون"},
        headers=ORIGIN,
    )
    assert blocked.status_code == 429
    assert "غدًا" in blocked.get_json()["message"]


def test_quota_counts_the_sending_day_not_the_reading_day(client, seeded):
    """
    التسجيل بأثرٍ رجعيّ مشروع، فالعدّ على **يوم الإرسال**: عشرون طلبًا موزّعةً
    على عشرين تاريخَ قراءةٍ ماضٍ تبلغ الحدّ كما تبلغه عشرون على تاريخٍ واحد.

    @covers ق-٢٧٨
    """
    _login(client)
    for index in range(reading.MAX_SUBMISSIONS_PER_DAY):
        day = date(2026, 8, 1) + timedelta(days=index)
        r = client.post(
            "/api/me/readings",
            json={"read_on": day.isoformat(), "pages": 2, "book_title": "كتاب"},
            headers=ORIGIN,
        )
        assert r.status_code == 201, (index, r.get_json())

    blocked = client.post(
        "/api/me/readings",
        json={"read_on": "2026-09-01", "pages": 2, "book_title": "كتاب"},
        headers=ORIGIN,
    )
    assert blocked.status_code == 429


def test_quota_is_per_student_not_per_org(client, seeded):
    """
    حدٌّ على مستوى الجمعية يجعل طالبًا واحدًا يُسكت البقيّة — وهو ما نمنعه
    هنا: الحدّ صفةُ مُرسِلٍ لا صفةُ قناة.

    @covers ق-٢٧٨
    """
    _login(client)
    for index in range(reading.MAX_SUBMISSIONS_PER_DAY):
        client.post(
            "/api/me/readings",
            json={"read_on": "2026-08-01", "pages": 3, "book_title": f"كتاب {index}"},
            headers=ORIGIN,
        )
    client.post("/api/auth/logout", headers=ORIGIN)

    _login(client, "1002")
    r = client.post(
        "/api/me/readings",
        json={"read_on": "2026-08-01", "pages": 3, "book_title": "كتاب الثاني"},
        headers=ORIGIN,
    )
    assert r.status_code == 201, r.get_json()
