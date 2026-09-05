"""
التفاعل اليوميّ — و-٩ج · FR-060، و-٩د · FR-061/FR-062.

**أوّل كتابة `ledger` جديدة في هذه الوحدة** (`kind='daily_question'`)، وأوّل
قيدَي `UNIQUE` جديدين كليًّا في المشروع (`daily_questions.org_id+day`،
`pilot_of_week.org_id+week_start`) — كلاهما مُثبَت في القاعدة الحقيقية
بـSQL خام قبل أي كود خدمة (`docs/slices/و-٩.md`).

**ث-١٧** (`answers.correct` و`point_event_id` لا يفترقان، `CHECK` +
دفاع خدمة عبر `ledger.append_pending`) أُضيف بعد مراجعة صريحة لذرّية
الكتابة — دفاعٌ مزدوج بنمط ث-١٣ب.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Answer, DailyQuestion, Membership, Note, Org, PointEvent
from app.services import engagement, ledger

ORIGIN = {"Origin": "http://localhost:5173"}
TODAY = "/api/questions/today"
ADMIN_NOTES = "/api/admin/notes"
SUBMIT_NOTE = "/api/notes"
WEEK_PILOT = "/api/week/pilot"
ADMIN_WEEK_PILOT = "/api/admin/week/pilot"
CHOICES = [{"id": 1, "text": "الأولى"}, {"id": 2, "text": "الثانية"}, {"id": 3, "text": "الثالثة"}]
# مسارات HTTP تستدعي الخدمة بلا `now`، فتستعمل الوقت الحقيقي — يجب أن يكون
# «اليوم» الافتراضي هنا نفس «اليوم» الحقيقي بتوقيت الرياض، لا تاريخًا ثابتًا
# قد يقع في الماضي أو المستقبل بالنسبة إلى لحظة تشغيل الاختبار الفعلية.
TODAY_RIYADH = datetime.now(UTC).astimezone(ZoneInfo("Asia/Riyadh")).date()


def _login(client, student_no="1001"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": "1234"}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _question(org_id, day=None, correct_id=2, reward="2.50"):
    q = DailyQuestion(
        org_id=org_id,
        day=TODAY_RIYADH if day is None else day,
        prompt="أيّ سورة أطول؟",
        choices=CHOICES,
        correct_id=correct_id,
        note="البقرة أطول سور القرآن.",
        reward_hours=Decimal(reward),
    )
    db.session.add(q)
    db.session.commit()
    return q


def _answer_url(question_id):
    return f"/api/questions/{question_id}/answer"


# ═══ ق-١٠٠ — UNIQUE(org_id, day) في القاعدة الحقيقية ═══


def test_unique_org_day_constraint_exists_at_db_level(client, seeded):
    """@covers ق-١٠٠ — يُثبَت بالنموذج مباشرةً، لا بمسار: لا خدمة تُنشئ سؤالًا."""
    _question(seeded["org_id"])
    dup = DailyQuestion(
        org_id=seeded["org_id"],
        day=TODAY_RIYADH,
        prompt="سؤال آخر لنفس اليوم",
        choices=CHOICES,
        correct_id=1,
        note="...",
        reward_hours=Decimal("1.00"),
    )
    db.session.add(dup)
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


# ═══ ق-١٢٣ · ق-١٢٤ — ث-١٧: `correct` و`point_event_id` لا يفترقان ═══


def test_check_constraint_rejects_correct_answer_without_event(client, seeded):
    """@covers ق-١٢٣ — إجابة صحيحة بلا حدث دفتر، مباشرةً عبر النموذج."""
    q = _question(seeded["org_id"])
    row = Answer(
        org_id=seeded["org_id"],
        user_id=seeded["users"]["1001"],
        question_id=q.id,
        choice_id=q.correct_id,
        correct=True,
        point_event_id=None,
    )
    db.session.add(row)
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


def test_check_constraint_rejects_wrong_answer_with_event(client, seeded):
    """@covers ق-١٢٣ — الاتّجاه الآخر: إجابة خاطئة تحمل حدثًا لم تستحقّه."""
    q = _question(seeded["org_id"])
    event = ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind="daily_question",
                delta=Decimal("1.00"),
                user_id=seeded["users"]["1001"],
                occurred_at=datetime.now(UTC),
            )
        ]
    )[0]
    row = Answer(
        org_id=seeded["org_id"],
        user_id=seeded["users"]["1001"],
        question_id=q.id,
        choice_id=1,
        correct=False,
        point_event_id=event.id,
    )
    db.session.add(row)
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


def test_correct_answer_always_carries_its_own_event_id(client, seeded):
    """
    @covers ق-١٢٤ — دفاعٌ مزدوج (نمط ث-١٣ب): الخدمة تربط `point_event_id`
    بحدثه الصحيح فعليًّا، لا بأي حدث. يثبت أن الرابط ذو معنى لا مجرّد
    عدم-فراغ.
    """
    q = _question(seeded["org_id"], correct_id=2, reward="2.50")
    _login(client)
    client.post(_answer_url(q.id), json={"choice_id": 2}, headers=ORIGIN)

    row = db.session.scalar(select(Answer).where(Answer.question_id == q.id))
    assert row.point_event_id is not None
    event = db.session.get(PointEvent, row.point_event_id)
    assert event.kind == "daily_question"
    assert event.user_id == seeded["users"]["1001"]
    assert event.delta == Decimal("2.50")


# ═══ ق-٩٤ · ق-٩٥ — عقد GET /questions/today ═══


def test_today_hides_correct_id_and_note_before_answering(client, seeded):
    """@covers ق-٩٤"""
    _question(seeded["org_id"])
    _login(client)
    body = client.get(TODAY).json
    assert body["question"]["answered"] is None
    assert set(body["question"]) == {"id", "prompt", "choices", "answered"}
    assert all(set(c) == {"id", "text"} for c in body["question"]["choices"])


def test_today_is_null_not_404_when_no_question_seeded(client, seeded):
    """@covers ق-٩٥ — حالة مصمَّمة، نمط `team: null`."""
    _login(client)
    r = client.get(TODAY)
    assert r.status_code == 200
    assert r.json == {"question": None}


# ═══ ق-٩٦ — الإجابة لا تختفي عند إعادة الفتح ═══


def test_today_shows_answered_result_after_answering(client, seeded):
    """@covers ق-٩٦"""
    q = _question(seeded["org_id"])
    _login(client)
    client.post(_answer_url(q.id), json={"choice_id": 1}, headers=ORIGIN)

    body = client.get(TODAY).json
    assert body["question"]["answered"] == {
        "choice_id": 1,
        "correct": False,
        "correct_id": 2,
        "note": "البقرة أطول سور القرآن.",
        "awarded_hours": "0.00",
    }


# ═══ ق-٩٧ — إجابة صحيحة تكتب حدث دفتر ═══


def test_correct_answer_writes_ledger_event_and_awards_reward(client, seeded):
    """@covers ق-٩٧"""
    q = _question(seeded["org_id"], correct_id=2, reward="2.50")
    _login(client)
    r = client.post(_answer_url(q.id), json={"choice_id": 2}, headers=ORIGIN)

    assert r.json == {
        "choice_id": 2,
        "correct": True,
        "correct_id": 2,
        "note": "البقرة أطول سور القرآن.",
        "awarded_hours": "2.50",
    }
    deck = client.get("/api/me/deck").json
    assert deck["hours"] == "2.50"


# ═══ ق-٩٨ — إجابة خاطئة: الشرح يظهر، ولا حدث دفتر ═══


def test_wrong_answer_shows_explanation_and_writes_no_ledger_event(client, seeded):
    """@covers ق-٩٨ — بلا عقوبة على الخطأ (ط-٦)، وبلا مكافأة أيضًا."""
    q = _question(seeded["org_id"], correct_id=2, reward="2.50")
    _login(client)
    r = client.post(_answer_url(q.id), json={"choice_id": 1}, headers=ORIGIN)

    assert r.json["correct"] is False
    assert r.json["correct_id"] == 2
    assert r.json["note"] == "البقرة أطول سور القرآن."
    assert r.json["awarded_hours"] == "0.00"

    deck = client.get("/api/me/deck").json
    assert deck["hours"] == "0.00"


# ═══ ق-٩٩ — إجابة ثانية ⇒ ٤٠٩ ═══


def test_second_answer_is_rejected_with_409(client, seeded):
    """@covers ق-٩٩ — القيد في القاعدة، لا زرّ مُعطَّل."""
    q = _question(seeded["org_id"])
    _login(client)
    client.post(_answer_url(q.id), json={"choice_id": 1}, headers=ORIGIN)
    r = client.post(_answer_url(q.id), json={"choice_id": 2}, headers=ORIGIN)
    assert r.status_code == 409


# ═══ ق-١٠١ — خيار غير موجود ⇒ ٤٢٢ ═══


def test_unknown_choice_id_is_422(client, seeded):
    """@covers ق-١٠١"""
    q = _question(seeded["org_id"])
    _login(client)
    r = client.post(_answer_url(q.id), json={"choice_id": 999}, headers=ORIGIN)
    assert r.status_code == 422


# ═══ ق-١٠٢ — سؤال غير موجود / ليس لليوم ⇒ ٤٠٤ ═══


def test_answering_nonexistent_question_is_404(client, seeded):
    """@covers ق-١٠٢"""
    _login(client)
    r = client.post(_answer_url(99999), json={"choice_id": 1}, headers=ORIGIN)
    assert r.status_code == 404


def test_answering_yesterdays_question_today_is_404(client, seeded):
    """@covers ق-١٠٢ — سؤالٌ حقيقيّ لكن ليس لليوم الحالي."""
    q = _question(seeded["org_id"], day=TODAY_RIYADH - timedelta(days=1))
    _login(client)
    r = client.post(_answer_url(q.id), json={"choice_id": 1}, headers=ORIGIN)
    assert r.status_code == 404


# ═══ ق-١٠٣ — تخويل ═══


def test_questions_routes_require_login(client, seeded):
    """@covers ق-١٠٣"""
    q = _question(seeded["org_id"])
    assert client.get(TODAY).status_code == 401
    assert client.post(_answer_url(q.id), json={"choice_id": 1}, headers=ORIGIN).status_code == 401


# ═══ ق-١٠٤ — «اليوم» بتوقيت المنظمة لا UTC الخام ═══


def test_today_uses_org_timezone_not_naive_utc_date(client, seeded):
    """
    @covers ق-١٠٤ — ٢٢:٠٠ UTC الاثنين ٣ أغسطس = ٠١:٠٠ الثلاثاء ٤ أغسطس
    بتوقيت الرياض (UTC+3). سؤالٌ مبذور ليوم ٤ أغسطس يجب أن يظهر عند هذه
    اللحظة، رغم أن تاريخ UTC الخام في نفس اللحظة ما زال ٣ أغسطس.
    """
    org = db.session.get(Org, seeded["org_id"])
    assert org.timezone == "Asia/Riyadh"
    instant = datetime(2026, 8, 3, 22, 0, tzinfo=UTC)
    assert instant.astimezone(ZoneInfo("Asia/Riyadh")).date().isoformat() == "2026-08-04"
    assert instant.date().isoformat() == "2026-08-03"

    q_tuesday = _question(seeded["org_id"], day="2026-08-04")

    found, _ = engagement.today(org, seeded["users"]["1001"], now=instant)
    assert found is not None and found.id == q_tuesday.id


# ═══ ق-١٠٧ — POST /notes ⇒ ٢٠١ بجسم فارغ ═══


def test_submit_note_returns_201_empty_body(client, seeded):
    """@covers ق-١٠٧"""
    _login(client)
    r = client.post(SUBMIT_NOTE, json={"body": "رسالة مجهولة"}, headers=ORIGIN)
    assert r.status_code == 201
    assert r.json is None


# ═══ ق-١٠٨ — بنية الجدول بلا مصدر (ث-١٢) ═══


def test_notes_table_has_no_sender_columns(client, seeded):
    """@covers ق-١٠٨ — فحص المخطط لا سلوك."""
    columns = {c.name for c in Note.__table__.columns}
    assert "user_id" not in columns
    assert "ip" not in columns
    assert columns == {"id", "org_id", "body", "day", "read_at"}


# ═══ ق-١٠٩ — ملاحظة فارغة ⇒ ٤٢٢ ═══


def test_submit_blank_note_is_422(client, seeded):
    """@covers ق-١٠٩"""
    _login(client)
    r = client.post(SUBMIT_NOTE, json={"body": "   "}, headers=ORIGIN)
    assert r.status_code == 422


# ═══ ق-١١٠ — GET /admin/notes: الأحدث أوّلًا، بلا مصدر ═══


def test_admin_notes_ordered_newest_first_and_has_no_sender_field(client, seeded):
    """@covers ق-١١٠"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    client.post(SUBMIT_NOTE, json={"body": "الأولى"}, headers=ORIGIN)
    client.post(SUBMIT_NOTE, json={"body": "الثانية"}, headers=ORIGIN)

    body = client.get(ADMIN_NOTES).json
    assert [n["body"] for n in body["notes"]][:2] == ["الثانية", "الأولى"]
    assert all(set(n) == {"id", "body", "day", "read_at"} for n in body["notes"])


