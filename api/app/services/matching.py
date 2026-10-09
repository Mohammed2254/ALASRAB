"""
مطابقة أسماء راصد بطلاب المنظّمة — `RULES.md` §٧.

**القاعدة: تُعرَض البدائل ولا يُختار تلقائيًّا.** المطابقة القريبة في بيانات
الدرجات تُنسَب ساعات لطالب خطأ، ولا يكتشفها أحد — فلا مطابقة تقريبية هنا
إطلاقًا، Trim فقط ثم تطابق تامّ.

**تطابق متعدّد (طالبان بنفس الاسم بعد القصّ) يُعامَل كعدم تطابق** — امتدادٌ
من Recon و-٥ (`docs/archive/slices/و-٥.md` §٢، قرار #٦): لا مستند سابق يحسم هذه
الحالة صراحةً، لكن اختيار أحدهما صمتًا هو بالضبط ما يمنعه مبدأ «لا تخمين».
"""

from dataclasses import dataclass, field

from sqlalchemy import select

from ..extensions import db
from ..models import Membership, User
from . import membership


@dataclass(frozen=True)
class Match:
    status: str  # 'matched' | 'ambiguous' | 'unmatched'
    user_id: int | None = None
    candidate_ids: list[int] = field(default_factory=list)


def match_names(org_id: int, names: list[str]) -> dict[str, Match]:
    """
    اسمٌ واحد ⇒ نتيجة مطابقة واحدة. **قراءة فقط** — لا كتابة هنا إطلاقًا.

    المطابقة على طلاب المنظّمة **النشِطين بعضوية سارية** وحدهم — نفس فلترة
    `services/quran.roster`/`services/entry._roster`، مكرَّرة عمدًا لا
    مستوردة (نمط `_local_start_of_day_utc` القائم في أربع خدمات أخرى).
    """
    roster = db.session.execute(
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(
            *membership.active_roster_clauses(org_id),
        )
    ).scalars()

    by_name: dict[str, list[int]] = {}
    for u in roster:
        by_name.setdefault(u.full_name.strip(), []).append(u.id)

    results: dict[str, Match] = {}
    for name in names:
        candidates = by_name.get(name.strip(), [])
        if len(candidates) == 1:
            results[name] = Match(status="matched", user_id=candidates[0])
        elif len(candidates) > 1:
            results[name] = Match(status="ambiguous", candidate_ids=candidates)
        else:
            results[name] = Match(status="unmatched")
    return results
