import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap
import random
import plotly.express as px
from streamlit_folium import st_folium

# Cache data loading to prevent reloading on every rerun
@st.cache_data
def load_geojson(url):
    gdf = gpd.read_file(url)
    # Convert Year to datetime and extract year component
    if 'Year' in gdf.columns:
        gdf['Year'] = pd.to_datetime(gdf['Year']).dt.year
    return gdf

# Load data from GitHub
base_url = "https://raw.githubusercontent.com/rkr1969/webmap/main/"
main_layer_url = base_url + "lossyear_subdivision.geojson"
sum_layer_url = base_url + "subdivision_sum.geojson"

# Load GeoJSON data using cached function
main_gdf = load_geojson(main_layer_url)
sum_gdf = load_geojson(sum_layer_url)

# Reproject geometries to EPSG:4326 (required by Folium)
main_gdf = main_gdf.to_crs(epsg=4326)
sum_gdf = sum_gdf.to_crs(epsg=4326)

# Generate random colors for years
unique_years = sorted(main_gdf['Year'].unique())
colors = ["#" + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)]) for _ in unique_years]
year_color_map = {year: color for year, color in zip(unique_years, colors)}

# Debugging: Check for invalid geometries
print("Invalid geometries in main_gdf:", main_gdf[~main_gdf.geometry.is_valid].shape[0])
print("Invalid geometries in sum_gdf:", sum_gdf[~sum_gdf.geometry.is_valid].shape[0])

# Fix invalid geometries
main_gdf['geometry'] = main_gdf.geometry.apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)
sum_gdf['geometry'] = sum_gdf.geometry.apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)

# Create Folium map
def create_folium_map():
    m = folium.Map(
        location=[main_gdf.geometry.centroid.y.mean(), main_gdf.geometry.centroid.x.mean()],
        zoom_start=10,
        tiles="OpenStreetMap"  # Use OpenStreetMap as the base layer
    )

    # Add Fullscreen plugin
    Fullscreen().add_to(m)

    # Add GeoJSON layers with random colors based on Year
    for year, color in year_color_map.items():
        year_data = main_gdf[main_gdf['Year'] == year]
        folium.GeoJson(
            year_data,
            style_function=lambda feature, color=color: {
                "fillColor": color,
                "color": color,
                "weight": 1,
                "fillOpacity": 0.6
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["subdivision", "Area_hectare", "Year"],
                aliases=["Subdivision:", "Area (ha):", "Year:"],
                localize=True
            )
        ).add_to(m)

    # Add summary layer (black outlines)
    folium.GeoJson(
        sum_gdf,
        style_function=lambda feature: {
            "color": "black",
            "weight": 2,
            "fillOpacity": 0
        }
    ).add_to(m)

    return m

# Display map using Streamlit-Folium
try:
    st_folium(create_folium_map(), width=700, height=500)
except Exception as e:
    st.error(f"Error displaying map: {e}")
