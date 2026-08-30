from marshmallow import Schema, fields, validate


class LoginSchema(Schema):
    """
    **بلا `org_id`.** العقد في `API.md` §٣ لا يحمله، ولثلاثة أسباب: مراهقٌ لا
    يكتب رقم منظمة · والعميل لا يجوز أن يستكشف المنظمات · والتخويل كلّه على
    مستوى الجمعية (ARCHITECTURE §٧.٣). يُحلّ في الخادم بـ`auth.default_org_id`.
    """

    # الطول مفروض هنا لا في الواجهة: التحقّق على الحدّ هو التحقّق الوحيد الموثوق.
    student_no = fields.Str(required=True, validate=validate.Length(min=1, max=32))
    pin = fields.Str(required=True, validate=validate.Regexp(r"^\d{4}$"))


class UserSchema(Schema):
    id = fields.Int()
    full_name = fields.Str()
    student_no = fields.Str()
    role = fields.Str()


class SessionSchema(Schema):
    """
    الردّ **معشَّش تحت `user`** كما في `API.md` §٣ — لا مسطّح.

    التعشيش ليس ذوقًا: يترك مكانًا لحقول جلسة مستقبلية (انتهاء · تحذير) بلا أن
    تختلط بحقول المستخدم، فلا يُكسر العميل حين تُضاف.
    """

    user = fields.Nested(UserSchema)
