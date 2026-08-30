"""Core data model (spec section 6) plus OpenAI-compatible wire types.

Design rule that is load-bearing across the whole codebase:
`RiskVector.categories` is a SET. The brief is explicit that these risks
overlap -- a fabricated salary figure about a named colleague is BOTH a
hallucination and a privacy hit. Nothing here ever forces a single label.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


# --- detector primitives -----------------------------------------------------
class PIIHit(BaseModel):
    text: str
    entity_type: str                 # PERSON, EMAIL, PHONE, AADHAAR, IBAN, ...
    in_context: bool                 # present in retrieved context?  <- overlap rule
    start: int = -1
    end: int = -1


Verdict = Literal["allow", "annotate", "redact", "hold", "block", "escalate"]
Reversibility = Literal["reversible", "costly", "irreversible"]
Tier = Literal["L0", "L1", "L2", "HUMAN"]


class RiskVector(BaseModel):
    groundedness: float = 1.0        # 0..1, claims supported by retrieval
    assertiveness: float = 0.0       # 0..1, how strongly the answer commits
    ceg: float = 0.0                 # 0..1, the confidence-evidence gap
    entropy_term: float = 0.0        # self-consistency / logprob uncertainty
    pii_entities: list[PIIHit] = Field(default_factory=list)
    pattern_hits: list[str] = Field(default_factory=list)
    injection_score: float = 0.0
    unsupported_claims: list[str] = Field(default_factory=list)
    categories: set[str] = Field(default_factory=set)   # OVERLAPPING, never exclusive
    severity: int = 0                # 0..3, fused
    fused: float = 0.0               # 0..1, the scalar the gate bands on
    backend_scores: dict[str, float] = Field(default_factory=dict)


class ActionRequest(BaseModel):
    tool: str                        # "refund.issue" | "email.send" | "ticket.note"
    reversibility: Reversibility = "reversible"
    blast_radius: int = 0            # 0..3, from policy
    arguments: dict = Field(default_factory=dict)


class Decision(BaseModel):
    request_id: str
    conversation_id: str = "single"
    turn_index: int = 0
    use_case: str = ""
    jurisdiction: str = ""
    policy_hash: str = ""            # which rules decided this
    tier_reached: Tier = "L0"
    risk: RiskVector = Field(default_factory=RiskVector)
    accumulated_risk: float = 0.0    # conversation-level carry-forward
    action: Optional[ActionRequest] = None
    band: Literal["low", "medium", "high"] = "low"
    verdict: Verdict = "allow"
    escalate: bool = False
    rationale: str = ""
    latency_ms: dict = Field(default_factory=dict)
    cost_usd: float = 0.0


# --- corpus record -----------------------------------------------------------
class Gold(BaseModel):
    risky: bool
    categories: list[str] = Field(default_factory=list)
    expected_verdict: str = "allow"
    note: str = ""


class CorpusRecord(BaseModel):
    id: str
    use_case: str
    turns: list[dict] = Field(default_factory=list)
    retrieved: list[str] = Field(default_factory=list)
    response: str = ""
    action_requested: Optional[dict] = None
    # `paired` records carry a second action to prove the reversibility flip.
    action_requested_b: Optional[dict] = None
    conversation_id: Optional[str] = None
    turn_index: int = 0
    self_consistency: Optional[float] = None   # simulated resample signal (offline)
    gold: Optional[Gold] = None
    gold_b: Optional[Gold] = None


# --- OpenAI-compatible wire types -------------------------------------------
class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[list[dict]] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: list[ChatMessage] = Field(default_factory=list)
    temperature: float = 0.2
    stream: bool = False
    tools: Optional[list[dict]] = None
    tool_choice: Optional[object] = None
    # CLEARANCE extensions (ignored by vanilla OpenAI clients):
    clearance: Optional[dict] = None   # {policy, retrieved, action, conversation_id}
