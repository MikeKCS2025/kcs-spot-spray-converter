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

spray_rate = st.number_input("Enter Spray Rate (Gallons per Acre)", min_value=0.1, value=1.0, step=0.1)

def is_valid_shapefile_set(file_list, base_name):
    required_exts = [".shp", ".shx", ".dbf", ".prj"]
    return all(f"{base_name}{ext}" in file_list for ext in required_exts)

def convert_zip_to_dji(zip_bytes, spray_rate):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "input.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_bytes.getvalue())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            file_list = os.listdir(temp_dir)
            base_names = set(os.path.splitext(f)[0] for f in file_list if f.endswith(".shp"))
            if not base_names:
                return None, None, "No .shp file found in the ZIP."

            base_name = list(base_names)[0]
            if not is_valid_shapefile_set(file_list, base_name):
                return None, None, "Missing one or more required shapefile components."

            # Read shapefile
            shp_reader = shapefile.Reader(os.path.join(temp_dir, f"{base_name}.shp"))
            fields = shp_reader.fields[1:]  # skip deletion flag
            field_names = [f[0] for f in fields]

            # Add spray rate to DBF
            temp_output_base = os.path.join(temp_dir, "updated")
            shp_writer = shapefile.Writer(temp_output_base)
            for field in fields:
                shp_writer.field(*field)
            if "GPA" not in field_names:
                shp_writer.field("GPA", "N", decimal=2)

            for rec, shape in zip(shp_reader.records(), shp_reader.shapes()):
                rec_dict = dict(zip(field_names, rec))
                rec_dict["GPA"] = spray_rate
                rec_values = [rec_dict.get(f, "") for f in field_names]
                rec_values.append(spray_rate)
                shp_writer.shape(shape)
                shp_writer.record(*rec_values)
            shp_writer.close()

            # Copy .prj file
            original_prj = os.path.join(temp_dir, f"{base_name}.prj")
            updated_prj = os.path.join(temp_dir, "updated.prj")
            if os.path.exists(original_prj):
                shutil.copy(original_prj, updated_prj)

            # Create two output zips
            out1 = os.path.join(temp_dir, "DJI_original.zip")
            out2 = os.path.join(temp_dir, "DJI_updated.zip")

            with zipfile.ZipFile(out1, 'w') as zip_out:
                for ext in [".shp", ".shx", ".dbf", ".prj"]:
                    file_path = os.path.join(temp_dir, f"{base_name}{ext}")
                    if os.path.exists(file_path):
                        zip_out.write(file_path, arcname=f"{base_name}{ext}")

            with zipfile.ZipFile(out2, 'w') as zip_out:
                for ext in [".shp", ".shx", ".dbf", ".prj"]:
                    file_path = os.path.join(temp_dir, f"updated{ext}")
                    if os.path.exists(file_path):
                        zip_out.write(file_path, arcname=f"updated{ext}")

            with open(out1, "rb") as f1, open(out2, "rb") as f2:
                return f1.read(), f2.read(), None

    except Exception as e:
        return None, None, f"Unexpected error: {e}"

# --- UI Logic ---
if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        output_original, output_updated, error = convert_zip_to_dji(uploaded_file, spray_rate)

        if error:
            st.error(error)
        else:
            st.success("ZIP file uploaded. Processing complete!")

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Download Original DJI ZIP",
                    data=output_original,
                    file_name="DJI_original.zip",
                    mime="application/zip"
                )
            with col2:
                st.download_button(
                    label="Download Updated ZIP (with GPA)",
                    data=output_updated,
                    file_name="DJI_updated.zip",
                    mime="application/zip"
                )
    elif uploaded_file.name.endswith(".json"):
        st.warning("JSON support coming soon. Please upload a Solvi .zip for now.")
