from marshmallow import Schema, fields


class ResetPinSchema(Schema):
    """
    الرمز الجديد — **يُعرض مرّة واحدة ولا يُسترجَع**.

    ولا يُخزَّن نصًّا صريحًا في أي مكان: لا في `users` (مهشَّر argon2id)، ولا في
    `audit_log` (`before`/`after` فارغان بنصّ §٧.٥).
    """

    student_no = fields.Str()
    pin = fields.Str()
