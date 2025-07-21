from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Column, Field, ForeignKey, SQLModel


class SessionModel(SQLModel, table=True):
    __tablename__: str = "session"

    id: str = Field(primary_key=True, nullable=False)
    expires_at: datetime = Field(nullable=False)
    token: str = Field(nullable=False, unique=True)
    created_at: datetime = Field(nullable=False)
    updated_at: datetime = Field(nullable=False)
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    user_id: str = Field(
        sa_column=Column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    )


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


class PlanModel(SQLModel, table=True):
    __tablename__: str = "plan"

    id: int = Field(primary_key=True, nullable=False)
    productId: int = Field(nullable=False)
    productName: Optional[str] = Field(default=None)
    variantId: int = Field(nullable=False, unique=True)
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    price: str = Field(nullable=False)
    isUsageBased: bool = Field(default=False)
    interval: Optional[str] = Field(default=None)
    intervalCount: Optional[int] = Field(default=None)
    trialInterval: Optional[str] = Field(default=None)
    trialIntervalCount: Optional[int] = Field(default=None)
    sort: Optional[int] = Field(default=None)


class SubscriptionModel(SQLModel, table=True):
    __tablename__: str = "subscription"

    id: int = Field(primary_key=True, nullable=False)
    lemonSqueezyId: str = Field(unique=True, nullable=False)
    orderId: int = Field(nullable=False)
    name: str = Field(nullable=False)
    email: str = Field(nullable=False)
    status: str = Field(nullable=False)
    statusFormatted: str = Field(nullable=False)
    renewsAt: Optional[str] = Field(default=None)
    endsAt: Optional[str] = Field(default=None)
    trialEndsAt: Optional[str] = Field(default=None)
    price: str = Field(nullable=False)
    isUsageBased: bool = Field(default=False)
    isPaused: bool = Field(default=False)
    subscriptionItemId: int = Field(nullable=False)
    userId: str = Field(foreign_key="user.id", nullable=False)
    planId: int = Field(foreign_key="plan.id", nullable=False)


class UsageModel(SQLModel, table=True):
    __tablename__: str = "usage"

    id: int = Field(primary_key=True, nullable=False)
    userId: str = Field(foreign_key="user.id", nullable=False)
    planName: str = Field(nullable=False)
    executionCount: int = Field(default=0, nullable=False)
    updatedAt: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class UserModel(SQLModel, table=True):
    __tablename__: str = "user"

    id: str = Field(primary_key=True, nullable=False)
    name: str = Field(nullable=False)
    email: str = Field(nullable=False, unique=True)
    email_verified: bool = Field(default=False, nullable=False)
    image: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
