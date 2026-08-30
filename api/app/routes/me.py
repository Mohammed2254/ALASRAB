"""
مسارات الطالب. **حدّ تنسيق لا مكان قواعد.**

المسار يفعل أربعة أشياء لا خامس: يتحقّق من المدخلات · يحلّ الهوية المصادَق عليها
· يستدعي الخدمة · يردّ الشكل الموثَّق. **لا حساب رتبة ولا ساعات ولا حالة طيران
هنا** — وكلٌّ منها له مالك واحد في `services/`.
"""

from flask import g
from flask.views import MethodView
from flask_smorest import Blueprint

from ..extensions import db
from ..models import Org
from ..schemas import DeckSchema
from ..security import login_required
from ..services import deck as deck_service

blp = Blueprint("me", __name__, url_prefix="/api", description="بطاقة الطيار")


@blp.route("/me/deck")
class Deck(MethodView):
    @login_required
    @blp.response(200, DeckSchema)
    def get(self):
        """
        بطاقة **الطالب المصادَق عليه**.

        الهوية من الجلسة لا من الطلب: لا معرّف في المسار ولا في الاستعلام، فلا
        يوجد ما يُتلاعب به أصلًا. وهذا أقوى من التحقّق من الملكية — يُلغي
        المسار الذي يحتاج تحقّقًا.
        """
        org = db.session.get(Org, g.user.org_id)
        card = deck_service.build(org, g.user.id)

        return {
            "rank": {"name": card.rank.name, "tier": card.rank.tier},
            "hours": card.hours,
            "next_rank": None
            if card.next_rank is None
            else {
                "name": card.next_rank.name,
                "at_hours": card.next_rank.at_hours,
                "progress_pct": card.progress_pct,
                "remaining": card.remaining,
            },
            "flight": {
                "grounded": card.flight.grounded,
                "last_activity_on": card.flight.last_activity_on,
            },
            # rank_in_org مؤجَّل إلى و-٩ (FR-051) — ولا يُحسب هنا كحلٍّ مؤقّت.
            "team": None if card.team is None else {"name": card.team.name, "rank_in_org": None},
        }
