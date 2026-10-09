from flask import Flask, jsonify, request
from sqlalchemy import text
from werkzeug.exceptions import HTTPException

from .config import Config, assert_production_safe
from .extensions import api, db, migrate

# الطرق الآمنة: لا تغيّر حالة، فلا تحتاج فحص Origin.
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# ترويسات ثابتة لا تعتمد على الإعداد.
SECURITY_HEADERS = {
    # لا تخمين نوع المحتوى: ملفٌّ يُرفَع ويُفسَّر HTML هو XSS مخزَّن.
    "X-Content-Type-Options": "nosniff",
    # نقرٌ مخفيّ — والمنصّة كلّها أفعالٌ بزرّ واحد (اعتماد · أرشفة · تعطيل).
    # `frame-ancestors` في CSP أدناه هي البديل الحديث، وهذه للمتصفّح القديم.
    "X-Frame-Options": "DENY",
    # لا يُسرَّب مسارٌ إداريّ في `Referer` إلى موقعٍ خارجيّ.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # المنصّة لا تطلب شيئًا من هذه، فمنعُها يسدّ ما لم يُطلب.
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

# **صارمة لأنها تستطيع أن تكون:** الواجهة المبنيّة بلا موردٍ خارجيّ واحد
# (الخطوط محليّة في `ui/public/fonts/`، وGSAP داخل الحزمة) — تحقّقتُ منها
# في ناتج البناء لا افتراضًا.
#
# و`style-src` وحدها تحمل `unsafe-inline`: React يكتب `style="…"` سمةً
# (شريط التقدّم يمرّر `--p` كذلك)، وسمةُ النمط تحتاجها. وحمايةُ CSP الحقيقية
# في `script-src 'self'` وهي مُحكَمة بلا استثناء.
BASE_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'none'"
)

# `EXPOSE_API_DOCS` تجلب Swagger UI من jsdelivr، فسياسةٌ لا تسمح به تُظهر
# صفحةً بيضاء وتُوهم أن المسار معطوب. مفتاحٌ تطويريّ وحده — وحرسُ الإقلاع
# يرفض تفعيله إنتاجًا أصلًا.
DOCS_CDN = "https://cdn.jsdelivr.net"


