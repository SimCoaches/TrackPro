#!/usr/bin/env python3
"""
Test script to verify community page loading optimizations.
"""

import time
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_community_page_loading():
    """Test the community page loading performance."""
    print("🧪 Testing Community Page Loading Optimizations")
    print("=" * 50)
    
    try:
        from PyQt6.QtWidgets import QApplication
        from trackpro.ui.pages.community.community_page import CommunityPage
        
        # Create QApplication
        app = QApplication(sys.argv)
        
        print("📱 Creating CommunityPage instance...")
        start_time = time.time()
        
        # Create the community page
        community_page = CommunityPage()
        
        creation_time = time.time() - start_time
        print(f"✅ CommunityPage created in {creation_time:.2f} seconds")
        
        # Test activation time
        print("🔄 Testing page activation...")
        activation_start = time.time()
        
        # Simulate page activation
        community_page.on_page_activated()
        
        activation_time = time.time() - activation_start
        print(f"✅ Page activation completed in {activation_time:.2f} seconds")
        
        print(f"\n📊 Performance Summary:")
        print(f"   • Page creation: {creation_time:.2f}s")
        print(f"   • Page activation: {activation_time:.2f}s")
        print(f"   • Total time: {creation_time + activation_time:.2f}s")
        
        if activation_time < 1.0:
            print("✅ SUCCESS: Community page loads quickly!")
        else:
            print("⚠️  WARNING: Community page still takes time to activate")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing community page: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_community_page_loading()
    sys.exit(0 if success else 1) 