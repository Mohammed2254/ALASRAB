"""
اعتمادُ القراءات وتحضيرُها — `services/reading.py` يملك الاثنين.

**ومعًا لأنهما نطاقٌ واحد:** التحضير قراءةٌ بنافذةِ أيّامٍ وحدٍّ أدنى
(`activity_type="tahdir"`)، ونفسُ الخدمة ونفسُ الجدول ونفسُ آلية الاعتماد.
"""

from datetime import date

from flask import g, request
from flask.views import MethodView
from flask_smorest import abort

from ...schemas.reading import (
    AdminEntryResultSchema,
    AdminTahdirEntrySchema,
    ApproveSchema,
    OrgTahdirReportSchema,
    QueueSchema,
    RejectSchema,
    ReviewResultsSchema,
)
from ...security import admin_required
from ...services import reading as reading_service
from .._helpers import org_of_session as _org
from . import blp


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
        """
        تقرير التحضير (FR-093) — **يشمل من لم يُرسل شيئًا**.

        `?from=&to=` لفترةٍ محدَّدة، وبدونهما أسبوع اليوم. والفترة تُؤخذ منها
        أيّامُ التحضير في كل أسبوع، فالأسبوع حالةٌ خاصّة لا مسارٌ ثانٍ.
        """
        raw_from = request.args.get("from")
        raw_to = request.args.get("to")
        try:
            from_day = date.fromisoformat(raw_from) if raw_from else None
            to_day = date.fromisoformat(raw_to) if raw_to else None
        except ValueError:
            abort(422, message="تاريخ غير صالح — الصيغة YYYY-MM-DD.")
        try:
            return reading_service.org_tahdir_report(_org(), from_day, to_day)
        except reading_service.ReadingError as exc:
            abort(exc.status, message=str(exc))
