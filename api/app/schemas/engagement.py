from decimal import Decimal

from marshmallow import Schema, fields, validate


class ChoiceSchema(Schema):
    id = fields.Int()
    text = fields.Str()


class AnsweredSchema(Schema):
    choice_id = fields.Int()
    correct = fields.Bool()
    # يظهران دائمًا — قبل الإجابة `answered` كلّها `None` فلا تصلان أصلًا.
    correct_id = fields.Int()
    note = fields.Str()
    awarded_hours = fields.Decimal(as_string=True)
    # أيّامٌ متتالية من الإجابات الصحيحة — **مشتقّةٌ من `answers` لا مخزَّنة**،
    # فلا عمود ولا هجرة، ولا حقلٌ يتباعد عن مصدره.
    streak = fields.Int()


class QuestionSchema(Schema):
    id = fields.Int()
    prompt = fields.Str()
    choices = fields.List(fields.Nested(ChoiceSchema))
    answered = fields.Nested(AnsweredSchema, allow_none=True)


class TodayQuestionSchema(Schema):
    # `null` لا ٤٠٤ — بلا سؤال اليوم حالة مصمَّمة (نمط `team: null`).
    question = fields.Nested(QuestionSchema, allow_none=True)


class AnswerSchema(Schema):
    choice_id = fields.Int(required=True, validate=validate.Range(min=1))


class SubmitNoteSchema(Schema):
    body = fields.Str(required=True, validate=validate.Length(min=1, max=2000))


class AdminNoteRowSchema(Schema):
    id = fields.Int()
    body = fields.Str()
    day = fields.Date()
    read_at = fields.DateTime(allow_none=True)


class AdminNotesListSchema(Schema):
    notes = fields.List(fields.Nested(AdminNoteRowSchema))


class MarkNoteReadSchema(Schema):
    # `true` وحدها ذات معنى — لا رجوع إلى «غير مقروءة» (نمط ArchiveTeamSchema).
    read = fields.Bool(required=True, validate=validate.Equal(True))


class MarkedNoteSchema(Schema):
    id = fields.Int()
    read_at = fields.DateTime()


class WeekPilotRowSchema(Schema):
    full_name = fields.Str()
    reason = fields.Str()


class WeekPilotSchema(Schema):
    # `null` — لم يُختَر أحد لهذا الأسبوع بعد (حالة مصمَّمة).
    pilot = fields.Nested(WeekPilotRowSchema, allow_none=True)


class ChooseWeekPilotSchema(Schema):
    user_id = fields.Int(required=True, validate=validate.Range(min=1))
    # نصّ حرّ إلزاميّ — القيمة كلّها في «لماذا» (ط-١٠).
    reason = fields.Str(required=True, validate=validate.Length(min=1, max=1000))
    # «وزن الاختيار» — ساعاتٌ إضافية. صفرٌ مشروع (تكريمٌ بلا ساعات)، والسالب
    # مرفوض. غيابُه = صفر، فالعقد القديم يبقى صالحًا.
    bonus_hours = fields.Decimal(
        load_default=Decimal("0"), as_string=True, validate=validate.Range(min=0)
    )


class ChosenWeekPilotSchema(Schema):
    user_id = fields.Int()
    full_name = fields.Str()
    week_start = fields.Date()
    bonus_hours = fields.Decimal(as_string=True)
