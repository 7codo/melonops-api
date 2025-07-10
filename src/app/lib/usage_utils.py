from typing import Literal, cast

from sqlmodel import Session, select

from app.lib.caching_utils import cached_function
from app.lib.constants import mcps_passport, models_passport
from app.lib.db.database import engine
from app.lib.db.models import PlanModel, SubscriptionModel


@cached_function()
def get_active_subscription_plan_name(
    user_id: str,
) -> Literal["basic", "pro", "enterprise"]:
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
            return "basic"
        # 3. If more than one, raise error
        if len(subscriptions) > 1:
            raise Exception("Multiple active subscriptions found for user.")
        # 4. If exactly one, fetch the related plan by id and return its name
        plan_id = subscriptions[0].planId
        plan = session.exec(select(PlanModel).where(PlanModel.id == plan_id)).first()
        if not plan:
            raise Exception("Plan not found for active subscription.")
        return cast(Literal["pro", "enterprise"], plan.name)


@cached_function()
def check_allowed_model(*, llm: str, user_id: str) -> bool:
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

    allowed_models = models_passport[active_plan_name]
    if llm not in allowed_models:
        raise Exception("Please upgrade to access this model.")
    return True


@cached_function()
def check_allowed_mcps(*, mcp_id: str, user_id: str) -> bool:
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
    allowed_mcps = mcps_passport[active_plan_name]

    if mcp_id not in allowed_mcps:
        raise Exception("Please upgrade to access this MCP.")

    return True
