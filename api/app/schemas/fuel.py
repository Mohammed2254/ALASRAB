from marshmallow import Schema, fields, validate

# ═══ الأنشطة ═══


class CriterionRowSchema(Schema):
    key = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    weight_pct = fields.Decimal(required=True, as_string=True)


class CriterionOutSchema(CriterionRowSchema):
    id = fields.Int()


class ActivityRowSchema(Schema):
    id = fields.Int()
    key = fields.Str()
    name = fields.Str()
    litres_full = fields.Decimal(as_string=True)
    criteria = fields.List(fields.Nested(CriterionOutSchema))


class ActivitiesListSchema(Schema):
    activities = fields.List(fields.Nested(ActivityRowSchema))


class CreateActivitySchema(Schema):
    key = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    litres_full = fields.Decimal(required=True, as_string=True, validate=validate.Range(min=0.01))
    criteria = fields.List(
        fields.Nested(CriterionRowSchema), required=True, validate=validate.Length(min=1)
    )


class CreatedActivitySchema(Schema):
    id = fields.Int()


# ═══ التقييم ═══


class ScoreRowSchema(Schema):
    criterion_id = fields.Int(required=True)
    score_pct = fields.Decimal(
        required=True, as_string=True, validate=validate.Range(min=0, max=100)
    )


class AssessSchema(Schema):
    team_id = fields.Int(required=True)
    activity_id = fields.Int(required=True)
    occurred_on = fields.Date(required=True)
    scores = fields.List(
        fields.Nested(ScoreRowSchema), required=True, validate=validate.Length(min=1)
    )
    note = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=500))


class AssessedSchema(Schema):
    id = fields.Int()
    total_pct = fields.Decimal(as_string=True)
    litres = fields.Decimal(as_string=True)


# ═══ محطة التزوّد ═══


class RecentAssessmentSchema(Schema):
    activity_name = fields.Str()
    occurred_on = fields.Date()
    total_pct = fields.Decimal(as_string=True)
    litres = fields.Decimal(as_string=True)


class StationTeamSchema(Schema):
    name = fields.Str()
    litres = fields.Decimal(as_string=True)


class StationSchema(Schema):
    team = fields.Nested(StationTeamSchema, allow_none=True)
    tank_capacity_l = fields.Decimal(as_string=True, allow_none=True)
    recent = fields.List(fields.Nested(RecentAssessmentSchema))
