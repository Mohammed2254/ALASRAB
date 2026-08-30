from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class WeightVersion(db.Model):
    """
    إصدار أوزان بتاريخ سريان.

    وجوده هو ما يمنع أن يغيّر تعديلُ وزنٍ اليومَ أرقامَ الماضي، فيستيقظ الطلاب على
    ترتيب لم يصنعوه — بلا أن يفعل أحدٌ شيئًا خاطئًا.
    """

    __tablename__ = "weight_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(String, nullable=True)


class Weight(db.Model):
    """
    قيمة النشاط الواحد بالساعات داخل إصدار.

    `activity_type` نصّ مفتوح — **قرار لا كسل** (ADR-005): «حفظ» و«مراجعة»
    و«حضور» و«نسبة إنجاز» كلّها صفوف لا كود. فحين تصل عيّنة راصد ويتبيّن أنها
    تعطي نسبة لا صفحات، التغيير صفٌّ في جدول لا هجرة.
    """

    __tablename__ = "weights"
    __table_args__ = (UniqueConstraint("version_id", "activity_type", name="uq_weight_activity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("weight_versions.id"), nullable=False)
    activity_type: Mapped[str] = mapped_column(String, nullable=False)
    hours_per_unit: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)


class MasteryMultiplier(db.Model):
    """
    مضاعف التقدير داخل إصدار.

    **مفصول عن `weights`** لأنه يضرب أنشطة عدّة لا نشاطًا واحدًا؛ ودمجهما يعني
    تكرار المضاعف في كل صفّ نشاط، ثم افتراقها عند أوّل تعديل.
    """

    __tablename__ = "mastery_multipliers"
    __table_args__ = (UniqueConstraint("version_id", "grade", name="uq_mastery_grade"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("weight_versions.id"), nullable=False)
    grade: Mapped[str] = mapped_column(String, nullable=False)
    multiplier: Mapped[Decimal] = mapped_column(Numeric(5, 3), nullable=False)


class RankThreshold(db.Model):
    """
    عتبات الرتب. **صفوف لا أرقام في الكود:** السُّلّم أربع رتب اليوم وسيزيد،
    وإضافة رتبة شاشة إعدادات لا هجرة قاعدة بيانات.
    """

    __tablename__ = "rank_thresholds"
    __table_args__ = (
        UniqueConstraint("org_id", "key", name="uq_rank_key"),
        UniqueConstraint("org_id", "tier", name="uq_rank_tier"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    at_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
