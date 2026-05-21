from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from src.models.request import CallerInfo


class QuotaCaller(CallerInfo):
    """
    Caller information specifically for quota management and API usage tracking.
    Used by the generation engine to track API calls and manage quotas.
    Inherits all fields from CallerInfo for full compatibility with providers.
    """
    
    @classmethod
    def from_request_data(
        cls, 
        user_id: int, 
        workspace_id: str, 
        project_id: str, 
        session_id: str,
        api_keys: Optional[Dict[str, Optional[str]]] = None
    ) -> "QuotaCaller":
        """
        Create QuotaCaller from request data, handling type conversions.
        
        Args:
            user_id: User ID (will be converted to string)
            workspace_id: Workspace UUID
            project_id: Project UUID  
            session_id: Session UUID
            api_keys: Optional API keys dictionary
            
        Returns:
            QuotaCaller instance
        """
        return cls(
            user_id=str(user_id),  # Convert int to str
            workspace_id=workspace_id,
            project_id=project_id, 
            session_id=session_id,
            api_keys=api_keys or {}
        )


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