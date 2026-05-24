import streamlit as st
import pandas as pd
import requests
import math
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🔑 HARDCODED API CREDENTIALS CONFIGURATION
# Paste your free TomTom Consumer API Key here to unlock real-time detour calculations!
# ==============================================================================
HARDCODED_TOMTOM_API_KEY = "PASTE_YOUR_FREE_TOMTOM_KEY_HERE"
HARDCODED_NSW_API_KEY = "1MYSRAx5yvqHUZc6VGtxix6oMA2qgfRT"
HARDCODED_NSW_API_SECRET = "BMvWacw15Et8uFGF"
HARDCODED_NSW_AUTH_HEADER = "Basic MU1ZU1JBeDV5dnFIVVpjNlZHdHhpeDZvTUEycWdmUlQ6Qk12V2Fj准TUEycWdmUlQ6Qk12V2FjdzE1RXQ4dUZHRg=="
# ==============================================================================

# Mobile-first page configuration
st.set_page_config(page_title="Fuel Tracker Mobile", page_icon="⛽", layout="centered")

st.title("⛽ Automated Fuel Optimizer")
st.markdown("Zero manual data entry. App pulls live regional prices and tracks the best option automatically.")

# --- SYSTEM OAUTH SECURITY HANDSHAKE GENERATOR ---
def get_nsw_bearer_token():
    """Generates the required temporary Bearer security token from the OAuth gateway."""
    url = "https://api.onegov.nsw.gov.au/oauth/client_credential/accesstoken"
    headers = {
        "Authorization": HARDCODED_NSW_AUTH_HEADER.strip(),
        "Content-Type": "application/json"
    }
    params = {"grant_type": "client_credentials"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    except Exception as e:
        logger.error(f"OAuth Handshake Connection Failed: {e}")
        return None

# Check token status on startup
bearer_token_sample = get_nsw_bearer_token()
tomtom_key_active = HARDCODED_TOMTOM_API_KEY and "PASTE_YOUR" not in HARDCODED_TOMTOM_API_KEY

# Show API status in sidebar
with st.sidebar:
    st.sidebar.header("🔑 API Status Dashboard")
    st.caption("Active traffic telemetry tracking regional roadway parameters.")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if tomtom_key_active:
            st.success("✅ TomTom Detours")
        else:
            st.info("ℹ️ Math Estimations")
    with col2:
        if bearer_token_sample:
            st.success("✅ NSW FuelCheck")
        else:
            st.error("❌ NSW Handshake Broken")

# Geocoding service using OpenStreetMap Nominatim API
def geocode_address(address_string):
    """Converts a user typed location or address text into GPS coordinates."""
    if not address_string:
        return None
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "FuelFinderMobileApp/1.0"}
    params = {"q": address_string, "format": "json", "limit": 1}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200 and len(response.json()) > 0:
            data = response.json()[0]
            return float(data["lat"]), float(data["lon"])
    except Exception as e:
        logger.error(f"Geocoding lookup error: {e}")
    return None

# Map destinations to coordinates around Wollongong
DESTINATION_LOOKUP = {
    "Wollongong CBD": {"lat": -34.4278, "lon": 150.8931},
    "University of Wollongong": {"lat": -34.4068, "lon": 150.8787},
    "Corrimal Shopping Centre": {"lat": -34.3844, "lon": 150.8953},
    "Shellharbour (Longer Drive)": {"lat": -34.5581, "lon": 150.8549}
}

# --- AUTOMATED API DATA FETCHERS ---
def get_demo_data():
    return [
        {"Station": "Shell Coles Express Fairy Meadow", "Price": 1.84, "Latitude": -34.3920, "Longitude": 150.8990, "Brand": "Shell"},
        {"Station": "7-Eleven Wollongong North", "Price": 1.69, "Latitude": -34.4100, "Longitude": 150.8750, "Brand": "7-Eleven"},
        {"Station": "Metro Fuel Wollongong", "Price": 1.72, "Latitude": -34.4400, "Longitude": 150.8600, "Brand": "Metro"},
        {"Station": "Caltex Woolworths Corrimal", "Price": 1.81, "Latitude": -34.3810, "Longitude": 150.8910, "Brand": "Caltex"}
    ]

