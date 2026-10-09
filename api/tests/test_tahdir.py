"""
تحضير القراءة — و-١١ · FR-090..093.

نفس مسار و-٤ (طلب معلَّق ← اعتماد ← حدث) ببرنامج مستقلّ (`activity_type`)
وقيود إضافية (يوم الأسبوع، الحدّ الأدنى، تقرير أسبوعي). بلا محاكاة: تطبيق
Flask حقيقي وقاعدة حقيقية.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models import AuditEntry, Membership, Org, PointEvent, ReadingSubmission, Weight
from app.services import reading as reading_service

ORIGIN = {"Origin": "http://localhost:5173"}
PIN = "1234"
MINE = "/api/me/readings"
TAHDIR_MINE = "/api/me/tahdir"
QUEUE = "/api/admin/readings"
TAHDIR_QUEUE = "/api/admin/tahdir"
APPROVE = "/api/admin/readings/approve"
ENTRY = "/api/admin/tahdir/entry"
REPORT = "/api/admin/tahdir/report"

# ٢٠٢٦-٠٨-٠٢ أحد · ٠٣ اثنين · ٠٤ ثلاثاء · ٠٥ أربعاء — كلّها ماضية بأمان
# نسبةً إلى تاريخ تشغيل هذه الاختبارات (٢٠٢٦-٠٩ فصاعدًا).
SUNDAY = date(2026, 8, 2)
MONDAY = date(2026, 8, 3)
THURSDAY = date(2026, 8, 6)
SATURDAY = date(2026, 8, 1)


def _login(client, student_no="1001"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": PIN}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _add_tahdir_weight(seeded, hours="1.00"):
    """
    وزن `tahdir` **غير مبذور** في `conftest.py` (رقمه الحقيقيّ لم يُحسم بعد —
    «نحدده لاحقًا»)، فيُضاف محليًّا هنا فقط لإثبات أن الآلية تعمل — نفس نمط
    `test_admin_attendance.py::_add_attendance_weight`.
    """
    db.session.add(
        Weight(
            version_id=seeded["versions"]["new"],
            activity_type="tahdir",
            hours_per_unit=Decimal(hours),
        )
    )
    db.session.commit()


def _submit_tahdir(client, read_on=SUNDAY, pages=10, book="كتاب التحضير"):
    return client.post(
        TAHDIR_MINE,
        json={"read_on": read_on.isoformat(), "pages": pages, "book_title": book},
        headers=ORIGIN,
    )


def _balance(user_id):
    return db.session.scalar(
        select(db.func.coalesce(db.func.sum(PointEvent.delta), 0)).where(
            PointEvent.user_id == user_id
        )
    )


# ═══ ق-١٥٧ — خارج الأحد–الأربعاء يُرفض ═══


def test_tahdir_outside_sun_to_wed_is_rejected(client, seeded):
    """@covers ق-١٥٧"""
    _login(client)
    r = _submit_tahdir(client, read_on=THURSDAY)
    assert r.status_code == 422


# ═══ ق-١٥٨ — داخل النطاق بصفحات ≥٧ يُقبل معلَّقًا ═══


def test_tahdir_within_sun_to_wed_is_accepted(client, seeded):
    """@covers ق-١٥٨"""
    _login(client)
    r = _submit_tahdir(client, read_on=MONDAY, pages=8)
    assert r.status_code == 201
    assert r.json["status"] == "pending"


# ═══ ق-١٥٩ — صفحات دون ٧ ⇒ ٤٢٢ ═══


def test_tahdir_below_minimum_pages_is_rejected(client, seeded):
    """@covers ق-١٥٩"""
    _login(client)
    r = _submit_tahdir(client, pages=6)
    assert r.status_code == 422


def test_tahdir_exactly_minimum_pages_is_accepted(client, seeded):
    """@covers ق-١٥٩ — الحدّ الآخر: ٧ بالضبط يُقبل."""
    _login(client)
    assert _submit_tahdir(client, pages=7).status_code == 201


# ═══ ق-١٦٠ — لا ساعات قبل الاعتماد ═══


def test_tahdir_submission_grants_no_hours_before_approval(client, seeded):
    """@covers ق-١٦٠"""
    uid = seeded["users"]["1001"]
    _login(client)
    before = _balance(uid)
    r = _submit_tahdir(client)
    assert r.status_code == 201
    assert _balance(uid) == before
    assert db.session.scalar(select(ReadingSubmission.point_event_id)) is None


# ═══ ق-١٦١ — إرسال مزدوج ⇒ ٤٠٩ ═══


def test_duplicate_tahdir_same_day_book_is_rejected(client, seeded):
    """@covers ق-١٦١"""
    _login(client)
    assert _submit_tahdir(client, read_on=SUNDAY, book="نفس الكتاب").status_code == 201
    assert _submit_tahdir(client, read_on=SUNDAY, book="نفس الكتاب").status_code == 409


# ═══ ق-١٦٢ — الاعتماد عبر المسار القائم بلا تعديل ═══


def test_tahdir_approved_via_existing_readings_approve_route(client, seeded):
    """
    @covers ق-١٦٢ — إعادة استعمال حرفيّة، صفر منطق خلفيّ جديد.

    **الوزن المستعمَل وزن `tahdir` لا وزن `reading`** — هذا بالضبط ما يمسكه
    هذا المعيار: مسارٌ عامّ على `activity_type` قد يُغري بحساب الوزن من ثابتٍ
    واحد بدل صفّ الطلب نفسه.
    """
    uid = seeded["users"]["1001"]
    _add_tahdir_weight(seeded, hours="2.00")  # يختلف عمدًا عن وزن reading (٠.١٥)
    _login(client)
    sid = _submit_tahdir(client, pages=10).json["id"]
    _make_admin(uid)

    r = client.post(APPROVE, json={"ids": [sid]}, headers=ORIGIN)
    assert r.status_code == 200
    assert r.json["results"][0]["hours"] == "20.00"  # ١٠ × ٢.٠٠ — لا ١٠ × ٠.١٥
    assert _balance(uid) == Decimal("20.00")


# ═══ ق-١٦٣ — عزل القوائم الإدارية ═══


def test_admin_tahdir_queue_shows_only_tahdir(client, seeded):
    """@covers ق-١٦٣"""
    _login(client)
    tid = _submit_tahdir(client).json["id"]
    client.post("/api/auth/logout", headers=ORIGIN)

    _login(client, "1002")
    rid = client.post(
        MINE,
        json={"read_on": SUNDAY.isoformat(), "pages": 40, "book_title": "قراءة عامّة"},
        headers=ORIGIN,
    ).json["id"]
    client.post("/api/auth/logout", headers=ORIGIN)

    _make_admin(seeded["users"]["1001"])
    _login(client)
    tahdir_ids = [s["id"] for s in client.get(TAHDIR_QUEUE).json["submissions"]]
    reading_ids = [s["id"] for s in client.get(QUEUE).json["submissions"]]

    assert tahdir_ids == [tid]
    assert reading_ids == [rid]


# ═══ ق-١٦٤ — عزل قوائم الطالب ═══


def test_student_tahdir_and_reading_lists_are_separate(client, seeded):
    """@covers ق-١٦٤"""
    _login(client)
    _submit_tahdir(client, book="كتاب التحضير")
    client.post(
        MINE,
        json={"read_on": SUNDAY.isoformat(), "pages": 40, "book_title": "كتاب القراءة"},
        headers=ORIGIN,
    )

    tahdir = client.get(TAHDIR_MINE).json["submissions"]
    reading = client.get(MINE).json["readings"]
    assert [s["book_title"] for s in tahdir] == ["كتاب التحضير"]
    assert [r["book_title"] for r in reading] == ["كتاب القراءة"]


# ═══ ق-١٦٥ — الإضافة الإدارية المباشرة ═══


def test_admin_entry_creates_approved_event_immediately(client, seeded):
    """@covers ق-١٦٥ — الساعات محسوبة عبر المحرّك لا مُدخَلة."""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _add_tahdir_weight(seeded, hours="3.00")
    _make_admin(admin)
    _login(client)

    r = client.post(
        ENTRY,
        json={
            "user_id": target,
            "read_on": SUNDAY.isoformat(),
            "pages": 10,
            "book_title": "تحضير مباشر",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 201
    assert r.json["status"] == "approved"
    assert r.json["hours"] == "30.00"  # ١٠ × ٣.٠٠ — لا ١٠ (رقمٌ مُدخَل مباشرةً)
    assert _balance(target) == Decimal("30.00")
    assert (
        db.session.scalar(
            select(ReadingSubmission.status).where(ReadingSubmission.user_id == target)
        )
        == "approved"
    )


# ═══ ق-١٦٦ — لا استثناء إداريّ لقواعد اليوم/الحدّ الأدنى ═══


def test_admin_entry_still_enforces_tahdir_day(client, seeded):
    """@covers ق-١٦٦"""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _add_tahdir_weight(seeded)  # السقوط يجب أن يكون من يوم الأسبوع لا من وزن مفقود.
    _make_admin(admin)
    _login(client)

    r = client.post(
        ENTRY,
        json={
            "user_id": target,
            "read_on": THURSDAY.isoformat(),
            "pages": 10,
            "book_title": "تحضير خميس",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 422
    assert r.json["message"] == "تحضير القراءة يكون من الأحد إلى الأربعاء فقط."
    assert _balance(target) == 0


# ═══ ق-١٦٧ — سطر تدقيق منسوب، ذرّيّ مع الحدث ═══


def test_admin_entry_writes_attributed_audit_row(client, seeded):
    """@covers ق-١٦٧"""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _add_tahdir_weight(seeded)
    _make_admin(admin)
    _login(client)

    client.post(
        ENTRY,
        json={
            "user_id": target,
            "read_on": SUNDAY.isoformat(),
            "pages": 10,
            "book_title": "تحضير مباشر",
        },
        headers=ORIGIN,
    )
    entry = db.session.scalar(select(AuditEntry))
    assert entry.kind == "reading_admin_entry"
    assert entry.actor_id == admin
    assert entry.actor_id != target


# ═══ ق-١٧٤ — إرسال مزدوج عبر الإضافة الإدارية المباشرة ⇒ ٤٠٩ لا ٥٠٠ ═══
#
# اكتُشفت أثناء الإثبات العدائي لـق-١٦٦: `db.session.flush()` يُدرج فعليًّا
# فيصطدم بقيد `UNIQUE` **قبل** `try/except` الذي كان يحرس `commit()` وحده —
# فيسرّب `IntegrityError` خامًا (٥٠٠) بدل ٤٠٩ المقصود. لم يكن هذا جزءًا من
# الخطّة الأصلية (§٨.٢)، بل عيبٌ حقيقيّ ظهر جانبيًّا فأُصلح فورًا.


def test_duplicate_admin_entry_is_409_not_500(client, seeded):
    """@covers ق-١٧٤"""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _add_tahdir_weight(seeded)
    _make_admin(admin)
    _login(client)

    body = {
        "user_id": target,
        "read_on": SUNDAY.isoformat(),
        "pages": 10,
        "book_title": "نسخة",
    }
    r1 = client.post(ENTRY, json=body, headers=ORIGIN)
    r2 = client.post(ENTRY, json=body, headers=ORIGIN)
    assert r1.status_code == 201
    assert r2.status_code == 409
    assert r2.json["message"] == "سجّلت هذا الكتاب في هذا اليوم من قبل."


# ═══ ق-١٦٨ — المسار السالب الإلزامي ═══


def test_tahdir_admin_routes_require_admin(client, seeded):
    """@covers ق-١٦٨"""
    _login(client)
    assert client.get(TAHDIR_QUEUE).status_code == 403
    assert client.get(REPORT).status_code == 403
    assert (
        client.post(
            ENTRY,
            json={
                "user_id": seeded["users"]["1002"],
                "read_on": SUNDAY.isoformat(),
                "pages": 10,
                "book_title": "x",
            },
            headers=ORIGIN,
        ).status_code
        == 403
    )


def test_tahdir_routes_require_session(client, seeded):
    """@covers ق-١٦٨"""
    assert client.get(TAHDIR_MINE).status_code == 401
    assert client.get(TAHDIR_QUEUE).status_code == 401
    assert client.get(REPORT).status_code == 401


# ═══ ق-١٦٩ — «يوم مكتمل» = معتمد بصفحات ≥٧ لا معلَّق ═══
#
# `weekly_report` يُستدعى **مباشرةً من الخدمة** بـ`now`
# مجمَّدًا (نمط `entry.undo(..., now=...)` القائم في `test_admin_attendance.py`)
# — لا عبر HTTP: التقرير دائمًا عن «الأسبوع الحاليّ» الحقيقيّ، وربطه بتاريخ
# ثابت في الماضي (SUNDAY) عبر HTTP كان سيجعل الاختبار هشًّا زمنيًّا (نفس
# هشاشة `test_undo_after_window_is_409` الموثَّقة في `HANDOFF.md` §١٢).

FIXED_NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)  # داخل أسبوع الأحد ٠٢–٠٥ أغسطس


def test_completed_day_requires_approval_not_just_submission(client, seeded):
    """@covers ق-١٦٩"""
    org = db.session.get(Org, seeded["org_id"])
    _login(client)
    _submit_tahdir(client, read_on=SUNDAY, pages=10)  # يبقى معلَّقًا — لا اعتماد

    week = reading_service.weekly_report(org, seeded["users"]["1001"], now=FIXED_NOW)
    sunday_entry = next(d for d in week["days"] if d["date"] == SUNDAY)
    assert sunday_entry["completed"] is False
    assert sunday_entry["pages"] == 0  # الصفحات المعلَّقة لا تُحتسَب في التقرير


def test_completed_day_true_after_approval_with_enough_pages(client, seeded):
    """@covers ق-١٦٩ — الحدّ الآخر."""
    uid = seeded["users"]["1001"]
    org = db.session.get(Org, seeded["org_id"])
    _add_tahdir_weight(seeded)
    _login(client)
    sid = _submit_tahdir(client, read_on=SUNDAY, pages=10).json["id"]
    _make_admin(uid)
    client.post(APPROVE, json={"ids": [sid]}, headers=ORIGIN)

    week = reading_service.weekly_report(org, uid, now=FIXED_NOW)
    sunday_entry = next(d for d in week["days"] if d["date"] == SUNDAY)
    assert sunday_entry["completed"] is True
    assert sunday_entry["pages"] == 10


# ═══ ق-١٧٠ — النسبة والتعثّر ═══


def test_percent_is_pages_over_28_and_struggling_below_100(client, seeded):
    """@covers ق-١٧٠"""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    org = db.session.get(Org, seeded["org_id"])
    _add_tahdir_weight(seeded)
    _make_admin(admin)
    _login(client)
    # ١٠ صفحات فقط من أصل ٢٨ ⇒ ٣٥.٧٪ ومتعثّر.
    r = client.post(
        ENTRY,
        json={
            "user_id": target,
            "read_on": SUNDAY.isoformat(),
            "pages": 10,
            "book_title": "تحضير",
        },
        headers=ORIGIN,
    )
    assert r.status_code == 201

    week = reading_service.weekly_report(org, target, now=FIXED_NOW)
    assert week["pages_total"] == 10
    assert week["percent"] == 35.7
    assert week["struggling"] is True


def test_full_target_is_not_struggling(client, seeded):
    """@covers ق-١٧٠ — الحدّ الآخر: ٢٨/٢٨ = ١٠٠٪ غير متعثّر."""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    org = db.session.get(Org, seeded["org_id"])
    _add_tahdir_weight(seeded)
    _make_admin(admin)
    _login(client)
    for i, d in enumerate([SUNDAY, MONDAY]):
        r = client.post(
            ENTRY,
            json={
                "user_id": target,
                "read_on": d.isoformat(),
                "pages": 14,
                "book_title": f"تحضير {i}",
            },
            headers=ORIGIN,
        )
        assert r.status_code == 201

    week = reading_service.weekly_report(org, target, now=FIXED_NOW)
    assert week["pages_total"] == 28
    assert week["percent"] == 100.0
    assert week["struggling"] is False


# ═══ ق-١٧١ — تقرير المنظمة يشمل من لم يُرسل شيئًا ═══


def test_org_report_includes_students_with_no_submission(client, seeded):
    """@covers ق-١٧١"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    report = client.get(REPORT).json
    user_ids = {s["user_id"] for s in report["students"]}
    assert seeded["users"]["1001"] in user_ids
    assert seeded["users"]["1002"] in user_ids
    silent = next(s for s in report["students"] if s["user_id"] == seeded["users"]["1002"])
    assert silent["pages_total"] == 0
    assert silent["percent"] == 0.0
    assert silent["struggling"] is True


