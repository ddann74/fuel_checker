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
    # (Mock calculation loop logic here)
    # Assume results list is populated...
    
    # After sorting the dataframe by "Total Trip Cost":
    df = pd.DataFrame(results).sort_values("Total Trip Cost")
    
    # 🌟 NEW: Extract the Best Result for Color-Coded Highlight
    best_option = df.iloc[0]
    
    # Highlight the winner in a specific colored metric container
    st.subheader("🏆 Your Best Deal")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Best Station", value=best_option['Station'])
    with col2:
        st.metric(label="Net Savings", value=f"${best_option['Net Savings']:.2f}", delta="Optimal")
    
    st.divider()
    st.write("### All Available Options")
    
    # --- TABLE DISPLAY ---
    display_df = df.copy()
    # (Formatting logic remains the same)
    st.dataframe(
        display_df[["Station", "Brand", "Net Savings", "True Cost/L", "Total Trip Cost", "Added Detour", "Navigate"]],
        column_config={"Navigate": st.column_config.LinkColumn("🏎️ Action", display_text="Open Waze")},
        hide_index=True
    )
