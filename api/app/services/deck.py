"""
بطاقة الطيار — FR-010 · FR-011 · FR-013.

**كل رقم يُحسب هنا**، فلا تحسب الواجهة شيئًا (`AGENTS.md` ٥). وهذا الملفّ
**ينسّق ولا يملك**: الرصيد من سجلّ الأحداث، والحالة من `readiness`، والرتب من
`rank_thresholds`. ما يملكه هو **قراءة سُلّم الرتب** وحدها.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select

from ..extensions import db
from ..models import Membership, Org, PointEvent, RankThreshold, Team
from . import readiness

CENT = Decimal("0.01")


@dataclass(frozen=True)
class Deck:
    hours: Decimal
    rank: RankThreshold
    next_rank: RankThreshold | None
    progress_pct: float | None
    remaining: Decimal | None
    flight: readiness.Flight
    team: Team | None


def _hours(org_id: int, user_id: int) -> Decimal:
    """
    الرصيد = مجموع الأحداث. **لا عمود رصيد في أي مكان** (ADR-001).

    والتصحيحات سالبة، فتدخل المجموع بلا معاملة خاصّة — وهذا ما يجعل التراجع
    مجّانيًّا بدل أن يكون مسارًا ثانيًا.
    """
    total = db.session.scalar(
        select(func.coalesce(func.sum(PointEvent.delta), 0)).where(
            PointEvent.org_id == org_id,
            PointEvent.user_id == user_id,
            PointEvent.scope == "individual",
        )
    )
    return Decimal(total).quantize(CENT)


def _slice_progress(hours: Decimal, rank: RankThreshold, nxt: RankThreshold | None):
    """
    التقدّم **داخل شريحة الرتبة الحالية لا مطلقًا** (ط-٣).

    ٦١١ ساعة نحو «رائد سرب ٩٠٠» من «طيار أول ٤٠٠» = ٤٢.٢٪ لا ٦٨٪. الفرق بين
    الشريحة والمطلق أشيع خطأ في شرائط التقدّم، ونتيجته أن يرى الطالب نفسه أقرب
    ممّا هو، ثم يتوقّف الشريط عن التحرّك.

    وفي أعلى رتبة: `None` — فتعرض الواجهة **رسالة إتمام لا شريطًا ممتلئًا**.
    """
    if nxt is None:
        return None, None
    span = nxt.at_hours - rank.at_hours
    gained = max(hours - rank.at_hours, Decimal(0))
    pct = (gained / span * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return float(min(pct, Decimal(100))), (nxt.at_hours - hours).quantize(CENT)


def build(org: Org, user_id: int) -> Deck:
    """يُبنى من الأحداث والقواعد وحدها — لا قيمة ثابتة ولا مخزَّنة."""
    hours = _hours(org.id, user_id)

    ladder = db.session.scalars(
        select(RankThreshold).where(RankThreshold.org_id == org.id).order_by(RankThreshold.at_hours)
    ).all()
    if not ladder:
        raise ValueError("لا سُلّم رتب مهيّأ لهذه المنظمة.")

    # أدنى رتبة أرضيةٌ لا يُسقَط منها: رصيدٌ سالب بعد تصحيح يبقي صاحبه «طيارًا».
    reached = [i for i, r in enumerate(ladder) if hours >= r.at_hours]
    index = reached[-1] if reached else 0
    rank = ladder[index]

    # التالية بالنسبة إلى **الرتبة** لا إلى الساعات. لو قيست بالساعات لأعادت
    # العتبةَ نفسها عند رصيد سالب (٠ > −١٠)، فتصير الشريحة صفرًا ⇒ قسمة على صفر.
    nxt = ladder[index + 1] if index + 1 < len(ladder) else None
    progress_pct, remaining = _slice_progress(hours, rank, nxt)

    team = db.session.scalar(
        select(Team)
        .join(Membership, Membership.team_id == Team.id)
        .where(Membership.user_id == user_id, Membership.left_at.is_(None))
    )

    return Deck(
        hours=hours,
        rank=rank,
        next_rank=nxt,
        progress_pct=progress_pct,
        remaining=remaining,
        flight=readiness.flight_state(org, user_id),
        team=team,
    )
