"""
FuelCheck API Integration
Handles fuel price data from FuelCheck NSW API
"""

import requests
import streamlit as st
from config import FUELCHECK_API_KEY, FUELCHECK_BASE_URL, SEARCH_RADIUS_KM

@st.cache_data(ttl=3600)
def get_fuel_prices(latitude, longitude):
    """
    Fetch fuel prices from FuelCheck NSW API
    
    Args:
        latitude: Station latitude
        longitude: Station longitude
    
    Returns:
        List of fuel stations with prices
    """
    try:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius": SEARCH_RADIUS_KM,
            "apikey": FUELCHECK_API_KEY
        }
        
        response = requests.get(
            f"{FUELCHECK_BASE_URL}/fuel/prices",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        stations = []
        
        for station in data.get("stations", []):
            stations.append({
                "id": station.get("id"),
                "name": station.get("name"),
                "brand": station.get("brand"),
                "address": station.get("address"),
                "latitude": station.get("latitude"),
                "longitude": station.get("longitude"),
                "price": float(station.get("price", 0)),
                "fuel_type": station.get("fuel_type", "ULP"),
                "last_updated": station.get("last_updated")
            })
        
        return stations
    
    except requests.exceptions.RequestException as e:
        st.error(f"❌ FuelCheck API Error: {str(e)}")
        return []
    except Exception as e:
        st.error(f"❌ Error processing fuel data: {str(e)}")
        return []

def get_cheapest_fuel(stations):
    """
    Find the cheapest fuel station from list
    
    Args:
        stations: List of fuel stations
    
    Returns:
        Cheapest station or None
    """
    if not stations:
        return None
    
    return min(stations, key=lambda x: x["price"])
