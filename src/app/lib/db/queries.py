from datetime import datetime
from sqlmodel import Session
from sqlalchemy import func, select
from app.lib.db.database import engine


def get_current_timestamp() -> datetime:
    with Session(engine) as session:
        result = session.execute(select(func.now())).scalar_one()
    return result
