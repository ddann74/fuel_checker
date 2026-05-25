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
        tank_capacity = st.number_input("Total Tank Capacity (L)", value=60)
        trip_mode = st.radio("Trip Mode", ["One Way", "Return"], horizontal=True)
    with col2:
        fuel_gauge_pct = st.slider("Current Fuel (%)", 0, 100, 25, step=25)
        manual_volume = st.number_input("Fuel Required (L) - Optional", min_value=0.0, value=0.0)

    liters_to_fill = manual_volume if manual_volume > 0 else int(tank_capacity * (1 - (fuel_gauge_pct / 100.0)))
    multiplier = 2 if trip_mode == "Return" else 1

manual_dest = st_searchbox(search_address, label="Destination", placeholder="Enter destination...")

if st.button("🚀 Find Profitable Stations (>$5 Savings)"):
    if not manual_dest:
        st.warning("Please select a destination.")
        st.stop()
        
    dest_coords = geocode_address(manual_dest)
    if not dest_coords:
        st.error("❌ Could not resolve destination.")
        st.stop()
        
    raw_stations = [
        {"Station": "Ampol Urbanista", "Price": 1.88, "Latitude": -34.0321, "Longitude": 150.7560, "Brand": "Ampol"},
        {"Station": "Enhance Smeaton Grange", "Price": 1.85, "Latitude": -34.0418, "Longitude": 150.7614, "Brand": "Enhance"},
        {"Station": "EG Ampol Mount Annan", "Price": 1.90, "Latitude": -34.0469, "Longitude": 150.7609, "Brand": "Ampol"},
        {"Station": "Shell Fairy Meadow", "Price": 1.84, "Latitude": -34.3920, "Longitude": 150.8990, "Brand": "Shell"},
        {"Station": "7-Eleven Wollongong", "Price": 1.69, "Latitude": -34.4100, "Longitude": 150.8750, "Brand": "7-Eleven"}
    ]
    
    results = []
    base_dist = get_live_tomtom_distance(user_lat, user_lon, dest_coords[0], dest_coords[1])
    
    # Calculate Max Price for Savings Baseline
    max_price = max(s['Price'] for s in raw_stations)
    baseline_cost = (liters_to_fill * max_price)
    
    for row in raw_stations:
        leg_a = get_live_tomtom_distance(user_lat, user_lon, row['Latitude'], row['Longitude'])
        leg_b = get_live_tomtom_distance(row['Latitude'], row['Longitude'], dest_coords[0], dest_coords[1])
        detour_km = max(0.0, (leg_a + leg_b) - base_dist)
        
        total_trip_cost = (liters_to_fill * row['Price']) + (((detour_km * multiplier * fuel_economy) / 100.0) * row['Price'])
        net_savings = baseline_cost - total_trip_cost
        
        # Only include if savings >= $5
        if net_savings >= 5.0:
            results.append({
                "Station": row['Station'], "Brand": row['Brand'], 
                "Net Savings": net_savings,
                "Detour (km)": round(detour_km, 1),
                "On-Route": "✅ Yes" if detour_km <= 5.0 else "❌ No",
                "Real Price/L": total_trip_cost / liters_to_fill if liters_to_fill > 0 else row['Price'],
                "Total Cost": total_trip_cost,
                "Navigate": f"waze://?ll={row['Latitude']},{row['Longitude']}&navigate=yes"
            })
    
    if not results:
        st.warning("No stations found that provide at least $5.00 in net savings.")
    else:
        df = pd.DataFrame(results).sort_values("Net Savings", ascending=False)
        
        # Display Formatting
        df_display = df.copy()
        df_display["Net Savings"] = df_display["Net Savings"].map("${:.2f}".format)
        df_display["Total Cost"] = df_display["Total Cost"].map("${:.2f}".format)
        df_display["Real Price/L"] = df_display["Real Price/L"].map("${:.3f}".format)
        
        st.dataframe(
            df_display[["Station", "Brand", "Net Savings", "Detour (km)", "On-Route", "Real Price/L", "Total Cost", "Navigate"]], 
            column_config={"Navigate": st.column_config.LinkColumn("🗺️ Action", display_text="Map")},
            hide_index=True
        )
