"""EmailJS integration for sending support tickets via email."""

import requests
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EmailJSClient:
    """Client for sending emails through EmailJS service."""
    
    def __init__(self, service_id: str, template_id: str, public_key: str, private_key: Optional[str] = None):
        """
        Initialize EmailJS client.
        
        Args:
            service_id: Your EmailJS service ID
            template_id: Your EmailJS template ID
            public_key: Your EmailJS public key
            private_key: Your EmailJS private key (required for strict mode)
        """
        self.service_id = service_id
        self.template_id = template_id
        self.public_key = public_key
        self.private_key = private_key
        # Use send endpoint for strict mode with private key, send-form for public only
        self.api_url = "https://api.emailjs.com/api/v1.0/email/send" if private_key else "https://api.emailjs.com/api/v1.0/email/send-form"
    
    def send_support_ticket(self, 
                          subject: str, 
                          priority: str, 
                          category: str, 
                          description: str,
                          user_email: Optional[str] = None,
                          user_name: Optional[str] = None) -> bool:
        """
        Send a support ticket via EmailJS.
        
        Args:
            subject: Ticket subject
            priority: Ticket priority (Low, Medium, High, Critical)
            category: Issue category
            description: Detailed description
            user_email: User's email address (optional)
            user_name: User's name (optional)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            logger.info("📨 [EMAILJS DEBUG] Starting send_support_ticket()")
            logger.info(f"📨 [EMAILJS DEBUG] API URL: {self.api_url}")
            logger.info(f"📨 [EMAILJS DEBUG] Service ID: {self.service_id}")
            logger.info(f"📨 [EMAILJS DEBUG] Template ID: {self.template_id}")
            logger.info(f"📨 [EMAILJS DEBUG] Public Key: {self.public_key[:10]}..." if self.public_key else "None")
            logger.info(f"📨 [EMAILJS DEBUG] Private Key: {('*' * 10) + '...' if self.private_key else 'None (using public mode)'}")
            logger.info(f"📨 [EMAILJS DEBUG] Using strict mode: {bool(self.private_key)}")
            
            # Prepare email template parameters
            template_params = {
                'ticket_subject': subject,
                'ticket_priority': priority,
                'ticket_category': category,
                'ticket_description': description,
                'user_email': user_email or 'Anonymous User',
                'user_name': user_name or 'TrackPro User',
                'timestamp': self._get_timestamp()
            }
            
            logger.info(f"📨 [EMAILJS DEBUG] Template params: {template_params}")
            
            # Prepare request payload
            payload = {
                'service_id': self.service_id,
                'template_id': self.template_id,
                'user_id': self.public_key,
                'template_params': template_params
            }
            
            logger.info(f"📨 [EMAILJS DEBUG] Request payload prepared (size: {len(json.dumps(payload))} bytes)")
            
            # Send email via EmailJS API - use different methods based on strict mode
            if self.private_key:
                # Strict mode: Use JSON with private key
                logger.info("📨 [EMAILJS DEBUG] Using strict mode with private key")
                payload['accessToken'] = self.private_key  # Add private key for strict mode
                
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'TrackPro/1.0',
                }
                
                logger.info(f"📨 [EMAILJS DEBUG] JSON payload being sent (private key redacted)")
                logger.info("📨 [EMAILJS DEBUG] Sending POST request to EmailJS API (strict mode)...")
                
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
            else:
                # Public mode: Use form data
                import urllib.parse
                
                logger.info("📨 [EMAILJS DEBUG] Using public mode (form data)")
                # Convert payload to form data for send-form endpoint
                form_data = {
                    'service_id': payload['service_id'],
                    'template_id': payload['template_id'],
                    'user_id': payload['user_id'],  # send-form endpoint uses user_id, not public_key
                    **payload['template_params']
                }
                
                logger.info(f"📨 [EMAILJS DEBUG] Form data being sent: {form_data}")
                logger.info("📨 [EMAILJS DEBUG] Sending POST request to EmailJS API (public mode)...")
                
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
                
                response = requests.post(
                    self.api_url,
                    data=urllib.parse.urlencode(form_data),
                    headers=headers,
                    timeout=10
                )
            
            logger.info(f"📨 [EMAILJS DEBUG] Response received:")
            logger.info(f"📨 [EMAILJS DEBUG]   Status Code: {response.status_code}")
            logger.info(f"📨 [EMAILJS DEBUG]   Headers: {dict(response.headers)}")
            logger.info(f"📨 [EMAILJS DEBUG]   Content: {response.text}")
            
            if response.status_code == 200:
                logger.info(f"✅ [EMAILJS DEBUG] Support ticket sent successfully - Subject: {subject}")
                return True
            else:
                logger.error(f"❌ [EMAILJS DEBUG] EmailJS API error - Status: {response.status_code}, Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("❌ [EMAILJS DEBUG] EmailJS request timed out")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [EMAILJS DEBUG] EmailJS request failed: {e}")
            import traceback
            logger.error(f"❌ [EMAILJS DEBUG] Request traceback: {traceback.format_exc()}")
            return False
        except Exception as e:
            logger.error(f"❌ [EMAILJS DEBUG] Unexpected error sending email: {e}")
            import traceback
            logger.error(f"❌ [EMAILJS DEBUG] General traceback: {traceback.format_exc()}")
            return False
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for the email."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    def test_connection(self) -> bool:
        """
        Test EmailJS connection with a simple test email.
        
        Returns:
            bool: True if test successful, False otherwise
        """
        try:
            return self.send_support_ticket(
                subject="EmailJS Test Connection",
                priority="Low", 
                category="General Question",
                description="This is a test email to verify EmailJS integration is working correctly.",
                user_email="test@trackpro.app",
                user_name="TrackPro System Test"
            )
        except Exception as e:
            logger.error(f"❌ EmailJS connection test failed: {e}")
            return False


class EmailJSConfig:
    """Configuration management for EmailJS settings."""
    
    def __init__(self):
        self.service_id = None
        self.template_id = None 
        self.public_key = None
        self.private_key = None
        self._load_config()
    
    def _load_config(self):
        """Load EmailJS configuration from file or environment."""
        try:
            # Try to load from config file first
            self._load_from_file()
        except Exception:
            # Fall back to environment variables
            self._load_from_env()
    
    def _load_from_file(self):
        """Load configuration from emailjs_config.json file."""
        try:
            import os
            config_path = os.path.join(os.path.dirname(__file__), 'emailjs_config.json')
            
            logger.info(f"🔧 [CONFIG DEBUG] Looking for config file at: {config_path}")
            
            if os.path.exists(config_path):
                logger.info("🔧 [CONFIG DEBUG] Config file found, reading contents...")
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"🔧 [CONFIG DEBUG] Config file contents: {config}")
                    
                    self.service_id = config.get('service_id')
                    self.template_id = config.get('template_id')
                    self.public_key = config.get('public_key')
                    self.private_key = config.get('private_key')
                    
                    logger.info(f"🔧 [CONFIG DEBUG] Loaded values:")
                    logger.info(f"🔧 [CONFIG DEBUG]   service_id: {self.service_id}")
                    logger.info(f"🔧 [CONFIG DEBUG]   template_id: {self.template_id}")
                    logger.info(f"🔧 [CONFIG DEBUG]   public_key: {self.public_key[:10]}..." if self.public_key else "None")
                    logger.info(f"🔧 [CONFIG DEBUG]   private_key: {('*' * 10) + '...' if self.private_key else 'None'}")
                    
                    logger.info("✅ [CONFIG DEBUG] Loaded EmailJS config from file")
            else:
                logger.warning(f"⚠️ [CONFIG DEBUG] EmailJS config file not found at: {config_path}")
        except Exception as e:
            logger.error(f"❌ [CONFIG DEBUG] Error loading EmailJS config from file: {e}")
            import traceback
            logger.error(f"❌ [CONFIG DEBUG] Config load traceback: {traceback.format_exc()}")
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        import os
        self.service_id = os.getenv('EMAILJS_SERVICE_ID')
        self.template_id = os.getenv('EMAILJS_TEMPLATE_ID')
        self.public_key = os.getenv('EMAILJS_PUBLIC_KEY')
        self.private_key = os.getenv('EMAILJS_PRIVATE_KEY')
        
        if all([self.service_id, self.template_id, self.public_key]):
            logger.info(f"✅ Loaded EmailJS config from environment variables (strict mode: {bool(self.private_key)})")
        else:
            logger.warning("⚠️ EmailJS environment variables not found")
    
    def is_configured(self) -> bool:
        """Check if EmailJS is properly configured."""
        return all([self.service_id, self.template_id, self.public_key])
    
    def get_client(self) -> Optional[EmailJSClient]:
        """Get configured EmailJS client."""
        if self.is_configured():
            return EmailJSClient(self.service_id, self.template_id, self.public_key, self.private_key)
        else:
            logger.error("❌ EmailJS not properly configured")
            return None