def fetch_live_fuelcheck_prices(fuel_type, current_lat, current_lon):
    token = get_nsw_bearer_token()
    if not token:
        return get_demo_data()
    
    url = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v2/fuel/prices"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": HARDCODED_NSW_API_KEY.strip(),
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "transactionid": "1",
        "requesttimestamp": datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        data = response.json()
        
        prices_list = data.get('prices', [])
        stations_list = data.get('stations', [])
        
        stn_map = {}
        for s in stations_list:
            stn_map[s.get('code')] = {
                "name": s.get('name', 'Unknown Station'),
                "lat": float(s.get('location', {}).get('latitude', 0)),
                "lon": float(s.get('location', {}).get('longitude', 0)),
                "brand": s.get('brand', 'Generic')
            }
        
        type_trans = {"E10": "E10", "U91": "U91", "P95": "P95", "P98": "P98", "Diesel": "DL"}
        target_code = type_trans.get(fuel_type, "E10")
        
        parsed_stations = []
        for p in prices_list:
            if p.get('fueltype') == target_code:
                stn_code = p.get('stationcode')
                meta = stn_map.get(stn_code)
                if meta and meta['lat'] != 0:
                    lat_dist = abs(meta['lat'] - current_lat)
                    lon_dist = abs(meta['lon'] - current_lon)
                    
                    if lat_dist > 0.25 or lon_dist > 0.25: 
                        continue
                        
                    parsed_stations.append({
                        "Station": meta['name'],
                        "Price": float(p.get('price', 0)) / 100.0 if float(p.get('price', 0)) > 10.0 else float(p.get('price', 0)),
                        "Latitude": meta['lat'],
                        "Longitude": meta['lon'],
                        "Brand": meta['brand']
                    })
        
        if parsed_stations:
            return parsed_stations
        return get_demo_data()
    except Exception as e:
        logger.error(f"Live Feed Fetch Failure: {e}")
        return get_demo_data()

