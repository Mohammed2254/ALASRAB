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
from ..models import Org
from ..schemas import ApproveSchema, QueueSchema, RejectSchema, ReportSchema, ReviewResultsSchema
from ..security import admin_required
from ..services import reading as reading_service
from ..services import reports as reports_service

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
