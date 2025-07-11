#!/usr/bin/env python3
"""
Minimal test for secure session encryption functionality.
"""

import os
import sys
import json
import tempfile
import logging
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import secrets

# Suppress logging
logging.disable(logging.CRITICAL)

def test_basic_encryption():
    """Test basic encryption functionality."""
    print("🔐 TESTING BASIC ENCRYPTION")
    print("="*40)
    
    try:
        # Test data
        test_data = {
            'access_token': 'test_access_token_12345',
            'refresh_token': 'test_refresh_token_67890',
            'expires_at': 1234567890,
            'remember_me': True
        }
        
        print(f"📝 Test data: {test_data}")
        
        # Generate key
        password = "test_password"
        salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode())
        
        # Create cipher
        fernet = Fernet(base64.urlsafe_b64encode(key))
        
        # Encrypt data
        json_data = json.dumps(test_data, separators=(',', ':')).encode()
        encrypted_data = fernet.encrypt(json_data)
        
        print("✅ Data encrypted successfully")
        print(f"📄 Encrypted data (first 50 chars): {encrypted_data[:50]}...")
        
        # Verify it's encrypted
        if b'test_access_token_12345' in encrypted_data:
            print("❌ WARNING: Data appears to be plaintext!")
            return False
        else:
            print("✅ Data is properly encrypted")
        
        # Decrypt data
        decrypted_json = fernet.decrypt(encrypted_data)
        decrypted_data = json.loads(decrypted_json.decode())
        
        print("✅ Data decrypted successfully")
        
        # Verify integrity
        if decrypted_data == test_data:
            print("✅ Data integrity verified - decrypted data matches original")
        else:
            print("❌ Data integrity failed")
            print(f"Original:  {test_data}")
            print(f"Decrypted: {decrypted_data}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error in encryption test: {e}")
        return False

def test_secure_session_import():
    """Test importing the secure session module."""
    print("\n🔧 TESTING SECURE SESSION IMPORT")
    print("="*40)
    
    try:
        # Try to import without triggering full trackpro initialization
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import just the secure session module
        from trackpro.auth.secure_session import SecureSessionManager
        print("✅ SecureSessionManager imported successfully")
        
        # Create instance
        session_manager = SecureSessionManager("TestApp")
        print("✅ SecureSessionManager instance created")
        
        # Test basic functionality
        test_data = {'test': 'data'}
        
        # Save
        success = session_manager.save_session(test_data)
        if success:
            print("✅ Session saved successfully")
        else:
            print("❌ Failed to save session")
            return False
        
        # Load
        loaded_data = session_manager.load_session()
        if loaded_data == test_data:
            print("✅ Session loaded successfully with correct data")
        else:
            print("❌ Failed to load session or data mismatch")
            return False
        
        # Clear
        success = session_manager.clear_session()
        if success:
            print("✅ Session cleared successfully")
        else:
            print("❌ Failed to clear session")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error in secure session test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🔐 MINIMAL SECURE SESSION TESTS")
    print("="*50)
    
    tests = [
        ("Basic Encryption", test_basic_encryption),
        ("Secure Session Import", test_secure_session_import)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            failed += 1
    
    print("\n" + "="*50)
    print("🏁 TEST SUMMARY")
    print("="*50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Encryption is working!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 