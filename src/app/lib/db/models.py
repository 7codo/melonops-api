from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY


class MCPModel(SQLModel, table=True):
    __tablename__: str = "mcp"

    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
    name: str = Field(max_length=225, nullable=False)
    description: str = Field(nullable=False)
    url: str = Field(max_length=225, nullable=False)
    provider_id: Optional[str] = Field(default=None, max_length=225)
    scopes: List[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String), nullable=False)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class AccountModel(SQLModel, table=True):
    __tablename__: str = "account"

    id: str = Field(primary_key=True)
    account_id: str = Field(nullable=False)
    provider_id: str = Field(nullable=False)
    user_id: str = Field(foreign_key="user.id", nullable=False)
    access_token: Optional[str] = Field(default=None)
    refresh_token: Optional[str] = Field(default=None)
    id_token: Optional[str] = Field(default=None)
    access_token_expires_at: Optional[datetime] = Field(default=None)
    refresh_token_expires_at: Optional[datetime] = Field(default=None)
    scope: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    created_at: datetime = Field(nullable=False)
    updated_at: datetime = Field(nullable=False)


class AgentModel(SQLModel, table=True):
    __tablename__: str = "agent"

    id: UUID = Field(
        default_factory=uuid4, primary_key=True, nullable=False, unique=True
    )
    name: Optional[str] = Field(max_length=225, default=None)
    description: Optional[str] = Field(default=None)
    system_prompt: Optional[str] = Field(default=None)
    tools_ids: List[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String), nullable=False)
    )
    user_id: str = Field(foreign_key="user.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class AgentMcpModel(SQLModel, table=True):
    __tablename__: str = "agent_mcp"

    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
    agent_id: UUID = Field(foreign_key="agent.id", nullable=False)
    mcp_id: UUID = Field(foreign_key="mcp.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class TaskModel(SQLModel, table=True):
    __tablename__: str = "task"

    id: UUID = Field(
        default_factory=uuid4, primary_key=True, nullable=False, unique=True
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    title: str = Field(nullable=False)
    user_id: str = Field(foreign_key="user.id", nullable=False)
    agent_id: UUID = Field(foreign_key="agent.id", nullable=False)
