import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium import GeoJsonPopup
from streamlit_folium import st_folium
import plotly.express as px  # For interactive pie chart

# Title of the app
st.title("Management Regime Map")

# Load the first GeoJSON file (Management Regime)
GITHUB_URL_MR = "https://raw.githubusercontent.com/rkr1969/webmap/main/ManagementRegime.geojson"
gdf_mr = gpd.read_file(GITHUB_URL_MR)

# Load the second GeoJSON file (Subdivision Summary)
GITHUB_URL_SD = "https://raw.githubusercontent.com/rkr1969/webmap/main/subdivision_sum.geojson"
gdf_sd = gpd.read_file(GITHUB_URL_SD)

# Ensure the GeoDataFrames have the required columns
required_columns_mr = {'Name', 'code', 'regime', 'area_ha'}
if not required_columns_mr.issubset(gdf_mr.columns):
    st.error(f"Management Regime GeoJSON file must contain the following columns: {required_columns_mr}")
    st.stop()

# Step 1: Sum the 'area_ha' column based on the 'regime' column for Management Regime
area_summary = gdf_mr.groupby('regime')['area_ha'].sum().reset_index()
st.subheader("Summary of Area by Management Regime")
st.dataframe(area_summary)

# Step 2: Display the table with 'Name', 'code', 'regime', 'area_ha'
st.subheader("Detailed Table for Management Regime")
st.dataframe(gdf_mr[['Name', 'code', 'regime', 'area_ha']])

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
m = folium.Map(location=[gdf_mr.geometry.centroid.y.mean(), gdf_mr.geometry.centroid.x.mean()], zoom_start=10)

# Add the first GeoJSON layer ('macro_element_div_1') for Management Regime
popup_fields_mr = ['Name', 'code', 'regime', 'area_ha']
popup_mr = GeoJsonPopup(
    fields=popup_fields_mr,
    aliases=popup_fields_mr,
    localize=True,
    labels=True,
    style="background-color: yellow;",
)

folium.GeoJson(
    gdf_mr,
    name='macro_element_div_1',  # Name of the first layer
    popup=popup_mr,
    tooltip=folium.GeoJsonTooltip(fields=popup_fields_mr),
    style_function=lambda x: {'fillColor': 'green', 'color': 'black', 'weight': 1, 'fillOpacity': 0.5},  # Style for the first layer
).add_to(m)

# Add the second GeoJSON layer ('subdivision_sum') for Subdivision Summary
# Exclude the 'geometry' column from the list of fields
all_fields_sd = [col for col in gdf_sd.columns if col != 'geometry']  # Exclude 'geometry'

folium.GeoJson(
    gdf_sd,
    name='subdivision_sum',  # Name of the second layer
    tooltip=folium.GeoJsonTooltip(fields=all_fields_sd),  # Use all fields except 'geometry'
    style_function=lambda x: {'fillColor': 'blue', 'color': 'black', 'weight': 1, 'fillOpacity': 0.1},  # Style for the second layer
).add_to(m)

# Add a LayerControl to toggle between layers
folium.LayerControl().add_to(m)

# Display the map in Streamlit
st.subheader("Interactive Map with Subdivision Summary Layer")
st_folium(m, width=700, height=500)
