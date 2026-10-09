"""
طلبات القراءة: الطالب يُرسل، والمشرف يعتمد أو يرفض.

**هذه أوّل خدمة إنتاج تستدعي `ledger`.** وحدّها المعلَن: تقرّر **متى** يستحقّ
الاعتمادُ حدثًا ولماذا؛ و`ledger` يعرف **كيف** يُلحق حدثٌ صحيح (AGENTS ٨).
فلا يظهر `PointEvent(` هنا، ولا يعرف `ledger` ما «القراءة».

@implements FR-020, FR-021, FR-022, FR-023, FR-024, FR-090, FR-091, FR-092, FR-093
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Membership, Org, PointEvent, ReadingSubmission, Team, User
from ..rules.engine import Achievement, ruleset_at
from . import audit, ledger, week

ACTIVITY = "reading"
KIND = "reading"

# و-١١ — تحضير القراءة. `kind` على الحدث يبقى `'reading'` للبرنامجين معًا
# (`services/readiness.py` يحسب «أرضي» من `kind IN ('quran','reading')`) —
# `activity_type` وحده يميّز الوزن، نفس سابقة `seed.py` (إنجازات متعدّدة
# تحت `kind` ثابت واحد).
TAHDIR = "tahdir"
TAHDIR_MIN_PAGES = 7
TAHDIR_WEEK_TARGET_PAGES = 28
# أيام التحضير في الأسبوع — السبت إلى الأربعاء (`و-١١`).
TAHDIR_WEEK_DAYS = 4

# عتبتا درجات الانتظام، **منقولتان حرفيًّا من النموذج المعتمد**
# (`ratio >= 0.9 ? 'ممتاز' : ratio >= 0.5 ? 'منتظم' : 'يحتاج متابعة'`).
#
# وهي **قاعدة عمل لا عرض**، فمكانها هنا لا في الواجهة («الواجهة تعرض ولا
# تحسب»). وكونها رقمين في سطرٍ واحد يجعل تغييرها قرارًا في مكانٍ واحد، لا
# بحثًا في شاشات.
TAHDIR_TIER_GOOD = Decimal("0.9")
TAHDIR_TIER_FAIR = Decimal("0.5")
# Python `date.weekday()`: الاثنين=٠..الأحد=٦. الأحد–الأربعاء المطلوبة = {٦,٠,١,٢}.
TAHDIR_ALLOWED_WEEKDAYS = {6, 0, 1, 2}

# `API.md §١` — «`/me/readings` ٢٠/يوم». الرقم من الوثيقة لا من اجتهادٍ هنا.
MAX_SUBMISSIONS_PER_DAY = 20


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


def _check_tahdir_day(read_on: date) -> None:
    """ث-١٨ — تحضير القراءة الأحد–الأربعاء حصرًا. القاعدة تحرسه أيضًا (دفاع مزدوج)."""
    if read_on.weekday() not in TAHDIR_ALLOWED_WEEKDAYS:
        raise ReadingError("تحضير القراءة يكون من الأحد إلى الأربعاء فقط.")


def _check_daily_quota(org: Org, user_id: int) -> None:
    """
    `API.md §١`: «`/me/readings` ٢٠/يوم». **كان موثَّقًا وغير منفَّذ** حتى
    و-٢١ — وحدٌ في وثيقةٍ لا يحدّ شيئًا.

    و`uq_reading_per_day` لا يكفي: يمنع تكرار **نفس العنوان** في نفس اليوم،
    فطالبٌ يكتب مئة عنوان مختلف يُغرق طابور المشرف بلا أن يلمس القيد. وإغراقُ
    الطابور يعني أن الاعتماد يتأخّر على الجميع (خ-١).

    **والعدّ على يوم الإرسال لا على `read_on`:** التسجيل بأثرٍ رجعيّ مشروع
    (`read_on` ماضٍ)، والمقصود حدُّ الإرسال لا حدُّ المواضيع.
    """
    since = datetime.combine(local_today(org), time.min, tzinfo=ZoneInfo(org.timezone))
    sent_today = db.session.scalar(
        select(func.count(ReadingSubmission.id)).where(
            ReadingSubmission.user_id == user_id,
            ReadingSubmission.created_at >= since.astimezone(UTC),
        )
    )
    if sent_today >= MAX_SUBMISSIONS_PER_DAY:
        raise ReadingError(
            f"بلغتَ حدّ {MAX_SUBMISSIONS_PER_DAY} طلبًا في اليوم — أعِد المحاولة غدًا.",
            status=429,
        )


def submit(
    org: Org,
    user_id: int,
    read_on: date,
    pages: int,
    book_title: str,
    activity_type: str = ACTIVITY,
) -> ReadingSubmission:
    """
    طلبٌ معلَّق **لا يمنح ساعات** (FR-021 · FR-091): `point_event_id` يبقى
    فارغًا، وث-٥ في القاعدة يمنع غير ذلك.
    """
    if read_on > local_today(org):
        raise ReadingError("لا يمكن تسجيل قراءة بتاريخ لم يأتِ بعد.")
    if activity_type == TAHDIR:
        _check_tahdir_day(read_on)
    _check_daily_quota(org, user_id)

    submission = ReadingSubmission(
        org_id=org.id,
        user_id=user_id,
        read_on=read_on,
        pages=pages,
        book_title=book_title.strip(),
        activity_type=activity_type,
        status="pending",
    )
    db.session.add(submission)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ReadingError("سجّلت هذا الكتاب في هذا اليوم من قبل.", status=409) from exc
    return submission


def admin_submit(
    org: Org,
    actor_id: int,
    user_id: int,
    read_on: date,
    pages: int,
    book_title: str,
    activity_type: str = TAHDIR,
) -> Review:
    """
    FR-092 — إضافة مباشرة نيابةً عن طالب: **معتمَدة فورًا**، بلا مرور بحالة
    معلَّقة (نمط `services/quran.add_entry`، و-٦). نفس فحوص `submit()` تسري
    هنا حرفيًّا — لا استثناء إداريّ لقواعد التاريخ أو يوم الأسبوع.

    ذرّيّة مع `audit_log`: `ledger.append_pending` (`flush` لا `commit`) ثم
    `audit.record` ثم `commit` واحد — فشلٌ في أيّهما لا يترك حدثًا يتيمًا.
    """
    if read_on > local_today(org):
        raise ReadingError("لا يمكن تسجيل قراءة بتاريخ لم يأتِ بعد.")
    if activity_type == TAHDIR:
        _check_tahdir_day(read_on)

    target = db.session.get(User, user_id)
    if target is None or target.org_id != org.id:
        raise ReadingError("لا طالب بهذا المعرّف.", status=404)

    occurred_at = occurred_at_for(org, read_on)
    try:
        hours = ruleset_at(org.id, occurred_at).hours_for(
            Achievement(
                user_id=user_id,
                occurred_at=occurred_at,
                activity_type=activity_type,
                quantity=Decimal(pages),
            )
        )
    except ValueError as exc:
        raise ReadingError(str(exc)) from exc

    event = ledger.append_pending(
        [
            ledger.EventSpec(
                org_id=org.id,
                kind=KIND,
                delta=hours,
                user_id=user_id,
                occurred_at=occurred_at,
                actor_id=actor_id,
            )
        ]
    )[0]

    submission = ReadingSubmission(
        org_id=org.id,
        user_id=user_id,
        read_on=read_on,
        pages=pages,
        book_title=book_title.strip(),
        activity_type=activity_type,
        status="approved",
        reviewer_id=actor_id,
        reviewed_at=datetime.now(UTC),
        point_event_id=event.id,
    )
    db.session.add(submission)
    label = "تحضير" if activity_type == TAHDIR else "قراءة"
    summary = f"إضافة {label} مباشرة: {pages} صفحة لـ{target.full_name} ({book_title.strip()})"
    try:
        # `flush` يُدرج فعليًّا فيصطدم بقيد `UNIQUE` هنا لا عند `commit` —
        # كلاهما داخل هذا الحارس الواحد، وإلا مرّ تكرارٌ بـ`500` خام
        # (اكتُشف عدائيًّا: التقاط `submission.id` قبل `commit` كان يترك
        # الإدراج نفسه بلا حماية).
        db.session.flush()  # لالتقاط submission.id قبل بناء سطر التدقيق
        audit.record(
            org_id=org.id,
            kind="reading_admin_entry",
            summary=summary,
            actor_id=actor_id,
            after={"event_id": event.id, "submission_id": submission.id, "delta": str(event.delta)},
        )
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ReadingError("سجّلت هذا الكتاب في هذا اليوم من قبل.", status=409) from exc

    return Review(submission.id, "approved", str(hours))


def list_for_user(
    user_id: int, activity_type: str = ACTIVITY
) -> list[tuple[ReadingSubmission, PointEvent | None]]:
    """
    طلبات الطالب الأحدث أوّلًا، ومعها حدثها إن اعتُمد — بلا N+1.

    **مُصفًّى على `activity_type`** (و-١١) — بلا هذا، تحضير القراءة كان
    سيظهر مختلطًا في «قراءاتي» العامّة بصمت.
    """
    return db.session.execute(
        select(ReadingSubmission, PointEvent)
        .outerjoin(PointEvent, PointEvent.id == ReadingSubmission.point_event_id)
        .where(
            ReadingSubmission.user_id == user_id, ReadingSubmission.activity_type == activity_type
        )
        .order_by(ReadingSubmission.created_at.desc(), ReadingSubmission.id.desc())
    ).all()


def pending_queue(
    org_id: int, activity_type: str = ACTIVITY
) -> list[tuple[ReadingSubmission, str]]:
    """
    طابور المشرف: **الأقدم أوّلًا** (م-٢)، وعلى مستوى الجمعية لا السرب
    (`ARCHITECTURE.md` §٧.٣). يُرجع الطلب واسم صاحبه بلا استعلام لكل صفّ.

    **مُصفًّى على `activity_type`** (و-١١) — بلا هذا، تحضير القراءة كان
    سيظهر مختلطًا في طابور القراءة العامّ بصمت.
    """
    return db.session.execute(
        select(ReadingSubmission, User.full_name)
        .join(User, User.id == ReadingSubmission.user_id)
        .where(
            ReadingSubmission.org_id == org_id,
            ReadingSubmission.status == "pending",
            ReadingSubmission.activity_type == activity_type,
        )
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
                # activity_type **من الصفّ نفسه** لا ثابتًا (و-١١): طلب تحضير
                # يُعتمَد بوزن `tahdir` لا وزن `reading` رغم إعادة استعمال
                # هذا المسار حرفيًّا للبرنامجين معًا.
                activity_type=s.activity_type,
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


# ═══ FR-093 — التقرير الأسبوعي لتحضير القراءة ═══

_ARABIC_WEEKDAY = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


def _tahdir_rows_this_week(
    org: Org, week_start: date, user_id: int | None = None
) -> list[tuple[ReadingSubmission, str]]:
    window_end = week_start + timedelta(days=3)  # الأربعاء
    conditions = [
        ReadingSubmission.org_id == org.id,
        ReadingSubmission.activity_type == TAHDIR,
        ReadingSubmission.status == "approved",
        ReadingSubmission.read_on >= week_start,
        ReadingSubmission.read_on <= window_end,
    ]
    if user_id is not None:
        conditions.append(ReadingSubmission.user_id == user_id)
    return db.session.execute(
        select(ReadingSubmission, User.full_name)
        .join(User, User.id == ReadingSubmission.user_id)
        .where(*conditions)
    ).all()


def _summarize_week(week_start: date, pages_by_day: dict[date, int]) -> dict:
    """
    **يومٌ مكتمل = إرسالٌ معتمَد بصفحات ≥٧** (لا معلَّق، مطابقًا لمبدأ FR-021).
    `percent` مبنيّ على **مجموع الصفحات** لا عدد الأيام — الحقلان يُعرضان
    معًا لا أحدهما بديلًا عن الآخر (`docs/slices/و-١١.md` §٢).
    """
    days = []
    for i in range(4):
        d = week_start + timedelta(days=i)
        pages = pages_by_day.get(d, 0)
        days.append(
            {
                "date": d,
                "weekday": _ARABIC_WEEKDAY[d.weekday()],
                "completed": pages >= TAHDIR_MIN_PAGES,
                "pages": pages,
            }
        )
    pages_total = sum(day["pages"] for day in days)
    percent = round(pages_total / TAHDIR_WEEK_TARGET_PAGES * 100, 1)
    return {
        "week_start": week_start,
        "days": days,
        "pages_total": pages_total,
        "target_pages": TAHDIR_WEEK_TARGET_PAGES,
        "percent": percent,
        # «متعثّر» = دون ١٠٠٪ من الهدف الأسبوعي، **بلا هامش تسامح** (قرار مؤكَّد).
        "struggling": percent < 100,
    }


def weekly_report(org: Org, user_id: int, now: datetime | None = None) -> dict:
    """تحضير طالبٍ واحد لأسبوعه الحاليّ (FR-093 · `GET /me/tahdir`)."""
    week_start = week.week_start_local(org, now or datetime.now(UTC))
    rows = _tahdir_rows_this_week(org, week_start, user_id)
    pages_by_day: dict[date, int] = {}
    for submission, _name in rows:
        pages_by_day[submission.read_on] = (
            pages_by_day.get(submission.read_on, 0) + submission.pages
        )
    return _summarize_week(week_start, pages_by_day)


def _tahdir_days_between(org: Org, from_day: date, to_day: date) -> list[date]:
    """
    أيام التحضير المؤهَّلة داخل فترة — **تعميمٌ للأسبوع لا استبدالٌ له.**

    التحضير أربعة أيام من بداية كل أسبوع؛ ففترةٌ تمتدّ أسابيع تُؤخَذ منها
    أيّامُ التحضير في كل أسبوع مقطوعةً بحدّي الفترة. وفترةٌ طولها أسبوعٌ واحد
    تعطي الأيام الأربعة نفسها — فالتقرير الأسبوعيّ حالةٌ خاصّة من هذا لا
    مسارٌ ثانٍ يتباعد عنه.
    """
    days: list[date] = []
    cursor = week.week_start_of(org, from_day)
    while cursor <= to_day:
        for i in range(TAHDIR_WEEK_DAYS):
            day = cursor + timedelta(days=i)
            if from_day <= day <= to_day:
                days.append(day)
        cursor += timedelta(days=7)
    return days


def _tier_of(active: int, total: int) -> str:
    """`'good' | 'fair' | 'low'` — القرار هنا، والواجهة تُلوّن وتُسمّي فقط."""
    if total == 0:
        return "low"
    ratio = Decimal(active) / Decimal(total)
    if ratio >= TAHDIR_TIER_GOOD:
        return "good"
    if ratio >= TAHDIR_TIER_FAIR:
        return "fair"
    return "low"


def org_tahdir_report(
    org: Org,
    from_day: date | None = None,
    to_day: date | None = None,
    now: datetime | None = None,
) -> dict:
    """
    تقرير التحضير لفترةٍ محدَّدة — وافتراضُها أسبوع اليوم (FR-093).

    النموذج المعتمد يضيف «إصدار تقرير بفترة محدَّدة» وثلاث بطاقات إحصاء
    ودرجاتِ انتظام. والدرجات **تُحسب هنا** لا في الشاشة.
    """
    if (from_day is None) != (to_day is None):
        raise ReadingError("الفترة تُحدَّد بطرفيها معًا أو لا تُحدَّد.")
    if from_day is None or to_day is None:
        start = week.week_start_local(org, now or datetime.now(UTC))
        from_day, to_day = start, start + timedelta(days=TAHDIR_WEEK_DAYS - 1)
    if from_day > to_day:
        raise ReadingError("تاريخ البداية بعد تاريخ النهاية.")

    eligible = _tahdir_days_between(org, from_day, to_day)
    eligible_set = set(eligible)

    roster = db.session.execute(
        select(User.id, User.full_name, Team.name)
        .join(Membership, Membership.user_id == User.id)
        .join(Team, Team.id == Membership.team_id)
        .where(User.org_id == org.id, User.is_active.is_(True), Membership.left_at.is_(None))
    ).all()

    rows = db.session.execute(
        select(ReadingSubmission).where(
            ReadingSubmission.org_id == org.id,
            ReadingSubmission.activity_type == TAHDIR,
            ReadingSubmission.status == "approved",
            ReadingSubmission.read_on >= from_day,
            ReadingSubmission.read_on <= to_day,
        )
    ).scalars()

    pages_by_user_day: dict[int, dict[date, int]] = {}
    for submission in rows:
        if submission.read_on in eligible_set:
            by_day = pages_by_user_day.setdefault(submission.user_id, {})
            by_day[submission.read_on] = by_day.get(submission.read_on, 0) + submission.pages

    students = []
    for user_id, full_name, team_name in roster:
        by_day = pages_by_user_day.get(user_id, {})
        active = sum(1 for pages in by_day.values() if pages >= TAHDIR_MIN_PAGES)
        pages_total = sum(by_day.values())
        students.append(
            {
                "user_id": user_id,
                "full_name": full_name,
                "team_name": team_name,
                "days_completed": active,
                "days_total": len(eligible),
                "pages_total": pages_total,
                "percent": round(pages_total / (TAHDIR_MIN_PAGES * len(eligible)) * 100, 1)
                if eligible
                else 0.0,
                "tier": _tier_of(active, len(eligible)),
                # يبقى للتوافق مع مستهلكٍ قائم — «متعثّر» دون الهدف بلا تسامح.
                "struggling": active < len(eligible),
            }
        )

    students.sort(key=lambda r: r["full_name"])
    return {
        "from_day": from_day,
        "to_day": to_day,
        "days_total": len(eligible),
        "totals": {
            "pages": sum(s["pages_total"] for s in students),
            "participants": sum(1 for s in students if s["days_completed"]),
            "fully_regular": sum(
                1 for s in students if s["days_total"] and s["days_completed"] == s["days_total"]
            ),
        },
        "students": students,
    }
