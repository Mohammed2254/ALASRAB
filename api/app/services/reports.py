"""
التقرير الدوري للمشرف — FR-085.

**كل رقم مشتقّ من سجلّ الأحداث بلا جدول جديد** (`TRACEABILITY.md:90`). وهذا ليس
تقشّفًا: جدولُ ملخّصات يحتاج تحديثًا مع كل حدث، ويفترق عن مصدره في أوّل مسار
ينساه — وهي نفس علّة رفض «عمود رصيد» في ADR-001.

**قراءة خالصة:** لا `ledger` ولا كتابة ولا هجرة.

@implements FR-085
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from ..extensions import db
from ..models import Membership, Org, Team, User
from ..rules.engine import CENT
from . import hours as hours_query
from . import readiness

DEFAULT_DAYS = 7
MAX_DAYS = 90
TOP_MOVERS = 5


@dataclass(frozen=True)
class Report:
    days: int
    since: datetime
    total_hours: Decimal
    active_pilots: int
    teams: list[dict]
    top_movers: list[dict]
    grounded: list[dict]


def build(org: Org, days: int = DEFAULT_DAYS) -> Report:
    """يُبنى باستعلامين على السجلّ — بلا N+1 وبلا جدول ملخّصات."""
    days = max(1, min(days, MAX_DAYS))
    since = datetime.now(UTC) - timedelta(days=days)
    window = hours_query.sum_by_user(org.id, since)

    # صفٌّ لكل طالب في عضوية سارية، ومعه ساعات نافذته (صفر إن لم ينشط).
    rows = db.session.execute(
        select(
            User.id,
            User.full_name,
            Team.id.label("team_id"),
            Team.name.label("team_name"),
            func.coalesce(window.c.hours, 0).label("hours"),
        )
        .join(Membership, Membership.user_id == User.id)
        .join(Team, Team.id == Membership.team_id)
        .outerjoin(window, window.c.user_id == User.id)
        .where(
            User.org_id == org.id,
            User.is_active.is_(True),
            Membership.left_at.is_(None),
        )
    ).all()

    by_team: dict[int, dict] = {}
    movers, total = [], Decimal(0)
    for user_id, full_name, team_id, team_name, hours in rows:
        hours = Decimal(hours).quantize(CENT)
        total += hours
        team = by_team.setdefault(
            team_id, {"id": team_id, "name": team_name, "hours": Decimal(0), "members": 0}
        )
        team["hours"] += hours
        team["members"] += 1
        if hours > 0:
            movers.append({"user_id": user_id, "full_name": full_name, "hours": hours})

    for team in by_team.values():
        # المعدّل لا المجموع — اتّساقًا مع صدارة الأسراب (FR-051): المجموع يقيس
        # الحجم لا الاجتهاد، فسربٌ من عشرة يسبق سربًا من أربعة بلا فضل.
        team["avg_hours"] = (team["hours"] / team["members"]).quantize(CENT)

    movers.sort(key=lambda m: m["hours"], reverse=True)

    # «من سقط» بالاسم — **للمشرف وحده**. القرار ٥ يمنع عرضه للطلاب، وهذه شاشة
    # إشراف: من يلاحق الطالب يحتاج أن يعرف من يلاحق.
    grounded = []
    for user_id, full_name, _team_id, _team_name, _hours in rows:
        flight = readiness.flight_state(org, user_id)
        if flight.grounded:
            grounded.append(
                {
                    "user_id": user_id,
                    "full_name": full_name,
                    "last_activity_on": flight.last_activity_on,
                }
            )

    return Report(
        days=days,
        since=since,
        total_hours=total.quantize(CENT),
        active_pilots=len(movers),
        teams=sorted(by_team.values(), key=lambda t: t["avg_hours"], reverse=True),
        top_movers=movers[:TOP_MOVERS],
        grounded=grounded,
    )
