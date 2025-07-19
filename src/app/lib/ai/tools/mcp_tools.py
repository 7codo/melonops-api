import logging
from datetime import timezone

from fastapi import HTTPException
from langchain_core.tools.base import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from sqlmodel import Session, select

from app.lib.caching_utils import async_cached_function
from app.lib.config import get_settings
from app.lib.db.database import engine
from app.lib.db.models import AccountModel, MCPModel
from app.lib.db.queries import get_current_timestamp
from app.lib.usage_utils import check_allowed_mcps

settings = get_settings()
logger = logging.getLogger(__name__)


@async_cached_function()
async def get_tools_from_mcps(mcp_ids: list[str], user_id: str) -> list[BaseTool]:
    logger.info(f"Fetching tools for MCP IDs: {mcp_ids} and user_id: {user_id}")
    with Session(engine) as session:
        statement = select(MCPModel).where(MCPModel.id.in_(mcp_ids))  # type: ignore
        mcps = list(session.exec(statement).all())
        logger.debug(f"Fetched MCPs from DB: {[mcp.id for mcp in mcps]}")
        server_params = {}
        for mcp in mcps:
            logger.info(f"Checking allowed MCP for mcp_id: {mcp.id}")
            check_allowed_mcps(mcp_id=str(mcp.id), user_id=user_id)
            params = {"url": mcp.url, "transport": "streamable_http", "headers": {}}
            if mcp.provider_id is not None:
                logger.debug(f"MCP {mcp.id} has provider_id: {mcp.provider_id}")
                with Session(engine) as session:
                    statement = select(AccountModel).where(
                        AccountModel.provider_id == mcp.provider_id,
                        AccountModel.user_id == user_id,
                    )
                    account = session.exec(statement).first()

                    if not account:
                        logger.error(
                            f"No account found for provider ID {mcp.provider_id} and user_id {user_id}"
                        )
                        raise HTTPException(
                            status_code=400,
                            detail=f"No account was found for provider ID {mcp.provider_id}. Please verify your connection or add an account to proceed.",
                        )
                    if account.scope is None:
                        logger.error(
                            f"Account scopes missing for provider ID {mcp.provider_id} and user_id {user_id}"
                        )
                        raise HTTPException(
                            status_code=400,
                            detail="Account scopes required",
                        )
                    account_scopes = set(account.scope.split(","))
                    mcp_scopes = set(mcp.scopes)
                    if not mcp_scopes.issubset(account_scopes):
                        logger.error(
                            f"Account scopes {account_scopes} do not match MCP scopes {mcp_scopes} for provider ID {mcp.provider_id}"
                        )
                        raise HTTPException(
                            status_code=400,
                            detail=f"The account scopes do not match the connector scopes for provider ID {mcp.provider_id}. Please log in to {mcp.provider_id} and grant the necessary access permissions to proceed.",
                        )
                    if mcp.provider_id == "google":
                        now = get_current_timestamp()
                        if (
                            account.access_token_expires_at
                            and account.access_token_expires_at.replace(
                                tzinfo=timezone.utc
                            )
                            < now
                        ):
                            logger.warning(
                                f"Access token expired for provider ID {mcp.provider_id} and user_id {user_id}"
                            )
                            raise HTTPException(
                                status_code=400,
                                detail=f"The access token for provider ID {mcp.provider_id} has expired. Please reauthenticate to continue.",
                            )
                        params["headers"] = {
                            "X-ACCESS-TOKEN": account.access_token,
                            "X-REFRESH-TOKEN": account.refresh_token,
                            "X-SCOPES": account.scope,
                            "X-ACCESS-TOKEN-EXPIRES-AT": str(
                                account.access_token_expires_at
                            )
                            if account.access_token_expires_at
                            else None,
                            "X-CLIENT-ID": settings.google_client_id,
                            "X-CLIENT-SECRET": settings.google_client_secret,
                        }
                        logger.debug(f"Set Google headers for MCP {mcp.id}")
            server_params[mcp.name] = params
            logger.info(f"Server params set for MCP {mcp.name}")

        logger.info(
            f"Instantiating MultiServerMCPClient with params for {list(server_params.keys())}"
        )
        client = MultiServerMCPClient(server_params)
        tools = await client.get_tools()
        logger.info(f"Fetched {len(tools)} tools from MCPs")
        return tools
