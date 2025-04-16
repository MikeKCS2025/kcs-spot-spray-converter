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

def extract_and_package_shapefiles(uploaded_file):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "input.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.read())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            shapefiles = [f for f in os.listdir(temp_dir) if f.endswith(".shp")]
            if not shapefiles:
                return None, "No .shp files found inside the ZIP."

            base_name = os.path.splitext(shapefiles[0])[0]
            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            missing = [ext for ext in required_exts if not os.path.exists(os.path.join(temp_dir, base_name + ext))]

            if missing:
                return None, f"Missing required files: {', '.join(missing)}"

            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            for ext in required_exts:
                src = os.path.join(temp_dir, base_name + ext)
                dst = os.path.join(output_dir, base_name + ext)
                shutil.copy(src, dst)

            output_zip_path = os.path.join(temp_dir, f"dji-ready-{uuid.uuid4().hex[:8]}.zip")
            with zipfile.ZipFile(output_zip_path, 'w') as zipf:
                for ext in required_exts:
                    file_path = os.path.join(output_dir, base_name + ext)
                    zipf.write(file_path, arcname=os.path.basename(file_path))

            with open(output_zip_path, "rb") as f:
                return f.read(), None

    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        result, error = extract_and_package_shapefiles(uploaded_file)
        if error:
            st.error(f"❌ {error}")
        else:
            st.success("✅ Successfully converted your Solvi file!")
            st.download_button(
                label="Download DJI-ready ZIP",
                data=result,
                file_name="dji_ready.zip",
                mime="application/zip"
            )
    else:
        st.warning("Only Solvi .zip exports are supported right now.")
