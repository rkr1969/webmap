import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium import GeoJson
from branca.colormap import LinearColormap
from streamlit_folium import st_folium  # Import st_folium

# Define colors with 40% transparency
COLORS = {
    'Terai or Madhesh': 'rgba(255, 0, 0, 0.4)',
    'Inner River Valley': 'rgba(0, 0, 255, 0.4)',
    'Bhawar': 'rgba(0, 255, 0, 0.4)',
    'Chure Hillslopes': 'rgba(0, 255, 0, 0.4)'
}

# Fetch GeoJSON data from GitHub
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/rkr1969/webmap/main/physiography_subdivision.geojson"
    gdf = gpd.read_file(url)
    
    # Debugging: Inspect the GeoDataFrame
    st.write("GeoDataFrame Info:")
    st.write(gdf.info())
    st.write("First 5 rows of GeoDataFrame:")
    st.write(gdf.head())
    
    return gdf

# Function to calculate summary tables
def calculate_summary_tables(gdf):
    # Table 1: Physiography-wise percentage of total area
    total_area = gdf['Area_sqkm'].sum()
    table1 = gdf.groupby('Physiography')['Area_sqkm'].sum().reset_index()
    table1['Percentage'] = (table1['Area_sqkm'] / total_area) * 100

    # Table 2: Subdivision-wise percentage of total area within each physiography
    table2 = gdf.groupby(['Physiography', 'subdivision'])['Area_sqkm'].sum().reset_index()
    table2['Percentage'] = (
        table2.groupby('Physiography')['Area_sqkm'].transform(lambda x: (x / x.sum()) * 100)
    )

    return table1, table2

# Main function
def main():
    st.title("Physiography Visualization")

    # Load data
    gdf = load_data()

    # Calculate summary tables
    table1, table2 = calculate_summary_tables(gdf)

    # Display summary tables
    st.subheader("Summary Table 1: Physiography-wise Percentage of Total Area")
    st.dataframe(table1)
    st.download_button(
        label="Download Table 1",
        data=table1.to_csv(index=False),
        file_name="summary_table1.csv",
        mime="text/csv"
    )

    st.subheader("Summary Table 2: Subdivision-wise Percentage of Total Area within Each Physiography")
    st.dataframe(table2)
    st.download_button(
        label="Download Table 2",
        data=table2.to_csv(index=False),
        file_name="summary_table2.csv",
        mime="text/csv"
    )

    # Create Folium map
    m = folium.Map(location=[gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()], zoom_start=7)

    # Add GeoJSON layer with styling
    def style_function(feature):
        physiography = feature['properties']['Physiography']
        return {
            'fillColor': COLORS.get(physiography, '#ffffff'),
            'color': 'none',  # No outer line
            'fillOpacity': 1  # Transparency is already included in color
        }

    folium.GeoJson(
        gdf.to_json(),  # Convert to JSON string
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=['subdivision', 'Physiography', 'Area_sqkm'], aliases=['Subdivision', 'Physiography', 'Area (sq km)'])
    ).add_to(m)

    # Display the map
    st.subheader("Interactive Map")
    folium_static = st_folium(m, width=700, height=500)  # Use st_folium to render the map

if __name__ == "__main__":
    main()
