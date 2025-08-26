"""Twilio SMS verification service for 2FA."""

import logging
from ..config import config
import os

# Twilio import with fallback
try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioClient = None
    TwilioException = Exception

logger = logging.getLogger(__name__)

class TwilioService:
    """Service for handling SMS-based verification using Twilio."""
    
    def __init__(self):
        self.client = None
        self.initialize()
    
    def initialize(self):
        """Initialize Twilio client if credentials are available."""
        if not TWILIO_AVAILABLE:
            logger.warning("Twilio library not available. SMS features will be disabled.")
            return False
            
        try:
            account_sid = config.twilio_account_sid
            auth_token = config.twilio_auth_token
            
            if account_sid and auth_token:
                self.client = TwilioClient(account_sid, auth_token)
                logger.info("Twilio service initialized successfully")
                return True
            else:
                logger.warning("Twilio credentials not configured. SMS features will be disabled.")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize Twilio service: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Twilio service is available."""
        return TWILIO_AVAILABLE and self.client is not None
    
    def send_verification_code(self, phone_number: str) -> dict:
        """Send SMS verification code to phone number.
        
        Args:
            phone_number: Phone number to send code to (e.g. +1234567890)
            
        Returns:
            dict: {'success': bool, 'message': str, 'status': str}
        """
        if not self.is_available():
            return {
                'success': False,
                'message': 'Twilio service is not available'
            }

        # DEVELOPMENT/FALLBACK MODE - Allow testing without valid Twilio credentials
        # This activates when TRACKPRO_DEV_MODE is set or when running without proper config
        account_sid = config.twilio_account_sid
        auth_token = config.twilio_auth_token
        dev_mode = (os.getenv('TRACKPRO_DEV_MODE') == 'true' or 
                   not (account_sid and auth_token and config.twilio_verify_service_sid))

        if dev_mode:
            logger.info(f"DEV/FALLBACK MODE: Mock sending verification code to {phone_number}")
            return {
                'success': True,
                'message': 'Verification code sent (Development/Fallback Mode)',
                'sid': 'mock_verification_sid'
            }

        try:
            verification = self.client.verify.services(
                config.twilio_verify_service_sid
            ).verifications.create(
                to=phone_number,
                channel='sms'
            )
            
            logger.info(f"Verification code sent to {phone_number}")
            return {
                'success': True,
                'message': 'Verification code sent successfully',
                'sid': verification.sid
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Twilio error sending verification: {error_msg}")
            return {
                'success': False,
                'message': f'Failed to send verification code: {error_msg}'
            }
    
    def verify_code(self, phone_number: str, code: str) -> dict:
        """Verify SMS code for phone number.
        
        Args:
            phone_number: Phone number the code was sent to
            code: 6-digit verification code
            
        Returns:
            dict: {'success': bool, 'message': str, 'status': str}
        """
        if not self.is_available():
            return {
                'success': False,
                'message': 'SMS service is not available',
                'status': 'unavailable'
            }
        
        # DEVELOPMENT/FALLBACK MODE - Accept any 6-digit code when in fallback mode
        account_sid = config.twilio_account_sid
        auth_token = config.twilio_auth_token
        dev_mode = (os.getenv('TRACKPRO_DEV_MODE') == 'true' or 
                   not (account_sid and auth_token and config.twilio_verify_service_sid))
        
        if dev_mode:
            # In dev/fallback mode, accept any 6-digit code
            if len(code.strip()) == 6 and code.strip().isdigit():
                logger.info(f"DEV/FALLBACK MODE: Accepting verification code for {phone_number}")
                return {
                    'success': True,
                    'message': 'Phone number verified successfully (Development/Fallback Mode)',
                    'status': 'approved'
                }
            else:
                return {
                    'success': False,
                    'message': 'Please enter a valid 6-digit code',
                    'status': 'denied'
                }
        
        try:
            verification_check = self.client.verify.services(
                config.twilio_verify_service_sid
            ).verification_checks.create(
                to=phone_number,
                code=code.strip()
            )
            
            if verification_check.status == 'approved':
                return {
                    'success': True,
                    'message': 'Phone number verified successfully',
                    'status': 'approved'
                }
            elif verification_check.status == 'denied':
                return {
                    'success': False,
                    'message': 'Invalid verification code',
                    'status': 'denied'
                }
            else:
                return {
                    'success': False,
                    'message': f'Verification failed: {verification_check.status}',
                    'status': verification_check.status
                }
                
        except TwilioException as e:
            logger.error(f"Twilio verification error: {e}")
            return {
                'success': False,
                'message': f'SMS verification error: {str(e)}',
                'status': 'error'
            }
        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'status': 'error'
            }

# Global service instance
# PERFORMANCE OPTIMIZATION: Commented out to save 479ms during startup
# twilio_service = TwilioService()
twilio_service = None  # Disabled for performance - SMS features not in use 