def create_app(config_object=Config):
    """مصنع التطبيق: يسمح للاختبارات بإنشاء تطبيق بإعدادات أخرى بلا حيل عامة."""
    # `static_url_path=""` لا `/static` الافتراضي — الواجهة المبنيّة (`ui/dist/`)
    # تُنسَخ إلى `app/static/` وقت بناء صورة Docker (و-١٩)، فتُخدَم من الجذر
    # نفسه الذي يخدم `/api/*`: **أصلٌ واحد في الإنتاج**، تمامًا كما علّق
    # `ui/vite.config.ts` منذ و-١٣ (الوكيل يحاكي هذا محليًّا، فلا CORS إنتاجًا).
    app = Flask(__name__, static_url_path="")
    app.config.from_object(config_object)

    # **حرسُ إقلاع لا فحصُ طلب** (و-٢١): إعدادٌ تطويريّ على خادم حيّ يُرى في
    # سجلّ النشر، لا بعد أسبوعٍ من استعمالٍ غير آمن.
    assert_production_safe(app.config)

    csp = (
        BASE_CSP.replace("script-src 'self'", f"script-src 'self' {DOCS_CDN}").replace(
            "style-src 'self'", f"style-src 'self' {DOCS_CDN}"
        )
        if app.config.get("OPENAPI_SWAGGER_UI_PATH")
        else BASE_CSP
    )

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

    # ترويسات أمان على **كل** ردّ — صفحةً كان أو JSON أو خطأ.
    #
    # `after_request` لا `send_static_file` وحده: ردُّ الخطأ هو أوّل ما يصل
    # متصفّحًا مخترقًا، وترويسةٌ تُضاف للناجح وحده تُغطّي المسار الأسهل وتترك
    # الأصعب. وهي ثابتة تُحسَب مرّةً خارج الدالّة لا في كل طلب.
    @app.after_request
    def security_headers(response):
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        response.headers.setdefault("Content-Security-Policy", csp)
        if app.config["SESSION_COOKIE_SECURE"]:
            # HSTS خلف HTTPS وحده: إرسالها على http لا معنى له، وإرسالها
            # محليًّا يقفل `localhost` على https في متصفّح المطوّر لسنة.
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    @app.errorhandler(413)
    def too_large(_exc):
        """
        سقف `MAX_CONTENT_LENGTH` يردّ ٤١٣ بصفحة HTML افتراضًا — فيكسر العقد
        `{"message": …}` (`API.md` §١) على أكبر مسارٍ يرفع ملفًّا.
        """
        return jsonify(message="الملفّ أكبر من الحدّ المسموح."), 413

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

        @covers ق-٢٩٩
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

        و`/api/*` تُردّ **JSON** بالشكل الموثَّق (`API.md` §١).

        **وكان هذا التعليق يزعم ذلك والكود يفعل غيره** حتى و-٢١: كان
        `return exc` يُسلّم الاستثناء لفلاسك فيُصيِّره **صفحة HTML إنجليزية**
        — أي أن أوّل ردٍّ يراه عميلٌ أخطأ في المسار يكسر العقد الذي يوثّقه
        هذا السطر. اكتُشف بـ`curl` على صورة الإنتاج لا باختبار.

        **والتمييز بـ`exc.data` لا بالحدس:** ظننتُ أوّلًا أن معالج المخطّط
        أخصُّ فيسبق معالج التطبيق — **وكان ظنًّا خاطئًا**، أمسكه الاختبار:
        صارت كلُّ `abort(404, message=…)` تردّ الرسالة العامّة، فضاع «لا طالب
        بهذا المعرّف» وما يشبهه. و`flask-smorest` يُعلّق الرسالة المقصودة على
        `exc.data`، فوجودُها هو الفرق القاطع بين:

        · **إجهاضٍ مقصود** — رسالتُه مُعلَّقةٌ على `exc.data`، فتُصيَّر JSON.
        · **٤٠٤ توجيهيّ** — لا قاعدة ولا رسالة، فتُصنَع واحدة.

        **والعطل كان أوسع مما ظهر أوّلًا:** هذا المعالج يعترض **كل** ٤٠٤ على
        مستوى التطبيق، فيمنع معالجَ `flask-smorest` من تصيير ردّه. و`return
        exc` يُسلّم الاستثناء لفلاسك فيُصيِّره **HTML إنجليزيًّا** — أي أن
        *كل* `abort(404, message=…)` على مسار API كان يردّ HTML لا JSON، لا
        ٤٠٤ المسار المجهول وحده. ورسائلُ ٤٠٤ الموثَّقة في `API.md §٦` لم تكن
        تصل العميل بالشكل الموعود قطّ.

        **ولماذا عاش:** لا اختبار واحدًا كان يؤكّد **جسم** ردّ ٤٠٤ — كلُّها
        تؤكّد رمز الحالة وحده. فالعقد موثَّقٌ وغير محروس.
        """
        if request.path.startswith("/api/"):
            # `exc.data` تحمل رسالة الإجهاض المقصود؛ وغيابُها يعني ٤٠٤ توجيهيًّا.
            data = getattr(exc, "data", None)
            return jsonify(**data) if data else jsonify(message="لا مسار بهذا العنوان."), 404
        return app.send_static_file("index.html")

    # الاستيراد هنا لا في الأعلى: النماذج تحتاج db المهيّأ، واستيرادها مبكرًا
    # يخلق دورة استيراد.
    from . import models  # noqa: F401
    from .cli import register_cli
    from .routes import admin, auth, me

    register_cli(app)

    api.register_blueprint(auth.blp)
    api.register_blueprint(me.blp)
    api.register_blueprint(admin.blp)

    return app
