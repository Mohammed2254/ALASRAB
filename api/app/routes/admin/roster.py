"""
سجلُّ الطلاب (`FR-095` · `FR-096`) وإعادةُ تعيين الرمز (`FR-004`).

**والرمز يُولَّد في الخادم ويُعرض مرّة** ولا يُقبَل من العميل أصلًا، ولا
يظهر في أيّ قراءةٍ ولا في سطر تدقيق.
"""

from flask import g
from flask.views import MethodView
from flask_smorest import abort

from ...extensions import db
from ...models import User
from ...schemas.audit import ResetPinSchema
from ...schemas.roster import (
    ActiveSetSchema,
    BulkCreatedSchema,
    BulkCreateStudentsSchema,
    CreateStudentSchema,
    IssuedStudentSchema,
    RoleSetSchema,
    RosterListSchema,
    SetActiveSchema,
    SetRoleSchema,
)
from ...security import admin_required
from ...services import auth as auth_service
from ...services import roster as roster_service
from .._helpers import org_of_session as _org
from . import blp

# ═══ و-٢١ — سجلّ الطلاب ═══
#
# **لا بند `SCOPE.md` لإنشاء طالب** — فُرض أنهم موجودون، وكان الكاتب الوحيد
# لـ`User` في المشروع كلّه هو `seed.py` (وهو يرفض الإنتاج). فقاعدةٌ منشورة
# جديدة كانت بلا أيّ طريق إلى طالب. التفصيل في `docs/archive/slices/و-٢١.md` §١.


@blp.route("/admin/users")
class AdminUsers(MethodView):
    @admin_required
    @blp.response(200, RosterListSchema)
    def get(self):
        """السجلّ كاملًا — **بما فيه المعطَّلون**، مُعلَّمين لا مخفيّين."""
        return {"students": roster_service.roster(g.user.org_id)}

    @admin_required
    @blp.arguments(CreateStudentSchema)
    @blp.response(201, IssuedStudentSchema)
    def post(self, data):
        """
        طالبٌ واحد. الرمز **يُولَّد في الخادم ويُعرض مرّة** — لا يُقبَل من
        العميل أصلًا: مشرفٌ يملأ مئتَي رمز بيده سيكتب `1234` للجميع، وهو
        بعينه ما يُسقط `NFR-03`.
        """
        try:
            return roster_service.create_student(
                _org(), data["full_name"], data["student_no"], data["team_id"], g.user.id
            )
        except roster_service.RosterError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/users/bulk")
class AdminUsersBulk(MethodView):
    @admin_required
    @blp.arguments(BulkCreateStudentsSchema)
    @blp.response(201, BulkCreatedSchema)
    def post(self, data):
        """
        لصقةٌ واحدة لمئتَي طالب — **لأن الإفراديّ وحده شاشةٌ لا تُستعمل**.
        السطر الفاشل يُبلَّغ ولا يُسقط الناجح (سابقة استيراد راصد).
        """
        try:
            return roster_service.create_students_bulk(
                _org(), data["rows"], data["team_id"], g.user.id
            )
        except roster_service.RosterError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/users/<int:user_id>/role")
class AdminUserRole(MethodView):
    @admin_required
    @blp.arguments(SetRoleSchema)
    @blp.response(200, RoleSetSchema)
    def patch(self, data, user_id):
        """ترقيةٌ أو تنزيل — **ولا يُنزَّل آخر مشرف**، فلا تُقفَل الجمعية."""
        try:
            return roster_service.set_role(_org(), user_id, data["role"], g.user.id)
        except roster_service.RosterError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/users/<int:user_id>/active")
class AdminUserActive(MethodView):
    @admin_required
    @blp.arguments(SetActiveSchema)
    @blp.response(200, ActiveSetSchema)
    def patch(self, data, user_id):
        """
        تعطيلٌ أو إعادة تفعيل — **لا حذف**: حذف الطالب يتيّم أحداثه (ADR-004).
        والتعطيل يُبطل الجلسات، فكوكي عمرُه تسعون يومًا لا يبقى حيًّا بعده.
        """
        try:
            return roster_service.set_active(_org(), user_id, data["active"], g.user.id)
        except roster_service.RosterError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/users/<int:user_id>/reset-pin")
class ResetPin(MethodView):
    @admin_required
    @blp.response(200, ResetPinSchema)
    def post(self, user_id):
        """
        رمزٌ جديد **يُعرض مرّة واحدة** (FR-004 · `ARCHITECTURE.md` §٧.٥).

        **مسارٌ مستقلّ لا حقلٌ في `PATCH /admin/teams`:** فعلٌ يُبطل كل جلسات
        مستخدم يجب أن يكون صريحًا في العقد، فلا يُطلَق عرَضًا بتغيير لاحق في
        مسار الأسراب (`API.md` §٦).

        والنطاق `org_id` وحده — المشرف على مستوى الجمعية (§٧.٣).
        """
        target = db.session.get(User, user_id)
        if target is None or target.org_id != g.user.org_id:
            # رسالة واحدة لغير الموجود وللخارج عن المنظمة: التفريق يكشف وجود
            # مستخدمين في منظمات أخرى.
            abort(404, message="لا طالب بهذا المعرّف.")

        new_pin = auth_service.reset_pin(g.user.org_id, target, actor_id=g.user.id)
        return {"student_no": target.student_no, "pin": new_pin}
