import json
import os
from pathlib import Path
from typing import Any, Dict


class ConfigManager:
    """Manages application configuration stored in gp-management.json"""
    
    DEFAULT_CONFIG = {
        "api_url": "http://127.0.0.1:8000"
    }
    
    def __init__(self, config_file: str = "gp-management.json"):
        """Initialize config manager with a config file path"""
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """Load configuration from file, creating with defaults if it doesn't exist"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = self.DEFAULT_CONFIG.copy()
                self.save()
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}. Using defaults.")
            self.config = self.DEFAULT_CONFIG.copy()
    
    def save(self) -> None:
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save it"""
        self.config[key] = value
        self.save()
    
    def get_api_url(self) -> str:
        """Get the API URL from config"""
        return self.get("api_url", self.DEFAULT_CONFIG["api_url"])
    
    def set_api_url(self, url: str) -> None:
        """Save the API URL to config"""
        self.set("api_url", url)
