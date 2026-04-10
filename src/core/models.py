# src/core/models.py
# Defines all request and response data shapes for the Context Layer API.
# These models are the contract between the API and its consumers.

import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from src.core.settings import MAX_IDENTIFIER_LENGTH


class ContextRequest(BaseModel):
    """Incoming request to retrieve context."""

    intent: str = Field(..., description="The intent key, e.g. 'create_campaign'")
    domain: str = Field(..., description="The domain folder name, e.g. 'banking'")
    explain: bool = Field(
        default=False,
        description="If true, include a meta block showing which files and sections were used.",
    )

    @field_validator("domain", "intent")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validates that domain and intent contain only safe identifier characters.

        Prevents path traversal attacks (e.g. '../../etc/passwd') and other
        injection attempts by restricting input to letters, digits, underscores,
        and hyphens up to MAX_IDENTIFIER_LENGTH characters.
        """
        pattern = rf"^[a-zA-Z0-9_-]{{1,{MAX_IDENTIFIER_LENGTH}}}$"
        if not re.match(pattern, v):
            raise ValueError(
                f"must contain only letters, digits, underscores, or hyphens "
                f"(max {MAX_IDENTIFIER_LENGTH} characters)"
            )
        return v


class ContextMeta(BaseModel):
    """Optional metadata block explaining what was loaded and why."""

    domain: str
    intent_requested: str
    intent_matched: str  # Either the requested intent or the configured default
    sources_loaded: List[str]  # Filenames that were read
    sections_found: int  # Total sections parsed from all files
    sections_returned: int  # Sections that matched the intent filter


class ContextResponse(BaseModel):
    """Structured context bundle returned to the caller."""

    intent: str
    domain: str
    context: Dict[str, str]  # Keys are section names, values are content strings
    meta: Optional[ContextMeta] = None  # Only present when explain=True


class HealthResponse(BaseModel):
    """Response shape for GET /health."""

    status: str
    version: str
    domains_available: int
    intents_available: int


class DomainInfo(BaseModel):
    """Summary of a single domain returned by GET /domains."""

    name: str
    files: int
    sections: int
