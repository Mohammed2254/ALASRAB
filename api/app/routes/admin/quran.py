"""
التصحيحُ والتعديل القرآنيّ (`FR-035`..`FR-037` · `FR-080`).

**والتصحيحُ حدثٌ معاكس لا تعديلُ صفّ** (ADR-004): الدفترُ يُلحَق ولا
يُعدَّل، فالخطأُ يُعالَج بحدثٍ يُلغيه لا بمحوِه.
"""

from flask import g, request
from flask.views import MethodView
from flask_smorest import abort

from ...schemas.quran import (
    AddQuranEntrySchema,
    AmendedEventSchema,
    AmendEventSchema,
    EventRefSchema,
    QuranEventsListSchema,
    ReverseEventSchema,
    StudentsListSchema,
)
from ...security import admin_required
from ...services import quran as quran_service
from .._helpers import org_of_session as _org
from . import blp

# ═══ و-٦ — التصحيح والتعديل القرآني (FR-035 · FR-036 · FR-037 · FR-080) ═══


@blp.route("/admin/quran/students")
class QuranStudents(MethodView):
    @admin_required
    @blp.response(200, StudentsListSchema)
    def get(self):
        """قائمة اختيار الهدف — **على مستوى الجمعية** (§٧.٣)، بنية تحتية لـFR-036."""
        return {
            "students": [
                {"id": u.id, "full_name": u.full_name} for u in quran_service.roster(g.user.org_id)
            ]
        }


@blp.route("/admin/quran/events")
class QuranEvents(MethodView):
    @admin_required
    @blp.response(200, QuranEventsListSchema)
    def get(self):
        """أحدث أحداث طالب، ليختار المشرف أيّها يُصحَّح — بنية تحتية لـFR-035."""
        user_id = request.args.get("user_id", type=int)
        if user_id is None:
            abort(422, message="user_id إلزاميّ.")
        try:
            events = quran_service.recent_events_for(_org(), user_id)
        except quran_service.QuranError as exc:
            abort(exc.status, message=str(exc))
        return {
            "events": [
                {
                    "id": e.id,
                    "kind": e.kind,
                    "delta": e.delta,
                    "occurred_on": e.occurred_at.date(),
                    "reason": e.reason,
                }
                for e in events
            ]
        }


@blp.route("/admin/events/<int:event_id>/reverse")
class ReverseEvent(MethodView):
    @admin_required
    @blp.arguments(ReverseEventSchema)
    @blp.response(201, EventRefSchema)
    def post(self, data, event_id):
        """
        FR-035 · FR-080 — تصحيحٌ **حدث معاكس بسبب إلزامي**، لا `UPDATE` ولا
        `DELETE` أبدًا (`ADR-004`). يكتب `audit_log` ذرّيًّا مع الحدث (FR-037).
        """
        try:
            return quran_service.reverse(_org(), event_id, data["reason"], g.user.id)
        except quran_service.QuranError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/events/<int:event_id>/amend")
class AmendEvent(MethodView):
    @admin_required
    @blp.arguments(AmendEventSchema)
    @blp.response(201, AmendedEventSchema)
    def post(self, data, event_id):
        """
        «تعديل» في النموذج المعتمد = **عكسٌ + بديل في معاملةٍ واحدة**.

        ADR-004 يمنع `UPDATE`/`DELETE` على الدفتر، والمشرف يريد تصحيح رقمٍ لا
        محوَ تاريخ — فالشكل مطابقٌ للنموذج والثابت محفوظ، ويبقى الأثر كاملًا:
        أصلٌ وعكسٌ وبديل.
        """
        try:
            return quran_service.amend(
                _org(),
                event_id,
                data["reason"],
                g.user.id,
                occurred_on=data["occurred_on"],
                activity_type=data["activity_type"],
                quantity=data["quantity"],
                mastery=data["mastery"],
            )
        except quran_service.QuranError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/quran/entry")
class QuranEntry(MethodView):
    @admin_required
    @blp.arguments(AddQuranEntrySchema)
    @blp.response(201, EventRefSchema)
    def post(self, data):
        """
        FR-036 — إضافة سجلّ ناقص يدويًّا. **الساعات محسوبة عبر `rules/engine`**
        لا مُدخَلة (AGENTS ٥)، و**بلا `raw_row_id`** (مستقلّ عن اللصق).
        """
        try:
            return quran_service.add_entry(
                _org(),
                data["user_id"],
                data["occurred_on"],
                data["activity_type"],
                data["quantity"],
                data["mastery"],
                data["reason"],
                g.user.id,
            )
        except quran_service.QuranError as exc:
            abort(exc.status, message=str(exc))
