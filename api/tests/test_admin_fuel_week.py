"""
أسبوع الوقود — و-٢٠ · النموذج المعتمد.

**بلا محاكاة:** كل اختبار يمرّ عبر المسارات الحقيقية، لا استدعاء الخدمة
مباشرةً — العقد هو ما يُختبَر.
"""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.extensions import db
from app.models import AuditEntry, FuelAssessment, Membership, Org, PointEvent

ORIGIN = {"Origin": "http://localhost:5173"}
WEEK = "/api/admin/fuel/week"


def _login(client, student_no="1001", pin="1234"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": pin}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _activity(client, key="act", litres_full="50"):
    client.post(
        "/api/admin/fuel/activities",
        json={
            "key": key,
            "name": "الحفظ الجماعي",
            "litres_full": litres_full,
            "criteria": [
                {"key": "a", "name": "الحضور", "weight_pct": "40"},
                {"key": "q", "name": "الجودة", "weight_pct": "60"},
            ],
        },
        headers=ORIGIN,
    )
    a = client.get("/api/admin/fuel/activities", headers=ORIGIN).json["activities"][-1]
    return a["id"], [c["id"] for c in a["criteria"]]


def _week_start(org_id, day: date) -> date:
    org = db.session.get(Org, org_id)
    return day - timedelta(days=(day.weekday() - org.week_starts_on) % 7)


def _setup(client, seeded):
    _make_admin(seeded["users"]["1001"])
    _login(client)
    return _activity(client)


# ═══ ق-٢٤٧ — العرض لا يكتب، والحالة معلَنة ═══


def test_unopened_week_shows_default_tasks_without_writing(client, seeded):
    """
    @covers ق-٢٤٧

    تصفّحُ أسبوعٍ ماضٍ لا يترك خلفه صفًّا لكل أسبوع مرّ به المشرف.
    """
    activity_id, _ = _setup(client, seeded)

    r = client.get(f"{WEEK}?week_start=2026-01-05", headers=ORIGIN)
    assert r.status_code == 200
    assert r.json["state"] == "unopened"
    assert [t["activity_id"] for t in r.json["tasks"]] == [activity_id]
    assert db.session.scalar(db.text("SELECT count(*) FROM fuel_weeks")) == 0


def test_week_start_is_normalised_not_taken_literally(client, seeded):
    """@covers ق-٢٤٧ — تاريخٌ وسط الأسبوع يعطي بدايته لا نفسه."""
    _setup(client, seeded)
    mid = date(2026, 1, 8)
    expected = _week_start(seeded["org_id"], mid)

    r = client.get(f"{WEEK}?week_start={mid.isoformat()}", headers=ORIGIN)
    assert r.json["week_start"] == expected.isoformat()


# ═══ ق-٢٤٨ — مسوّدةٌ بلا أثر في الدفتر ═══


def test_draft_scores_write_nothing_to_the_ledger(client, seeded):
    """
    @covers ق-٢٤٨

    الفارق الجوهريّ عن و-٨: التقييم لم يعد يكتب فورًا.
    """
    activity_id, crits = _setup(client, seeded)
    before = db.session.scalar(select(db.func.count(PointEvent.id)))

    client.post(
        f"{WEEK}/team",
        json={"activity_id": activity_id, "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )
    r = client.post(
        f"{WEEK}/scores",
        json={
            "activity_id": activity_id,
            "scores": [
                {"criterion_id": crits[0], "score_pct": "100"},
                {"criterion_id": crits[1], "score_pct": "50"},
            ],
        },
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert r.json["state"] == "draft"
    task = r.json["tasks"][0]
    assert task["assessed"] is True
    assert task["total_pct"] == "70.00"  # ١٠٠×٤٠٪ + ٥٠×٦٠٪
    assert task["litres"] == "35.00"  # ٧٠٪ من ٥٠

    assert db.session.scalar(select(db.func.count(PointEvent.id))) == before
    assert db.session.scalar(select(db.func.count(FuelAssessment.id))) == 0


# ═══ ق-٢٤٩ — الاعتماد يكتب مرّةً، وبتاريخ الأسبوع ═══


def test_approval_writes_events_dated_to_the_week_not_today(client, seeded):
    """
    @covers ق-٢٤٩

    **جوهر مطلب المستخدم:** التقييم قد يتأخّر، فيقيّم المشرف أسبوعًا مضى —
    ويجب أن تقع لتراته في ذلك الأسبوع لا في الحاضر، وإلّا تغيّر ترتيبٌ لم
    يصنعه أحد.
    """
    activity_id, crits = _setup(client, seeded)
    past = _week_start(seeded["org_id"], date(2026, 1, 5))
    qs = f"?week_start={past.isoformat()}"

    client.post(
        f"{WEEK}/team{qs}",
        json={"activity_id": activity_id, "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )
    client.post(
        f"{WEEK}/scores{qs}",
        json={
            "activity_id": activity_id,
            "scores": [
                {"criterion_id": crits[0], "score_pct": "100"},
                {"criterion_id": crits[1], "score_pct": "100"},
            ],
        },
        headers=ORIGIN,
    )

    r = client.post(f"{WEEK}/approve{qs}", headers=ORIGIN)
    assert r.status_code == 200
    assert r.json["state"] == "approved"

    event = db.session.scalar(select(PointEvent).where(PointEvent.kind == "fuel"))
    org = db.session.get(Org, seeded["org_id"])
    # بتوقيت المنظّمة لا بتوقيت الجهاز — الفارق يقلب التاريخ يومًا كاملًا.
    local_day = event.occurred_at.astimezone(ZoneInfo(org.timezone)).date()
    assert local_day == past, "الحدث يجب أن يقع في أسبوعه لا في الحاضر"
    assert event.delta == 50  # ١٠٠٪ من ٥٠ لترًا

    assessment = db.session.scalar(select(FuelAssessment))
    assert assessment.occurred_on == past
    assert assessment.point_event_id == event.id, "ق-٦٧: لا تقييم بلا حدث"


def test_approving_twice_is_refused_not_doubled(client, seeded):
    """@covers ق-٢٤٩ — الاعتماد إجراءٌ واحد لا رجعة فيه."""
    activity_id, crits = _setup(client, seeded)
    client.post(
        f"{WEEK}/team",
        json={"activity_id": activity_id, "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )
    client.post(
        f"{WEEK}/scores",
        json={
            "activity_id": activity_id,
            "scores": [
                {"criterion_id": crits[0], "score_pct": "100"},
                {"criterion_id": crits[1], "score_pct": "100"},
            ],
        },
        headers=ORIGIN,
    )
    assert client.post(f"{WEEK}/approve", headers=ORIGIN).status_code == 200
    assert client.post(f"{WEEK}/approve", headers=ORIGIN).status_code == 409
    assert db.session.scalar(select(db.func.count(PointEvent.id).filter())) >= 1
    assert db.session.scalar(select(db.func.count(FuelAssessment.id))) == 1


def test_approved_week_refuses_further_edits(client, seeded):
    """@covers ق-٢٤٩ — ما دخل الدفتر لا يُعدَّل (ADR-004)."""
    activity_id, crits = _setup(client, seeded)
    client.post(
        f"{WEEK}/team",
        json={"activity_id": activity_id, "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )
    client.post(
        f"{WEEK}/scores",
        json={
            "activity_id": activity_id,
            "scores": [
                {"criterion_id": crits[0], "score_pct": "100"},
                {"criterion_id": crits[1], "score_pct": "100"},
            ],
        },
        headers=ORIGIN,
    )
    client.post(f"{WEEK}/approve", headers=ORIGIN)

    r = client.post(
        f"{WEEK}/scores",
        json={"activity_id": activity_id, "scores": [{"criterion_id": crits[0], "score_pct": "10"}]},
        headers=ORIGIN,
    )
    assert r.status_code == 409


def test_task_without_team_or_scores_is_skipped_and_counted(client, seeded):
    """
    @covers ق-٢٤٩

    مهمّةٌ بلا سرب أو بلا درجات تُتخطّى — **ويُبلَّغ عددُها** فلا يُظنّ أنها
    احتُسبت.
    """
    activity_id, _ = _setup(client, seeded)
    # فُتح الأسبوع بتعيين سربٍ ثم أُزيل، فبقيت مهمّةٌ بلا درجات.
    client.post(
        f"{WEEK}/team",
        json={"activity_id": activity_id, "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )
    r = client.post(f"{WEEK}/approve", headers=ORIGIN)
    assert r.status_code == 200
    assert db.session.scalar(select(db.func.count(FuelAssessment.id))) == 0

    entry = db.session.scalar(
        select(AuditEntry).where(AuditEntry.kind == "fuel_week_approved")
    )
    assert entry.after["skipped"] == 1
    assert entry.after["assessments"] == 0


# ═══ ق-٢٥٠ — مهامُّ الأسبوع تُعدَّل لذلك الأسبوع وحده ═══


def test_removing_a_task_does_not_touch_another_week(client, seeded):
    """@covers ق-٢٥٠ — «بعض الأسابيع تختلف مهامها»."""
    activity_id, _ = _setup(client, seeded)
    past = _week_start(seeded["org_id"], date(2026, 1, 5))

    # يُفتح الأسبوعان ثم تُزال المهمّة من الماضي وحده.
    client.post(
        f"{WEEK}/team",
        json={"activity_id": activity_id, "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )
    client.post(
        f"{WEEK}/team?week_start={past.isoformat()}",
        json={"activity_id": activity_id, "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )

    r = client.delete(
        f"{WEEK}/tasks?week_start={past.isoformat()}",
        json={"activity_id": activity_id},
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert r.json["tasks"] == []

    current = client.get(WEEK, headers=ORIGIN).json
    assert [t["activity_id"] for t in current["tasks"]] == [activity_id]


def test_same_squad_may_take_two_tasks(client, seeded):
    """
    @covers ق-٢٥٠

    «لكل سرب مهمّة واحدة» **إرشادٌ لا قيد** (قرار المستخدم) — فلا يُرفض.
    """
    first_id, _ = _setup(client, seeded)
    second_id, _ = _activity(client, key="act2")

    a = client.post(
        f"{WEEK}/team",
        json={"activity_id": first_id, "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )
    b = client.post(
        f"{WEEK}/team",
        json={"activity_id": second_id, "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )
    assert a.status_code == 200
    assert b.status_code == 200
    assigned = [t["team_id"] for t in b.json["tasks"]]
    assert assigned == [seeded["team_id"], seeded["team_id"]]


def test_week_routes_require_admin(client, seeded):
    """@covers ق-٢٤٧ — الحارس الحقيقيّ في الخادم لا في الواجهة."""
    _login(client)  # طالبٌ لا مشرف
    assert client.get(WEEK, headers=ORIGIN).status_code == 403
    assert client.post(f"{WEEK}/approve", headers=ORIGIN).status_code == 403
