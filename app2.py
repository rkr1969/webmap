import streamlit as st
import requests
import folium
from folium.plugins import MeasureControl, Fullscreen
import pandas as pd
import geopandas as gpd
from streamlit_folium import st_folium
import json

# Load GeoJSON data for Landuse_Ward
@st.cache_data
def load_geojson(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP issues
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching GeoJSON data: {e}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON data: {e}")
        return None

# Corrected URLs
url_landuse = "https://raw.githubusercontent.com/rkr1969/webmap/main/Landuse_Ward.geojson"
geojson_data = load_geojson(url_landuse)

if geojson_data is None:
    st.error("Failed to load Landuse_Ward GeoJSON data. Please check the URL or file format.")
else:
    # Extract unique values for Subdivision and Landuse
    subdivisions = sorted(set(feature['properties']['Subdivision'] for feature in geojson_data['features']))
    landuses = sorted(set(feature['properties']['Landuse'] for feature in geojson_data['features']))

    # Add 'All' option to dropdowns
    subdivisions.insert(0, 'All')
    landuses.insert(0, 'All')

    # Streamlit UI: Dropdowns and Button
    st.title("Interactive Map and Data Explorer")
    selected_subdivision = st.selectbox("Select Subdivision", subdivisions)
    selected_landuse = st.selectbox("Select Landuse", landuses)
    apply_filters = st.button("Apply Filters")

    # Function to filter and update the map
    def update_combined_map(subdivision, landuse):
        # Filter features based on selected subdivision and landuse
        filtered_features = [
            feature for feature in geojson_data['features']
            if (feature['properties']['Subdivision'] == subdivision or subdivision == 'All') and
               (feature['properties']['Landuse'] == landuse or landuse == 'All')
        ]

        # Create base map centered around Nepal
        m = folium.Map(location=[26.814980, 85.992495], zoom_start=10)

        # Add dynamic scale bar using MeasureControl
        measure_control = MeasureControl(
            position='bottomleft',
            primary_length_unit='kilometers',
            secondary_length_unit='meters',
            primary_area_unit='hectares',
            secondary_area_unit='sqmeters'
        )
        m.add_child(measure_control)

        # Add Fullscreen plugin
        fullscreen = Fullscreen(position='topright', title='Fullscreen', title_cancel='Exit Fullscreen')
        m.add_child(fullscreen)

        # Add Landuse_Ward layer
        landuse_layer = folium.FeatureGroup(name="Landuse Ward")
        for feature in filtered_features:
            landuse_type = feature['properties']['Landuse']
            color = {
                'Bare Ground': 'lightred',
                'Built Area': 'darkred',
                'Crops': 'yellow',
                'Flooded Vegetation': 'lightblue',
                'Rangeland': 'lightgreen',
                'Trees': 'darkgreen',
                'Water': 'blue'
            }.get(landuse_type, 'gray')
            folium.GeoJson(
                feature,
                style_function=lambda x, color=color: {
                    'fillColor': color,
                    'color': 'none',
                    'weight': 0,
                    'fillOpacity': 0.4
                },
                tooltip=f"Subdivision: {feature['properties']['Subdivision']} "
                        f"Landuse: {feature['properties']['Landuse']} "
                        f"Area (hectares): {feature['properties']['Area_hectare']:.2f}"
            ).add_to(landuse_layer)
        landuse_layer.add_to(m)

        # Add LayerControl to toggle layers
        folium.LayerControl().add_to(m)

        return m

    # Main App Logic
    if apply_filters:
        # Update Map
        st.subheader("Interactive Map")
        m = update_combined_map(selected_subdivision, selected_landuse)
        st_folium(m, width=700, height=500)
    else:
        # Initial Map
        st.subheader("Interactive Map")
        m = update_combined_map('All', 'All')
        st_folium(m, width=700, height=500)
