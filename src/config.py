"""Configuration management for the Wine Chatbot application."""
import os
import streamlit as st
from pathlib import Path
from typing import Dict, Any

class Config:
    def __init__(self):
        self._config = {}
        self._load_config()

    def _load_config(self) -> None:
        # Load all sections from Streamlit secrets
        self._config = dict(st.secrets)
        
        # Ensure all required sections exist
        required_sections = ['postgres', 'google', 'mail', 'openai', 'app', 'mongodb', 'ai']
        for section in required_sections:
            if section not in self._config:
                self._config[section] = {}
        
        # Add Streamlit-specific configurations
        self._config['streamlit'] = {
            'page_title': st.secrets.get('streamlit', {}).get('page_title', 'Wine Chatbot'),
            'page_icon': st.secrets.get('streamlit', {}).get('page_icon', '🍷'),
            'layout': st.secrets.get('streamlit', {}).get('layout', 'centered'),
            'initial_sidebar_state': st.secrets.get('streamlit', {}).get('initial_sidebar_state', 'auto'),
        }

    def debug_secrets(self) -> dict:
        """Debug function to check the status of secrets loading.
        Returns a dictionary with debug information about secrets."""
        debug_info = {
            'secrets_loaded': hasattr(st, 'secrets'),
            'available_sections': list(st.secrets.keys()) if hasattr(st, 'secrets') else [],
            'missing_sections': [],
            'empty_sections': []
        }
        
        required_sections = ['postgres', 'google', 'mail', 'openai', 'app', 'mongodb', 'ai']
        for section in required_sections:
            if section not in self._config:
                debug_info['missing_sections'].append(section)
            elif not self._config[section]:
                debug_info['empty_sections'].append(section)
        
        return debug_info

    def get(self, section: str, key: str = None) -> Any:
        """Get a configuration value."""
        print(self._config)
        if key is None:
            return self._config.get(section, {})
        return self._config.get(section, {}).get(key)

    def get_streamlit_config(self) -> Dict[str, Any]:
        """Get all Streamlit-related configurations."""
        return self.get('streamlit')

# Create a singleton instance
config = Config()

# Streamlit configurations
STREAMLIT_CONFIG = {
    'page_title': os.getenv('STREAMLIT_PAGE_TITLE', 'Wine Chatbot'),
    'page_icon': os.getenv('STREAMLIT_PAGE_ICON', '🍷'),
    'layout': os.getenv('STREAMLIT_LAYOUT', 'centered'),
    'initial_sidebar_state': os.getenv('STREAMLIT_SIDEBAR_STATE', 'auto'),
}

# API configurations
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
MODEL_NAME = os.getenv('MODEL_NAME', 'gemini-2.0-flash-lite')

# Memory configurations
MEMORY_TYPE = os.getenv('MEMORY_TYPE', 'conversation')
MAX_MEMORY_ITEMS = int(os.getenv('MAX_MEMORY_ITEMS', '50'))

# Chat configurations
MAX_TOKENS = int(os.getenv('MAX_TOKENS', '2000'))
TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))

def get_streamlit_config():
    """Get all Streamlit-related configurations."""
    return STREAMLIT_CONFIG


# Get debug information about secrets
debug_info = config.debug_secrets()

# Print the debug information in a readable format
print("\n=== Secrets Debug Information ===")
print(f"Secrets loaded: {debug_info['secrets_loaded']}")
print("\nAvailable sections:")
for section in debug_info['available_sections']:
    print(f"- {section}")

print("\nMissing required sections:")
for section in debug_info['missing_sections']:
    print(f"- {section}")

print("\nEmpty sections (need configuration):")
for section in debug_info['empty_sections']:
    print(f"- {section}")