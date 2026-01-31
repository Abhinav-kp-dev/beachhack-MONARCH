from typing import Optional, Dict, Any
import hashlib


class IdentityService:
    """Service for customer identity resolution"""
    
    async def resolve_identity(
        self, 
        email: Optional[str] = None,
        phone: Optional[str] = None,
        customer_id: Optional[str] = None
    ) -> str:
        """Resolve customer identity from various identifiers"""
        if customer_id:
            return customer_id
        
        # Generate consistent ID from email or phone
        if email:
            return f"cust_{hashlib.md5(email.encode()).hexdigest()[:12]}"
        
        if phone:
            return f"cust_{hashlib.md5(phone.encode()).hexdigest()[:12]}"
        
        # Generate random ID for anonymous customers
        import uuid
        return f"cust_{str(uuid.uuid4())[:12]}"
    
    async def merge_identities(
        self, 
        primary_id: str, 
        secondary_id: str
    ) -> Dict[str, Any]:
        """Merge two customer identities"""
        return {
            "merged": True,
            "primary_id": primary_id,
            "secondary_id": secondary_id,
            "message": f"Merged {secondary_id} into {primary_id}"
        }


identity_service = IdentityService()
