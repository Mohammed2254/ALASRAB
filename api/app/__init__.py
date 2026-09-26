from flask import Flask, jsonify, request
from sqlalchemy import text
from werkzeug.exceptions import HTTPException

from .config import Config
from .extensions import api, db, migrate

# الطرق الآمنة: لا تغيّر حالة، فلا تحتاج فحص Origin.
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def create_app(config_object=Config):
    """مصنع التطبيق: يسمح للاختبارات بإنشاء تطبيق بإعدادات أخرى بلا حيل عامة."""
    # `static_url_path=""` لا `/static` الافتراضي — الواجهة المبنيّة (`ui/dist/`)
    # تُنسَخ إلى `app/static/` وقت بناء صورة Docker (و-١٩)، فتُخدَم من الجذر
    # نفسه الذي يخدم `/api/*`: **أصلٌ واحد في الإنتاج**، تمامًا كما علّق
    # `ui/vite.config.ts` منذ و-١٣ (الوكيل يحاكي هذا محليًّا، فلا CORS إنتاجًا).
    app = Flask(__name__, static_url_path="")
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    api.init_app(app)

    @app.before_request
    def check_origin():
        """
        ADR-006 — الطبقة الثانية ضدّ CSRF فوق SameSite=Lax.

        غياب Origin على طلب مغيِّر للحالة **رفضٌ لا تساهل**: الطبقة تسقط كلها لو
        كفى المهاجمَ أن يحذف ترويسة.
        """
        if request.method in SAFE_METHODS:
            return None
        origin = request.headers.get("Origin")
        if origin not in app.config["CORS_ALLOWED_ORIGINS"]:
            return jsonify(message="طلب من مصدر غير مسموح."), 403
        return None

    @app.errorhandler(Exception)
    def json_error(exc):
        """
        كل ردّ خطأ بالشكل الموثَّق `{"message": …}` — حتى غير المتوقَّع منه
        (`API.md` §١). بلا هذا يردّ Flask صفحة HTML على استثناء غير ملتقَط،
        فيكسر العقد ويعرض أثر التنفيذ في وضع التنقيح.

        **التفصيل يُسجَّل ولا يُرسَل:** رسالة SQL أو مسار ملفّ في ردّ خطأ خريطةٌ
        للمهاجم، والمستخدم لا ينتفع بها.
        """
        if isinstance(exc, HTTPException):
            return exc  # ٤٠١ و٤٠٣ و٤٢٢ من smorest — لها شكلها ورسالتها المقصودة
        app.logger.exception("خطأ غير متوقَّع")
        return jsonify(message="حدث خلل في الخادم. حاول بعد قليل."), 500

    @app.get("/health")
    def health():
        """
        يفحص القاعدة فعلًا: خادمٌ يردّ ٢٠٠ وقاعدته ساقطة يخدع المراقبة ويؤخّر
        اكتشاف العطل — وهو أسوأ من غياب الفحص.
        """
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            return jsonify(status="db_unreachable"), 503
        return jsonify(status="ok")

    @app.errorhandler(404)
    def spa_fallback(exc):
        """
        رابطٌ عميق لمسار طيّاريّ (`/admin/report` مثلًا) يصل الخادم مباشرةً عند
        تحديث الصفحة أو فتح رابط — التوجيه كلّه في المتصفّح (ADR-008)، فالخادم
        لا يعرف هذا المسار إطلاقًا. **يُعاد له `index.html`** ليقرأه العميل.
        `/api/*` وحدها مستثناة — طلبٌ لمسار API غير موجود يبقى ٤٠٤ JSON
        بالشكل الموثَّق (`API.md` §١)، لا صفحة HTML تكسر العقد.
        """
        if request.path.startswith("/api/"):
            return exc
        return app.send_static_file("index.html")

    # الاستيراد هنا لا في الأعلى: النماذج تحتاج db المهيّأ، واستيرادها مبكرًا
    # يخلق دورة استيراد.
    from . import models  # noqa: F401
    from .routes import admin, auth, me

    api.register_blueprint(auth.blp)
    api.register_blueprint(me.blp)
    api.register_blueprint(admin.blp)

    return app
