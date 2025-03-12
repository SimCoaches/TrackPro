import logging
import sqlite3
import os
import json
import time
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

class DataManager:
    """Manages data storage and retrieval for the Race Coach feature."""
    
    def __init__(self, db_path=None):
        """Initialize the data manager.
        
        Args:
            db_path: Path to the SQLite database file. If None, a default path is used.
        """
        try:
            if db_path is None:
                # Create default path in user's documents folder
                docs_path = Path(os.path.expanduser("~/Documents/TrackPro"))
                try:
                    docs_path.mkdir(parents=True, exist_ok=True)
                    db_path = docs_path / "race_coach.db"
                except Exception as e:
                    logger.warning(f"Could not create directory in Documents: {e}")
                    # Fall back to a local file
                    db_path = "race_coach.db"
            
            # Handle relative paths
            if not os.path.isabs(db_path):
                # Use the current directory
                db_path = os.path.abspath(db_path)
            
            self.db_path = str(db_path)
            self._init_database()
            
            logger.info(f"Data manager initialized with database at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing data manager: {e}")
            raise
    
    def _init_database(self):
        """Initialize the database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            iracing_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            configuration TEXT,
            length REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            class TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY,
            driver_id INTEGER,
            track_id INTEGER,
            car_id INTEGER,
            session_type TEXT,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES drivers (id),
            FOREIGN KEY (track_id) REFERENCES tracks (id),
            FOREIGN KEY (car_id) REFERENCES cars (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS laps (
            id INTEGER PRIMARY KEY,
            session_id INTEGER,
            lap_number INTEGER,
            lap_time REAL,
            is_valid BOOLEAN,
            telemetry_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sectors (
            id INTEGER PRIMARY KEY,
            lap_id INTEGER,
            sector_number INTEGER,
            sector_time REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lap_id) REFERENCES laps (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS super_laps (
            id INTEGER PRIMARY KEY,
            track_id INTEGER,
            car_id INTEGER,
            lap_time REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT,
            FOREIGN KEY (track_id) REFERENCES tracks (id),
            FOREIGN KEY (car_id) REFERENCES cars (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Database schema initialized")
    
    def get_or_create_driver(self, name, iracing_id=None):
        """Get or create a driver record.
        
        Args:
            name: The driver's name
            iracing_id: The driver's iRacing ID (optional)
            
        Returns:
            The driver ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if driver exists
        cursor.execute(
            "SELECT id FROM drivers WHERE name=? AND (iracing_id=? OR (iracing_id IS NULL AND ? IS NULL))",
            (name, iracing_id, iracing_id)
        )
        result = cursor.fetchone()
        
        if result:
            driver_id = result[0]
        else:
            # Create new driver
            cursor.execute(
                "INSERT INTO drivers (name, iracing_id) VALUES (?, ?)",
                (name, iracing_id)
            )
            driver_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return driver_id
    
    def get_or_create_track(self, name, configuration=None, length=None):
        """Get or create a track record.
        
        Args:
            name: The track name
            configuration: The track configuration (optional)
            length: The track length in meters (optional)
            
        Returns:
            The track ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if track exists
        cursor.execute(
            "SELECT id FROM tracks WHERE name=? AND (configuration=? OR (configuration IS NULL AND ? IS NULL))",
            (name, configuration, configuration)
        )
        result = cursor.fetchone()
        
        if result:
            track_id = result[0]
            
            # Update length if provided and different
            if length is not None:
                cursor.execute(
                    "UPDATE tracks SET length=? WHERE id=? AND (length IS NULL OR length!=?)",
                    (length, track_id, length)
                )
        else:
            # Create new track
            cursor.execute(
                "INSERT INTO tracks (name, configuration, length) VALUES (?, ?, ?)",
                (name, configuration, length)
            )
            track_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return track_id
    
    def get_or_create_car(self, name, car_class=None):
        """Get or create a car record.
        
        Args:
            name: The car name
            car_class: The car class (optional)
            
        Returns:
            The car ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if car exists
        cursor.execute(
            "SELECT id FROM cars WHERE name=?",
            (name,)
        )
        result = cursor.fetchone()
        
        if result:
            car_id = result[0]
            
            # Update class if provided and different
            if car_class is not None:
                cursor.execute(
                    "UPDATE cars SET class=? WHERE id=? AND (class IS NULL OR class!=?)",
                    (car_class, car_id, car_class)
                )
        else:
            # Create new car
            cursor.execute(
                "INSERT INTO cars (name, class) VALUES (?, ?)",
                (name, car_class)
            )
            car_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return car_id
    
    def create_session(self, driver_id, track_id, car_id, session_type="Practice"):
        """Create a new session record.
        
        Args:
            driver_id: The driver ID
            track_id: The track ID
            car_id: The car ID
            session_type: The session type (default: "Practice")
            
        Returns:
            The session ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_time = time.time()
        
        cursor.execute(
            "INSERT INTO sessions (driver_id, track_id, car_id, session_type, start_time) VALUES (?, ?, ?, ?, ?)",
            (driver_id, track_id, car_id, session_type, start_time)
        )
        session_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def end_session(self, session_id):
        """End a session by setting its end time.
        
        Args:
            session_id: The session ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        end_time = time.time()
        
        cursor.execute(
            "UPDATE sessions SET end_time=? WHERE id=?",
            (end_time, session_id)
        )
        
        conn.commit()
        conn.close()
    
    def add_lap(self, session_id, lap_number, lap_time, is_valid=True, telemetry=None):
        """Add a lap record.
        
        Args:
            session_id: The session ID
            lap_number: The lap number
            lap_time: The lap time in seconds
            is_valid: Whether the lap is valid (default: True)
            telemetry: Telemetry data for the lap (optional)
            
        Returns:
            The lap ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        telemetry_file = None
        
        # Save telemetry data to file if provided
        if telemetry is not None:
            try:
                # Create directory for telemetry files if it doesn't exist
                telemetry_dir = os.path.join(os.path.dirname(self.db_path), "telemetry")
                os.makedirs(telemetry_dir, exist_ok=True)
                
                # Generate filename based on session ID and lap number
                telemetry_file = os.path.join(telemetry_dir, f"session_{session_id}_lap_{lap_number}.json")
                
                # Save telemetry data to file
                with open(telemetry_file, 'w') as f:
                    json.dump(telemetry, f)
            except Exception as e:
                logger.error(f"Error saving telemetry data: {e}")
                telemetry_file = None
        
        cursor.execute(
            "INSERT INTO laps (session_id, lap_number, lap_time, is_valid, telemetry_file) VALUES (?, ?, ?, ?, ?)",
            (session_id, lap_number, lap_time, is_valid, telemetry_file)
        )
        lap_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return lap_id
    
    def add_sector(self, lap_id, sector_number, sector_time):
        """Add a sector time record.
        
        Args:
            lap_id: The lap ID
            sector_number: The sector number
            sector_time: The sector time in seconds
            
        Returns:
            The sector ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO sectors (lap_id, sector_number, sector_time) VALUES (?, ?, ?)",
            (lap_id, sector_number, sector_time)
        )
        sector_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return sector_id
    
    def get_best_lap(self, track_id, car_id, driver_id=None):
        """Get the best lap time for a track/car combination.
        
        Args:
            track_id: The track ID
            car_id: The car ID
            driver_id: The driver ID (optional, if None returns best overall)
            
        Returns:
            A tuple of (lap_id, lap_time) or None if no laps found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if driver_id is None:
            # Get best overall lap
            cursor.execute('''
            SELECT l.id, l.lap_time
            FROM laps l
            JOIN sessions s ON l.session_id = s.id
            WHERE s.track_id = ? AND s.car_id = ? AND l.is_valid = 1
            ORDER BY l.lap_time ASC
            LIMIT 1
            ''', (track_id, car_id))
        else:
            # Get best lap for specific driver
            cursor.execute('''
            SELECT l.id, l.lap_time
            FROM laps l
            JOIN sessions s ON l.session_id = s.id
            WHERE s.track_id = ? AND s.car_id = ? AND s.driver_id = ? AND l.is_valid = 1
            ORDER BY l.lap_time ASC
            LIMIT 1
            ''', (track_id, car_id, driver_id))
        
        result = cursor.fetchone()
        
        conn.close()
        
        return result if result else None
    
    def get_best_sectors(self, track_id, car_id, max_sectors=3):
        """Get the best sector times for a track/car combination.
        
        Args:
            track_id: The track ID
            car_id: The car ID
            max_sectors: The maximum number of sectors (default: 3)
            
        Returns:
            A list of (sector_number, sector_time, driver_id) tuples
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        best_sectors = []
        
        for sector_num in range(1, max_sectors + 1):
            cursor.execute('''
            SELECT sect.sector_number, sect.sector_time, s.driver_id
            FROM sectors sect
            JOIN laps l ON sect.lap_id = l.id
            JOIN sessions s ON l.session_id = s.id
            WHERE s.track_id = ? AND s.car_id = ? AND sect.sector_number = ? AND l.is_valid = 1
            ORDER BY sect.sector_time ASC
            LIMIT 1
            ''', (track_id, car_id, sector_num))
            
            result = cursor.fetchone()
            
            if result:
                best_sectors.append(result)
        
        conn.close()
        
        return best_sectors
    
    def save_super_lap(self, track_id, car_id, lap_time, data):
        """Save a super lap record.
        
        Args:
            track_id: The track ID
            car_id: The car ID
            lap_time: The lap time in seconds
            data: The super lap data (will be stored as JSON)
            
        Returns:
            The super lap ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert data to JSON string
        data_json = json.dumps(data)
        
        cursor.execute(
            "INSERT INTO super_laps (track_id, car_id, lap_time, data) VALUES (?, ?, ?, ?)",
            (track_id, car_id, lap_time, data_json)
        )
        super_lap_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return super_lap_id
    
    def get_super_lap(self, track_id, car_id):
        """Get the latest super lap for a track/car combination.
        
        Args:
            track_id: The track ID
            car_id: The car ID
            
        Returns:
            A tuple of (super_lap_id, lap_time, data) or None if no super lap found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, lap_time, data FROM super_laps WHERE track_id=? AND car_id=? ORDER BY created_at DESC LIMIT 1",
            (track_id, car_id)
        )
        
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            super_lap_id, lap_time, data_json = result
            data = json.loads(data_json)
            return (super_lap_id, lap_time, data)
        
        return None 