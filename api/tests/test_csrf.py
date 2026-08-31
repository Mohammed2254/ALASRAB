"""
CSRF وسلوك الكوكي — ADR-006 و ARCHITECTURE §٧.٢.

الكوكي يُرسَل تلقائيًّا مع كل طلب إلى نطاقنا، **بما فيه طلبٌ أنشأه موقع آخر**.
الدفاع طبقتان: `SameSite=Lax` في المتصفّح، وفحص `Origin` في الخادم — وكلٌّ منهما
تسقط في حالة تصمد فيها الأخرى.
"""

import pytest

from app.security import COOKIE

ALLOWED = {"Origin": "http://localhost:5173"}
LOGIN = "/api/auth/login"
CREDS = {"student_no": "1001", "pin": "1234"}


# ═══ ق-٤ — فحص Origin على الطلبات المغيّرة ═══


@pytest.mark.parametrize(
    "case, headers",
    [
        ("أصل أجنبي", {"Origin": "https://evil.example"}),
        ("نطاق مشابه", {"Origin": "http://localhost:5173.evil.example"}),
        ("مخطّط مختلف", {"Origin": "https://localhost:5173"}),
        ("منفذ مختلف", {"Origin": "http://localhost:9999"}),
        ("بلا Origin", {}),
    ],
)
def test_state_changing_request_is_rejected(client, seeded, case, headers):
    """
    @covers ق-٤

    **غياب `Origin` رفضٌ لا تساهل:** لو كفى المهاجمَ أن يحذف ترويسة، لسقطت
    الطبقة كلها. والمطابقة نصّية تامّة — لا `startswith` يمرّر `…5173.evil`.
    """
    r = client.post(LOGIN, json=CREDS, headers=headers)
    assert r.status_code == 403, case


def test_allowed_origin_passes(client, seeded):
    assert client.post(LOGIN, json=CREDS, headers=ALLOWED).status_code == 200


def test_logout_is_also_protected(client, seeded):
    """كل مغيِّر للحالة، لا الدخول وحده. الخروج القسري إزعاجٌ حقيقي للطالب."""
    client.post(LOGIN, json=CREDS, headers=ALLOWED)
    assert (
        client.post("/api/auth/logout", headers={"Origin": "https://evil.example"}).status_code
        == 403
    )


def test_origin_check_rejects_before_touching_credentials(client, seeded):
    """
    الرفض يقع في `before_request` **قبل** أي عمل: لا محاولة دخول تُسجَّل، فلا
    يستطيع مهاجم إغراق `login_attempts` ليقفل حسابًا لا يملكه.
    """
    from sqlalchemy import select

    from app.extensions import db
    from app.models import LoginAttempt

    client.post(LOGIN, json=CREDS, headers={"Origin": "https://evil.example"})
    assert db.session.scalars(select(LoginAttempt)).all() == []


# ═══ الطرق الآمنة لا تحتاج الفحص ═══


def test_get_requests_do_not_require_origin(client, seeded):
    """
    `GET` لا يغيّر حالة، وفرض `Origin` عليه يكسر فتح الرابط مباشرةً في المتصفّح
    — وهو أشيع فعل عند الطالب.
    """
    assert client.get("/health").status_code == 200
    assert client.get("/api/auth/me").status_code == 401  # ٤٠١ لا ٤٠٣


# ═══ ق-١ — سمات الكوكي ═══


def test_cookie_carries_the_designed_attributes(client, seeded):
    header = client.post(LOGIN, json=CREDS, headers=ALLOWED).headers["Set-Cookie"]

    assert "HttpOnly" in header, "بلاها يسرق أي XSS جلسة ٩٠ يومًا"
    assert "SameSite=Lax" in header, "الطبقة الأولى ضد CSRF"
    assert "Path=/" in header
    # ٩٠ يومًا: مراهقٌ يُطالَب بالدخول كل أسبوع يهجر التطبيق.
    assert "Max-Age=7776000" in header


def test_secure_flag_follows_configuration_not_a_constant(client, seeded, app):
    """
    `Secure` من البيئة: المتصفّح **يرفض** الكوكي الآمن على http، فتثبيته `True`
    يكسر التطوير، و`False` يكسر أمان الإنتاج. نثبت أنه يتبع الإعداد فعلًا.
    """
    assert "Secure" not in client.post(LOGIN, json=CREDS, headers=ALLOWED).headers["Set-Cookie"]

    app.config["SESSION_COOKIE_SECURE"] = True
    client.post("/api/auth/logout", headers=ALLOWED)
    assert "Secure" in client.post(LOGIN, json=CREDS, headers=ALLOWED).headers["Set-Cookie"]
    app.config["SESSION_COOKIE_SECURE"] = False


def test_logout_clears_the_cookie(client, seeded):
    client.post(LOGIN, json=CREDS, headers=ALLOWED)
    header = client.post("/api/auth/logout", headers=ALLOWED).headers["Set-Cookie"]
    assert COOKIE in header and ("Max-Age=0" in header or "Expires" in header)


# ═══ API.md §٢ — العقد معطَّل في الإنتاج ═══


def test_api_docs_are_disabled_when_env_var_is_absent(monkeypatch):
    """
    واجهة `/docs` تعرض كل مسار وكل حقل — خريطة جاهزة لمن يبحث عن سطح هجوم.

    نقيس **الافتراض عند غياب المتغيّر** لا بيئة التطوير الحالية (التي تُفعّله
    عمدًا): نُعيد تحميل الوحدة بعد إزالة المتغيّر ومنع `dotenv` من إعادته.
    نسيان الضبط في الإنتاج يجب أن **يُخفي لا يكشف**.
    """
    import importlib

    import dotenv

    import app.config as config_module

    monkeypatch.delenv("EXPOSE_API_DOCS", raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    reloaded = importlib.reload(config_module)
    try:
        assert not hasattr(reloaded.Config, "OPENAPI_SWAGGER_UI_PATH")
        assert not hasattr(reloaded.Config, "OPENAPI_URL_PREFIX")
    finally:
        importlib.reload(config_module)  # لا تُلوَّث الاختبارات التالية


def test_api_docs_appear_only_when_explicitly_enabled(monkeypatch):
    """الحدّ الآخر: بلاه قد يمرّ اختبارٌ لأن المتغيّر لا يُقرأ إطلاقًا."""
    import importlib

    import dotenv

    import app.config as config_module

    monkeypatch.setenv("EXPOSE_API_DOCS", "true")
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    reloaded = importlib.reload(config_module)
    try:
        assert reloaded.Config.OPENAPI_SWAGGER_UI_PATH == "/docs"
    finally:
        importlib.reload(config_module)