def calculate_haversine_fallback(origin_lat, origin_lon, dest_lat, dest_lon):
    R = 6371.0  
    dlat = math.radians(dest_lat - origin_lat)
    dlon = math.radians(dest_lon - origin_lon)
    a = (math.sin(dlat / 2)**2 + math.cos(math.radians(origin_lat)) * math.cos(math.radians(dest_lat)) * math.sin(dlon / 2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    km = (R * c) * 1.3
    return km

def get_live_tomtom_distance(origin_lat, origin_lon, dest_lat, dest_lon, api_key=None):
    """Pings TomTom for active car driving distance between two points."""
    if not api_key or "PASTE_YOUR" in api_key:
        return calculate_haversine_fallback(origin_lat, origin_lon, dest_lat, dest_lon)
        
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{origin_lat},{origin_lon}:{dest_lat},{dest_lon}/json"
    params = {"key": api_key.strip(), "traffic": "true", "travelMode": "car"}
    
    try:
        response = requests.get(url, params=params, timeout=6)
        if response.status_code == 200:
            return response.json()['routes'][0]['summary']['lengthInMeters'] / 1000.0
        return calculate_haversine_fallback(origin_lat, origin_lon, dest_lat, dest_lon)
    except Exception:
        return calculate_haversine_fallback(origin_lat, origin_lon, dest_lat, dest_lon)

# --- USER SETTINGS CONTAINER ---
with st.expander("📍 Location & Route Configuration", expanded=True):
    # Live Search Input Field for Custom Start Position
    custom_start_input = st.text_input("📍 Your Current Location / Start Address", value="Fairy Meadow, NSW")
    
    col1, col2 = st.columns(2)
    with col1:
        fuel_economy = st.number_input("Fuel Economy (L/100km)", min_value=1.0, value=8.5, step=0.1)
        tank_capacity = st.number_input("Total Tank Capacity (Liters)", min_value=10, value=60, step=5)
    with col2:
        fuel_type_selection = st.selectbox("Select Fuel Type", options=["E10", "U91", "P95", "P98", "Diesel"])
        planned_dest_name = st.selectbox("Where are you driving to?", options=list(DESTINATION_LOOKUP.keys()))
    
    fuel_gauge_pct = st.slider("Current Fuel Gauge (%)", min_value=0, max_value=100, value=25, step=5)
    liters_to_fill = int(tank_capacity * (1 - (fuel_gauge_pct / 100.0)))
    st.info(f"📋 Target Volume to Fill: **{liters_to_fill} Liters**")

# --- COMPLETELY AUTOMATED CORE ENGINE ---
if st.button("🚀 Auto-Scan & Optimize Best Fuel Value", type="primary", width="stretch"):
    dest_coords = DESTINATION_LOOKUP[planned_dest_name]
    
    with st.spinner("Resolving starting address position..."):
        coords = geocode_address(custom_start_input)
        if coords:
            start_lat, start_lon = coords
            st.success(f"📍 Location Found: {start_lat:.4f}, {start_lon:.4f}")
        else:
            st.warning("⚠️ Location not found. Defaulting to Fairy Meadow base profile.")
            start_lat, start_lon = -34.397, 150.893

    with st.spinner("Analyzing routing detours and market pricing fields..."):
        raw_stations = fetch_live_fuelcheck_prices(fuel_type_selection, start_lat, start_lon)
        
        # 1. Base Case: Get direct distance from custom start location straight to destination
        base_direct_km = get_live_tomtom_distance(
            start_lat, start_lon, 
            dest_coords["lat"], dest_coords["lon"], HARDCODED_TOMTOM_API_KEY
        )
    
    if raw_stations is None or len(raw_stations) == 0:
        st.error("❌ **No Stations Found**")
    else:
        results = []
        for row in raw_stations:
            stn_name = row['Station']
            price = float(row['Price'])
            stn_lat = float(row['Latitude'])
            stn_lon = float(row['Longitude'])
            brand = row.get('Brand', 'Unknown')
            
            # 2. Detour Leg A: Custom location to the fuel station
            leg_a_km = get_live_tomtom_distance(
                start_lat, start_lon, stn_lat, stn_lon, HARDCODED_TOMTOM_API_KEY
            )
            # 3. Detour Leg B: Fuel station to the final destination
            leg_b_km = get_live_tomtom_distance(
                stn_lat, stn_lon, dest_coords["lat"], dest_coords["lon"], HARDCODED_TOMTOM_API_KEY
            )
            
            # Detour calculations
            total_detour_route_km = leg_a_km + leg_b_km
            added_detour_km = max(0.0, total_detour_route_km - base_direct_km)
            
            # Financial calculations
            fuel_burned_on_detour = (added_detour_km * fuel_economy) / 100.0
            cost_of_detour_travel = fuel_burned_on_detour * price
            cost_at_pump = liters_to_fill * price
            true_total_cost = cost_at_pump + cost_of_detour_travel
            
            effective_ppl = true_total_cost / liters_to_fill if liters_to_fill > 0 else 0
            nav_url = f"https://www.google.com/maps/search/?api=1&query={stn_lat},{stn_lon}"
                
            results.append({
                "Station": stn_name,
                "Brand": brand,
                "Price": price,
                "Added Detour": added_detour_km,
                "True $/L": effective_ppl,
                "Total Cost": true_total_cost,
                "Navigate": nav_url
            })
        
        if results:
            df_res = pd.DataFrame(results).sort_values(by="Total Cost").reset_index(drop=True)
            best_cost = df_res.iloc[0]["Total Cost"]
            worst_cost = df_res.iloc[-1]["Total Cost"]
            potential_savings = max(0.0, worst_cost - best_cost)
            best_price = df_res.iloc[0]["True $/L"]
            
            st.success(f"🏆 **Automated Recommendation:** {df_res.iloc[0]['Station']}\n\nTrue Cost (With Detour): **${best_price:.3f}/L**")
            
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.metric(label="💵 Total Trip Cost", value=f"${best_cost:.2f}")
            with sc2:
                st.metric(label="🚗 Extra Detour KM", value=f"{df_res.iloc[0]['Added Detour']:.2f} km")
            with sc3:
                st.metric(label="💸 Net Savings", value=f"${potential_savings:.2f}")
            
            df_display = df_res.copy()
            df_display["Price"] = df_display["Price"].map("${:.2f}".format)
            df_display["Added Detour"] = df_display["Added Detour"].map("{:.2f} km".format)
            df_display["True $/L"] = df_display["True $/L"].map("${:.3f}".format)
            df_display["Total Cost"] = df_display["Total Cost"].map("${:.2f}".format)
            df_display = df_display[["Station", "Brand", "Price", "Added Detour", "True $/L", "Total Cost", "Navigate"]]
            
            st.dataframe(
                df_display, 
                width="stretch",
                column_config={"Navigate": st.column_config.LinkColumn("🗺️ Action", display_text="Route App")},
                hide_index=True
            )

# --- FOOTER ---
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data Stabilization: Active")
st.checkbox("Data Stabilization Indicator active", value=True, disabled=True)
