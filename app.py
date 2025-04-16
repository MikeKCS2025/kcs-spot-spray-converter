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
    min_value=0.1,
    max_value=20.0,
    value=1.0,
    step=0.1
)

output_format = st.selectbox(
    "Choose Output Format",
    ["DJI Shapefiles", "DJI Task File (JSON)"]
)

def process_zip(uploaded_file, spray_rate, output_format):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "input.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            base_names = set()
            for file in os.listdir(temp_dir):
                if file.endswith(".shp"):
                    base = os.path.splitext(file)[0]
                    base_names.add(base)

            if not base_names:
                return None, "No .shp file found in the ZIP."

            base_name = list(base_names)[0]
            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            missing = [ext for ext in required_exts if not os.path.exists(os.path.join(temp_dir, base_name + ext))]
            if missing:
                return None, f"Missing required files: {', '.join(missing)}"

            shp_path = os.path.join(temp_dir, base_name + ".shp")
            r = shapefile.Reader(shp_path)
            fields = r.fields[1:]  # skip deletion flag
            field_names = [field[0] for field in fields]

            w = shapefile.Writer(os.path.join(temp_dir, "updated"))
            w.fields = list(r.fields[1:])

            if "GPA" not in field_names:
                w.field("GPA", "N", decimal=2)

            for sr in r.shapeRecords():
                rec = sr.record.as_dict()
                shape = sr.shape
                if "GPA" not in rec:
                    rec["GPA"] = spray_rate
                new_record = [rec.get(name, "") for name in field_names] + [rec["GPA"]]
                w.shape(shape)
                w.record(*new_record)

            for ext in [".shx", ".dbf", ".prj"]:
                shutil.copyfile(
                    os.path.join(temp_dir, base_name + ext),
                    os.path.join(temp_dir, "updated" + ext)
                )

            output_zip_path = os.path.join(temp_dir, "DJI_ready.zip")
            with zipfile.ZipFile(output_zip_path, 'w') as zip_out:
                for ext in [".shp", ".shx", ".dbf", ".prj"]:
                    filepath = os.path.join(temp_dir, "updated" + ext)
                    zip_out.write(filepath, arcname="updated" + ext)

            with open(output_zip_path, "rb") as f:
                return f.read(), None

    except Exception as e:
        return None, f"Unexpected error: {e}"

# --- HANDLE UPLOAD ---
if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        output_file, error = process_zip(uploaded_file, spray_rate, output_format)

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
        st.warning("JSON support coming soon.")
