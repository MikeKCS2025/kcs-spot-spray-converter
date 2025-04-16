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
            f.write(zip_bytes.read())

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        base_names = set()
        for file in os.listdir(temp_dir):
            if file.endswith(".shp"):
                base = os.path.splitext(file)[0]
                base_names.add(base)

        if not base_names:
            return None

        base_name = list(base_names)[0]
        required_exts = [".shp", ".shx", ".dbf", ".prj"]
        missing = [ext for ext in required_exts if not os.path.exists(os.path.join(temp_dir, base_name + ext))]

        if missing:
            return None

        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        for ext in required_exts:
            shutil.copy(os.path.join(temp_dir, base_name + ext), os.path.join(output_dir, base_name + ext))

        output_zip_path = os.path.join(temp_dir, f"DJI-ready_{uuid.uuid4().hex}.zip")
        with zipfile.ZipFile(output_zip_path, 'w') as zip_out:
            for ext in required_exts:
                file_path = os.path.join(output_dir, base_name + ext)
                zip_out.write(file_path, arcname=os.path.basename(file_path))

        with open(output_zip_path, "rb") as output_file:
            return output_file.read()

if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        result = extract_shapefiles_from_zip(uploaded_file)
        if result:
            st.success("✅ Successfully converted your Solvi file!")
            st.download_button(
                label="Download DJI-ready ZIP",
                data=result,
                file_name="dji_ready.zip",
                mime="application/zip"
            )
