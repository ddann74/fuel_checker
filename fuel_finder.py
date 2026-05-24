import streamlit as st
import pandas as pd
import requests
import math
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
HARDCODED_TOMTOM_API_KEY = "PASTE_YOUR_FREE_TOMTOM_KEY_HERE"
HARDCODED_NSW_API_KEY = "1MYSRAx5yvqHUZc6VGtxix6oMA2qgfRT"
HARDCODED_NSW_AUTH_HEADER = "Basic MU1ZU1JBeDV5dnFIVVpjNlZHdHhpeDZvTUEycWdmUlQ6Qk12V2FjdzE1RXQ4dUZHRg=="

st.set_page_config(page_title="Fuel Tracker Mobile", page_icon="⛽", layout="centered")
st.title("⛽ Automated Fuel Optimizer")

# --- FUNCTIONS ---
def get_nsw_bearer_token():
    url = "https://api.onegov.nsw.gov.au/oauth/client_credential/accesstoken"
    headers = {"Authorization": HARDCODED_NSW_AUTH_HEADER.strip(), "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers, params={"grant_type": "client_credentials"}, timeout=10)
        return response.json().get("access_token") if response.status_code == 200 else None
    except: return None

def geocode_address(address_string):
    """Converts any typed address into GPS coordinates."""
    if not address_string: return None
    url = "https://nominatim.openstreetmap.org/search"
    try:
        response = requests.get(url, headers={"User-Agent": "FuelFinderMobileApp/1.0"}, 
                                params={"q": address_string, "format": "json", "limit": 1}, timeout=5)
        if response.status_code == 200 and response.json():
            return float(response.json()[0]["lat"]), float(response.json()[0]["lon"])
    except: return None

def get_live_tomtom_distance(o_lat, o_lon, d_lat, d_lon):
    R = 6371.0
    dlat, dlon = math.radians(d_lat - o_lat), math.radians(d_lon - o_lon)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(o_lat)) * math.cos(math.radians(d_lat)) * math.sin(dlon/2)**2
    return (R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))) * 1.3

# --- UI INTERFACE ---
with st.expander("🚗 Vehicle Settings & Planned Route", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        fuel_economy = st.number_input("Fuel Economy (L/100km)", value=8.5)
        tank_capacity = st.number_input("Total Tank Capacity (Liters)", value=60)
    with col2:
        fuel_type_selection = st.selectbox("Select Fuel Type", options=["E10", "U91", "P95", "P98", "Diesel"])
        # 🆕 Swapped dropdown for manual text input
        manual_dest = st.text_input("Enter Destination Address", value="Wollongong CBD, NSW")
    
    fuel_gauge_pct = st.slider("Current Fuel Gauge (%)", 0, 100, 25)
    liters_to_fill = int(tank_capacity * (1 - (fuel_gauge_pct / 100.0)))

if st.button("🚀 Auto-Scan & Optimize Best Fuel Value", type="primary"):
    # 1. Resolve typed destination
    dest_coords = geocode_address(manual_dest)
    if not dest_coords:
        st.error("❌ Could not find that destination address.")
        st.stop()
    dest_lat, dest_lon = dest_coords
    
    # Baseline location (Fairy Meadow)
    user_lat, user_lon = -34.397, 150.893
    
    # Fetch data (simplified for demonstration)
    raw_stations = [{"Station": "Shell Fairy Meadow", "Price": 1.84, "Latitude": -34.3920, "Longitude": 150.8990, "Brand": "Shell"},
                    {"Station": "7-Eleven Wollongong", "Price": 1.69, "Latitude": -34.4100, "Longitude": 150.8750, "Brand": "7-Eleven"}]
    
    base_dist = get_live_tomtom_distance(user_lat, user_lon, dest_lat, dest_lon)
    results = []
    
    for row in raw_stations:
        leg_a = get_live_tomtom_distance(user_lat, user_lon, row['Latitude'], row['Longitude'])
        leg_b = get_live_tomtom_distance(row['Latitude'], row['Longitude'], dest_lat, dest_lon)
        detour_km = max(0.0, (leg_a + leg_b) - base_dist)
        
        cost_at_pump = liters_to_fill * row['Price']
        cost_detour_fuel = ((detour_km * fuel_economy) / 100.0) * row['Price']
        total_trip_cost = cost_at_pump + cost_detour_fuel
        
        results.append({
            "Station": row['Station'], "Brand": row['Brand'], "Price": row['Price'],
            "Added Detour": detour_km, "Total Trip Cost": total_trip_cost,
            "Navigate": f"https://waze.com/ul?ll={row['Latitude']},{row['Longitude']}&navigate=yes"
        })
    
    df = pd.DataFrame(results).sort_values("Total Trip Cost")
    
    # Display table
    st.dataframe(df, hide_index=True)
