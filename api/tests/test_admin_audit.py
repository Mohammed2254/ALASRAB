"""
سجلّ التدقيق — و-٧ · FR-084. والمسار السالب الإلزامي لكل مسارات و-٧ السبعة.
"""

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Membership

ORIGIN = {"Origin": "http://localhost:5173"}


def _login(client, student_no="1001", pin="1234"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": pin}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


# ═══ ق-٦٠ — مفتوح لكل مشرف بلا حدّ team_id ═══


def test_admin_sees_actions_of_another_admin_in_a_different_team(client, seeded):
    """@covers ق-٦٠"""
    admin_a, admin_b = seeded["users"]["1001"], seeded["users"]["1002"]
    _make_admin(admin_a)
    _make_admin(admin_b)

    # المشرف ب ينشئ سربًا جديدًا وينقل نفسه إليه — فيصير في سرب مختلف عن أ.
    _login(client, "1002")
    other_team = client.post(
        "/api/admin/teams", json={"name": "سرب آخر", "code": "OTH"}, headers=ORIGIN
    ).json
    client.post(
        f"/api/admin/teams/{other_team['id']}/members", json={"user_id": admin_b}, headers=ORIGIN
    )
    client.post("/api/auth/logout", headers=ORIGIN)

    _login(client, "1001")
    entries = client.get("/api/admin/audit", headers=ORIGIN).json["entries"]
    kinds_by_admin_b = [
        e for e in entries if e["kind"] in ("team_created", "membership_transferred")
    ]
    assert len(kinds_by_admin_b) == 2
    assert all(e["actor_name"] for e in kinds_by_admin_b)


# ═══ ق-٦١ — الحالة الفارغة ═══


def test_org_with_no_changes_returns_empty_list_not_an_error(client, seeded):
    """@covers ق-٦١"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = client.get("/api/admin/audit", headers=ORIGIN)
    assert r.status_code == 200
    assert r.json["entries"] == []


def test_newest_entry_appears_first(client, seeded):
    """@covers ق-٦٠ — ترتيبٌ يخدم القراءة: الأحدث أوّلًا."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    client.post("/api/admin/teams", json={"name": "الأوّل", "code": "AAA"}, headers=ORIGIN)
    client.post("/api/admin/teams", json={"name": "الثاني", "code": "BBB"}, headers=ORIGIN)

    entries = client.get("/api/admin/audit", headers=ORIGIN).json["entries"]
    assert "الثاني" in entries[0]["summary"]


# ═══ ق-٦٢ — المسار السالب الإلزامي على كل مسارات و-٧ ═══

ENDPOINTS = [
    ("GET", "/api/admin/weights", None),
    ("POST", "/api/admin/weights", {}),
    ("GET", "/api/admin/thresholds", None),
    ("POST", "/api/admin/thresholds", {}),
    ("POST", "/api/admin/thresholds/preview", {}),
    ("GET", "/api/admin/teams", None),
    ("POST", "/api/admin/teams", {}),
    ("PATCH", "/api/admin/teams/1", {}),
    ("POST", "/api/admin/teams/1/members", {}),
    ("GET", "/api/admin/audit", None),
]


@pytest.mark.parametrize("method, path, body", ENDPOINTS)
def test_no_cookie_is_401(client, seeded, method, path, body):
    """@covers ق-٦٢"""
    kwargs = {"headers": ORIGIN}
    if body is not None:
        kwargs["json"] = body
    r = client.open(path, method=method, **kwargs)
    assert r.status_code == 401


@pytest.mark.parametrize("method, path, body", ENDPOINTS)
def test_pilot_is_403(client, seeded, method, path, body):
    """@covers ق-٦٢ — الشقّ الثاني: جلسة سارية بلا دور مشرف."""
    _login(client)  # 1001 طيار — لم يُرفَّع
    kwargs = {"headers": ORIGIN}
    if body is not None:
        kwargs["json"] = body
    r = client.open(path, method=method, **kwargs)
    assert r.status_code == 403
