"""
حالة الطيران — `RULES.md` §٨ و ث-١٤.

**محسوبة لا مخزَّنة.** لا عمود `grounded` في `users`: القيمة المشتقّة تفترق عن
مصدرها في أوّل مسار يَنسى تحديثها — وهي نفس علّة رفض «عمود رصيد» في ADR-001.

**المالك الوحيد لهذا الحساب.** `deck` و`standings` تستدعيانه ولا تعيدان حسابه
(ARCHITECTURE §٣ — مالكون أحاديّون).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select

from ..extensions import db
from ..models import Org, PointEvent

# القرآن والقراءة معًا — نصّ المستخدم صراحةً. الحضور والسؤال اليومي لا يرفعان
# الطائرة: حضورُ حصّةٍ بلا تسميع ولا قراءة ليس النشاط الذي تقيسه هذه الحالة.
ACTIVITY_KINDS = ("quran", "reading")


@dataclass(frozen=True)
class Flight:
    grounded: bool
    last_activity_on: date | None


def flight_state(org: Org, user_id: int, now: datetime | None = None) -> Flight:
    """طيّار واحد — غلافٌ على `flight_states` (المصدر الوحيد لصيغة الحساب)."""
    return flight_states(org, [user_id], now)[user_id]


def flight_states(
    org: Org, user_ids: Sequence[int], now: datetime | None = None
) -> dict[int, Flight]:
    """
    نسخة مجمَّعة — استعلام واحد لعدّة طيّارين، لا `flight_state` في حلقة.

    اللوحات (و-٩ب) تحتاج حالة عضو سرب كامل دفعة واحدة، وعقدها الموثَّق يشترط
    **استعلام واحد بلا N+1**؛ استدعاء `flight_state` في حلقة كان سينتهكه رغم
    مروره في `reports.py` (تقرير مشرف غير مقيَّد بهذا الشرط). أرضيّ ⟺ آخر حدث
    نشاط أقدم من `orgs.grounded_after_days` — نفس تعريف `flight_state` تمامًا،
    والعتبة **عمود إعداد لا رقم في الكود** (ف-٢).
    """
    if not user_ids:
        return {}

    rows = db.session.execute(
        select(PointEvent.user_id, func.max(PointEvent.occurred_at))
        .where(
            PointEvent.org_id == org.id,
            PointEvent.user_id.in_(user_ids),
            PointEvent.kind.in_(ACTIVITY_KINDS),
        )
        .group_by(PointEvent.user_id)
    ).all()
    last_by_user = dict(rows)

    cutoff = (now or datetime.now(UTC)) - timedelta(days=org.grounded_after_days)
    result = {}
    for user_id in user_ids:
        last = last_by_user.get(user_id)
        if last is None:
            # طالبٌ لم يبدأ بعدُ ليس متأخّرًا. وسمُه أرضيًّا في أوّل يوم هو أسوأ
            # ما تفعله منصة تحفيز بمن لم يُتَح له أن يُنجز شيئًا.
            result[user_id] = Flight(grounded=False, last_activity_on=None)
        else:
            result[user_id] = Flight(grounded=last < cutoff, last_activity_on=last.date())
    return result
