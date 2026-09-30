from marshmallow import Schema, fields


class PilotRowSchema(Schema):
    full_name = fields.Str()
    hours = fields.Decimal(as_string=True)
    # تغيّرُ الموضع عن الأسبوع الماضي: موجبٌ صعود · سالبٌ هبوط · صفرٌ ثبات.
    chg = fields.Int()


class PilotsBoardSchema(Schema):
    pilots = fields.List(fields.Nested(PilotRowSchema))


class ReadinessCountSchema(Schema):
    flying = fields.Int()
    grounded = fields.Int()


class TeamBoardRowSchema(Schema):
    team = fields.Str()
    # فكّ التعادل (FR-052) — معروض دائمًا لأنه هو نفسه المعيار المُعلَن.
    code = fields.Str()
    avg_hours = fields.Decimal(as_string=True)
    members = fields.Int()
    readiness = fields.Nested(ReadinessCountSchema)
    # تغيّرُ الموضع عن الأسبوع الماضي: موجبٌ صعود · سالبٌ هبوط · صفرٌ ثبات.
    # **محسوبٌ بإعادة ترتيبٍ على نافذةٍ سابقة** لا بلقطةٍ مخزَّنة، فالدفتر
    # يبقى المصدر الوحيد.
    chg = fields.Int()



class TeamsBoardSchema(Schema):
    teams = fields.List(fields.Nested(TeamBoardRowSchema))


class AircraftSchema(Schema):
    # `null` للساقط في scope=general — إنجاز فقط، لا اسم (ف-١).
    name = fields.Str(allow_none=True)
    size = fields.Decimal(as_string=True)
    # نسبة جاهزة للعرض (٠-١٠٠، الأكبر بين الأسطول = ١٠٠) — لا حساب في الواجهة.
    size_pct = fields.Int()
    grounded = fields.Bool()


class FormationSchema(Schema):
    scope = fields.Str()
    aircraft = fields.List(fields.Nested(AircraftSchema))
