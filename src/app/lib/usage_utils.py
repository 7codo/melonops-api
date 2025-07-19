import base64
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, cast

import requests
from sqlmodel import Session, select

from app.lib.caching_utils import cached_function
from app.lib.config import get_settings
from app.lib.constants import (
    executions_passport,
    mcps_passport,
    models_passport,
    tokens_passport,
)
from app.lib.db.database import engine
from app.lib.db.models import PlanModel, SubscriptionModel, UsageModel

settings = get_settings()

# Set up logger
logger = logging.getLogger(__name__)


def get_active_subscription_plan_name(
    user_id: str,
) -> Literal["free", "starter", "pro", "enterprise"]:
    logger.info(f"Getting active subscription plan for user_id={user_id}")
    """
    Get the plan name for the user's active subscription.

    Args:
        user_id (str): The ID of the user to get the subscription plan for.

    Returns:
        Optional[str]: The plan name if user has an active subscription, None otherwise.
    """
    with Session(engine) as session:
        # 1. Query all active subscriptions for the user
        subscriptions = session.exec(
            select(SubscriptionModel).where(
                SubscriptionModel.userId == user_id,
                SubscriptionModel.status.in_(["active", "trialing", "past_due"]),  # type: ignore
            )
        ).all()

        # 2. If no subscriptions, return 'basic'
        if len(subscriptions) == 0:
            logger.info(
                f"No active subscriptions for user_id={user_id}, returning 'basic'."
            )
            return "free"
        # 3. If more than one, raise error
        if len(subscriptions) > 1:
            logger.error(f"Multiple active subscriptions found for user_id={user_id}.")
            raise Exception(
                "Multiple active subscriptions were found for this user. Please contact support for assistance."
            )
        # 4. If exactly one, fetch the related plan by id and return its name
        plan_id = subscriptions[0].planId
        plan = session.exec(select(PlanModel).where(PlanModel.id == plan_id)).first()
        if not plan:
            logger.error(f"No plan found for plan_id={plan_id} and user_id={user_id}.")
            raise Exception(
                "No plan was found for the active subscription. Please contact support for further assistance."
            )
        logger.info(f"Returning plan name '{plan.name}' for user_id={user_id}.")
        return cast(Literal["pro", "enterprise"], plan.name)


@cached_function()
def check_allowed_model(*, llm: str, user_id: str) -> bool:
    logger.info(f"Checking if model '{llm}' is allowed for user_id={user_id}")
    """
    Check if the user is allowed to use the specified model based on their subscription plan.

    Args:
        llm (str): The model name to check
        user_id (str): The user ID to check permissions for

    Returns:
        bool: True if the user is allowed to use the model, False otherwise

    Raises:
        Exception: If the user is not allowed to use the model
    """
    active_plan_name = get_active_subscription_plan_name(user_id)
    if active_plan_name == "enterprise":
        logger.info(
            f"Enterprise plan detected for user_id={user_id}, all models allowed."
        )
        return True

    allowed_models = models_passport[active_plan_name]
    if llm not in allowed_models:
        logger.error(
            f"Model '{llm}' not allowed for user_id={user_id} with plan '{active_plan_name}'."
        )
        raise Exception(
            "This model is available on a higher-tier plan. Please consider upgrading to gain access."
        )
    logger.info(f"Model '{llm}' allowed for user_id={user_id}.")
    return True


def check_allowed_mcps(*, mcp_id: str, user_id: str) -> bool:
    logger.info(f"Checking if MCP '{mcp_id}' is allowed for user_id={user_id}")
    """
    Check if the user is allowed to use the specified MCPs based on their subscription plan.

    Args:
        mcp_id (str): The MCP ID to check
        user_id (str): The user ID to check permissions for

    Returns:
        bool: True if the user is allowed to use the MCPs, False otherwise

    Raises:
        Exception: If the user is not allowed to use the MCPs
    """
    active_plan_name = get_active_subscription_plan_name(user_id)
    if active_plan_name == "enterprise":
        logger.info(
            f"Enterprise plan detected for user_id={user_id}, all MCPs allowed."
        )
        return True
    allowed_mcps = mcps_passport[active_plan_name]

    if mcp_id not in allowed_mcps:
        logger.error(
            f"MCP '{mcp_id}' not allowed for user_id={user_id} with plan '{active_plan_name}'."
        )
        raise Exception(
            "This connector is available with a higher-tier plan. Please upgrade to unlock access."
        )
    logger.info(f"MCP '{mcp_id}' allowed for user_id={user_id}.")
    return True


