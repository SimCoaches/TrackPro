"""
Secure Session Manager for TrackPro

This module provides secure session storage with encryption, integrity verification,
and proper file permissions for authentication tokens and session data.
"""

import os
import json
import hashlib
import secrets
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import platform
import stat
import base64

logger = logging.getLogger(__name__)

class SecureSessionManager:
    """Manages secure session storage with encryption and integrity verification."""
    
    def __init__(self, app_name: str = "TrackPro"):
        """Initialize the secure session manager.
        
        Args:
            app_name: Name of the application for file path generation
        """
        self.app_name = app_name
        self._setup_paths()
        self._setup_encryption()
        
    def _setup_paths(self):
        """Setup secure file paths for session storage."""
        # Use platform-appropriate directories
        if platform.system() == "Windows":
            base_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), self.app_name)
        elif platform.system() == "Darwin":  # macOS
            base_dir = os.path.join(os.path.expanduser("~/Library/Application Support"), self.app_name)
        else:  # Linux and others
            base_dir = os.path.join(os.path.expanduser("~/.local/share"), self.app_name)
        
        self.session_dir = Path(base_dir) / "secure_sessions"
        self.session_file = self.session_dir / "session.enc"
        self.key_file = self.session_dir / "session.key"
        
        # Create directory with secure permissions
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._set_secure_permissions(self.session_dir)
        
    def _setup_encryption(self):
        """Setup encryption components."""
        self.salt_size = 32  # 256 bits
        self.key_iterations = 600000  # OWASP recommended minimum for PBKDF2
        self.algorithm = hashes.SHA256()
        
    def _generate_key(self, password: str, salt: bytes) -> bytes:
        """Generate encryption key from password and salt using PBKDF2.
        
        Args:
            password: Master password for key derivation
            salt: Random salt for key derivation
            
        Returns:
            Derived encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=self.algorithm,
            length=32,  # 256 bits
            salt=salt,
            iterations=self.key_iterations,
        )
        return kdf.derive(password.encode())
    
    def _get_machine_identifier(self) -> str:
        """Get a unique machine identifier for key derivation.
        
        Returns:
            Machine-specific identifier
        """
        # Use multiple machine-specific values for better uniqueness
        identifiers = []
        
        # Add hostname
        identifiers.append(platform.node())
        
        # Add platform details
        identifiers.append(platform.system())
        identifiers.append(platform.release())
        
        # Add user name
        identifiers.append(os.getlogin() if hasattr(os, 'getlogin') else os.environ.get('USERNAME', 'unknown'))
        
        # On Windows, try to get machine GUID
        if platform.system() == "Windows":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                  r"SOFTWARE\Microsoft\Cryptography") as key:
                    machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
                    identifiers.append(machine_guid)
            except Exception:
                pass
        
        # Create hash of all identifiers
        combined = "|".join(identifiers)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _derive_master_key(self) -> bytes:
        """Derive master key from machine identifier.
        
        Returns:
            Master key for encryption
        """
        machine_id = self._get_machine_identifier()
        app_salt = f"{self.app_name}_session_encryption_v1".encode()
        
        # Use Scrypt for key derivation (more secure than PBKDF2)
        kdf = Scrypt(
            length=32,
            salt=app_salt,
            n=2**14,  # CPU/memory cost parameter
            r=8,      # Block size parameter
            p=1,      # Parallelization parameter
        )
        
        return kdf.derive(machine_id.encode())
    
    def _set_secure_permissions(self, path: Path):
        """Set secure file permissions (owner read/write only).
        
        Args:
            path: Path to secure
        """
        try:
            if platform.system() != "Windows":
                # Unix-like systems: set to 700 for directories, 600 for files
                if path.is_dir():
                    os.chmod(path, stat.S_IRWXU)  # 700
                else:
                    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 600
            else:
                # Windows: Try to use Windows-specific permissions with fallback
                try:
                    import win32security
                    import win32api
                    try:
                        # Prefer ntsecuritycon for FILE_ALL_ACCESS on some pywin32 builds
                        import ntsecuritycon as win32con
                    except Exception:
                        import win32con
                    
                    # Get current user SID
                    user_sid = win32security.GetTokenInformation(
                        win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY),
                        win32security.TokenUser
                    )[0]
                    
                    # Create DACL with only current user having full control
                    dacl = win32security.ACL()
                    try:
                        access_mask = win32con.FILE_ALL_ACCESS
                    except Exception:
                        # Fallback: GENERIC_ALL if FILE_ALL_ACCESS missing
                        access_mask = getattr(win32con, 'GENERIC_ALL', 0x10000000)
                    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, access_mask, user_sid)
                    
                    # Set security descriptor
                    sd = win32security.SECURITY_DESCRIPTOR()
                    sd.SetSecurityDescriptorDacl(1, dacl, 0)
                    
                    # Apply to file/directory
                    win32security.SetFileSecurity(str(path), win32security.DACL_SECURITY_INFORMATION, sd)
                except ImportError:
                    # win32security not available, use basic Windows file attributes
                    logger.warning("Windows security modules not available, using basic file attributes")
                    import subprocess
                    try:
                        # Use icacls command to set permissions
                        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', f'{os.getlogin()}:(F)'], 
                                     check=True, capture_output=True)
                    except Exception as icacls_e:
                        logger.warning(f"Could not set Windows permissions via icacls: {icacls_e}")
                        # Final fallback: just set file attributes
                        try:
                            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Could not set secure permissions on {path}: {e}")
            # Final fallback: try basic permissions
            try:
                if path.is_dir():
                    os.chmod(path, 0o700)
                else:
                    os.chmod(path, 0o600)
            except Exception:
                pass
    
    def _encrypt_data(self, data: Dict[str, Any]) -> Tuple[bytes, bytes]:
        """Encrypt session data.
        
        Args:
            data: Session data to encrypt
            
        Returns:
            Tuple of (encrypted_data, salt)
        """
        # Generate random salt
        salt = secrets.token_bytes(self.salt_size)
        
        # Derive key from master key and salt
        master_key = self._derive_master_key()
        kdf = PBKDF2HMAC(
            algorithm=self.algorithm,
            length=32,
            salt=salt,
            iterations=self.key_iterations,
        )
        derived_key = kdf.derive(master_key)
        
        # Create Fernet cipher
        fernet = Fernet(base64.urlsafe_b64encode(derived_key))
        
        # Serialize and encrypt data
        json_data = json.dumps(data, separators=(',', ':'), default=str).encode()
        encrypted_data = fernet.encrypt(json_data)
        
        return encrypted_data, salt
    
    def _decrypt_data(self, encrypted_data: bytes, salt: bytes) -> Dict[str, Any]:
        """Decrypt session data.
        
        Args:
            encrypted_data: Encrypted session data
            salt: Salt used for encryption
            
        Returns:
            Decrypted session data
        """
        # Derive key from master key and salt
        master_key = self._derive_master_key()
        kdf = PBKDF2HMAC(
            algorithm=self.algorithm,
            length=32,
            salt=salt,
            iterations=self.key_iterations,
        )
        derived_key = kdf.derive(master_key)
        
        # Create Fernet cipher
        fernet = Fernet(base64.urlsafe_b64encode(derived_key))
        
        # Decrypt and deserialize data
        json_data = fernet.decrypt(encrypted_data)
        return json.loads(json_data.decode())
    
    def _generate_integrity_hash(self, data: Dict[str, Any]) -> str:
        """Generate integrity hash for session data.
        
        Args:
            data: Session data to hash
            
        Returns:
            Hex-encoded integrity hash
        """
        # Create canonical representation of data
        canonical_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
        
        # Add machine identifier to prevent cross-machine session theft
        machine_id = self._get_machine_identifier()
        combined_data = f"{canonical_data}|{machine_id}"
        
        # Generate hash
        return hashlib.sha256(combined_data.encode()).hexdigest()
    
    def _verify_integrity(self, data: Dict[str, Any], expected_hash: str) -> bool:
        """Verify session data integrity.
        
        Args:
            data: Session data to verify
            expected_hash: Expected integrity hash
            
        Returns:
            True if integrity is verified, False otherwise
        """
        actual_hash = self._generate_integrity_hash(data)
        return secrets.compare_digest(actual_hash, expected_hash)
    
    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """Save session data securely.
        
        Args:
            session_data: Session data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add timestamp and version info
            import time
            def _sanitize(obj: Any) -> Any:
                try:
                    # Fast path for builtins
                    if isinstance(obj, (str, int, float, bool)) or obj is None:
                        return obj
                    # Datetime-like
                    try:
                        from datetime import datetime, date
                        if isinstance(obj, (datetime, date)):
                            return obj.isoformat()
                    except Exception:
                        pass
                    # Mappings
                    if isinstance(obj, dict):
                        return {k: _sanitize(v) for k, v in obj.items()}
                    # Iterables
                    if isinstance(obj, (list, tuple, set)):
                        return [_sanitize(v) for v in obj]
                    # Fallback to string
                    return str(obj)
                except Exception:
                    return str(obj)

            secure_data = {
                'version': '1.0',
                'timestamp': str(int(time.time())),
                'data': _sanitize(session_data)
            }
            
            # Generate integrity hash
            integrity_hash = self._generate_integrity_hash(secure_data)
            
            # Encrypt data
            encrypted_data, salt = self._encrypt_data(secure_data)
            
            # Create final structure
            final_data = {
                'salt': base64.b64encode(salt).decode(),
                'data': base64.b64encode(encrypted_data).decode(),
                'integrity': integrity_hash
            }
            
            # Write to file with secure permissions
            with open(self.session_file, 'w') as f:
                json.dump(final_data, f, separators=(',', ':'))
            
            # Set secure permissions on the file
            self._set_secure_permissions(self.session_file)
            
            logger.info("Session saved securely with encryption")
            return True
            
        except Exception as e:
            logger.error(f"Error saving secure session: {e}")
            return False
    
    def load_session(self) -> Optional[Dict[str, Any]]:
        """Load and decrypt session data.
        
        Returns:
            Session data if successful, None otherwise
        """
        try:
            if not self.session_file.exists():
                logger.info("No secure session file found")
                return None
            
            # Read encrypted data
            with open(self.session_file, 'r') as f:
                file_data = json.load(f)
            
            # Extract components
            salt = base64.b64decode(file_data['salt'])
            encrypted_data = base64.b64decode(file_data['data'])
            integrity_hash = file_data['integrity']
            
            # Decrypt data
            decrypted_data = self._decrypt_data(encrypted_data, salt)
            
            # Verify integrity
            if not self._verify_integrity(decrypted_data, integrity_hash):
                logger.error("Session integrity verification failed - data may be corrupted or tampered with")
                return None
            
            # Return the actual session data
            return decrypted_data.get('data', {})
            
        except Exception as e:
            logger.error(f"Error loading secure session: {e}")
            return None
    
    def clear_session(self) -> bool:
        """Clear stored session data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.session_file.exists():
                # Securely overwrite file before deletion
                self._secure_delete(self.session_file)
                logger.info("Session cleared securely")
            return True
        except Exception as e:
            logger.error(f"Error clearing secure session: {e}")
            return False
    
    def _secure_delete(self, file_path: Path):
        """Securely delete a file by overwriting it multiple times.
        
        Args:
            file_path: Path to file to delete
        """
        try:
            if not file_path.exists():
                return
            
            # Get file size
            file_size = file_path.stat().st_size
            
            # Overwrite with random data multiple times
            with open(file_path, 'r+b') as f:
                for _ in range(3):  # 3 passes should be sufficient for SSDs
                    f.seek(0)
                    f.write(secrets.token_bytes(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Finally delete the file
            file_path.unlink()
            
        except Exception as e:
            logger.warning(f"Could not securely delete {file_path}: {e}")
            # Fall back to regular deletion
            try:
                file_path.unlink()
            except Exception:
                pass
    
    def migrate_from_plaintext(self, plaintext_file: Path) -> bool:
        """Migrate session data from plaintext file to encrypted storage.
        
        Args:
            plaintext_file: Path to plaintext session file
            
        Returns:
            True if migration successful, False otherwise
        """
        try:
            if not plaintext_file.exists():
                logger.info("No plaintext session file to migrate")
                return True
            
            # Read plaintext data
            with open(plaintext_file, 'r') as f:
                plaintext_data = json.load(f)
            
            # Save as encrypted
            success = self.save_session(plaintext_data)
            
            if success:
                # Securely delete plaintext file
                self._secure_delete(plaintext_file)
                logger.info("Successfully migrated session from plaintext to encrypted storage")
                return True
            else:
                logger.error("Failed to migrate session to encrypted storage")
                return False
                
        except Exception as e:
            logger.error(f"Error migrating session from plaintext: {e}")
            return False
    
    def session_exists(self) -> bool:
        """Check if a session file exists.
        
        Returns:
            True if session file exists, False otherwise
        """
        return self.session_file.exists()
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session storage.
        
        Returns:
            Dictionary with session storage information
        """
        return {
            'session_file': str(self.session_file),
            'session_exists': self.session_exists(),
            'encryption_enabled': True,
            'integrity_verification': True,
            'secure_permissions': True,
            'platform': platform.system(),
            'session_dir': str(self.session_dir)
        } 