# ═══ ق-١١١ · ق-١١٢ — تعليم مقروءة أحاديّ الاتّجاه ═══


def test_mark_note_read_sets_read_at(client, seeded):
    """@covers ق-١١١"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    client.post(SUBMIT_NOTE, json={"body": "ملاحظة"}, headers=ORIGIN)
    note = db.session.scalar(select(Note).where(Note.org_id == seeded["org_id"]))
    assert note.read_at is None

    r = client.patch(f"{ADMIN_NOTES}/{note.id}", json={"read": True}, headers=ORIGIN)
    assert r.status_code == 200
    assert r.json["read_at"] is not None


def test_marking_note_unread_is_rejected(client, seeded):
    """@covers ق-١١٢ — `read` يقبل `true` وحدها، لا رجوع إلى «غير مقروءة»."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    client.post(SUBMIT_NOTE, json={"body": "ملاحظة"}, headers=ORIGIN)
    note = db.session.scalar(select(Note).where(Note.org_id == seeded["org_id"]))
    r = client.patch(f"{ADMIN_NOTES}/{note.id}", json={"read": False}, headers=ORIGIN)
    assert r.status_code == 422


# ═══ ق-١١٣ — تخويل /admin/notes ═══


def test_admin_notes_requires_admin(client, seeded):
    """@covers ق-١١٣"""
    assert client.get(ADMIN_NOTES).status_code == 401
    _login(client)
    assert client.get(ADMIN_NOTES).status_code == 403


