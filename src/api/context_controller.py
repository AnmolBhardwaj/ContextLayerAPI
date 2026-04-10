# src/api/context_controller.py
# FastAPI router. Only talks to: core.resolver, core.builder, core.models, core.settings.
# No direct imports from sources/ or utils/ — that is the resolver's job.

from typing import List

from fastapi import APIRouter, HTTPException

from src.core.builder import build_context
from src.core.models import (
    ContextMeta,
    ContextRequest,
    ContextResponse,
    DomainInfo,
    HealthResponse,
)
from src.core.resolver import (
    get_domain_info,
    list_available_domains,
    list_available_intents,
    list_domain_sections,
    resolve_context,
)
from src.core.settings import API_VERSION

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Liveness probe. Returns version and a live count of domains and intents."""
    return HealthResponse(
        status="ok",
        version=API_VERSION,
        domains_available=len(list_available_domains()),
        intents_available=len(list_available_intents()),
    )


@router.get("/domains", response_model=List[DomainInfo])
def list_domains() -> List[DomainInfo]:
    """Returns available domains with their file and section counts."""
    domains = list_available_domains()
    result = []
    for name in domains:
        try:
            info = get_domain_info(name)
            result.append(DomainInfo(**info))
        except FileNotFoundError:
            pass
    return result


@router.get("/intents", response_model=List[str])
def list_intents() -> List[str]:
    """Returns the list of intent keys defined in intent_map.yaml."""
    return list_available_intents()


@router.get("/domains/{domain}/sections", response_model=List[str])
def get_domain_sections(domain: str) -> List[str]:
    """Returns the list of section keys available for a given domain."""
    try:
        return list_domain_sections(domain)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/context", response_model=ContextResponse)
def get_context(request: ContextRequest) -> ContextResponse:
    """
    Returns structured context for a given domain + intent combination.
    Pass `explain: true` to include a metadata block showing which files
    and sections were loaded.
    """
    try:
        all_sections, source_files, active_intent, include_keys = resolve_context(
            domain=request.domain,
            intent=request.intent,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    context = build_context(
        all_sections=all_sections,
        include_keys=include_keys,
    )

    meta = None

    if request.explain:
        meta = ContextMeta(
            domain=request.domain,
            intent_requested=request.intent,
            intent_matched=active_intent,
            sources_loaded=source_files,
            sections_found=len(all_sections),
            sections_returned=len(context),
        )

    return ContextResponse(
        intent=active_intent,
        domain=request.domain,
        context=context,
        meta=meta,
    )
