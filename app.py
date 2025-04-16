import streamlit as st
import zipfile
import tempfile
import os
import shutil
import shapefile  # pyshp

st.set_page_config(page_title="Solvi to DJI Converter", layout="centered")

st.title("Solvi to DJI Converter")
st.caption("Upload your Solvi `.zip` or `.json` file and download DJI-compatible shapefiles.")

uploaded_file = st.file_uploader(
    "Drag and drop file here",
    type=["zip", "json"],
    help="Limit 200MB per file • ZIP, JSON"
)

spray_rate = st.number_input(
    "Enter Spray Rate (Gallons per Acre)", min_value=0.0, step=0.1, format="%.2f"
)

def process_zip(uploaded_file, gpa_value):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "input.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find base .shp name
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

            # Modify .dbf to add GPA
            dbf_path = os.path.join(temp_dir, base_name + ".dbf")
            reader = shapefile.Reader(dbf_path)
            fields = reader.fields[1:]  # skip DeletionFlag
            field_names = [field[0] for field in fields]
            records = reader.records()
            shapes = reader.shapes()

            writer = shapefile.Writer(os.path.join(temp_dir, "updated"), shapeType=reader.shapeType)
            for field in fields:
                writer.field(*field)
            if "GPA" not in field_names:
                writer.field("GPA", "N", 10, 2)

            for rec, shp in zip(records, shapes):
                rec = list(rec)
                if "GPA" not in field_names:
                    rec.append(gpa_value)
                writer.record(*rec)
                writer.shape(shp)

            writer.close()

            # Rename updated files back to original
            for ext in required_exts:
                shutil.move(os.path.join(temp_dir, "updated" + ext), os.path.join(temp_dir, base_name + ext))

            # Zip it back up
            output_zip_path = os.path.join(temp_dir, "DJI_ready.zip")
            with zipfile.ZipFile(output_zip_path, 'w') as zip_out:
                for ext in required_exts:
                    file_path = os.path.join(temp_dir, base_name + ext)
                    zip_out.write(file_path, arcname=os.path.basename(file_path))

            with open(output_zip_path, "rb") as f:
                return f.read(), None
    except Exception as e:
        return None, f"Unexpected error: {e}"

# --- HANDLE UPLOAD ---
if uploaded_file and uploaded_file.name.endswith(".zip"):
    if spray_rate == 0.0:
        st.warning("Please enter a spray rate (GPA) before proceeding.")
    else:
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
    st.warning("JSON file support coming soon. Please upload a .zip from Solvi.")
