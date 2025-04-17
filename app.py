import streamlit as st
import zipfile
import tempfile
import os
import shapefile
import json

st.set_page_config(page_title="Solvi to DJI Converter", layout="centered")
st.title("Solvi to DJI Converter")
st.caption("Upload your Solvi `.zip` or `.json` file and download DJI-compatible outputs.")

uploaded_file = st.file_uploader("Upload ZIP or JSON", type=["zip", "json"])

# GPA Presets + Custom Input
preset_options = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
selected = st.selectbox("Select GPA (Gallons per Acre)", options=preset_options + ["Custom"])

if selected == "Custom":
    spray_rate = st.number_input("Enter custom GPA", min_value=0.1, value=1.0, step=0.1)
else:
    spray_rate = float(selected)

# Output format selector
output_format = st.selectbox("Select Output Format", ["Shapefile ZIP", "GeoJSON"])

# ZIP → Shapefile or GeoJSON converter
def process_zip_to_output(uploaded_file, spray_rate, output_format):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "upload.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find .shp
            shp_file = next((f for f in os.listdir(temp_dir) if f.endswith(".shp")), None)
            if not shp_file:
                return None, "No .shp file found in the archive."

            base_name = os.path.splitext(shp_file)[0]
            base_path = os.path.join(temp_dir, base_name)
            required_exts = [".shp", ".shx", ".dbf", ".prj"]

            for ext in required_exts:
                if not os.path.exists(base_path + ext):
                    return None, f"Missing required file: {base_name + ext}"

            if output_format == "Shapefile ZIP":
                # Repackage the original shapefile set
                output_zip = os.path.join(temp_dir, "DJI_ready.zip")
                with zipfile.ZipFile(output_zip, "w") as zip_out:
                    for ext in required_exts:
                        zip_out.write(base_path + ext, arcname=os.path.basename(base_path + ext))
                with open(output_zip, "rb") as f:
                    return f.read(), None

            elif output_format == "GeoJSON":
                r = shapefile.Reader(base_path)
                geojson_data = {
                    "type": "FeatureCollection",
                    "features": []
                }

                for sr in r.shapeRecords():
                    geometry = sr.shape.__geo_interface__
                    props = {f"field_{i}": val for i, val in enumerate(sr.record)}
                    props["GPA"] = spray_rate
                    geojson_data["features"].append({
                        "type": "Feature",
                        "geometry": geometry,
                        "properties": props
                    })

                geojson_path = os.path.join(temp_dir, "DJI_ready.geojson")
                with open(geojson_path, "w") as f:
                    json.dump(geojson_data, f)

                with open(geojson_path, "rb") as f:
                    return f.read(), None

        return None, "Unhandled processing condition."
    except Exception as e:
        return None, f"Unexpected error: {e}"

# Trigger processing
if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        output_data, error = process_zip_to_output(uploaded_file, spray_rate, output_format)

        if error:
            st.error(error)
        else:
            ext = "zip" if output_format == "Shapefile ZIP" else "geojson"
            mime = "application/zip" if ext == "zip" else "application/json"
            st.success("Processing complete!")
            st.download_button(
                label=f"Download {ext.upper()}",
                data=output_data,
                file_name=f"DJI_ready.{ext}",
                mime=mime
            )

    elif uploaded_file.name.endswith(".json"):
        st.warning("JSON support is coming soon — stay tuned!")
