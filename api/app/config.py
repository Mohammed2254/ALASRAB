import os

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in {"1", "true", "yes"}


DEV_SECRET_KEY = "dev-only-not-for-production"

# سقف جسم الطلب. أكبر ما يُرفَع فعلًا هو ملفّ راصد: ١٣ عمودًا × ٢٠٠ طالب
# ≈ ٥٠KB، فمِيبيبايتان فائضٌ واسع. **وغيابُ السقف يعني استنزاف ذاكرة الخادم
# بطلبٍ واحد** — وهو أرخص هجوم على المنصّة كلّها، ولا يحتاج حسابًا.
MAX_CONTENT_LENGTH_BYTES = 2 * 1024 * 1024


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET_KEY)

    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH_BYTES

    # الكوكي الآمن يُرفض على http، فالتطوير المحلي يحتاجه false. القيمة من البيئة
    # لا من الكود، حتى لا يُنشر الإنتاج بإعداد التطوير.
    SESSION_COOKIE_SECURE = _flag("SESSION_COOKIE_SECURE")

    # ADR-006: الطبقة الثانية ضد CSRF. نسيان ضبطها يكسر كل طلب مغيِّر للحالة —
    # عطل صاخب لا صامت، وهذا مقصود: الفشل الصامت في الأمان أسوأ من التوقّف.
    CORS_ALLOWED_ORIGINS = [
        o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
    ]

    # flask-smorest يولّد OpenAPI من مخططات Marshmallow، فيبقى العقد مطابقًا للكود.
    API_TITLE = "الأسراب API"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.3"

    # `API.md` §٢: العقد يخدم المطوّر لا المستخدم، و**يُعطَّل في الإنتاج**.
    # واجهة تعرض كل مسار وكل حقل هي خريطة جاهزة لمن يبحث عن سطح هجوم — والقيمة
    # التي تعطيها للمطوّر لا يحتاجها أحد على الخادم الحيّ.
    # الافتراض **معطَّل**: نسيان الضبط يُخفي لا يكشف.
    if _flag("EXPOSE_API_DOCS"):
        OPENAPI_URL_PREFIX = "/"
        OPENAPI_SWAGGER_UI_PATH = "/docs"
        OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://asrab:asrab_dev_only@127.0.0.1:5434/asrab_v2_test",
    )
    TESTING = True
    CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]

    # **لا يُورَّث من بيئة المطوّر** (و-٢١): `Config` يقرأ `EXPOSE_API_DOCS`
    # وقت تعريف الصنف، فمطوّرٌ يضعها في `.env` كان يحصل على سياسة محتوى
    # مختلفة عن CI — واختبارٌ نتيجتُه تتبع ملفًّا غير مُتعقَّب ليس اختبارًا.
    OPENAPI_URL_PREFIX = None
    OPENAPI_SWAGGER_UI_PATH = None


class ProductionConfigError(RuntimeError):
    """
    إعدادٌ تطويريّ على خادم حيّ. **يُرفع وقت الإقلاع لا وقت الطلب** — فالعطل
    يُرى في سجلّ النشر لا بعد أسبوعٍ من استعمالٍ غير آمن.
    """


def assert_production_safe(config) -> None:
    """
    حرسُ إقلاع: نفس مبدأ حرس `seed.py` — **الفشل الصاخب أرحم من الصامت**.

    و`SESSION_COOKIE_SECURE` هي علامة الإنتاج الوحيدة الصادقة في هذا المشروع:
    المتصفّح يرفض الكوكي الآمن على http، فلا تُضبَط `true` إلا خلف HTTPS
    حقيقيّ. و`docker-compose.prod.yml` يضبطها، و`docker-compose.yml` المحليّ
    لا يضبطها — فالحرس يعمل حيث يجب ويصمت حيث يجب.

    **ولا يُفحص شيءٌ من هذا في التطوير:** حرسٌ يمنع `flask run` محليًّا
    سيُعطَّل في أوّل يوم، وحرسٌ معطَّل ليس حرسًا.
    """
    if not config.get("SESSION_COOKIE_SECURE"):
        return

    problems = []
    if config.get("SECRET_KEY") == DEV_SECRET_KEY:
        problems.append(
            "SECRET_KEY هو الافتراض التطويريّ المعروف — ولّد واحدًا: "
            "python3 -c 'import secrets; print(secrets.token_urlsafe(48))'"
        )
    if not config.get("CORS_ALLOWED_ORIGINS"):
        problems.append(
            "CORS_ALLOWED_ORIGINS فارغة — فحص Origin (ADR-006) يرفض كل طلب "
            "مغيِّر للحالة، فالمنصّة تقرأ ولا تكتب."
        )
    if config.get("OPENAPI_SWAGGER_UI_PATH"):
        problems.append(
            "EXPOSE_API_DOCS مفعَّلة — واجهةٌ تعرض كل مسار وكل حقل خريطةُ سطح "
            "هجومٍ جاهزة، و`API.md` §٢ يوجب تعطيلها إنتاجًا."
        )

    if problems:
        raise ProductionConfigError("إعدادات غير صالحة للإنتاج:\n  · " + "\n  · ".join(problems))
