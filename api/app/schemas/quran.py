from decimal import Decimal

from marshmallow import Schema, fields, validate

from .event import EventRefSchema, EventRowSchema


class StudentRowSchema(Schema):
    id = fields.Int()
    full_name = fields.Str()


class StudentsListSchema(Schema):
    students = fields.List(fields.Nested(StudentRowSchema))


class QuranEventsListSchema(Schema):
    events = fields.List(fields.Nested(EventRowSchema))


class ReverseEventSchema(Schema):
    # إلزامي في المخطّط **وفي القاعدة** (ث-٧ الموسَّعة) — نفس نمط `RejectSchema`.
    reason = fields.Str(required=True, validate=validate.Length(min=1, max=500))


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


class AmendEventSchema(Schema):
    """
    «تعديل» = عكسٌ + بديل. **بلا `user_id`**: البديل يخصّ صاحب الحدث الأصل
    دائمًا — وتمريرُه لفتح بابًا لنقل ساعاتٍ من طالب إلى آخر باسم «تعديل».
    """

    occurred_on = fields.Date(required=True)
    activity_type = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    quantity = fields.Decimal(
        required=True, as_string=True, validate=validate.Range(min=Decimal("0.01"))
    )
    mastery = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=50))
    reason = fields.Str(required=True, validate=validate.Length(min=1, max=500))


class AmendedEventSchema(Schema):
    """الأثر كاملًا: عكسُ الأصل وبديلُه — لا رقمٌ واحد يخفي العملية."""

    correction = fields.Nested(EventRefSchema)
    replacement = fields.Nested(EventRefSchema)
