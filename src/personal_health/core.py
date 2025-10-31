"""Core functionality and FastAPI application."""

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

from personal_health.api.operation_ids import OperationId
from personal_health.api.routes import router as api_router
from personal_health.config import Config
from personal_health.db import Database
from personal_health.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        FastAPI: configured FastAPI instance
    """
    config = Config()

    log_level = config.get("logging.level", "INFO")
    setup_logging(level=log_level)

    description = (
        "A modular, local-first system to log, analyze, and predict personal health correlations."
    )
    # Create FastAPI app
    app = FastAPI(
        title="Personal Health MCP System",
        description=description,
        version="0.1.0",
    )

    # Initialize database early
    db = Database(config.get("database.path", "data/health.db"))
    db.init()

    # Include routers before MCP wrapper so it can discover operations
    app.include_router(api_router, tags=["health"])

    # And then mount it
    include_operations_mcp = FastApiMCP(
        app,
        name="personal-health-mcp",
        description=description,
        include_operations=[
            OperationId.ADD_ENTRY,
            OperationId.UPDATE_ENTRY,
            OperationId.GET_ENTRY,
            OperationId.GET_ENTRIES,
            OperationId.GET_SUMMARY,
            OperationId.GET_PREDICTION,
            OperationId.ANALYZE_TRIGGERS,
        ],
    )
    include_operations_mcp.mount_http()

    logger.info("Application initialized")
    return app


app = create_app()
