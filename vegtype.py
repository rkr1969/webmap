import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import Fullscreen
import random
from streamlit_folium import st_folium

# Initialize session state variables
if "map_initialized" not in st.session_state:
    st.session_state.map_initialized = False
if "folium_map" not in st.session_state:
    st.session_state.folium_map = None
if "vegetation_gdf" not in st.session_state:
    st.session_state.vegetation_gdf = None
if "sum_gdf" not in st.session_state:
    st.session_state.sum_gdf = None

# Cache data loading to prevent reloading on every rerun
@st.cache_data
def load_geojson(url):
    gdf = gpd.read_file(url)
    return gdf

# Load data from GitHub
base_url = "https://raw.githubusercontent.com/rkr1969/webmap/main/"
vegetation_layer_url = base_url + "vegetationTypeSD.geojson"
sum_layer_url = base_url + "subdivision_sum.geojson"

# Load GeoJSON data using cached function
if st.session_state.vegetation_gdf is None or st.session_state.sum_gdf is None:
    vegetation_gdf = load_geojson(vegetation_layer_url)
    sum_gdf = load_geojson(sum_layer_url)

    # Reproject geometries to EPSG:4326 (required by Folium)
    vegetation_gdf = vegetation_gdf.to_crs(epsg=4326)
    sum_gdf = sum_gdf.to_crs(epsg=4326)

    # Fix invalid geometries
    vegetation_gdf['geometry'] = vegetation_gdf.geometry.apply(lambda geom: geom.buffer(0)
