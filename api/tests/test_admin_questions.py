"""
سؤال اليوم — الشقّ الإداريّ (و-٢١).

**الفجوة التي يسدّها:** `FR-060` بندٌ **MUST** وشاشةُ الطالب مبنيّة منذ و-٩،
لكن `SCOPE.md` ط-٦ أعلن أن «لا مسار إنشاء إداريًّا» والصفوف تُدرَج «بذرة أو
SQL». وأثرُ ذلك على خادمٍ منشور: جمعيةٌ جديدة بلا سؤالٍ واحد إلى الأبد —
فشاشةٌ كاملةٌ من شاشات الطيّار ميتةٌ بالتصميم.

@covers ق-٢٧٩, ق-٢٨٠, ق-٢٨١
"""

from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models import Answer, DailyQuestion, Membership

ORIGIN = {"Origin": "http://localhost:5173"}

BODY = {
    "day": "2026-08-01",
    "prompt": "كم عدد أجزاء القرآن الكريم؟",
    "choices": [{"id": 1, "text": "عشرون"}, {"id": 2, "text": "ثلاثون"}],
    "correct_id": 2,
    "note": "ثلاثون جزءًا، وتقسيمه اصطلاحٌ للتيسير لا توقيف.",
    "reward_hours": "1.00",
}


def _login(client, student_no="1001", pin="1234"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": pin}, headers=ORIGIN
    )


def _as_admin(client, seeded):
    m = db.session.scalar(select(Membership).where(Membership.user_id == seeded["users"]["1001"]))
    m.role = "admin"
    db.session.commit()
    _login(client)


# ═══ ق-٢٧٩ — الإنشاء يُنتج سؤالًا يراه الطالب فعلًا ═══


def test_created_question_reaches_the_pilot_screen(client, seeded):
    """
    **الفحص ليس وجود الصفّ بل وصولُه إلى الطالب.** مسارُ إنشاءٍ لا تراه شاشةُ
    `/questions/today` يسدّ الفجوة على الورق وحده.

    @covers ق-٢٧٩
    """
    _as_admin(client, seeded)
    today = client.get("/api/questions/today", headers=ORIGIN).get_json()
    assert today["question"] is None  # لا سؤال قبل الإنشاء

    from app.models import Org
    from app.services.reading import local_today

    org = db.session.get(Org, seeded["org_id"])
    r = client.post(
        "/api/admin/questions",
        json={**BODY, "day": local_today(org).isoformat()},
        headers=ORIGIN,
    )
    assert r.status_code == 201, r.get_json()

    after = client.get("/api/questions/today", headers=ORIGIN).get_json()
    assert after["question"]["prompt"] == BODY["prompt"]


def test_one_question_per_day(client, seeded):
    """القيد `uq_daily_questions_org_day` هو الضمانة — والرسالة تذكر اليوم.

    @covers ق-٢٧٩
    """
    _as_admin(client, seeded)
    assert client.post("/api/admin/questions", json=BODY, headers=ORIGIN).status_code == 201

    second = client.post("/api/admin/questions", json=BODY, headers=ORIGIN)
    assert second.status_code == 409
    assert "2026-08-01" in second.get_json()["message"]


def test_correct_id_outside_the_choices_is_refused(client, seeded):
    """
    **الحرس الحقيقيّ:** `correct_id` خارج الخيارات يُنتج سؤالًا **لا إجابة
    صحيحة له** — فكلُّ من يجيبه يُخطئ، ولا شيء في القاعدة يمنع ذلك.

    @covers ق-٢٧٩
    """
    _as_admin(client, seeded)
    r = client.post("/api/admin/questions", json={**BODY, "correct_id": 99}, headers=ORIGIN)
    assert r.status_code == 422
    assert "أحد الخيارات" in r.get_json()["message"]
    assert db.session.scalar(select(db.func.count(DailyQuestion.id))) == 0


def test_explanation_is_required_not_optional(client, seeded):
    """
    `FR-060`: «الجواب الصحيح **وشرحه** يظهران في الحالتين» — فالشرح نصفُ
    المتطلَّب، وسؤالٌ بلا شرحٍ ينقضه بصمت.

    @covers ق-٢٧٩
    """
    _as_admin(client, seeded)
    blank = client.post("/api/admin/questions", json={**BODY, "note": "   "}, headers=ORIGIN)
    assert blank.status_code == 422


def test_single_choice_is_not_a_question(client, seeded):
    """@covers ق-٢٧٩"""
    _as_admin(client, seeded)
    one = {**BODY, "choices": [{"id": 1, "text": "وحيد"}], "correct_id": 1}
    assert client.post("/api/admin/questions", json=one, headers=ORIGIN).status_code == 422


# ═══ ق-٢٨٠ — سؤالٌ أُجيب لا يُعدَّل ولا يُحذَف ═══


def _answer_it(client, seeded, question_id):
    """الطالب الثاني يجيب — فيُقفَل السؤال."""
    client.post("/api/auth/logout", headers=ORIGIN)
    _login(client, "1002")
    r = client.post(f"/api/questions/{question_id}/answer", json={"choice_id": 2}, headers=ORIGIN)
    assert r.status_code in (200, 201), r.get_json()
    client.post("/api/auth/logout", headers=ORIGIN)
    _login(client)


