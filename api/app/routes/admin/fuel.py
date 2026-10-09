"""
الوقود: الأنشطةُ وتقييمُها (`FR-070` · `FR-071`) وأسبوعُ الوقود
(`FR-073`..`FR-075`).

**ومسوّدةٌ ثمّ اعتمادٌ واحد**: الدرجاتُ لا أثر لها في الدفتر حتى الاعتماد،
والأحداثُ تُؤرَّخ **ببداية الأسبوع المُقيَّم لا باليوم** — فتقييمٌ متأخّر
يقع في مكانه الصحيح.

و`_requested_week` أدناه لهذه المسارات وحدها، وكان في الملفّ الموحَّد داخل
قسم راصد.
"""

from datetime import UTC, date, datetime

from flask import g, request
from flask.views import MethodView
from flask_smorest import abort

from ...schemas.fuel import (
    ActivitiesListSchema,
    AssessedSchema,
    AssessSchema,
    AssignTeamSchema,
    CreateActivitySchema,
    CreatedActivitySchema,
    FuelWeekSchema,
    WeekScoresSchema,
    WeekTaskRefSchema,
)
from ...security import admin_required
from ...services import fuel as fuel_service
from ...services import fuel_week as fuel_week_service
from ...services import week as week_service
from .._helpers import org_of_session as _org
from . import blp


def _requested_week(org) -> date:
    """
    `?week_start=YYYY-MM-DD` ⇒ بداية الأسبوع الذي يقع فيه، وبدونه أسبوع اليوم.

    **يُطبَّع دائمًا** عبر `week_service`: تاريخٌ وسط الأسبوع يعطي بدايته، فلا
    يُنشأ «أسبوع» مفتاحه يوم ثلاثاء لأن المشرف أرسل ذلك التاريخ.
    """
    raw = request.args.get("week_start")
    if not raw:
        return week_service.week_start_local(org, datetime.now(UTC))
    try:
        return week_service.week_start_of(org, date.fromisoformat(raw))
    except ValueError:
        abort(422, message="تاريخ الأسبوع غير صالح — الصيغة YYYY-MM-DD.")


# ═══ و-٨ — الوقود (FR-070 · FR-071) ═══


@blp.route("/admin/fuel/activities")
class FuelActivities(MethodView):
    @admin_required
    @blp.response(200, ActivitiesListSchema)
    def get(self):
        return {"activities": fuel_service.list_activities(g.user.org_id)}

    @admin_required
    @blp.arguments(CreateActivitySchema)
    @blp.response(201, CreatedActivitySchema)
    def post(self, data):
        """إنشاءٌ **جديد** — لا تعديل على نشاط قائم. ث-١٠أ: الأوزان تجمع ١٠٠٪."""
        try:
            return fuel_service.create_activity(
                _org(), data["key"], data["name"], data["litres_full"], data["criteria"]
            )
        except fuel_service.FuelError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/fuel/assess")
class FuelAssess(MethodView):
    @admin_required
    @blp.arguments(AssessSchema)
    @blp.response(201, AssessedSchema)
    def post(self, data):
        """
        تقييمٌ **جديد**. `team_id` صريح — المشرف على مستوى الجمعية يقيّم أيّ
        سرب (§٧.٣). ث-١٠ب: أوزان البنود المُقيَّمة فعلًا تجمع ١٠٠٪.
        """
        scores = {s["criterion_id"]: s["score_pct"] for s in data["scores"]}
        try:
            return fuel_service.assess(
                _org(),
                data["team_id"],
                data["activity_id"],
                data["occurred_on"],
                scores,
                data["note"],
                g.user.id,
            )
        except fuel_service.FuelError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/fuel/week")
class FuelWeekView(MethodView):
    @admin_required
    @blp.response(200, FuelWeekSchema)
    def get(self):
        """
        حالة أسبوع الوقود — `?week_start=YYYY-MM-DD`، وبدونه أسبوع اليوم.

        **بلا كتابة**: أسبوعٌ لم يُفتح يُعرَض بقائمته الافتراضية، فتصفّحُ
        الماضي لا يترك صفوفًا فارغة خلفه.
        """
        org = _org()
        return fuel_week_service.week_view(org, _requested_week(org))


@blp.route("/admin/fuel/week/team")
class FuelWeekTeam(MethodView):
    @admin_required
    @blp.arguments(AssignTeamSchema)
    @blp.response(200, FuelWeekSchema)
    def post(self, data):
        """تعيين سربٍ لمهمّة — «لكل سرب مهمّة واحدة» إرشادٌ لا قيد."""
        org = _org()
        try:
            return fuel_week_service.set_task_team(
                org, _requested_week(org), data["activity_id"], data["team_id"]
            )
        except fuel_service.FuelError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/fuel/week/tasks")
class FuelWeekTasks(MethodView):
    @admin_required
    @blp.arguments(WeekTaskRefSchema)
    @blp.response(200, FuelWeekSchema)
    def post(self, data):
        """إضافة مهمّة **لهذا الأسبوع وحده**."""
        org = _org()
        try:
            return fuel_week_service.add_task(org, _requested_week(org), data["activity_id"])
        except fuel_service.FuelError as exc:
            abort(exc.status, message=str(exc))

    @admin_required
    @blp.arguments(WeekTaskRefSchema)
    @blp.response(200, FuelWeekSchema)
    def delete(self, data):
        """إزالة مهمّة **لهذا الأسبوع وحده** — لا تمسّ النشاط ولا أسبوعًا آخر."""
        org = _org()
        try:
            return fuel_week_service.remove_task(org, _requested_week(org), data["activity_id"])
        except fuel_service.FuelError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/fuel/week/scores")
class FuelWeekScores(MethodView):
    @admin_required
    @blp.arguments(WeekScoresSchema)
    @blp.response(200, FuelWeekSchema)
    def post(self, data):
        """درجاتٌ **مسوّدة** — لا حدث دفتر، ولا فحص «تجمع ١٠٠٪» إلا عند الاعتماد."""
        scores = {s["criterion_id"]: s["score_pct"] for s in data["scores"]}
        org = _org()
        try:
            return fuel_week_service.save_scores(
                org, _requested_week(org), data["activity_id"], scores
            )
        except fuel_service.FuelError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/fuel/week/approve")
class FuelWeekApprove(MethodView):
    @admin_required
    @blp.response(200, FuelWeekSchema)
    def post(self):
        """
        اعتماد الأسبوع — **مرّةً واحدة**، والأحداث مؤرَّخة ببداية الأسبوع لا
        باليوم (فتقييمٌ متأخّر يقع في مكانه من الدفتر).
        """
        org = _org()
        try:
            return fuel_week_service.approve_week(
                org, _requested_week(org), g.user.id, datetime.now(UTC)
            )
        except fuel_service.FuelError as exc:
            abort(exc.status, message=str(exc))
