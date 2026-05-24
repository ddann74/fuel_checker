import streamlit as st
import pandas as pd
import requests
import math
from streamlit_searchbox import st_searchbox
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="Fuel Tracker Mobile", page_icon="⛽", layout="centered")
st.title("⛽ Automated Fuel Optimizer")

# --- FUNCTIONS ---
def get_location_js():
    return """
    <button id="btn" onclick="getLocation()" style="padding: 10px; cursor: pointer;">📍 Detect My Location</button>
    <script>
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition((pos) => {
                    const url = window.location.href.split('?')[0] + '?lat=' + pos.coords.latitude + '&lon=' + pos.coords.longitude;
                    window.location.href = url;
                });
            }
        }
    </script>
    """

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
        response = requests.get(url, params={"q": address_string, "format": "json", "limit": 1}, 
                                headers={"User-Agent": "FuelFinderApp/1.0"}, timeout=10)
        data = response.json()
        if response.status_code == 200 and data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        return None
    except: return None

def get_live_tomtom_distance(o_lat, o_lon, d_lat, d_lon):
    R = 6371.0
    dlat, dlon = math.radians(d_lat - o_lat), math.radians(d_lon - o_lon)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(o_lat)) * math.cos(math.radians(d_lat)) * math.sin(dlon/2)**2
    return (R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))) * 1.3

# --- UI INTERFACE ---
query_params = st.query_params
user_lat = float(query_params.get("lat", -34.397))
user_lon = float(query_params.get("lon", 150.893))

st.write(f"📍 Current Location: {user_lat:.4f}, {user_lon:.4f}")
components.html(get_location_js(), height=60)

with st.expander("🚗 Vehicle Settings & Route", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        fuel_economy = st.number_input("Fuel Economy (L/100km)", value=8.5)
        tank_capacity = st.number_input("Tank Capacity (L)", value=60)
        trip_mode = st.radio("Trip Mode", ["One Way", "Return"], horizontal=True)
    with col2:
        manual_dest = st_searchbox(search_address, label="Destination", placeholder="Enter destination...")
        fuel_gauge_pct = st.slider("Current Fuel (%)", 0, 100, 25, step=25)
    
    liters_to_fill = int(tank_capacity * (1 - (fuel_gauge_pct / 100.0)))
    multiplier = 2 if trip_mode == "Return" else 1

if st.button("🚀 Find On-Route Stations"):
    if not manual_dest:
        st.warning("Please select a destination.")
        st.stop()
        
    dest_coords = geocode_address(manual_dest)
    if not dest_coords:
        st.error("❌ Could not resolve destination.")
        st.stop()
        
    raw_stations = [
        {"Station": "Shell Fairy Meadow", "Price": 1.84, "Latitude": -34.3920, "Longitude": 150.8990, "Brand": "Shell"},
        {"Station": "7-Eleven Wollongong", "Price": 1.69, "Latitude": -34.4100, "Longitude": 150.8750, "Brand": "7-Eleven"},
        {"Station": "Metro Fuel North Wollongong", "Price": 1.65, "Latitude": -34.4130, "Longitude": 150.8950, "Brand": "Metro"},
        {"Station": "BP Corrimal", "Price": 1.89, "Latitude": -34.3810, "Longitude": 150.9050, "Brand": "BP"},
        {"Station": "Coles Express Towradgi", "Price": 1.79, "Latitude": -34.4020, "Longitude": 150.9020, "Brand": "Coles"}
    ]
    
    results = []
    base_dist = get_live_tomtom_distance(user_lat, user_lon, dest_coords[0], dest_coords[1])
    
    for row in raw_stations:
        leg_a = get_live_tomtom_distance(user_lat, user_lon, row['Latitude'], row['Longitude'])
        leg_b = get_live_tomtom_distance(row['Latitude'], row['Longitude'], dest_coords[0], dest_coords[1])
        detour_km = max(0.0, (leg_a + leg_b) - base_dist)
        
        if detour_km <= 5.0:
            # Scale distance fuel by multiplier
            total_trip_cost = (liters_to_fill * row['Price']) + (((detour_km * multiplier * fuel_economy) / 100.0) * row['Price'])
            results.append({
                "Station": row['Station'], "Brand": row['Brand'], 
                "Detour (km)": round(detour_km, 1),
                "Total Cost": total_trip_cost,
                "Real Price/L": total_trip_cost / liters_to_fill if liters_to_fill > 0 else row['Price'],
                "Navigate": f"waze://?ll={row['Latitude']},{row['Longitude']}&navigate=yes"
            })
    
    if not results:
        st.error("No stations found within 5km of your route.")
    else:
        df = pd.DataFrame(results).sort_values("Total Cost")
        df["Net Savings"] = df["Total Cost"].max() - df["Total Cost"]
        
        df_display = df.copy()
        df_display["Net Savings"] = df_display["Net Savings"].map("${:.2f}".format)
        df_display["Total Cost"] = df_display["Total Cost"].map("${:.2f}".format)
        df_display["Real Price/L"] = df_display["Real Price/L"].map("${:.3f}".format)
        
        st.dataframe(
            df_display[["Station", "Brand", "Detour (km)", "Real Price/L", "Net Savings", "Total Cost", "Navigate"]], 
            column_config={"Navigate": st.column_config.LinkColumn("🗺️ Action", display_text="Map")},
            hide_index=True
        )
