import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from branca.colormap import LinearColormap
import base64

# Load GeoJSON file from GitHub
@st.cache_data
def load_geojson(url):
    return gpd.read_file(url)

# Define colors for physiography
COLORS = {
    'Terai or Madhesh': 'rgba(255, 0, 0, 0.4)',  # Red with 40% transparency
    'Inner River Valley': 'rgba(0, 0, 255, 0.4)',  # Blue with 40% transparency
    'Bhawar': 'rgba(0, 128, 0, 0.4)',  # Green with 40% transparency
    'Chure Hillslopes': 'rgba(0, 128, 0, 0.4)'  # Green with 40% transparency
}

# Function to calculate summary tables
def calculate_summary_tables(gdf):
    # Table-1: Subdivision-wise percentage of total Area_sqkm by Physiography
    table1 = (
        gdf.groupby(['Physiography', 'subdivision'])['Area_sqkm']
        .sum()
        .groupby(level=0)  # Group by 'Physiography'
        .apply(lambda x: 100 * x / x.sum())  # Calculate percentage
        .reset_index()  # Reset index without specifying `name`
    )
    table1.rename(columns={0: 'Percentage'}, inplace=True)  # Rename the aggregated column

    # Table-2: Physiography-wise percentage of total Area_sqkm
    total_area = gdf['Area_sqkm'].sum()
    table2 = (
        gdf.groupby('Physiography')['Area_sqkm']
        .sum()
        .apply(lambda x: 100 * x / total_area)  # Calculate percentage
        .reset_index()  # Reset index without specifying `name`
    )
    table2.rename(columns={'Area_sqkm': 'Percentage'}, inplace=True)  # Rename the aggregated column

    return table1, table2

# Function to download DataFrame as CSV
def download_csv(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download {filename}</a>'
    return href

# Main Streamlit App
def main():
    st.title("Physiography Visualization")

    # Load GeoJSON data
    geojson_url = "https://raw.githubusercontent.com/rkr1969/webmap/main/physiography_subdivision.geojson"
    gdf = load_geojson(geojson_url)

    # Calculate summary tables
    table1, table2 = calculate_summary_tables(gdf)

    # Display summary tables
    st.subheader("Summary Table-1: Subdivision-wise Percentage of Total Area_sqkm by Physiography")
    st.dataframe(table1)
    st.markdown(download_csv(table1, "summary_table1.csv"), unsafe_allow_html=True)

    st.subheader("Summary Table-2: Physiography-wise Percentage of Total Area_sqkm")
    st.dataframe(table2)
    st.markdown(download_csv(table2, "summary_table2.csv"), unsafe_allow_html=True)

    # Create Folium Map
    m = folium.Map(location=[gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()], zoom_start=8)

    # Add Physiography Layer
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': COLORS.get(x['properties']['Physiography'], 'rgba(0, 0, 0, 0.4)'),
            'color': 'none',  # No outer line
            'fillOpacity': 0.4
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['subdivision', 'Physiography', 'Area_sqkm'],
            aliases=['Subdivision:', 'Physiography:', 'Area (sqkm):']
        )
    ).add_to(m)

    # Add Subdivision Summary Layer
    subdivision_sum_url = "https://raw.githubusercontent.com/rkr1969/webmap/main/subdivision_sum.geojson"
    subdivision_gdf = load_geojson(subdivision_sum_url)

    folium.GeoJson(
        subdivision_gdf,
        style_function=lambda x: {'fillColor': 'transparent', 'color': 'black'},
        tooltip=folium.GeoJsonTooltip(fields=['subdivision'], aliases=['Subdivision:'])
    ).add_to(m)

    # Display Map in Streamlit
    st.subheader("Interactive Map")
    folium_static(m)

# Run the app
if __name__ == "__main__":
    main()
