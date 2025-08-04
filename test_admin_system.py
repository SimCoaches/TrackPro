#!/usr/bin/env python3
"""
Test script for the admin system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trackpro.auth.hierarchy_manager import hierarchy_manager
from trackpro.auth.user_manager import get_current_user, is_current_user_dev, is_current_user_moderator

def test_admin_system():
    """Test the admin system functionality."""
    print("Testing Admin System")
    print("=" * 40)
    
    # Test hardcoded admin
    print("Testing Hardcoded Admin:")
    print(f"  Hardcoded admin email: {hierarchy_manager.hardcoded_admin_email}")
    print(f"  Is hardcoded admin: {hierarchy_manager.is_hardcoded_admin('lawrence@simcoaches.com')}")
    print(f"  Is admin: {hierarchy_manager.is_admin('lawrence@simcoaches.com')}")
    print()
    
    # Test dynamic admin functions
    print("Testing Dynamic Admin Functions:")
    print(f"  Current dynamic admins: {hierarchy_manager.get_dynamic_admin_emails()}")
    print(f"  All admin emails: {hierarchy_manager.get_all_admin_emails()}")
    print()
    
    # Test current user
    current_user = get_current_user()
    if current_user:
        print(f"Current User: {current_user.email}")
        print(f"Is Dev: {is_current_user_dev()}")
        print(f"Is Moderator: {is_current_user_moderator()}")
        print(f"Is Admin: {hierarchy_manager.is_admin(current_user.email)}")
        print()
        
        # Test permission checks with email
        print("Testing Permission Checks with Email:")
        print(f"  Is Dev (with email): {hierarchy_manager.is_user_dev(current_user.id, current_user.email)}")
        print(f"  Is Moderator (with email): {hierarchy_manager.is_user_moderator(current_user.id, current_user.email)}")
        print(f"  Has 'user_management' permission: {hierarchy_manager.check_permission(current_user.id, 'user_management', current_user.email)}")
        print()
        
        # Test adding a dynamic admin (only if current user is admin)
        if hierarchy_manager.is_admin(current_user.email):
            print("Testing Dynamic Admin Management:")
            test_email = "test@example.com"
            
            # Try to add test admin
            result = hierarchy_manager.add_dynamic_admin(test_email, current_user.email)
            print(f"  Add admin result: {result}")
            
            # Check if it was added
            print(f"  Dynamic admins after add: {hierarchy_manager.get_dynamic_admin_emails()}")
            
            # Try to remove test admin
            result = hierarchy_manager.remove_dynamic_admin(test_email, current_user.email)
            print(f"  Remove admin result: {result}")
            
            print(f"  Dynamic admins after remove: {hierarchy_manager.get_dynamic_admin_emails()}")
        else:
            print("Current user is not admin - skipping dynamic admin tests")
    
    print("\n✓ Admin system test completed!")

if __name__ == "__main__":
    test_admin_system() 