from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import ORMModel


class AuditOut(ORMModel):
    id: str
    actor_id: str | None
    actor_email: str
    action: str
    target_type: str
    target_id: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    ip: str
    created_at: datetime
