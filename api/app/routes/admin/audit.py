"""
سجلُّ التغييرات (`FR-084`) — **التعويضُ عن دمج الدورين** (`SCOPE.md §٣.٣`):
من يُدخل الدرجات هو من يضبط قواعد احتسابها، فالحمايةُ تنتقل من *منع
الصلاحية* إلى **كشف الاستعمال**. وقيمتُه مشروطةٌ بكونه مرئيًّا لكل المشرفين.
"""

from flask import g
from flask.views import MethodView

from ...schemas.audit_log import AuditLogSchema
from ...security import admin_required
from ...services import audit as audit_service
from . import blp

# ═══ و-٧ — سجلّ التدقيق (FR-084) ═══


@blp.route("/admin/audit")
class AuditLog(MethodView):
    @admin_required
    @blp.response(200, AuditLogSchema)
    def get(self):
        """
        **مفتوح لكل مشرف بلا حدّ `team_id`** — التعويض عن دمج الدورين (§٧.٣).
        منظمة بلا تغييرات ⇒ `{"entries": []}` صراحةً، لا خطأ (ق-٦١).
        """
        rows = audit_service.list_for_org(g.user.org_id)
        return {
            "entries": [
                {"id": e.id, "kind": e.kind, "summary": e.summary, "actor_name": name, "at": e.at}
                for e, name in rows
            ]
        }
