"""
اللوحات والتشكيل — FR-050 · FR-051 · FR-052 · FR-053 (و-٩ب).

**قراءة خالصة، بلا `ledger` وبلا جدول جديد** — كل رقم مشتقّ من `point_events`
كبقية الوحدة (`reports.py`، `deck.py`)، ونمط استعلامها مأخوذ منهما حرفيًّا.

**نافذة الأسبوع الحالي** من `services/week.py` (`RULES.md` §٩.١أ — كانت
مكرَّرة هنا عمدًا قبل و-١٢) تخصّ `/boards/pilots` و`/boards/teams` وحدهما — نصّ ط-٧
الحرفي («نافذة الأسبوع من الأحد»). `/boards/formation` **تراكميّ** بقصد:
ط-٨ لا يذكر «الأسبوع»، والمشهد سرديّ لا دوريّ (`API.md` §٥).

**الجاهزية عبر `readiness.flight_states` المجمَّعة لا في حلقة** — عقد
`/boards/teams` يشترط صراحةً «استعلام واحد بلا N+1».
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Select, func, select

from ..extensions import db
from ..models import Membership, Org, PointEvent, Team, User
from . import readiness, week

CENT = Decimal("0.01")


def _hours_subquery(org_id: int, since: datetime | None, until: datetime | None = None) -> Select:
    """
    مجموع ساعات كل مستخدم — بنافذة إن مُرِّر `since`، أو تراكميًّا بلا شرط.

    و`until` **حدٌّ أعلى حصريّ** أُضيف في و-٢٠ لحساب ترتيب الأسبوع الماضي:
    بدونه كانت النافذة مفتوحةً إلى الأبد فتخلط الأسبوعين.
    """
    conditions = [PointEvent.org_id == org_id, PointEvent.scope == "individual"]
    if since is not None:
        conditions.append(PointEvent.occurred_at >= since)
    if until is not None:
        conditions.append(PointEvent.occurred_at < until)
    return (
        select(PointEvent.user_id, func.sum(PointEvent.delta).label("hours"))
        .where(*conditions)
        .group_by(PointEvent.user_id)
        .subquery()
    )


def _pilot_rows(org: Org, since: datetime, until: datetime | None) -> list:
    window = _hours_subquery(org.id, since, until)
    return db.session.execute(
        select(User.id, User.full_name, func.coalesce(window.c.hours, 0).label("hours"))
        .join(Membership, Membership.user_id == User.id)
        .outerjoin(window, window.c.user_id == User.id)
        .where(User.org_id == org.id, User.is_active.is_(True), Membership.left_at.is_(None))
        # فكّ تعادل بـ`id` — استقرار تقنيّ بحت، لا معيار FR-052 (يخصّ الأسراب وحدها).
        .order_by(func.coalesce(window.c.hours, 0).desc(), User.id)
    ).all()


def _ranks_of(ordered_keys: list) -> dict:
    """مفتاحٌ ⇒ موضعه (١ = الأعلى) — في ترتيبٍ جاهز."""
    return {key: position for position, key in enumerate(ordered_keys, start=1)}


def pilots_board(org: Org, now: datetime | None = None) -> list[dict]:
    """
    FR-050 — صدارة الأفراد بساعات الأسبوع الحالي، تنازليًّا.

    **و`chg` تغيّرُ الموضع عن الأسبوع الماضي** (و-٢٠): موجبٌ صعود، وسالبٌ
    هبوط، وصفرٌ ثبات. ويُحسب **بإعادة الترتيب على نافذة الأسبوع الماضي** لا
    بلقطةٍ مخزَّنة — فلا جدولَ يتباعد عن الدفتر، ولا هجرةَ، والدفترُ هو
    المصدر الوحيد دائمًا.
    """
    now = now or datetime.now(UTC)
    since = week.week_start_utc(org, now)
    previous_since = since - timedelta(days=7)

    rows = _pilot_rows(org, since, None)
    before = _ranks_of([uid for uid, _n, _h in _pilot_rows(org, previous_since, since)])
    current = _ranks_of([uid for uid, _n, _h in rows])

    return [
        {
            "full_name": full_name,
            "hours": Decimal(hours).quantize(CENT),
            "chg": before[uid] - current[uid] if uid in before else 0,
        }
        for uid, full_name, hours in rows
    ]


def teams_board(org: Org, now: datetime | None = None) -> list[dict]:
    """
    FR-051/FR-052 — صدارة الأسراب بالمعدّل، فكّ التعادل بـ`code` تصاعديًّا.

    **و`chg` تغيّرُ الموضع عن الأسبوع الماضي** (و-٢٠) — بإعادة ترتيبٍ على
    نافذةٍ سابقة لا بلقطةٍ مخزَّنة، كما في صدارة الأفراد.
    """
    now = now or datetime.now(UTC)
    since = week.week_start_utc(org, now)
    board = _teams_board_window(org, since, None, now)
    before = _ranks_of(
        [t["id"] for t in _teams_board_window(org, since - timedelta(days=7), since, now)]
    )
    current = _ranks_of([t["id"] for t in board])
    for row in board:
        row["chg"] = before[row["id"]] - current[row["id"]] if row["id"] in before else 0
    return board


def _teams_board_window(
    org: Org, since: datetime, until: datetime | None, now: datetime
) -> list[dict]:
    window = _hours_subquery(org.id, since, until)
    rows = db.session.execute(
        select(
            Team.id,
            Team.name,
            Team.code,
            User.id.label("uid"),
            func.coalesce(window.c.hours, 0).label("hours"),
        )
        .join(Membership, Membership.team_id == Team.id)
        .join(User, User.id == Membership.user_id)
        .outerjoin(window, window.c.user_id == User.id)
        .where(
            Team.org_id == org.id,
            Team.archived_at.is_(None),
            Membership.left_at.is_(None),
            User.is_active.is_(True),
        )
    ).all()

    by_team: dict[int, dict] = {}
    member_ids: dict[int, list[int]] = {}
    for team_id, name, code, uid, hours in rows:
        t = by_team.setdefault(
            team_id, {"id": team_id, "name": name, "code": code, "total": Decimal(0), "members": 0}
        )
        t["total"] += Decimal(hours)
        t["members"] += 1
        member_ids.setdefault(team_id, []).append(uid)

    all_uids = [uid for ids in member_ids.values() for uid in ids]
    flights = readiness.flight_states(org, all_uids, now)

    board = []
    for team_id, t in by_team.items():
        flying = sum(1 for uid in member_ids[team_id] if not flights[uid].grounded)
        board.append(
            {
                "id": team_id,
                "team": t["name"],
                "code": t["code"],
                "avg_hours": (t["total"] / t["members"]).quantize(CENT),
                "members": t["members"],
                "readiness": {"flying": flying, "grounded": t["members"] - flying},
            }
        )
    board.sort(key=lambda r: (-r["avg_hours"], r["code"]))
    return board


def team_rank(org: Org, team_id: int, now: datetime | None = None) -> int | None:
    """موضع السرب (١ = الأعلى) في نفس ترتيب `teams_board` — لـ`GET /me/deck`."""
    board = teams_board(org, now)
    for position, row in enumerate(board, start=1):
        if row["id"] == team_id:
            return position
    return None


@dataclass(frozen=True)
class _Aircraft:
    user_id: int
    full_name: str
    hours: Decimal


def _team_aircraft(org: Org, team_id: int) -> list[_Aircraft]:
    window = _hours_subquery(org.id, None)
    rows = db.session.execute(
        select(User.id, User.full_name, func.coalesce(window.c.hours, 0).label("hours"))
        .join(Membership, Membership.user_id == User.id)
        .outerjoin(window, window.c.user_id == User.id)
        .where(
            Membership.team_id == team_id,
            Membership.left_at.is_(None),
            User.org_id == org.id,
            User.is_active.is_(True),
        )
    ).all()
    return [_Aircraft(uid, name, Decimal(hours).quantize(CENT)) for uid, name, hours in rows]


def _general_aircraft(org: Org) -> list[_Aircraft]:
    window = _hours_subquery(org.id, None)
    rows = db.session.execute(
        select(User.id, User.full_name, func.coalesce(window.c.hours, 0).label("hours"))
        .join(Membership, Membership.user_id == User.id)
        .outerjoin(window, window.c.user_id == User.id)
        .where(User.org_id == org.id, User.is_active.is_(True), Membership.left_at.is_(None))
    ).all()
    return [_Aircraft(uid, name, Decimal(hours).quantize(CENT)) for uid, name, hours in rows]


def formation(org: Org, user_id: int, scope: str, now: datetime | None = None) -> dict:
    """
    FR-053 — محكوم بف-١: `team` أسماء كاملة شاملة الساقطين، `general` بلا
    اسم للساقط («إنجاز فقط»). الحجم تراكميّ (توثيق الوحدة أعلاه).
    """
    if scope == "team":
        membership = db.session.scalar(
            select(Membership).where(Membership.user_id == user_id, Membership.left_at.is_(None))
        )
        # بلا عضوية سارية: لا معنى لـ«سربي» — مشهدٌ فارغ لا خطأ (نمط `team: null`).
        aircraft = _team_aircraft(org, membership.team_id) if membership else []
    else:
        aircraft = _general_aircraft(org)

    flights = readiness.flight_states(org, [a.user_id for a in aircraft], now)
    # نسبة مئوية جاهزة للعرض مباشرةً — لا حساب في الواجهة (`check-no-domain-logic.mjs`
    # يمنعه، ونمط `next_rank.progress_pct` في `GET /me/deck` نفسه هنا).
    max_hours = max((a.hours for a in aircraft), default=Decimal(0))
    return {
        "scope": scope,
        "aircraft": [
            {
                "name": a.full_name if scope == "team" or not flights[a.user_id].grounded else None,
                "size": a.hours,
                "size_pct": round(float(a.hours / max_hours) * 100) if max_hours > 0 else 0,
                "grounded": flights[a.user_id].grounded,
            }
            for a in aircraft
        ],
    }