def test_answered_question_cannot_be_edited(client, seeded):
    """
    **القاعدة مشتقّة من ث-١٧ لا مُختَرعة:** `answers.correct` و
    `answers.point_event_id` لا يفترقان بقيدٍ في القاعدة، وقد كُتبا معًا لحظة
    الإجابة. فتغييرُ `correct_id` بعدها يجعل إجابةً صحيحةً تبدو خاطئة **وقد
    دُفعت ساعاتُها فعلًا** — تناقضٌ لا يُطلقه مشغّل ولا يراه أحد.

    @covers ق-٢٨٠
    """
    _as_admin(client, seeded)
    from app.models import Org
    from app.services.reading import local_today

    org = db.session.get(Org, seeded["org_id"])
    created = client.post(
        "/api/admin/questions",
        json={**BODY, "day": local_today(org).isoformat()},
        headers=ORIGIN,
    ).get_json()
    _answer_it(client, seeded, created["id"])

    r = client.patch(
        f"/api/admin/questions/{created['id']}",
        json={**{k: v for k, v in BODY.items() if k != "day"}, "correct_id": 1},
        headers=ORIGIN,
    )
    assert r.status_code == 409
    assert "أوّل إجابة" in r.get_json()["message"]

    # والصحيح لم يتغيّر فعلًا — لا رسالةُ رفضٍ على كتابةٍ وقعت.
    question = db.session.get(DailyQuestion, created["id"])
    assert question.correct_id == 2


def test_answered_question_cannot_be_deleted(client, seeded):
    """الحذف يتيّم أحداث الدفتر التي دفعتها الإجابة الصحيحة (ADR-004).

    @covers ق-٢٨٠
    """
    _as_admin(client, seeded)
    from app.models import Org
    from app.services.reading import local_today

    org = db.session.get(Org, seeded["org_id"])
    created = client.post(
        "/api/admin/questions",
        json={**BODY, "day": local_today(org).isoformat()},
        headers=ORIGIN,
    ).get_json()
    _answer_it(client, seeded, created["id"])

    assert client.delete(f"/api/admin/questions/{created['id']}", headers=ORIGIN).status_code == 409
    assert db.session.get(DailyQuestion, created["id"]) is not None
    assert db.session.scalar(select(db.func.count(Answer.id))) == 1


def test_unanswered_question_can_be_edited_and_deleted(client, seeded):
    """
    والحرس **ليس منعًا مطلقًا**: قبل أوّل إجابة لا أثر للسؤال في أيّ مكان —
    لا حدث دفتر ولا صفّ إجابة — فتصحيحُ خطأٍ مطبعيّ لا يحتاج يومًا جديدًا.

    @covers ق-٢٨٠
    """
    _as_admin(client, seeded)
    created = client.post("/api/admin/questions", json=BODY, headers=ORIGIN).get_json()

    body = {k: v for k, v in BODY.items() if k != "day"}
    patched = client.patch(
        f"/api/admin/questions/{created['id']}",
        json={**body, "prompt": "نصّ مُصحَّح"},
        headers=ORIGIN,
    )
    assert patched.status_code == 200, patched.get_json()
    assert db.session.get(DailyQuestion, created["id"]).prompt == "نصّ مُصحَّح"

    assert client.delete(f"/api/admin/questions/{created['id']}", headers=ORIGIN).status_code == 204
    assert db.session.get(DailyQuestion, created["id"]) is None


# ═══ ق-٢٨١ — القائمة والصلاحية ═══


def test_list_reports_the_answer_count_and_lock_state(client, seeded):
    """
    **`locked` حقلٌ من الخادم لا استنتاجٌ في الواجهة**: مقارنةٌ في الشاشة
    تُسقطها بوّابة AST، و«مُقفَل» قاعدةٌ (ث-١٧) لا عرض.

    @covers ق-٢٨١
    """
    _as_admin(client, seeded)
    from app.models import Org
    from app.services.reading import local_today

    org = db.session.get(Org, seeded["org_id"])
    created = client.post(
        "/api/admin/questions",
        json={**BODY, "day": local_today(org).isoformat()},
        headers=ORIGIN,
    ).get_json()

    before = client.get("/api/admin/questions", headers=ORIGIN).get_json()["questions"][0]
    assert before["answers"] == 0 and before["locked"] is False
    assert before["reward_hours"] == "1.00"

    _answer_it(client, seeded, created["id"])
    after = client.get("/api/admin/questions", headers=ORIGIN).get_json()["questions"][0]
    assert after["answers"] == 1 and after["locked"] is True


def test_questions_admin_is_closed_to_pilots(client, seeded):
    """`@admin_required` هو الحاكم — لا حرس الواجهة (`AGENTS.md` ٩).

    @covers ق-٢٨١
    """
    _login(client, "1002")
    assert client.get("/api/admin/questions", headers=ORIGIN).status_code == 403
    assert client.post("/api/admin/questions", json=BODY, headers=ORIGIN).status_code == 403


def test_negative_reward_is_refused(client, seeded):
    """ساعاتٌ سالبة على إجابةٍ صحيحة تطرح من رصيد الطالب — عقوبةٌ على الصواب.

    @covers ق-٢٨١
    """
    _as_admin(client, seeded)
    r = client.post("/api/admin/questions", json={**BODY, "reward_hours": "-1.00"}, headers=ORIGIN)
    assert r.status_code == 422


def test_create_writes_one_audit_line(client, seeded):
    """@covers ق-٢٨١"""
    _as_admin(client, seeded)
    client.post("/api/admin/questions", json=BODY, headers=ORIGIN)
    entries = client.get("/api/admin/audit", headers=ORIGIN).get_json()["entries"]
    kinds = [e["kind"] for e in entries]
    assert kinds.count("question_created") == 1


def test_reward_is_stored_as_decimal_not_float(client, seeded):
    """`Numeric(8,2)` — والعرض من الخادم نصًّا (`API.md §١`: لا `float`)."""
    _as_admin(client, seeded)
    created = client.post(
        "/api/admin/questions", json={**BODY, "reward_hours": "2.50"}, headers=ORIGIN
    ).get_json()
    assert db.session.get(DailyQuestion, created["id"]).reward_hours == Decimal("2.50")
