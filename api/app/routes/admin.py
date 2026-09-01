"""
مسارات المشرف. **حدّ تنسيق لا مكان قواعد.**

وصلاحية المشرف **على مستوى الجمعية** لا السرب (`ARCHITECTURE.md` §٧.٣): لا يُفحص
`team_id` هنا ولا في أي استعلام إداري.
"""

from datetime import timedelta

from flask import g, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..extensions import db
from ..models import Org, User
from ..schemas import (
    ActivitiesListSchema,
    ApproveSchema,
    ArchivedTeamSchema,
    ArchiveTeamSchema,
    AssessedSchema,
    AssessSchema,
    AuditLogSchema,
    CreateActivitySchema,
    CreatedActivitySchema,
    CreatedTeamSchema,
    CreateTeamSchema,
    CreateWeightVersionSchema,
    QueueSchema,
    RejectSchema,
    ReportSchema,
    ResetPinSchema,
    ReviewResultsSchema,
    SaveThresholdsSchema,
    TeamsListSchema,
    ThresholdsPreviewSchema,
    ThresholdsSchema,
    TransferMemberSchema,
    TransferredMemberSchema,
    WeightsSchema,
    WeightVersionIdSchema,
)
from ..security import admin_required
from ..services import audit as audit_service
from ..services import auth as auth_service
from ..services import fuel as fuel_service
from ..services import reading as reading_service
from ..services import reports as reports_service
from ..services import rules_admin as rules_admin_service
from ..services import teams as teams_service

blp = Blueprint("admin", __name__, url_prefix="/api", description="شاشات المشرف")


def _org():
    return db.session.get(Org, g.user.org_id)


@blp.route("/admin/readings")
class ReadingQueue(MethodView):
    @admin_required
    @blp.response(200, QueueSchema)
    def get(self):
        """الطابور **الأقدم أوّلًا** — من انتظر أطول يُبتّ فيه أوّلًا (م-٢)."""
        return {
            "submissions": [
                {
                    "id": s.id,
                    "student_name": name,
                    "read_on": s.read_on,
                    "pages": s.pages,
                    "book_title": s.book_title,
                    "created_at": s.created_at,
                }
                for s, name in reading_service.pending_queue(g.user.org_id)
            ]
        }


@blp.route("/admin/readings/approve")
class ApproveReadings(MethodView):
    @admin_required
    @blp.arguments(ApproveSchema)
    @blp.response(200, ReviewResultsSchema)
    def post(self, data):
        """
        اعتماد **جماعي وذرّي**: فشل واحد ⇒ لا شيء يُلحق (ق-٢٤).

        دفعةٌ نصفية تترك المشرف لا يعرف أين توقّفت، فيعيد الاعتماد كلّه — وهو
        بالضبط ما يجعل الأرقام مشكوكًا فيها.
        """
        try:
            results = reading_service.approve(_org(), data["ids"], g.user.id)
        except reading_service.ReadingError as exc:
            abort(exc.status, message=str(exc))
        return {"results": [r.__dict__ for r in results]}


@blp.route("/admin/readings/<int:submission_id>/reject")
class RejectReading(MethodView):
    @admin_required
    @blp.arguments(RejectSchema)
    @blp.response(200, ReviewResultsSchema)
    def post(self, data, submission_id):
        """الرفض يوجب سببًا **يراه الطالب** (ث-٦ · FR-024)."""
        try:
            result = reading_service.reject(_org(), submission_id, g.user.id, data["reason"])
        except reading_service.ReadingError as exc:
            abort(exc.status, message=str(exc))
        return {"results": [result.__dict__]}


@blp.route("/admin/report")
class Report(MethodView):
    @admin_required
    @blp.response(200, ReportSchema)
    def get(self):
        """
        الملخّص الدوري — **كل رقم مشتقّ من سجلّ الأحداث** بلا جدول ملخّصات
        يفترق عن مصدره (FR-085).
        """
        report = reports_service.build(_org(), request.args.get("days", 7, type=int))
        return {
            "window": {
                "from": report.since.date(),
                "to": report.since.date() + timedelta(days=report.days),
                "days": report.days,
            },
            "totals": {
                "hours": report.total_hours,
                "active_pilots": report.active_pilots,
                "grounded_pilots": len(report.grounded),
            },
            "teams": report.teams,
            "top_movers": report.top_movers,
            "grounded": report.grounded,
        }


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


