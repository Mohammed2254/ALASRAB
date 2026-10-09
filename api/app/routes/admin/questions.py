"""
سؤالُ اليوم — الشقّ الإداريّ (`FR-097`).

**وسؤالٌ أُجيب لا يُعدَّل ولا يُحذَف**: ث-١٧ يربط `answers.correct` بـ
`point_event_id` وقد كُتبا معًا، فتغييرُ الصحيح بعدها يجعل إجابةً صحيحةً
تبدو خاطئة وقد دُفعت ساعاتُها.
"""

from flask import g
from flask.views import MethodView
from flask_smorest import abort

from ...schemas.daily_question import (
    CreateQuestionSchema,
    QuestionRefSchema,
    QuestionsListSchema,
    UpdateQuestionSchema,
)
from ...security import admin_required
from ...services import daily_question as question_service
from .._helpers import org_of_session as _org
from . import blp

# ═══ و-٢١ — سؤال اليوم: الشقّ الإداريّ ═══
#
# `SCOPE.md` ط-٦ أعلن صراحةً أن **لا مسار إنشاء إداريًّا** والصفوف تُدرَج
# «بذرة أو SQL». وأثرُ ذلك على خادمٍ منشور: جمعيةٌ جديدة بلا سؤالٍ واحد إلى
# الأبد، فشاشةٌ كاملة من شاشات الطيّار **ميتةٌ بالتصميم** — في بندٍ MUST.


@blp.route("/admin/questions")
class AdminQuestions(MethodView):
    @admin_required
    @blp.response(200, QuestionsListSchema)
    def get(self):
        """الأحدث أوّلًا، وكلٌّ معه عدد من أجاب — وهو ما يُعلِم أنه مُقفَل."""
        return {"questions": question_service.list_questions(g.user.org_id)}

    @admin_required
    @blp.arguments(CreateQuestionSchema)
    @blp.response(201, QuestionRefSchema)
    def post(self, data):
        """سؤالٌ واحد لكل يوم — والتكرار يردّه `uq_daily_questions_org_day`."""
        try:
            return question_service.create_question(
                _org(),
                day=data["day"],
                prompt=data["prompt"],
                choices=data["choices"],
                correct_id=data["correct_id"],
                note=data["note"],
                reward_hours=data["reward_hours"],
                actor_id=g.user.id,
            )
        except question_service.DailyQuestionError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/questions/<int:question_id>")
class AdminQuestionDetail(MethodView):
    @admin_required
    @blp.arguments(UpdateQuestionSchema)
    @blp.response(200, QuestionRefSchema)
    def patch(self, data, question_id):
        """
        **قبل أوّل إجابة وحدها.** بعدها تغييرُ `correct_id` يجعل إجابةً صحيحةً
        تبدو خاطئة وقد دُفعت ساعاتُها فعلًا — و`answers.correct` و
        `point_event_id` لا يفترقان بقيدٍ في القاعدة (ث-١٧).
        """
        try:
            return question_service.update_question(
                _org(),
                question_id,
                prompt=data["prompt"],
                choices=data["choices"],
                correct_id=data["correct_id"],
                note=data["note"],
                reward_hours=data["reward_hours"],
                actor_id=g.user.id,
            )
        except question_service.DailyQuestionError as exc:
            abort(exc.status, message=str(exc))

    @admin_required
    @blp.response(204)
    def delete(self, question_id):
        """
        **الحذف الوحيد المسموح في المنصّة كلّها** — ومشروعٌ لأن السؤال قبل أن
        يُجاب لا أثر له في أيّ مكان: لا حدث دفتر ولا صفّ إجابة. بخلاف السرب
        (يُؤرشَف) والطالب (يُعطَّل)، وكلاهما يملك تاريخًا.
        """
        try:
            question_service.delete_question(_org(), question_id, g.user.id)
        except question_service.DailyQuestionError as exc:
            abort(exc.status, message=str(exc))
        return ""
