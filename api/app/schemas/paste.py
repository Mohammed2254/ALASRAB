from marshmallow import Schema, fields

# ملاحظة: لا مخطَّط لجسم الطلب هنا — `/admin/paste/*` تستقبل `multipart/
# form-data` (ملفّ + حقول نصّية)، فتُقرَأ في المسار مباشرةً من
# `request.files`/`request.form` (نمط لا يلائم `@blp.arguments` القائم على
# JSON). مخطَّطات الردّ وحدها هنا.


class PastePreviewRowSchema(Schema):
    name = fields.Str()
    match_status = fields.Str()  # 'matched' | 'ambiguous' | 'unmatched'
    user_id = fields.Int(allow_none=True)
    candidate_ids = fields.List(fields.Int())
    percentages = fields.Dict(keys=fields.Str(), values=fields.Str())
    attendance = fields.Str()
    tasmi3_days = fields.Str()


class PastePreviewSchema(Schema):
    batch_id = fields.Str()
    duplicate_warning = fields.Bool()
    duplicate_imported_at = fields.Str(allow_none=True)
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
