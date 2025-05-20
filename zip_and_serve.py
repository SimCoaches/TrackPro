#!/usr/bin/env python3
"""
zip_and_serve.py - Zips the TrackPro project and serves it via HTTP.

This script creates a zip archive of the project (excluding certain directories)
and starts a simple HTTP server to make the zip file available for download.
"""

import os
import zipfile
import http.server
import socketserver
import socket
from pathlib import Path
import sys

def create_dist_folder():
    """Create dist folder if it doesn't exist."""
    dist_path = Path("dist")
    dist_path.mkdir(exist_ok=True)
    return dist_path

def zip_project(dist_path):
    """Zip the project directory, excluding specified folders."""
    excluded_dirs = ['venv', '.git', '__pycache__', 'dist']
    zip_path = dist_path / "TrackPro.zip"
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Start from the current directory
            base_dir = Path(".")
            
            for root, dirs, files in os.walk(base_dir):
                # Remove excluded directories from dirs list to avoid walking them
                dirs[:] = [d for d in dirs if d not in excluded_dirs]
                
                # Add all files
                for file in files:
                    file_path = Path(root) / file
                    # Skip the zip file itself if it already exists
                    if file_path == zip_path:
                        continue
                    # Add file to zip with a relative path
                    zipf.write(file_path, file_path.relative_to(base_dir))
        
        return zip_path.absolute()
    except Exception as e:
        print(f"Error creating zip file: {e}")
        sys.exit(1)

def start_server(dist_path):
    """Start a simple HTTP server serving the dist directory."""
    os.chdir(dist_path)
    
    # Get the local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    port = 8000
    handler = http.server.SimpleHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"\nServer started at port {port}")
            print(f"Download your zip file at:")
            print(f"  http://localhost:{port}/TrackPro.zip")
            print(f"  http://{local_ip}:{port}/TrackPro.zip (local network)")
            print("\nPress Ctrl+C to stop the server")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

def main():
    """Main function to orchestrate the process."""
    try:
        print("Creating dist folder...")
        dist_path = create_dist_folder()
        
        print("Zipping project directory...")
        zip_file_path = zip_project(dist_path)
        
        print(f"Zip file created: {zip_file_path}")
        
        print("Starting HTTP server...")
        start_server(dist_path)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 