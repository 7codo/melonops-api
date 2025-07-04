from typing import Optional

from fastapi import HTTPException
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlmodel import Session

from app.lib.db.database import engine

# from app.lib.db.models import Session as SessionModel

# Global variable to store the checkpointer instance
_checkpointer: Optional[AsyncPostgresSaver] = None


def set_checkpointer(checkpointer: AsyncPostgresSaver):
    """Set the global checkpointer instance."""
    global _checkpointer
    _checkpointer = checkpointer


async def get_checkpointer() -> AsyncPostgresSaver:
    """Get the global checkpointer instance."""
    global _checkpointer
    if _checkpointer is None:
        raise HTTPException(status_code=500, detail="Checkpointer not initialized")
    return _checkpointer


def get_sqlmodel_session():
    with Session(engine) as session:
        yield session


# async def verify_session_token(
#     request: Request,
#     session: Session = Depends(get_sqlmodel_session),
# ):
#     # Try to get token from cookies first
#     session_token = request.cookies.get("better-auth.session_token")

#     # If not in cookies, try to get from Authorization header
#     if not session_token:
#         auth_header = request.headers.get("Authorization")
#         if auth_header and auth_header.startswith("Bearer "):
#             session_token = auth_header.split(" ")[1]

#     if not session_token:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Authentication token missing",
#         )
#     token = session_token.split(".")[0]
#     if not token:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Malformed token",
#         )
#     statement = select(SessionModel).where(SessionModel.token == token)
#     try:
#         session_from_db = session.exec(statement).one()
#     except (NoResultFound, MultipleResultsFound) as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid session {e}"
#         )

#     now = datetime.now()
#     if now > session_from_db.expires_at:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired session"
#         )

#     return session_from_db
