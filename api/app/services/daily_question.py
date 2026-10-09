"""
سؤال اليوم — الشقّ الإداريّ (و-٢١).

**الفجوة التي يسدّها:** `FR-060` بند **MUST**، وشاشةُ الطالب مبنيّة منذ و-٩ —
لكن `SCOPE.md` ط-٦ أعلن صراحةً أن **لا مسار إنشاء إداريًّا**، والصفوف تُدرَج
«بذرة أو SQL». وأثرُ ذلك على خادمٍ منشور: الجمعية الجديدة بلا سؤالٍ واحد
إلى الأبد، فشاشةٌ كاملةٌ من شاشات الطيّار **ميتةٌ بالتصميم** — وهو ما لا يصحّ
في بندٍ MUST.

**والقاعدة الحاكمة: سؤالٌ أُجيب لا يُعدَّل ولا يُحذَف.** وهي مشتقّة من ث-١٧
لا مُختَرعة: `answers.correct` و`answers.point_event_id` **لا يفترقان** بقيدٍ
في القاعدة، وقد كُتبا معًا لحظة الإجابة. فتغييرُ `correct_id` بعدها يجعل
إجابةً صحيحةً تبدو خاطئة وقد دُفعت ساعاتُها فعلًا — وحذفُ السؤال يتيّم تلك
الأحداث في الدفتر (ADR-004). فالتعديل مسموحٌ **قبل أوّل إجابة وحدها**.

@implements FR-097
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Answer, DailyQuestion, Org
from . import audit

# خيارَان حدٌّ أدنى (سؤالٌ بخيارٍ واحد ليس سؤالًا)، وأربعةٌ حدٌّ أعلى — بطاقة
# الطالب تعرضها عمودًا واحدًا على عرض ٣٢٠px، والخامس يُخرجها عن المنفذ.
MIN_CHOICES = 2
MAX_CHOICES = 4


class DailyQuestionError(Exception):
    """خطأ عملٍ يُترجَم إلى رمز حالة في المسار — لا يعرف HTTP (نمط `TeamsError`)."""

    def __init__(self, message: str, status: int = 422):
        self.status = status
        super().__init__(message)


def list_questions(org_id: int) -> list[dict]:
    """
    الأسئلة **الأحدث أوّلًا**، وكلٌّ معه **عدد من أجاب**.

    والعدد ليس زينة: هو ما يُخبر المشرف أن السؤال **مُقفَل** — فلا يضغط زرًّا
    يردّ الخادمُ عليه بـ٤٢٢. ووصلٌ واحد لا N+1: قائمةٌ تنمو يومًا كل يوم.
    """
    rows = db.session.execute(
        select(DailyQuestion, func.count(Answer.id))
        .outerjoin(Answer, Answer.question_id == DailyQuestion.id)
        .where(DailyQuestion.org_id == org_id)
        .group_by(DailyQuestion.id)
        .order_by(DailyQuestion.day.desc())
    ).all()
    return [
        {
            "id": q.id,
            "day": q.day.isoformat(),
            "prompt": q.prompt,
            "choices": q.choices,
            "correct_id": q.correct_id,
            "note": q.note,
            "reward_hours": q.reward_hours,
            "answers": answered,
            # حقلٌ معلَن لا استنتاجٌ في الواجهة: «مُقفَل» قاعدةٌ لا عرض.
            "locked": answered > 0,
        }
        for q, answered in rows
    ]


def _validate(
    prompt: str, choices: list[dict], correct_id: int, note: str, reward_hours: Decimal
) -> tuple[str, list[dict], str]:
    prompt = prompt.strip()
    note = note.strip()
    if not prompt:
        raise DailyQuestionError("نصّ السؤال مطلوب.")
    if not note:
        # `FR-060`: «الجواب الصحيح **وشرحه** يظهران في الحالتين» — فالشرح
        # ليس حقلًا اختياريًّا بل نصفُ المتطلَّب.
        raise DailyQuestionError("شرح الجواب مطلوب — يظهر للطالب صحّت إجابته أم لا.")

    cleaned = [{"id": c["id"], "text": c["text"].strip()} for c in choices]
    if not (MIN_CHOICES <= len(cleaned) <= MAX_CHOICES):
        raise DailyQuestionError(f"الخيارات بين {MIN_CHOICES} و{MAX_CHOICES}.")
    if any(not c["text"] for c in cleaned):
        raise DailyQuestionError("لا خيار بلا نصّ.")

    ids = [c["id"] for c in cleaned]
    if len(set(ids)) != len(ids):
        raise DailyQuestionError("معرّفات الخيارات مكرَّرة.")
    if correct_id not in ids:
        # **الحرس الحقيقيّ:** `correct_id` خارج الخيارات يُنتج سؤالًا **لا
        # إجابة صحيحة له** — فكلّ من يجيبه يُخطئ، ولا شيء في القاعدة يمنعه.
        raise DailyQuestionError("الجواب الصحيح يجب أن يكون أحد الخيارات.")
    if reward_hours < 0:
        raise DailyQuestionError("ساعات المكافأة لا تكون سالبة.")

    return prompt, cleaned, note


def create_question(
    org: Org,
    *,
    day: date,
    prompt: str,
    choices: list[dict],
    correct_id: int,
    note: str,
    reward_hours: Decimal,
    actor_id: int,
) -> dict:
    """سؤالٌ واحد لكل يوم — والتكرار يردّه قيد `uq_daily_questions_org_day`."""
    prompt, cleaned, note = _validate(prompt, choices, correct_id, note, reward_hours)

    question = DailyQuestion(
        org_id=org.id,
        day=day,
        prompt=prompt,
        choices=cleaned,
        correct_id=correct_id,
        note=note,
        reward_hours=reward_hours,
    )
    db.session.add(question)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise DailyQuestionError(f"يوجد سؤال ليوم {day.isoformat()} أصلًا.", status=409) from exc

    audit.record(
        org_id=org.id,
        kind="question_created",
        summary=f"سؤال يوم {day.isoformat()}",
        actor_id=actor_id,
        after={"question_id": question.id, "day": day.isoformat()},
    )
    db.session.commit()
    return {"id": question.id, "day": question.day.isoformat()}


def _editable(org_id: int, question_id: int) -> DailyQuestion:
    question = db.session.get(DailyQuestion, question_id)
    if question is None or question.org_id != org_id:
        raise DailyQuestionError("لا سؤال بهذا المعرّف.", status=404)

    answered = db.session.scalar(
        select(func.count(Answer.id)).where(Answer.question_id == question.id)
    )
    if answered:
        raise DailyQuestionError(
            f"أجاب عليه {answered} طالبًا — لا يُعدَّل ولا يُحذَف بعد أوّل إجابة.",
            status=409,
        )
    return question


def update_question(
    org: Org,
    question_id: int,
    *,
    prompt: str,
    choices: list[dict],
    correct_id: int,
    note: str,
    reward_hours: Decimal,
    actor_id: int,
) -> dict:
    """
    تعديلٌ **قبل أوّل إجابة وحدها**. و`day` لا يتغيّر: نقلُ سؤالٍ إلى يومٍ آخر
    مساوٍ لحذفه وإنشائه، ومسارٌ صريحٌ لذلك أوضح من حقلٍ يفعله ضمنًا.
    """
    question = _editable(org.id, question_id)
    prompt, cleaned, note = _validate(prompt, choices, correct_id, note, reward_hours)

    before = {"prompt": question.prompt, "correct_id": question.correct_id}
    question.prompt = prompt
    question.choices = cleaned
    question.correct_id = correct_id
    question.note = note
    question.reward_hours = reward_hours

    audit.record(
        org_id=org.id,
        kind="question_updated",
        summary=f"تعديل سؤال يوم {question.day.isoformat()}",
        actor_id=actor_id,
        before=before,
        after={"question_id": question.id, "correct_id": correct_id},
    )
    db.session.commit()
    return {"id": question.id, "day": question.day.isoformat()}


def delete_question(org: Org, question_id: int, actor_id: int) -> None:
    """
    حذفٌ **قبل أوّل إجابة وحدها** — وبعدها يتيّم أحداثَ الدفتر (ADR-004).

    وهو **الحذف الوحيد المسموح في المنصّة كلّها**، ومشروعٌ لأن السؤال قبل أن
    يُجاب **لا أثر له في أيّ مكان**: لا حدث دفتر ولا صفّ إجابة. بخلاف السرب
    (يُؤرشَف) والطالب (يُعطَّل) — وكلاهما يملك تاريخًا.
    """
    question = _editable(org.id, question_id)
    day = question.day.isoformat()
    db.session.delete(question)
    audit.record(
        org_id=org.id,
        kind="question_deleted",
        summary=f"حذف سؤال يوم {day}",
        actor_id=actor_id,
        before={"question_id": question_id, "day": day},
    )
    db.session.commit()
