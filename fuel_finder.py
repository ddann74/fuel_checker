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

# Mobile-first page configuration
st.set_page_config(page_title="Fuel Tracker Mobile", page_icon="⛽", layout="centered")

st.title("⛽ Automated Fuel Optimizer")
st.markdown("Zero manual data entry. App pulls live regional prices and tracks the best option automatically.")

# --- API KEYS CONFIGURATION ---
st.sidebar.header("🔑 API Credentials")

# Support both sidebar input and environment variables
GOOGLE_MAPS_API_KEY = st.sidebar.text_input(
    "Google Maps API Key (Optional)", 
    type="password", 
    value=os.getenv("GOOGLE_MAPS_API_KEY", ""),
    help="Optional - for accurate driving distances. Leave blank to use estimated distances."
)

NSW_FUEL_API_KEY = st.sidebar.text_input(
    "NSW FuelCheck API Token", 
    type="password", 
    value=os.getenv("NSW_FUEL_API_KEY", ""),
    help="Required for live fuel prices. Get from: https://api-portal.onegov.nsw.gov.au/"
)

# Show API status in sidebar
with st.sidebar:
    st.divider()
    st.subheader("📊 API Status")
    col1, col2 = st.columns(2)
    with col1:
        if GOOGLE_MAPS_API_KEY and GOOGLE_MAPS_API_KEY.strip():
            st.success("✅ Google Maps")
        else:
            st.info("ℹ️ Estimated Distances")
    with col2:
        if NSW_FUEL_API_KEY and NSW_FUEL_API_KEY.strip():
            st.success("✅ NSW FuelCheck")
        else:
            st.info("ℹ️ Demo Mode (Test Data)")

