"""
مسارات المشرف. **حدّ تنسيق لا مكان قواعد.**

وصلاحية المشرف **على مستوى الجمعية** لا السرب (`ARCHITECTURE.md` §٧.٣): لا يُفحص
`team_id` هنا ولا في أي استعلام إداري.
"""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from flask import g, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..extensions import db
from ..models import Org, User
from ..schemas import (
    ActivitiesListSchema,
    AddedQuranEntrySchema,
    AddQuranEntrySchema,
    AdminEntryResultSchema,
    AdminNotesListSchema,
    AdminTahdirEntrySchema,
    ApproveSchema,
    ArchivedTeamSchema,
    ArchiveTeamSchema,
    AssessedSchema,
    AssessSchema,
    AssignTeamSchema,
    AttendanceStatusSchema,
    AuditLogSchema,
    ChooseWeekPilotSchema,
    ChosenWeekPilotSchema,
    CreateActivitySchema,
    CreatedActivitySchema,
    CreatedTeamSchema,
    CreateTeamSchema,
    CreateWeightVersionSchema,
    FuelWeekSchema,
    MarkedNoteSchema,
    MarkNoteReadSchema,
    OrgTahdirReportSchema,
    PasteCommitResultSchema,
    PastePreviewSchema,
    QueueSchema,
    QuranEventsListSchema,
    RecordAttendanceSchema,
    RecordedAttendanceSchema,
    RejectSchema,
    ReportSchema,
    ResetPinSchema,
    ReversedEventSchema,
    ReverseEventSchema,
    ReviewResultsSchema,
    SaveThresholdsSchema,
    StudentsListSchema,
    TeamsListSchema,
    ThresholdsPreviewSchema,
    ThresholdsSchema,
    TransferMemberSchema,
    TransferredMemberSchema,
    UndoneAttendanceSchema,
    WeekScoresSchema,
    WeekTaskRefSchema,
    WeightsSchema,
    WeightVersionIdSchema,
)
from ..security import admin_required
from ..services import audit as audit_service
from ..services import auth as auth_service
from ..services import engagement as engagement_service
from ..services import entry as entry_service
from ..services import fuel as fuel_service
from ..services import fuel_week as fuel_week_service
from ..services import paste as paste_service
from ..services import quran as quran_service
from ..services import reading as reading_service
from ..services import reports as reports_service
from ..services import rules_admin as rules_admin_service
from ..services import teams as teams_service
from ..services import week as week_service

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


# ═══ و-٥ — استيراد راصد (FR-030..034/040) ═══
#
# **الاسم تاريخيّ لا وظيفيّ** (`docs/slices/و-٥.md` §٢ قرار #١٠): الأصل كان
# لصق نصّ قبل وصول عيّنة راصد الحقيقية، والفعليّ اليوم استيراد ملفّ CSV —
# ولا داعي لكسر مسار موثَّق سلفًا لتغيّر تفصيل التنفيذ.
#
# **multipart/form-data لا JSON** — ملفّ حقيقيّ لا يلائم `@blp.arguments`
# القائم على مخطّط JSON، فالحقول تُقرَأ مباشرةً من `request.files`/
# `request.form` هنا، ومخطّط الردّ وحده مُعلَن.


def _parse_occurred_on() -> date:
    raw = request.form.get("occurred_on")
    try:
        return date.fromisoformat(raw)
    except (TypeError, ValueError):
        abort(422, message="تاريخ الوقوع مطلوب بصيغة YYYY-MM-DD.")


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


def _read_uploaded_file() -> bytes:
    uploaded = request.files.get("file")
    if uploaded is None:
        abort(422, message="الملفّ مطلوب.")
    return uploaded.read()


@blp.route("/admin/paste/preview")
class PastePreview(MethodView):
    @admin_required
    @blp.response(200, PastePreviewSchema)
    def post(self):
        """**بلا كتابة** (ق-١٩٢) — لا `raw_rows`، لا حدث."""
        file_bytes = _read_uploaded_file()
        occurred_on = _parse_occurred_on()
        try:
            return paste_service.preview(_org(), file_bytes, occurred_on)
        except paste_service.PasteError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/paste/commit")
class PasteCommit(MethodView):
    @admin_required
    @blp.response(201, PasteCommitResultSchema)
    def post(self):
        """
        raw_rows تُكتب دائمًا لكل صفّ طالب حقيقيّ، ثم إلحاق الجديد فقط —
        ما سبق استيراده (نفس تاريخ/طالب/نشاط) يُستبعَد صراحةً بلا رفض الدفعة.
        """
        file_bytes = _read_uploaded_file()
        occurred_on = _parse_occurred_on()
        try:
            name_resolutions = {
                k: int(v)
                for k, v in json.loads(request.form.get("name_resolutions") or "{}").items()
            }
            value_overrides = {
                name: {field: Decimal(str(v)) for field, v in overrides.items()}
                for name, overrides in json.loads(
                    request.form.get("value_overrides") or "{}"
                ).items()
            }
        except (ValueError, TypeError, AttributeError):
            abort(422, message="صيغة قرارات المشرف (name_resolutions/value_overrides) غير صالحة.")

        try:
            return paste_service.commit(
                _org(),
                g.user.id,
                file_bytes,
                occurred_on,
                name_resolutions,
                value_overrides,
            )
        except paste_service.PasteError as exc:
            abort(exc.status, message=str(exc))


# ═══ و-١١ — تحضير القراءة (FR-090..093) ═══


