import streamlit as st
import geopandas as gpd
import pandas as pd
import tempfile
import zipfile
import os

# Branding and layout setup
st.set_page_config(page_title="KCS Spot Spray Converter", layout="centered")
st.image("https://yourdomain.com/logo.png", width=200)  # Replace with actual logo URL
st.title("Kingdom Crop Spraying - Spot Spray Converter")
st.markdown("Convert Solvi shapefiles into DJI Agras-ready CSV files for targeted spot spraying with ease.")

# Step 1: Upload ZIP file containing SHP components
uploaded_file = st.file_uploader("Upload your Solvi SHP file (.zip with .shp, .shx, .dbf, .prj included)", type="zip")

radius = st.number_input("Default Spray Radius (m)", min_value=0.1, value=1.0, step=0.1)
amount = st.number_input("Default Spray Amount (L)", min_value=0.1, value=0.5, step=0.1)

if uploaded_file is not None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "upload.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.read())

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]

        if not shp_files:
            st.error("No .shp file found in the uploaded archive.")
        else:
            shp_path = os.path.join(tmpdir, shp_files[0])
            try:
                gdf = gpd.read_file(shp_path)
                gdf['Longitude'] = gdf.geometry.x
                gdf['Latitude'] = gdf.geometry.y
                gdf['Radius (m)'] = radius
                gdf['Amount (L)'] = amount
                gdf['Name'] = ['Target_{}'.format(i+1) for i in range(len(gdf))]

                dji_df = gdf[['Longitude', 'Latitude', 'Radius (m)', 'Amount (L)', 'Name']]
                st.success("✅ File converted successfully!")
                st.dataframe(dji_df.head())

                csv_bytes = dji_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download DJI-Compatible CSV",
                    data=csv_bytes,
                    file_name="dji_spot_spray_targets.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"❌ Error reading shapefile: {e}")

st.markdown("---")
st.caption("© 2025 Kingdom Crop Spraying. All rights reserved. | www.kingdomcropspraying.com")