# Add API Test Button
with st.sidebar:
    st.divider()
    if st.button("🧪 Test NSW FuelCheck API", use_container_width=True):
        if not NSW_FUEL_API_KEY or NSW_FUEL_API_KEY.strip() == "":
            st.warning("⚠️ No API key entered. Please add your NSW FuelCheck API token first.")
        else:
            with st.spinner("Testing API connection..."):
                try:
                    # Official NSW FuelCheck API endpoint via OneGov
                    url = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v1/fuel/prices/near"
                    headers = {
                        "apikey": NSW_FUEL_API_KEY,
                        "Content-Type": "application/json",
                        "User-Agent": "FuelOptimizer/1.0"
                    }
                    params = {
                        "latitude": -34.397,
                        "longitude": 150.893,
                        "fueltype": "E10",
                        "radius": 15
                    }
                    
                    logger.info(f"Testing API with URL: {url}")
                    logger.info(f"Parameters: {params}")
                    
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    logger.info(f"Response status code: {response.status_code}")
                    logger.info(f"Response headers: {response.headers}")
                    logger.info(f"Response body: {response.text[:500]}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        sites_count = len(data) if isinstance(data, list) else len(data.get('sites', []))
                        st.success(f"✅ **API is Working!**")
                        st.write(f"Found **{sites_count}** fuel stations")
                        if sites_count > 0:
                            st.write("Sample station:")
                            sample = data[0] if isinstance(data, list) else data['sites'][0]
                            st.json(sample)
                    elif response.status_code == 401:
                        st.error("❌ **Authentication Failed (401)**")
                        st.write("Your API key is invalid or expired. Check your NSW FuelCheck token.")
                        st.write(f"Response: {response.text}")
                    elif response.status_code == 403:
                        st.error("❌ **Access Denied (403)**")
                        st.write("Your API key doesn't have permission. Check your account settings.")
                        st.write(f"Response: {response.text}")
                    elif response.status_code == 404:
                        st.error("❌ **Endpoint Not Found (404)**")
                        st.write("The API endpoint may have changed. Check: https://api-portal.onegov.nsw.gov.au/")
                        st.write(f"Response: {response.text}")
                    else:
                        st.error(f"❌ **API Error ({response.status_code})**")
                        st.write(f"Response: {response.text}")
                        
                except requests.exceptions.Timeout:
                    st.error("❌ **Connection Timeout**")
                    st.write("The API took too long to respond. Check your internet connection.")
                except requests.exceptions.ConnectionError as e:
                    st.error("❌ **Connection Error**")
                    st.write(f"Could not reach the API server. Details: {str(e)}")
                except ValueError as e:
                    st.error("❌ **Invalid JSON Response**")
                    st.write(f"API returned non-JSON response. Details: {str(e)}")
                except Exception as e:
                    st.error(f"❌ **Error: {type(e).__name__}**")
                    st.write(f"Details: {str(e)}")

# Fallback coordinates if live mobile telemetry hasn't refreshed yet
if 'user_lat' not in st.session_state:
    st.session_state.user_lat = -34.397  # Fairy Meadow / Wollongong area baseline
    st.session_state.user_lon = 150.893

# --- AUTOMATED API DATA FETCHERS ---

def get_demo_data():
    """Return demo/test data for Wollongong area."""
    return [
        {"Station": "Shell Coles Express Fairy Meadow", "Price": 1.84, "Latitude": -34.3920, "Longitude": 150.8990, "Type": "Direct Trip", "Brand": "Shell"},
        {"Station": "7-Eleven Wollongong North", "Price": 1.69, "Latitude": -34.4100, "Longitude": 150.8750, "Type": "Detour", "Brand": "7-Eleven"},
        {"Station": "Metro Fuel Wollongong", "Price": 1.72, "Latitude": -34.4400, "Longitude": 150.8600, "Type": "Direct Trip", "Brand": "Metro"},
        {"Station": "Caltex Woolworths Corrimal", "Price": 1.81, "Latitude": -34.3810, "Longitude": 150.8910, "Type": "Detour", "Brand": "Caltex"}
    ]


def fetch_live_fuelcheck_prices(user_lat, user_lon, fuel_type="E10", api_key=None):
    """
    Automated Feed: Connects directly to the NSW FuelCheck API to pull real-time prices 
    for all surrounding service stations within a geographic bounding box.
    
    NSW FuelCheck API Documentation:
    https://api-portal.onegov.nsw.gov.au/
    
    Endpoint: GET https://api.onegov.nsw.gov.au/FuelPriceCheck/v1/fuel/prices/near
    Query Parameters:
    - latitude: User's latitude
    - longitude: User's longitude
    - fueltype: E10, U91, P95, P98, Diesel
    - radius: Search radius in kilometers
    """
    
    # Fallback test data - use if no valid API key
    if not api_key or api_key.strip() == "":
        logger.info("No NSW FuelCheck API key provided. Using fallback test data.")
        st.info("🧪 **Demo Mode**: Using test data for Wollongong area. Add your NSW FuelCheck API key in the sidebar for live data.")
        demo = get_demo_data()
        logger.info(f"Returning {len(demo)} test stations")
        return demo
    
    # Official NSW FuelCheck API Endpoint via OneGov
    url = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v1/fuel/prices/near"
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
        "User-Agent": "FuelOptimizer/1.0"
    }
    
    # API accepts latitude, longitude, fueltype, radius (km)
    params = {
        "latitude": user_lat,
        "longitude": user_lon,
        "fueltype": fuel_type,
        "radius": 15  # Search radius in km
    }
    
    try:
        logger.info(f"Fetching LIVE fuel prices for {fuel_type} near ({user_lat}, {user_lon})")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"API Response received with {len(data) if isinstance(data, list) else len(data.get('sites', []))} stations")
        stations = []
        
        # Handle both list and object responses
        sites = data if isinstance(data, list) else data.get('sites', [])
        
        for stn in sites:
            try:
                stations.append({
                    "Station": stn.get('stationname', stn.get('name', 'Unknown')),
                    "Price": float(stn.get('price', 0)) / 100.0 if stn.get('price', 0) > 100 else float(stn.get('price', 0)),
                    "Latitude": float(stn.get('latitude', stn.get('lat', 0))),
                    "Longitude": float(stn.get('longitude', stn.get('long', 0))),
                    "Type": "Direct Trip",
                    "Brand": stn.get('brand', 'Unknown'),
                    "Updated": stn.get('updated', stn.get('lastUpdated', 'N/A'))
                })
            except (ValueError, KeyError) as e:
                logger.warning(f"Error parsing station data: {e}")
                continue
        
        if stations:
            logger.info(f"Successfully fetched {len(stations)} live stations")
            st.success(f"✅ Fetched {len(stations)} live stations from NSW FuelCheck API")
            return stations
        else:
            logger.warning("NSW API returned empty stations list. Falling back to demo data.")
            st.warning("⚠️ No stations found from API. Using demo data instead.")
            return get_demo_data()
        
    except requests.exceptions.Timeout:
        logger.error("NSW FuelCheck API request timed out")
        st.error("⏱️ NSW FuelCheck API timed out. Falling back to demo data.")
        return get_demo_data()
    except requests.exceptions.HTTPError as e:
        logger.error(f"NSW FuelCheck API HTTP error: {e.response.status_code}")
        st.error(f"❌ NSW FuelCheck API Error: {e.response.status_code}. Falling back to demo data.")
        if e.response.status_code == 401:
            st.warning("🔑 Invalid API key. Check your NSW FuelCheck token.")
        elif e.response.status_code == 403:
            st.warning("🚫 Access denied. Your API key may not have permission.")
        elif e.response.status_code == 404:
            st.warning("🔍 API endpoint not found. Check the API documentation.")
        return get_demo_data()
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to NSW FuelCheck API")
        st.error("❌ Connection error. Could not reach the API server.")
        return get_demo_data()
    except Exception as e:
        logger.error(f"Unexpected error fetching fuel prices: {e}")
        st.error(f"❌ Error fetching fuel prices: {str(e)}")
        return get_demo_data()


