"""
أسبوع المنظّمة — المالك الوحيد (`RULES.md` §٩.١أ).

نافذة المنافسة الاجتماعية: تبدأ يوم `orgs.week_starts_on` بتوقيت
`orgs.timezone`، ويراها الطالب في الصدارة وطيار الأسبوع وتقرير التحضير
والحضور — ولاحقًا في أسابيع الوقود ولوحة القيادة.

**لماذا مالكٌ واحد بعد أن كانت الصيغة مكرَّرة عمدًا؟** كانت أربع نسخ حرفية
(`standings` · `entry` · `engagement` · `reading`)، ونسختان منها توثّقان التكرار
بأنه مقصود «لا مُجرَّد». والسبب الذي نقض القصد ليس كراهية التكرار — بل أن هذه
الصيغة **تحمل معامل سياسة** (`week_starts_on`) تقرؤه من صفٍّ قابل للتغيير، فهي
ليست ثابتًا رياضيًّا. ونسخةٌ خامسة وسادسة كانتا قادمتين (و-١٥ · و-١٦). والفارق
لو وقع لا يظهر عطلًا بل **رقمين مختلفين لنفس الكلمة على شاشتين** — وهو أسوأ من
العطل لأن أحدًا لا يلاحظه، والثقة في الأرقام هي المنتج كلّه.

**ولا تُضاف هنا نافذة التقرير المتدحرجة** (`آخر N يومًا`): مالكها
`reports.py` وهي نوعٌ آخر بقصد، لا نسخةٌ ناقصة من هذه (`RULES.md` §٩.١ب).
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..models import Org


def week_start_local(org: Org, now: datetime) -> date:
    """
    بداية الأسبوع الحالي **كتاريخ بتوقيت المنظمة**.

    لمن يقارن بعمود `DATE` (`pilot_of_week.week_start` · نافذة التحضير ·
    مفتاح `external_ref` للحضور) — فالتاريخ هو ما يُخزَّن هناك لا اللحظة.
    """
    local_now = now.astimezone(ZoneInfo(org.timezone))
    days_since_start = (local_now.weekday() - org.week_starts_on) % 7
    return local_now.date() - timedelta(days=days_since_start)


def week_start_utc(org: Org, now: datetime) -> datetime:
    """
    بداية الأسبوع الحالي **كلحظة بـUTC**.

    لمن يقارن بـ`point_events.occurred_at` (الصدارة) — والتحويل نفسه الذي
    يحكمه `RULES.md` §٩: بداية اليوم المحليّ ثم إلى UTC، لا منتصف ليل UTC.
    """
    local_start = week_start_local(org, now)
    return datetime.combine(local_start, time.min, tzinfo=ZoneInfo(org.timezone)).astimezone(UTC)