# ═══ ق-١٧٢ — صفر تراجع: طابور القراءة العامّ يعمل كما كان ═══


def test_general_reading_queue_unaffected_by_tahdir(client, seeded):
    """@covers ق-١٧٢ — نفس سلوك و-٤ الأصليّ رغم وجود برنامج تحضير جديد."""
    _login(client)
    _submit_tahdir(client)
    client.post(
        MINE,
        json={"read_on": SUNDAY.isoformat(), "pages": 40, "book_title": "قراءة عادية"},
        headers=ORIGIN,
    )
    client.post("/api/auth/logout", headers=ORIGIN)

    _make_admin(seeded["users"]["1001"])
    _login(client)
    submissions = client.get(QUEUE).json["submissions"]
    assert len(submissions) == 1
    assert submissions[0]["book_title"] == "قراءة عادية"


# ═══ ق-٢٥٩ — تقرير التحضير بفترة محدَّدة ودرجاتُ انتظام (و-٢٠) ═══


def _approve_all(client, seeded):
    """يعتمد كل ما في الطابور — الساعات والدرجات لا تُحتسب قبل الاعتماد."""
    ids = [s["id"] for s in client.get(TAHDIR_QUEUE).json["submissions"]]
    if ids:
        client.post(APPROVE, json={"ids": ids}, headers=ORIGIN)
    return ids


