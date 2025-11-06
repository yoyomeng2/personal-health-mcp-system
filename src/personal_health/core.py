"""Core functionality and FastAPI application."""

from fastapi import Depends, FastAPI
from fastapi_mcp import FastApiMCP
from fastapi_mcp.types import AuthConfig

from personal_health.api.dependencies import init_dependencies
from personal_health.api.routes import (
    router as api_router,
)
from personal_health.api.routes import (
    verify_chatgpt_token,
    verify_claude_token,
)
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
    app.include_router(api_router)

    # Claude MCP - read-only operations with auth
    claude_ops = ["get_entries", "get_summary", "analyze_triggers", "get_prediction"]
    claude_mcp = FastApiMCP(
        app,
        name="personal-health-claude",
        description="Claude Desktop integration - read-only operations",
        include_operations=claude_ops,
        headers=["X-API-Key"],  # Forward X-API-Key header from MCP client to tool calls
        auth_config=AuthConfig(dependencies=[Depends(verify_claude_token)]),
    )
    claude_mcp.mount_http(mount_path="/mcp/claude")

    # ChatGPT MCP - full access with auth
    chatgpt_ops = [
        "add_entry",
        "update_entry",
        "get_entries",
        "extract_features",
        "get_summary",
        "update_user_profile",
        "get_user_profile",
    ]
    chatgpt_mcp = FastApiMCP(
        app,
        name="personal-health-chatgpt",
        description="ChatGPT integration - full access",
        include_operations=chatgpt_ops,
        headers=["X-API-Key"],  # Forward X-API-Key header from MCP client to tool calls
        auth_config=AuthConfig(dependencies=[Depends(verify_chatgpt_token)]),
    )
    chatgpt_mcp.mount_http(mount_path="/mcp/chatgpt")

    logger.info("Application initialized")
    logger.info(f"Claude MCP operations ({len(claude_ops)}): {claude_ops}")
    logger.info(f"ChatGPT MCP operations ({len(chatgpt_ops)}): {chatgpt_ops}")
    return app


app = create_app()
