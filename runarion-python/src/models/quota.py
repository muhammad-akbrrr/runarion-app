from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

# Not used for now
class WorkspaceQuota(BaseModel):
    id: int
    name: str
    slug: str
    cover_image_url: Optional[str]
    timezone: Optional[str]
    settings: Optional[Dict[str, Any]]
    permissions: Optional[Dict[str, Any]]
    cloud_storage: Optional[Dict[str, Any]]
    llm: Optional[Dict[str, Any]]
    billing_email: Optional[str]
    billing_name: Optional[str]
    billing_address: Optional[str]
    billing_city: Optional[str]
    billing_state: Optional[str]
    billing_postal_code: Optional[str]
    billing_country: Optional[str]
    billing_phone: Optional[str]
    billing_tax_id: Optional[str]
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    trial_ends_at: Optional[datetime]
    subscription_ends_at: Optional[datetime]
    is_active: bool = True
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]
    quota: Optional[int] = 0