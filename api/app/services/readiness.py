"""
حالة الطيران — `RULES.md` §٨ و ث-١٤.

**محسوبة لا مخزَّنة.** لا عمود `grounded` في `users`: القيمة المشتقّة تفترق عن
مصدرها في أوّل مسار يَنسى تحديثها — وهي نفس علّة رفض «عمود رصيد» في ADR-001.

**المالك الوحيد لهذا الحساب.** `deck` و`standings` تستدعيانه ولا تعيدان حسابه
(ARCHITECTURE §٣ — مصفوفة الملكية).
"""

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
    """
    أرضيّ ⟺ آخر حدث نشاط أقدم من `orgs.grounded_after_days`.

    والعتبة **عمود إعداد لا رقم في الكود** (ف-٢): تغيير القاعدة صفٌّ لا نشر.
    والعودة تلقائية — أوّل حدث يعيده طائرًا بلا تدخّل مشرف.
    """
    last = db.session.scalar(
        select(func.max(PointEvent.occurred_at)).where(
            PointEvent.org_id == org.id,
            PointEvent.user_id == user_id,
            PointEvent.kind.in_(ACTIVITY_KINDS),
        )
    )
    if last is None:
        # طالبٌ لم يبدأ بعدُ ليس متأخّرًا. وسمُه أرضيًّا في أوّل يوم هو أسوأ ما
        # تفعله منصة تحفيز بمن لم يُتَح له أن يُنجز شيئًا.
        return Flight(grounded=False, last_activity_on=None)

    cutoff = (now or datetime.now(UTC)) - timedelta(days=org.grounded_after_days)
    return Flight(grounded=last < cutoff, last_activity_on=last.date())
