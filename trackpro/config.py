"""Configuration management for TrackPro."""

import os
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'supabase': {
        'enabled': True,  # Start with cloud sync enabled by default
        'url': 'https://xbfotxwpntqplvvsffrr.supabase.co',
        'key': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhiZm90eHdwbnRxcGx2dnNmZnJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQzMTM5NjUsImV4cCI6MjA1OTg4OTk2NX0.AwLUhaxQQn9xnpTwgOrRIdWQYsVI9-ikC2Qb-6SR2h8',
        'debug_mode': False  # Set to True for additional diagnostic logging
    },
    'ui': {
        'minimize_to_tray': False  # Whether to minimize to system tray instead of closing
    },
    'eye_tracking': {
        'enabled': False,  # Eye tracking disabled by default
        'auto_start_with_session': True,  # Automatically start recording when racing session begins
        'auto_calibrate_on_startup': False,  # Prompt for calibration when TrackPro starts
        'camera_index': 0,  # Which camera to use (0 = default)
        'recording_fps': 30,  # Eye tracking recording frame rate
        'require_calibration': True,  # Require calibration before recording
        'show_gaze_overlay': False,  # Show real-time gaze overlay during racing (performance impact)
        'save_raw_video': False  # Save raw camera video alongside gaze data (large files)
    },
    'twilio': {
        'enabled': True,  # Default to enabled
        'account_sid': '',
        'auth_token': '',
        'verify_service_sid': '',
        'debug_mode': False  # Default to disabled
    }
}

# Startup optimization settings
STARTUP_OPTIMIZATIONS = {
    'defer_curve_loading': True,
    'defer_cloud_sync': True,
    'defer_hidhide_init': True,
    'aggressive_cache_during_startup': True,
    'startup_grace_period_seconds': 60,
    'early_splash_screen': True
}

