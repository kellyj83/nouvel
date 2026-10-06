"""Provider-independent data contracts for post-call follow-up analysis."""

from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Base contract that rejects unexpected fields and trims surrounding whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AttendeeRole(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class FollowUpUrgency(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DealReadiness(str, Enum):
    NO_ACTIVE_OPPORTUNITY = "no_active_opportunity"
    EARLY = "early"
    PROGRESSING = "progressing"
    BLOCKED = "blocked"
    READY = "ready"


class EvidenceSource(str, Enum):
    TRANSCRIPT = "transcript"
    MEETING_SUMMARY = "meeting_summary"
    ATTIO = "attio"


class NextAction(str, Enum):
    SEND_FOLLOW_UP = "send_follow_up"
    CREATE_TASK = "create_task"
    REQUEST_INFORMATION = "request_information"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    NO_ACTION = "no_action"


class Attendee(ContractModel):
    name: str = Field(min_length=1)
    email: str | None = None
    role: AttendeeRole = AttendeeRole.UNKNOWN


class GranolaMeeting(ContractModel):
    note_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    occurred_at: AwareDatetime
    summary: str = Field(min_length=1)
    transcript: str = Field(min_length=1)
    attendees: list[Attendee] = Field(min_length=1)


class AttioContext(ContractModel):
    company_name: str = Field(min_length=1)
    company_record_id: str | None = None
    contact_names: list[str] = Field(default_factory=list)
    deal_name: str | None = None
    deal_record_id: str | None = None
    deal_stage: str | None = None
    deal_owner: str | None = None
    recent_history: list[str] = Field(default_factory=list)
    qualification_context: list[str] = Field(default_factory=list)


class FollowUpInput(ContractModel):
    meeting: GranolaMeeting
    attio: AttioContext


class Evidence(ContractModel):
    source: EvidenceSource
    excerpt: str = Field(min_length=1)
    interpretation: str = Field(min_length=1)


class Commitment(ContractModel):
    description: str = Field(min_length=1)
    owner: str | None = None
    deadline_as_stated: str | None = None
    evidence_excerpt: str = Field(min_length=1)


class RecommendedAction(ContractModel):
    action: NextAction
    owner: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    deadline: AwareDatetime | None = None


class DraftFollowUp(ContractModel):
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)


class AttioTaskSuggestion(ContractModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    assignee: str | None = None
    deadline: AwareDatetime | None = None


class FollowUpAssessment(ContractModel):
    follow_up_urgency: FollowUpUrgency
    urgency_confidence: float = Field(ge=0.0, le=1.0)
    urgency_reason: str = Field(min_length=1)
    deal_readiness: DealReadiness
    readiness_confidence: float = Field(ge=0.0, le=1.0)
    readiness_reason: str = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)
    commitments: list[Commitment] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    recommended_action: RecommendedAction
    draft_follow_up: DraftFollowUp | None = None
    suggested_attio_note: str = Field(min_length=1)
    suggested_attio_task: AttioTaskSuggestion | None = None
    requires_human_approval: bool = True


class QueueItem(ContractModel):
    rank: int = Field(ge=1)
    priority_score: int = Field(ge=0)
    note_id: str = Field(min_length=1)
    meeting_title: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    deal_name: str | None = None
    owner: str = Field(min_length=1)
    follow_up_urgency: FollowUpUrgency
    deal_readiness: DealReadiness
    urgency_reason: str = Field(min_length=1)
    readiness_reason: str = Field(min_length=1)
    next_action: RecommendedAction
    evidence: list[Evidence] = Field(min_length=1)
    requires_human_approval: bool = True


class FollowUpQueue(ContractModel):
    items: list[QueueItem] = Field(default_factory=list)
