"""
استيرادُ راصد والحضور — **معًا لأنهما يتقاسمان `paste_service`**:
`AttendanceFromRasd` ينادي `paste_service.latest_import_view`، فالحضورُ
يُقرَأ من آخر استيرادٍ لا من إدخالٍ مستقلّ.

والخطّافان أدناه للّصق وحده، وكانا في الملفّ الموحَّد بين خطّافاتٍ تخصّ
نطاقاتٍ أخرى.
"""

import json
from datetime import date
from decimal import Decimal

from flask import g, request
from flask.views import MethodView
from flask_smorest import abort

from ...schemas.entry import (
    AttendanceStatusSchema,
    RecordAttendanceSchema,
    RecordedAttendanceSchema,
    UndoneAttendanceSchema,
)
from ...schemas.paste import PasteCommitResultSchema, PastePreviewSchema, RasdLatestImportSchema
from ...security import admin_required
from ...services import entry as entry_service
from ...services import paste as paste_service
from .._helpers import org_of_session as _org
from . import blp

# ═══ و-٥ — استيراد راصد (FR-030..034/040) ═══
#
# **الاسم تاريخيّ لا وظيفيّ** (`docs/archive/slices/و-٥.md` §٢ قرار #١٠): الأصل كان
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


@blp.route("/admin/attendance/rasd")
class AttendanceFromRasd(MethodView):
    @admin_required
    @blp.response(200, RasdLatestImportSchema)
    def get(self):
        """
        حضور آخر استيراد راصد — **للعرض فقط**، لا يُعدَّل هنا (النموذج).

        والإدخال اليدويّ أعلاه يبقى **احتياطيًّا موثَّقًا** كما صُمّم
        (FR-041/042): راصد المصدر الأساسيّ، لا المصدر الوحيد.
        """
        return paste_service.latest_import_view(_org())


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
