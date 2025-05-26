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

# Create global config instance
config = Config() 