from marshmallow import Schema, fields, validate


class PilotRosterRowSchema(Schema):
    user_id = fields.Int()
    full_name = fields.Str()


class AttendanceStatusSchema(Schema):
    week_start = fields.Date()
    already_recorded = fields.Bool()
    pilots = fields.List(fields.Nested(PilotRosterRowSchema))
    absent_user_ids = fields.List(fields.Int())
    # `null` — لا حضور مسجَّل بعد، أو انتهت مهلة التراجع فعلًا.
    undo_until = fields.DateTime(allow_none=True)


class RecordAttendanceSchema(Schema):
    absent_user_ids = fields.List(fields.Int(validate=validate.Range(min=1)), load_default=list)


class RecordedAttendanceSchema(Schema):
    present = fields.Int()
    absent = fields.Int()
    hours_each = fields.Decimal(as_string=True)
    undo_until = fields.DateTime()


class UndoneAttendanceSchema(Schema):
    reversed = fields.Int()
