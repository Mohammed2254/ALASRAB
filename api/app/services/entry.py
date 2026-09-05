"""
الحضور اليدويّ — FR-041 · FR-042 (احتياطيّ — و-٩هـ).

**لا جدول جديد** — يكتب `point_events` مباشرةً (`kind='attendance'`)، ويمرّ
من `rules/engine` كأي نشاط آخر (ف-٦: «الحضور نشاط في جدول الأوزان، إن قرّرت
أنه لا يمنح ساعات يُضبط وزنه إلى صفر — صفّ لا كود»).

**idempotency بقيد `point_events` القائم أصلًا لا بقيد جديد** (نمط ث-٣،
ومُدرَج صراحةً في توثيق `ledger.py` منذ البداية كأحد سبعة مسارات تحترم
`external_ref` حتميًّا): `attendance:{week_start}:{user_id}`. إرسال الدفعة
مرّتين يصطدم بـ`uq_event_external_ref` القائم — مُثبَت بـSQL خام قبل هذا
الملفّ (`docs/slices/و-٩.md`).

**التراجع خلال ٥ دقائق يُقاس من `created_at`** (وقت التسجيل) لا
`occurred_at` (وقت الحضور نفسه، دائمًا بداية الأسبوع) — والتصحيح نفسه محميّ
بـ`external_ref` حتميّ آخر يمنع تراجعًا مزدوجًا.
"""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Membership, Org, PointEvent, User
from ..rules.engine import Achievement, ruleset_at
from . import ledger

UNDO_WINDOW = timedelta(minutes=5)
ACTIVITY = "attendance"


class AttendanceError(Exception):
    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


def _week_start(org: Org, now: datetime) -> date:
    """نفس تعريف نافذة `standings.py`/`engagement.py` (نمط RULES.md §٩)."""
    local_now = now.astimezone(ZoneInfo(org.timezone))
    days_since_start = (local_now.weekday() - org.week_starts_on) % 7
    return local_now.date() - timedelta(days=days_since_start)


def _week_start_utc(org: Org, week_start: date) -> datetime:
    return datetime.combine(week_start, time.min, tzinfo=ZoneInfo(org.timezone)).astimezone(UTC)


def _ref(week_start: date, user_id: int) -> str:
    return f"attendance:{week_start.isoformat()}:{user_id}"


def _undo_ref(week_start: date, user_id: int) -> str:
    return f"attendance-undo:{week_start.isoformat()}:{user_id}"


def _roster(org_id: int) -> list[User]:
    return list(
        db.session.scalars(
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(User.org_id == org_id, User.is_active.is_(True), Membership.left_at.is_(None))
        )
    )


def _week_events(org: Org, week_start: date) -> list[PointEvent]:
    return list(
        db.session.scalars(
            select(PointEvent).where(
                PointEvent.org_id == org.id,
                PointEvent.kind == ACTIVITY,
                PointEvent.external_ref.like(f"attendance:{week_start.isoformat()}:%"),
            )
        )
    )


def week_status(org: Org, now: datetime | None = None) -> dict:
    """حالة الأسبوع الحالي — للشاشة عند الفتح (FR-041)."""
    now = now or datetime.now(UTC)
    week_start = _week_start(org, now)
    events = _week_events(org, week_start)
    undo_until = None
    if events:
        undo_until = min(e.created_at for e in events) + UNDO_WINDOW
        if undo_until <= now:
            undo_until = None

    present_ids = {e.user_id for e in events}
    roster = _roster(org.id)
    absent_ids = [u.id for u in roster if u.id not in present_ids] if events else []

    return {
        "week_start": week_start,
        "already_recorded": bool(events),
        "pilots": [{"user_id": u.id, "full_name": u.full_name} for u in roster],
        "absent_user_ids": absent_ids,
        "undo_until": undo_until,
    }


def record(
    org: Org, actor_id: int, absent_user_ids: list[int], now: datetime | None = None
) -> dict:
    """
    تسجيل حضور الأسبوع الحالي — **الحاضرون فقط يمنحون ساعات** (FR-041/FR-042).

    معاملة واحدة (`ledger.append` بدفعة واحدة)، وidempotency بـ`external_ref`
    حتميّ لكل طالب حاضر.
    """
    now = now or datetime.now(UTC)
    week_start = _week_start(org, now)
    occurred_at = _week_start_utc(org, week_start)

    roster = _roster(org.id)
    absent = set(absent_user_ids) & {u.id for u in roster}
    present = [u for u in roster if u.id not in absent]

    try:
        ruleset = ruleset_at(org.id, occurred_at)
        specs = [
            ledger.EventSpec(
                org_id=org.id,
                kind=ACTIVITY,
                delta=ruleset.hours_for(
                    Achievement(
                        user_id=u.id,
                        occurred_at=occurred_at,
                        activity_type=ACTIVITY,
                        quantity=Decimal("1"),
                    )
                ),
                user_id=u.id,
                occurred_at=occurred_at,
                actor_id=actor_id,
                external_ref=_ref(week_start, u.id),
            )
            for u in present
        ]
    except ValueError as exc:
        raise AttendanceError("الحضور غير مُوزَّن لهذه المنظمة بعد.", status=422) from exc

    hours_each = specs[0].delta if specs else Decimal("0.00")
    try:
        ledger.append(specs)
    except IntegrityError as exc:
        db.session.rollback()
        raise AttendanceError("الحضور مُسجَّل لهذا الأسبوع من قبل.", status=409) from exc

    return {
        "present": len(present),
        "absent": len(absent),
        "hours_each": hours_each,
        "undo_until": now + UNDO_WINDOW,
    }


def undo(org: Org, actor_id: int, now: datetime | None = None) -> int:
    """تراجعٌ عن دفعة الأسبوع الحالي كاملةً، خلال ٥ دقائق من التسجيل (FR-042)."""
    now = now or datetime.now(UTC)
    week_start = _week_start(org, now)
    events = _week_events(org, week_start)
    if not events:
        raise AttendanceError("لا حضور مسجَّل لهذا الأسبوع لتتراجع عنه.", status=404)

    oldest = min(e.created_at for e in events)
    if now - oldest > UNDO_WINDOW:
        raise AttendanceError("انتهت مهلة التراجع (٥ دقائق).", status=409)

    reason = "تراجع عن حضور الأسبوع خلال ٥ دقائق."
    specs = [
        ledger.EventSpec(
            org_id=e.org_id,
            kind="correction",
            delta=-e.delta,
            occurred_at=e.occurred_at,
            user_id=e.user_id,
            team_id=e.team_id,
            reason=reason,
            actor_id=actor_id,
            external_ref=_undo_ref(week_start, e.user_id),
        )
        for e in events
    ]
    try:
        ledger.append(specs)
    except IntegrityError as exc:
        db.session.rollback()
        raise AttendanceError("تراجعتَ عن حضور هذا الأسبوع من قبل.", status=409) from exc
    return len(events)
