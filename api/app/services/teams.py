"""
الأسراب والعضويات — و-٧ · FR-083.

**أرشفة لا حذف، ونقلٌ لا يزوّر التاريخ** (م-١٠): حذف سرب يتيّم أحداثه، ونقلُ
طالبٍ بلا `left_at` يقفز سربه الجديد في الترتيب بتاريخ لم يصنعه.

@implements FR-083
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Membership, Team, User
from . import audit


class TeamsError(Exception):
    """خطأ عملٍ يُترجَم إلى رمز حالة في المسار — لا يعرف HTTP (نمط `ReadingError`)."""

    def __init__(self, message: str, status: int = 422):
        self.status = status
        super().__init__(message)


def list_teams(org_id: int) -> list[dict]:
    """كل الأسراب — **بما فيها المؤرشَفة**، مُعلَّمة لا مخفيّة."""
    active_counts = dict(
        db.session.execute(
            select(Membership.team_id, func.count(Membership.id))
            .where(Membership.org_id == org_id, Membership.left_at.is_(None))
            .group_by(Membership.team_id)
        ).all()
    )
    teams = db.session.scalars(select(Team).where(Team.org_id == org_id).order_by(Team.id)).all()

    # أعضاء كل سرب — استعلامٌ واحد لكل الأسراب لا واحدٌ لكل سربٍ (N+1 في
    # شاشةٍ يفتحها المشرف كثيرًا). النموذج المعتمد يعرض الأعضاء لا عددهم
    # فقط: «٩ عضو» بلا أسماءٍ لا يُدار به سرب.
    roster: dict[int, list[dict]] = {}
    rows = db.session.execute(
        select(Membership.team_id, User.id, User.full_name, User.student_no)
        .join(User, User.id == Membership.user_id)
        .where(Membership.org_id == org_id, Membership.left_at.is_(None))
        .order_by(Membership.team_id, User.full_name)
    ).all()
    for team_id, user_id, full_name, student_no in rows:
        roster.setdefault(team_id, []).append(
            {"user_id": user_id, "full_name": full_name, "student_no": student_no}
        )

    return [
        {
            "id": t.id,
            "name": t.name,
            "code": t.code,
            "archived_at": t.archived_at,
            "active_members": active_counts.get(t.id, 0),
            "members": roster.get(t.id, []),
        }
        for t in teams
    ]


def create_team(org, name: str, code: str, actor_id: int) -> Team:
    team = Team(org_id=org.id, name=name.strip(), code=code.strip())
    db.session.add(team)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise TeamsError("رمز السرب مستعمَل في هذه المنظمة.", status=409) from exc

    audit.record(
        org_id=org.id,
        kind="team_created",
        summary=f"سربٌ جديد: {team.name} ({team.code})",
        actor_id=actor_id,
        after={"team_id": team.id, "name": team.name, "code": team.code},
    )
    db.session.commit()
    return team


def _get_team(org_id: int, team_id: int) -> Team:
    team = db.session.get(Team, team_id)
    if team is None or team.org_id != org_id:
        raise TeamsError("لا سرب بهذا المعرّف.", status=404)
    return team


def archive_team(org, team_id: int, actor_id: int) -> Team:
    team = _get_team(org.id, team_id)
    if team.archived_at is not None:
        raise TeamsError("السرب مؤرشَف أصلًا.")

    active = db.session.scalar(
        select(func.count(Membership.id)).where(
            Membership.team_id == team.id, Membership.left_at.is_(None)
        )
    )
    if active:
        # أرشفةٌ تترك طلّابًا بلا سرب حيّ تكسر بطاقتهم وصدارة الأسراب معًا.
        raise TeamsError("للسرب أعضاء ساريّون — انقلهم إلى سرب آخر أوّلًا.")

    team.archived_at = datetime.now(UTC)
    audit.record(
        org_id=org.id,
        kind="team_archived",
        summary=f"أُرشِف السرب: {team.name}",
        actor_id=actor_id,
        after={"team_id": team.id},
    )
    db.session.commit()
    return team


def transfer_member(org, team_id: int, user_id: int, actor_id: int) -> Membership:
    """
    **العضوية القديمة تُغلَق لا تُحذَف، والجديدة تُفتح** — نقلٌ لا يزوّر التاريخ:
    أحداث الطالب في `point_events` تبقى منسوبة كما وقعت، بلا أثر لمكان وجوده
    الآن على ما فعله في الماضي.
    """
    team = _get_team(org.id, team_id)
    if team.archived_at is not None:
        raise TeamsError("لا عضوية جديدة في سرب مؤرشَف.")

    user = db.session.get(User, user_id)
    if user is None or user.org_id != org.id:
        raise TeamsError("لا طالب بهذا المعرّف.", status=404)

    current = db.session.scalar(
        select(Membership).where(Membership.user_id == user.id, Membership.left_at.is_(None))
    )
    role = current.role if current is not None else "pilot"
    if current is not None:
        current.left_at = datetime.now(UTC)

    membership = Membership(org_id=org.id, user_id=user.id, team_id=team.id, role=role)
    db.session.add(membership)
    db.session.flush()

    audit.record(
        org_id=org.id,
        kind="membership_transferred",
        summary=f"نُقل {user.full_name} إلى سرب {team.name}",
        actor_id=actor_id,
        before={"team_id": current.team_id} if current is not None else None,
        after={"team_id": team.id},
    )
    db.session.commit()
    return membership
