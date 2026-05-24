"""
Configuration file for API keys and settings
Store your API keys here (DO NOT COMMIT THIS FILE TO PUBLIC REPOS)
"""

import os
from dotenv import load_dotenv

load_dotenv()

# FuelCheck API Configuration
FUELCHECK_API_KEY = os.getenv("FUELCHECK_API_KEY", "your_fuelcheck_api_key_here")
FUELCHECK_BASE_URL = "https://fuelcheck.nsw.gov.au/api/v1"

# TomTom API Configuration
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "your_tomtom_api_key_here")
TOMTOM_BASE_URL = "https://api.tomtom.com/routing/1/calculateRoute"

# App Settings
SEARCH_RADIUS_KM = 10
DEFAULT_FUEL_ECONOMY = 8.5
DEFAULT_TANK_CAPACITY = 60
MAX_DETOUR_KM = 15

# Brands to filter (leave empty to show all)
FUEL_BRANDS = ["Shell", "BP", "Caltex", "Ampol", "Priceline"]