def get_llm_usage_for_active_subscription_range(
    user_id: str, llm: str
) -> Dict[str, Any]:
    logger.info(f"Getting LLM usage for user_id={user_id}, llm={llm}")
    """
    Get LLM usage for the user's active subscription range (last 30 days from renewsAt/endsAt).

    Args:
        user_id (str): The user ID to check usage for
        llm (str): The LLM model name to check usage for

    Returns:
        dict: Usage data per model, grand totals, and date range
    """
    # 1. Get active subscription
    with Session(engine) as session:
        subscriptions = session.exec(
            select(SubscriptionModel).where(
                SubscriptionModel.userId == user_id,
                SubscriptionModel.status.in_(["active", "trialing", "past_due"]),  # type: ignore
            )
        ).all()
        if len(subscriptions) == 0:
            # Free plan: use now to 30 days ago
            ends_at = datetime.now(timezone.utc)
            start_date = ends_at - timedelta(days=30)
            logger.info(
                f"No active subscription for user_id={user_id}, using free plan window {start_date} to {ends_at}."
            )
        else:
            if len(subscriptions) > 1:
                logger.error(
                    f"Multiple active subscriptions found for user_id={user_id}."
                )
                raise Exception(
                    "Multiple active subscriptions found. Please contact support."
                )
            active_sub = subscriptions[0]
            ends_at = None
            if active_sub.renewsAt:
                ends_at = datetime.fromisoformat(active_sub.renewsAt)
            elif active_sub.endsAt:
                ends_at = datetime.fromisoformat(active_sub.endsAt)
            if not ends_at:
                logger.error(
                    f"Active subscription for user_id={user_id} has no renewsAt or endsAt date."
                )
                raise Exception("Active subscription has no renewsAt or endsAt date")
            start_date = ends_at - timedelta(days=30)
            logger.info(
                f"Active subscription window for user_id={user_id}: {start_date} to {ends_at}."
            )

    # 2. Fetch LLM usage using get_tokens_by_session_and_user
    tokens = get_tokens_by_session_and_user(
        user_id=user_id,
        selected_llm=llm,
        start_date=start_date.isoformat(),
        end_date=ends_at.isoformat(),
    )
    logger.info(
        f"Returning LLM usage for user_id={user_id}, llm={llm}, tokens={tokens}, start_date={start_date}, end_date={ends_at}."
    )
    return {
        "llm": llm,
        "tokens": tokens,
        "start_date": start_date.isoformat(),
        "end_date": ends_at.isoformat(),
    }


def check_llm_token_limit(user_id: str, llm: str):
    logger.info(f"Checking LLM token limit for user_id={user_id}, llm={llm}")
    # 1. Get usage
    usage = get_llm_usage_for_active_subscription_range(user_id, llm)
    tokens = usage["tokens"]
    # 2. Get plan
    plan = get_active_subscription_plan_name(user_id)
    if plan == "enterprise":
        logger.info(
            f"Enterprise plan detected for user_id={user_id}, unlimited tokens."
        )
        return True
    # 3. Get allowed tokens for this LLM and plan
    plan_limits = tokens_passport.get(plan, {})
    allowed_tokens = plan_limits.get(llm, None)
    if allowed_tokens is None:
        logger.error(
            f"No usage limits set for llm={llm}, plan={plan}, user_id={user_id}."
        )
        raise Exception(
            "No usage limits have been set for this LLM. If this issue persists, please contact support for assistance."
        )
    # 4. Check if within limit
    within_limit = tokens < allowed_tokens
    if not within_limit:
        logger.error(
            f"Token usage exceeded for user_id={user_id}, llm={llm}: {tokens}/{allowed_tokens}."
        )
        raise Exception(
            f"Your usage of {tokens} tokens for the model '{llm}' has reached the allowed limit of {allowed_tokens} tokens for your current plan ('{plan}'). "
            "Please consider upgrading your plan. If you have any questions, feel free to contact support."
        )
    logger.info(
        f"Token usage within limit for user_id={user_id}, llm={llm}: {tokens}/{allowed_tokens}."
    )


