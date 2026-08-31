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
