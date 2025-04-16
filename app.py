import streamlit as st
import zipfile
import tempfile
import os
import shutil
import uuid

st.set_page_config(page_title="Solvi to DJI Converter", layout="centered")

st.title("Solvi to DJI Converter")
st.caption("Upload your Solvi `.zip` or `.json` file and download DJI-compatible shapefiles.")

uploaded_file = st.file_uploader(
    "Drag and drop file here", 
    type=["zip", "json"],
    help="Limit 200MB per file • ZIP, JSON"
)

def extract_shapefiles_from_zip(zip_bytes):
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "input.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_bytes.getvalue())
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Look for .shp and required associated files
        base_names = set()
        for file in os.listdir(temp_dir):
            if file.endswith(".shp"):
                base = os.path.splitext(file)[0]
                base_names.add(base)

        if not base_names:
            return None, "No .shp file found inside the ZIP."

        base_name = list(base_names)[0]
        required_exts = [".shp", ".shx", ".dbf", ".prj"]
        missing = [ext for ext in required_exts if not os.path.exists(os.path.join(temp_dir, base_name + ext))]

        if missing:
            return None, f"Missing associated shapefile components: {', '.join(missing)}"

        # Create output zip
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        for ext in required_exts:
            shutil.copy(os.path.join(temp_dir, base_name + ext), os.path.join(output_dir, base_name + ext))

        output_zip_path = os.path.join(temp_dir, f"{base_name}_DJI_Ready.zip")
        with zipfile.ZipFile(output_zip_path, "w") as zipf:
            for file in os.listdir(output_dir):
                zipf.write(os.path.join(output_dir, file), file)

        return output_zip_path, None

if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        output_zip, error = extract_shapefiles_from_zip(uploaded_file)
        if error:
            st.error(error)
        elif output_zip:
            with open(output_zip, "rb") as f:
                st.success("✅ Conversion successful! Your DJI-ready shapefile is ready.")
                st.download_button(
                    label="⬇️ Download DJI Shapefile Zip",
                    data=f.read(),
                    file_name=os.path.basename(output_zip),
                    mime="application/zip"
                )
    else:
        st.warning("Currently, only .zip files containing shapefiles are supported.")
