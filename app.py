import streamlit as st
import zipfile
import tempfile
import os
import shapefile  # pyshp
import shutil

st.set_page_config(page_title="Solvi to DJI Converter", layout="centered")

st.title("Solvi to DJI Converter")
st.caption("Upload your Solvi `.zip` and download DJI-ready shapefiles with embedded spray rates.")

uploaded_file = st.file_uploader("Drop your Solvi ZIP file here", type=["zip"])
spray_rate = st.number_input("Spray Rate (GPA)", min_value=0.1, value=2.0, step=0.1)

def convert_zip(uploaded_file, spray_rate):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "upload.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.read())

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find base name
            base_name = next(f.split(".")[0] for f in os.listdir(temp_dir) if f.endswith(".shp"))

            # Validate required files
            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            for ext in required_exts:
                if not os.path.exists(os.path.join(temp_dir, f"{base_name}{ext}")):
                    return None, None, f"Missing {ext} file"

            # Create original ZIP (untouched)
            original_zip_path = os.path.join(temp_dir, "DJI_original.zip")
            with zipfile.ZipFile(original_zip_path, "w") as z:
                for ext in required_exts:
                    path = os.path.join(temp_dir, f"{base_name}{ext}")
                    z.write(path, arcname=f"{base_name}{ext}")

            # Inject GPA into DBF
            reader = shapefile.Reader(os.path.join(temp_dir, f"{base_name}.shp"))
            fields = reader.fields[1:]
            field_names = [f[0] for f in fields]

            writer = shapefile.Writer(os.path.join(temp_dir, "updated"))
            for field in fields:
                writer.field(*field)
            if "GPA" not in field_names:
                writer.field("GPA", "N", 10, 2)

            for rec, shape in zip(reader.records(), reader.shapes()):
                rec_values = list(rec)
                if "GPA" not in field_names:
                    rec_values.append(round(spray_rate, 2))
                writer.record(*rec_values)
                writer.shape(shape)

            writer.close()

            # Copy PRJ over to match updated
            shutil.copyfile(os.path.join(temp_dir, f"{base_name}.prj"), os.path.join(temp_dir, "updated.prj"))

            # Create updated ZIP (with GPA)
            updated_zip_path = os.path.join(temp_dir, "DJI_updated.zip")
            with zipfile.ZipFile(updated_zip_path, "w") as z:
                for ext in [".shp", ".shx", ".dbf", ".prj"]:
                    path = os.path.join(temp_dir, f"updated{ext}")
                    if os.path.exists(path):
                        z.write(path, arcname=f"updated{ext}")

            with open(original_zip_path, "rb") as f1, open(updated_zip_path, "rb") as f2:
                return f1.read(), f2.read(), None

    except Exception as e:
        return None, None, f"Unexpected error: {e}"

# --- Frontend UI ---
if uploaded_file:
    with st.spinner("Processing..."):
        original_zip, updated_zip, error = convert_zip(uploaded_file, spray_rate)

    if error:
        st.error(error)
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "⬇️ Download Original DJI ZIP",
                data=original_zip,
                file_name="DJI_original.zip",
                mime="application/zip"
            )
        with col2:
            st.download_button(
                "⬇️ Download Updated ZIP (with GPA)",
                data=updated_zip,
                file_name="DJI_updated.zip",
                mime="application/zip"
            )
