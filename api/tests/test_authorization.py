"""
التخويل — ARCHITECTURE §٧.٣: `role='admin'` صلاحية **على مستوى الجمعية**.

هذه الاختبارات تحرس نصًّا ملزمًا: لا يجوز لأي كود لاحق أن يفترض أن
`memberships.team_id` يحدّ ما يراه المشرف.
"""

from flask import g

from app.extensions import db
from app.models import Membership, Team
from app.security import admin_required, login_required, role_of

ORIGIN = {"Origin": "http://localhost:5173"}
CREDS = {"student_no": "1001", "pin": "1234"}


def _make_admin(user_id):
    m = db.session.scalar(db.select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _guarded_routes(app):
    """مساران مؤقّتان للاختبار: الحرّاس تُختبر عبر Flask حقيقي لا باستدعاء مباشر."""

    @app.get("/t/user")
    @login_required
    def _u():
        return {"role": role_of(g.membership), "team_id": g.membership.team_id}

    @app.get("/t/admin")
    @admin_required
    def _a():
        return {"ok": True}


# ═══ الحارس يفرّق بين الدورين ═══


def test_pilot_is_refused_admin_route(client, seeded, app):
    _guarded_routes(app)
    client.post("/api/auth/login", json=CREDS, headers=ORIGIN)
    assert client.get("/t/user").status_code == 200
    assert client.get("/t/admin").status_code == 403


def test_admin_passes_admin_route(client, seeded, app):
    _guarded_routes(app)
    _make_admin(seeded["users"]["1001"])
    client.post("/api/auth/login", json=CREDS, headers=ORIGIN)
    assert client.get("/t/admin").status_code == 200


def test_anonymous_gets_401_not_403(client, seeded, app):
    """التمييز مقصود: ٤٠١ «من أنت؟» و٤٠٣ «أعرفك ولا يحقّ لك»."""
    _guarded_routes(app)
    assert client.get("/t/admin").status_code == 401


# ═══ §٧.٣ — الصلاحية على مستوى الجمعية لا السرب ═══


def test_admin_scope_is_org_wide_not_team_bound(client, seeded, app):
    """
    مشرفُ سربٍ **أ** يبقى مشرفًا بعد نقله إلى سربٍ **ب**: الصلاحية لا تُقيَّد
    بالسرب. لو انقلب هذا يومًا لكان اللصق من راصد — وهو يأتي لكل الطلاب دفعة
    واحدة — مستحيلًا.
    """
    _guarded_routes(app)
    _make_admin(seeded["users"]["1001"])
    other = Team(org_id=seeded["org_id"], name="سرب آخر", code="OTH")
    db.session.add(other)
    db.session.flush()
    m = db.session.scalar(
        db.select(Membership).where(Membership.user_id == seeded["users"]["1001"])
    )
    m.team_id = other.id
    db.session.commit()

    client.post("/api/auth/login", json=CREDS, headers=ORIGIN)
    assert client.get("/t/admin").status_code == 200
    assert client.get("/t/user").json["team_id"] == other.id


def test_role_lives_on_membership_not_on_user(client, seeded):
    """
    فحص المخطط: عمود `role` في `memberships` لا في `users` — وهو ما يسمح لشخص
    أن يكون مشرفًا في منظمة ومستخدمًا في أخرى بلا تغيير في المخطط.
    """
    cols = (
        db.session.execute(
            db.text(
                "SELECT table_name FROM information_schema.columns "
                "WHERE column_name='role' AND table_schema='public'"
            )
        )
        .scalars()
        .all()
    )
    assert cols == ["memberships"]


# ═══ الفشل مُغلق عند غياب العضوية ═══


def test_user_without_membership_can_still_see_own_identity(client, seeded, app):
    """
    طالبٌ نُقل فبقي لحظةً بلا عضوية يرى بطاقته — `SCOPE.md` ط-٢ يوجب أن تكون
    الحالة الناقصة **مصمَّمة لا مكسورة**، وقفلُه خارج حسابه أشدّ كسرًا.
    """
    db.session.execute(db.text("DELETE FROM memberships"))
    db.session.commit()
    client.post("/api/auth/login", json=CREDS, headers=ORIGIN)
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json["user"]["role"] == "pilot"  # أقلّ الأدوار صلاحيةً


def test_user_without_membership_is_never_admin(client, seeded, app):
    """الفشل مُغلق: غياب المعلومة **يمنع** لا يسمح."""
    _guarded_routes(app)
    _make_admin(seeded["users"]["1001"])
    client.post("/api/auth/login", json=CREDS, headers=ORIGIN)
    assert client.get("/t/admin").status_code == 200

    db.session.execute(db.text("UPDATE memberships SET left_at = now()"))
    db.session.commit()
    assert client.get("/t/admin").status_code == 403


def test_expired_membership_is_ignored(client, seeded, app):
    """`membership_of` يقرأ العضوية السارية وحدها — `left_at IS NULL`."""
    _guarded_routes(app)
    db.session.execute(db.text("UPDATE memberships SET left_at = now(), role='admin'"))
    db.session.commit()
    client.post("/api/auth/login", json=CREDS, headers=ORIGIN)
    assert client.get("/t/admin").status_code == 403
