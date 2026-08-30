from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class User(db.Model):
    """
    الطيارون والمشرفون.

    **لا عمود `role`:** الدور صفة على العضوية لا على المستخدم، فيمكن لشخص أن يكون
    مشرفًا في منظمة ومستخدمًا في أخرى بلا تغيير في المخطط.

    **ولا عمود `grounded` (ث-١٤):** حالة الطيران **محسوبة** من آخر حدث معتمد.
    عمودٌ يحمل قيمة مشتقّة يفترق عن مصدره في أوّل مسار يَنسى تحديثه — وهي نفس
    علّة رفض «عمود رصيد» في ADR-001.
    """

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("org_id", "student_no", name="uq_user_student_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    student_no: Mapped[str] = mapped_column(String, nullable=False)

    # رمز من أربعة أرقام ضعيف بطبيعته: ١٠٬٠٠٠ احتمال. تخزينه نصًّا صريحًا يحوّل أي
    # تسرّب لقاعدة البيانات إلى تسرّب حسابات فوري، فيُهشَّر بـargon2id.
    pin_hash: Mapped[str] = mapped_column(String, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
