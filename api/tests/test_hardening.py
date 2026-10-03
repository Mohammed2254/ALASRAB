"""
التصليب للإنتاج — و-٢١.

ثلاثة ثقوب كانت قائمة، كلٌّ منها **عطلٌ صامت** لا صاخب: سقفُ جسمٍ مفقود،
وترويساتُ أمان غائبة، وإعدادٌ تطويريّ يُنشَر بلا اعتراض.

@covers ق-٢٧٣, ق-٢٧٤, ق-٢٧٥
"""

import io

import pytest
from sqlalchemy import select

from app import BASE_CSP, DOCS_CDN, create_app

# **الوحدة لا الأسماء، لحرس الهوية لا الأناقة.**
#
# `tests/test_csrf.py` يستعمل `importlib.reload(app.config)` ليُثبت أن
# `EXPOSE_API_DOCS` تُقرَأ وقت تعريف الصنف. وإعادةُ التحميل تبني **أصنافًا
# جديدة الهوية** بنفس الأسماء، و«إعادة التحميل مرّةً أخرى للتنظيف» لا تُرجع
# الهوية الأولى. فاسمٌ مُستورَد هنا وقت الاستيراد يصير — بعد ذلك الاختبار —
# صنفًا **غير** الذي يرفعه `app/config.py` الحاليّ: فيفلت من `pytest.raises`
# ويسقط الاختبار بحسب ترتيب التنفيذ وحده.
#
# وقد وقع هذا فعلًا: الأربعة أدناه تمرّ منفردةً وتسقط في المجموعة الكاملة.
# والمرجع عبر الوحدة يُقرأ **وقت النداء**، فيطابق الحاليّ أيًّا كان.
from app import config as config_module
from app.config import MAX_CONTENT_LENGTH_BYTES, TestConfig
from app.extensions import db
from app.models import Membership

ORIGIN = {"Origin": "http://localhost:5173"}


# ═══ ق-٢٧٣ — سقف جسم الطلب ═══


def test_oversized_body_is_refused_with_the_documented_shape(client):
    """
    **غيابُ السقف أرخص هجوم على المنصّة** — استنزاف ذاكرة بطلبٍ واحد بلا حساب.
    و٤١٣ الافتراضيّ صفحةُ HTML تكسر عقد `{"message"}` (`API.md` §١) على أكبر
    مسارٍ يرفع ملفًّا.

    @covers ق-٢٧٣
    """
    payload = b"x" * (MAX_CONTENT_LENGTH_BYTES + 1024)
    r = client.post(
        "/api/auth/login", data=payload, headers=ORIGIN, content_type="application/json"
    )

    assert r.status_code == 413
    assert r.get_json()["message"]


