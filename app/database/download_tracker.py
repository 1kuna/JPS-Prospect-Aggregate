import os
import json
import datetime
from pathlib import Path
from src.utils.file_utils import ensure_directory, find_files
from src.utils.logger import logger

# Set up logging using the centralized utility
logger = logger.bind(name="database.download_tracker")

class DownloadTracker:
    """
    A class for tracking download timestamps for multiple data sources.
    Uses a JSON file to store timestamps for each data source.
    """
    
    def __init__(self):
        """Initialize the DownloadTracker."""
        # Get the data directory
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
        
        # Ensure the data directory exists
        self.tracker_dir = os.path.join(self.data_dir, 'tracker')
        ensure_directory(self.tracker_dir)
        
        # Path to the timestamps file
        self.timestamps_file = os.path.join(self.tracker_dir, "download_timestamps.json")
        
        # Load existing timestamps or create a new file
        self.timestamps = self._load_timestamps()
    
    def _load_timestamps(self):
        """Load timestamps from the JSON file or create a new file if it doesn't exist."""
        if os.path.exists(self.timestamps_file):
            try:
                with open(self.timestamps_file, 'r') as f:
                    timestamps = json.load(f)
                logger.info(f"Loaded timestamps from {self.timestamps_file}")
                return timestamps
            except Exception as e:
                logger.warning(f"Error loading timestamps file: {e}")
                # If there's an error, create a new timestamps dictionary
                return {}
        else:
            logger.info(f"No timestamps file found at {self.timestamps_file}, creating a new one")
            return {}
    
    def _save_timestamps(self):
        """Save timestamps to the JSON file."""
        try:
            with open(self.timestamps_file, 'w') as f:
                json.dump(self.timestamps, f, indent=2)
            logger.info(f"Saved timestamps to {self.timestamps_file}")
        except Exception as e:
            logger.error(f"Error saving timestamps file: {e}")
    
    def get_last_download_time(self, source_name):
        """
        Get the last download time for a specific data source.
        
        Args:
            source_name (str): The name of the data source.
            
        Returns:
            datetime.datetime or None: The last download time as a datetime object, or None if not found.
        """
        if source_name in self.timestamps:
            try:
                timestamp_str = self.timestamps[source_name]
                return datetime.datetime.fromisoformat(timestamp_str)
            except Exception as e:
                logger.warning(f"Error parsing timestamp for {source_name}: {e}")
                return None
        else:
            logger.info(f"No timestamp found for {source_name}")
            return None
    
    def set_last_download_time(self, source_name, timestamp=None):
        """
        Set the last download time for a specific data source.
        
        Args:
            source_name (str): The name of the data source.
            timestamp (datetime.datetime, optional): The timestamp to set. Defaults to current time.
        """
        if timestamp is None:
            timestamp = datetime.datetime.now()
        
        self.timestamps[source_name] = timestamp.isoformat()
        self._save_timestamps()
        logger.info(f"Set last download time for {source_name} to {timestamp.isoformat()}")
    
    def should_download(self, source_name, interval_hours=24):
        """
        Check if a download should be performed for a specific data source based on the interval.
        
        Args:
            source_name (str): The name of the data source.
            interval_hours (int, optional): The interval in hours. Defaults to 24.
            
        Returns:
            bool: True if a download should be performed, False otherwise.
        """
        last_download_time = self.get_last_download_time(source_name)
        
        if last_download_time is None:
            logger.info(f"No previous download time found for {source_name}, should download")
            return True
        
        # Calculate time difference
        current_time = datetime.datetime.now()
        time_diff = current_time - last_download_time
        
        # Convert interval to seconds
        interval_seconds = interval_hours * 60 * 60
        
        # Check if the time difference is greater than the interval
        if time_diff.total_seconds() >= interval_seconds:
            logger.info(f"{source_name} was last downloaded {time_diff.total_seconds() / 3600:.2f} hours ago (more than {interval_hours} hours), should download")
            return True
        else:
            logger.info(f"{source_name} was last downloaded {time_diff.total_seconds() / 3600:.2f} hours ago (less than {interval_hours} hours), no need to download")
            return False
    
    def verify_file_exists(self, source_name, file_pattern, min_size=0):
        """
        Verify that a file matching the pattern exists and is not empty.
        
        Args:
            source_name (str): The name of the data source
            file_pattern (str): The pattern to match files against (e.g., "*.csv")
            min_size (int): Minimum file size in bytes
            
        Returns:
            bool: True if a valid file exists, False otherwise
        """
        source_dir = os.path.join(self.data_dir, 'downloads', source_name.lower().replace(' ', '_'))
        
        if not os.path.exists(source_dir):
            logger.warning(f"Source directory not found for {source_name}: {source_dir}")
            return False
        
        files = find_files(source_dir, file_pattern, min_size=min_size)
        
        if not files:
            logger.warning(f"No valid files found for {source_name} matching pattern {file_pattern}")
            return False
        
        logger.info(f"Found {len(files)} valid file(s) for {source_name}")
        return True

# Create a singleton instance
download_tracker = DownloadTracker() 