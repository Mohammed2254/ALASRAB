from marshmallow import Schema, fields


class AuditEntrySchema(Schema):
    id = fields.Int()
    kind = fields.Str()
    summary = fields.Str()
    # اسم الفاعل لا معرّفه وحده — الشاشة قائمة تُقرَأ لا واجهة تُطابِق (FR-084).
    actor_name = fields.Str()
    at = fields.DateTime()


class AuditLogSchema(Schema):
    # فارغة صراحةً لا خطأ — ق-٦١: منظمة بلا تغييرات ترجع {"entries": []}.
    entries = fields.List(fields.Nested(AuditEntrySchema))
