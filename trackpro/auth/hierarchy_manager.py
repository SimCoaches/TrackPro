"""
User Hierarchy Manager for TrackPro.

Manages user hierarchy levels, roles, and permissions.
"""

import logging
from typing import Optional, Dict, Any, List
import re
from enum import Enum
from dataclasses import dataclass
from ..database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class HierarchyLevel(Enum):
    """User hierarchy levels."""
    TEAM = "TEAM"
    SPONSORED_DRIVERS = "SPONSORED_DRIVERS"
    DRIVERS = "DRIVERS"
    PADDOCK = "PADDOCK"

@dataclass
class UserHierarchy:
    """User hierarchy information."""
    user_id: str
    hierarchy_level: HierarchyLevel
    is_dev: bool = False
    is_moderator: bool = False
    dev_permissions: Dict[str, Any] = None
    moderator_permissions: Dict[str, Any] = None
    assigned_by: Optional[str] = None
    assigned_at: Optional[str] = None

class HierarchyManager:
    """Manages user hierarchy and permissions."""
    
    def __init__(self):
        """Initialize the hierarchy manager."""
        self.supabase = get_supabase_client()

    # ---------- Helpers ----------
    def _looks_like_uuid(self, value: str) -> bool:
        try:
            import uuid
            uuid.UUID(str(value))
            return True
        except Exception:
            return False

    def _resolve_user_id(self, identifier: str) -> Optional[str]:
        """Resolve a user identifier which may be a UUID or an email to a UUID.

        This makes callers tolerant to mistakenly passing an email address where a UUID is expected.
        """
        try:
            if not identifier:
                return None
            # If it's already a UUID, return as-is
            if self._looks_like_uuid(identifier):
                return identifier
            # If it looks like an email, try to map via user_profiles
            if "@" in identifier:
                try:
                    resp = self.supabase.from_("user_profiles").select("user_id").eq("email", identifier).single().execute()
                    if resp and getattr(resp, 'data', None) and resp.data.get("user_id"):
                        return resp.data["user_id"]
                except Exception:
                    pass
            return None
        except Exception:
            return None

    def is_simcoaches_email(self, email: str) -> bool:
        """Check if email belongs to the simcoaches.com domain."""
        try:
            return bool(email) and email.lower().endswith("@simcoaches.com")
        except Exception:
            return False
    
    def is_admin(self, user_id: str) -> bool:
        """Check if user has dev permissions, making them an admin.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user is a dev, False otherwise
        """
        return self.is_user_dev(user_id)

    def get_user_hierarchy(self, user_id: str) -> Optional[UserHierarchy]:
        """Get user hierarchy information.
        
        Args:
            user_id: User ID
            
        Returns:
            UserHierarchy object or None
        """
        try:
            # Add timeout to prevent hanging during startup
            import concurrent.futures
            import threading
            
            def fetch_hierarchy():
                try:
                    # Gracefully accept an email by resolving it to a UUID
                    resolved_id = self._resolve_user_id(user_id)
                    lookup_id = resolved_id or user_id
                    response = self.supabase.table("user_hierarchy").select("*").eq("user_id", lookup_id).single().execute()
                    return response.data if response.data else None
                except Exception as e:
                    logger.error(f"Error fetching user hierarchy: {e}")
                    return None
            
            # Use a timeout to prevent hanging
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(fetch_hierarchy)
                try:
                    data = future.result(timeout=3.0)  # 3 second timeout
                except concurrent.futures.TimeoutError:
                    logger.warning(f"Timeout getting user hierarchy for {user_id}")
                    return None
                except Exception as e:
                    logger.error(f"Error getting user hierarchy: {e}")
                    return None
            
            if data:
                return UserHierarchy(
                    user_id=data['user_id'],
                    hierarchy_level=HierarchyLevel(data['hierarchy_level']),
                    is_dev=data.get('is_dev', False),
                    is_moderator=data.get('is_moderator', False),
                    dev_permissions=data.get('dev_permissions', {}),
                    moderator_permissions=data.get('moderator_permissions', {}),
                    assigned_by=data.get('assigned_by'),
                    assigned_at=data.get('assigned_at')
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting user hierarchy: {e}")
            return None
    
    def is_user_dev(self, user_id: str, email: Optional[str] = None) -> bool:
        """Check if user has dev permissions.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user is a dev, False otherwise
        """
        # Accept email for backward compatibility
        if email and not self._looks_like_uuid(user_id):
            resolved = self._resolve_user_id(email)
            user_id = resolved or user_id
        hierarchy = self.get_user_hierarchy(user_id)
        return hierarchy.is_dev if hierarchy else False
    
    def is_user_moderator(self, user_id: str, email: Optional[str] = None) -> bool:
        """Check if user has moderator permissions.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user is a moderator, False otherwise
        """
        if email and not self._looks_like_uuid(user_id):
            resolved = self._resolve_user_id(email)
            user_id = resolved or user_id
        hierarchy = self.get_user_hierarchy(user_id)
        return hierarchy.is_moderator if hierarchy else False
    
    def get_user_level(self, user_id: str, email: Optional[str] = None) -> HierarchyLevel:
        """Get user's hierarchy level.
        
        Args:
            user_id: User ID
            
        Returns:
            User's hierarchy level (defaults to PADDOCK)
        """
        if email and not self._looks_like_uuid(user_id):
            resolved = self._resolve_user_id(email)
            user_id = resolved or user_id
        hierarchy = self.get_user_hierarchy(user_id)
        return hierarchy.hierarchy_level if hierarchy else HierarchyLevel.PADDOCK
    
    def can_modify_hierarchy(self, modifier_id: str, target_id: str) -> bool:
        """Check if a user can modify another user's hierarchy.
        
        Args:
            modifier_id: ID of user making the modification
            target_id: ID of user being modified
            
        Returns:
            True if modification is allowed, False otherwise
        """
        modifier_hierarchy = self.get_user_hierarchy(modifier_id)
        if not modifier_hierarchy:
            return False

        if modifier_hierarchy.is_dev:
            return True
        
        # Moderators can modify users below them in hierarchy
        if modifier_hierarchy.is_moderator:
            modifier_level = modifier_hierarchy.hierarchy_level
            target_level = self.get_user_level(target_id)
            
            # Define hierarchy order (higher index = higher level)
            hierarchy_order = {
                HierarchyLevel.TEAM: 4,
                HierarchyLevel.SPONSORED_DRIVERS: 3,
                HierarchyLevel.DRIVERS: 2,
                HierarchyLevel.PADDOCK: 1
            }
            
            return hierarchy_order.get(modifier_level, 0) > hierarchy_order.get(target_level, 0)
        
        return False
    
    def update_user_hierarchy(self, target_id: str, modifier_id: str, 
                            hierarchy_level: HierarchyLevel, is_dev: bool = False, 
                            is_moderator: bool = False, dev_permissions: Dict[str, Any] = None,
                            moderator_permissions: Dict[str, Any] = None) -> Dict[str, Any]:
        """Update user hierarchy.
        
        Args:
            target_id: ID of user to update
            modifier_id: ID of user making the change
            hierarchy_level: New hierarchy level
            is_dev: Whether user should have dev permissions
            is_moderator: Whether user should have moderator permissions
            dev_permissions: Specific dev permissions
            moderator_permissions: Specific moderator permissions
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Check permissions
            if not self.can_modify_hierarchy(modifier_id, target_id):
                return {"success": False, "message": "Insufficient permissions to modify user hierarchy"}
            
            # Prepare update data
            update_data = {
                "hierarchy_level": hierarchy_level.value,
                "is_dev": is_dev,
                "is_moderator": is_moderator,
                "assigned_by": modifier_id,
                "updated_at": "now()"
            }
            
            if dev_permissions is not None:
                update_data["dev_permissions"] = dev_permissions
            
            if moderator_permissions is not None:
                update_data["moderator_permissions"] = moderator_permissions
            
            # Update hierarchy
            response = self.supabase.table("user_hierarchy").update(update_data).eq("user_id", target_id).execute()
            
            if response.data:
                logger.info(f"User {target_id} hierarchy updated by {modifier_id}")
                return {"success": True, "message": "User hierarchy updated successfully"}
            
            return {"success": False, "message": "Failed to update user hierarchy"}
            
        except Exception as e:
            logger.error(f"Error updating user hierarchy: {e}")
            return {"success": False, "message": f"Failed to update user hierarchy: {e}"}
    
    def get_users_by_level(self, level: HierarchyLevel, limit: int = 100) -> List[UserHierarchy]:
        """Get all users at a specific hierarchy level.
        
        Args:
            level: Hierarchy level to search for
            limit: Maximum number of users to return
            
        Returns:
            List of UserHierarchy objects
        """
        try:
            response = self.supabase.table("user_hierarchy").select("*").eq("hierarchy_level", level.value).limit(limit).execute()
            
            users = []
            for data in response.data or []:
                users.append(UserHierarchy(
                    user_id=data['user_id'],
                    hierarchy_level=HierarchyLevel(data['hierarchy_level']),
                    is_dev=data.get('is_dev', False),
                    is_moderator=data.get('is_moderator', False),
                    dev_permissions=data.get('dev_permissions', {}),
                    moderator_permissions=data.get('moderator_permissions', {}),
                    assigned_by=data.get('assigned_by'),
                    assigned_at=data.get('assigned_at')
                ))
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting users by level: {e}")
            return []
    
    def get_dev_users(self) -> List[UserHierarchy]:
        """Get all users with dev permissions.
        
        Returns:
            List of dev users
        """
        try:
            response = self.supabase.table("user_hierarchy").select("*").eq("is_dev", True).execute()
            
            users = []
            for data in response.data or []:
                users.append(UserHierarchy(
                    user_id=data['user_id'],
                    hierarchy_level=HierarchyLevel(data['hierarchy_level']),
                    is_dev=data.get('is_dev', False),
                    is_moderator=data.get('is_moderator', False),
                    dev_permissions=data.get('dev_permissions', {}),
                    moderator_permissions=data.get('moderator_permissions', {}),
                    assigned_by=data.get('assigned_by'),
                    assigned_at=data.get('assigned_at')
                ))
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting dev users: {e}")
            return []
    
    def get_moderator_users(self) -> List[UserHierarchy]:
        """Get all users with moderator permissions.
        
        Returns:
            List of moderator users
        """
        try:
            response = self.supabase.table("user_hierarchy").select("*").eq("is_moderator", True).execute()
            
            users = []
            for data in response.data or []:
                users.append(UserHierarchy(
                    user_id=data['user_id'],
                    hierarchy_level=HierarchyLevel(data['hierarchy_level']),
                    is_dev=data.get('is_dev', False),
                    is_moderator=data.get('is_moderator', False),
                    dev_permissions=data.get('dev_permissions', {}),
                    moderator_permissions=data.get('moderator_permissions', {}),
                    assigned_by=data.get('assigned_by'),
                    assigned_at=data.get('assigned_at')
                ))
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting moderator users: {e}")
            return []
    
    def check_permission(self, user_id: str, permission: str, email: Optional[str] = None) -> bool:
        """Check if user has a specific permission.
        
        Args:
            user_id: User ID
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        if email and not self._looks_like_uuid(user_id):
            resolved = self._resolve_user_id(email)
            user_id = resolved or user_id
        hierarchy = self.get_user_hierarchy(user_id)
        if not hierarchy:
            return False
        
        # Dev users have all permissions
        if hierarchy.is_dev and hierarchy.dev_permissions.get('all_permissions', False):
            return True
        
        # Check specific dev permissions
        if hierarchy.is_dev and hierarchy.dev_permissions.get(permission, False):
            return True
        
        # Check moderator permissions
        if hierarchy.is_moderator and hierarchy.moderator_permissions.get(permission, False):
            return True
        
        return False

    # ---------- Admin emails (dynamic) ----------
    def get_dynamic_admin_emails(self) -> List[str]:
        """Return emails of users with dynamic admin (is_dev=True) permissions."""
        try:
            resp = self.supabase.table("user_hierarchy").select("user_id").eq("is_dev", True).execute()
            user_ids = [row.get("user_id") for row in (getattr(resp, 'data', None) or []) if row.get("user_id")]
            emails: List[str] = []
            for uid in user_ids:
                try:
                    p = self.supabase.from_("user_profiles").select("email").eq("user_id", uid).single().execute()
                    if p and getattr(p, 'data', None) and p.data.get("email"):
                        emails.append(p.data["email"].lower())
                except Exception:
                    continue
            # Deduplicate
            return sorted(list({e for e in emails if e}))
        except Exception as e:
            logger.error(f"Error getting dynamic admin emails: {e}")
            return []

    def get_all_admin_emails(self) -> List[str]:
        """Return the union of hardcoded and dynamic admin emails."""
        try:
            hardcoded = ["lawrence@simcoaches.com"]
            dynamic_list = self.get_dynamic_admin_emails()
            combined = {e.lower() for e in (hardcoded + dynamic_list) if e}
            return sorted(list(combined))
        except Exception as e:
            logger.error(f"Error getting all admin emails: {e}")
            return ["lawrence@simcoaches.com"]

    def add_dynamic_admin(self, email: str, added_by_email: Optional[str] = None) -> Dict[str, Any]:
        """Grant dynamic admin (dev) permissions to a user by email."""
        try:
            if not email or "@" not in email:
                return {"success": False, "message": "Invalid email"}
            # Only hardcoded admins can modify admin list
            if not (added_by_email and self.is_simcoaches_email(added_by_email)):
                return {"success": False, "message": "Only Sim Coaches team members can modify admins"}
            uid = self._resolve_user_id(email)
            if not uid:
                return {"success": False, "message": "User not found for the provided email"}
            # Try update first
            try:
                upd = self.supabase.table("user_hierarchy").update({
                    "is_dev": True,
                    "assigned_by": added_by_email,
                    "updated_at": "now()"
                }).eq("user_id", uid).execute()
                if getattr(upd, 'data', None):
                    return {"success": True, "message": f"Granted admin to {email}"}
            except Exception:
                pass
            # Insert if no existing row
            try:
                ins = self.supabase.table("user_hierarchy").insert({
                    "user_id": uid,
                    "hierarchy_level": HierarchyLevel.TEAM.value,
                    "is_dev": True,
                    "is_moderator": True,
                    "assigned_by": added_by_email
                }).execute()
                if getattr(ins, 'data', None):
                    return {"success": True, "message": f"Granted admin to {email}"}
            except Exception as e:
                logger.error(f"Error inserting dynamic admin: {e}")
            return {"success": False, "message": "Failed to grant admin"}
        except Exception as e:
            logger.error(f"Error adding dynamic admin: {e}")
            return {"success": False, "message": str(e)}

    def remove_dynamic_admin(self, email: str, removed_by_email: Optional[str] = None) -> Dict[str, Any]:
        """Revoke dynamic admin (dev) permissions from a user by email."""
        try:
            if not email or "@" not in email:
                return {"success": False, "message": "Invalid email"}
            if not (removed_by_email and self.is_simcoaches_email(removed_by_email)):
                return {"success": False, "message": "Only Sim Coaches team members can modify admins"}
            uid = self._resolve_user_id(email)
            if not uid:
                return {"success": False, "message": "User not found for the provided email"}
            upd = self.supabase.table("user_hierarchy").update({
                "is_dev": False,
                "updated_at": "now()"
            }).eq("user_id", uid).execute()
            if getattr(upd, 'data', None):
                return {"success": True, "message": f"Removed admin from {email}"}
            return {"success": False, "message": "Failed to remove admin"}
        except Exception as e:
            logger.error(f"Error removing dynamic admin: {e}")
            return {"success": False, "message": str(e)}

# Create global instance
hierarchy_manager = HierarchyManager() 