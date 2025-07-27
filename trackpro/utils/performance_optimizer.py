"""Performance optimization utilities for TrackPro."""

import os
import shutil
import tempfile
import logging
import platform
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Optimizes TrackPro performance by managing resources and cache."""
    
    @staticmethod
    def clear_web_engine_cache():
        """Clear Qt WebEngine cache to improve performance."""
        try:
            # Determine if we're running from a PyInstaller bundle
            if getattr(sys, 'frozen', False):
                # Running from PyInstaller bundle - use application directory
                app_dir = os.path.dirname(sys.executable)
                if platform.system() == "Windows":
                    cache_paths = [
                        os.path.join(app_dir, "QtWebEngine", "Cache"),
                        os.path.join(app_dir, "QtWebEngine", "Data"),
                        os.path.expanduser("~\\AppData\\Local\\TrackPro\\QtWebEngine"),
                        os.path.expanduser("~\\AppData\\Local\\Temp\\QtWebEngine")
                    ]
                else:
                    cache_paths = [
                        os.path.join(app_dir, "QtWebEngine", "Cache"),
                        os.path.join(app_dir, "QtWebEngine", "Data"),
                        os.path.expanduser("~/.cache/TrackPro/QtWebEngine"),
                        os.path.expanduser("~/.local/share/TrackPro/QtWebEngine")
                    ]
            else:
                # Running from source - use user directories
                if platform.system() == "Windows":
                    cache_paths = [
                        os.path.expanduser("~\\AppData\\Local\\TrackPro\\QtWebEngine"),
                        os.path.expanduser("~\\AppData\\Local\\Temp\\QtWebEngine"),
                        os.path.expanduser("~\\AppData\\Roaming\\TrackPro\\QtWebEngine")
                    ]
                else:
                    cache_paths = [
                        os.path.expanduser("~/.cache/TrackPro/QtWebEngine"),
                        os.path.expanduser("~/.local/share/TrackPro/QtWebEngine")
                    ]
            
            cleared_size = 0
            for cache_path in cache_paths:
                if os.path.exists(cache_path):
                    try:
                        # Calculate size before clearing
                        size = sum(os.path.getsize(os.path.join(dirpath, filename))
                                 for dirpath, dirnames, filenames in os.walk(cache_path)
                                 for filename in filenames)
                        
                        shutil.rmtree(cache_path)
                        cleared_size += size
                        logger.info(f"Cleared WebEngine cache: {cache_path}")
                    except Exception as e:
                        logger.warning(f"Could not clear cache {cache_path}: {e}")
            
            if cleared_size > 0:
                size_mb = cleared_size / (1024 * 1024)
                logger.info(f"Cleared {size_mb:.1f} MB of WebEngine cache")
                return True
                
        except Exception as e:
            logger.error(f"Error clearing WebEngine cache: {e}")
            
        return False
    
    @staticmethod
    def clear_temp_files():
        """Clear temporary files that might slow down the application."""
        try:
            cleared_count = 0
            
            # Clear temp directory of TrackPro-related files
            temp_dir = tempfile.gettempdir()
            trackpro_temp_pattern = ["trackpro_", "discord_", "vjoy_", "telemetry_"]
            
            for filename in os.listdir(temp_dir):
                for pattern in trackpro_temp_pattern:
                    if filename.lower().startswith(pattern.lower()):
                        try:
                            file_path = os.path.join(temp_dir, filename)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                                cleared_count += 1
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                                cleared_count += 1
                        except Exception as e:
                            logger.warning(f"Could not remove temp file {filename}: {e}")
                        break
            
            if cleared_count > 0:
                logger.info(f"Cleared {cleared_count} temporary files")
                return True
                
        except Exception as e:
            logger.error(f"Error clearing temp files: {e}")
            
        return False
    
    @staticmethod
    def optimize_dns_cache():
        """Optimize DNS cache settings for better connectivity."""
        try:
            if platform.system() == "Windows":
                # On Windows, we can flush DNS cache
                import subprocess
                result = subprocess.run(["ipconfig", "/flushdns"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("DNS cache flushed successfully")
                    return True
                else:
                    logger.warning("Could not flush DNS cache")
            else:
                # On Linux/Mac, DNS cache handling varies by system
                logger.info("DNS cache optimization not implemented for this OS")
                
        except Exception as e:
            logger.error(f"Error optimizing DNS cache: {e}")
            
        return False
    
    @staticmethod
    def clear_authentication_cache():
        """Clear cached authentication data that might be causing delays."""
        try:
            cleared_files = []
            
            # Look for TrackPro auth cache files
            trackpro_dir = os.path.expanduser("~/.trackpro")
            if os.path.exists(trackpro_dir):
                cache_files = ["session_cache.json", "auth_cache.json", "token_cache.json"]
                for cache_file in cache_files:
                    cache_path = os.path.join(trackpro_dir, cache_file)
                    if os.path.exists(cache_path):
                        try:
                            os.remove(cache_path)
                            cleared_files.append(cache_file)
                        except Exception as e:
                            logger.warning(f"Could not remove {cache_file}: {e}")
            
            if cleared_files:
                logger.info(f"Cleared auth cache files: {', '.join(cleared_files)}")
                return True
                
        except Exception as e:
            logger.error(f"Error clearing authentication cache: {e}")
            
        return False
    
    @staticmethod
    def optimize_for_performance():
        """Run all performance optimizations."""
        optimizations_performed = []
        
        logger.info("Starting performance optimization...")
        
        if PerformanceOptimizer.clear_web_engine_cache():
            optimizations_performed.append("WebEngine cache cleared")
            
        if PerformanceOptimizer.clear_temp_files():
            optimizations_performed.append("Temporary files cleared")
            
        if PerformanceOptimizer.optimize_dns_cache():
            optimizations_performed.append("DNS cache optimized")
            
        # Note: Don't clear auth cache automatically as it will log users out
        # if PerformanceOptimizer.clear_authentication_cache():
        #     optimizations_performed.append("Authentication cache cleared")
        
        if optimizations_performed:
            logger.info(f"Performance optimization complete: {', '.join(optimizations_performed)}")
            return True, optimizations_performed
        else:
            logger.info("No optimizations were performed")
            return False, []
    
    @staticmethod
    def get_performance_report():
        """Get a report on current performance issues."""
        report = {
            "web_engine_cache_size": 0,
            "temp_files_count": 0,
            "dns_status": "unknown",
            "recommendations": []
        }
        
        try:
            # Check WebEngine cache size
            if platform.system() == "Windows":
                cache_paths = [
                    os.path.expanduser("~\\AppData\\Local\\TrackPro\\QtWebEngine"),
                    os.path.expanduser("~\\AppData\\Local\\Temp\\QtWebEngine")
                ]
            else:
                cache_paths = [
                    os.path.expanduser("~/.cache/TrackPro/QtWebEngine")
                ]
            
            total_cache_size = 0
            for cache_path in cache_paths:
                if os.path.exists(cache_path):
                    size = sum(os.path.getsize(os.path.join(dirpath, filename))
                             for dirpath, dirnames, filenames in os.walk(cache_path)
                             for filename in filenames)
                    total_cache_size += size
            
            report["web_engine_cache_size"] = total_cache_size / (1024 * 1024)  # MB
            
            # Check temp files
            temp_dir = tempfile.gettempdir()
            trackpro_temp_pattern = ["trackpro_", "discord_", "vjoy_", "telemetry_"]
            temp_count = 0
            
            for filename in os.listdir(temp_dir):
                for pattern in trackpro_temp_pattern:
                    if filename.lower().startswith(pattern.lower()):
                        temp_count += 1
                        break
            
            report["temp_files_count"] = temp_count
            
            # Generate recommendations
            if report["web_engine_cache_size"] > 50:  # More than 50MB
                report["recommendations"].append("Clear WebEngine cache (large size detected)")
                
            if report["temp_files_count"] > 10:
                report["recommendations"].append("Clear temporary files")
                
            report["recommendations"].append("Restart application after optimizations")
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            
        return report 