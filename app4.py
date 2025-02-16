import streamlit as st
import requests
import folium
from folium.plugins import MeasureControl, Fullscreen
import pandas as pd
import geopandas as gpd
from streamlit_folium import st_folium
import random

# Load GeoJSON data for Landuse_Ward
@st.cache_data
def load_geojson(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error loading GeoJSON: {e}")
        return None

url_landuse = "https://raw.githubusercontent.com/rkr1969/webmap/main/Landuse_Ward.geojson"
geojson_data = load_geojson(url_landuse)

# Load GeoJSON data for Management Regime
url_management_regime = "https://raw.githubusercontent.com/rkr1969/webmap/main/Management_Regime.geojson"
management_regime_data = load_geojson(url_management_regime)

if geojson_data is None or management_regime_data is None:
    st.error("Failed to load required GeoJSON data.")
else:
    # Extract unique values for Subdivision, Landuse, and Regime
    subdivisions = sorted(set(feature['properties']['Subdivision'] for feature in geojson_data['features']))
    landuses = sorted(set(feature['properties']['Landuse'] for feature in geojson_data['features']))
    regimes = sorted(set(feature['properties']['regime'] for feature in management_regime_data['features']))

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

        # Add Management Regime layer
        management_regime_layer = folium.FeatureGroup(name="Management Regime")
        regime_colors = {regime: "#{:06x}".format(random.randint(0, 0xFFFFFF)) for regime in regimes}
        for feature in management_regime_data['features']:
            regime = feature['properties']['regime']
            color = regime_colors.get(regime, 'gray')
            folium.GeoJson(
                feature,
                style_function=lambda x, color=color: {
                    'fillColor': color,
                    'color': 'none',
                    'weight': 0,
                    'fillOpacity': 0.4
                },
                tooltip=f"Regime: {regime} "
                        f"Area (hectares): {feature['properties'].get('Area_hectare', 0):.2f}"
            ).add_to(management_regime_layer)
        management_regime_layer.add_to(m)

        # Load ForestFire GeoJSON data
        url_forestfire = "https://raw.githubusercontent.com/rkr1969/webmap/main/ForestFire.geojson"
        gdf = gpd.read_file(url_forestfire)

        # Filter ForestFire data based on selected subdivision and landuse
        filtered_gdf = gdf.copy()
        if subdivision != 'All':
            filtered_gdf = filtered_gdf[filtered_gdf['Subdivision'] == subdivision]
        if landuse != 'All':
            filtered_gdf = filtered_gdf[filtered_gdf['Palika'].isin(
                [feature['properties']['Palika'] for feature in filtered_features]
            )]

        # Add ForestFire layer
        forestfire_layer = folium.FeatureGroup(name="Forest Fire Sensitivity")
        color_mapping = {
            'High Sensitive': 'darkblue',
            'Moderately Sensitive': 'yellow',
            'Sensitive': 'red'
        }
        for desc, color in color_mapping.items():
            subset = filtered_gdf[filtered_gdf['Description'] == desc]
            if not subset.empty:
                folium.GeoJson(
                    subset,
                    name=desc,
                    style_function=lambda x, color=color: {
                        'fillColor': color,
                        'color': 'none',
                        'weight': 0,
                        'fillOpacity': 0.4
                    },
                    tooltip=folium.GeoJsonTooltip(
                        fields=['Subdivision', 'Palika', 'Description', 'Area_hectare'],
                        aliases=['Subdivision:', 'Palika:', 'Fire Sensitivity:', 'Area (hectares):'],
                        localize=True
                    )
                ).add_to(forestfire_layer)
        forestfire_layer.add_to(m)

        # Add LayerControl to toggle layers
        folium.LayerControl().add_to(m)

        return m

    # Function to update and display summarized tables
    def update_tables(subdivision, landuse):
        # Filter Landuse_Ward data
        filtered_features = [
            feature for feature in geojson_data['features']
            if (feature['properties']['Subdivision'] == subdivision or subdivision == 'All') and
               (feature['properties']['Landuse'] == landuse or landuse == 'All')
        ]
        landuse_data = pd.DataFrame([
            {
                'Subdivision': feature['properties']['Subdivision'],
                'Landuse': feature['properties']['Landuse'],
                'Area_hectare': feature['properties'].get('Area_hectare', 0)
            } for feature in filtered_features
        ])

        # Summarize Landuse table
        if landuse_data.empty:
            landuse_summary = pd.DataFrame(columns=['Subdivision', 'Landuse', 'Area_hectare', '% of Subdivision', '% of Total'])
        else:
            landuse_summary = (
                landuse_data.groupby(['Subdivision', 'Landuse'])
                .agg(Area_hectare=('Area_hectare', 'sum'))
                .reset_index()
            )
            total_area = landuse_summary['Area_hectare'].sum()
            subdivision_totals = landuse_summary.groupby('Subdivision')['Area_hectare'].sum().rename('Subdivision_Total')
            landuse_summary = landuse_summary.merge(subdivision_totals, on='Subdivision')
            landuse_summary['% of Subdivision'] = (landuse_summary['Area_hectare'] / landuse_summary['Subdivision_Total'] * 100).round(2)
            landuse_summary['% of Total'] = (landuse_summary['Area_hectare'] / total_area * 100).round(2)
            landuse_summary = landuse_summary.drop('Subdivision_Total', axis=1)
            landuse_summary['% of Subdivision'] = landuse_summary['% of Subdivision'].astype(str) + '%'
            landuse_summary['% of Total'] = landuse_summary['% of Total'].astype(str) + '%'

        # Filter ForestFire data
        url_forestfire = "https://raw.githubusercontent.com/rkr1969/webmap/main/ForestFire.geojson"
        gdf = gpd.read_file(url_forestfire)
        filtered_gdf = gdf.copy()
        if subdivision != 'All':
            filtered_gdf = filtered_gdf[filtered_gdf['Subdivision'] == subdivision]
        if landuse != 'All':
            filtered_gdf = filtered_gdf[filtered_gdf['Palika'].isin(
                [feature['properties']['Palika'] for feature in filtered_features]
            )]

        # Summarize ForestFire table
        if filtered_gdf.empty:
            forestfire_summary = pd.DataFrame(columns=['Subdivision', 'Fire Sensitivity', 'Area_hectare', '% of Subdivision', '% of Total'])
        else:
            forestfire_summary = (
                filtered_gdf.groupby(['Subdivision', 'Description'])
                .agg(Area_hectare=('Area_hectare', 'sum'))
                .reset_index()
            )
            forestfire_summary = forestfire_summary.rename(columns={'Description': 'Fire Sensitivity'})
            total_area = forestfire_summary['Area_hectare'].sum()
            subdivision_totals = forestfire_summary.groupby('Subdivision')['Area_hectare'].sum().rename('Subdivision_Total')
            forestfire_summary = forestfire_summary.merge(subdivision_totals, on='Subdivision')
            forestfire_summary['% of Subdivision'] = (forestfire_summary['Area_hectare'] / forestfire_summary['Subdivision_Total'] * 100).round(2)
            forestfire_summary['% of Total'] = (forestfire_summary['Area_hectare'] / total_area * 100).round(2)
            forestfire_summary = forestfire_summary.drop('Subdivision_Total', axis=1)
            forestfire_summary['% of Subdivision'] = forestfire_summary['% of Subdivision'].astype(str) + '%'
            forestfire_summary['% of Total'] = forestfire_summary['% of Total'].astype(str) + '%'

        return landuse_summary, forestfire_summary

    # Main App Logic
    if apply_filters:
        # Update Map
        st.subheader("Interactive Map")
        m = update_combined_map(selected_subdivision, selected_landuse)
        st_folium(m, width=700, height=500)

        # Update Tables
        st.subheader("Summary Tables")
        landuse_summary, forestfire_summary = update_tables(selected_subdivision, selected_landuse)

        st.write("Landuse Summary Table")
        st.dataframe(landuse_summary)

        st.write("Forest Fire Summary Table")
        st.dataframe(forestfire_summary)

        # Download Buttons
        st.subheader("Download Summarized Tables")
        if not landuse_summary.empty:
            st.download_button(
                label="Download Landuse Summary Table",
                data=landuse_summary.to_csv(index=False),
                file_name="landuse_summary_table.csv",
                mime="text/csv"
            )
        else:
            st.warning("No Landuse data available to download.")

        if not forestfire_summary.empty:
            st.download_button(
                label="Download ForestFire Summary Table",
                data=forestfire_summary.to_csv(index=False),
                file_name="forestfire_summary_table.csv",
                mime="text/csv"
            )
        else:
            st.warning("No ForestFire data available to download.")
    else:
        # Initial Map
        st.subheader("Interactive Map")
        m = update_combined_map('All', 'All')
        st_folium(m, width=700, height=500)

        # Initial Tables
        st.subheader("Summary Tables")
        landuse_summary, forestfire_summary = update_tables('All', 'All')

        st.write("Landuse Summary Table")
        st.dataframe(landuse_summary)

        st.write("Forest Fire Summary Table")
        st.dataframe(forestfire_summary)

        # Download Buttons
        st.subheader("Download Summarized Tables")
        if not landuse_summary.empty:
            st.download_button(
                label="Download Landuse Summary Table",
                data=landuse_summary.to_csv(index=False),
                file_name="landuse_summary_table.csv",
                mime="text/csv"
            )
        else:
            st.warning("No Landuse data available to download.")

        if not forestfire_summary.empty:
            st.download_button(
                label="Download ForestFire Summary Table",
                data=forestfire_summary.to_csv(index=False),
                file_name="forestfire_summary_table.csv",
                mime="text/csv"
            )
        else:
            st.warning("No ForestFire data available to download.")
