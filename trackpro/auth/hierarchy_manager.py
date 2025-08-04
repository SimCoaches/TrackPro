"""
User Hierarchy Manager for TrackPro.

Manages user hierarchy levels, roles, and permissions.
"""

import logging
from typing import Optional, Dict, Any, List
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
        # Hardcoded admin email - this user always has full admin access
        self.hardcoded_admin_email = "lawrence@simcoaches.com"
        # Dynamic admin emails - these can be modified without updates
        self.dynamic_admin_emails = set()
        self._load_dynamic_admins()
    
    def _load_dynamic_admins(self):
        """Load dynamic admin emails from database."""
        try:
            # Create admin_emails table if it doesn't exist
            self._ensure_admin_emails_table()
            
            # Load dynamic admin emails
            response = self.supabase.table("admin_emails").select("email").execute()
            if response.data:
                self.dynamic_admin_emails = {row['email'] for row in response.data}
            else:
                self.dynamic_admin_emails = set()
                
        except Exception as e:
            logger.error(f"Error loading dynamic admin emails: {e}")
            self.dynamic_admin_emails = set()
    
    def _ensure_admin_emails_table(self):
        """Ensure the admin_emails table exists."""
        try:
            # Try to create the table if it doesn't exist
            # We'll use a simple approach - just try to query the table
            # If it doesn't exist, we'll handle it gracefully
            response = self.supabase.table("admin_emails").select("id").limit(1).execute()
            # If we get here, the table exists
            return True
        except Exception as e:
            logger.warning(f"Admin emails table may not exist: {e}")
            # The table will be created by the migration we already applied
            return False
    
    def is_hardcoded_admin(self, email: str) -> bool:
        """Check if email is the hardcoded admin.
        
        Args:
            email: Email to check
            
        Returns:
            True if hardcoded admin, False otherwise
        """
        return email.lower() == self.hardcoded_admin_email.lower()
    
    def is_dynamic_admin(self, email: str) -> bool:
        """Check if email is a dynamic admin.
        
        Args:
            email: Email to check
            
        Returns:
            True if dynamic admin, False otherwise
        """
        return email.lower() in {admin.lower() for admin in self.dynamic_admin_emails}
    
    def is_admin(self, email: str) -> bool:
        """Check if email has admin access (hardcoded or dynamic).
        
        Args:
            email: Email to check
            
        Returns:
            True if admin, False otherwise
        """
        return self.is_hardcoded_admin(email) or self.is_dynamic_admin(email)
    
    def add_dynamic_admin(self, email: str, added_by: str = None) -> Dict[str, Any]:
        """Add a dynamic admin email.
        
        Args:
            email: Email to add as admin
            added_by: Email of user adding the admin
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Only hardcoded admin can add dynamic admins
            if not self.is_admin(added_by):
                return {"success": False, "message": "Only admins can add other admins"}
            
            # Add to database
            response = self.supabase.table("admin_emails").insert({
                "email": email.lower(),
                "added_by": added_by
            }).execute()
            
            if response.data:
                # Reload dynamic admins
                self._load_dynamic_admins()
                logger.info(f"Added dynamic admin: {email}")
                return {"success": True, "message": f"Added {email} as admin"}
            
            return {"success": False, "message": "Failed to add admin"}
            
        except Exception as e:
            logger.error(f"Error adding dynamic admin: {e}")
            return {"success": False, "message": f"Failed to add admin: {e}"}
    
    def remove_dynamic_admin(self, email: str, removed_by: str = None) -> Dict[str, Any]:
        """Remove a dynamic admin email.
        
        Args:
            email: Email to remove from admin
            removed_by: Email of user removing the admin
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Only hardcoded admin can remove dynamic admins
            if not self.is_admin(removed_by):
                return {"success": False, "message": "Only admins can remove other admins"}
            
            # Cannot remove hardcoded admin
            if self.is_hardcoded_admin(email):
                return {"success": False, "message": "Cannot remove hardcoded admin"}
            
            # Remove from database
            response = self.supabase.table("admin_emails").delete().eq("email", email.lower()).execute()
            
            if response.data:
                # Reload dynamic admins
                self._load_dynamic_admins()
                logger.info(f"Removed dynamic admin: {email}")
                return {"success": True, "message": f"Removed {email} from admins"}
            
            return {"success": False, "message": "Failed to remove admin"}
            
        except Exception as e:
            logger.error(f"Error removing dynamic admin: {e}")
            return {"success": False, "message": f"Failed to remove admin: {e}"}
    
    def get_all_admin_emails(self) -> List[str]:
        """Get all admin emails (hardcoded + dynamic).
        
        Returns:
            List of admin emails
        """
        admins = [self.hardcoded_admin_email]
        admins.extend(list(self.dynamic_admin_emails))
        return admins
    
    def get_dynamic_admin_emails(self) -> List[str]:
        """Get only dynamic admin emails.
        
        Returns:
            List of dynamic admin emails
        """
        return list(self.dynamic_admin_emails)
    
    def get_user_hierarchy(self, user_id: str) -> Optional[UserHierarchy]:
        """Get user hierarchy information.
        
        Args:
            user_id: User ID
            
        Returns:
            UserHierarchy object or None
        """
        try:
            response = self.supabase.table("user_hierarchy").select("*").eq("user_id", user_id).single().execute()
            
            if response.data:
                data = response.data
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
    
    def is_user_dev(self, user_id: str, user_email: str = None) -> bool:
        """Check if user has dev permissions.
        
        Args:
            user_id: User ID
            user_email: User email (for admin checks)
            
        Returns:
            True if user is a dev, False otherwise
        """
        # Check if user is admin (hardcoded or dynamic)
        if user_email and self.is_admin(user_email):
            return True
        
        # Check database hierarchy
        hierarchy = self.get_user_hierarchy(user_id)
        return hierarchy.is_dev if hierarchy else False
    
    def is_user_moderator(self, user_id: str, user_email: str = None) -> bool:
        """Check if user has moderator permissions.
        
        Args:
            user_id: User ID
            user_email: User email (for admin checks)
            
        Returns:
            True if user is a moderator, False otherwise
        """
        # Check if user is admin (hardcoded or dynamic)
        if user_email and self.is_admin(user_email):
            return True
        
        # Check database hierarchy
        hierarchy = self.get_user_hierarchy(user_id)
        return hierarchy.is_moderator if hierarchy else False
    
    def get_user_level(self, user_id: str) -> HierarchyLevel:
        """Get user's hierarchy level.
        
        Args:
            user_id: User ID
            
        Returns:
            User's hierarchy level (defaults to PADDOCK)
        """
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
        # Dev users can modify anyone
        if self.is_user_dev(modifier_id):
            return True
        
        # Moderators can modify users below them in hierarchy
        if self.is_user_moderator(modifier_id):
            modifier_level = self.get_user_level(modifier_id)
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
    
    def check_permission(self, user_id: str, permission: str, user_email: str = None) -> bool:
        """Check if user has a specific permission.
        
        Args:
            user_id: User ID
            permission: Permission to check
            user_email: User email (for admin checks)
            
        Returns:
            True if user has permission, False otherwise
        """
        # Check if user is admin (hardcoded or dynamic)
        if user_email and self.is_admin(user_email):
            return True
        
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

# Create global instance
hierarchy_manager = HierarchyManager() 