import streamlit as st
import zipfile
import tempfile
import os
import shutil
import shapefile  # pyshp
from shapefile import Writer, Reader

st.set_page_config(page_title="Solvi to DJI Converter", layout="centered")

st.title("Solvi to DJI Converter")
st.caption("Upload your Solvi `.zip` or `.json` file and download DJI-compatible shapefiles.")

uploaded_file = st.file_uploader(
    "Drag and drop file here",
    type=["zip", "json"],
    help="Limit 200MB per file • ZIP, JSON"
)

gpa = st.number_input(
    "Enter Spray Rate (Gallons per Acre)",
    min_value=0.1,
    max_value=10.0,
    step=0.1,
    value=1.0
)

def convert_zip(zip_bytes, gpa):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "input.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_bytes.getvalue())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find base shapefile
            base_names = set()
            for file in os.listdir(temp_dir):
                if file.endswith(".shp"):
                    base = os.path.splitext(file)[0]
                    base_names.add(base)

            if not base_names:
                return None, None, "No .shp file found in the ZIP."

            base_name = list(base_names)[0]
            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            missing = [ext for ext in required_exts if not os.path.exists(os.path.join(temp_dir, base_name + ext))]
            if missing:
                return None, None, f"Missing required files: {', '.join(missing)}"

            # Copy original for safe export
            standard_zip = os.path.join(temp_dir, "original_dji.zip")
            with zipfile.ZipFile(standard_zip, 'w') as orig_zip:
                for ext in required_exts:
                    file_path = os.path.join(temp_dir, base_name + ext)
                    orig_zip.write(file_path, arcname=os.path.basename(file_path))

            # Read and update DBF
            reader = Reader(os.path.join(temp_dir, base_name + ".shp"))
            fields = reader.fields[1:]  # skip DeletionFlag
            field_names = [field[0] for field in fields]
            records = reader.records()
            shapes = reader.shapes()

            new_dbf = os.path.join(temp_dir, "updated.dbf")
            writer = Writer(os.path.join(temp_dir, base_name))
            for field in fields:
                writer.field(*field)

            if "Rate" not in field_names:
                writer.field("Rate", "N", 10, 2)

            for i, record in enumerate(records):
                record = list(record)
                if "Rate" not in field_names:
                    record.append(round(gpa, 2))
                else:
                    rate_idx = field_names.index("Rate")
                    record[rate_idx] = round(gpa, 2)
                writer.record(*record)
                writer.shape(shapes[i])

            writer.close()

            # Updated zip
            updated_zip = os.path.join(temp_dir, "updated_dji.zip")
            with zipfile.ZipFile(updated_zip, 'w') as update_zip:
                for ext in required_exts:
                    path = os.path.join(temp_dir, base_name + ext)
                    update_zip.write(path, arcname=os.path.basename(path))

            return standard_zip, updated_zip, None

    except Exception as e:
        return None, None, f"Unexpected error: {e}"

# --- FRONTEND DISPLAY ---
if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        st.success("ZIP file uploaded. Processing...")

        standard_zip, updated_zip, error = convert_zip(uploaded_file, gpa)

        if error:
            st.error(error)
        else:
            col1, col2 = st.columns(2)
            with col1:
                with open(standard_zip, "rb") as f:
                    st.download_button(
                        label="Download Original ZIP",
                        data=f.read(),
                        file_name="Original_DJI.zip",
                        mime="application/zip"
                    )
            with col2:
                with open(updated_zip, "rb") as f:
                    st.download_button(
                        label="Download Updated ZIP",
                        data=f.read(),
                        file_name="Updated_DJI.zip",
                        mime="application/zip"
                    )
    else:
        st.warning("JSON file support coming soon. Please upload a .zip from Solvi.")