# ═══ و-٧ — الأوزان (FR-081) ═══


@blp.route("/admin/weights")
class Weights(MethodView):
    @admin_required
    @blp.response(200, WeightsSchema)
    def get(self):
        return rules_admin_service.list_weights(g.user.org_id)

    @admin_required
    @blp.arguments(CreateWeightVersionSchema)
    @blp.response(201, WeightVersionIdSchema)
    def post(self, data):
        """إصدارٌ **جديد** لا تعديل — ث-١١ لا تمسّ الماضي (`docs/slices/و-٧.md`)."""
        try:
            return rules_admin_service.create_weight_version(
                _org(),
                data["effective_from"],
                {w["activity_type"]: w["hours_per_unit"] for w in data["weights"]},
                {m["grade"]: m["multiplier"] for m in data["multipliers"]},
                data["note"],
                g.user.id,
            )
        except rules_admin_service.RulesAdminError as exc:
            abort(exc.status, message=str(exc))


# ═══ و-٧ — العتبات (FR-082) ═══


@blp.route("/admin/thresholds")
class Thresholds(MethodView):
    @admin_required
    @blp.response(200, ThresholdsSchema)
    def get(self):
        return {"thresholds": rules_admin_service.list_thresholds(g.user.org_id)}

    @admin_required
    @blp.arguments(SaveThresholdsSchema)
    @blp.response(200, ThresholdsPreviewSchema)
    def post(self, data):
        """يحفظ ثم يُرجع شكل المعاينة نفسه — ما رآه المشرف هو ما وقع فعلًا."""
        rows = [rules_admin_service.ThresholdRow(**r) for r in data["thresholds"]]
        try:
            return rules_admin_service.save_thresholds(_org(), rows, g.user.id)
        except rules_admin_service.RulesAdminError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/thresholds/preview")
class ThresholdsPreview(MethodView):
    @admin_required
    @blp.arguments(SaveThresholdsSchema)
    @blp.response(200, ThresholdsPreviewSchema)
    def post(self, data):
        """**بلا كتابة.** `demoted` فارغ دائمًا — و-٧ · ت-٢ (ق-٥٠)."""
        rows = [rules_admin_service.ThresholdRow(**r) for r in data["thresholds"]]
        try:
            return rules_admin_service.preview_thresholds(_org(), rows)
        except rules_admin_service.RulesAdminError as exc:
            abort(exc.status, message=str(exc))


# ═══ و-٧ — الأسراب (FR-083) ═══


@blp.route("/admin/teams")
class Teams(MethodView):
    @admin_required
    @blp.response(200, TeamsListSchema)
    def get(self):
        return {"teams": teams_service.list_teams(g.user.org_id)}

    @admin_required
    @blp.arguments(CreateTeamSchema)
    @blp.response(201, CreatedTeamSchema)
    def post(self, data):
        try:
            return teams_service.create_team(_org(), data["name"], data["code"], g.user.id)
        except teams_service.TeamsError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/teams/<int:team_id>")
class TeamDetail(MethodView):
    @admin_required
    @blp.arguments(ArchiveTeamSchema)
    @blp.response(200, ArchivedTeamSchema)
    def patch(self, _data, team_id):
        """أرشفة فقط — لا إلغاء أرشفة اليوم (م-١٠: قرارٌ يستحقّ مسارًا صريحًا)."""
        try:
            return teams_service.archive_team(_org(), team_id, g.user.id)
        except teams_service.TeamsError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/teams/<int:team_id>/members")
class TeamMembers(MethodView):
    @admin_required
    @blp.arguments(TransferMemberSchema)
    @blp.response(200, TransferredMemberSchema)
    def post(self, data, team_id):
        """نقلٌ لا يزوّر التاريخ: العضوية القديمة تُغلَق لا تُحذَف (م-١٠)."""
        try:
            return teams_service.transfer_member(_org(), team_id, data["user_id"], g.user.id)
        except teams_service.TeamsError as exc:
            abort(exc.status, message=str(exc))


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
