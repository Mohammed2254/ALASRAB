"""حذف عمودٍ ميّت: teams.thread_color — و-٢٢

Revision ID: 5696cc2ab08c
Revises: 922a1b617a1f

`Team.thread_color` صفرُ مراجع في `app/` و`tests/` و`ui/src/` — يُكتب
بلا كاتبٍ ويُقرأ بلا قارئ. وصفرُ صفوفٍ تحمل قيمةً (مقيسًا قبل الحذف)، فالحذف
لا يُفقد بيانات.

**و`Membership.joined_at` لا يُحذف** رغم أنه غير مقروءٍ هو أيضًا: ذاك
**تاريخُ عضوية** يكتبه `server_default`، وحذفُه يمحو متى انتسب كلُّ طالب —
وهو ما تمنعه روح ADR-004 (أرشفةٌ لا حذف). غيرُ المقروء ليس ميّتًا إن كان
تاريخًا.
"""

import sqlalchemy as sa
from alembic import op

revision = "5696cc2ab08c"
down_revision = "922a1b617a1f"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("teams", "thread_color")


def downgrade():
    op.add_column("teams", sa.Column("thread_color", sa.String(), nullable=True))
