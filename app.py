import streamlit as st
import zipfile
import tempfile
import os
import shapefile  # pyshp
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
    min_value=0.01,
    value=1.0,
    step=0.1
)

def process_zip(uploaded_file, spray_rate):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "input.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Identify shapefile base name
            base_name = None
            for file in os.listdir(temp_dir):
                if file.endswith(".shp"):
                    base_name = os.path.splitext(file)[0]
                    break

            if not base_name:
                return None, "No .shp file found in the ZIP."

            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            missing = [ext for ext in required_exts if not os.path.exists(os.path.join(temp_dir, base_name + ext))]
            if missing:
                return None, f"Missing required files: {', '.join(missing)}"

            # Modify attribute table
            shp_path = os.path.join(temp_dir, base_name + ".shp")
            r = shapefile.Reader(shp_path)
            fields = r.fields[1:]  # Skip deletion flag
            field_names = [field[0] for field in fields]
            records = r.records()
            shapes = r.shapes()

            updated_path = os.path.join(temp_dir, "updated.shp")
            w = shapefile.Writer(updated_path)
            for field in fields:
                w.field(*field)
            if "Rate" not in field_names:
                w.field("Rate", "N", decimal=2)

            for rec, shape in zip(records, shapes):
                rec = list(rec)
                if "Rate" not in field_names:
                    rec.append(round(spray_rate, 2))
                w.record(*rec)
                w.shape(shape)

            w.close()

            # Copy original .prj and .shx and .dbf
            for ext in [".prj", ".shx", ".dbf"]:
                shutil.copy(os.path.join(temp_dir, base_name + ext), os.path.join(temp_dir, "updated" + ext))

            # Create output ZIP
            output_zip_path = os.path.join(temp_dir, "DJI_ready.zip")
            with zipfile.ZipFile(output_zip_path, 'w') as zip_out:
                for ext in [".shp", ".shx", ".dbf", ".prj"]:
                    file_path = os.path.join(temp_dir, "updated" + ext)
                    zip_out.write(file_path, arcname="updated" + ext)

            with open(output_zip_path, "rb") as f:
                return f.read(), None

    except Exception as e:
        return None, f"Unexpected error: {e}"

if uploaded_file and uploaded_file.name.endswith(".zip"):
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
elif uploaded_file and uploaded_file.name.endswith(".json"):
    st.warning("JSON file support coming soon. Please upload a `.zip` from Solvi.")
