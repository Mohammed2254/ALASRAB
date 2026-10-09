"""
الصندوق الأسود وطيّارُ الأسبوع (`FR-061` · `FR-062`).

**والملاحظةُ مجهولةٌ بنيةَ الجدول** لا بسياسة: لا حقلَ مرسِلٍ ولا IP،
و`day` بلا ساعة عمدًا (`NFR-04`). تُعلَّم مقروءةً ولا تُحذف.
"""

from flask import g
from flask.views import MethodView
from flask_smorest import abort

from ...extensions import db
from ...models import User
from ...schemas.engagement import (
    AdminNotesListSchema,
    ChooseWeekPilotSchema,
    ChosenWeekPilotSchema,
    MarkedNoteSchema,
    MarkNoteReadSchema,
)
from ...security import admin_required
from ...services import engagement as engagement_service
from .._helpers import org_of_session as _org
from . import blp


@blp.route("/admin/notes")
class AdminNotes(MethodView):
    @admin_required
    @blp.response(200, AdminNotesListSchema)
    def get(self):
        """الملاحظات — بلا مصدر ولا قناة ردّ أصلًا (ث-١٢ · م-٥)."""
        return {"notes": engagement_service.list_notes(g.user.org_id)}


@blp.route("/admin/notes/<int:note_id>")
class AdminNoteDetail(MethodView):
    @admin_required
    @blp.arguments(MarkNoteReadSchema)
    @blp.response(200, MarkedNoteSchema)
    def patch(self, _data, note_id):
        """تعليم مقروءة فقط — لا حذف ولا رجوع (م-٥)."""
        try:
            return engagement_service.mark_note_read(g.user.org_id, note_id)
        except engagement_service.EngagementError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/week/pilot")
class AdminWeekPilot(MethodView):
    @admin_required
    @blp.arguments(ChooseWeekPilotSchema)
    @blp.response(201, ChosenWeekPilotSchema)
    def post(self, data):
        """اختيار طيار الأسبوع — واحدٌ لكل أسبوع (ث-٩ · FR-062 · م-٦)."""
        try:
            row = engagement_service.choose_week_pilot(
                _org(), g.user.id, data["user_id"], data["reason"], data["bonus_hours"]
            )
        except engagement_service.EngagementError as exc:
            abort(exc.status, message=str(exc))
        pilot = db.session.get(User, row.user_id)
        return {
            "user_id": row.user_id,
            "full_name": pilot.full_name,
            "week_start": row.week_start,
            "bonus_hours": row.bonus_hours,
        }
