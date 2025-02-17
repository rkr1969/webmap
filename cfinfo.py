import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium import GeoJsonPopup
from streamlit_folium import st_folium
import plotly.express as px  # For interactive pie chart

# Title of the app
st.title("Management Regime Map")

# Load the GeoJSON file from GitHub
GITHUB_URL = "https://raw.githubusercontent.com/rkr1969/webmap/main/ManagementRegime.geojson"
gdf = gpd.read_file(GITHUB_URL)

# Ensure the GeoDataFrame has the required columns
required_columns = {'Name', 'code', 'regime', 'area_ha'}
if not required_columns.issubset(gdf.columns):
    st.error(f"GeoJSON file must contain the following columns: {required_columns}")
    st.stop()

# Step 1: Sum the 'area_ha' column based on the 'regime' column
area_summary = gdf.groupby('regime')['area_ha'].sum().reset_index()
st.subheader("Summary of Area by Management Regime")
st.dataframe(area_summary)

# Step 2: Display the table with 'Name', 'code', 'regime', 'area_ha'
st.subheader("Detailed Table")
st.dataframe(gdf[['Name', 'code', 'regime', 'area_ha']])

# Step 3: Create an interactive pie chart for 'regime' vs 'area_ha'
st.subheader("Pie Chart: Area Distribution by Management Regime")
fig_pie = px.pie(
    area_summary,
    names='regime',
    values='area_ha',
    title="Area Distribution by Management Regime",
    hole=0.3,  # Optional: Creates a donut chart
)
st.plotly_chart(fig_pie, use_container_width=True)

# Step 4: Create a Folium map with popups
m = folium.Map(location=[gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()], zoom_start=10)

# Define the popup fields
popup_fields = ['Name', 'code', 'regime', 'area_ha']
popup = GeoJsonPopup(
    fields=popup_fields,
    aliases=popup_fields,
    localize=True,
    labels=True,
    style="background-color: yellow;",
)

# Add GeoJSON layer to the map
folium.GeoJson(
    gdf,
    popup=popup,
    tooltip=folium.GeoJsonTooltip(fields=popup_fields),
).add_to(m)

# Display the map in Streamlit
st.subheader("Interactive Map")
st_folium(m, width=700, height=500)