class Config:
    """Configuration manager for TrackPro."""
    
    def __init__(self):
        """Initialize configuration."""
        self.config_dir = Path.home() / ".trackpro"
        self.config_file = self.config_dir / "config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file or create default."""
        try:
            # Create config directory if it doesn't exist
            self.config_dir.mkdir(exist_ok=True)
            
            # Load existing config if it exists
            if self.config_file.exists():
                with open(self.config_file) as f:
                    config = json.load(f)
                    # Ensure supabase config exists
                    if 'supabase' not in config:
                        config['supabase'] = DEFAULT_CONFIG['supabase']
                    # Ensure ui config exists
                    if 'ui' not in config:
                        config['ui'] = DEFAULT_CONFIG['ui']
                    # Ensure eye_tracking config exists
                    if 'eye_tracking' not in config:
                        config['eye_tracking'] = DEFAULT_CONFIG['eye_tracking']
                    # Ensure twilio config exists
                    if 'twilio' not in config:
                        config['twilio'] = DEFAULT_CONFIG['twilio']
                    return config
            
            # Create default config
            default_config = DEFAULT_CONFIG.copy()
            
            # Save default config
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            
            return default_config
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()  # Return defaults instead of empty dict
    
    def save(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get(self, key: str, default=None):
        """Get a configuration value."""
        try:
            # Handle nested keys with dot notation
            keys = key.split('.')
            value = self.config
            for k in keys:
                if k not in value:
                    return default
                value = value[k]
            return value
        except Exception:
            return default
    
    def set(self, key: str, value):
        """Set a configuration value."""
        try:
            # Handle nested keys with dot notation
            keys = key.split('.')
            config = self.config
            for k in keys[:-1]:
                config = config.setdefault(k, {})
            config[keys[-1]] = value
            self.save()
        except Exception as e:
            logger.error(f"Error setting config value: {e}")
    
    @property
    def supabase_url(self) -> str:
        """Get Supabase URL from config or environment."""
        url = os.getenv('SUPABASE_URL') or self.get('supabase.url', '')
        if not url:
            logger.warning("Supabase URL not found in environment or config")
        else:
            logger.info("Found Supabase URL")
        return url
    
    @property
    def supabase_key(self) -> str:
        """Get Supabase key from config or environment."""
        key = os.getenv('SUPABASE_KEY') or self.get('supabase.key', '')
        if not key:
            logger.warning("Supabase key not found in environment or config")
        else:
            logger.info("Found Supabase key")
        return key
    
    @property
    def supabase_enabled(self) -> bool:
        """Check if Supabase integration is enabled."""
        enabled = self.get('supabase.enabled', True)  # Default to True
        
        # Force enable for debugging if needed
        if os.getenv('TRACKPRO_FORCE_SUPABASE', '').lower() == 'true':
            logger.info("Supabase forcibly enabled by environment variable")
            self.set('supabase.enabled', True)
            return True
        
        logger.info(f"Supabase enabled: {enabled}")
        return enabled
    
    @property
    def supabase_debug(self) -> bool:
        """Check if Supabase debug mode is enabled."""
        debug = self.get('supabase.debug_mode', False)
        if os.getenv('TRACKPRO_SUPABASE_DEBUG', '').lower() == 'true':
            debug = True
        return debug

    @property
    def minimize_to_tray(self) -> bool:
        """Check if minimize to tray is enabled."""
        return self.get('ui.minimize_to_tray', False)

    # Eye tracking configuration properties
    @property
    def eye_tracking_enabled(self) -> bool:
        """Check if eye tracking is enabled."""
        return self.get('eye_tracking.enabled', False)
    
    @property
    def eye_tracking_auto_start(self) -> bool:
        """Check if eye tracking should auto-start with racing sessions."""
        return self.get('eye_tracking.auto_start_with_session', True)
    
    @property
    def eye_tracking_auto_calibrate(self) -> bool:
        """Check if eye tracking should auto-calibrate on startup."""
        return self.get('eye_tracking.auto_calibrate_on_startup', False)
    
    @property
    def eye_tracking_camera_index(self) -> int:
        """Get the camera index for eye tracking."""
        return self.get('eye_tracking.camera_index', 0)
    
    @property
    def eye_tracking_fps(self) -> int:
        """Get the eye tracking recording frame rate."""
        return self.get('eye_tracking.recording_fps', 30)
    
    @property
    def eye_tracking_require_calibration(self) -> bool:
        """Check if calibration is required before recording."""
        return self.get('eye_tracking.require_calibration', True)
    
    @property
    def eye_tracking_show_overlay(self) -> bool:
        """Check if real-time gaze overlay should be shown."""
        return self.get('eye_tracking.show_gaze_overlay', False)
    
    @property
    def eye_tracking_save_video(self) -> bool:
        """Check if raw camera video should be saved."""
        return self.get('eye_tracking.save_raw_video', False)

    # Twilio configuration properties for SMS 2FA
    @property
    def twilio_account_sid(self) -> str:
        """Get Twilio Account SID from environment or config."""
        sid = os.getenv('TWILIO_ACCOUNT_SID') or self.get('twilio.account_sid', '')
        if not sid:
            logger.warning("Twilio Account SID not found in environment or config")
        return sid

    @property
    def twilio_auth_token(self) -> str:
        """Get Twilio Auth Token from environment or config."""
        token = os.getenv('TWILIO_AUTH_TOKEN') or self.get('twilio.auth_token', '')
        if not token:
            logger.warning("Twilio Auth Token not found in environment or config")
        return token

    @property
    def twilio_verify_service_sid(self) -> str:
        """Get Twilio Verify Service SID from environment or config."""
        service_sid = os.getenv('TWILIO_VERIFY_SERVICE_SID') or self.get('twilio.verify_service_sid', '')
        if not service_sid:
            logger.warning("Twilio Verify Service SID not found in environment or config")
        return service_sid

    @property
    def twilio_enabled(self) -> bool:
        """Check if Twilio integration is enabled."""
        enabled = self.get('twilio.enabled', True)  # Default to True
        
        # Force disable if credentials are missing
        if not (self.twilio_account_sid and self.twilio_auth_token and self.twilio_verify_service_sid):
            logger.info("Twilio disabled due to missing credentials")
            return False
        
        if os.getenv('TRACKPRO_FORCE_TWILIO', '').lower() == 'true':
            logger.info("Twilio forcibly enabled by environment variable")
            self.set('twilio.enabled', True)
            return True
        
        logger.info(f"Twilio enabled: {enabled}")
        return enabled

    @property
    def twilio_debug(self) -> bool:
        """Check if Twilio debug mode is enabled."""
        debug = self.get('twilio.debug_mode', False)
        if os.getenv('TRACKPRO_TWILIO_DEBUG', '').lower() == 'true':
            debug = True
        return debug

# Create global config instance
config = Config() 