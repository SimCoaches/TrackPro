"""Configuration management for TrackPro."""

import os
import json
from pathlib import Path
import logging
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file with proper path resolution
def _load_env_file():
    """Load .env file from the correct location for both dev and built executable."""
    import sys
    
    # Possible locations for .env file
    possible_env_paths = []
    
    # For development: relative to this file's parent directory (project root)
    possible_env_paths.append(Path(__file__).parent.parent / ".env")
    
    # For built executable: relative to executable directory
    if getattr(sys, 'frozen', False):
        # Running as built executable
        exe_dir = Path(sys.executable).parent
        possible_env_paths.append(exe_dir / ".env")
        possible_env_paths.append(exe_dir.parent / ".env")
    
    # Current working directory
    possible_env_paths.append(Path.cwd() / ".env")
    
    # Try to load .env from each possible location
    for env_path in possible_env_paths:
        if env_path.exists():
            logger.info(f"Loading environment variables from: {env_path}")
            load_dotenv(env_path)
            return True
    
    logger.warning("No .env file found - using system environment variables only")
    return False

_load_env_file()

# Version for the current terms of service.
# This should be incremented when terms_of_service.txt is updated.
CURRENT_TERMS_VERSION = 1

DEFAULT_CONFIG = {
    'supabase': {
        'enabled': True,  # Start with cloud sync enabled by default
        'url': '',  # Now loaded from environment variables
        'key': '',  # Now loaded from environment variables
        'debug_mode': False  # Set to True for additional diagnostic logging
    },
    'performance': {
        'cpu_affinity_enabled': False,  # Opt-in: pin process to subset of CPU cores
        'prefer_software_opengl': False  # Persisted fallback if hardware GL fails
    },
    'ui': {
        'minimize_to_tray': False,  # Whether to minimize to system tray instead of closing
        'start_with_windows': False,  # Whether to start TrackPro with Windows
        'start_minimized': True  # Whether to start minimized when starting with Windows
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
    },
    'voice_chat': {
        'enabled': True,  # Voice chat enabled by default
        'server_url': '',  # Optional: wss://voice.yourdomain (falls back to localhost)
        'webrtc_enabled': False,  # Enable embedded WebRTC (LiveKit)
        'livekit_host_url': '',   # e.g., wss://your-livekit-host
        'livekit_token_url': '',  # Supabase Edge Function URL to mint tokens
        'sample_rate': 48000,  # High quality sample rate
        'channels': 1,  # Mono - most microphones are mono
        'bit_depth': 16,  # Reduced bit depth for lower latency
        'buffer_size': 128,  # Ultra-low latency buffer (was 512)
        'input_device': None,  # Will be set by user
        'output_device': None,  # Will be set by user
        'input_volume': 80,  # Input volume percentage
        'output_volume': 80,  # Output volume percentage
        'noise_suppression': False,  # Disabled for lower latency
        'echo_cancellation': False,  # Disabled for lower latency
        'automatic_gain': False,  # Disabled for lower latency
        'ultra_low_latency': True,  # Enable ultra-low latency mode
        'direct_monitoring': True,  # Enable direct monitoring (hear yourself instantly)
        'priority_threading': True  # Use high-priority threads for audio processing
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
        self._setup_fallback_environment()
    
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
    
    def _setup_fallback_environment(self):
        """Set up fallback environment for built executables when external config is missing."""
        import sys
        
        # Check if we're running as a built executable
        is_frozen = getattr(sys, 'frozen', False)
        
        # Only enable fallback mode if ALL credential sources are completely missing
        has_any_credentials = (
            self.twilio_account_sid or 
            self.twilio_auth_token or 
            self.twilio_verify_service_sid or
            os.getenv('TWILIO_ACCOUNT_SID') or
            os.getenv('TWILIO_AUTH_TOKEN') or 
            os.getenv('TWILIO_VERIFY_SERVICE_SID')
        )
        
        if (is_frozen and 
            not has_any_credentials and
            not os.getenv('TRACKPRO_DEV_MODE')):
            
            logger.warning("Built executable detected with no Twilio configuration anywhere - enabling fallback mode")
            logger.info("To enable real 2FA, ensure .env file is present with Twilio credentials")
            os.environ['TRACKPRO_DEV_MODE'] = 'true'
        elif has_any_credentials:
            logger.info("Twilio credentials detected - 2FA will use real SMS verification")
    
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

    # Performance settings
    @property
    def cpu_affinity_enabled(self) -> bool:
        return bool(os.getenv('TRACKPRO_CPU_AFFINITY', '').lower() == 'true' or self.get('performance.cpu_affinity_enabled', False))

    def set_cpu_affinity_enabled(self, enabled: bool):
        self.set('performance.cpu_affinity_enabled', bool(enabled))

    @property
    def prefer_software_opengl(self) -> bool:
        return self.get('performance.prefer_software_opengl', False)

    def set_prefer_software_opengl(self, enabled: bool):
        self.set('performance.prefer_software_opengl', bool(enabled))
    
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

    @property
    def start_with_windows(self) -> bool:
        """Check if TrackPro should start with Windows."""
        return self.get('ui.start_with_windows', False)

    @property
    def start_minimized(self) -> bool:
        """Check if TrackPro should start minimized when starting with Windows."""
        return self.get('ui.start_minimized', True)

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
        """Get Twilio Account SID from environment, config.ini, or config."""
        # First check environment variable
        sid = os.getenv('TWILIO_ACCOUNT_SID')
        if sid:
            return sid
            
        # Then check config.ini file (with proper path resolution for both dev and built exe)
        try:
            import configparser
            import sys
            
            # Check multiple possible locations for config.ini
            possible_paths = []
            
            # For development: relative to this file
            possible_paths.append(Path(__file__).parent.parent / "config.ini")
            
            # For built executable: relative to executable directory
            if getattr(sys, 'frozen', False):
                # Running as built executable
                exe_dir = Path(sys.executable).parent
                possible_paths.append(exe_dir / "config.ini")
                possible_paths.append(exe_dir.parent / "config.ini")
            
            # Current working directory
            possible_paths.append(Path.cwd() / "config.ini")
            
            # Search for config.ini in all possible locations
            for config_ini_path in possible_paths:
                if config_ini_path.exists():
                    logger.info(f"Found config.ini at: {config_ini_path}")
                    config_parser = configparser.ConfigParser()
                    config_parser.read(config_ini_path)
                    if 'twilio' in config_parser and 'account_sid' in config_parser['twilio']:
                        sid = config_parser['twilio']['account_sid'].strip()
                        if sid:
                            logger.info("Found Twilio Account SID in config.ini")
                            return sid
            
            logger.info("config.ini not found or doesn't contain Twilio Account SID")
        except Exception as e:
            logger.warning(f"Error reading config.ini for Twilio Account SID: {e}")
            
        # Finally check JSON config
        sid = self.get('twilio.account_sid', '')
        if not sid:
            logger.warning("Twilio Account SID not found in environment, config.ini, or config")
        return sid

    @property
    def twilio_auth_token(self) -> str:
        """Get Twilio Auth Token from environment, config.ini, or config."""
        # First check environment variable
        token = os.getenv('TWILIO_AUTH_TOKEN')
        if token:
            return token
            
        # Then check config.ini file (with proper path resolution for both dev and built exe)
        try:
            import configparser
            import sys
            
            # Check multiple possible locations for config.ini
            possible_paths = []
            
            # For development: relative to this file
            possible_paths.append(Path(__file__).parent.parent / "config.ini")
            
            # For built executable: relative to executable directory
            if getattr(sys, 'frozen', False):
                # Running as built executable
                exe_dir = Path(sys.executable).parent
                possible_paths.append(exe_dir / "config.ini")
                possible_paths.append(exe_dir.parent / "config.ini")
            
            # Current working directory
            possible_paths.append(Path.cwd() / "config.ini")
            
            # Search for config.ini in all possible locations
            for config_ini_path in possible_paths:
                if config_ini_path.exists():
                    config_parser = configparser.ConfigParser()
                    config_parser.read(config_ini_path)
                    if 'twilio' in config_parser and 'auth_token' in config_parser['twilio']:
                        token = config_parser['twilio']['auth_token'].strip()
                        if token:
                            logger.info("Found Twilio Auth Token in config.ini")
                            return token
        except Exception as e:
            logger.warning(f"Error reading config.ini for Twilio Auth Token: {e}")
            
        # Finally check JSON config
        token = self.get('twilio.auth_token', '')
        if not token:
            logger.warning("Twilio Auth Token not found in environment, config.ini, or config")
        return token

    @property
    def twilio_verify_service_sid(self) -> str:
        """Get Twilio Verify Service SID from environment, config.ini, or config."""
        # First check environment variable
        service_sid = os.getenv('TWILIO_VERIFY_SERVICE_SID')
        if service_sid:
            return service_sid
            
        # Then check config.ini file (with proper path resolution for both dev and built exe)
        try:
            import configparser
            import sys
            
            # Check multiple possible locations for config.ini
            possible_paths = []
            
            # For development: relative to this file
            possible_paths.append(Path(__file__).parent.parent / "config.ini")
            
            # For built executable: relative to executable directory
            if getattr(sys, 'frozen', False):
                # Running as built executable
                exe_dir = Path(sys.executable).parent
                possible_paths.append(exe_dir / "config.ini")
                possible_paths.append(exe_dir.parent / "config.ini")
            
            # Current working directory
            possible_paths.append(Path.cwd() / "config.ini")
            
            # Search for config.ini in all possible locations
            for config_ini_path in possible_paths:
                if config_ini_path.exists():
                    config_parser = configparser.ConfigParser()
                    config_parser.read(config_ini_path)
                    if 'twilio' in config_parser and 'verify_service_sid' in config_parser['twilio']:
                        service_sid = config_parser['twilio']['verify_service_sid'].strip()
                        if service_sid:
                            logger.info("Found Twilio Verify Service SID in config.ini")
                            return service_sid
        except Exception as e:
            logger.warning(f"Error reading config.ini for Twilio Verify Service SID: {e}")
            
        # Finally check JSON config
        service_sid = self.get('twilio.verify_service_sid', '')
        if not service_sid:
            logger.warning("Twilio Verify Service SID not found in environment, config.ini, or config")
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
    
    # Voice Chat Configuration Properties
    
    @property
    def voice_chat_enabled(self) -> bool:
        """Get voice chat enabled setting."""
        return self.get('voice_chat.enabled', True)

    @property
    def voice_chat_server_url(self) -> str:
        """Get the voice server base URL (e.g., wss://voice.yourdomain). Falls back to localhost for dev."""
        # Prefer environment variable for easy deployment overrides
        url = os.getenv('TRACKPRO_VOICE_SERVER_URL') or self.get('voice_chat.server_url', '')
        if not url:
            # Development fallback
            url = 'ws://localhost:8080'
            logger.info("Voice server URL not configured; using dev fallback ws://localhost:8080")
        else:
            logger.info("Using configured voice server URL")
        return url

    @property
    def voice_chat_webrtc_enabled(self) -> bool:
        return bool(os.getenv('TRACKPRO_VOICE_WEBRTC', '').lower() == 'true' or self.get('voice_chat.webrtc_enabled', False))

    @property
    def voice_chat_livekit_host_url(self) -> str:
        return os.getenv('TRACKPRO_LIVEKIT_HOST_URL') or self.get('voice_chat.livekit_host_url', '')

    @property
    def voice_chat_livekit_token_url(self) -> str:
        return os.getenv('TRACKPRO_LIVEKIT_TOKEN_URL') or self.get('voice_chat.livekit_token_url', '')
    
    @property
    def voice_chat_sample_rate(self) -> int:
        """Get voice chat sample rate."""
        return self.get('voice_chat.sample_rate', 48000)
    
    @property
    def voice_chat_channels(self) -> int:
        """Get voice chat channel count."""
        return self.get('voice_chat.channels', 1)  # Changed from 2 to 1 - most mics are mono
    
    @property
    def voice_chat_bit_depth(self) -> int:
        """Get voice chat bit depth."""
        return self.get('voice_chat.bit_depth', 16)
    
    @property
    def voice_chat_buffer_size(self) -> int:
        """Get voice chat buffer size."""
        return self.get('voice_chat.buffer_size', 128)
    
    @property
    def voice_chat_input_device(self) -> Optional[int]:
        """Get voice chat input device index."""
        return self.get('voice_chat.input_device')
    
    @property
    def voice_chat_output_device(self) -> Optional[int]:
        """Get voice chat output device index."""
        return self.get('voice_chat.output_device')
    
    @property
    def voice_chat_input_volume(self) -> int:
        """Get voice chat input volume percentage."""
        return self.get('voice_chat.input_volume', 80)
    
    @property
    def voice_chat_output_volume(self) -> int:
        """Get voice chat output volume percentage."""
        return self.get('voice_chat.output_volume', 80)
    
    @property
    def voice_chat_noise_suppression(self) -> bool:
        """Get voice chat noise suppression setting."""
        return self.get('voice_chat.noise_suppression', True)
    
    @property
    def voice_chat_echo_cancellation(self) -> bool:
        """Get voice chat echo cancellation setting."""
        return self.get('voice_chat.echo_cancellation', True)
    
    @property
    def voice_chat_automatic_gain(self) -> bool:
        """Get voice chat automatic gain setting."""
        return self.get('voice_chat.automatic_gain', False)  # Disabled for lower latency
    
    @property
    def voice_chat_ultra_low_latency(self) -> bool:
        """Get voice chat ultra-low latency mode setting."""
        return self.get('voice_chat.ultra_low_latency', True)
    
    @property
    def voice_chat_direct_monitoring(self) -> bool:
        """Get voice chat direct monitoring setting."""
        return self.get('voice_chat.direct_monitoring', True)
    
    @property
    def voice_chat_priority_threading(self) -> bool:
        """Get voice chat priority threading setting."""
        return self.get('voice_chat.priority_threading', True)

# Create global config instance
config = Config() 