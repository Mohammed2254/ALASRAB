"""
حرّاس المسارات. كل endpoint محميّ يمرّ بأحدهما — لا استثناء.

الحارس **على تعريف المسار** لا داخل الجسم: نسيانه في الجسم لا يُرى في المراجعة
(ARCHITECTURE §٧.٣).
"""

from functools import wraps

from flask import g, request
from flask_smorest import abort

from .extensions import db
from .models import User
from .services.auth import membership_of, session_for

COOKIE = "asrab_session"


def current_identity():
    """
    (المستخدم، العضوية السارية) أو (None, None).

    **العضوية اختيارية عمدًا:** طالبٌ نُقل بين الأسراب فبقي لحظةً بلا عضوية يجب
    أن يرى بطاقته لا أن يُقفَل خارج حسابه — و`SCOPE.md` ط-٢ يوجب أن تكون الحالة
    الناقصة **مصمَّمة لا مكسورة**. والأثر الأمني آمن في الاتّجاه الصحيح: بلا
    عضوية لا دور، وبلا دور لا صلاحية إشراف.
    """
    session = session_for(request.cookies.get(COOKIE, ""))
    if session is None:
        return None, None
    user = db.session.get(User, session.user_id)
    if user is None or not user.is_active:
        return None, None
    return user, membership_of(user)


def login_required(fn):
    """يضع `g.user` و`g.membership`، أو يردّ ٤٠١ برسالة لا تكشف السبب."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        user, membership = current_identity()
        if user is None:
            abort(401, message="الجلسة غير صالحة. سجّل الدخول من جديد.")
        g.user = user
        g.membership = membership
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    """
    يبني على `login_required`. الدور صفة على **العضوية** لا على المستخدم، فيمكن
    لشخص أن يكون مشرفًا في منظمة ومستخدمًا في أخرى بلا تغيير في المخطط.

    وصلاحية المشرف **على مستوى الجمعية** لا السرب (ARCHITECTURE §٧.٣): لا يُفحص
    `team_id` هنا ولا في أي استعلام إداري.

    وبلا عضوية ⇒ ٤٠٣. الفشل مُغلق: غياب المعلومة يمنع لا يسمح.
    """

    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if g.membership is None or g.membership.role != "admin":
            abort(403, message="هذه الصفحة للمشرفين.")
        return fn(*args, **kwargs)

    return wrapper


def role_of(membership) -> str:
    """الدور المعروض. بلا عضوية: `pilot` — أقلّ الأدوار صلاحيةً."""
    return membership.role if membership is not None else "pilot"