def test_report_defaults_to_this_week_and_reports_its_window(client, seeded):
    """@covers ق-٢٥٩ — الأسبوع حالةٌ خاصّة من الفترة لا مسارٌ ثانٍ."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.get(REPORT).json
    assert r["days_total"] == 4, "أيام التحضير أربعة في الأسبوع"
    assert r["from_day"] < r["to_day"]
    assert "totals" in r and "students" in r


def test_explicit_range_spanning_two_weeks_counts_eight_days(client, seeded):
    """
    @covers ق-٢٥٩

    الفترة تُؤخذ منها أيّامُ التحضير في **كل أسبوع** لا أيامها التقويمية —
    أسبوعان ⇒ ثمانية أيام مؤهَّلة لا أربعة عشر.
    """
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.get(f"{REPORT}?from=2026-08-01&to=2026-08-14").json
    assert r["days_total"] == 8


def test_tiers_are_computed_on_the_server_by_the_mockup_thresholds(client, seeded):
    """
    @covers ق-٢٥٩

    الدرجة **قاعدة عمل** لا عرض: ٤/٤ ⇒ ممتاز · ٢/٤ ⇒ منتظم · ٠/٤ ⇒ يحتاج
    متابعة (عتبتا ٠٫٩ و٠٫٥ من النموذج المعتمد).
    """
    _add_tahdir_weight(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)
    for day in (SUNDAY, MONDAY, date(2026, 8, 4), date(2026, 8, 5)):
        _submit_tahdir(client, read_on=day, pages=10)
    _approve_all(client, seeded)

    r = client.get(f"{REPORT}?from=2026-08-01&to=2026-08-05").json
    mine = next(s for s in r["students"] if s["user_id"] == seeded["users"]["1001"])
    silent = next(s for s in r["students"] if s["user_id"] == seeded["users"]["1002"])

    assert mine["days_completed"] == 4 and mine["days_total"] == 4
    assert mine["tier"] == "good"
    assert silent["tier"] == "low"
    assert mine["team_name"], "السرب عمودٌ في النموذج"


def test_totals_count_participants_and_fully_regular(client, seeded):
    """@covers ق-٢٥٩ — البطاقات الثلاث في النموذج."""
    _add_tahdir_weight(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)
    for day in (SUNDAY, MONDAY, date(2026, 8, 4), date(2026, 8, 5)):
        _submit_tahdir(client, read_on=day, pages=10)
    _approve_all(client, seeded)

    totals = client.get(f"{REPORT}?from=2026-08-01&to=2026-08-05").json["totals"]
    assert totals["pages"] == 40
    assert totals["participants"] == 1
    assert totals["fully_regular"] == 1


def test_half_range_gives_the_middle_tier(client, seeded):
    """@covers ق-٢٥٩ — ٢/٤ = ٠٫٥ بالضبط ⇒ «منتظم» لا «يحتاج متابعة»."""
    _add_tahdir_weight(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)
    for day in (SUNDAY, MONDAY):
        _submit_tahdir(client, read_on=day, pages=10)
    _approve_all(client, seeded)

    r = client.get(f"{REPORT}?from=2026-08-01&to=2026-08-05").json
    mine = next(s for s in r["students"] if s["user_id"] == seeded["users"]["1001"])
    assert mine["days_completed"] == 2
    assert mine["tier"] == "fair"


def test_half_open_or_reversed_range_is_refused(client, seeded):
    """@covers ق-٢٥٩ — فترةٌ بطرفٍ واحد أو مقلوبة خطأٌ معلَن لا تخمين."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    assert client.get(f"{REPORT}?from=2026-08-01").status_code == 422
    assert client.get(f"{REPORT}?from=2026-08-10&to=2026-08-01").status_code == 422
    assert client.get(f"{REPORT}?from=غير-تاريخ&to=2026-08-01").status_code == 422
