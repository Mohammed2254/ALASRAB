from marshmallow import Schema, fields, validate

# ═══ الأوزان — FR-081 ═══


class WeightRowSchema(Schema):
    activity_type = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    # `min=0` لا `min=0.01`: **الصفر قرارٌ مشروع** — «نخلي الحضور ماله قيمة
    # ونضربه بصفر» (قرار المستخدم، و-٢٠)، فتعطيل نشاطٍ يكون بوزنه لا بحذفه.
    # والسالب مرفوض: كان يُقبل بلا مُصادِق فيطرح ساعاتٍ من كل استيراد صامتًا.
    hours_per_unit = fields.Decimal(required=True, as_string=True, validate=validate.Range(min=0))


class MultiplierRowSchema(Schema):
    grade = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    # نفس المنطق: صفرٌ مشروع (درجةٌ لا تُحتسب)، وسالبٌ مرفوض.
    multiplier = fields.Decimal(required=True, as_string=True, validate=validate.Range(min=0))


class CreateWeightVersionSchema(Schema):
    # تاريخ محلّي لا لحظة UTC — يُحوَّل في الخدمة (`RULES.md` §٩)، نفس عقد
    # `SubmitReadingSchema.read_on`.
    effective_from = fields.Date(required=True)
    note = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=200))
    weights = fields.List(
        fields.Nested(WeightRowSchema), required=True, validate=validate.Length(min=1)
    )
    multipliers = fields.List(fields.Nested(MultiplierRowSchema), load_default=list)


class WeightVersionIdSchema(Schema):
    id = fields.Int()
    effective_from = fields.DateTime()


class CurrentWeightVersionSchema(Schema):
    id = fields.Int()
    effective_from = fields.DateTime()
    note = fields.Str(allow_none=True)
    weights = fields.List(fields.Nested(WeightRowSchema))
    multipliers = fields.List(fields.Nested(MultiplierRowSchema))


class WeightsSchema(Schema):
    current = fields.Nested(CurrentWeightVersionSchema, allow_none=True)
    history = fields.List(fields.Nested(WeightVersionIdSchema))


# ═══ العتبات — FR-082 ═══


class ThresholdRowSchema(Schema):
    key = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    tier = fields.Int(required=True, validate=validate.Range(min=1))
    at_hours = fields.Decimal(required=True, as_string=True, validate=validate.Range(min=0))


class ThresholdsSchema(Schema):
    thresholds = fields.List(fields.Nested(ThresholdRowSchema))


class SaveThresholdsSchema(Schema):
    thresholds = fields.List(
        fields.Nested(ThresholdRowSchema), required=True, validate=validate.Length(min=1)
    )


class RankShiftSchema(Schema):
    user_id = fields.Int()
    from_tier = fields.Int()
    to_tier = fields.Int()


class ThresholdsPreviewSchema(Schema):
    promoted = fields.List(fields.Nested(RankShiftSchema))
    # فارغة **دائمًا** — و-٧ · ت-٢ (ق-٥٠). حقلٌ حاضرٌ في العقد لا لأنه يُتوقَّع
    # أن يمتلئ، بل لأن غيابه يخفي الضمانة بدل إثباتها.
    demoted = fields.List(fields.Nested(RankShiftSchema))
    warning = fields.Str(allow_none=True)
