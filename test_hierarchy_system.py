#!/usr/bin/env python3
"""
Test script for the user hierarchy system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trackpro.auth.hierarchy_manager import hierarchy_manager, HierarchyLevel
from trackpro.auth.user_manager import get_current_user, is_current_user_dev, is_current_user_moderator

def test_hierarchy_system():
    """Test the hierarchy system functionality."""
    print("Testing User Hierarchy System")
    print("=" * 40)
    
    # Test current user
    current_user = get_current_user()
    if current_user:
        print(f"Current User: {current_user.email}")
        print(f"Hierarchy Level: {current_user.hierarchy_level}")
        print(f"Is Dev: {current_user.is_dev}")
        print(f"Is Moderator: {current_user.is_moderator}")
        print()
        
        # Test hierarchy manager functions
        print("Testing Hierarchy Manager Functions:")
        print("-" * 30)
        
        # Test getting user hierarchy
        hierarchy = hierarchy_manager.get_user_hierarchy(current_user.id)
        if hierarchy:
            print(f"✓ User hierarchy retrieved successfully")
            print(f"  Level: {hierarchy.hierarchy_level.value}")
            print(f"  Dev: {hierarchy.is_dev}")
            print(f"  Moderator: {hierarchy.is_moderator}")
        else:
            print("✗ Failed to get user hierarchy")
        
        # Test permission checks
        print(f"\nPermission Checks:")
        print(f"  Is Dev: {is_current_user_dev()}")
        print(f"  Is Moderator: {is_current_user_moderator()}")
        print(f"  Has 'user_management' permission: {hierarchy_manager.check_permission(current_user.id, 'user_management')}")
        print(f"  Has 'content_moderation' permission: {hierarchy_manager.check_permission(current_user.id, 'content_moderation')}")
        
        # Test hierarchy levels
        print(f"\nHierarchy Levels:")
        for level in HierarchyLevel:
            print(f"  {level.value}")
        
        print("\n✓ Hierarchy system test completed successfully!")
    else:
        print("✗ No current user found - please log in first")

if __name__ == "__main__":
    test_hierarchy_system() 