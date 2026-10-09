"""
الأوزان والعتبات — `services/rules_admin.py` يملك الاثنين (`FR-081` ·
`FR-082`).

**ومعًا لأنهما خدمةٌ واحدة**، وكانت مشتّتةً في الملفّ الموحَّد على ثلاثة
فواصل — و`AppendThreshold` تحت فاصل «الأسراب».
"""

from flask import g
from flask.views import MethodView
from flask_smorest import abort

from ...schemas.rules_admin import (
    AppendThresholdSchema,
    CreateWeightVersionSchema,
    SaveThresholdsSchema,
    ThresholdsPreviewSchema,
    ThresholdsSchema,
    WeightsSchema,
    WeightVersionIdSchema,
)
from ...security import admin_required
from ...services import rules_admin as rules_admin_service
from .._helpers import org_of_session as _org
from . import blp

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
        """إصدارٌ **جديد** لا تعديل — ث-١١ لا تمسّ الماضي (`docs/archive/slices/و-٧.md`)."""
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


@blp.route("/admin/thresholds/append")
class AppendThreshold(MethodView):
    @admin_required
    @blp.arguments(AppendThresholdSchema)
    @blp.response(200, ThresholdsPreviewSchema)
    def post(self, data):
        """
        رتبةٌ جديدة **في قمّة السُّلّم وحدها** — «+ إضافة رتبة» (و-٢١).

        ومسارٌ مستقلّ لا حقلٌ في `POST /admin/thresholds`: ذاك يستبدل السُّلّم
        كاملًا بما يُرسله العميل، وهذا يُلحق بقاعدةٍ يحرسها الخادم. ودمجُهما
        يعني أن الواجهة تحسب `tier` — وهي لا تحسب (`AGENTS.md`).
        """
        try:
            return rules_admin_service.append_threshold(
                _org(), data["name"], data["at_hours"], g.user.id
            )
        except rules_admin_service.RulesAdminError as exc:
            # `exc.status` لا ٤٢٢ مُثبَّتًا: هذا كان **المعالجَ الوحيدَ** من
            # أربعين يُثبّت الرمز. والسلوكُ اليوم واحدٌ (كلُّ رفعةٍ تستعمل
            # افتراضَ `ServiceError`)، فالعطلُ **مؤجَّلٌ لا غائب**: أوّلُ رفعةٍ
            # بـ`status=409` تُسطَّح إلى ٤٢٢ صامتةً.
            abort(exc.status, message=str(exc))
