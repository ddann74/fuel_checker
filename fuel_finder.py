# ... inside the button click logic, after calculating base_dist ...
    
    results = []
    # Maximum allowed detour (km)
    DETOUR_THRESHOLD = 5.0 
    
    for row in raw_stations:
        # Distance from CURRENT LOCATION to STATION
        leg_a = get_live_tomtom_distance(user_lat, user_lon, row['Latitude'], row['Longitude'])
        # Distance from STATION to DESTINATION
        leg_b = get_live_tomtom_distance(row['Latitude'], row['Longitude'], dest_coords[0], dest_coords[1])
        
        # The detour is the total trip (leg A + leg B) minus the direct path (base_dist)
        detour_km = max(0.0, (leg_a + leg_b) - base_dist)
        
        # Apply the Detour Filter
        if detour_km <= DETOUR_THRESHOLD:
            total_trip_cost = (liters_to_fill * row['Price']) + (((detour_km * multiplier * fuel_economy) / 100.0) * row['Price'])
            results.append({
                "Station": row['Station'], "Brand": row['Brand'], 
                "Detour (km)": round(detour_km, 1),
                "Total Cost": total_trip_cost,
                "Real Price/L": total_trip_cost / liters_to_fill if liters_to_fill > 0 else row['Price'],
                "Navigate": f"waze://?ll={row['Latitude']},{row['Longitude']}&navigate=yes"
            })
