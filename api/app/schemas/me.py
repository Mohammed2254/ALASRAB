from marshmallow import Schema, fields

from .event import EventRowSchema


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
    # محسوب في `services/standings::team_rank` (و-٩ب، FR-051) — نفس ترتيب
    # `GET /boards/teams`. `null` نظريًّا بلا حالة تنتجه اليوم (كل سرب في هذا
    # الترتيب سرب الطالب نفسه بالضرورة)، أُبقي قابلًا للعدم دفاعًا لا وعدًا.
    rank_in_org = fields.Int(allow_none=True)


class DeckSchema(Schema):
    rank = fields.Nested(RankSchema)
    hours = fields.Decimal(as_string=True)
    next_rank = fields.Nested(NextRankSchema, allow_none=True)
    flight = fields.Nested(FlightSchema)
    team = fields.Nested(TeamSchema, allow_none=True)


class EventsSchema(Schema):
    events = fields.List(fields.Nested(EventRowSchema))
