from langchain_mcp_adapters.client import MultiServerMCPClient
from app.lib.db.models import MCPModel, AccountModel
from sqlmodel import Session, select
from app.lib.db.database import engine
from app.lib.config import get_settings
from fastapi import HTTPException
from app.lib.db.queries import get_current_timestamp
from datetime import timezone

settings = get_settings()


async def get_tools_from_mcps(mcps: list[MCPModel], user_id: str):
    server_params = {}
    for mcp in mcps:
        params = {"url": mcp.url, "transport": "streamable_http", "headers": {}}
        if mcp.provider_id is not None:
            with Session(engine) as session:
                statement = select(AccountModel).where(
                    AccountModel.provider_id == mcp.provider_id,
                    AccountModel.user_id == user_id,
                )
                account = session.exec(statement).first()

                if not account:
                    raise HTTPException(
                        status_code=400,
                        detail=f"No account found for provider_id {mcp.provider_id}",
                    )
                if account.scope is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Account scopes required",
                    )
                account_scopes = set(account.scope.split(","))
                mcp_scopes = set(mcp.scopes)
                if not mcp_scopes.issubset(account_scopes):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Account scopes do not match MCP scopes for provider_id {mcp.provider_id}",
                    )
                if mcp.provider_id == "google":
                    now = get_current_timestamp()
                    if (
                        account.access_token_expires_at
                        and account.access_token_expires_at.replace(tzinfo=timezone.utc)
                        < now
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Access token for provider_id {mcp.provider_id} has expired",
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
        server_params[mcp.name] = params

    client = MultiServerMCPClient(server_params)
    tools = await client.get_tools()
    return tools