@blp.route("/admin/tahdir")
class TahdirQueue(MethodView):
    @admin_required
    @blp.response(200, QueueSchema)
    def get(self):
        """
        طابور تحضير القراءة وحده — **مُصفًّى عن `/admin/readings`** (FR-092
        بنية تحتية). الاعتماد والرفض عبر `/admin/readings/approve`·`reject`
        القائمين حرفيًّا — عامّان على معرّف الطلب بصرف النظر عن `activity_type`.
        """
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
                for s, name in reading_service.pending_queue(
                    g.user.org_id, activity_type=reading_service.TAHDIR
                )
            ]
        }


@blp.route("/admin/tahdir/entry")
class TahdirEntry(MethodView):
    @admin_required
    @blp.arguments(AdminTahdirEntrySchema)
    @blp.response(201, AdminEntryResultSchema)
    def post(self, data):
        """
        إضافة مباشرة نيابةً عن طالب — **معتمَدة فورًا** (FR-092، نمط
        `POST /admin/quran/entry` من و-٦). نفس قيود `/me/tahdir` تسري هنا
        حرفيًّا — لا استثناء إداريّ ليوم الأسبوع أو الحدّ الأدنى.
        """
        try:
            result = reading_service.admin_submit(
                _org(),
                g.user.id,
                data["user_id"],
                data["read_on"],
                data["pages"],
                data["book_title"],
                activity_type=data["activity_type"],
            )
        except reading_service.ReadingError as exc:
            abort(exc.status, message=str(exc))
        return {"id": result.submission_id, "status": result.status, "hours": result.hours}


@blp.route("/admin/tahdir/report")
class TahdirReport(MethodView):
    @admin_required
    @blp.response(200, OrgTahdirReportSchema)
    def get(self):
        """تقرير أسبوعيّ لكل طلاب الجمعية (FR-093) — **يشمل من لم يُرسل شيئًا**."""
        return reading_service.org_weekly_report(_org())


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
        return fuel_week_service.week_view(_org(), _requested_week(_org()))


@blp.route("/admin/fuel/week/team")
class FuelWeekTeam(MethodView):
    @admin_required
    @blp.arguments(AssignTeamSchema)
    @blp.response(200, FuelWeekSchema)
    def post(self, data):
        """تعيين سربٍ لمهمّة — «لكل سرب مهمّة واحدة» إرشادٌ لا قيد."""
        try:
            return fuel_week_service.set_task_team(
                _org(), _requested_week(_org()), data["activity_id"], data["team_id"]
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
        try:
            return fuel_week_service.add_task(_org(), _requested_week(_org()), data["activity_id"])
        except fuel_service.FuelError as exc:
            abort(exc.status, message=str(exc))

    @admin_required
    @blp.arguments(WeekTaskRefSchema)
    @blp.response(200, FuelWeekSchema)
    def delete(self, data):
        """إزالة مهمّة **لهذا الأسبوع وحده** — لا تمسّ النشاط ولا أسبوعًا آخر."""
        try:
            return fuel_week_service.remove_task(
                _org(), _requested_week(_org()), data["activity_id"]
            )
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
        try:
            return fuel_week_service.save_scores(
                _org(), _requested_week(_org()), data["activity_id"], scores
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
        try:
            return fuel_week_service.approve_week(
                _org(), _requested_week(_org()), g.user.id, datetime.now(UTC)
            )
        except fuel_service.FuelError as exc:
            abort(exc.status, message=str(exc))


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
                _org(), g.user.id, data["user_id"], data["reason"]
            )
        except engagement_service.EngagementError as exc:
            abort(exc.status, message=str(exc))
        pilot = db.session.get(User, row.user_id)
        return {"user_id": row.user_id, "full_name": pilot.full_name, "week_start": row.week_start}


@blp.route("/admin/attendance")
class Attendance(MethodView):
    @admin_required
    @blp.response(200, AttendanceStatusSchema)
    def get(self):
        """قائمة السرب وحالة الأسبوع الحالي — للشاشة عند الفتح (FR-041)."""
        return entry_service.week_status(_org())

    @admin_required
    @blp.arguments(RecordAttendanceSchema)
    @blp.response(201, RecordedAttendanceSchema)
    def post(self, data):
        """**الجميع حاضر افتراضًا** — الطلب يحمل الغائبين فقط (FR-041 · FR-042)."""
        try:
            return entry_service.record(_org(), g.user.id, data["absent_user_ids"])
        except entry_service.AttendanceError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/attendance/undo")
class AttendanceUndo(MethodView):
    @admin_required
    @blp.response(200, UndoneAttendanceSchema)
    def post(self):
        """تراجعٌ عن دفعة الأسبوع الحالي كاملةً، خلال ٥ دقائق (FR-042)."""
        try:
            count = entry_service.undo(_org(), g.user.id)
        except entry_service.AttendanceError as exc:
            abort(exc.status, message=str(exc))
        return {"reversed": count}


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
    @blp.response(201, ReversedEventSchema)
    def post(self, data, event_id):
        """
        FR-035 · FR-080 — تصحيحٌ **حدث معاكس بسبب إلزامي**، لا `UPDATE` ولا
        `DELETE` أبدًا (`ADR-004`). يكتب `audit_log` ذرّيًّا مع الحدث (FR-037).
        """
        try:
            return quran_service.reverse(_org(), event_id, data["reason"], g.user.id)
        except quran_service.QuranError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/quran/entry")
class QuranEntry(MethodView):
    @admin_required
    @blp.arguments(AddQuranEntrySchema)
    @blp.response(201, AddedQuranEntrySchema)
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
