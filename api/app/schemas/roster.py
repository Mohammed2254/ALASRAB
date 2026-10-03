"""
سجلّ الطلاب — و-٢١. **لا بند `SCOPE.md` لإنشاء طالب**، فُرض أنهم موجودون.
"""

from marshmallow import Schema, fields, validate

ROLE = validate.OneOf(("pilot", "admin"))


class RosterRowSchema(Schema):
    id = fields.Int()
    full_name = fields.Str()
    student_no = fields.Str()
    role = fields.Str()
    # طالبٌ أُغلقت عضويته (نقلٌ قديم) يظهر بلا سرب لا يختفي من السجلّ.
    team_name = fields.Str(allow_none=True)
    is_active = fields.Bool()


class RosterListSchema(Schema):
    students = fields.List(fields.Nested(RosterRowSchema))


class CreateStudentSchema(Schema):
    full_name = fields.Str(required=True, validate=validate.Length(min=1, max=120))
    student_no = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    team_id = fields.Int(required=True)


class IssuedStudentSchema(Schema):
    """
    `pin` نصًّا — **الموضع الوحيد في العقد كلّه الذي يحمل رمزًا صريحًا**،
    ولمرّةٍ واحدة لحظة الإنشاء (نفس عقد `/admin/users/<id>/reset-pin`).
    ولا يظهر في أيّ `GET` أبدًا: `RosterRowSchema` بلا حقل رمز بالبناء.
    """

    id = fields.Int()
    full_name = fields.Str()
    student_no = fields.Str()
    pin = fields.Str()


class BulkStudentRowSchema(Schema):
    full_name = fields.Str(required=True, validate=validate.Length(min=1, max=120))
    student_no = fields.Str(required=True, validate=validate.Length(min=1, max=20))


class BulkCreateStudentsSchema(Schema):
    team_id = fields.Int(required=True)
    rows = fields.List(fields.Nested(BulkStudentRowSchema), required=True)


class BulkFailureSchema(Schema):
    line = fields.Int()
    message = fields.Str()


class BulkCreatedSchema(Schema):
    """
    الناجح والفاشل **معًا في ردٍّ واحد**: لصقةٌ تُرفض كلّها لأن رقمًا مكرَّر
    تُجبر المشرف على تفتيشها بعينه — وهو ما يدفعه إلى تركها (خ-١).
    """

    created = fields.List(fields.Nested(IssuedStudentSchema))
    failed = fields.List(fields.Nested(BulkFailureSchema))


class SetRoleSchema(Schema):
    role = fields.Str(required=True, validate=ROLE)


class RoleSetSchema(Schema):
    id = fields.Int()
    role = fields.Str()


class SetActiveSchema(Schema):
    active = fields.Bool(required=True)


class ActiveSetSchema(Schema):
    id = fields.Int()
    is_active = fields.Bool()
