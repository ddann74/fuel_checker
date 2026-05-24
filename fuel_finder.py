import streamlit as st
import pandas as pd
import requests
import math
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Fuel Tracker Mobile", page_icon="⛽", layout="centered")
st.title("⛽ Automated Fuel Optimizer")

# --- UI INTERFACE ---
with st.expander("📍 Location & Route Configurator", expanded=True):
    start_addr = st.text_input("📍 Starting Address", value="Fairy Meadow, NSW")
    dest_addr = st.text_input("🏁 Final Destination", value="Wollongong CBD, NSW")
    fuel_economy = st.number_input("Fuel Economy (L/100km)", value=8.5)
    tank_cap = st.number_input("Tank Capacity (L)", value=60)
    fuel_pct = st.slider("Fuel Gauge (%)", 0, 100, 25)
    liters_to_fill = int(tank_cap * (1 - (fuel_pct / 100.0)))

if st.button("🚀 Auto-Scan & Optimize"):
    # --- MOCK DATA FOR TESTING ---
    results = [
        {
            "Station": "Shell Fairy Meadow",
            "Brand": "Shell",
            "Net Savings": 8.50,
            "True Cost/L": 1.79,
            "Total Trip Cost": 12.30,
            "Added Detour": 0.5,
            "Navigate": "https://waze.com/ul?ll=-34.37,150.89"
        },
        {
            "Station": "BP West Wollongong",
            "Brand": "BP",
            "Net Savings": 5.25,
            "True Cost/L": 1.82,
            "Total Trip Cost": 15.55,
            "Added Detour": 2.1,
            "Navigate": "https://waze.com/ul?ll=-34.42,150.88"
        },
        {
            "Station": "Caltex Keiraville",
            "Brand": "Caltex",
            "Net Savings": 6.75,
            "True Cost/L": 1.81,
            "Total Trip Cost": 13.80,
            "Added Detour": 1.3,
            "Navigate": "https://waze.com/ul?ll=-34.40,150.87"
        },
        {
            "Station": "Priceline Coniston",
            "Brand": "Priceline",
            "Net Savings": 3.50,
            "True Cost/L": 1.84,
            "Total Trip Cost": 17.80,
            "Added Detour": 4.5,
            "Navigate": "https://waze.com/ul?ll=-34.38,150.85"
        },
        {
            "Station": "Ampol North Beach",
            "Brand": "Ampol",
            "Net Savings": 7.20,
            "True Cost/L": 1.80,
            "Total Trip Cost": 14.25,
            "Added Detour": 1.8,
            "Navigate": "https://waze.com/ul?ll=-34.41,150.89"
        }
    ]
    
    try:
        if not results:
            st.warning("⚠️ No fuel stations found. Please check your locations and try again.")
        else:
            # After sorting the dataframe by "Total Trip Cost":
            df = pd.DataFrame(results).sort_values("Total Trip Cost")
            
            # 🌟 Extract the Best Result for Color-Coded Highlight
            best_option = df.iloc[0]
            
            # Highlight the winner in a specific colored metric container
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
            
            # --- TABLE DISPLAY ---
            display_df = df.copy()
            
            # Format the dataframe for display
            display_df["Net Savings"] = display_df["Net Savings"].apply(lambda x: f"${x:.2f}")
            display_df["True Cost/L"] = display_df["True Cost/L"].apply(lambda x: f"${x:.2f}")
            display_df["Total Trip Cost"] = display_df["Total Trip Cost"].apply(lambda x: f"${x:.2f}")
            display_df["Added Detour"] = display_df["Added Detour"].apply(lambda x: f"{x:.1f}km")
            
            # Ensure all required columns exist
            required_columns = ["Station", "Brand", "Net Savings", "True Cost/L", "Total Trip Cost", "Added Detour", "Navigate"]
            available_columns = [col for col in required_columns if col in display_df.columns]
            
            if available_columns:
                st.dataframe(
                    display_df[available_columns],
                    column_config={"Navigate": st.column_config.LinkColumn("🏎️ Action", display_text="Open Waze")},
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.error("❌ Error: Required data columns are missing from results.")
    
    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")
        st.info("Please verify your input values and try again.")
