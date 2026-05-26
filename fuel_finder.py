import streamlit as st
import pandas as pd
import requests
import math
from streamlit_searchbox import st_searchbox
import streamlit.components.v1 as components

# --- CONFIGURATION ---
NSW_API_KEY        = "1MYSRAx5yvqHUZc6VGtxix6oMA2qgfRT"
NSW_API_SECRET     = "BMvWacw15Et8uFGF"
NSW_AUTH_HEADER    = "Basic MU1ZU1JBeDV5dnFIVVpjNlZHdHhpeDZvTUEycWdmUlQ6Qk12V2FjdzE1RXQ4dUZHRg=="
TOMTOM_API_KEY     = "RoiDwi5Y35NaVKTJEyFTX5VtED45vS2e"

st.set_page_config(page_title="Fuel Optimizer", page_icon="⛽", layout="centered")
st.title("⛽ Automated Fuel Optimizer")

# --- FUNCTIONS ---

def get_location_js():
    return """
    <button id="btn" onclick="getLocation()" style="padding:10px 18px;cursor:pointer;background:#1a1a1a;color:#4ade80;border:1px solid #2d5a2d;border-radius:6px;font-size:0.85rem;">
        📍 Detect My Location
    </button>
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
    if not searchterm or len(searchterm) < 3:
        return []
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": searchterm, "format": "json", "limit": 5},
            headers={"User-Agent": "FuelFinderApp/1.0"},
            timeout=3,
        )
        return [res["display_name"] for res in r.json()]
    except:
        return []

def geocode_address(address_string):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address_string, "format": "json", "limit": 1},
            headers={"User-Agent": "FuelFinderApp/1.0"},
            timeout=10,
        )
        data = r.json()
        if r.status_code == 200 and data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        pass
    return None

def get_tomtom_distance_km(o_lat, o_lon, d_lat, d_lon):
    """Real road distance from TomTom Routing API."""
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{o_lat},{o_lon}:{d_lat},{d_lon}/json"
    try:
        r = requests.get(
            url,
            params={"key": TOMTOM_API_KEY, "travelMode": "car", "routeType": "fastest"},
            timeout=8,
        )
        data = r.json()
        meters = data["routes"][0]["summary"]["lengthInMeters"]
        return meters / 1000.0
    except:
        R = 6371.0
        dlat = math.radians(d_lat - o_lat)
        dlon = math.radians(d_lon - o_lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(o_lat)) * math.cos(math.radians(d_lat)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * 1.3

def get_nsw_access_token():
    """Exchange API key+secret for a short-lived OAuth bearer token."""
    r = requests.post(
        "https://api.onegov.nsw.gov.au/oauth/client_credential/accesstoken",
        params={"grant_type": "client_credentials"},
        headers={
            "Authorization": NSW_AUTH_HEADER,
            "Content-Type":  "application/x-www-form-urlencoded",
        },
        timeout=10,
    )
    if not r.ok:
        raise Exception(f"Token request failed — HTTP {r.status_code}: {r.text[:300]}")
    # Show raw response in sidebar for debugging
    st.sidebar.code(f"Token response ({r.status_code}):\n{r.text[:500]}", language="text")
    if not r.text.strip():
        raise Exception(f"Token request returned HTTP 200 but empty body. Headers: {dict(r.headers)}")
    return r.json()["access_token"]

def fetch_nsw_fuel_prices(lat, lon, radius_km=10, fuel_type="E10"):
    """Fetch live prices from NSW FuelCheck API."""
    try:
        token = get_nsw_access_token()
    except Exception as e:
        st.error(f"NSW Auth error: {e}")
        return []

    url = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v1/fuel/prices/nearby"
    headers = {
        "Authorization":    f"Bearer {token}",
        "apikey":           NSW_API_KEY,
        "Content-Type":     "application/json; charset=utf-8",
        "transactionid":    "1",
        "requesttimestamp": "01/01/2024 00:00:00 AM",
    }
    payload = {
        "fueltype":       fuel_type,
        "namedlocation":  f"{lat},{lon}",
        "radius":         str(radius_km),
        "sortby":         "price",
        "resultsperpage": "25",
        "page":           "1",
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        stations = []
        for s in data.get("stations", []):
            price_cents = s.get("Price") or s.get("price")
            if not price_cents:
                continue
            stations.append({
                "Station":   s.get("Name")    or s.get("name",    "Unknown"),
                "Brand":     s.get("Brand")   or s.get("brand",   ""),
                "Price":     float(price_cents) / 100.0,
                "Latitude":  float(s.get("Lat") or s.get("lat",  lat)),
                "Longitude": float(s.get("Lng") or s.get("lng",  lon)),
                "Address":   s.get("Address") or s.get("address", ""),
            })
        return stations
    except Exception as e:
        st.error(f"NSW Fuel API error: {e}")
        return []

# --- UI ---

query_params = st.query_params
user_lat = float(query_params.get("lat", -34.397))
user_lon = float(query_params.get("lon", 150.893))

components.html(get_location_js(), height=55)
st.caption(f"📍 Current position: `{user_lat:.5f}, {user_lon:.5f}`")

with st.expander("🚗 Vehicle Settings & Route", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        fuel_economy   = st.number_input("Fuel Economy (L/100km)", value=8.5, step=0.5)
        tank_capacity  = st.number_input("Total Tank Capacity (L)", value=60.0, step=5.0)
        trip_mode      = st.radio("Trip Mode", ["One Way", "Return"], horizontal=True)
    with col2:
        fuel_gauge_pct = st.slider("Current Fuel (%)", 0, 100, 25, step=5)
        fuel_type      = st.selectbox("Fuel Type", ["E10", "U91", "U95", "U98", "P98", "Diesel"])
        manual_volume  = st.number_input("Override Fill Volume (L, 0 = auto)", min_value=0.0, value=0.0)
        search_radius  = st.slider("Search Radius (km)", 5, 50, 10, step=5)

    liters_to_fill  = manual_volume if manual_volume > 0 else round(tank_capacity * (1.0 - fuel_gauge_pct / 100.0), 1)
    trip_multiplier = 2 if trip_mode == "Return" else 1

st.caption(f"Will fill **{liters_to_fill:.1f} L** of {fuel_type}")

manual_dest = st_searchbox(search_address, label="Destination", placeholder="Enter destination…")

if st.button("🚀 Find Best Station (Ranked by Savings)", use_container_width=True, type="primary"):

    if not manual_dest:
        st.warning("Please enter a destination.")
        st.stop()

    with st.spinner("Geocoding destination…"):
        dest_coords = geocode_address(manual_dest)
    if not dest_coords:
        st.error("❌ Could not resolve destination.")
        st.stop()
    dest_lat, dest_lon = dest_coords

    with st.spinner(f"Fetching live {fuel_type} prices within {search_radius} km…"):
        raw_stations = fetch_nsw_fuel_prices(user_lat, user_lon, search_radius, fuel_type)

    if not raw_stations:
        st.warning("No stations returned. Try a larger search radius or different fuel type.")
        st.stop()

    with st.spinner("Calculating road distances via TomTom…"):

        # ── Leg 0: direct trip distance (used only as a reference baseline) ──
        base_dist_km = get_tomtom_distance_km(user_lat, user_lon, dest_lat, dest_lon)

        results = []
        for row in raw_stations:
            s_lat, s_lon = row["Latitude"], row["Longitude"]
            price = row["Price"]

            # ── Leg A: user → station ──────────────────────────────────────────
            # Real road km you must drive before you can fill up.
            leg_a_km = get_tomtom_distance_km(user_lat, user_lon, s_lat, s_lon)

            # ── Leg B: station → destination ──────────────────────────────────
            # Road km from the station to your final destination.
            # This is driven on a FULL tank at this station's price.
            leg_b_km = get_tomtom_distance_km(s_lat, s_lon, dest_lat, dest_lon)

            # ── Detour km ─────────────────────────────────────────────────────
            # How much EXTRA distance this station adds vs going direct.
            # Used for the On-Route indicator only — not part of cost anymore.
            detour_km = max(0.0, (leg_a_km + leg_b_km) - base_dist_km)

            # ── Fuel burnt on Leg A (before fill-up) ──────────────────────────
            # You're burning existing tank fuel to reach the station.
            # We price this at the station's rate because that's the fuel
            # you're effectively choosing to consume by picking this station.
            leg_a_fuel_cost = (leg_a_km * fuel_economy / 100.0) * price

            # ── Fuel burnt on Leg B (after fill-up) ───────────────────────────
            # You filled up at this station so this leg runs on its fuel price.
            # For a return trip the driver refuels once, so we only multiply
            # the destination leg — not the full return — by trip_multiplier.
            leg_b_fuel_cost = (leg_b_km * trip_multiplier * fuel_economy / 100.0) * price

            # ── Fill cost ─────────────────────────────────────────────────────
            # Straight purchase cost of the litres you're putting in the tank.
            fill_cost = liters_to_fill * price

            # ── Total trip cost ───────────────────────────────────────────────
            # Everything combined: getting to the station + filling up +
            # driving the rest of the way to the destination.
            total_cost = fill_cost + leg_a_fuel_cost + leg_b_fuel_cost

            # ── Effective price per litre ─────────────────────────────────────
            # Spreads all trip costs back over the litres purchased so you can
            # compare stations on a single apples-to-apples $/L figure.
            eff_price = total_cost / liters_to_fill if liters_to_fill > 0 else price

            results.append({
                "_total":       total_cost,
                "Station":      row["Station"],
                "Brand":        row["Brand"],
                "Listed $/L":   price,
                "Eff $/L":      eff_price,
                "To Station":   round(leg_a_km, 1),
                "To Dest":      round(leg_b_km, 1),
                "Detour (km)":  round(detour_km, 1),
                "On-Route":     "✅" if detour_km <= 3.0 else ("🔶" if detour_km <= 8.0 else "❌"),
                "Fill Cost":    fill_cost,
                "Total Cost":   total_cost,
                "Net Savings":  0.0,
                "Navigate":     f"https://waze.com/ul?ll={dest_lat},{dest_lon}&navigate=yes&from={s_lat},{s_lon}",
            })

    df = pd.DataFrame(results).sort_values("_total").reset_index(drop=True)
    worst = df["_total"].max()
    df["Net Savings"] = worst - df["_total"]

    df_display = df.copy()
    df_display["Net Savings"] = df_display["Net Savings"].map("${:.2f}".format)
    df_display["Total Cost"]  = df_display["Total Cost"].map("${:.2f}".format)
    df_display["Fill Cost"]   = df_display["Fill Cost"].map("${:.2f}".format)
    df_display["Listed $/L"]  = df_display["Listed $/L"].map("${:.3f}".format)
    df_display["Eff $/L"]     = df_display["Eff $/L"].map("${:.3f}".format)

    st.success(f"✅ {len(df)} stations found · Direct trip: {base_dist_km:.1f} km")

    st.dataframe(
        df_display[[
            "Station", "Brand", "On-Route", "Listed $/L", "Eff $/L",
            "To Station", "To Dest", "Detour (km)",
            "Fill Cost", "Net Savings", "Total Cost", "Navigate"
        ]],
        column_config={
            "Navigate": st.column_config.LinkColumn("🗺️ Navigate", display_text="Waze"),
            "To Station": st.column_config.NumberColumn("To Station (km)"),
            "To Dest":    st.column_config.NumberColumn("To Dest (km)"),
        },
        hide_index=True,
        use_container_width=True,
    )

    # --- FILTERS (applied after results are calculated) ---
    st.markdown("---")
    st.markdown("### 🔍 Filter Results")

    all_brands = sorted(df["Brand"].dropna().unique().tolist())

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        min_savings = st.number_input(
            "Min Net Savings ($)", min_value=0.0, value=0.0, step=0.50,
            help="Only show stations that save at least this much vs the worst option"
        )
        max_detour = st.slider(
            "Max Detour (km)", min_value=0, max_value=50,
            value=int(df["Detour (km)"].max()) + 1,
            help="Hide stations that require more than this detour"
        )
    with f_col2:
        on_route_only = st.checkbox(
            "✅ On-Route only (≤ 3 km detour)",
            value=False,
            help="Only show stations with a detour of 3 km or less"
        )
        selected_brands = st.multiselect(
            "Brand", options=all_brands, default=all_brands,
            help="Uncheck brands you want to exclude"
        )

    # Apply filters to the numeric df (before formatting)
    mask = (
        (df["Net Savings"]  >= min_savings) &
        (df["Detour (km)"] <= max_detour) &
        (df["Brand"].isin(selected_brands))
    )
    if on_route_only:
        mask &= (df["Detour (km)"] <= 3.0)

    df_filtered = df[mask].copy()

    if df_filtered.empty:
        st.warning("No stations match your filters. Try relaxing them.")
    else:
        # Re-format filtered subset
        df_show = df_filtered.copy()
        df_show["Net Savings"] = df_show["Net Savings"].map("${:.2f}".format)
        df_show["Total Cost"]  = df_show["Total Cost"].map("${:.2f}".format)
        df_show["Fill Cost"]   = df_show["Fill Cost"].map("${:.2f}".format)
        df_show["Listed $/L"]  = df_show["Listed $/L"].map("${:.3f}".format)
        df_show["Eff $/L"]     = df_show["Eff $/L"].map("${:.3f}".format)

        st.caption(f"Showing **{len(df_filtered)}** of {len(df)} stations")

        st.dataframe(
            df_show[[
                "Station", "Brand", "On-Route", "Listed $/L", "Eff $/L",
                "To Station", "To Dest", "Detour (km)",
                "Fill Cost", "Net Savings", "Total Cost", "Navigate"
            ]],
            column_config={
                "Navigate":   st.column_config.LinkColumn("🗺️ Navigate", display_text="Waze"),
                "To Station": st.column_config.NumberColumn("To Station (km)"),
                "To Dest":    st.column_config.NumberColumn("To Dest (km)"),
            },
            hide_index=True,
            use_container_width=True,
        )
