import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from langchain_core.tools.base import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from sqlmodel import Session, select

from app.lib.caching_utils import async_cached_function
from app.lib.config import get_settings
from app.lib.db.database import engine
from app.lib.db.models import AccountModel, MCPModel, SessionModel
from app.lib.db.queries import get_current_timestamp
from app.lib.usage_utils import check_allowed_mcps

settings = get_settings()
logger = logging.getLogger(__name__)


async def _get_valid_user_session_token(db_session: Session, user_id: str) -> str:
    """
    Fetches the latest valid session token for a user in a single query.
    """
    session_stmt = (
        select(SessionModel.token)
        .where(
            SessionModel.user_id == user_id,
            SessionModel.expires_at > datetime.utcnow(),
        )
        .order_by(SessionModel.expires_at.desc())
        .limit(1)
    )
    result = db_session.execute(session_stmt)
    token = result.scalar_one_or_none()

    if not token:
        logger.warning(f"No valid session found for user_id: {user_id}")
        raise HTTPException(
            status_code=401,
            detail="Your session is invalid or has expired. Please log in again.",
        )
    return token


def _prepare_google_provider_headers(
    mcp: MCPModel, account: AccountModel, session_token: str
) -> dict:
    """
    Prepares and validates the headers required for a Google provider.
    """
    if not account.scope:
        logger.error(
            f"Account scopes missing for provider 'google' and user_id {account.user_id}"
        )
        raise HTTPException(status_code=400, detail="Account scopes are missing.")

    account_scopes = set(account.scope.split(","))
    if not set(mcp.scopes).issubset(account_scopes):
        logger.error(
            f"Account scopes {account_scopes} do not satisfy MCP scopes {mcp.scopes}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"The account permissions are insufficient for the '{mcp.name}' connector. Please reconnect your account and grant all requested permissions.",
        )

    if (
        account.access_token_expires_at
        and account.access_token_expires_at.replace(tzinfo=timezone.utc)
        < get_current_timestamp()
    ):
        logger.warning(
            f"Access token expired for provider 'google' and user_id {account.user_id}"
        )
        raise HTTPException(
            status_code=400,
            detail="The access token for 'google' has expired. Please re-authenticate.",
        )

    return {
        "X-ACCESS-TOKEN": account.access_token,
        "X-REFRESH-TOKEN": account.refresh_token,
        "X-SCOPES": account.scope,
        "X-ACCESS-TOKEN-EXPIRES-AT": str(account.access_token_expires_at)
        if account.access_token_expires_at
        else None,
        "X-CLIENT-ID": settings.google_client_id,
        "X-CLIENT-SECRET": settings.google_client_secret,
        "Authorization": f"Bearer {session_token}",
    }


@async_cached_function()
async def get_tools_from_mcps(
    mcp_ids: list[str],
    user_id: str,
) -> list[BaseTool]:
    """
    Asynchronously fetches tools from multiple MCPs for a given user.

    This optimized version:
    1. Uses a single async database session.
    2. Fetches all required MCPs, Accounts, and the user Session in parallelizable, non-blocking queries.
    3. Avoids the N+1 query problem by fetching all accounts at once.
    4. Refactors provider-specific logic into helper functions for clarity.
    """
    logger.info(f"Fetching tools for MCP IDs: {mcp_ids} and user_id: {user_id}")

    # Step 1: Fetch all necessary data from the database in a minimal number of queries.
    # Fetch all requested MCPs at once.
    mcp_stmt = select(MCPModel).where(MCPModel.id.in_(mcp_ids))
    with Session(engine) as db_session:
        mcps = db_session.execute(mcp_stmt).scalars().all()
        logger.debug(f"Fetched {len(mcps)} MCPs from DB: {[mcp.id for mcp in mcps]}")

        # Fetch the user's session token once.
        session_token = await _get_valid_user_session_token(db_session, user_id)

        # Collect all unique provider IDs from the fetched MCPs.
        provider_ids = {mcp.provider_id for mcp in mcps if mcp.provider_id}
        accounts_by_provider = {}

        # Fetch all required accounts for the collected provider IDs in a single query.
        if provider_ids:
            acc_stmt = select(AccountModel).where(
                AccountModel.provider_id.in_(provider_ids),
                AccountModel.user_id == user_id,
            )
            account_results = db_session.execute(acc_stmt).scalars().all()
            accounts_by_provider = {acc.provider_id: acc for acc in account_results}
            logger.debug(
                f"Fetched {len(accounts_by_provider)} accounts for providers: {list(accounts_by_provider.keys())}"
            )

    # Step 2: Process the fetched data and prepare parameters for the client.
    # This loop now contains no database calls.
    server_params = {}
    for mcp in mcps:
        logger.info(f"Processing MCP: {mcp.id} ({mcp.name})")

        # This check can be performed without I/O
        check_allowed_mcps(mcp_id=str(mcp.id), user_id=user_id)

        params = {
            "url": mcp.url,
            "transport": "streamable_http",
            "headers": {},
        }

        if mcp.provider_id:
            account = accounts_by_provider.get(mcp.provider_id)
            if not account:
                logger.error(
                    f"No account found for provider ID {mcp.provider_id} and user_id {user_id}"
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"An account for '{mcp.provider_id}' was not found. Please connect your account to proceed.",
                )

            # Delegate header creation to provider-specific functions for better organization.
            if mcp.provider_id == "google":
                params["headers"] = _prepare_google_provider_headers(
                    mcp, account, session_token
                )
            elif mcp.provider_id == "notion":
                params["headers"] = {
                    "X-ACCESS-TOKEN": account.access_token,
                    "Authorization": f"Bearer {session_token}",
                }
            else:
                params["headers"] = {
                    "Authorization": f"Bearer {session_token}",
                }
        else:
            params["headers"] = {
                "Authorization": f"Bearer {session_token}",
            }

        server_params[mcp.name] = params
        logger.info(f"Server params prepared for MCP {mcp.name}")

    # Step 3: Instantiate the client and fetch the tools.
    if not server_params:
        logger.warning(
            "No server parameters were generated, returning empty list of tools."
        )
        return []

    logger.info(
        f"Instantiating MultiServerMCPClient for servers: {list(server_params.keys())}"
    )
    client = MultiServerMCPClient(server_params)
    tools = await client.get_tools()

    prompts = {}
    for mcp in mcps:
        try:
            prompt = await client.get_prompt(mcp.name, "instructions")
            prompts[mcp.name] = prompt[0].content
            logger.info(f"Fetched prompt for MCP {mcp.name}")
        except Exception as e:
            logger.warning(f"Failed to fetch prompt for {mcp.name}: {e}")
            prompts[mcp.name] = ""

    logger.info(f"Successfully fetched {len(tools)} tools from MCPs.")
    logger.info(f"prompts {len(prompts)}")

    return {"tools": tools, "prompts": prompts}
