"""
جمعُ الساعات من الدفتر — **المالكُ الوحيد للصيغة**.

نفسُ سابقة `services/week.py`: صيغةٌ **تحمل سياسةً** لا ثابتًا رياضيًّا،
فلها مالكٌ واحد.

كانت نسختان: `reports._window_hours(org_id, since)` و
`standings._hours_subquery(org_id, since, until=None)` — والثانيةُ مجموعةٌ
عليا من الأولى تمامًا. وتَبِعاتُ افتراقهما ليست عطلًا بل **رقمَين مختلفَين
لنفس الكلمة على شاشتين**: «ساعاتي» في التقرير و«ساعاتي» في الصدارة.

**والسياسةُ المحمولة هنا شقّان:**

١. `scope == "individual"` — الوقودُ جماعيّ ولا يُجمَع مع الساعات الفردية
   أبدًا (الثابتُ المعلَن: «الساعات فردية والوقود جماعيّ ولا يلتقيان»).
   فنطاقٌ ثالثٌ يُضاف يومًا يجب أن يُقرَّر مكانُه **هنا مرّةً** لا في موضعين.
٢. `sum(delta)` لا رصيدٌ مخزَّن — ADR-001: عمودُ رصيدٍ يفترق عن مصدره في
   أوّل مسارٍ ينسى تحديثه.

**ويُستورَد باسم `hours_query`** في `standings` و`reports`: الاسمُ `hours`
متغيّرُ حلقةٍ في كليهما، و`ruff` كشف الأمرَ بـ`F823` — «مرجعٌ قبل الإسناد»،
وهو خطرُ عطلٍ لا تحذيرُ أسلوب.

**ولا `commit` ولا كتابة:** هذا بانيُ استعلامٍ محض. والكتابةُ في الدفتر
يملكها `services/ledger.py` وحده، وفصلُ القراءة عنها مقصود.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.sql import Subquery

from ..models import PointEvent


def sum_by_user(
    org_id: int, since: datetime | None = None, until: datetime | None = None
) -> Subquery:
    """
    مجموعُ ساعات كل طالب — **بنافذة إن مُرِّر `since`، وتراكميًّا بلا شرط**.

    فالتراكميُّ («رصيدي») والحركةُ («من تقدّم هذا الأسبوع») سؤالان مختلفان
    بنفس الصيغة، لا صيغتان.

    **والنوعُ `Subquery` لا `Select`:** كان `standings._hours_subquery` يُعلن
    `-> Select` وهو خطأ — `.subquery()` تُرجع `Subquery`، والمستهلكون يقرؤون
    `window.c.hours` وهو ما لا يملكه `Select`. تعليقٌ نوعيٌّ كاذب لا يُسقط
    `ruff` لكنه يُضلّل من يقرأ.

    و`until` **حدٌّ أعلى حصريّ**: بدونه تبقى نافذةُ «الأسبوع الماضي» مفتوحةً
    إلى الأبد فتخلط الأسبوعين (أُضيف في و-٢٠ لحساب تغيّر الترتيب).
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
