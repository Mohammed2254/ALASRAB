"""
سؤال اليوم — الشقّ الإداريّ (و-٢١). `SCOPE.md` ط-٦ أعلن غياب مسار الإنشاء،
و`FR-060` بندٌ **MUST** — فشاشةٌ ميتةٌ على خادمٍ منشور لا تصحّ له.
"""

from marshmallow import Schema, fields, validate

from ..services.daily_question import MAX_CHOICES, MIN_CHOICES


class QuestionChoiceSchema(Schema):
    id = fields.Int(required=True, validate=validate.Range(min=1))
    text = fields.Str(required=True, validate=validate.Length(min=1, max=200))


class QuestionRowSchema(Schema):
    id = fields.Int()
    day = fields.Str()
    prompt = fields.Str()
    choices = fields.List(fields.Nested(QuestionChoiceSchema))
    correct_id = fields.Int()
    note = fields.Str()
    reward_hours = fields.Decimal(as_string=True)
    answers = fields.Int()
    # **حقلٌ معلَن لا استنتاج من `answers > 0` في الواجهة**: «مُقفَل» قاعدةٌ
    # (ث-١٧) لا عرض، ومقارنةٌ في الشاشة تُسقطها بوّابة AST أصلًا.
    locked = fields.Bool()


class QuestionsListSchema(Schema):
    questions = fields.List(fields.Nested(QuestionRowSchema))


class _QuestionBodySchema(Schema):
    prompt = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    choices = fields.List(
        fields.Nested(QuestionChoiceSchema),
        required=True,
        validate=validate.Length(min=MIN_CHOICES, max=MAX_CHOICES),
    )
    correct_id = fields.Int(required=True)
    # مطلوبٌ لا اختياريّ: `FR-060` يوجب ظهور «الجواب الصحيح **وشرحه**» في
    # الحالتين — فالشرح نصفُ المتطلَّب لا تحسينٌ له.
    note = fields.Str(required=True, validate=validate.Length(min=1, max=1000))
    reward_hours = fields.Decimal(required=True, as_string=True, validate=validate.Range(min=0))


class CreateQuestionSchema(_QuestionBodySchema):
    day = fields.Date(required=True)


class UpdateQuestionSchema(_QuestionBodySchema):
    """**بلا `day`**: نقلُ سؤالٍ إلى يومٍ آخر مساوٍ لحذفه وإنشائه، ومسارٌ صريح أوضح."""


class QuestionRefSchema(Schema):
    id = fields.Int()
    day = fields.Str()
