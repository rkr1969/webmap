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
if "main_gdf" not in st.session_state:
    st.session_state.main_gdf = None
if "sum_gdf" not in st.session_state:
    st.session_state.sum_gdf = None

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
if st.session_state.main_gdf is None or st.session_state.sum_gdf is None:
    main_gdf = load_geojson(main_layer_url)
    sum_gdf = load_geojson(sum_layer_url)

    # Reproject geometries to EPSG:4326 (required by Folium)
    main_gdf = main_gdf.to_crs(epsg=4326)
    sum_gdf = sum_gdf.to_crs(epsg=4326)

    # Fix invalid geometries
    main_gdf['geometry'] = main_gdf.geometry.apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)
    sum_gdf['geometry'] = sum_gdf.geometry.apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)

    # Store data in session state
    st.session_state.main_gdf = main_gdf
    st.session_state.sum_gdf = sum_gdf

# Retrieve data from session state
main_gdf = st.session_state.main_gdf
sum_gdf = st.session_state.sum_gdf

# Generate random colors for years
unique_years = sorted(main_gdf['Year'].unique())
colors = ["#" + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)]) for _ in unique_years]
year_color_map = {year: color for year, color in zip(unique_years, colors)}

# Create Folium map
if st.session_state.folium_map is None:
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
                fields=["subdivision", "Area_hectare", "Year"],  # Fields to display in tooltip
                aliases=["Subdivision:", "Area (ha):", "Year:"],  # Custom labels for fields
                localize=True,  # Format numbers for better readability
                sticky=True  # Keep tooltip visible while hovering
            )
        ).add_to(m)

    # Add summary layer (black outlines)
    folium.GeoJson(
        sum_gdf,
        style_function=lambda feature: {
            "color": "black",
            "weight": 2,
            "fillOpacity": 0
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["subdivision"],  # Fields to display in tooltip
            aliases=["Subdivision:"],  # Custom label for field
            localize=True,
            sticky=True
        )
    ).add_to(m)

    # Store the map in session state
    st.session_state.folium_map = m
    st.session_state.map_initialized = True

# Display the map using st_folium
if st.session_state.folium_map is not None:
    st_folium(st.session_state.folium_map, width=700, height=500, returned_objects=[])

# Create summary tables
st.header("Summary Tables")

# Table 1: Year-wise sum with percentage of total
table1 = main_gdf.groupby('Year')['Area_hectare'].sum().reset_index()
table1['% of Total'] = (table1['Area_hectare'] / table1['Area_hectare'].sum() * 100).round(2)
st.subheader("Year-wise Tree Loss Area (hectares)")
st.dataframe(table1)
st.download_button(
    label="Download Table 1",
    data=table1.to_csv().encode('utf-8'),
    file_name='year_wise_tree_loss.csv',
    mime='text/csv'
)

# Table 2: Subdivision and Year-wise sum with percentages
table2 = main_gdf.groupby(['subdivision', 'Year'])['Area_hectare'].sum().reset_index()

# Calculate % of subdivision total
subdivision_totals = table2.groupby('subdivision')['Area_hectare'].sum()
table2['% of Subdivision'] = table2.apply(
    lambda row: (row['Area_hectare'] / subdivision_totals[row['subdivision']] * 100).round(2), axis=1
)

# Calculate % of overall total
table2['% of Total'] = (table2['Area_hectare'] / table2['Area_hectare'].sum() * 100).round(2)

st.subheader("Subdivision & Year-wise Tree Loss Area (hectares)")
st.dataframe(table2)
st.download_button(
    label="Download Table 2",
    data=table2.to_csv().encode('utf-8'),
    file_name='subdivision_year_wise_tree_loss.csv',
    mime='text/csv'
)

# Interactive Chart: Year vs Area_hectare
st.header("Interactive Chart: Year vs Area_hectare")
chart_data = main_gdf.groupby('Year')['Area_hectare'].sum().reset_index()

fig = px.bar(
    chart_data,
    x='Year',
    y='Area_hectare',
    title="Year-wise Tree Loss Area (hectares)",
    labels={'Year': 'Year', 'Area_hectare': 'Tree Loss Area (hectares)'},
    template="plotly_dark"  # Optional: Dark theme for better aesthetics
)

fig.update_traces(marker_color='rgb(158,202,225)', marker_line_color='rgb(8,48,107)',
                  marker_line_width=1.5, opacity=0.6)

st.plotly_chart(fig, use_container_width=True)
