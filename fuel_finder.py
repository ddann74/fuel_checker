import streamlit as st
import pandas as pd
import requests
import math
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

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
with st.expander("📍 Location & Route Configurator", expanded=True):
    start_addr = st.text_input("📍 Starting Address", value="Fairy Meadow, NSW")
    dest_addr = st.text_input("🏁 Final Destination", value="Wollongong CBD, NSW")
    fuel_economy = st.number_input("Fuel Economy (L/100km)", value=8.5)
    tank_cap = st.number_input("Tank Capacity (L)", value=60)
    fuel_pct = st.slider("Fuel Gauge (%)", 0, 100, 25)
    liters_to_fill = int(tank_cap * (1 - (fuel_pct / 100.0)))

if st.button("🚀 Auto-Scan & Optimize"):
    start_lat, start_lon = geocode_address(start_addr) or (-34.397, 150.893)
    dest_lat, dest_lon = geocode_address(dest_addr) or (-34.4278, 150.8931)
    
    # Using dummy data for demonstration logic
    raw_stations = [{"Station": "Shell Fairy Meadow", "Price": 1.84, "Latitude": -34.3920, "Longitude": 150.8990, "Brand": "Shell"},
                    {"Station": "7-Eleven Wollongong", "Price": 1.69, "Latitude": -34.4100, "Longitude": 150.8750, "Brand": "7-Eleven"}]
    
    base_dist = get_live_tomtom_distance(start_lat, start_lon, dest_lat, dest_lon)
    results = []
    
    for row in raw_stations:
        leg_a = get_live_tomtom_distance(start_lat, start_lon, row['Latitude'], row['Longitude'])
        leg_b = get_live_tomtom_distance(row['Latitude'], row['Longitude'], dest_lat, dest_lon)
        detour_km = max(0.0, (leg_a + leg_b) - base_dist)
        
        cost_at_pump = liters_to_fill * row['Price']
        cost_detour_fuel = ((detour_km * fuel_economy) / 100.0) * row['Price']
        total_trip_cost = cost_at_pump + cost_detour_fuel
        
        results.append({
            "Station": row['Station'], "Brand": row['Brand'], "Price": row['Price'],
            "Added Detour": detour_km, "Total Trip Cost": total_trip_cost,
            "True Cost/L": total_trip_cost / liters_to_fill,
            "Navigate": f"https://waze.com/ul?ll={row['Latitude']},{row['Longitude']}&navigate=yes"
        })
    
    df = pd.DataFrame(results).sort_values("Total Trip Cost")
    df["Net Savings"] = df["Total Trip Cost"].max() - df["Total Trip Cost"]
    df["Net Savings"] = df["Net Savings"].clip(lower=0.0)
    
    display_df = df.copy()
    display_df["Price"] = display_df["Price"].map("${:.2f}".format)
    display_df["Added Detour"] = display_df["Added Detour"].map("{:.2f} km".format)
    display_df["Net Savings"] = display_df["Net Savings"].map("${:.2f}".format)
    display_df["True Cost/L"] = display_df["True Cost/L"].map("${:.3f}".format)
    display_df["Total Trip Cost"] = display_df["Total Trip Cost"].map("${:.2f}".format)
    
    st.dataframe(
        display_df[["Station", "Brand", "Net Savings", "True Cost/L", "Total Trip Cost", "Added Detour", "Navigate"]],
        column_config={"Navigate": st.column_config.LinkColumn("🏎️ Action", display_text="Open Waze")},
        hide_index=True
    )
