import streamlit as st
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
    try:
        gdf = gpd.read_file(url)
        return gdf
    except Exception as e:
        st.error(f"Error loading GeoJSON from {url}: {e}")
        return None

# Load data from GitHub
base_url = "https://raw.githubusercontent.com/rkr1969/webmap/main/"
vegetation_layer_url = base_url + "vegetationTypeSD.geojson"
sum_layer_url = base_url + "subdivision_sum.geojson"

# Load GeoJSON data using cached function
if st.session_state.vegetation_gdf is None or st.session_state.sum_gdf is None:
    vegetation_gdf = load_geojson(vegetation_layer_url)
    sum_gdf = load_geojson(sum_layer_url)
    if vegetation_gdf is None or sum_gdf is None:
        st.error("Failed to load one or more GeoJSON files. Please check the URLs and data formats.")
        st.stop()
    # Reproject geometries to EPSG:4326 (required by Folium)
    try:
        vegetation_gdf = vegetation_gdf.to_crs(epsg=4326)
        sum_gdf = sum_gdf.to_crs(epsg=4326)
    except Exception as e:
        st.error(f"Error reprojecting geometries: {e}")
        st.stop()
    # Fix invalid geometries
    vegetation_gdf['geometry'] = vegetation_gdf.geometry.apply(
        lambda geom: geom.buffer(0) if geom is not None and not geom.is_valid else geom
    )
    sum_gdf['geometry'] = sum_gdf.geometry.apply(
        lambda geom: geom.buffer(0) if geom is not None and not geom.is_valid else geom
    )
    # Validate data
    required_columns_veg = {"subdivision", "vegetation_zone", "vegetation_type", "area_ha"}
    required_columns_sum = {"subdivision"}
    if not required_columns_veg.issubset(vegetation_gdf.columns):
        st.error(f"Missing required columns in vegetation data. Expected: {required_columns_veg}, Found: {vegetation_gdf.columns}")
        st.stop()
    if not required_columns_sum.issubset(sum_gdf.columns):
        st.error(f"Missing required columns in subdivision data. Expected: {required_columns_sum}, Found: {sum_gdf.columns}")
        st.stop()
    # Store data in session state
    st.session_state.vegetation_gdf = vegetation_gdf
    st.session_state.sum_gdf = sum_gdf

# Retrieve data from session state
vegetation_gdf = st.session_state.vegetation_gdf
sum_gdf = st.session_state.sum_gdf

# Generate random colors for vegetation types
unique_vegetation_types = sorted(vegetation_gdf['vegetation_type'].unique())
colors = ["#" + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)]) for _ in unique_vegetation_types]
vegetation_color_map = {vegetation_type: color for vegetation_type, color in zip(unique_vegetation_types, colors)}

# Create Folium map only if it hasn't been initialized yet
if not st.session_state.map_initialized:
    try:
        m = folium.Map(
            location=[vegetation_gdf.geometry.centroid.y.mean(), vegetation_gdf.geometry.centroid.x.mean()],
            zoom_start=10,
            tiles="OpenStreetMap"  # Use OpenStreetMap as the base layer
        )
        # Add Fullscreen plugin
        Fullscreen().add_to(m)

        # Create FeatureGroups for each layer
        vegetation_layer_group = folium.FeatureGroup(name="Vegetation Type (Random Colors)")
        sum_layer_group = folium.FeatureGroup(name="Subdivision Outlines")

        # Add vegetation layer with random colors based on vegetation_type
        for vegetation_type, color in vegetation_color_map.items():
            vegetation_data = vegetation_gdf[vegetation_gdf['vegetation_type'] == vegetation_type]
            folium.GeoJson(
                vegetation_data,
                style_function=lambda feature, color=color: {
                    "fillColor": color,
                    "color": "none",  # No polygon outlines
                    "fillOpacity": 0.4  # 40% transparency
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["subdivision", "vegetation_zone", "vegetation_type", "area_ha"],
                    aliases=["Subdivision:", "Vegetation Zone:", "Vegetation Type:", "Area (ha):"],
                    localize=True,
                    sticky=True
                )
            ).add_to(vegetation_layer_group)

        # Add subdivision outlines layer
        folium.GeoJson(
            sum_gdf,
            style_function=lambda feature: {
                "color": "black",  # Set outline color
                "weight": 2,       # Set line weight
                "fillOpacity": 0   # Make sure it is only an outline
            }
        ).add_to(sum_layer_group)

        # Add FeatureGroups to the map
        vegetation_layer_group.add_to(m)
        sum_layer_group.add_to(m)

        # Add LayerControl to toggle layers
        folium.LayerControl().add_to(m)

        # Store the map in session state
        st.session_state.folium_map = m
        st.session_state.map_initialized = True

    except Exception as e:
        st.error(f"Error creating Folium map: {e}")
        st.stop()

# Display the Folium map using Streamlit
if st.session_state.folium_map:
    st_folium(st.session_state.folium_map, width=700, height=500, returned_objects=[])
    # Display a table of vegetation data
st.write("Vegetation Data:")
st.dataframe(vegetation_gdf)
