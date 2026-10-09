"""
التفاعل اليوميّ — FR-060 (و-٩ج)، FR-061/FR-062 (و-٩د).

**المكافأة `daily_questions.reward_hours` مباشرةً — لا عبر `rules/engine`**
(قرار Reconcile و-٩ج): خاصّية هذا السؤال بعينه لا وزن نشاط عامّ يُعاد معايرته
مع الزمن. الفرق بينهما ترك `seed.py` يحمل وزن `daily_question` شاذًّا لم
يستعمله كود قطّ — أُزيل بعد هذا الملفّ (`docs/slices/و-٩.md`).

**ومسار الإنشاء الإداريّ في `services/daily_question.py`** (و-٢١ · `FR-097`)
— مفصولٌ عن هذا الملفّ لأن هذا يخدم الطالب وذاك المشرف، نفس قسمة `me.ts`
مقابل `adminQueue.ts` في الواجهة.

**نافذة أسبوع `pilot_of_week` من `services/week.py`** (`RULES.md` §٩.١أ).
كانت مكرَّرة هنا عمدًا، واعتراضُها القديم كان صحيحًا: الدالّة في `standings.py`
**خاصّة** (`_week_start`)، واستيراد خاصٍّ من خدمة شقيقة ترابطٌ لا إعادة استعمال.
و-١٢ أزالت الاعتراض لا القاعدة: صار للنافذة **وحدةٌ مخصَّصة بواجهة عامّة**، فلا
خدمة تستعير من أخرى — وصيغةٌ تقرأ `week_starts_on` من صفٍّ قابل للتغيير ليست
«ثلاثة أسطر متشابهة» بل سياسةً يجب أن تتّفق عبر الشاشات.

@implements FR-060, FR-061, FR-062
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Answer, DailyQuestion, Note, Org, PilotOfWeek, User
from . import ledger, week
from .errors import ServiceError

ZERO = Decimal("0.00")


class EngagementError(ServiceError):
    """
    خطأ نطاق التفاعل — الاسمُ يبقى لأن المسارات تُلقّط به (`services/errors.py`).

    **وكان `status` إلزاميًّا هنا وافتراضيًّا في الثمانية الأخرى** — نداءان
    لمفهومٍ واحد. والوراثةُ توحّدهما بافتراض `422`، **ولا تُغيّر سلوكًا
    اليوم**: كلُّ النداءات الأربعةَ عشر في هذين الملفّين تُمرّر `status=`
    صراحةً (مقيسًا قبل التغيير). والأثرُ على نداءٍ قادمٍ وحده، و`422` هو
    الصواب له: «الطلبُ مفهومٌ وقاعدةُ عملٍ ترفضه».
    """


@dataclass(frozen=True)
class AnswerResult:
    choice_id: int
    correct: bool
    correct_id: int
    note: str
    awarded_hours: Decimal
    #: أيّامٌ متتالية من الإجابات الصحيحة، منتهيةً بسؤال اليوم.
    streak: int


def answer_streak(org: Org, user_id: int, now: datetime | None = None) -> int:
    """
    السلسلة المتتالية — **مشتقّةٌ من `answers` بلا هجرة ولا عمودٍ جديد.**

    تُعدّ أيّامُ الأسئلة (لا أيّام التقويم) نزولًا من سؤال اليوم: كل يومٍ
    أجاب فيه الطالب **صحيحًا** يزيد العدّاد، وأوّل يومٍ لم يُجب فيه أو أخطأ
    يقطعها. فيومٌ لم يُطرَح فيه سؤالٌ أصلًا لا يكسر السلسلة — وإلّا عاقب
    الطالبَ غيابُ سؤالٍ لا صنعَ له فيه.
    """
    rows = db.session.execute(
        select(DailyQuestion.day, Answer.correct)
        .outerjoin(
            Answer,
            (Answer.question_id == DailyQuestion.id) & (Answer.user_id == user_id),
        )
        .where(DailyQuestion.org_id == org.id, DailyQuestion.day <= _today(org, now))
        .order_by(DailyQuestion.day.desc())
    ).all()

    streak = 0
    for _day, correct in rows:
        if not correct:
            break
        streak += 1
    return streak


def _today(org: Org, now: datetime | None = None) -> date:
    """«اليوم» بتوقيت المنظمة لا المتصفّح ولا الخادم (SCOPE.md ط-٦)."""
    return (now or datetime.now(UTC)).astimezone(ZoneInfo(org.timezone)).date()


def _result_of(question: DailyQuestion, answer_row: Answer, streak: int = 0) -> AnswerResult:
    return AnswerResult(
        choice_id=answer_row.choice_id,
        correct=answer_row.correct,
        correct_id=question.correct_id,
        note=question.note,
        awarded_hours=question.reward_hours if answer_row.correct else ZERO,
        streak=streak,
    )


def today(
    org: Org, user_id: int, now: datetime | None = None
) -> tuple[DailyQuestion | None, AnswerResult | None]:
    """سؤال اليوم، وإجابة الطالب عليه إن وُجدت — **الصحيح وشرحه لا يُخفيان بعد الإجابة**."""
    question = db.session.scalar(
        select(DailyQuestion).where(
            DailyQuestion.org_id == org.id, DailyQuestion.day == _today(org, now)
        )
    )
    if question is None:
        return None, None

    answer_row = db.session.scalar(
        select(Answer).where(Answer.user_id == user_id, Answer.question_id == question.id)
    )
    if answer_row is None:
        return question, None
    return question, _result_of(question, answer_row, answer_streak(org, user_id, now))


def answer(
    org: Org, user_id: int, question_id: int, choice_id: int, now: datetime | None = None
) -> AnswerResult:
    """
    إجابة واحدة لكل (طالب، سؤال) — القيد **في القاعدة** (ث-٨).

    ترتيبٌ مقصود: صفّ الإجابة يُثبَّت (flush) أوّلًا فيكشف التكرار **قبل** أي
    كتابة في الدفتر — فلا يوجد احتمال حدث دفتر يتيم لإجابة رُفضت لاحقًا.

    **`correct` و`point_event_id` يلتزمان بـ`commit` واحد** (ث-١٧): الصفّ
    يُثبَّت أوّلًا بقيمتَي حارس (`correct=False, point_event_id=None`) —
    تحقّقان قيد ث-١٧ دائمًا فلا يصطدمان به عند كشف التكرار — ثم يُصحَّحان
    معًا فقط إن كانت الإجابة صحيحة، بعد ربط حدث الدفتر لا قبله، فلا تمرّ
    الإجابة أبدًا بحالة «صحيحة بلا حدث» ولو للحظة داخل المعاملة.
    """
    now = now or datetime.now(UTC)
    question = db.session.get(DailyQuestion, question_id)
    if question is None or question.org_id != org.id or question.day != _today(org, now):
        raise EngagementError("لا سؤال بهذا المعرّف اليوم.", status=404)
    if not any(c["id"] == choice_id for c in question.choices):
        raise EngagementError("الخيار غير موجود ضمن خيارات هذا السؤال.", status=422)

    row = Answer(
        org_id=org.id,
        user_id=user_id,
        question_id=question.id,
        choice_id=choice_id,
        correct=False,
        point_event_id=None,
    )
    db.session.add(row)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise EngagementError("أُجيب عن هذا السؤال من قبل.", status=409) from exc

    correct = choice_id == question.correct_id
    if correct:
        event = ledger.append_pending(
            [
                ledger.EventSpec(
                    org_id=org.id,
                    kind="daily_question",
                    delta=question.reward_hours,
                    user_id=user_id,
                    occurred_at=now,
                )
            ]
        )[0]
        row.correct = True
        row.point_event_id = event.id
    db.session.commit()

    # تُحسب **بعد** الإيداع: إجابةُ اليوم جزءٌ من السلسلة التي يراها الطالب.
    return _result_of(question, row, answer_streak(org, user_id, now))


def submit_note(org: Org, body: str, now: datetime | None = None) -> None:
    """
    ملاحظة مجهولة — FR-061. **بلا `user_id` ولا `ip`** (ث-١٢، بنية الجدول).

    `day` لا `datetime` كامل — دقّة الثانية تكفي لفكّ الجهالة بمقارنة سجلّ
    الدخول (ط-٩ الحرفي).
    """
    body = (body or "").strip()
    if not body:
        raise EngagementError("الملاحظة لا يمكن أن تكون فارغة.", status=422)
    db.session.add(Note(org_id=org.id, body=body, day=_today(org, now)))
    db.session.commit()


def list_notes(org_id: int) -> list[Note]:
    """للمشرف — الأحدث أوّلًا (م-٥)."""
    return list(
        db.session.scalars(
            select(Note).where(Note.org_id == org_id).order_by(Note.day.desc(), Note.id.desc())
        )
    )


def mark_note_read(org_id: int, note_id: int, now: datetime | None = None) -> Note:
    """تعليمٌ أحاديّ الاتّجاه — لا رجوع إلى «غير مقروءة» (م-٥: تعليم لا حذف)."""
    note = db.session.get(Note, note_id)
    if note is None or note.org_id != org_id:
        raise EngagementError("لا ملاحظة بهذا المعرّف.", status=404)
    note.read_at = now or datetime.now(UTC)
    db.session.commit()
    return note


def week_pilot(org: Org, now: datetime | None = None) -> PilotOfWeek | None:
    """طيار الأسبوع الحالي — FR-062. `None` إن لم يُختَر بعد (حالة مصمَّمة)."""
    week_start = week.week_start_local(org, now or datetime.now(UTC))
    return db.session.scalar(
        select(PilotOfWeek).where(
            PilotOfWeek.org_id == org.id, PilotOfWeek.week_start == week_start
        )
    )


def choose_week_pilot(
    org: Org,
    actor_id: int,
    user_id: int,
    reason: str,
    bonus_hours: Decimal | None = None,
    now: datetime | None = None,
) -> PilotOfWeek:
    """
    اختيار طيار الأسبوع — FR-062 · م-٦. **واحدٌ لكل أسبوع** (ث-٩).

    اختيار ثانٍ لا يستبدل الأوّل — يُرفض بـ`409` (نمط أرشفة السرب: قرارٌ
    أحاديّ الاتّجاه، وتغييره مسارٌ صريح لا حقلٌ يُستبدَل ضمنيًّا).

    **و«وزن الاختيار» (و-٢٠):** ساعاتٌ إضافية تُمنَح للمختار، وحدثُها مؤرَّخٌ
    **ببداية الأسبوع** لا بلحظة الاختيار — كما ينصّ النموذج حرفيًّا: «تظهر في
    سجلّ ساعاتي مع تاريخ هذا الأسبوع بالضبط». واختيارٌ متأخّر يوم الخميس عن
    أسبوعٍ بدأ السبت يجب ألّا ينقل ساعاته إلى يوم الخميس.

    وصفرٌ اختيارٌ مشروع: تكريمٌ بلا ساعات — فلا حدث يُكتب أصلًا.
    """
    reason = (reason or "").strip()
    if not reason:
        raise EngagementError("السبب إلزاميّ — القيمة كلّها في «لماذا».", status=422)
    if db.session.get(User, user_id) is None:
        raise EngagementError("لا طالب بهذا المعرّف.", status=422)

    bonus = Decimal(bonus_hours if bonus_hours is not None else 0)
    if bonus < 0:
        raise EngagementError("وزن الاختيار لا يكون سالبًا.", status=422)

    now = now or datetime.now(UTC)
    week_start = week.week_start_local(org, now)
    row = PilotOfWeek(
        org_id=org.id,
        week_start=week_start,
        user_id=user_id,
        reason=reason,
        actor_id=actor_id,
        bonus_hours=bonus,
    )
    db.session.add(row)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise EngagementError("طيار الأسبوع مُختار من قبل لهذا الأسبوع.", status=409) from exc

    if bonus > 0:
        occurred_at = datetime.combine(
            week_start, time.min, tzinfo=ZoneInfo(org.timezone)
        ).astimezone(UTC)
        event = ledger.append(
            [
                ledger.EventSpec(
                    org_id=org.id,
                    kind="week_pilot",
                    delta=bonus,
                    user_id=user_id,
                    occurred_at=occurred_at,
                    actor_id=actor_id,
                    reason=f"طيار الأسبوع — {reason}",
                )
            ]
        )[0]
        row.point_event_id = event.id

    db.session.commit()
    return row
