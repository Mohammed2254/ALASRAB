"""
التقرير الدوريّ — `services/reports.py`.

**ونافذةٌ متدحرجة لا أسبوع** (`?days=`، سبعةٌ افتراضًا · `RULES.md §٩.١ب`):
«من تقدّم» سؤالٌ عن الفترة لا عن العمر. وكان هذا المسار تحت فاصل «تحضير
القراءة» في الملفّ الموحَّد — انحرافُ فاصلٍ كشفه التقسيم.
"""

from datetime import timedelta

from flask import request
from flask.views import MethodView

from ...schemas.report import ReportSchema
from ...security import admin_required
from ...services import reports as reports_service
from .._helpers import org_of_session as _org
from . import blp


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
