from marshmallow import Schema, fields


class WindowSchema(Schema):
    from_ = fields.Date(data_key="from")
    to = fields.Date()
    days = fields.Int()


class TotalsSchema(Schema):
    hours = fields.Decimal(as_string=True)
    active_pilots = fields.Int()
    grounded_pilots = fields.Int()


class TeamRowSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    hours = fields.Decimal(as_string=True)
    members = fields.Int()
    # معدّل لا مجموع — اتّساقًا مع صدارة الأسراب (FR-051).
    avg_hours = fields.Decimal(as_string=True)


class MoverSchema(Schema):
    user_id = fields.Int()
    full_name = fields.Str()
    hours = fields.Decimal(as_string=True)


class GroundedSchema(Schema):
    user_id = fields.Int()
    full_name = fields.Str()
    last_activity_on = fields.Date(allow_none=True)


class ReportSchema(Schema):
    window = fields.Nested(WindowSchema)
    totals = fields.Nested(TotalsSchema)
    teams = fields.List(fields.Nested(TeamRowSchema))
    top_movers = fields.List(fields.Nested(MoverSchema))
    # بالاسم — **للمشرف وحده**. القرار ٥ يمنع عرض المتأخّر بالاسم للطلاب،
    # وهذه شاشة إشراف لا صدارة.
    grounded = fields.List(fields.Nested(GroundedSchema))
