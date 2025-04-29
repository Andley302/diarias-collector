"""
Update checker for the Diárias Collector application.
Checks for new versions from a GitHub JSON file and provides update notifications.
"""

import requests
import json
from packaging import version
from src.utils.version import VERSION

class UpdateChecker:
    """Class to check for updates from GitHub."""
    
    def __init__(self, github_user="Andley302", repo="diarias-collector", branch="development"):
        """Initialize the update checker with GitHub repository information."""
        self.github_user = github_user
        self.repo = repo
        self.current_version = VERSION
        self.latest_version = None
        self.release_url = f"https://github.com/{github_user}/{repo}/releases"
        self.version_json_url = f"https://raw.githubusercontent.com/{github_user}/{repo}/{branch}/version.json"
    
    def check_for_updates(self):
        """
        Check if a new version is available.
        
        Returns:
            tuple: (update_available, latest_version, release_url)
                - update_available (bool): True if an update is available
                - latest_version (str): The latest version string
                - release_url (str): URL to the releases page
        """
        try:
            response = requests.get(self.version_json_url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            self.latest_version = data.get("version")
            
            if not self.latest_version:
                return False, self.current_version, self.release_url
            
            current = version.parse(self.current_version)
            latest = version.parse(self.latest_version)
            
            return latest > current, self.latest_version, self.release_url
            
        except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
            print(f"Error checking for updates: {e}")
            return False, self.current_version, self.release_url
