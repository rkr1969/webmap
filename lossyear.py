import streamlit as st
import pandas as pd
import geopandas as gpd
import pydeck as pdk
from datetime import datetime
import random
import plotly.express as px  # For interactive charts

# Load data from GitHub
base_url = "https://raw.githubusercontent.com/rkr1969/webmap/main/"

def load_geojson(url):
    gdf = gpd.read_file(url)
    # Convert Year to datetime and extract year component
    if 'Year' in gdf.columns:
        gdf['Year'] = pd.to_datetime(gdf['Year']).dt.year
    return gdf

main_layer_url = base_url + "lossyear_subdivision.geojson"
sum_layer_url = base_url + "subdivision_sum.geojson"

main_gdf = load_geojson(main_layer_url)
sum_gdf = load_geojson(sum_layer_url)

# Generate random colors for years
unique_years = sorted(main_gdf['Year'].unique())
colors = [tuple(random.randint(0, 255) for _ in range(3)) for _ in unique_years]
year_color_map = {year: color for year, color in zip(unique_years, colors)}

# Add a color column to main_gdf based on the Year
main_gdf['color'] = main_gdf['Year'].apply(lambda year: list(year_color_map[year]) + [100])

# Ensure geometries are valid and in the correct format
main_gdf['geometry'] = main_gdf.geometry.apply(lambda geom: geom if geom.is_valid else geom.buffer(0))
sum_gdf['geometry'] = sum_gdf.geometry.apply(lambda geom: geom if geom.is_valid else geom.buffer(0))

# Reproject geometries to EPSG:4326 (required by PyDeck)
main_gdf = main_gdf.to_crs(epsg=4326)
sum_gdf = sum_gdf.to_crs(epsg=4326)

# Calculate total tree loss area
total_loss = main_gdf['Area_hectare'].sum()

# Create PyDeck layers
main_layer = pdk.Layer(
    'GeoJsonLayer',  # Use GeoJsonLayer instead of PolygonLayer
    data=main_gdf.__geo_interface__,  # Pass GeoJSON-compatible data
    stroked=False,
    filled=True,
    get_fill_color='color',  # Use the precomputed color column
    opacity=0.4,
    pickable=True,
    auto_highlight=True,
    visible=True  # Initially visible
)

sum_layer = pdk.Layer(
    'GeoJsonLayer',  # Use GeoJsonLayer instead of PolygonLayer
    data=sum_gdf.__geo_interface__,  # Pass GeoJSON-compatible data
    stroked=True,
    filled=False,
    get_line_color=[0, 0, 0],
    pickable=True,
    visible=True  # Initially visible
)

# Set view state
view_state = pdk.ViewState(
    latitude=main_gdf.geometry.centroid.y.mean(),
    longitude=main_gdf.geometry.centroid.x.mean(),
    zoom=10
)

# Add OpenStreetMap as basemap
basemap = pdk.Layer(
    "TileLayer",
    url="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    opacity=1.0
)

# Layer visibility toggles
st.sidebar.header("Layer Controls")
show_main_layer = st.sidebar.checkbox("Show Main Layer", value=True)
show_sum_layer = st.sidebar.checkbox("Show Summary Layer", value=True)

# Update layer visibility
main_layer.visible = show_main_layer
sum_layer.visible = show_sum_layer

# Create deck
deck = pdk.Deck(
    layers=[basemap, main_layer, sum_layer],
    initial_view_state=view_state,
    tooltip={
        'html': '<b>Subdivision:</b> {subdivision}<br/>'
                '<b>Area (ha):</b> {Area_hectare}<br/>'
                '<b>Year:</b> {Year}',
        'style': {'color': 'white'}
    }
)

# Display map
st.pydeck_chart(deck)

# Create summary tables
st.header("Summary Tables")

# Table 1: Year-wise sum with percentage of total
table1 = main_gdf.groupby('Year')['Area_hectare'].sum().reset_index()
table1['% of Total'] = (table1['Area_hectare'] / total_loss * 100).round(2)
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
table2['% of Total'] = (table2['Area_hectare'] / total_loss * 100).round(2)

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
