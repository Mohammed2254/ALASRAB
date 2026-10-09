"""
محرّك القواعد — للساعات وحدها. **المكان الوحيد في المشروع الذي تُحسب فيه ساعة.**

الوقود لا يمرّ من هنا: لترات يشتقّها `services/fuel` من بنود موزونة تجمع ١٠٠٪،
ثم يُلحقها `ledger`. حسابٌ مختلف لعملة مختلفة، وخلطهما في محرّك واحد يجعل
الاثنين أصعب.

**هذا الملفّ لا يعرف Flask ولا المسارات ولا الخدمات، ولا يكتب في القاعدة ولا
ينفّذ commit.** يقرأ القواعد ويحسب. من يُلحق الحدث هو `services/ledger` وحده.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from ..extensions import db
from ..models import MasteryMultiplier, Weight, WeightVersion

# **دقّةُ الساعة — المالكُ الوحيد.** كانت ستّ نسخٍ متطابقة في `deck` و`fuel`
# و`reports` و`rules_admin` و`standings` وهنا. ومكانُها هذا الملفّ لأن
# `rules/` أدنى طبقة (تستورد من `models` وحدها) والخدماتُ تستورد منها أصلًا —
# فالاتّجاه سليم. ودقّةُ الساعة مفهومُ محرّكٍ لا مفهومُ خدمة.
CENT = Decimal("0.01")


@dataclass(frozen=True)
class Achievement:
    """
    الحدث المطبّع: ما يخرج من أي adapter، ولا يعرف شيئًا عن النقاط ولا الرتب.
    تغيير المصدر (إدخال يدوي، لصق إكسل، رفع ملف، API مستقبلي) لا يتجاوز هذا الشكل.
    """

    user_id: int
    occurred_at: datetime
    # نصّ مفتوح لا قائمة مغلقة (ADR-005): الوحدة نفسها غير محسومة حتى تصل عيّنة
    # راصد (س-١). 'memorize' بالصفحات و'quran_progress' بالنقطة المئوية كلاهما
    # يمرّ من هنا بلا تغيير حرف واحد — لأن المعادلة محايدة تجاه ما تعنيه الوحدة.
    activity_type: str
    quantity: Decimal  # صفحات · أو نقاط مئوية · أو ١ للسؤال اليومي
    mastery: str | None = None  # 'mastered' | 'accepted' | 'repeat'
    external_ref: str | None = None


@dataclass(frozen=True)
class RuleSet:
    """
    قواعد إصدار واحد، محمَّلة دفعة واحدة.

    وُجد لأن دفعة الإدخال تحتوي عشرات الإنجازات تشترك في لحظة الوقوع نفسها،
    فتحميل القواعد لكلٍّ منها على حدة ثلاثةُ استعلامات مضروبة في العدد — وهو
    N+1 في أكثر المسارات حساسية للزمن عندنا (شاشة الإدخال ومعيارها «أقلّ من
    دقيقة»). التحميل مرة واحدة يجعلها ثلاثة استعلامات مهما كبر السرب.
    """

    version_id: int
    weights: dict[str, Decimal]
    multipliers: dict[str, Decimal]

    def hours_for(self, achievement: Achievement) -> Decimal:
        weight = self.weights.get(achievement.activity_type)
        if weight is None:
            raise ValueError(
                f"لا وزن للنشاط «{achievement.activity_type}» في الإصدار {self.version_id}"
            )

        multiplier = Decimal("1")
        if achievement.mastery is not None:
            found = self.multipliers.get(achievement.mastery)
            if found is None:
                raise ValueError(
                    f"لا مضاعف للتقدير «{achievement.mastery}» في الإصدار {self.version_id}"
                )
            multiplier = found

        # التقريب مرة واحدة في النهاية، مطابقًا لـNUMERIC(8,2) في العمود.
        return (achievement.quantity * weight * multiplier).quantize(CENT)


def ruleset_at(org_id: int, moment: datetime) -> RuleSet:
    """
    قواعد اللحظة التي وقع فيها الإنجاز — لا القواعد الحالية.

    هذا السطر تحديدًا هو ما يمنع أن يغيّر تعديلُ وزنٍ اليومَ أرقامَ الماضي، فيستيقظ
    الطلاب على ترتيب لم يصنعوه.
    """
    version = db.session.scalar(
        select(WeightVersion)
        .where(WeightVersion.org_id == org_id, WeightVersion.effective_from <= moment)
        .order_by(WeightVersion.effective_from.desc())
        .limit(1)
    )
    if version is None:
        raise ValueError(
            f"لا إصدار أوزان سارٍ في {moment.isoformat()} — "
            "لا يجوز احتساب حدث بقاعدة لم تكن قائمة وقت وقوعه."
        )

    weights = dict(
        db.session.execute(
            select(Weight.activity_type, Weight.hours_per_unit).where(
                Weight.version_id == version.id
            )
        ).all()
    )
    multipliers = dict(
        db.session.execute(
            select(MasteryMultiplier.grade, MasteryMultiplier.multiplier).where(
                MasteryMultiplier.version_id == version.id
            )
        ).all()
    )
    return RuleSet(version_id=version.id, weights=weights, multipliers=multipliers)


def hours_for(org_id: int, achievement: Achievement) -> Decimal:
    """
    تحويل إنجاز واحد إلى ساعات.

    للاستدعاء المفرد. الدفعات تستعمل `ruleset_at` مرة ثم `RuleSet.hours_for` لكل
    عنصر، فلا تتكرّر ثلاثة استعلامات بعدد الإنجازات.
    """
    return ruleset_at(org_id, achievement.occurred_at).hours_for(achievement)