# ═══ ق-١١٤ — GET /week/pilot: null قبل الاختيار ═══


def test_week_pilot_is_null_before_selection(client, seeded):
    """@covers ق-١١٤ — حالة مصمَّمة لا ٤٠٤."""
    _login(client)
    r = client.get(WEEK_PILOT)
    assert r.status_code == 200
    assert r.json == {"pilot": None}


# ═══ ق-١١٥ · ق-١١٦ — الاختيار ثم ظهوره للطيّارين ═══


def test_choosing_week_pilot_then_visible_to_pilots(client, seeded):
    """
    @covers ق-١١٥, ق-١١٦ — ق-١١٥ يتحقّق من `week_start` نفسه، لا فقط من
    نجاح الطلب: يُقارَن بصيغة `standings._week_start` المحسوبة يدويًّا في
    `test_standings.py` (نفس `org.week_starts_on`), لا بالقيمة العائدة من
    الخدمة نفسها — وإلا كان الإثبات دائريًّا.
    """
    org = db.session.get(Org, seeded["org_id"])
    now = datetime.now(UTC)
    local_now = now.astimezone(ZoneInfo(org.timezone))
    days_since_start = (local_now.weekday() - org.week_starts_on) % 7
    expected_week_start = (local_now.date() - timedelta(days=days_since_start)).isoformat()

    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post(
        ADMIN_WEEK_PILOT,
        json={"user_id": seeded["users"]["1002"], "reason": "ثبات حضوره هذا الأسبوع."},
        headers=ORIGIN,
    )
    assert r.status_code == 201
    assert r.json["full_name"] == "طالب ثانٍ"
    assert r.json["week_start"] == expected_week_start

    body = client.get(WEEK_PILOT).json
    assert body == {"pilot": {"full_name": "طالب ثانٍ", "reason": "ثبات حضوره هذا الأسبوع."}}


