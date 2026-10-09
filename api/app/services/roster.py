"""
سجلّ الطلاب — إنشاء وتعطيل وتغيير دور (و-٢١).

**سبب وجوده:** `SCOPE.md` فيه `FR-004` (إعادة تعيين رمز) و`FR-083` (إدارة
الأسراب والعضويات)، **ولا بند لإنشاء طالب**. فُرض أن الطلاب موجودون سلفًا،
وكان الكاتب الوحيد لـ`User` في المشروع كلّه هو `seed.py` — وهو يرفض الإنتاج.

ثلاثة قرارات صريحة:

**(١) الرمز يُولَّد ولا يُكتَب.** مشرفٌ يملأ مئتَي رمز بيده سيكتب `1234`
للجميع، وهو بعينه ما يُسقط `NFR-03`. والمولِّد واحد مشترك مع إعادة التعيين
(`auth.generate_pin`) — فلا مولِّد ثانٍ أضعف.

**(٢) تعطيل لا حذف.** حذف الطالب يتيّم أحداثه في الدفتر (ADR-004)، و`is_active`
مُرشَّح **في كل مسار قراءة** بلا استثناء (الصدارة · التقارير · التشكيل ·
المطابقة · الدخول) — فالعلم وحده يكفي، والعضوية تبقى تاريخًا لا تُغلَق.

**(٣) الدور على العضوية لا على المستخدم** — فتغييره تعديل صفّ العضوية السارية،
وصلاحية المشرف على مستوى الجمعية لا السرب (`AGENTS.md` ٩).

@implements FR-095, FR-096
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Membership, Team, User
from . import audit
from .auth import generate_pin, hash_pin, revoke_all_sessions
from .errors import ServiceError

ROLES = ("pilot", "admin")

# حدٌّ للّصق الجماعيّ: ٢٠٠ طالبًا هو المدى المصرَّح به للمنصّة، والمئتان
# الباقية هامش. سقفٌ موجود أفضل من طلبٍ يُسقط العامل بصمت.
BULK_MAX_ROWS = 400


class RosterError(ServiceError):
    """خطأ نطاق roster — الاسمُ يبقى لأن المسارات تُلقّط به (`services/errors.py`)."""


def roster(org_id: int) -> list[dict]:
    """
    كل الطلاب — **بما فيهم المعطَّلون**، مُعلَّمين لا مخفيّين: مشرفٌ لا يرى
    المعطَّل لا يستطيع إعادة تفعيله، فيُعيد إنشاءه برقمٍ آخر ويتشظّى تاريخه.

    اسم السرب والدور بوصلٍ واحد لا N+1 — القائمة تُقرَأ جملةً في شاشةٍ تُفتح
    كثيرًا. و`outerjoin` لا `join`: طالبٌ أُغلقت عضويته (نقلٌ قديم) يجب أن
    يظهر بلا سرب، لا أن يختفي من السجلّ.
    """
    rows = db.session.execute(
        select(User, Membership.role, Team.name)
        .outerjoin(Membership, (Membership.user_id == User.id) & (Membership.left_at.is_(None)))
        .outerjoin(Team, Team.id == Membership.team_id)
        .where(User.org_id == org_id)
        .order_by(User.is_active.desc(), User.full_name)
    ).all()
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "student_no": user.student_no,
            "role": role or "pilot",
            "team_name": team_name,
            "is_active": user.is_active,
        }
        for user, role, team_name in rows
    ]


def _active_team(org_id: int, team_id: int) -> Team:
    team = db.session.get(Team, team_id)
    if team is None or team.org_id != org_id:
        raise RosterError("لا سرب بهذا المعرّف.", status=404)
    if team.archived_at is not None:
        raise RosterError("لا عضوية جديدة في سرب مؤرشَف.")
    return team


def _target(org_id: int, user_id: int) -> User:
    user = db.session.get(User, user_id)
    if user is None or user.org_id != org_id:
        raise RosterError("لا طالب بهذا المعرّف.", status=404)
    return user


def _add_student(org_id: int, full_name: str, student_no: str, team: Team) -> tuple[User, str]:
    """
    الإنشاء الذرّي بلا `commit` — فالإفراديّ والجماعيّ **نفس الكتابة** لا
    نسختان تفترقان (درس `_plan_rows` في و-٢٠).

    و`savepoint` حول الإدراج: رقمٌ مكرَّر في السطر الخمسين من لصقةٍ يجب أن
    يُبلَّغ عنه وحده، لا أن يُسقط المعاملة كلّها ومعها التسعة والأربعون.
    """
    name = full_name.strip()
    number = student_no.strip()
    if not name:
        raise RosterError("اسم الطالب مطلوب.")
    if not number:
        raise RosterError("رقم الطالب مطلوب.")

    pin = generate_pin()
    user = User(org_id=org_id, full_name=name, student_no=number, pin_hash=hash_pin(pin))
    try:
        with db.session.begin_nested():
            db.session.add(user)
            db.session.flush()
    except IntegrityError as exc:
        raise RosterError(f"رقم الطالب {number} مستعمل أصلًا.", status=409) from exc

    db.session.add(Membership(org_id=org_id, user_id=user.id, team_id=team.id, role="pilot"))
    return user, pin


def create_student(org, full_name: str, student_no: str, team_id: int, actor_id: int) -> dict:
    """
    طالبٌ واحد. الرمز يُعاد **نصًّا مرّةً واحدة** ولا يُخزَّن (عقد `reset_pin`).

    وسطر التدقيق **بلا الرمز** صراحةً — سطرٌ يحمله يحوّل السجلّ نفسه إلى
    تسريب (§٧.٥).
    """
    team = _active_team(org.id, team_id)
    user, pin = _add_student(org.id, full_name, student_no, team)
    audit.record(
        org_id=org.id,
        kind="user_created",
        summary=f"طالب جديد: {user.full_name} ({user.student_no}) في سرب {team.name}",
        actor_id=actor_id,
        after={"user_id": user.id, "team_id": team.id},
    )
    db.session.commit()
    return {"id": user.id, "full_name": user.full_name, "student_no": user.student_no, "pin": pin}


def create_students_bulk(org, rows: list[dict], team_id: int, actor_id: int) -> dict:
    """
    لصقةٌ واحدة لمئتَي طالب — **لأن الإفراديّ وحده شاشةٌ لا تُستعمل**.

    **السطر الفاشل يُبلَّغ ولا يُسقط الناجح**: لصقةٌ تُرفض كلّها لأن رقمًا
    واحدًا مكرَّر تُجبر المشرف على تفتيشها بعينه — وهو ما يدفعه إلى تركها
    (خ-١). نفس سابقة استيراد راصد: التكرار يُستبعَد ولا تُرفض الدفعة.
    """
    if not rows:
        raise RosterError("لا صفوف في اللصقة.")
    if len(rows) > BULK_MAX_ROWS:
        raise RosterError(f"اللصقة أكثر من {BULK_MAX_ROWS} صفًّا — قسّمها.")

    team = _active_team(org.id, team_id)
    created, failed = [], []
    for index, row in enumerate(rows, start=1):
        try:
            user, pin = _add_student(
                org.id, row.get("full_name", ""), row.get("student_no", ""), team
            )
        except RosterError as exc:
            failed.append({"line": index, "message": str(exc)})
            continue
        created.append(
            {
                "id": user.id,
                "full_name": user.full_name,
                "student_no": user.student_no,
                "pin": pin,
            }
        )

    if created:
        audit.record(
            org_id=org.id,
            kind="users_imported",
            summary=f"إضافة {len(created)} طالبًا إلى سرب {team.name}",
            actor_id=actor_id,
            after={"team_id": team.id, "created": len(created), "failed": len(failed)},
        )
    db.session.commit()
    return {"created": created, "failed": failed}


def set_role(org, user_id: int, role: str, actor_id: int) -> dict:
    """
    ترقيةٌ أو تنزيل — **على العضوية السارية**.

    **ولا يُنزَّل آخر مشرف:** جمعيةٌ بلا مشرف لا يفتحها أحد، ولا مسار في
    المنصّة يُعيد إنشاء واحد (التأسيس يعمل على قاعدةٍ فارغة وحدها). فهذا
    الفحص ليس تهذيبًا بل الحائل الوحيد بين خطأٍ وقفلٍ دائم.
    """
    if role not in ROLES:
        raise RosterError("دورٌ غير معروف.")
    user = _target(org.id, user_id)
    membership = db.session.scalar(
        select(Membership).where(Membership.user_id == user.id, Membership.left_at.is_(None))
    )
    if membership is None:
        raise RosterError("لا عضوية سارية لهذا الطالب — انقله إلى سرب أوّلًا.")
    if membership.role == role:
        return {"id": user.id, "role": role}

    if membership.role == "admin" and _other_admins(org.id, user.id) == 0:
        raise RosterError("هذا آخر مشرف في الجمعية — عيِّن مشرفًا آخر قبل تنزيله.")

    before = membership.role
    membership.role = role
    audit.record(
        org_id=org.id,
        kind="role_changed",
        summary=f"دور {user.full_name}: {before} ⇒ {role}",
        actor_id=actor_id,
        before={"role": before},
        after={"user_id": user.id, "role": role},
    )
    db.session.commit()
    return {"id": user.id, "role": role}


def _other_admins(org_id: int, except_user_id: int) -> int:
    return db.session.scalar(
        select(func.count(Membership.id))
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.org_id == org_id,
            Membership.left_at.is_(None),
            Membership.role == "admin",
            Membership.user_id != except_user_id,
            User.is_active.is_(True),
        )
    )


def set_active(org, user_id: int, active: bool, actor_id: int) -> dict:
    """
    تعطيلٌ أو إعادة تفعيل — **علمٌ واحد، والعضوية تبقى تاريخًا**.

    `is_active` مُرشَّح في كل مسار قراءة وفي الدخول نفسه، فالعلم يُخرج الطالب
    من الصدارة والتقارير والتشكيل والمطابقة فورًا. وإغلاق العضوية معه كان
    يجعل إعادة التفعيل تحتاج سربًا من جديد بلا سبب.

    والتعطيل **يُبطل الجلسات**: علمٌ يمنع الدخول الجديد ولا يُخرج كوكيًّا
    حيًّا عمره تسعون يومًا ليس تعطيلًا.
    """
    user = _target(org.id, user_id)
    if user.is_active == active:
        return {"id": user.id, "is_active": active}

    if not active and _is_last_admin(org.id, user.id):
        raise RosterError("هذا آخر مشرف في الجمعية — عيِّن مشرفًا آخر قبل تعطيله.")

    user.is_active = active
    if not active:
        revoke_all_sessions(user.id)
    verb = "إعادة تفعيل" if active else "تعطيل"
    audit.record(
        org_id=org.id,
        kind="user_reactivated" if active else "user_deactivated",
        summary=f"{verb} {user.full_name} ({user.student_no})",
        actor_id=actor_id,
        after={"user_id": user.id, "is_active": active},
    )
    db.session.commit()
    return {"id": user.id, "is_active": active}


def _is_last_admin(org_id: int, user_id: int) -> bool:
    membership = db.session.scalar(
        select(Membership).where(Membership.user_id == user_id, Membership.left_at.is_(None))
    )
    if membership is None or membership.role != "admin":
        return False
    return _other_admins(org_id, user_id) == 0
