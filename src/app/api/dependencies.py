from datetime import datetime
from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.lib.db.database import engine

# from app.lib.db.models import Session as SessionModel


# async def get_sqlmodel_session():
#     with Session(engine) as session:
#         yield session


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


def print_request_headers(request: Request):
    print(f"\n\n\nRequest headers: {dict(request)}\n\n\n")
