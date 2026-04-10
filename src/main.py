# src/main.py
# FastAPI application factory.

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.context_controller import router
from src.core.resolver import list_available_domains, list_available_intents
from src.core.settings import (
    API_DESCRIPTION,
    API_PREFIX,
    API_TITLE,
    API_VERSION,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("context_layer")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async context manager for application lifecycle events."""
    # Startup
    try:
        domains = list_available_domains()
        intents = list_available_intents()
        logger.info(
            "Context Layer %s started — %d domain(s): [%s] | %d intent(s): [%s]",
            API_VERSION,
            len(domains),
            ", ".join(domains),
            len(intents),
            ", ".join(intents),
        )
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Context Layer API shutting down")


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
)

# Enable CORS for public API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=API_PREFIX)
