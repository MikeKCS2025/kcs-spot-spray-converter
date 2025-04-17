import streamlit as st
import zipfile
import tempfile
import os
import shapefile  # pyshp

st.set_page_config(page_title="Solvi to DJI Converter", layout="centered")
st.title("Solvi to DJI Converter")
st.caption("Upload your Solvi `.zip` or `.json` file and download DJI-compatible shapefiles.")

uploaded_file = st.file_uploader("Drag and drop file here", type=["zip", "json"], help="Limit 200MB per file • ZIP, JSON")

spray_rate = st.number_input("Enter Spray Rate (Gallons per Acre)", min_value=0.01, step=0.1, value=1.0, format="%.2f")

def convert_zip_to_dji(file, gpa_rate):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "input.zip")
            with open(zip_path, "wb") as f:
                f.write(file.getvalue())

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Identify base name (e.g., detections)
            base_name = None
            for f in os.listdir(temp_dir):
                if f.endswith(".shp"):
                    base_name = f.replace(".shp", "")
                    break
            if not base_name:
                return None, "No .shp file found in archive."

            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            for ext in required_exts:
                if not os.path.exists(os.path.join(temp_dir, base_name + ext)):
                    return None, f"Missing required file: {base_name + ext}"

            # Read shapefile and add GPA field
            reader = shapefile.Reader(os.path.join(temp_dir, base_name))
            fields = reader.fields[1:]  # skip DeletionFlag
            field_names = [field[0] for field in fields]
            records = reader.records()
            shapes = reader.shapes()

            writer = shapefile.Writer(os.path.join(temp_dir, f"{base_name}_GPA"))
            for field in fields:
                writer.field(*field)
            if "GPA" not in field_names:
                writer.field("GPA", "N", decimal=2)

            for rec, shape in zip(records, shapes):
                rec_data = list(rec)
                if "GPA" not in field_names:
                    rec_data.append(float(gpa_rate))
                writer.record(*rec_data)
                writer.shape(shape)

            # Save new set
            output_base = os.path.join(temp_dir, f"{base_name}_GPA")
            writer.close()

            # Copy original PRJ
            prj_src = os.path.join(temp_dir, base_name + ".prj")
            prj_dst = output_base + ".prj"
            with open(prj_src, "r") as f_src, open(prj_dst, "w") as f_dst:
                f_dst.write(f_src.read())

            # Create output zip
            output_zip_path = os.path.join(temp_dir, "DJI_ready.zip")
            with zipfile.ZipFile(output_zip_path, "w") as zip_out:
                for ext in [".shp", ".shx", ".dbf", ".prj"]:
                    zip_out.write(output_base + ext, arcname=os.path.basename(output_base + ext))

            with open(output_zip_path, "rb") as f:
                return f.read(), None

    except Exception as e:
        return None, f"Unexpected error: {e}"

# Handle upload
if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        output_file, error = convert_zip_to_dji(uploaded_file, spray_rate)
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
        st.warning("JSON file support coming soon. Please upload a `.zip` from Solvi.")
