"""
المصادقة: رقم الطالب + رمز من أربعة أرقام، وجلسة في قاعدة البيانات.
"""

import hashlib
import secrets
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import func, select, update

from ..extensions import db
from ..models import LoginAttempt, Membership, Org, Session, User
from . import audit

SESSION_DAYS = 90
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

_hasher = PasswordHasher()

# هاش ثابت لرمزٍ لا يُستعمل، غرضه **دفع كلفة argon2 حين لا يوجد المستخدم**.
#
# بدونه: رقم غير موجود يردّ فورًا، ورقم موجود برمز خاطئ يدفع عشرات الميلي ثانية.
# الرسالة واحدة والزمن ليس واحدًا — فتعود شاشة الدخول أداة تعداد للطلاب، وهو
# بالضبط ما تمنعه §٧.١. الرسالة الواحدة بلا زمن واحد ضمانة ناقصة.
_DUMMY_HASH = _hasher.hash("0000")


class AuthError(Exception):
    """فشل الدخول. الرسالة واحدة لكل الأسباب — انظر `login`."""


class LockedOut(AuthError):
    def __init__(self, minutes_left: int):
        self.minutes_left = minutes_left
        super().__init__(f"الحساب مقفل مؤقّتًا. جرّب بعد {minutes_left} دقيقة.")


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_token(token: str) -> str:
    """
    التوكن عشوائي ٣٢ بايت، فـSHA-256 كافٍ هنا ولا حاجة لـargon2.
    argon2 يبطّئ التخمين في الأسرار منخفضة الإنتروبيا كرمز من أربعة أرقام؛
    وتوكن ٢٥٦ بت لا يُخمَّن أصلًا، فإبطاء التحقّق يكلّف كل طلب بلا مقابل.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def hash_pin(pin: str) -> str:
    return _hasher.hash(pin)


def _recent_failures(org_id: int, student_no: str) -> int:
    since = _now() - timedelta(minutes=LOCKOUT_MINUTES)
    return db.session.scalar(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.org_id == org_id,
            LoginAttempt.student_no == student_no,
            LoginAttempt.ok.is_(False),
            LoginAttempt.at >= since,
        )
    )


def default_org_id() -> int:
    """
    المنظمة التي يُنسب إليها الدخول.

    **لا تأتي من العميل:** العقد في `API.md` §٣ لا يحمل `org_id`، ولثلاثة أسباب —
    مراهقٌ لا يكتب رقم منظمة، والعميل لا يجوز أن يستكشف المنظمات، والتخويل كلّه
    على مستوى الجمعية (AGENTS ٩). ومع منظمة واحدة (`org_id` محمول احتياطًا بلا
    عزل مستأجرين) فأقلّ منظمة هي المقصودة قطعًا.
    """
    org_id = db.session.scalar(select(func.min(Org.id)))
    if org_id is None:
        raise AuthError("لا منظمة مهيّأة بعد.")
    return org_id


def login(org_id: int, student_no: str, pin: str) -> tuple[User, str]:
    """
    يُرجع (المستخدم، التوكن الخام). التوكن يُعطى للعميل مرة واحدة ولا يُخزَّن.

    رسالة الخطأ واحدة سواء كان الرقم غير موجود أو الرمز خاطئًا: التفريق بينهما
    يحوّل شاشة الدخول إلى أداة تعداد للأرقام المسجّلة.
    """
    if _recent_failures(org_id, student_no) >= MAX_ATTEMPTS:
        raise LockedOut(LOCKOUT_MINUTES)

    user = db.session.scalar(
        select(User).where(
            User.org_id == org_id,
            User.student_no == student_no,
            User.is_active.is_(True),
        )
    )

    # يُتحقّق دائمًا — من هاش المستخدم إن وُجد، ومن الهاش الوهمي إن لم يوجد —
    # فيتساوى زمن المسارين ولا يكشف الوجود من عدمه.
    ok = False
    try:
        _hasher.verify(user.pin_hash if user is not None else _DUMMY_HASH, pin)
        ok = user is not None
    except (VerifyMismatchError, VerificationError):
        ok = False
    except (InvalidHashError, UnicodeError):
        # **هاشٌ تالف في الصفّ** (استيرادٌ ناقص · تعديلٌ يدويّ على القاعدة ·
        # صفٌّ موروث). و`InvalidHashError` ترث `ValueError` **لا**
        # `VerificationError`، فلم يكن يلتقطها ما فوقها — فكان الدخول يردّ
        # **٥٠٠** على مسارٍ غير مصادَق عليه.
        #
        # و`UnicodeError` معها لا زيادةً: قيمةٌ غير ASCII في العمود تسقط عند
        # ترميز argon2 لها قبل أن تصل إلى فحص الشكل — عطلٌ ثانٍ بنفس السبب
        # ونفس الأثر، اكتُشف حين جُرّب هاشٌ تالف بحروف عربية.
        #
        # وردُّه خطأً ليس مجرّد قبح: يصير أوراكل يميّز ذلك الحساب عن غيره،
        # وهو بعينه ما يمنعه §٧.١ («الرسالة واحدة والزمن واحد»). ولأن الهاش
        # التالف يفشل **فورًا** بلا كلفة argon2، تُدفَع الكلفة هنا صراحةً
        # بالهاش الوهمي كي يتساوى الزمن كما يتساوى الردّ.
        with suppress(VerifyMismatchError, VerificationError):
            _hasher.verify(_DUMMY_HASH, pin)
        ok = False

    db.session.add(LoginAttempt(org_id=org_id, student_no=student_no, ok=ok))

    if not ok:
        db.session.commit()
        raise AuthError("رقم الطالب أو الرمز غير صحيح.")

    token = secrets.token_urlsafe(32)
    db.session.add(
        Session(
            user_id=user.id,
            token_hash=_hash_token(token),
            expires_at=_now() + timedelta(days=SESSION_DAYS),
        )
    )
    db.session.commit()
    return user, token


def session_for(token: str) -> Session | None:
    """الجلسة الصالحة لهذا التوكن، أو None. الإبطال والانتهاء يُفحصان هنا معًا."""
    if not token:
        return None
    return db.session.scalar(
        select(Session).where(
            Session.token_hash == _hash_token(token),
            Session.revoked.is_(False),
            Session.expires_at > _now(),
        )
    )


def logout(token: str) -> None:
    """إبطال فوري — وهذا بالضبط ما لا يستطيعه JWT."""
    s = session_for(token)
    if s is not None:
        s.revoked = True
        db.session.commit()


def revoke_all_sessions(user_id: int) -> int:
    """
    إبطال كل جلسات مستخدم. لا `commit` — المستدعي يُتمّ المعاملة.

    سبب إعادة التعيين غالبًا **فقدان الجهاز**، وترك جلساته حيّة يُبطل الغرض
    (`ARCHITECTURE.md` §٧.٥).
    """
    return db.session.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.revoked.is_(False))
        .values(revoked=True)
    ).rowcount


def generate_pin() -> str:
    """
    رمزٌ عشوائيّ من أربعة أرقام — **المولِّد الوحيد في المشروع**.

    `secrets` لا `random`: مولِّد ميرسين تُوِستر يُستنتَج من مخرجاته، فرمزٌ
    «عشوائيّ» منه يُتوقَّع. و`randbelow(10_000)` ثمّ `04d` توزيعٌ متساوٍ على
    العشرة آلاف — بخلاف تركيب أربعة أرقام مستقلّة الذي يُغري بـ`randint`
    الشامل للطرفين.
    """
    return f"{secrets.randbelow(10_000):04d}"


def reset_pin(org_id: int, target: User, actor_id: int) -> str:
    """
    رمزٌ جديد **يُعرض مرّة واحدة** ولا يُخزَّن نصًّا صريحًا أبدًا.

    ثلاثة أفعال في **معاملة واحدة**: تغيير الرمز، وإبطال الجلسات، وسطر التدقيق.
    وفصلُها يعني حالةً وسطى — رمزٌ جديد وجلساتٌ قديمة حيّة، أو تدقيقٌ لفعلٍ لم يتمّ.

    و`before`/`after` **فارغان عمدًا**: «يُسجَّل منسوبًا — **بلا قيمة الـPIN**»
    (§٧.٥). سطرُ تدقيقٍ يحمل الرمز يحوّل السجلّ نفسه إلى تسريب.
    """
    new_pin = generate_pin()
    target.pin_hash = hash_pin(new_pin)
    revoke_all_sessions(target.id)
    audit.record(
        org_id=org_id,
        kind="pin_reset",
        summary=f"إعادة تعيين رمز الطالب {target.student_no}",
        actor_id=actor_id,
    )
    db.session.commit()
    return new_pin


def membership_of(user: User) -> Membership | None:
    return db.session.scalar(
        select(Membership).where(Membership.user_id == user.id, Membership.left_at.is_(None))
    )
