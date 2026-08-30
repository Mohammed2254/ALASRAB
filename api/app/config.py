import os

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in {"1", "true", "yes"}


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-for-production")

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
