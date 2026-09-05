"""مخططات Marshmallow: شكل الطلب والردّ والتحقّق. لا منطق أعمال ولا وصول للقاعدة."""

from .audit import ResetPinSchema
from .audit_log import AuditLogSchema
from .auth import LoginSchema, SessionSchema
from .engagement import (
    AdminNotesListSchema,
    AnsweredSchema,
    AnswerSchema,
    ChooseWeekPilotSchema,
    ChosenWeekPilotSchema,
    MarkedNoteSchema,
    MarkNoteReadSchema,
    SubmitNoteSchema,
    TodayQuestionSchema,
    WeekPilotSchema,
)
from .entry import (
    AttendanceStatusSchema,
    RecordAttendanceSchema,
    RecordedAttendanceSchema,
    UndoneAttendanceSchema,
)
from .fuel import (
    ActivitiesListSchema,
    AssessedSchema,
    AssessSchema,
    CreateActivitySchema,
    CreatedActivitySchema,
    StationSchema,
)
from .me import DeckSchema, EventsSchema
from .reading import (
    ApproveSchema,
    MyReadingsSchema,
    QueueSchema,
    RejectSchema,
    ReviewResultsSchema,
    SubmitReadingSchema,
    SubmittedSchema,
)
from .report import ReportSchema
from .rules_admin import (
    CreateWeightVersionSchema,
    SaveThresholdsSchema,
    ThresholdsPreviewSchema,
    ThresholdsSchema,
    WeightsSchema,
    WeightVersionIdSchema,
)
from .standings import FormationSchema, PilotsBoardSchema, TeamsBoardSchema
from .teams import (
    ArchivedTeamSchema,
    ArchiveTeamSchema,
    CreatedTeamSchema,
    CreateTeamSchema,
    TeamsListSchema,
    TransferMemberSchema,
    TransferredMemberSchema,
)

__all__ = [
    "ActivitiesListSchema",
    "AdminNotesListSchema",
    "AnswerSchema",
    "AnsweredSchema",
    "ApproveSchema",
    "ArchivedTeamSchema",
    "ArchiveTeamSchema",
    "AssessSchema",
    "AssessedSchema",
    "AttendanceStatusSchema",
    "AuditLogSchema",
    "ChooseWeekPilotSchema",
    "ChosenWeekPilotSchema",
    "CreateActivitySchema",
    "CreatedActivitySchema",
    "CreateTeamSchema",
    "CreateWeightVersionSchema",
    "CreatedTeamSchema",
    "DeckSchema",
    "EventsSchema",
    "FormationSchema",
    "LoginSchema",
    "MarkedNoteSchema",
    "MarkNoteReadSchema",
    "MyReadingsSchema",
    "PilotsBoardSchema",
    "QueueSchema",
    "RecordAttendanceSchema",
    "RecordedAttendanceSchema",
    "RejectSchema",
    "ResetPinSchema",
    "ReportSchema",
    "ReviewResultsSchema",
    "SaveThresholdsSchema",
    "SessionSchema",
    "StationSchema",
    "SubmitNoteSchema",
    "SubmitReadingSchema",
    "SubmittedSchema",
    "TeamsBoardSchema",
    "TeamsListSchema",
    "ThresholdsPreviewSchema",
    "ThresholdsSchema",
    "TodayQuestionSchema",
    "TransferMemberSchema",
    "TransferredMemberSchema",
    "UndoneAttendanceSchema",
    "WeekPilotSchema",
    "WeightVersionIdSchema",
    "WeightsSchema",
]