def test_oversized_upload_is_refused_on_the_real_file_path(client, seeded):
    """
    **المسار الذي يُستنزَف فعلًا** هو رفعُ ملفّ راصد (`multipart`)، لا جسمُ
    JSON. وفحصُ السقف على مسارٍ غير مصادَق يُرَدّ بـ٤٠١ قبل قراءة الجسم —
    فيمرّ الاختبار بلا أن يلمس السقف إطلاقًا.

    @covers ق-٢٧٣
    """
    membership = db.session.scalar(
        select(Membership).where(Membership.user_id == seeded["users"]["1001"])
    )
    membership.role = "admin"
    db.session.commit()
    client.post("/api/auth/login", json={"student_no": "1001", "pin": "1234"}, headers=ORIGIN)

    big = io.BytesIO(b"a,b,c\n" * (MAX_CONTENT_LENGTH_BYTES // 6 + 1024))
    r = client.post(
        "/api/admin/paste/preview",
        data={"file": (big, "rasd.csv")},
        headers=ORIGIN,
        content_type="multipart/form-data",
    )
    assert r.status_code == 413


def test_a_realistic_rasd_file_fits_under_the_cap(client):
    """
    سقفٌ يرفض الاستعمال المقصود ليس تصليبًا بل عطلًا. ٢٠٠ طالبًا × ١٣ عمودًا
    هو المدى المصرَّح به للمنصّة.

    @covers ق-٢٧٣
    """
    row = ",".join(["قيمة طويلة نسبيًّا"] * 13) + "\n"
    assert len(row.encode()) * 200 < MAX_CONTENT_LENGTH_BYTES


# ═══ ق-٢٧٤ — ترويسات الأمان ═══


@pytest.mark.parametrize(
    "header,expected",
    [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ],
)
def test_security_headers_on_a_successful_response(client, header, expected):
    """@covers ق-٢٧٤"""
    assert client.get("/health").headers[header] == expected


def test_security_headers_on_an_error_response(client):
    """
    **ردُّ الخطأ هو أوّل ما يصل متصفّحًا مخترقًا.** ترويسةٌ تُضاف للناجح وحده
    تُغطّي المسار الأسهل وتترك الأصعب — ولذلك `after_request` لا تزيينُ
    المسار السعيد.

    @covers ق-٢٧٤
    """
    r = client.post("/api/admin/users", json={}, headers=ORIGIN)
    assert r.status_code in (401, 403, 422)
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in r.headers


def test_csp_blocks_remote_script_by_default(client):
    """
    الحماية الحقيقية في `script-src 'self'` — ولا استثناء فيها: الواجهة
    المبنيّة بلا موردٍ خارجيّ واحد (الخطوط محليّة، وGSAP داخل الحزمة).

    @covers ق-٢٧٤
    """
    csp = client.get("/health").headers["Content-Security-Policy"]
    assert "script-src 'self';" in csp
    assert DOCS_CDN not in csp
    # و`unsafe-inline` في `style-src` وحدها: React يكتب `style="…"` سمةً.
    assert "'unsafe-inline'" in csp.split("style-src")[1].split(";")[0]
    assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
    assert "frame-ancestors 'none'" in csp


def test_hsts_is_absent_without_https(client):
    """
    إرسالها محليًّا يقفل `localhost` على https في متصفّح المطوّر **سنةً
    كاملة** — عطلٌ يتبع المطوّر إلى كل مشروع آخر على نفس المنفذ.

    @covers ق-٢٧٤
    """
    assert "Strict-Transport-Security" not in client.get("/health").headers


def test_hsts_is_present_behind_https(_schema):
    """@covers ق-٢٧٤"""

    class Https(TestConfig):
        SESSION_COOKIE_SECURE = True
        SECRET_KEY = "not-the-dev-default"

    app = create_app(Https)
    with app.app_context():
        headers = app.test_client().get("/health").headers
    assert "max-age=31536000" in headers["Strict-Transport-Security"]


def test_csp_admits_the_docs_cdn_only_when_docs_are_exposed():
    """
    سياسةٌ لا تسمح بـjsdelivr تُظهر Swagger صفحةً بيضاء وتُوهم أن المسار
    معطوب — فالاستثناء مقصود، ومحدودٌ بمفتاحٍ يرفضه حرسُ الإقلاع إنتاجًا.

    @covers ق-٢٧٤
    """
    assert DOCS_CDN not in BASE_CSP


# ═══ ق-٢٧٥ — حرس الإقلاع ═══


def _prod(**overrides):
    return {
        "SESSION_COOKIE_SECURE": True,
        "SECRET_KEY": "a-real-generated-secret",
        "CORS_ALLOWED_ORIGINS": ["https://asrab.example.com"],
        "OPENAPI_SWAGGER_UI_PATH": None,
        **overrides,
    }


def test_sane_production_config_passes():
    """حرسٌ يرفض الإعداد الصحيح يُعطَّل في أوّل يوم — وحرسٌ معطَّل ليس حرسًا."""
    assert config_module.assert_production_safe(_prod()) is None


def test_dev_secret_key_in_production_is_refused():
    """
    مفتاحٌ معروفٌ منشور. **ويُرفَع وقت الإقلاع لا وقت الطلب** — فالعطل يُرى
    في سجلّ النشر، لا بعد أسبوعٍ من استعمالٍ غير آمن.

    @covers ق-٢٧٥
    """
    with pytest.raises(config_module.ProductionConfigError, match="SECRET_KEY"):
        config_module.assert_production_safe(_prod(SECRET_KEY=config_module.DEV_SECRET_KEY))


def test_empty_cors_in_production_is_refused():
    """
    فحص `Origin` (ADR-006) يرفض كل طلب مغيِّر للحالة بقائمةٍ فارغة — فالمنصّة
    تُقرأ ولا تُكتَب، وهو عطلٌ يُكتشَف بعد أوّل اعتماد قراءة لا قبله.

    @covers ق-٢٧٥
    """
    with pytest.raises(config_module.ProductionConfigError, match="CORS_ALLOWED_ORIGINS"):
        config_module.assert_production_safe(_prod(CORS_ALLOWED_ORIGINS=[]))


def test_exposed_api_docs_in_production_is_refused():
    """`API.md` §٢ يوجب تعطيلها إنتاجًا — والوثيقة بلا حرسٍ لا توقف يدًا."""
    with pytest.raises(config_module.ProductionConfigError, match="EXPOSE_API_DOCS"):
        config_module.assert_production_safe(_prod(OPENAPI_SWAGGER_UI_PATH="/docs"))


def test_all_problems_are_reported_at_once():
    """
    عطلٌ واحدٌ في كل إقلاع يعني ثلاث دورات نشرٍ فاشلة لثلاثة أخطاء — ومن
    ينشر لأوّل مرّة يحتاج القائمة كاملةً مرّة.

    @covers ق-٢٧٥
    """
    with pytest.raises(config_module.ProductionConfigError) as exc:
        config_module.assert_production_safe(
            _prod(
                SECRET_KEY=config_module.DEV_SECRET_KEY,
                CORS_ALLOWED_ORIGINS=[],
                OPENAPI_SWAGGER_UI_PATH="/d",
            )
        )
    message = str(exc.value)
    assert "SECRET_KEY" in message
    assert "CORS_ALLOWED_ORIGINS" in message
    assert "EXPOSE_API_DOCS" in message


def test_guard_is_silent_in_development():
    """
    `SESSION_COOKIE_SECURE` علامةُ الإنتاج الوحيدة الصادقة هنا: المتصفّح يرفض
    الكوكي الآمن على http. فحرسٌ يمنع `flask run` محليًّا سيُعطَّل.

    @covers ق-٢٧٥
    """
    assert config_module.assert_production_safe({"SESSION_COOKIE_SECURE": False}) is None
    # بلا العلامة: المفتاح التطويريّ وحده لا يكفي لاستدعاء الحرس.
    dev_only = {"SECRET_KEY": config_module.DEV_SECRET_KEY}
    assert config_module.assert_production_safe(dev_only) is None
