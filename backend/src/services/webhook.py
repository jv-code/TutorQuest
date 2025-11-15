"""
Webhook verification and handling utilities for Clerk/Svix webhooks
"""
from svix.webhooks import Webhook, WebhookVerificationError
from fastapi import HTTPException, Request
import json

try:
    from config import settings
except ModuleNotFoundError:
    from src.config import settings


async def verify_webhook_signature(request: Request, webhook_secret: str) -> dict:
    """
    Verify Svix webhook signature and return the parsed payload.

    Args:
        request: FastAPI Request object containing headers and body
        webhook_secret: Svix webhook secret for verification

    Returns:
        Parsed webhook payload as dictionary

    Raises:
        HTTPException: If signature verification fails
    """
    # Get required headers
    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")

    if not svix_id or not svix_timestamp or not svix_signature:
        raise HTTPException(
            status_code=400,
            detail="Missing required Svix headers (svix-id, svix-timestamp, svix-signature)"
        )

    # Get the raw body
    body = await request.body()

    # Create Svix webhook instance
    wh = Webhook(webhook_secret)

    try:
        # Verify and parse the payload
        payload = wh.verify(body, {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature
        })
        return payload
    except WebhookVerificationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Webhook signature verification failed: {str(e)}"
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON payload: {str(e)}"
        )


def extract_primary_email(user_data: dict) -> str | None:
    """
    Extract the primary email address from Clerk user data.

    Args:
        user_data: Clerk user data dictionary

    Returns:
        Primary email address or None if not found
    """
    email_addresses = user_data.get("email_addresses", [])
    primary_email_id = user_data.get("primary_email_address_id")

    if not email_addresses:
        return None

    # Find the primary email
    if primary_email_id:
        for email_obj in email_addresses:
            if email_obj.get("id") == primary_email_id:
                return email_obj.get("email_address")

    # Fallback to first email if primary not found
    if email_addresses:
        return email_addresses[0].get("email_address")

    return None
