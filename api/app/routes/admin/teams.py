"""
الأسراب والعضويات (`FR-083`) — **أرشفةٌ لا حذف، ونقلٌ لا يزوّر التاريخ**.
"""

from flask import g
from flask.views import MethodView
from flask_smorest import abort

from ...schemas.teams import (
    ArchivedTeamSchema,
    ArchiveTeamSchema,
    CreatedTeamSchema,
    CreateTeamSchema,
    TeamsListSchema,
    TransferMemberSchema,
    TransferredMemberSchema,
)
from ...security import admin_required
from ...services import teams as teams_service
from .._helpers import org_of_session as _org
from . import blp


@blp.route("/admin/teams")
class Teams(MethodView):
    @admin_required
    @blp.response(200, TeamsListSchema)
    def get(self):
        return {"teams": teams_service.list_teams(g.user.org_id)}

    @admin_required
    @blp.arguments(CreateTeamSchema)
    @blp.response(201, CreatedTeamSchema)
    def post(self, data):
        try:
            return teams_service.create_team(_org(), data["name"], data["code"], g.user.id)
        except teams_service.TeamsError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/teams/<int:team_id>")
class TeamDetail(MethodView):
    @admin_required
    @blp.arguments(ArchiveTeamSchema)
    @blp.response(200, ArchivedTeamSchema)
    def patch(self, _data, team_id):
        """أرشفة فقط — لا إلغاء أرشفة اليوم (م-١٠: قرارٌ يستحقّ مسارًا صريحًا)."""
        try:
            return teams_service.archive_team(_org(), team_id, g.user.id)
        except teams_service.TeamsError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/admin/teams/<int:team_id>/members")
class TeamMembers(MethodView):
    @admin_required
    @blp.arguments(TransferMemberSchema)
    @blp.response(200, TransferredMemberSchema)
    def post(self, data, team_id):
        """نقلٌ لا يزوّر التاريخ: العضوية القديمة تُغلَق لا تُحذَف (م-١٠)."""
        try:
            return teams_service.transfer_member(_org(), team_id, data["user_id"], g.user.id)
        except teams_service.TeamsError as exc:
            abort(exc.status, message=str(exc))
