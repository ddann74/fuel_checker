st.dataframe(
        display_df[["Station", "Brand", "Net Savings", "True Cost/L", "Total Trip Cost", "Added Detour", "Navigate"]],
        column_config={"Navigate": st.column_config.LinkColumn("🏎️ Action", display_text="Open Waze")},
        hide_index=True
    )
