#!/usr/bin/env python3
"""Test script for EmailJS integration."""

import sys
import os
import json

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

from trackpro.ui.pages.support.emailjs_client import EmailJSConfig, EmailJSClient


def test_emailjs_config():
    """Test EmailJS configuration loading."""
    print("Testing EmailJS Configuration...")
    
    config = EmailJSConfig()
    
    if config.is_configured():
        print("✅ EmailJS is configured")
        print(f"   Service ID: {config.service_id}")
        print(f"   Template ID: {config.template_id}")
        print(f"   Public Key: {config.public_key[:10]}..." if config.public_key else "None")
        return config
    else:
        print("❌ EmailJS is not configured")
        print("   Please set up emailjs_config.json or environment variables")
        return None


def test_emailjs_client(config):
    """Test EmailJS client functionality."""
    if not config:
        print("Skipping client test - no configuration")
        return
    
    print("\nTesting EmailJS Client...")
    
    client = config.get_client()
    if not client:
        print("❌ Failed to create EmailJS client")
        return
    
    print("✅ EmailJS client created successfully")
    
    # Test connection
    print("\nTesting EmailJS connection...")
    try:
        success = client.test_connection()
        if success:
            print("✅ EmailJS test email sent successfully!")
            print("   Check your support email for the test message")
        else:
            print("❌ EmailJS test email failed")
    except Exception as e:
        print(f"❌ EmailJS connection test error: {e}")


def create_sample_config():
    """Create a sample configuration file."""
    print("\nCreating sample configuration...")
    
    config_path = os.path.join(os.path.dirname(__file__), 'emailjs_config.json')
    template_path = os.path.join(os.path.dirname(__file__), 'emailjs_config.json.template')
    
    if os.path.exists(config_path):
        print(f"   Configuration file already exists: {config_path}")
        return
    
    if os.path.exists(template_path):
        # Copy template to config
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        with open(config_path, 'w') as f:
            f.write(template_content)
        
        print(f"✅ Sample configuration created: {config_path}")
        print("   Please edit this file with your actual EmailJS credentials")
    else:
        # Create basic template
        sample_config = {
            "service_id": "your_emailjs_service_id",
            "template_id": "your_emailjs_template_id", 
            "public_key": "your_emailjs_public_key"
        }
        
        with open(config_path, 'w') as f:
            json.dump(sample_config, f, indent=2)
        
        print(f"✅ Basic configuration created: {config_path}")
        print("   Please edit this file with your actual EmailJS credentials")


def main():
    """Main test function."""
    print("EmailJS Integration Test")
    print("=" * 50)
    
    # Test configuration
    config = test_emailjs_config()
    
    # Test client if configured
    if config and config.is_configured():
        test_emailjs_client(config)
    else:
        create_sample_config()
        print("\nTo complete setup:")
        print("1. Edit trackpro/ui/pages/support/emailjs_config.json")
        print("2. Add your EmailJS service_id, template_id, and public_key")
        print("3. Run this test again to verify the configuration")
    
    print("\n" + "=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    main()