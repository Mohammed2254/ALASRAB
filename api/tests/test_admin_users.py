"""
إعادة تعيين PIN وسجلّ التدقيق — و-٢ · FR-004.

**أوّل كاتب في `audit_log`.** والفاعل هو المشرف لا الطالب: سجلٌّ ينسب الفعل
لضحيّته يقلب معنى التدقيق.
"""

from sqlalchemy import select

from app.extensions import db
from app.models import AuditEntry, Membership, Session, User
from app.security import COOKIE

ORIGIN = {"Origin": "http://localhost:5173"}
PIN = "1234"


def _login(client, student_no="1001", pin=PIN):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": pin}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _reset(client, user_id):
    return client.post(f"/api/admin/users/{user_id}/reset-pin", headers=ORIGIN)


# ═══ ق-٤٠ — رمز جديد يُعرض مرّة واحدة ═══


def test_reset_returns_new_pin_and_old_one_stops_working(client, seeded):
    """@covers ق-٤٠"""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin)
    _login(client)

    body = _reset(client, target).json
    assert body["student_no"] == "1002"
    assert len(body["pin"]) == 4 and body["pin"].isdigit()

    client.post("/api/auth/logout", headers=ORIGIN)
    # القديم لم يعد يعمل، والجديد يعمل.
    assert _login(client, "1002", PIN).status_code == 401
    assert _login(client, "1002", body["pin"]).status_code == 200


def test_new_pin_is_never_stored_in_plaintext(client, seeded):
    """
    @covers ق-٤٠ — لا في `users` ولا في `audit_log`.

    رمزٌ يُخزَّن نصًّا صريحًا يحوّل أي تسرّب لقاعدة البيانات إلى تسرّب حسابات.
    """
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin)
    _login(client)
    new_pin = _reset(client, target).json["pin"]

    assert db.session.get(User, target).pin_hash != new_pin
    assert db.session.get(User, target).pin_hash.startswith("$argon2")
    entry = db.session.scalar(select(AuditEntry))
    assert new_pin not in (entry.summary + str(entry.before) + str(entry.after))


# ═══ ق-٤١ — كل الجلسات تُبطَل ═══


def test_reset_revokes_every_session_of_the_target(client, seeded):
    """
    @covers ق-٤١

    سبب إعادة التعيين غالبًا **فقدان الجهاز**، وترك جلساته حيّة يُبطل الغرض.
    """
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]

    # جلستان للطالب من "جهازين".
    tokens = []
    for _ in range(2):
        raw = _login(client, "1002").headers["Set-Cookie"].split(f"{COOKIE}=")[1].split(";")[0]
        tokens.append(raw)
        client.post("/api/auth/logout", headers=ORIGIN)
        db.session.execute(db.text("UPDATE sessions SET revoked = false"))
        db.session.commit()

    _make_admin(admin)
    _login(client)
    _reset(client, target)

    assert db.session.scalars(select(Session.revoked)).all() != []
    for raw in tokens:
        client.set_cookie(COOKIE, raw)
        assert client.get("/api/auth/me").status_code == 401


def test_reset_does_not_touch_other_users_sessions(client, seeded):
    """@covers ق-٤١ — الحدّ الآخر: إبطالٌ يطال الجميع يُخرج الجمعية كلها."""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin)
    _login(client)
    _reset(client, target)

    # جلسة المشرف نفسه ما زالت صالحة.
    assert client.get("/api/auth/me").status_code == 200


# ═══ ق-٤٢ · ق-٤٣ — سطر التدقيق ═══


def test_audit_row_is_attributed_to_the_admin_not_the_student(client, seeded):
    """
    @covers ق-٤٢

    سجلٌّ ينسب الفعل لضحيّته يقلب معنى التدقيق — وهو التعويض الوحيد عن دمج
    الدورين (`SCOPE.md` §٣.٣).
    """
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin)
    _login(client)
    _reset(client, target)

    entry = db.session.scalar(select(AuditEntry))
    assert entry.kind == "pin_reset"
    assert entry.actor_id == admin
    assert entry.actor_id != target
    assert "1002" in entry.summary


def test_audit_row_carries_no_payload(client, seeded):
    """@covers ق-٤٣ — «يُسجَّل منسوبًا — **بلا قيمة الـPIN**» (§٧.٥)."""
    admin, target = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin)
    _login(client)
    _reset(client, target)

    entry = db.session.scalar(select(AuditEntry))
    assert entry.before is None
    assert entry.after is None


def test_failed_reset_writes_no_audit_row(client, seeded):
    """
    @covers ق-٤٢ — الفعل والتدقيق ذرّيّان: طالب مجهول ⇒ لا سطر.

    سطرُ تدقيقٍ لفعلٍ لم يقع أسوأ من غياب السجلّ: يجعل القارئ يبحث عمّا لم يحدث.
    """
    _make_admin(seeded["users"]["1001"])
    _login(client)
    assert _reset(client, 99999).status_code == 404
    assert db.session.scalars(select(AuditEntry)).all() == []


# ═══ ق-٤٤ — المسار السالب الإلزامي ═══


def test_reset_without_cookie_is_401(client, seeded):
    """@covers ق-٤٤ — الشقّ الأوّل."""
    assert _reset(client, seeded["users"]["1002"]).status_code == 401


def test_pilot_cannot_reset_anyones_pin(client, seeded):
    """
    @covers ق-٤٤ — الشقّ الثاني.

    بلاه يُصفّر أي طالبٍ رمزَ زميله فيُخرجه من حسابه.
    """
    _login(client)
    assert _reset(client, seeded["users"]["1002"]).status_code == 403
    assert db.session.scalars(select(AuditEntry)).all() == []


def test_unknown_user_is_404(client, seeded):
    """@covers ق-٤٤ — الشقّ الثالث."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    assert _reset(client, 99999).status_code == 404


def test_user_from_another_org_is_404_not_403(client, seeded):
    """
    @covers ق-٤٤ — رسالة واحدة لغير الموجود وللخارج عن المنظمة.

    التفريق يكشف **وجود** مستخدمين في منظمات أخرى — نفس علّة الرسالة الواحدة
    في شاشة الدخول.
    """
    from app.models import Org

    other = Org(name="جمعية أخرى")
    db.session.add(other)
    db.session.flush()
    outsider = User(org_id=other.id, full_name="غريب", student_no="9001", pin_hash="x")
    db.session.add(outsider)
    db.session.commit()

    _make_admin(seeded["users"]["1001"])
    _login(client)
    assert _reset(client, outsider.id).status_code == 404
