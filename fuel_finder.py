import streamlit as st
import pandas as pd
import requests
import math
from datetime import datetime

# Import API modules
from api_fuelcheck import get_fuel_prices, get_cheapest_fuel
from api_tomtom import get_coordinates, calculate_route, calculate_detour
from navigation import generate_waze_url
from config import DEFAULT_FUEL_ECONOMY, DEFAULT_TANK_CAPACITY

# --- CONFIGURATION ---
st.set_page_config(page_title="Fuel Tracker Mobile", page_icon="⛽", layout="centered")
st.title("⛽ Automated Fuel Optimizer")

# --- UI INTERFACE ---
with st.expander("📍 Location & Route Configurator", expanded=True):
    start_addr = st.text_input("📍 Starting Address", value="Fairy Meadow, NSW")
    dest_addr = st.text_input("🏁 Final Destination", value="Wollongong CBD, NSW")
    fuel_economy = st.number_input("Fuel Economy (L/100km)", value=DEFAULT_FUEL_ECONOMY)
    tank_cap = st.number_input("Tank Capacity (L)", value=DEFAULT_TANK_CAPACITY)
    fuel_pct = st.slider("Fuel Gauge (%)", 0, 100, 25)
    liters_to_fill = int(tank_cap * (1 - (fuel_pct / 100.0)))

if st.button("🚀 Auto-Scan & Optimize"):
    with st.spinner("🔍 Finding best fuel prices..."):
        try:
            # Step 1: Get coordinates for start and destination
            st.info("📍 Geocoding addresses...")
            start_coords = get_coordinates(start_addr)
            dest_coords = get_coordinates(dest_addr)
            
            if not start_coords or not dest_coords:
                st.error("❌ Could not find coordinates for one or both addresses")
                st.stop()
            
            # Step 2: Get direct route distance
            st.info("🛣️ Calculating route...")
            direct_route = calculate_route(
                start_coords["latitude"], start_coords["longitude"],
                dest_coords["latitude"], dest_coords["longitude"]
            )
            
            if not direct_route:
                st.error("❌ Could not calculate route")
                st.stop()
            
            # Step 3: Get fuel prices near start location
            st.info("⛽ Fetching fuel prices...")
            stations = get_fuel_prices(
                start_coords["latitude"],
                start_coords["longitude"]
            )
            
            if not stations:
                st.warning("⚠️ No fuel stations found nearby. Using fallback data...")
                # Fallback mock data if API fails
                stations = [
                    {"id": 1, "name": "Shell Fairy Meadow", "brand": "Shell", "address": "Fairy Meadow", 
                     "latitude": -34.37, "longitude": 150.89, "price": 1.79, "fuel_type": "ULP"},
                    {"id": 2, "name": "BP West Wollongong", "brand": "BP", "address": "West Wollongong",
                     "latitude": -34.42, "longitude": 150.88, "price": 1.82, "fuel_type": "ULP"},
                    {"id": 3, "name": "Caltex Keiraville", "brand": "Caltex", "address": "Keiraville",
                     "latitude": -34.40, "longitude": 150.87, "price": 1.81, "fuel_type": "ULP"},
                ]
            
            # Step 4: Calculate costs for each station
            st.info("💰 Calculating trip costs...")
            results = []
            cheapest = get_cheapest_fuel(stations)
            
            for station in stations:
                # Calculate detour distance
                detour_km = calculate_detour(
                    start_coords["latitude"], start_coords["longitude"],
                    station["latitude"], station["longitude"],
                    dest_coords["latitude"], dest_coords["longitude"]
                )
                
                # Calculate total distance and fuel cost
                total_distance = direct_route["distance_km"] + detour_km
                fuel_cost = (total_distance / 100) * fuel_economy * station["price"]
                
                # Calculate savings vs cheapest option
                cheapest_cost = (total_distance / 100) * fuel_economy * cheapest["price"]
                net_savings = cheapest_cost - fuel_cost
                
                results.append({
                    "Station": station["name"],
                    "Brand": station["brand"],
                    "Address": station["address"],
                    "Price/L": station["price"],
                    "Net Savings": net_savings,
                    "True Cost/L": station["price"],
                    "Total Trip Cost": fuel_cost,
                    "Added Detour": detour_km,
                    "Navigate": generate_waze_url(station["latitude"], station["longitude"], station["name"])
                })
            
            # Step 5: Display results
            if not results:
                st.warning("⚠️ No fuel stations found. Please check your locations and try again.")
            else:
                # Sort by total trip cost
                df = pd.DataFrame(results).sort_values("Total Trip Cost")
                best_option = df.iloc[0]
                
                # Highlight the winner
                st.subheader("🏆 Your Best Deal")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(label="Best Station", value=best_option.get('Station', 'N/A'))
                with col2:
                    net_savings = best_option.get('Net Savings', 0)
                    st.metric(label="Net Savings", value=f"${net_savings:.2f}", delta="💰 Best")
                with col3:
                    trip_cost = best_option.get('Total Trip Cost', 0)
                    st.metric(label="Total Cost", value=f"${trip_cost:.2f}")
                
                st.divider()
                st.write("### All Available Options")
                
                # Format for display
                display_df = df.copy()
                display_df["Price/L"] = display_df["Price/L"].apply(lambda x: f"${x:.2f}")
                display_df["Net Savings"] = display_df["Net Savings"].apply(lambda x: f"${x:.2f}")
                display_df["True Cost/L"] = display_df["True Cost/L"].apply(lambda x: f"${x:.2f}")
                display_df["Total Trip Cost"] = display_df["Total Trip Cost"].apply(lambda x: f"${x:.2f}")
                display_df["Added Detour"] = display_df["Added Detour"].apply(lambda x: f"{x:.1f}km")
                
                # Display table
                st.dataframe(
                    display_df[["Station", "Brand", "Price/L", "Net Savings", "Total Trip Cost", "Added Detour", "Navigate"]],
                    column_config={"Navigate": st.column_config.LinkColumn("🏎️ Navigate", display_text="Open Waze")},
                    hide_index=True,
                    use_container_width=True
                )
                
                # Trip summary
                st.divider()
                st.write("### 📊 Trip Summary")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Distance", f"{direct_route['distance_km']:.1f} km")
                with col2:
                    st.metric("Duration", f"{direct_route['duration_minutes']:.0f} min")
                with col3:
                    st.metric("Fuel Needed", f"{(direct_route['distance_km'] / 100 * fuel_economy):.1f} L")
                with col4:
                    st.metric("Current Fuel", f"{(fuel_pct / 100 * tank_cap):.1f} L")
        
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
            st.info("Please verify your input values and try again.")
