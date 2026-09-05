from decimal import Decimal

from marshmallow import Schema, fields, validate


class StudentRowSchema(Schema):
    id = fields.Int()
    full_name = fields.Str()


class StudentsListSchema(Schema):
    students = fields.List(fields.Nested(StudentRowSchema))


class QuranEventRowSchema(Schema):
    id = fields.Int()
    kind = fields.Str()
    delta = fields.Decimal(as_string=True)
    occurred_on = fields.Date()
    reason = fields.Str(allow_none=True)


class QuranEventsListSchema(Schema):
    events = fields.List(fields.Nested(QuranEventRowSchema))


class ReverseEventSchema(Schema):
    # إلزامي في المخطّط **وفي القاعدة** (ث-٧ الموسَّعة) — نفس نمط `RejectSchema`.
    reason = fields.Str(required=True, validate=validate.Length(min=1, max=500))


class ReversedEventSchema(Schema):
    id = fields.Int()
    delta = fields.Decimal(as_string=True)
    kind = fields.Str()


class AddQuranEntrySchema(Schema):
    user_id = fields.Int(required=True)
    occurred_on = fields.Date(required=True)
    # نصّ مفتوح كـ`WeightRowSchema.activity_type` — يحسمه جدول الأوزان لا كود.
    activity_type = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    quantity = fields.Decimal(
        required=True, as_string=True, validate=validate.Range(min=Decimal("0.01"))
    )
    mastery = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=50))
    reason = fields.Str(required=True, validate=validate.Length(min=1, max=500))


class AddedQuranEntrySchema(Schema):
    id = fields.Int()
    delta = fields.Decimal(as_string=True)
    kind = fields.Str()
