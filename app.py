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

def process_zip(uploaded_file, spray_rate):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "input.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Dynamically find the base name of the shapefile
            base_names = set()
            for file in os.listdir(temp_dir):
                if file.endswith(".shp"):
                    base_names.add(os.path.splitext(file)[0])

            if not base_names:
                return None, "No .shp file found in the ZIP."

            base_name = list(base_names)[0]
            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            missing = [ext for ext in required_exts if not os.path.exists(os.path.join(temp_dir, base_name + ext))]
            if missing:
                return None, f"Missing required files: {', '.join(missing)}"

            # Write metadata for spray rate
            meta_path = os.path.join(temp_dir, "spray_rate.txt")
            with open(meta_path, "w") as meta_file:
                meta_file.write(f"Spray Rate: {spray_rate} gallons per acre")

            # Create output zip
            output_zip_path = os.path.join(temp_dir, "DJI_ready.zip")
            with zipfile.ZipFile(output_zip_path, 'w') as zip_out:
                for ext in required_exts:
                    file_path = os.path.join(temp_dir, base_name + ext)
                    zip_out.write(file_path, arcname=os.path.basename(file_path))
                zip_out.write(meta_path, arcname="spray_rate.txt")

            with open(output_zip_path, "rb") as f:
                return f.read(), None

    except Exception as e:
        return None, f"Unexpected error: {e}"

# --- UI Logic ---
if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        spray_rate = st.number_input("Enter Spray Rate (Gallons per Acre)", min_value=0.1, max_value=20.0, value=1.00, step=0.1)
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
        st.warning("JSON support coming soon. Please upload a .zip file for now.")