# ═══ ق-١١٧ — سبب فارغ ⇒ ٤٢٢ ═══


def test_choosing_week_pilot_without_reason_is_422(client, seeded):
    """@covers ق-١١٧ — ط-١٠: القيمة كلّها في «لماذا»."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post(
        ADMIN_WEEK_PILOT, json={"user_id": seeded["users"]["1002"], "reason": "   "}, headers=ORIGIN
    )
    assert r.status_code == 422


# ═══ ق-١١٨ — اختيار ثانٍ لنفس الأسبوع ⇒ ٤٠٩ (ث-٩) ═══


def test_second_week_pilot_choice_is_409(client, seeded):
    """@covers ق-١١٨"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    client.post(
        ADMIN_WEEK_PILOT,
        json={"user_id": seeded["users"]["1002"], "reason": "سبب أوّل"},
        headers=ORIGIN,
    )
    r = client.post(
        ADMIN_WEEK_PILOT,
        json={"user_id": seeded["users"]["1001"], "reason": "سبب ثانٍ"},
        headers=ORIGIN,
    )
    assert r.status_code == 409


# ═══ ق-١١٩ — طالب غير موجود ⇒ ٤٢٢ ═══


def test_choosing_nonexistent_user_is_422(client, seeded):
    """@covers ق-١١٩"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.post(ADMIN_WEEK_PILOT, json={"user_id": 99999, "reason": "سبب"}, headers=ORIGIN)
    assert r.status_code == 422


# ═══ ق-١٢٠ — تخويل /admin/week/pilot ═══


def test_admin_week_pilot_requires_admin(client, seeded):
    """@covers ق-١٢٠"""
    body = {"user_id": 1, "reason": "سبب"}
    assert client.post(ADMIN_WEEK_PILOT, json=body, headers=ORIGIN).status_code == 401
    _login(client)
    assert client.post(ADMIN_WEEK_PILOT, json=body, headers=ORIGIN).status_code == 403
