from marshmallow import Schema, fields


class RankSchema(Schema):
    name = fields.Str()
    tier = fields.Int()


class NextRankSchema(Schema):
    name = fields.Str()
    # نصّ عشري لا float: JSON number يفقد الدقّة في جافاسكربت، والساعات تُقارَن
    # بعتبات — رقمٌ منزلقٌ يضع الطالب في الرتبة الخطأ.
    at_hours = fields.Decimal(as_string=True)
    progress_pct = fields.Float()
    remaining = fields.Decimal(as_string=True)


class FlightSchema(Schema):
    grounded = fields.Bool()
    last_activity_on = fields.Date(allow_none=True)


class TeamSchema(Schema):
    name = fields.Str()
    # قابل للعدم بعقدٍ معلَن: ترتيب السرب FR-051 يملكه `services/standings` في
    # الوحدة ٩. `null` تعني «غير محسوب بعد» لا «لا سرب» — وغياب السرب نفسه
    # يُمثَّل بـ`team: null` (API.md §٤).
    rank_in_org = fields.Int(allow_none=True)


class DeckSchema(Schema):
    rank = fields.Nested(RankSchema)
    hours = fields.Decimal(as_string=True)
    next_rank = fields.Nested(NextRankSchema, allow_none=True)
    flight = fields.Nested(FlightSchema)
    team = fields.Nested(TeamSchema, allow_none=True)
