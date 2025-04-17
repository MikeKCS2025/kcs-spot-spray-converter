import streamlit as st
import zipfile
import tempfile
import os
import shutil

st.set_page_config(page_title="Solvi to DJI Converter", layout="centered")
st.title("Solvi to DJI Converter")
st.caption("Upload your Solvi `.zip` or `.json` file and download DJI-compatible shapefiles.")

uploaded_file = st.file_uploader(
    "Drag and drop file here",
    type=["zip", "json"],
    help="Limit 200MB per file • ZIP, JSON"
)

spray_rate = st.number_input(
    "Enter Spray Rate (Gallons per Acre)",
    min_value=0.1,
    max_value=20.0,
    step=0.1,
    value=1.0
)

def process_zip(uploaded_file, gpa):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "input.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Identify base name from .shp file
            shp_file = next((f for f in os.listdir(temp_dir) if f.endswith(".shp")), None)
            if not shp_file:
                return None, "No .shp file found in the ZIP."

            base_name = os.path.splitext(shp_file)[0]
            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            missing = [ext for ext in required_exts if not os.path.exists(os.path.join(temp_dir, base_name + ext))]
            if missing:
                return None, f"Missing required files: {', '.join(missing)}"

            # ✅ Add GPA logic if needed (placeholder for metadata injection)

            # Create output zip
            output_zip_path = os.path.join(temp_dir, "DJI_ready.zip")
            with zipfile.ZipFile(output_zip_path, 'w') as zip_out:
                for ext in required_exts:
                    file_path = os.path.join(temp_dir, base_name + ext)
                    zip_out.write(file_path, arcname=os.path.basename(file_path))

            with open(output_zip_path, "rb") as f:
                return f.read(), None

    except Exception as e:
        return None, f"Unexpected error: {e}"

if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        output_file, error = process_zip(uploaded_file, spray_rate)

        if error:
            st.error(error)
        else:
            st.success("ZIP file uploaded. Processing complete!")
            st.download_button(
                label="Download DJI Shapefile ZIP",
                data=output_file,
                file_name="DJI_ready.zip",
                mime="application/zip"
            )
    elif uploaded_file.name.endswith(".json"):
        st.warning("JSON file support coming soon. Please upload a .zip from Solvi.")
