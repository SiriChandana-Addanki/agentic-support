from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any

@dataclass
class Resolution:
    ticket_id: str; intent: str; reasoning_summary: str; evidence: list[dict[str, Any]]
    tools_called: list[dict[str, Any]]; action: str; status: str
    escalation_required: bool; escalation_reason: str | None; final_response: str
    def validate(self) -> None:
        if not self.ticket_id or not self.intent or not self.action or self.status not in {'resolved','escalated','awaiting_customer','failed'}:
            raise ValueError('invalid resolution schema')
        if self.escalation_required != (self.status == 'escalated'):
            raise ValueError('escalation status mismatch')
    def to_dict(self): self.validate(); return asdict(self)

@dataclass
class Trace:
    request_id: str; ticket_id: str; timestamp: str; model: str = 'deterministic-policy-planner-v1'
    tool_calls: list[dict[str, Any]] = field(default_factory=list); retrieval: list[dict[str, Any]] = field(default_factory=list)
    retries: int = 0; fallback: bool = False; escalation: bool = False; errors: list[str] = field(default_factory=list)
    latency_ms: float = 0.0; final_status: str = ''
    def safe_dict(self): return asdict(self)