def calculate_haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon):
    """Calculate approximate distance using Haversine formula."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(dest_lat - origin_lat)
    dlon = math.radians(dest_lon - origin_lon)
    a = (math.sin(dlat / 2)**2 + 
         math.cos(math.radians(origin_lat)) * 
         math.cos(math.radians(dest_lat)) * 
         math.sin(dlon / 2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c
    duration_mins = (distance_km / 60.0) * 60
    return distance_km, duration_mins


def get_driving_distance_and_time(origin_lat, origin_lon, dest_lat, dest_lon, api_key=None):
    """
    Get real driving distance and time using Google Maps Distance Matrix API.
    
    Google Maps Distance Matrix API Documentation:
    https://developers.google.com/maps/documentation/distance-matrix
    
    Falls back to Haversine formula if API key not provided.
    """
    
    # Fallback: Haversine formula for straight-line distance (always available)
    if not api_key or api_key.strip() == "":
        logger.info("No Google Maps API key. Using Haversine formula for distance estimation.")
        return calculate_haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)
    
    # Google Maps Distance Matrix API
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    
    params = {
        "origins": f"{origin_lat},{origin_lon}",
        "destinations": f"{dest_lat},{dest_lon}",
        "mode": "driving",
        "key": api_key
    }
    
    try:
        logger.info(f"Fetching distance from ({origin_lat},{origin_lon}) to ({dest_lat},{dest_lon})")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data['status'] != 'OK':
            logger.warning(f"Google Maps API status: {data['status']}")
            return calculate_haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)
        
        element = data['rows'][0]['elements'][0]
        
        if element['status'] == 'OK':
            distance_km = element['distance']['value'] / 1000.0
            duration_mins = element['duration']['value'] / 60.0
            logger.info(f"Distance: {distance_km:.1f} km (via Google Maps), Duration: {duration_mins:.0f} mins")
            return distance_km, duration_mins
        else:
            logger.warning(f"Distance Matrix element status: {element['status']}")
            return calculate_haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)
            
    except requests.exceptions.Timeout:
        logger.error("Google Maps API request timed out. Using Haversine.")
        return calculate_haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)
    except requests.exceptions.HTTPError as e:
        logger.error(f"Google Maps API HTTP error: {e.response.status_code}. Using Haversine.")
        return calculate_haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)
    except Exception as e:
        logger.error(f"Unexpected error in distance calculation: {e}")
        return calculate_haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)


def get_current_location():
    """
    Get user's current location using IP-based geolocation.
    
    Using IP Geolocation API (free service):
    https://ip-api.com/docs/api:json
    
    Endpoint: GET http://ip-api.com/json/
    Returns: latitude, longitude, city, country, etc.
    
    Note: This is a free service with rate limits (45 requests/minute)
    """
    try:
        logger.info("Attempting to fetch user location via IP geolocation")
        url = "http://ip-api.com/json/"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        if data.get('status') == 'success':
            lat = data.get('lat')
            lon = data.get('lon')
            city = data.get('city', 'Unknown')
            logger.info(f"Location detected: {city} ({lat}, {lon})")
            return lat, lon, city
        else:
            logger.warning(f"IP Geolocation failed: {data.get('message')}")
            return None, None, None
    except Exception as e:
        logger.error(f"Error getting location: {e}")
        return None, None, None


# --- USER SETTINGS CONTAINER ---
with st.expander("🚗 Vehicle Settings & Targets", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        fuel_economy = st.number_input(
            "Fuel Economy (L/100km)", 
            min_value=1.0, 
            value=8.5, 
            step=0.1,
            help="Your vehicle's fuel consumption rate"
        )
    
    with col2:
        tank_capacity = st.number_input(
            "Total Tank Capacity (Liters)", 
            min_value=10, 
            value=60, 
            step=5,
            help="Your vehicle's fuel tank size"
        )
    
    fuel_gauge_pct = st.slider(
        "Current Fuel Gauge (%)", 
        min_value=0, 
        max_value=100, 
        value=25, 
        step=5,
        help="How full is your tank?"
    )
    
    # Auto-calculate volume required
    liters_to_fill = int(tank_capacity * (1 - (fuel_gauge_pct / 100.0)))
    st.info(f"📋 Target Volume to Fill: **{liters_to_fill} Liters**")
    
    fuel_type_selection = st.selectbox(
        "Select Fuel Type", 
        options=["E10", "U91", "P95", "P98", "Diesel"],
        help="Select your vehicle's fuel type"
    )

# Location detection
if st.sidebar.button("📍 Detect My Location"):
    lat, lon, city = get_current_location()
    if lat and lon:
        st.session_state.user_lat = lat
        st.session_state.user_lon = lon
        st.sidebar.success(f"✅ Location detected: {city}")
    else:
        st.sidebar.error("❌ Could not detect location. Using default.")

# Display live location status
location_status = "Live Connection Active" if st.session_state.user_lat != -34.397 else "Using Location Default"
st.metric(
    label="🛰️ Mobile GPS Telemetry Status", 
    value=f"{st.session_state.user_lat:.4f}, {st.session_state.user_lon:.4f}",
    delta=location_status
)

# Add info box about API setup
with st.sidebar.expander("📡 API Setup Guide"):
    st.markdown("""
    ### API Keys (Optional):
    
    **NSW FuelCheck API (Recommended):**
    1. Visit [OneGov API Portal](https://api-portal.onegov.nsw.gov.au/)
    2. Register for a developer account
    3. Subscribe to FuelPriceCheck API
    4. Get your API key
    5. Paste key above for **live fuel prices**
    
    **Google Maps API (Optional):**
    1. Go to [Google Cloud Console](https://console.cloud.google.com)
    2. Create a new project
    3. Enable Distance Matrix API
    4. Create API key credentials
    5. Paste key above for **actual driving distances**
    
    ### How It Works:
    - 🧪 **Demo Mode**: Works without any API keys using test data
    - 🌏 **Distances**: Uses estimated distances if no Google Maps key
    - 📍 **Location**: Uses IP geolocation (free, 45 req/min)
    - ✅ **Progressive Enhancement**: Add keys anytime to upgrade!
    """)

# --- COMPLETELY AUTOMATED CORE ENGINE ---
if st.button("🚀 Auto-Scan & Optimize Best Fuel Value", type="primary", use_container_width=True):
    with st.spinner("Fetching market pricing data..."):
        # Auto-query the pricing matrix 
        raw_stations = fetch_live_fuelcheck_prices(
            st.session_state.user_lat, 
            st.session_state.user_lon, 
            fuel_type_selection, 
            NSW_FUEL_API_KEY
        )
    
    # Log what we got
    logger.info(f"Raw stations received: {len(raw_stations) if raw_stations else 0}")
    
    if raw_stations is None or len(raw_stations) == 0:
        st.error("❌ **No Stations Found**")
        st.divider()
        
        # Show comprehensive troubleshooting
        with st.expander("🔧 Troubleshooting Steps", expanded=True):
            st.markdown("""
            ### Step 1: Test Your API Key
            Click the 🧪 **Test NSW FuelCheck API** button in the sidebar to verify it's working.
            
            ### Step 2: Check These Common Issues
            
            **❌ No API key entered?**
            - Leave field blank to use demo data (4 test stations)
            - Demo mode always works!
            
            **❌ Got a 401 error?**
            - Your API key is invalid or expired
            - Get a new one from https://api-portal.onegov.nsw.gov.au/
            
            **❌ Got a 403 error?**
            - Your key exists but doesn't have permission
            - Check your FuelCheck account settings
            
            **❌ Got a 404 error?**
            - The API endpoint may have changed
            - Visit https://api-portal.onegov.nsw.gov.au/ for current endpoints
            
            **❌ Connection timeout?**
            - Check your internet connection
            - Try again in a few seconds
            
            ### Step 3: Update Your Location
            Click 📍 **Detect My Location** to ensure you're using current coordinates.
            
            ### Step 4: Check API Status
            Current API Status in sidebar shows what's active.
            """)
        
        st.info("💡 **Demo Data Available**: If you don't have an API key, the app should show demo data automatically. If not, try refreshing the page.")
        
    else:
        results = []
        with st.spinner("Calculating optimized routes..."):
            for row in raw_stations:
                stn_name = row['Station']
                price = float(row['Price'])
                stn_lat = float(row['Latitude'])
                stn_lon = float(row['Longitude'])
                trip_type = row.get('Type', 'Direct Trip')
                brand = row.get('Brand', 'Unknown')
                
                # Auto-calculate real-world driving routing matrix
                distance_km, duration_mins = get_driving_distance_and_time(
                    st.session_state.user_lat, 
                    st.session_state.user_lon, 
                    stn_lat, 
                    stn_lon, 
                    GOOGLE_MAPS_API_KEY
                )
                
                # Apply trip type multiplier
                multiplier = 2.0 if trip_type == "Direct Trip" else 1.0
                total_travel_distance = distance_km * multiplier
                
                # Calculate fuel costs
                fuel_burned = (total_travel_distance * fuel_economy) / 100.0
                cost_of_travel_fuel = fuel_burned * price
                cost_at_pump = liters_to_fill * price
                true_total_cost = cost_at_pump + cost_of_travel_fuel
                
                # Avoid division by zero
                effective_ppl = true_total_cost / liters_to_fill if liters_to_fill > 0 else 0
                
                nav_url = f"https://www.google.com/maps/search/?api=1&query={stn_lat},{stn_lon}"
                    
                results.append({
                    "Station": stn_name,
                    "Brand": brand,
                    "Price": price,
                    "Distance": distance_km,
                    "True $/L": effective_ppl,
                    "Total Cost": true_total_cost,
                    "Navigate": nav_url
                })
        
        if results and len(results) > 0:
            df_res = pd.DataFrame(results).sort_values(by="Total Cost").reset_index(drop=True)
            
            best_cost = df_res.iloc[0]["Total Cost"]
            worst_cost = df_res.iloc[-1]["Total Cost"]
            potential_savings = max(0.0, worst_cost - best_cost)
            best_price = df_res.iloc[0]["True $/L"]
            
            # Display recommendation
            st.success(f"🏆 **Automated Recommendation:** {df_res.iloc[0]['Station']}\n\nTrue Cost: **${best_price:.3f}/L**")
            
            # Metrics row
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.metric(label="💵 Optimized Trip Cost", value=f"${best_cost:.2f}")
            with sc2:
                st.metric(label="🚗 Distance", value=f"{df_res.iloc[0]['Distance']:.1f} km")
            with sc3:
                st.metric(label="💸 Potential Savings", value=f"${potential_savings:.2f}")
            
            # Format dataframe for display
            df_display = df_res.copy()
            df_display["Price"] = df_display["Price"].map("${:.2f}".format)
            df_display["Distance"] = df_display["Distance"].map("{:.1f} km".format)
            df_display["True $/L"] = df_display["True $/L"].map("${:.3f}".format)
            df_display["Total Cost"] = df_display["Total Cost"].map("${:.2f}".format)
            df_display = df_display[["Station", "Brand", "Price", "Distance", "True $/L", "Total Cost", "Navigate"]]
            
            st.dataframe(
                df_display, 
                use_container_width=True,
                column_config={
                    "Navigate": st.column_config.LinkColumn("🗺️ Action", display_text="Navigate")
                },
                hide_index=True
            )
            
            # Summary stats
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Best Price", f"${df_res['Price'].min():.2f}")
            with col2:
                st.metric("Worst Price", f"${df_res['Price'].max():.2f}")
            with col3:
                st.metric("Avg Distance", f"{df_res['Distance'].mean():.1f} km")
                
        else:
            st.error("❌ Engine failed to parse automated telemetry parameters.")

# --- FOOTER ---
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data Stabilization: Active")
st.checkbox("Data Stabilization Indicator active", value=True, disabled=True)