def check_usage_limit(
    user_id: str,
):
    logger.info(f"Checking usage limit for user_id={user_id}")
    """
    Get usage data for a user and plan.

    Args:
        user_id (str): The user ID to check usage for

    Returns:
        UsageModel | None: The usage record if found, else None
    """
    active_plan_name = get_active_subscription_plan_name(user_id)
    if active_plan_name == "enterprise":
        logger.info(
            f"Enterprise plan detected for user_id={user_id}, unlimited executions."
        )
        return True
    with Session(engine) as session:
        usage = session.exec(
            select(UsageModel).where(
                UsageModel.userId == user_id,
                UsageModel.planName == active_plan_name,
            )
        ).first()

    plan_name = active_plan_name
    limit = executions_passport.get(plan_name, None)
    if limit is None:
        logger.error(
            f"No execution limit found for the plan '{plan_name}'. Please check your subscription or contact support."
        )
        raise Exception(
            f"No execution limit found for the plan '{plan_name}'. Please check your subscription or contact support."
        )
    counts = usage.executionCount if usage is not None else 0
    if counts > limit:
        logger.error(
            f"Execution count exceeded for user_id={user_id}: {counts}/{limit}."
        )
        raise Exception(
            f"Your execution counts {counts} has reached the allowed limit of {limit} tokens for your current plan ('{plan_name}'). "
            "Please consider upgrading your plan. If you have any questions, feel free to contact support."
        )
    logger.info(
        f"Execution count within limit for user_id={user_id}: {counts}/{limit}."
    )


def get_tokens_by_session_and_user(
    *,
    user_id: str,
    session_id: str | None = None,
    agent_id: str | None = None,
    selected_llm: str | None = None,
    start_date: str,
    end_date: str,
) -> int:
    logger.info(
        f"Getting tokens for user_id={user_id}, session_id={session_id}, agent_id={agent_id}, selected_llm={selected_llm}, start_date={start_date}, end_date={end_date}."
    )
    auth = (settings.langfuse_public_key, settings.langfuse_secret_key)
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
    }
    filters = [
        {"column": "userId", "operator": "=", "value": user_id, "type": "string"},
    ]
    tags = []
    if session_id is not None:
        filters.append(
            {
                "column": "sessionId",
                "operator": "=",
                "value": session_id,
                "type": "string",
            }
        )

    if selected_llm is not None:
        tags.append(selected_llm)
    if agent_id is not None:
        tags.append(agent_id)

    if len(tags) > 0:
        filters.append(
            {
                "column": "tags",
                "operator": "any of",
                "value": tags,  # type: ignore
                "type": "arrayOptions",
            }
        )
    query = {
        "view": "traces",
        "metrics": [{"measure": "totalTokens", "aggregation": "sum"}],
        "filters": filters,
        "fromTimestamp": start_date,  # "2025-06-01T00:00:00Z"
        "toTimestamp": end_date,  # "2025-07-17T00:00:00Z"
    }
    resp = requests.get(
        f"{settings.langfuse_host}/api/public/metrics",
        params={"query": json.dumps(query)},
        headers=headers,
    )
    resp.raise_for_status()
    data = resp.json().get("data", [])
    tokens = int(data[0].get("sum_totalTokens", 0)) if data else 0
    logger.info(
        f"Returning tokens={tokens} for user_id={user_id}, session_id={session_id}, agent_id={agent_id}, selected_llm={selected_llm}."
    )
    return tokens
