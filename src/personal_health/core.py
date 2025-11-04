"""Core functionality and FastAPI application."""

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

from personal_health.api.dependencies import init_dependencies
from personal_health.api.operation_ids import get_mcp_operations
from personal_health.api.routes import router as api_router
from personal_health.config import Config
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

    # Initialize dependencies after logging is configured
    db_path = config.get("database.path", "data/health.db")
    init_dependencies(db_path)

    description = (
        "A modular, local-first system to log, analyze, and predict personal health correlations."
    )
    # Create FastAPI app
    app = FastAPI(
        title="Personal Health MCP System",
        description=description,
        version="0.1.0",
    )

    # Include routers (database is initialized in routes module)
    app.include_router(api_router, tags=["health"])

    # And then mount it
    include_operations_mcp = FastApiMCP(
        app,
        name="personal-health-mcp",
        description=description,
        include_operations=get_mcp_operations(),
    )
    include_operations_mcp.mount_http()

    logger.info("Application initialized")
    return app


app = create_app()
