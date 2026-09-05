"""
التصحيح والتعديل القرآني — FR-035 · FR-036 · FR-037 · FR-080 (و-٦).

**راصد قاعدة، والتعديل اليدوي استثناء** (`ADR-004`): تصحيحٌ بحدث معاكس أو
إضافةٌ لسجلّ ناقص، كلاهما **بسبب مكتوب إلزاميًّا**، وكلاهما يظهر في سجلّ
التدقيق **ذرّيًّا مع الحدث نفسه** — لا معاملتين منفصلتين (`docs/slices/و-٦.md`
§٢.٢). **بلا `raw_row_id`**: الإدخال اليدوي مستقلّ عن خطّ استيراد راصد
تمامًا (`HANDOFF.md` §٩).
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from ..extensions import db
from ..models import Membership, Org, PointEvent, User
from ..rules.engine import Achievement, hours_for
from . import audit, ledger
from .deck import recent_events

AUDIT_KIND = "quran_correction"


class QuranError(Exception):
    """خطأ عملٍ يُترجَم إلى رمز حالة في المسار — لا يعرف HTTP (نمط `ReadingError`)."""

    def __init__(self, message: str, status: int = 422):
        self.status = status
        super().__init__(message)


def _local_start_of_day_utc(org: Org, d: date) -> datetime:
    """
    `RULES.md` §٩ — نفس تحويل `reading.occurred_at_for`/`rules_admin`/`fuel`،
    مكرَّر عمدًا لا مستورَدًا (ثلاثة أسطر لا تبرّر اقتران و-٦ بوحدة أخرى مغلقة).
    """
    return datetime.combine(d, time.min, tzinfo=ZoneInfo(org.timezone)).astimezone(UTC)


def _local_today(org: Org) -> date:
    return datetime.now(ZoneInfo(org.timezone)).date()


def roster(org_id: int) -> list[User]:
    """
    طلاب المنظمة النشِطون بعضوية سارية — لملء قائمة اختيار الهدف.

    **نفس فلترة `services/entry._roster`، مكرَّرة عمدًا** (السطور القليلة لا
    تبرّر استيراد خدمة أخرى — نفس منطق `_local_start_of_day_utc` أعلاه).
    """
    return list(
        db.session.scalars(
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(User.org_id == org_id, User.is_active.is_(True), Membership.left_at.is_(None))
            .order_by(User.full_name)
        )
    )


def _load_target(org_id: int, user_id: int) -> User:
    target = db.session.get(User, user_id)
    if target is None or target.org_id != org_id:
        # رسالة واحدة لغير الموجود وللخارج عن المنظمة — التفريق يكشف وجود
        # مستخدمين في منظمات أخرى (نمط `ResetPin`).
        raise QuranError("لا طالب بهذا المعرّف.", status=404)
    return target


def reverse(org: Org, event_id: int, reason: str, actor_id: int) -> PointEvent:
    """
    FR-035 · FR-080 — تصحيحٌ بحدث معاكس. **الحدث الأصل قد يكون أيّ `kind`**،
    بما فيه `correction` نفسه (تصحيح تصحيح مسموح ومختبَر منذ و-١، انظر
    `docs/slices/و-٦.md` §٢.١أ) — `ledger.reverse_pending` لا يفحص `kind`
    الأصل إطلاقًا.
    """
    event = db.session.get(PointEvent, event_id)
    if event is None or event.org_id != org.id:
        raise QuranError("لا حدث بهذا المعرّف.", status=404)

    try:
        correction = ledger.reverse_pending(event, reason, actor_id)
    except ValueError as exc:
        raise QuranError(str(exc)) from exc

    audit.record(
        org_id=org.id,
        kind=AUDIT_KIND,
        summary=f"تصحيح: عكس الحدث #{event.id} بمقدار {correction.delta} — {correction.reason}",
        actor_id=actor_id,
        before={"event_id": event.id, "kind": event.kind, "delta": str(event.delta)},
        after={"event_id": correction.id, "kind": correction.kind, "delta": str(correction.delta)},
    )
    db.session.commit()
    return correction


def add_entry(
    org: Org,
    user_id: int,
    occurred_on: date,
    activity_type: str,
    quantity: Decimal,
    mastery: str | None,
    reason: str,
    actor_id: int,
) -> PointEvent:
    """
    FR-036 — إضافة سجلّ قرآني ناقص يدويًّا. **الساعات محسوبة عبر `rules/engine`
    كأي إنجاز** (AGENTS ٥) — لا رقم يُكتب مباشرةً، ولا `raw_rows` وسيطة.
    """
    if not reason or not reason.strip():
        raise QuranError("الإضافة اليدوية توجب سببًا مكتوبًا.")
    if occurred_on > _local_today(org):
        raise QuranError("لا يمكن تسجيل إنجاز بتاريخ لم يأتِ بعد.")

    target = _load_target(org.id, user_id)
    occurred_at = _local_start_of_day_utc(org, occurred_on)

    try:
        delta = hours_for(
            org.id,
            Achievement(
                user_id=target.id,
                occurred_at=occurred_at,
                activity_type=activity_type,
                quantity=quantity,
                mastery=mastery,
            ),
        )
    except ValueError as exc:
        raise QuranError(str(exc)) from exc

    event = ledger.append_pending(
        [
            ledger.EventSpec(
                org_id=org.id,
                kind="manual",
                delta=delta,
                user_id=target.id,
                occurred_at=occurred_at,
                reason=reason.strip(),
                actor_id=actor_id,
            )
        ]
    )[0]

    summary = f"إضافة يدوية: {delta} ساعة لـ{target.full_name} ({activity_type}) — {reason.strip()}"
    audit.record(
        org_id=org.id,
        kind=AUDIT_KIND,
        summary=summary,
        actor_id=actor_id,
        after={"event_id": event.id, "kind": event.kind, "delta": str(event.delta)},
    )
    db.session.commit()
    return event


def recent_events_for(org: Org, user_id: int) -> list[PointEvent]:
    """قراءة خالصة لملء شاشة الاختيار قبل التصحيح — لا كتابة."""
    _load_target(org.id, user_id)
    return recent_events(org.id, user_id)
