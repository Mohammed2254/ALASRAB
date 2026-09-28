from marshmallow import Schema, fields

# ملاحظة: لا مخطَّط لجسم الطلب هنا — `/admin/paste/*` تستقبل `multipart/
# form-data` (ملفّ + حقول نصّية)، فتُقرَأ في المسار مباشرةً من
# `request.files`/`request.form` (نمط لا يلائم `@blp.arguments` القائم على
# JSON). مخطَّطات الردّ وحدها هنا.


class PastePreviewTotalsSchema(Schema):
    """ما سيُكتب فعلًا، معدودًا **قبل** الكتابة — «لا استيراد بلا معاينة مقروءة»."""

    rows = fields.Int()
    rows_resolved = fields.Int()
    rows_needing_attention = fields.Int()
    events_new = fields.Int()
    events_already_imported = fields.Int()
    events_skipped_zero = fields.Int()
    # عشريٌّ نصّيّ لا `Str`: مجموع ساعاتٍ حقيقيّ، فتراه بوابة العقد (ق-٢١٩)
    # وتُلزم نظيره في TS بـ`Decimal` — «"611.25" عشريٌّ لا رقم» (ADR-009).
    hours_total = fields.Decimal(as_string=True)


class PastePreviewRowSchema(Schema):
    name = fields.Str()
    match_status = fields.Str()  # 'matched' | 'ambiguous' | 'unmatched'
    # حالة الصفّ في الخطّة: 'resolved' | 'unmatched' | 'ambiguous' | 'no_active_team'
    status = fields.Str()
    user_id = fields.Int(allow_none=True)
    candidate_ids = fields.List(fields.Int())
    percentages = fields.Dict(keys=fields.Str(), values=fields.Str())
    attendance = fields.Str()
    tasmi3_days = fields.Str()
    # فئة ⇒ {status, hours?} — نفس شكل ردّ التنفيذ بالضبط، لأنّها الخطّة نفسها.
    categories = fields.Dict(keys=fields.Str(), values=fields.Dict())


class PastePreviewSchema(Schema):
    batch_id = fields.Str()
    duplicate_warning = fields.Bool()
    duplicate_imported_at = fields.Str(allow_none=True)
    # تسميات صفوف التذييل المستبعَدة — الاستبعاد مُعلَن لا صامت.
    excluded_labels = fields.List(fields.Str())
    # لا نسخة أوزان سارية للتاريخ المطلوب: المعاينة تعمل، والاحتساب فارغ.
    weights_missing = fields.Bool()
    totals = fields.Nested(PastePreviewTotalsSchema)
    rows = fields.List(fields.Nested(PastePreviewRowSchema))


class PasteRowResultSchema(Schema):
    name = fields.Str()
    status = fields.Str()  # 'resolved' | 'unmatched' | 'ambiguous' | 'no_active_team'
    user_id = fields.Int(allow_none=True)
    categories = fields.Dict(keys=fields.Str(), values=fields.Dict())


class PasteCommitResultSchema(Schema):
    batch_id = fields.Str()
    rows = fields.List(fields.Nested(PasteRowResultSchema))
    events_created = fields.Int()


class RasdAttendanceRowSchema(Schema):
    name = fields.Str()
    team_name = fields.Str(allow_none=True)
    # عددٌ نصّيّ كما ورد في الملفّ — لا حاضر/غائب (`٢` من `أيام التسميع`).
    attendance = fields.Str()
    tasmi3_days = fields.Str()
    matched = fields.Bool()


class RasdLatestImportSchema(Schema):
    """آخر استيراد راصد — `null` قبل أوّل استيراد، حالةٌ مصمَّمة لا عطل."""

    imported_at = fields.Str(allow_none=True)
    rows = fields.List(fields.Nested(RasdAttendanceRowSchema))
