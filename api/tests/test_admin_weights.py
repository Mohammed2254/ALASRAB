"""
إصدارات الأوزان — و-٧ · FR-081.

**بلا محاكاة:** كل اختبار يمرّ عبر `POST /admin/weights` الحقيقي، لا استدعاء
`services/rules_admin` مباشرةً — العقد هو ما يُختبَر.
"""

from sqlalchemy import select

from app.extensions import db
from app.models import AuditEntry, Membership

ORIGIN = {"Origin": "http://localhost:5173"}


def _login(client, student_no="1001", pin="1234"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": pin}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _create(client, effective_from, weights, multipliers=None, note=None):
    return client.post(
        "/api/admin/weights",
        json={
            "effective_from": effective_from,
            "note": note,
            "weights": [
                {"activity_type": k, "hours_per_unit": str(v)} for k, v in weights.items()
            ],
            "multipliers": [
                {"grade": k, "multiplier": str(v)} for k, v in (multipliers or {}).items()
            ],
        },
        headers=ORIGIN,
    )


FULL_SET = {"memorize": "2.8", "quran_progress": "0.25", "reading": "0.18"}


# ═══ ق-٤٦ — إصدار جديد لا تعديل ═══


def test_create_version_appears_as_current_and_old_stays_in_history(client, seeded):
    """@covers ق-٤٦"""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _create(client, "2026-09-15", FULL_SET)
    assert r.status_code == 201
    new_id = r.json["id"]

    body = client.get("/api/admin/weights", headers=ORIGIN).json
    assert body["current"]["id"] == new_id
    assert {w["activity_type"] for w in body["current"]["weights"]} == set(FULL_SET)
    history_ids = {v["id"] for v in body["history"]}
    assert seeded["versions"]["new"] in history_ids
    assert seeded["versions"]["old"] in history_ids


def test_old_version_rows_are_untouched(client, seeded):
    """@covers ق-٤٦ — الحدّ الآخر: الإصدار القديم لم يُعدَّل حرفًا."""
    from app.models import Weight

    before = {
        w.activity_type: w.hours_per_unit
        for w in db.session.scalars(
            select(Weight).where(Weight.version_id == seeded["versions"]["new"])
        )
    }

    _make_admin(seeded["users"]["1001"])
    _login(client)
    _create(client, "2026-09-15", FULL_SET)

    after = {
        w.activity_type: w.hours_per_unit
        for w in db.session.scalars(
            select(Weight).where(Weight.version_id == seeded["versions"]["new"])
        )
    }
    assert before == after


# ═══ ق-٤٧ — effective_from يلي آخر إصدار ═══


def test_effective_from_before_latest_version_is_rejected(client, seeded):
    """@covers ق-٤٧"""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _create(client, "2020-01-01", FULL_SET)  # قبل الإصدار "old" و"new" معًا
    assert r.status_code == 422


def test_effective_from_equal_to_latest_is_rejected(client, seeded):
    """@covers ق-٤٧ — الحدّ شامل: التساوي مرفوض لا مقبول (يلبس أيّهما ساري)."""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _create(client, "2026-06-01", FULL_SET)  # نفس تاريخ الإصدار "new"
    assert r.status_code == 422


def test_effective_from_after_latest_is_accepted(client, seeded):
    """@covers ق-٤٧ — الحدّ الآخر: القيد ليس مفرطًا."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    assert _create(client, "2026-09-15", FULL_SET).status_code == 201


# ═══ ق-٤٨ — لا نشاط يُسقَط ═══


def test_dropping_a_previously_priced_activity_is_rejected(client, seeded):
    """@covers ق-٤٨ — «reading» كان له وزن في الإصدار الحالي وغاب هنا."""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _create(client, "2026-09-15", {"memorize": "2.8", "quran_progress": "0.25"})
    assert r.status_code == 422
    assert "reading" in r.json["message"]


def test_new_activity_not_priced_before_is_fine(client, seeded):
    """@covers ق-٤٨ — الحدّ الآخر: إضافة نشاط جديد لا تُرفض، فقط إسقاط قائم."""
    r_weights = dict(FULL_SET, attendance="3.0")
    _make_admin(seeded["users"]["1001"])
    _login(client)
    assert _create(client, "2026-09-15", r_weights).status_code == 201


# ═══ ق-٤٩ — سطر التدقيق ═══


def test_new_version_is_audited(client, seeded):
    """@covers ق-٤٩"""
    admin = seeded["users"]["1001"]
    _make_admin(admin)
    _login(client)
    r = _create(client, "2026-09-15", FULL_SET)

    entry = db.session.scalar(select(AuditEntry))
    assert entry.kind == "weights_version"
    assert entry.actor_id == admin
    assert entry.after["version_id"] == r.json["id"]


def test_failed_creation_writes_no_audit_row(client, seeded):
    """@covers ق-٤٩ — الفعل والتدقيق ذرّيّان."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    _create(client, "2020-01-01", FULL_SET)  # يُرفض — ق-٤٧
    assert db.session.scalars(select(AuditEntry)).all() == []


# ═══ ق-٢٤٠ — الصفر مشروع والسالب مرفوض (و-٢٠) ═══


def test_zero_weight_is_accepted_and_disables_the_activity(client, seeded):
    """
    @covers ق-٢٤٠

    تعطيل نشاطٍ يكون **بوزنه لا بحذفه** — قرار المستخدم في و-٢٠: «نخلي
    الحضور ماله قيمة ونضربه بصفر». فالصفر قيمةٌ صالحة لا خطأ إدخال.
    """
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _create(client, "2026-09-15", {**FULL_SET, "attendance": "0"})
    assert r.status_code == 201

    body = client.get("/api/admin/weights", headers=ORIGIN).json
    rows = {w["activity_type"]: w["hours_per_unit"] for w in body["current"]["weights"]}
    assert rows["attendance"] == "0.0000"


def test_negative_weight_is_rejected(client, seeded):
    """
    @covers ق-٢٤٠

    كان يُقبل بلا مُصادِق إطلاقًا — فوزنٌ سالب يطرح ساعاتٍ من كل استيراد
    راصد صامتًا، وهو عكس المقصود من «تعطيل نشاط».
    """
    _make_admin(seeded["users"]["1001"])
    _login(client)

    before = client.get("/api/admin/weights", headers=ORIGIN).json["current"]["id"]
    assert _create(client, "2026-09-15", {**FULL_SET, "attendance": "-1"}).status_code == 422
    # ولا إصدار جديد يُكتب — الرفض في المخطَّط قبل الخدمة، فالسارية لم تتغيّر.
    assert client.get("/api/admin/weights", headers=ORIGIN).json["current"]["id"] == before


def test_negative_multiplier_is_rejected(client, seeded):
    """@covers ق-٢٤٠ — نفس الثغرة في المضاعفات."""
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _create(client, "2026-09-15", FULL_SET, multipliers={"mastered": "-1.5"})
    assert r.status_code == 422
