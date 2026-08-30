"""
المصادقة — سلوكيًّا عبر تطبيق Flask حقيقي وقاعدة حقيقية.

**لا محاكاة:** الاختبار الذي يستبدل `session_for` بدالّة وهمية يثبت أن الاختبار
كُتب، لا أن الجلسة تُفحص من القاعدة. وهذا الفرق هو ADR-003 كلّه.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.extensions import db
from app.models import LoginAttempt, Session
from app.security import COOKIE

ORIGIN = {"Origin": "http://localhost:5173"}
PIN = "1234"
LOGIN = "/api/auth/login"


def _login(client, student_no="1001", pin=PIN):
    return client.post(LOGIN, json={"student_no": student_no, "pin": pin}, headers=ORIGIN)


def _cookie(response):
    return response.headers.get("Set-Cookie", "")


# ═══ ق-١ — الدخول ينشئ جلسة صالحة ═══


def test_correct_credentials_return_user_and_set_cookie(client, seeded):
    r = _login(client)
    assert r.status_code == 200
    # الردّ معشَّش تحت user كما في API.md §٣ — لا مسطّح.
    assert r.json["user"]["student_no"] == "1001"
    assert r.json["user"]["role"] == "pilot"
    assert COOKIE in _cookie(r)


def test_login_creates_exactly_one_session_row(client, seeded):
    _login(client)
    assert db.session.scalar(select(db.func.count(Session.id))) == 1


def test_response_never_leaks_the_pin_or_its_hash(client, seeded):
    """الرصد الوحيد الممكن هنا هو تسريب لا يُلاحَظ إلا بالبحث عنه صراحةً."""
    body = _login(client).get_data(as_text=True)
    assert PIN not in body
    assert "pin" not in body.lower()


# ═══ ق-٢ — لا تعداد: نفس الرمز ونفس الرسالة ═══


def test_unknown_student_and_wrong_pin_are_indistinguishable(client, seeded):
    """
    التفريق بين «رقم غير موجود» و«رمز خاطئ» يحوّل الشاشة إلى أداة تعداد للطلاب.
    المقارنة هنا **حرفية**: رمز الحالة والرسالة معًا.
    """
    unknown = client.post(LOGIN, json={"student_no": "9999", "pin": PIN}, headers=ORIGIN)
    wrong_pin = client.post(LOGIN, json={"student_no": "1001", "pin": "0000"}, headers=ORIGIN)

    assert unknown.status_code == wrong_pin.status_code == 401
    assert unknown.json["message"] == wrong_pin.json["message"]
    assert unknown.json == wrong_pin.json


def test_failed_login_sets_no_cookie(client, seeded):
    assert COOKIE not in _cookie(
        client.post(LOGIN, json={"student_no": "1001", "pin": "0000"}, headers=ORIGIN)
    )


def test_inactive_user_cannot_log_in(client, seeded):
    from app.models import User

    db.session.get(User, seeded["users"]["1001"]).is_active = False
    db.session.commit()
    assert _login(client).status_code == 401


# ═══ التوكن لا يُخزَّن نصًّا صريحًا ═══


def test_token_is_stored_hashed_not_plaintext(client, seeded):
    """
    تسرّب القاعدة يجب أن يكشف الهاش لا التوكن، فلا ينتحل أحد جلسة قائمة.

    نستخرج التوكن من الكوكي الفعلي ونؤكّد أنه **لا يظهر في أي صفّ**، وأن
    المخزَّن هو SHA-256 له.
    """
    import hashlib

    raw = _login(client).headers["Set-Cookie"].split(f"{COOKIE}=")[1].split(";")[0]
    stored = db.session.scalar(select(Session.token_hash))

    assert stored != raw
    assert len(stored) == 64  # SHA-256 hex
    assert stored == hashlib.sha256(raw.encode()).hexdigest()


# ═══ ق-٣ — الحارس ═══


def test_me_without_cookie_is_401(client, seeded):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_garbage_cookie_is_401(client, seeded):
    client.set_cookie(COOKIE, "not-a-real-token")
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_valid_session_returns_identity(client, seeded):
    _login(client)
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json["user"]["full_name"] == "طالب أول"


def test_session_lookup_hits_the_database(client, seeded):
    """
    جوهر ADR-003: الجلسة صفٌّ يُقرأ، لا توقيعٌ يُفكّ. حذف الصفّ من القاعدة
    مباشرةً يجب أن يُبطل الكوكي فورًا — وهو ما يستحيل مع JWT.
    """
    _login(client)
    assert client.get("/api/auth/me").status_code == 200
    db.session.execute(db.text("DELETE FROM sessions"))
    db.session.commit()
    assert client.get("/api/auth/me").status_code == 401


# ═══ ق-٩ — الخروج يُبطل في القاعدة ═══


def test_logout_revokes_the_session_row(client, seeded):
    _login(client)
    client.post("/api/auth/logout", headers=ORIGIN)
    assert db.session.scalar(select(Session.revoked)) is True


def test_same_cookie_is_rejected_after_logout(client, seeded):
    """
    **لو نجح هذا الطلب لكانت الجلسة ليست في القاعدة.** نعيد ضبط الكوكي يدويًّا
    بعد الخروج لأن العميل يحذفه — والمهاجم لا يحذفه.
    """
    raw = _login(client).headers["Set-Cookie"].split(f"{COOKIE}=")[1].split(";")[0]
    client.post("/api/auth/logout", headers=ORIGIN)

    client.set_cookie(COOKIE, raw)
    assert client.get("/api/auth/me").status_code == 401


def test_logout_without_session_succeeds_quietly(client, seeded):
    """بلا حارس عمدًا: ٤٠١ هنا يَعلق بالمستخدم في شاشة لا يخرج منها."""
    assert client.post("/api/auth/logout", headers=ORIGIN).status_code == 204


# ═══ انتهاء الصلاحية ═══


def test_expired_session_is_rejected(client, seeded):
    _login(client)
    s = db.session.scalar(select(Session))
    s.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.session.commit()
    assert client.get("/api/auth/me").status_code == 401


# ═══ FR-003 — القفل ═══


def test_lockout_after_five_failures(client, seeded):
    for _ in range(5):
        client.post(LOGIN, json={"student_no": "1001", "pin": "0000"}, headers=ORIGIN)

    r = _login(client)  # الرمز الصحيح — ومع ذلك يُرفض
    assert r.status_code == 429
    assert "١٥" in r.json["message"] or "15" in r.json["message"]


def test_lockout_counts_only_recent_failures(client, seeded):
    """محاولات قديمة لا تقفل الحساب اليوم — وإلا صار القفل دائمًا لا مؤقّتًا."""
    old = datetime.now(UTC) - timedelta(minutes=30)
    for _ in range(5):
        db.session.add(LoginAttempt(org_id=seeded["org_id"], student_no="1001", ok=False, at=old))
    db.session.commit()
    assert _login(client).status_code == 200


def test_lockout_is_per_student_not_global(client, seeded):
    """قفل طالبٍ لا يقفل زميله — وإلا صار تعطيل المنصة كلها بخمس محاولات."""
    for _ in range(5):
        client.post(LOGIN, json={"student_no": "1001", "pin": "0000"}, headers=ORIGIN)
    assert _login(client, student_no="1002").status_code == 200


def test_every_attempt_is_recorded(client, seeded):
    client.post(LOGIN, json={"student_no": "1001", "pin": "0000"}, headers=ORIGIN)
    _login(client)
    rows = db.session.scalars(select(LoginAttempt.ok)).all()
    assert rows == [False, True]


# ═══ §٧.٣ — لا org_id من العميل ═══


def test_client_supplied_org_id_is_rejected_loudly(client, seeded):
    """
    `LoginSchema` لا يعلن `org_id`، وMarshmallow يرفض المجهول افتراضيًّا ⇒ ٤٢٢.

    الرفض الصاخب **أفضل من التجاهل الصامت**: محاولة حقن حقل تظهر في السجلّ بدل
    أن تمرّ بلا أثر. والضمانة الأمنية قائمة في الحالتين — الخادم لا يقرؤه أصلًا.
    """
    r = client.post(LOGIN, json={"student_no": "1001", "pin": PIN, "org_id": 999}, headers=ORIGIN)
    assert r.status_code == 422
    assert db.session.scalar(select(db.func.count(Session.id))) == 0


def test_org_is_resolved_server_side(client, seeded):
    """
    الدخول ينجح **بلا `org_id` إطلاقًا**، والجلسة تُنسب لمستخدم المنظمة المبذورة.
    فلا تصير شاشة الدخول أداة استكشاف للمنظمات.
    """
    from app.models import User

    assert _login(client).status_code == 200
    session_row = db.session.scalar(select(Session))
    assert db.session.get(User, session_row.user_id).org_id == seeded["org_id"]


# ═══ القناة الجانبية الزمنية ═══


def test_unknown_student_costs_the_same_time_as_wrong_pin(client, seeded):
    """
    الرسالة الواحدة بلا زمن واحد **ضمانة ناقصة**: بلا الهاش الوهمي يردّ الرقم
    غير الموجود فورًا، ويدفع الموجودُ كلفة argon2id — والفارق يُقاس من المتصفّح
    فتعود الشاشة أداة تعداد.

    القياس بالوسيط لا بالمتوسّط: قيمة شاذّة واحدة من جدولة النظام تفسد المتوسّط.
    """
    import statistics
    import time

    def timings(student_no):
        out = []
        for _ in range(6):
            # محاولة جديدة لكل قياس، وتنظيف السجلّ حتى لا يتدخّل القفل.
            db.session.execute(db.text("DELETE FROM login_attempts"))
            db.session.commit()
            start = time.perf_counter()
            client.post(LOGIN, json={"student_no": student_no, "pin": "0000"}, headers=ORIGIN)
            out.append(time.perf_counter() - start)
        return statistics.median(out)

    unknown = timings("9999")
    known = timings("1001")
    ratio = max(unknown, known) / min(unknown, known)

    assert ratio < 2.0, (
        f"فارق زمني {ratio:.1f}× يكشف وجود الرقم: "
        f"مجهول {unknown * 1000:.0f}ms · معروف {known * 1000:.0f}ms"
    )
