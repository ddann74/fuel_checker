import streamlit as st
import pandas as pd
import requests
import math
from streamlit_searchbox import st_searchbox

# --- CONFIGURATION ---
st.set_page_config(page_title="Fuel Tracker Mobile", page_icon="⛽", layout="centered")
st.title("⛽ Automated Fuel Optimizer")

# --- FUNCTIONS ---
def search_address(searchterm: str):
    if not searchterm or len(searchterm) < 3: return []
    url = "https://nominatim.openstreetmap.org/search"
    try:
        response = requests.get(url, params={"q": searchterm, "format": "json", "limit": 5}, 
                                headers={"User-Agent": "FuelFinderApp/1.0"}, timeout=3)
        return [res["display_name"] for res in response.json()]
    except: return []

def geocode_address(address_string):
    url = "https://nominatim.openstreetmap.org/search"
    try:
        response = requests.get(url, params={"q": searchterm, "format": "json", "limit": 1}, 
                                headers={"User-Agent": "FuelFinderApp/1.0"}, timeout=5)
        if response.status_code == 200 and response.json():
            return float(response.json()[0]["lat"]), float(response.json()[0]["lon"])
    except: return None

def get_live_tomtom_distance(o_lat, o_lon, d_lat, d_lon):
    R = 6371.0
    dlat, dlon = math.radians(d_lat - o_lat), math.radians(d_lon - o_lon)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(o_lat)) * math.cos(math.radians(d_lat)) * math.sin(dlon/2)**2
    return (R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))) * 1.3

# --- UI INTERFACE ---
with st.expander("🚗 Vehicle Settings & Route", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        fuel_economy = st.number_input("Fuel Economy (L/100km)", value=8.5)
        tank_capacity = st.number_input("Tank Capacity (L)", value=60)
    with col2:
        manual_dest = st_searchbox(search_address, label="Destination", placeholder="Enter destination...")
    
    fuel_gauge_pct = st.slider("Current Fuel (%)", 0, 100, 25)
    liters_to_fill = int(tank_capacity * (1 - (fuel_gauge_pct / 100.0)))

if st.button("🚀 Find On-Route Stations"):
    if not manual_dest:
        st.warning("Please select a destination.")
        st.stop()
        
    dest_coords = geocode_address(manual_dest)
    if not dest_coords:
        st.error("❌ Could not resolve destination.")
        st.stop()
        
    user_lat, user_lon = -34.397, 150.893
    raw_stations = [{"Station": "Shell Fairy Meadow", "Price": 1.84, "Latitude": -34.3920, "Longitude": 150.8990, "Brand": "Shell"},
                    {"Station": "7-Eleven Wollongong", "Price": 1.69, "Latitude": -34.4100, "Longitude": 150.8750, "Brand": "7-Eleven"}]
    
    results = []
    base_dist = get_live_tomtom_distance(user_lat, user_lon, dest_coords[0], dest_coords[1])
    
    for row in raw_stations:
        leg_a = get_live_tomtom_distance(user_lat, user_lon, row['Latitude'], row['Longitude'])
        leg_b = get_live_tomtom_distance(row['Latitude'], row['Longitude'], dest_coords[0], dest_coords[1])
        detour_km = max(0.0, (leg_a + leg_b) - base_dist)
        
        # Only include if detour is under 5km
        if detour_km <= 5.0:
            total_trip_cost = (liters_to_fill * row['Price']) + (((detour_km * fuel_economy) / 100.0) * row['Price'])
            results.append({
                "Station": row['Station'], "Brand": row['Brand'], 
                "Detour (km)": round(detour_km, 1),
                "Total Cost": total_trip_cost,
                "Navigate": f"waze://?ll={row['Latitude']},{row['Longitude']}&navigate=yes"
            })
    
    if not results:
        st.error("No stations found within 5km of your route.")
    else:
        df = pd.DataFrame(results).sort_values("Total Cost")
        st.dataframe(df, column_config={"Navigate": st.column_config.LinkColumn("🗺️ Action", display_text="Map")}, hide_index=True)
