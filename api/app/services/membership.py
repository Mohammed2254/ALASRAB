"""
**مالكُ تعريف «عضوٌ نشط»** — `left_at IS NULL`.

وُجد في و-٢٢ لأن التعريفَ كان مكتوبًا **ثلاثًا وعشرين مرّة** في أحدَ عشرَ
ملفًّا، بشكلين متكرّرين حرفيًّا:

· **كشفُ جمعيةٍ نشط** (ثماني نسخ متطابقة): `User.org_id == X` و
  `User.is_active` و`Membership.left_at IS NULL` — في `entry` و`matching`
  و`quran` و`reading` و`reports` و`rules_admin` و`standings` (مرّتين).
· **عضويّةُ مستخدمٍ الحالية** (ستُّ نسخ): `select(Membership).where(user_id,
  left_at IS NULL)` — في `auth` و`roster` (مرّتين) و`standings` و`teams`
  و`deck` (بوصلةٍ إلى `Team`).

**ولماذا هذا تكرارٌ خطر لا مجرّد ضجيج:** الشرطُ الناقص **لا يُفشل استعلامًا**،
بل يُرجع صفًّا زائدًا — طالبٌ ترك السرب يظهر في الترتيب ويُحسب في المتوسّط
وتُطلب له ساعات. فنسخةٌ تُكتب غدًا وتنسى `left_at` تُنتج **رقمًا خاطئًا
صامتًا** لا خطأً صاخبًا. وهذا بعينه مبدأُ `week.py` و`hours.py`: ما يحمل
سياسةً له مالكٌ واحد.

**ولا يُلمَس** ما شُرِط بغير هذين الشكلين: `standings.py:112` (ترتيبُ أسراب —
يزيد `Team.archived_at`) و`:171` (سربٌ بعينه) و`roster.py:223` (المشرفون
وحدهم) و`teams.py` (عدٌّ لكل سرب) — شروطُها تختلف بما هو **جوهرٌ لا صياغة**،
وتوحيدُها يُخفي الفرق.
"""

from sqlalchemy import select
from sqlalchemy.sql.elements import ColumnElement

from ..extensions import db
from ..models import Membership, User


def active_roster_clauses(org_id: int) -> tuple[ColumnElement[bool], ...]:
    """
    شرطُ «طالبٌ نشطٌ في هذه الجمعية» — يُفكّ بـ`*` في `.where()`.

    والوصلُ يبقى على المستدعي (`join(Membership, Membership.user_id ==
    User.id)`): **الأعمدةُ المُسقَطة تختلف** بين المستدعين، فالمشترَكُ هو
    الشرطُ وحده لا الاستعلام. وبانٍ يُعيد استعلامًا كاملًا كان سيُجبرهم على
    التفافٍ أسوأ من التكرار.
    """
    return (
        User.org_id == org_id,
        User.is_active.is_(True),
        Membership.left_at.is_(None),
    )


def current(user_id: int) -> Membership | None:
    """
    عضويّةُ المستخدم الحالية، أو `None` لمن لا سربَ له.

    **و`None` حالةٌ مشروعة لا عطل:** طالبٌ أُنشئ ولم يُسنَد إلى سربٍ بعد
    (`roster.create_student` تسمح بذلك)، فالمستدعي يُقرّر ما يفعل.
    """
    return db.session.scalar(
        select(Membership).where(Membership.user_id == user_id, Membership.left_at.is_(None))
    )
