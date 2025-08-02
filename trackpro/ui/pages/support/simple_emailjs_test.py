#!/usr/bin/env python3
"""Simple EmailJS test without TrackPro dependencies."""

import requests
import json
import os
from datetime import datetime


def test_emailjs_direct():
    """Test EmailJS directly with your credentials."""
    print("EmailJS Direct Test")
    print("=" * 50)
    
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), 'emailjs_config.json')
    
    if not os.path.exists(config_path):
        print("❌ Configuration file not found:", config_path)
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        service_id = config.get('service_id')
        template_id = config.get('template_id')
        public_key = config.get('public_key')
        
        print(f"✅ Configuration loaded:")
        print(f"   Service ID: {service_id}")
        print(f"   Template ID: {template_id}")
        print(f"   Public Key: {public_key[:10]}...")
        
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    # Test email data
    template_params = {
        'ticket_subject': 'EmailJS Integration Test',
        'ticket_priority': 'Medium',
        'ticket_category': 'General Question',
        'ticket_description': 'This is a test email to verify EmailJS integration is working correctly.',
        'user_email': 'test@trackpro.app',
        'user_name': 'TrackPro System Test',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    }
    
    # Prepare request
    payload = {
        'service_id': service_id,
        'template_id': template_id,
        'user_id': public_key,
        'template_params': template_params
    }
    
    print(f"\n📧 Sending test email...")
    print(f"   Subject: {template_params['ticket_subject']}")
    print(f"   Priority: {template_params['ticket_priority']}")
    print(f"   Category: {template_params['ticket_category']}")
    
    try:
        response = requests.post(
            'https://api.emailjs.com/api/v1.0/email/send',
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Email sent successfully!")
            print("   Check your support email inbox")
            print("   (Check spam folder if not found)")
            return True
        else:
            print(f"❌ Email failed - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


def main():
    """Main test function."""
    success = test_emailjs_direct()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 EmailJS integration is working!")
        print("   Your TrackPro support page is ready to send emails")
    else:
        print("❌ EmailJS test failed")
        print("   Please check your configuration and try again")
    
    print("\nNext steps:")
    print("1. If test succeeded: Start TrackPro and test the support page")
    print("2. If test failed: Check EmailJS dashboard and configuration")


if __name__ == "__main__":
    main()