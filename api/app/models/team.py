from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class Team(db.Model):
    """السرب: وحدة التنافس الجماعي، ومالك عملة الوقود."""

    __tablename__ = "teams"
    # رمزا سرب متطابقان يجعلان اللصق ينسب صفوفًا إلى السرب الخطأ.
    __table_args__ = (UniqueConstraint("org_id", "code", name="uq_team_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)

    # أرشفة لا حذف: حذف السرب يتيّم أحداثه.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Membership(db.Model):
    """
    من في أي سرب، ومتى، وبأي دور.

    **فترة السريان ليست ترفًا:** بلا `left_at` ينقل المشرفُ طالبًا عنده ٤٠٠ ساعة،
    فيقفز سربه الجديد في الترتيب بتاريخ لم يصنعه.
    """

    __tablename__ = "memberships"
    __table_args__ = (
        # ث-٤: عضوية سارية واحدة لكل طالب. طالب في سربين يُحتسب مرّتين في معدّلين.
        Index(
            "uq_membership_active",
            "user_id",
            unique=True,
            postgresql_where=db.text("left_at IS NULL"),
        ),
        # أعضاء السرب الحاليون — مسار معدّل السرب في الصدارة.
        Index(
            "ix_membership_team_active",
            "team_id",
            postgresql_where=db.text("left_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)

    # 'pilot' | 'admin' — والمشرف صلاحيته على مستوى الجمعية لا السرب (AGENTS ٩).
    role: Mapped[str] = mapped_column(String, nullable=False, default="pilot")

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
