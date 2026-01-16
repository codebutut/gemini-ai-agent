import os
import unittest
from pathlib import Path
from unittest.mock import patch

# Create a dummy .env file for testing
with open(".env.test", "w") as f:
    f.write("GOOGLE_API_KEY=test_key_from_env_file")

# Mock the environment to simulate a fresh start
with patch.dict(os.environ, {}, clear=True):
    # We need to reload the module to trigger the top-level load_dotenv
    # But since we can't easily reload modules in this environment without side effects,
    # we will test the AppConfig logic directly.
    
    # First, ensure load_dotenv works
    from dotenv import load_dotenv
    load_dotenv(".env.test")
    
    if os.environ.get("GOOGLE_API_KEY") != "test_key_from_env_file":
        print("FAIL: load_dotenv did not load the key.")
        exit(1)
        
    # Now test AppConfig sync
    from gemini_agent.config.app_config import AppConfig
    
    # Create a dummy settings file
    settings_path = Path("settings_test.json")
    if settings_path.exists():
        settings_path.unlink()
        
    config = AppConfig(config_file=settings_path)
    
    # Check if config picked up the key from env
    if config.api_key != "test_key_from_env_file":
        print(f"FAIL: AppConfig did not pick up key from env. Got: {config.api_key}")
        exit(1)
        
    # Now test setting the key in config updates env
    config.api_key = "new_key_from_config"
    if os.environ.get("GOOGLE_API_KEY") != "new_key_from_config":
        print(f"FAIL: Setting config.api_key did not update os.environ. Got: {os.environ.get('GOOGLE_API_KEY')}")
        exit(1)
        
    print("SUCCESS: Environment variable sync works correctly.")

# Cleanup
if os.path.exists(".env.test"):
    os.remove(".env.test")
if os.path.exists("settings_test.json"):
    os.remove("settings_test.json")
