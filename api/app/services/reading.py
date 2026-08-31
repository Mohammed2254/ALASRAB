"""
طلبات القراءة: الطالب يُرسل، والمشرف يعتمد أو يرفض.

**هذه أوّل خدمة إنتاج تستدعي `ledger`.** وحدّها المعلَن: تقرّر **متى** يستحقّ
الاعتمادُ حدثًا ولماذا؛ و`ledger` يعرف **كيف** يُلحق حدثٌ صحيح (AGENTS ٨).
فلا يظهر `PointEvent(` هنا، ولا يعرف `ledger` ما «القراءة».
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Org, PointEvent, ReadingSubmission
from ..rules.engine import Achievement, ruleset_at
from . import ledger

ACTIVITY = "reading"
KIND = "reading"


class ReadingError(Exception):
    """خطأ عملٍ يُترجَم إلى رمز حالة في المسار — لا يعرف HTTP."""

    def __init__(self, message: str, status: int = 422):
        self.status = status
        super().__init__(message)


@dataclass(frozen=True)
class Review:
    """نتيجة مراجعة واحدة — ما يحتاجه المسار للردّ، لا كائن ORM."""

    submission_id: int
    status: str
    hours: str | None


def local_today(org: Org) -> date:
    """
    اليوم بتوقيت المنظمة لا UTC.

    طالبٌ في الرياض يسجّل مساء الخميس يجب ألّا يُرفض لأن UTC ما زال في الأربعاء
    (`RULES.md` §٩).
    """
    return datetime.now(ZoneInfo(org.timezone)).date()


def occurred_at_for(org: Org, read_on: date) -> datetime:
    """
    `RULES.md` §٩ — بداية يوم القراءة بتوقيت المنظمة، محوَّلة إلى UTC.

    اللحظة الناتجة تحدّد **أي إصدار أوزان يُختار** وحساب «أرضي» ونوافذ الأسبوع
    لاحقًا، فتركُها لاجتهاد المستدعي يعني ثلاثة أنظمة تختلف بصمت.
    """
    return datetime.combine(read_on, time.min, tzinfo=ZoneInfo(org.timezone)).astimezone(UTC)


def submit(org: Org, user_id: int, read_on: date, pages: int, book_title: str) -> ReadingSubmission:
    """
    طلبٌ معلَّق **لا يمنح ساعات** (FR-021): `point_event_id` يبقى فارغًا، وث-٥
    في القاعدة يمنع غير ذلك.
    """
    if read_on > local_today(org):
        raise ReadingError("لا يمكن تسجيل قراءة بتاريخ لم يأتِ بعد.")

    submission = ReadingSubmission(
        org_id=org.id,
        user_id=user_id,
        read_on=read_on,
        pages=pages,
        book_title=book_title.strip(),
        status="pending",
    )
    db.session.add(submission)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ReadingError("سجّلت هذا الكتاب في هذا اليوم من قبل.", status=409) from exc
    return submission


def list_for_user(user_id: int) -> list[tuple[ReadingSubmission, PointEvent | None]]:
    """طلبات الطالب الأحدث أوّلًا، ومعها حدثها إن اعتُمد — بلا N+1."""
    return db.session.execute(
        select(ReadingSubmission, PointEvent)
        .outerjoin(PointEvent, PointEvent.id == ReadingSubmission.point_event_id)
        .where(ReadingSubmission.user_id == user_id)
        .order_by(ReadingSubmission.created_at.desc(), ReadingSubmission.id.desc())
    ).all()


def pending_queue(org_id: int) -> list[tuple[ReadingSubmission, str]]:
    """
    طابور المشرف: **الأقدم أوّلًا** (م-٢)، وعلى مستوى الجمعية لا السرب
    (`ARCHITECTURE.md` §٧.٣). يُرجع الطلب واسم صاحبه بلا استعلام لكل صفّ.
    """
    from ..models import User

    return db.session.execute(
        select(ReadingSubmission, User.full_name)
        .join(User, User.id == ReadingSubmission.user_id)
        .where(ReadingSubmission.org_id == org_id, ReadingSubmission.status == "pending")
        .order_by(ReadingSubmission.created_at, ReadingSubmission.id)
    ).all()


def _load_pending(org_id: int, submission_ids: list[int]) -> list[ReadingSubmission]:
    found = db.session.scalars(
        select(ReadingSubmission).where(
            ReadingSubmission.org_id == org_id,
            ReadingSubmission.id.in_(submission_ids),
            ReadingSubmission.status == "pending",
        )
    ).all()
    missing = set(submission_ids) - {s.id for s in found}
    if missing:
        # الفشل قبل أي إلحاق: دفعةٌ نصفية تترك المشرف لا يعرف أين توقّفت،
        # فيعيد الاعتماد كلّه (ق-٢٤).
        raise ReadingError(f"طلبات غير موجودة أو سبق البتّ فيها: {sorted(missing)}", status=409)
    return found


def approve(org: Org, submission_ids: list[int], reviewer_id: int) -> list[Review]:
    """
    اعتماد **ذرّي**: إمّا كل الطلبات أو لا شيء (ق-٢٤).

    والحدث يُنشأ بـ`occurred_at` من **تاريخ القراءة** لا تاريخ الاعتماد
    (FR-023): تأخّر المشرف أسبوعًا لا ينقل إنجاز الطالب إلى أسبوع لم يصنعه.
    """
    if not submission_ids:
        raise ReadingError("لا طلبات محدَّدة.")

    submissions = _load_pending(org.id, submission_ids)
    now = datetime.now(UTC)

    specs, hours_by_id = [], {}
    for s in submissions:
        occurred_at = occurred_at_for(org, s.read_on)
        hours = ruleset_at(org.id, occurred_at).hours_for(
            Achievement(
                user_id=s.user_id,
                occurred_at=occurred_at,
                activity_type=ACTIVITY,
                quantity=s.pages,
            )
        )
        hours_by_id[s.id] = hours
        specs.append(
            ledger.EventSpec(
                org_id=org.id,
                kind=KIND,
                delta=hours,
                user_id=s.user_id,
                occurred_at=occurred_at,
                actor_id=reviewer_id,
                external_ref=f"reading:{s.id}",
            )
        )

    events = ledger.append(specs)

    # المعرّفات تُقرأ **قبل** أي تعديل: قراءة `event.id` بعد الإلحاق تُطلق
    # تحديثًا كسولًا، والتحديث يُطلق autoflush — فيُرسَل `status='approved'`
    # وحده قبل إسناد `point_event_id`، ويرفضه ث-٥ بحقّ.
    #
    # وهذا ليس التفافًا على القيد بل تصحيحٌ له: الصفّ يجب ألّا يمرّ بحالة
    # «معتمد بلا حدث» ولو للحظة داخل معاملة.
    event_ids = [event.id for event in events]
    for s, event_id in zip(submissions, event_ids, strict=True):
        s.point_event_id = event_id
        s.status = "approved"
        s.reviewer_id = reviewer_id
        s.reviewed_at = now
    db.session.commit()

    return [Review(s.id, "approved", str(hours_by_id[s.id])) for s in submissions]


def reject(org: Org, submission_id: int, reviewer_id: int, reason: str) -> Review:
    """الرفض يوجب سببًا يراه الطالب (ث-٦ · FR-024). ولا حدث ولا ساعات."""
    if not reason or not reason.strip():
        raise ReadingError("الرفض يوجب سببًا يراه الطالب.")

    submission = _load_pending(org.id, [submission_id])[0]
    submission.status = "rejected"
    submission.review_reason = reason.strip()
    submission.reviewer_id = reviewer_id
    submission.reviewed_at = datetime.now(UTC)
    db.session.commit()
    return Review(submission.id, "rejected", None)
