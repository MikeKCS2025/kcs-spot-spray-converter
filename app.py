import streamlit as st
import zipfile
import tempfile
import os
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
    "Enter Spray Rate (Gallons per Acre)",
    min_value=0.1,
    max_value=5.0,
    value=1.0,
    step=0.1
)

def process_zip(file, gpa):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "upload.zip")
            with open(zip_path, "wb") as f:
                f.write(file.getvalue())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)

            shp_file = None
            for fname in os.listdir(tmpdir):
                if fname.endswith(".shp"):
                    shp_file = os.path.join(tmpdir, fname)
                    base_name = os.path.splitext(fname)[0]
                    break

            if not shp_file:
                return None, "No .shp file found in archive."

            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            for ext in required_exts:
                full_path = os.path.join(tmpdir, base_name + ext)
                if not os.path.exists(full_path):
                    return None, f"Missing required file: {base_name + ext}"

            # Read original shapefile and write updated one
            r = shapefile.Reader(shp_file)
            fields = r.fields[1:]  # skip deletion flag
            field_names = [field[0] for field in fields]
            records = r.records()
            shapes = r.shapes()

            output_base = os.path.join(tmpdir, "updated")
            w = shapefile.Writer(output_base)
            w.fields = r.fields[1:]

            for rec in records:
                w.record(*rec)
            for shape in shapes:
                w.shape(shape)

            w.close()

            # Copy PRJ
            prj_src = os.path.join(tmpdir, base_name + ".prj")
            prj_dst = output_base + ".prj"
            if os.path.exists(prj_src):
                with open(prj_src, "r") as src, open(prj_dst, "w") as dst:
                    dst.write(src.read())
            else:
                return None, f"Projection file (.prj) not found: {prj_src}"

            # Zip output
            output_zip = os.path.join(tmpdir, "DJI_ready.zip")
            with zipfile.ZipFile(output_zip, "w") as zip_out:
                for ext in required_exts:
                    fpath = output_base + ext
                    if os.path.exists(fpath):
                        zip_out.write(fpath, arcname=os.path.basename(fpath))

            with open(output_zip, "rb") as final:
                return final.read(), None

    except Exception as e:
        return None, f"Unexpected error: {e}"

if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        with st.spinner("Processing ZIP file..."):
            output_data, error = process_zip(uploaded_file, spray_rate)
        if error:
            st.error(error)
        else:
            st.success("ZIP file uploaded. Processing complete!")
            st.download_button(
                label="Download DJI Shapefile ZIP",
                data=output_data,
                file_name="DJI_ready.zip",
                mime="application/zip"
            )
    elif uploaded_file.name.endswith(".json"):
        st.warning("JSON support coming soon. Please upload a .zip from Solvi.")
