from marshmallow import Schema, fields, validate


class SubmitReadingSchema(Schema):
    """
    ما يرسله الطالب. **لا `user_id`** — الهوية من الجلسة، فلا يوجد ما يُتلاعب به.
    """

    read_on = fields.Date(required=True)
    # الحدّ الأعلى ليس تحكّمًا: ٣٠٠٠ صفحة في يوم واحد خطأُ إدخال لا إنجاز،
    # وقبولها يفسد الترتيب قبل أن يلاحظه أحد.
    pages = fields.Int(required=True, validate=validate.Range(min=1, max=3000))
    book_title = fields.Str(required=True, validate=validate.Length(min=1, max=200))


class SubmittedSchema(Schema):
    id = fields.Int()
    status = fields.Str()


class MyReadingSchema(Schema):
    id = fields.Int()
    read_on = fields.Date()
    pages = fields.Int()
    book_title = fields.Str()
    status = fields.Str()
    review_reason = fields.Str(allow_none=True)
    reviewed_at = fields.DateTime(allow_none=True)
    # نصّ عشري كبقية المبالغ، **ويأتي محسوبًا من الحدث** لا من pages × وزن في
    # الواجهة (AGENTS ٥). فارغ في غير المعتمد (ث-٥).
    hours = fields.Decimal(as_string=True, allow_none=True)


class MyReadingsSchema(Schema):
    readings = fields.List(fields.Nested(MyReadingSchema))


class QueueItemSchema(Schema):
    id = fields.Int()
    student_name = fields.Str()
    read_on = fields.Date()
    pages = fields.Int()
    book_title = fields.Str()
    created_at = fields.DateTime()


class QueueSchema(Schema):
    submissions = fields.List(fields.Nested(QueueItemSchema))


class ApproveSchema(Schema):
    """اعتماد جماعي: الاعتماد الفردي في طابور من ٢٠ طلبًا يخالف NFR-02."""

    ids = fields.List(fields.Int(), required=True, validate=validate.Length(min=1))


class RejectSchema(Schema):
    # إلزامي في المخطّط **وفي القاعدة** (ث-٦): رفضٌ صامت يقتل الثقة أسرع من
    # غياب الميزة، والطالب يرى السبب (FR-024).
    reason = fields.Str(required=True, validate=validate.Length(min=1, max=500))


class ReviewResultSchema(Schema):
    submission_id = fields.Int()
    status = fields.Str()
    hours = fields.Decimal(as_string=True, allow_none=True)


class ReviewResultsSchema(Schema):
    results = fields.List(fields.Nested(ReviewResultSchema))


# ═══ و-١١ — تحضير القراءة (FR-090..093) ═══
# `MyReadingSchema`/`MyReadingsSchema`/`QueueItemSchema`/`QueueSchema` أعلاه
# **تُعاد استعمالها حرفيًّا** لتحضير القراءة — نفس شكل الصفّ تمامًا.


class SubmitTahdirSchema(Schema):
    """نفس `SubmitReadingSchema` بحدّ أدنى ٧ صفحات (FR-090) — لا حدّ أعلى."""

    read_on = fields.Date(required=True)
    pages = fields.Int(required=True, validate=validate.Range(min=7, max=3000))
    book_title = fields.Str(required=True, validate=validate.Length(min=1, max=200))


class TahdirDaySchema(Schema):
    date = fields.Date()
    weekday = fields.Str()
    completed = fields.Bool()
    pages = fields.Int()


class TahdirWeekSchema(Schema):
    week_start = fields.Date()
    days = fields.List(fields.Nested(TahdirDaySchema))
    pages_total = fields.Int()
    target_pages = fields.Int()
    percent = fields.Float()
    struggling = fields.Bool()


class TahdirReportSchema(Schema):
    submissions = fields.List(fields.Nested(MyReadingSchema))
    week = fields.Nested(TahdirWeekSchema)


class AdminTahdirEntrySchema(Schema):
    user_id = fields.Int(required=True)
    read_on = fields.Date(required=True)
    pages = fields.Int(required=True, validate=validate.Range(min=1, max=3000))
    book_title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    # اختياريّ — نفس المسار يخدم القراءة العادية أيضًا (`"reading"`).
    activity_type = fields.Str(load_default="tahdir", validate=validate.Length(min=1, max=50))


class AdminEntryResultSchema(Schema):
    id = fields.Int()
    status = fields.Str()
    hours = fields.Decimal(as_string=True, allow_none=True)


class OrgTahdirRowSchema(Schema):
    user_id = fields.Int()
    full_name = fields.Str()
    team_name = fields.Str()
    days_completed = fields.Int()
    days_total = fields.Int()
    pages_total = fields.Int()
    percent = fields.Float()
    # 'good' | 'fair' | 'low' — **درجةٌ محسوبة في الخادم** بعتبتَي النموذج،
    # والواجهة تُلوّن وتُسمّي فقط.
    tier = fields.Str()
    struggling = fields.Bool()


class OrgTahdirTotalsSchema(Schema):
    pages = fields.Int()
    participants = fields.Int()
    fully_regular = fields.Int()


class OrgTahdirReportSchema(Schema):
    from_day = fields.Date()
    to_day = fields.Date()
    days_total = fields.Int()
    totals = fields.Nested(OrgTahdirTotalsSchema)
    students = fields.List(fields.Nested(OrgTahdirRowSchema))
