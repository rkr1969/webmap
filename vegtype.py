import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import Fullscreen
import random
import plotly.express as px
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
    vegetation_gdf['geometry'] = vegetation_gdf.geometry.apply(
        lambda geom: geom.buffer(0) if not geom.is_valid else geom
    )
    sum_gdf['geometry'] = sum_gdf.geometry.apply(
        lambda geom: geom.buffer(0) if not geom.is_valid else geom
    )

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

# Create Folium map
if st.session_state.folium_map is None:
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
            "color": "black",
            "weight": 2,
            "fillOpacity": 0
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["subdivision"],
            aliases=["Subdivision:"],
            localize=True,
            sticky=True
        )
    ).add_to(sum_layer_group)

    # Add FeatureGroups to the map
    vegetation_layer_group.add_to(m)
    sum_layer_group.add_to(m)

    # Add LayerControl to toggle layers
    folium.LayerControl().add_to(m)

    # Store the map in session state
    st.session_state.folium_map = m
    st.session_state.map_initialized = True

# Display the map using st_folium
if st.session_state.folium_map is not None:
    st_folium(st.session_state.folium_map, width=700, height=500, returned_objects=[])

# Create summary tables
st.header("Summary Tables")

# Table 1: Subdivision-wise percentage of total area_ha grouped by vegetation_type
total_area = vegetation_gdf['area_ha'].sum()
table1 = vegetation_gdf.groupby(['subdivision', 'vegetation_type'])['area_ha'].sum().reset_index()
table1['% of Total'] = (table1['area_ha'] / total_area * 100).round(2)
st.subheader("Subdivision-wise Vegetation Type Area Distribution")
st.dataframe(table1)
st.download_button(
    label="Download Table 1",
    data=table1.to_csv(index=False).encode('utf-8'),
    file_name='subdivision_vegetation_type_summary.csv',
    mime='text/csv'
)

# Table 2: Vegetation type-wise percentage of total area_ha
table2 = vegetation_gdf.groupby('vegetation_type')['area_ha'].sum().reset_index()
table2['% of Total'] = (table2['area_ha'] / total_area * 100).round(2)
st.subheader("Vegetation Type-wise Area Distribution")
st.dataframe(table2)
st.download_button(
    label="Download Table 2",
    data=table2.to_csv(index=False).encode('utf-8'),
    file_name='vegetation_type_summary.csv',
    mime='text/csv'
)

# Interactive Bar Chart: Subdivision and Vegetation Type vs Area (ha)
st.header("Bar Chart: Subdivision & Vegetation Type vs Area (ha)")
chart_data = vegetation_gdf.groupby(['subdivision', 'vegetation_type'])['area_ha'].sum().reset_index()

# Create an interactive bar chart using Plotly
fig = px.bar(
    chart_data,
    x="subdivision",
    y="area_ha",
    color="vegetation_type",
    title="Subdivision & Vegetation Type vs Area (ha)",
    labels={"subdivision": "Subdivision", "area_ha": "Area (ha)", "vegetation_type": "Vegetation Type"},
    template="plotly_dark",  # Optional: Dark theme for better aesthetics
    barmode="group"  # Group bars by vegetation type
)

# Update layout for better readability
fig.update_layout(
    xaxis_title="Subdivision",
    yaxis_title="Area (ha)",
    legend_title="Vegetation Type",
    margin=dict(l=50, r=50, t=50, b=50),
    height=600
)

# Display the bar chart
st.plotly_chart(fig, use_container_width=True)
