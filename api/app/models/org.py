from sqlalchemy import Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class Org(db.Model):
    """
    المنظمة: حاوية كل شيء، ومكان الإعدادات التي تختلف بين منظمة وأخرى.

    org_id يُحمَل في كل جدول **احتياطًا بلا عزل مستأجرين**: كلفته اليوم عمود،
    وإضافته لاحقًا هجرة مؤلمة على كل جدول.
    """

    __tablename__ = "orgs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    timezone: Mapped[str] = mapped_column(String, nullable=False, default="Asia/Riyadh")

    # بترقيم datetime.weekday: ٠ الاثنين … ٦ الأحد. فالأحد = ٦.
    week_starts_on: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=6)

    # قاعدة «أرضي» إعدادٌ لا رقمٌ في الكود (ف-٢): تغييرها صفّ لا نشر.
    grounded_after_days: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=14)

    tank_capacity_l: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
