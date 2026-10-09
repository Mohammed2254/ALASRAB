"""
مسارات الدخول والجلسة. HTTP فقط: لا استعلام قاعدة بيانات ولا منطق أعمال.
"""

from flask import current_app, g, jsonify, make_response, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..schemas.auth import LoginSchema, SessionSchema
from ..security import COOKIE, login_required, role_of
from ..services import auth as auth_service

blp = Blueprint("auth", __name__, url_prefix="/api", description="الدخول والجلسة")

# ٩٠ يومًا: الطالب لا يُطالب بالدخول كل زيارة — وهذا أكثر ما يقتل الاستعمال
# اليومي في هذه الفئة العمرية.
COOKIE_MAX_AGE = auth_service.SESSION_DAYS * 24 * 60 * 60


def _body(user, membership):
    """شكل الردّ كما في `API.md` §٣: معشَّش تحت `user`."""
    return {
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "student_no": user.student_no,
            "role": role_of(membership),
        }
    }


def _set_cookie(response, token):
    response.set_cookie(
        COOKIE,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,  # لا يقرؤه جافاسكربت، فلا يُسرق بـXSS
        # secure من البيئة: المتصفّح يرفض الكوكي الآمن على http، فتثبيته true
        # يكسر التطوير، وتثبيته false يكسر أمان الإنتاج.
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        # الطبقة الأولى ضد CSRF — والثانية فحص Origin في create_app (ADR-006).
        samesite="Lax",
        path="/",
    )
    return response


@blp.route("/auth/login")
class Login(MethodView):
    @blp.arguments(LoginSchema)
    @blp.response(200, SessionSchema)
    def post(self, data):
        """رقم الطالب + رمز من أربعة أرقام. `org_id` يُحلّ في الخادم لا من العميل."""
        try:
            org_id = auth_service.default_org_id()
            user, token = auth_service.login(org_id, data["student_no"], data["pin"])
        except auth_service.LockedOut as e:
            abort(429, message=str(e))
        except auth_service.AuthError as e:
            abort(401, message=str(e))

        body = _body(user, auth_service.membership_of(user))
        return _set_cookie(make_response(jsonify(body)), token)


@blp.route("/auth/logout")
class Logout(MethodView):
    @blp.response(204)
    def post(self):
        """
        إبطال فوري **في القاعدة** — وهذا بالضبط ما لا يستطيعه JWT (ADR-003).

        بلا حارس عمدًا: تسجيل الخروج بجلسة منتهية يجب أن ينجح صامتًا لا أن يردّ
        ٤٠١، وإلا عَلِق المستخدم في شاشة لا يخرج منها.

        @covers ق-٩ · والصمتُ أثبته
        `tests/test_auth.py::test_logout_without_session_succeeds_quietly`.
        """
        auth_service.logout(request.cookies.get(COOKIE, ""))
        response = make_response("", 204)
        response.delete_cookie(COOKIE, path="/")
        return response


@blp.route("/auth/me")
class Me(MethodView):
    @login_required
    @blp.response(200, SessionSchema)
    def get(self):
        """المستخدم الحالي ودوره — تتحقّق منه الواجهة عند الإقلاع."""
        return _body(g.user, g.membership)
