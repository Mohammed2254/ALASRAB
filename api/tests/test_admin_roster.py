"""
سجلّ الطلاب — و-٢١.

**لا بند `SCOPE.md` لإنشاء طالب**: فيه `FR-004` (إعادة تعيين رمز) و`FR-083`
(إدارة الأسراب والعضويات)، وفُرض أن الطلاب موجودون سلفًا. هذا الملفّ يحرس
المسار الذي أُضيف ليُجيب «من أين؟».

@covers ق-٢٦٨, ق-٢٦٩, ق-٢٧٠, ق-٢٧١, ق-٢٧٢
"""

from sqlalchemy import select

from app.extensions import db
from app.models import AuditEntry, Membership, Session, User

ORIGIN = {"Origin": "http://localhost:5173"}


def _login(client, student_no="1001", pin="1234"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": pin}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _as_admin(client, seeded):
    _make_admin(seeded["users"]["1001"])
    _login(client)


# ═══ ق-٢٦٨ — الإنشاء يُنتج طالبًا يدخل فعلًا ═══


def test_created_student_can_log_in_with_the_issued_pin(client, seeded):
    """
    **الفحص ليس وجود الصفّ بل الدخول.** طالبٌ مُنشأ لا يدخل هو شاشةُ إدارةٍ
    تُنتج أسماءً لا مستخدمين.

    @covers ق-٢٦٨
    """
    _as_admin(client, seeded)

    r = client.post(
        "/api/admin/users",
        json={"full_name": "طالب جديد", "student_no": "2001", "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )
    assert r.status_code == 201, r.get_json()
    pin = r.get_json()["pin"]
    assert len(pin) == 4 and pin.isdigit()

    client.post("/api/auth/logout", headers=ORIGIN)
    assert _login(client, "2001", pin).status_code == 200


def test_issued_pin_is_never_returned_by_a_read(client, seeded):
    """
    الرمز في **ردّ الإنشاء وحده**. ظهورُه في `GET` يحوّل أيّ XSS أو لقطةَ
    شاشةٍ إلى تسريب حسابات — ولذلك `RosterRowSchema` بلا حقل رمز بالبناء.

    @covers ق-٢٦٨
    """
    _as_admin(client, seeded)
    client.post(
        "/api/admin/users",
        json={"full_name": "طالب جديد", "student_no": "2001", "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )

    rows = client.get("/api/admin/users", headers=ORIGIN).get_json()["students"]
    assert rows and all("pin" not in row for row in rows)


def test_audit_line_carries_no_pin(client, seeded):
    """سطرُ تدقيقٍ يحمل الرمز يحوّل السجلّ نفسه إلى تسريب (§٧.٥)."""
    _as_admin(client, seeded)
    pin = client.post(
        "/api/admin/users",
        json={"full_name": "طالب جديد", "student_no": "2001", "team_id": seeded["team_id"]},
        headers=ORIGIN,
    ).get_json()["pin"]

    entry = db.session.scalar(select(AuditEntry).where(AuditEntry.kind == "user_created"))
    assert entry is not None
    assert pin not in entry.summary
    assert pin not in str(entry.after)


def test_duplicate_student_no_is_refused(client, seeded):
    """
    `1001` مستعمل في `seeded` — والقيد `uq_user_student_no` هو الضمانة.

    @covers ق-٢٦٩
    """
    _as_admin(client, seeded)
    r = client.post(
        "/api/admin/users",
        json={"full_name": "مكرَّر", "student_no": "1001", "team_id": seeded["team_id"]},
        headers=ORIGIN,
    )
    assert r.status_code == 409


# ═══ ق-٢٦٩ — اللصقة الجماعية ═══


def test_bulk_reports_the_failing_row_without_dropping_the_good_ones(client, seeded):
    """
    **هذا هو السلوك المقصود، لا تساهلًا:** لصقةٌ تُرفض كلّها لأن رقمًا واحدًا
    مكرَّر تُجبر المشرف على تفتيش مئتَي سطرٍ بعينه — وهو ما يدفعه إلى تركها
    (خ-١: تأجيل الإدخال). نفس سابقة استيراد راصد: التكرار يُستبعَد ولا تُرفض
    الدفعة.

    @covers ق-٢٦٩
    """
    _as_admin(client, seeded)

    r = client.post(
        "/api/admin/users/bulk",
        json={
            "team_id": seeded["team_id"],
            "rows": [
                {"full_name": "أوّل", "student_no": "3001"},
                {"full_name": "مكرَّر", "student_no": "1001"},  # مستعمل في `seeded`
                {"full_name": "ثالث", "student_no": "3003"},
            ],
        },
        headers=ORIGIN,
    )
    assert r.status_code == 201, r.get_json()
    body = r.get_json()

    assert [c["student_no"] for c in body["created"]] == ["3001", "3003"]
    assert [f["line"] for f in body["failed"]] == [2]

    # والناجحان **محفوظان فعلًا** — لا رِدّ تقرير نجاحٍ على معاملةٍ ارتدّت.
    assert db.session.scalar(select(User).where(User.student_no == "3001")) is not None
    assert db.session.scalar(select(User).where(User.student_no == "3003")) is not None


def test_bulk_issues_a_distinct_pin_per_student(client, seeded):
    """رمزٌ واحدٌ لمئتَي طالب يُنشَر بينهم في يوم."""
    _as_admin(client, seeded)
    body = client.post(
        "/api/admin/users/bulk",
        json={
            "team_id": seeded["team_id"],
            "rows": [{"full_name": f"طالب {i}", "student_no": f"40{i:02d}"} for i in range(10)],
        },
        headers=ORIGIN,
    ).get_json()

    assert len(body["created"]) == 10
    assert len({c["pin"] for c in body["created"]}) > 1


# ═══ ق-٢٧٠ — التعطيل لا الحذف ═══


def test_deactivation_hides_the_student_without_deleting_history(client, seeded):
    """
    حذف الطالب يتيّم أحداثه في الدفتر (ADR-004)، و`is_active` مُرشَّح في كل
    مسار قراءة — فالعلم يكفي، والصفّ يبقى.

    @covers ق-٢٧٠
    """
    _as_admin(client, seeded)
    target = seeded["users"]["1002"]

    r = client.patch(f"/api/admin/users/{target}/active", json={"active": False}, headers=ORIGIN)
    assert r.status_code == 200
    assert r.get_json()["is_active"] is False

    user = db.session.get(User, target)
    assert user is not None  # لا حذف
    # والعضوية تبقى سارية: التعطيل علمٌ واحد، فإعادة التفعيل لا تحتاج سربًا.
    membership = db.session.scalar(
        select(Membership).where(Membership.user_id == target, Membership.left_at.is_(None))
    )
    assert membership is not None


def test_deactivated_student_cannot_log_in(client, seeded):
    """علمٌ لا يمنع الدخول ليس تعطيلًا."""
    _as_admin(client, seeded)
    client.patch(
        f"/api/admin/users/{seeded['users']['1002']}/active",
        json={"active": False},
        headers=ORIGIN,
    )
    client.post("/api/auth/logout", headers=ORIGIN)

    assert _login(client, "1002").status_code == 401


def test_deactivation_revokes_live_sessions(client, seeded):
    """
    **الكوكي عمرُه تسعون يومًا.** علمٌ يمنع الدخول الجديد ويترك جلسةً حيّة
    يعني أن المعطَّل يبقى داخلًا ثلاثة أشهر.

    @covers ق-٢٧٠
    """
    target = seeded["users"]["1002"]
    _login(client, "1002")  # جلسة الطالب نفسه

    # **الصفّ يبقى والعلم يُرفع** (`revoked`) لا يُحذَف: حذفُ الجلسة يمحو
    # أثرَ وجودها، والعدّ هنا على غير المُبطَلة لا على الصفوف.
    live = select(db.func.count(Session.id)).where(
        Session.user_id == target, Session.revoked.is_(False)
    )
    assert db.session.scalar(live) == 1

    _as_admin(client, seeded)
    client.patch(f"/api/admin/users/{target}/active", json={"active": False}, headers=ORIGIN)

    assert db.session.scalar(live) == 0


def test_reactivation_restores_login(client, seeded):
    """التعطيل قرارٌ قابل للنقض — بخلاف أرشفة السرب (م-١٠)، فالخطأ البشريّ وارد."""
    _as_admin(client, seeded)
    target = seeded["users"]["1002"]
    client.patch(f"/api/admin/users/{target}/active", json={"active": False}, headers=ORIGIN)
    client.patch(f"/api/admin/users/{target}/active", json={"active": True}, headers=ORIGIN)
    client.post("/api/auth/logout", headers=ORIGIN)

    assert _login(client, "1002").status_code == 200


# ═══ ق-٢٧١ — آخر مشرف ═══


def test_last_admin_cannot_be_demoted(client, seeded):
    """
    **الحائل الوحيد بين خطأٍ وقفلٍ دائم:** جمعيةٌ بلا مشرف لا يفتحها أحد، ولا
    مسار في المنصّة يُعيد إنشاء واحد — `flask bootstrap-org` يعمل على قاعدةٍ
    فارغة وحدها، فالتعافي يحتاج طرفية الخادم وSQL يدويًّا.

    @covers ق-٢٧١
    """
    _as_admin(client, seeded)
    r = client.patch(
        f"/api/admin/users/{seeded['users']['1001']}/role",
        json={"role": "pilot"},
        headers=ORIGIN,
    )
    assert r.status_code == 422
    assert "آخر مشرف" in r.get_json()["message"]


def test_last_admin_cannot_be_deactivated(client, seeded):
    """نفس القفل من بابٍ آخر — ومسارٌ محروسٌ وآخرُ مفتوح حرسٌ لا يحرس.

    @covers ق-٢٧١
    """
    _as_admin(client, seeded)
    r = client.patch(
        f"/api/admin/users/{seeded['users']['1001']}/active",
        json={"active": False},
        headers=ORIGIN,
    )
    assert r.status_code == 422


def test_admin_can_be_demoted_once_another_exists(client, seeded):
    """والحرس **ليس منعًا مطلقًا**: مشرفان فأحدهما قابل للتنزيل.

    @covers ق-٢٧١
    """
    _as_admin(client, seeded)
    second = seeded["users"]["1002"]
    assert (
        client.patch(
            f"/api/admin/users/{second}/role", json={"role": "admin"}, headers=ORIGIN
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/admin/users/{seeded['users']['1001']}/role",
            json={"role": "pilot"},
            headers=ORIGIN,
        ).status_code
        == 200
    )


# ═══ ق-٢٧٢ — النطاق والصلاحية ═══


def test_roster_is_closed_to_pilots(client, seeded):
    """`@admin_required` هو الحاكم — لا حرس الواجهة (`AGENTS.md` ٩)."""
    _login(client, "1002")
    assert client.get("/api/admin/users", headers=ORIGIN).status_code == 403
    assert (
        client.post(
            "/api/admin/users",
            json={"full_name": "x", "student_no": "9", "team_id": seeded["team_id"]},
            headers=ORIGIN,
        ).status_code
        == 403
    )


def test_roster_shows_deactivated_students(client, seeded):
    """
    مشرفٌ لا يرى المعطَّل لا يستطيع إعادة تفعيله، فيُعيد إنشاءه برقمٍ آخر
    ويتشظّى تاريخه بين حسابين.

    @covers ق-٢٧٢
    """
    _as_admin(client, seeded)
    target = seeded["users"]["1002"]
    client.patch(f"/api/admin/users/{target}/active", json={"active": False}, headers=ORIGIN)

    rows = client.get("/api/admin/users", headers=ORIGIN).get_json()["students"]
    row = next(r for r in rows if r["id"] == target)
    assert row["is_active"] is False


def test_creation_into_archived_team_is_refused(client, seeded):
    """لا عضوية جديدة في سرب مؤرشَف — نفس قاعدة `transfer_member` (م-١٠)."""
    _as_admin(client, seeded)

    # **سربٌ فارغ:** أرشفة سربٍ مأهول مرفوضة أصلًا (م-١٠)، فأرشفةُ سرب
    # `seeded` تفشل صامتًا ويمرّ الاختبار على سربٍ حيّ — فحصٌ أعمى.
    empty_team = client.post(
        "/api/admin/teams", json={"name": "سرب فارغ", "code": "EMP"}, headers=ORIGIN
    ).get_json()["id"]
    archived = client.patch(
        f"/api/admin/teams/{empty_team}", json={"archived": True}, headers=ORIGIN
    )
    assert archived.status_code == 200, archived.get_json()

    r = client.post(
        "/api/admin/users",
        json={"full_name": "طالب", "student_no": "5001", "team_id": empty_team},
        headers=ORIGIN,
    )
    assert r.status_code == 422
