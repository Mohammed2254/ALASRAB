from marshmallow import Schema, fields, validate


class TeamMemberSchema(Schema):
    """عضوٌ في سرب — النموذج يعرض الأسماء لا العدد وحده."""

    user_id = fields.Int()
    full_name = fields.Str()
    student_no = fields.Str()


class AdminTeamRowSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    code = fields.Str()
    archived_at = fields.DateTime(allow_none=True)
    active_members = fields.Int()
    members = fields.List(fields.Nested(TeamMemberSchema))


class TeamsListSchema(Schema):
    teams = fields.List(fields.Nested(AdminTeamRowSchema))


class CreateTeamSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=20))


class CreatedTeamSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    code = fields.Str()


class ArchiveTeamSchema(Schema):
    # `true` وحدها ذات معنى اليوم — لا إلغاء أرشفة (م-١٠: أرشفة لا حذف ولا رجوع
    # عنه ضمنيًّا؛ عودة سرب للعمل قرارٌ يستحقّ مسارًا صريحًا لا حقلًا بقيمتين).
    archived = fields.Bool(required=True, validate=validate.Equal(True))


class ArchivedTeamSchema(Schema):
    id = fields.Int()
    archived_at = fields.DateTime()


class TransferMemberSchema(Schema):
    user_id = fields.Int(required=True)


class TransferredMemberSchema(Schema):
    user_id = fields.Int()
    team_id = fields.Int()
    role = fields.Str()
