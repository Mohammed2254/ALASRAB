from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class Session(db.Model):
    """
    جلسة في قاعدة البيانات لا JWT.

    السبب واحد وحاسم: JWT لا يُبطَل قبل انتهائه. طالب قاصر ضاع جواله، أو مدير
    يجب أن يُخرج حسابًا الآن — كلاهما يتطلّب إبطالًا فوريًا. وقائمة الحظر التي
    تجعل JWT قابلًا للإبطال تعيد استعلام القاعدة لكل طلب، فتُلغي ميزته كلها.

    والتوكن يُخزَّن مهشَّرًا: تسرّب القاعدة يكشف الهاش لا التوكن، فلا ينتحل أحد
    جلسة قائمة.
    """

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_session_user", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LoginAttempt(db.Model):
    """
    محاولات الدخول، لقفل الحساب بعد تكرار الخطأ.

    رمز من أربعة أرقام = ١٠٬٠٠٠ احتمال فقط. بلا حدّ يُكسر آليًّا في دقائق، فالقفل
    ليس تشدّدًا بل هو ما يجعل الرمز القصير قابلًا للاستعمال أصلًا.
    """

    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_attempt_lookup", "org_id", "student_no", "at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    student_no: Mapped[str] = mapped_column(String, nullable=False)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
