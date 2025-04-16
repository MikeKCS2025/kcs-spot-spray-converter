import streamlit as st
import zipfile
import tempfile
import os
import shapefile  # pyshp
import pandas as pd

st.set_page_config(page_title="Solvi to DJI Converter", layout="centered")
st.title("Solvi to DJI Converter")
st.caption("Upload your Solvi `.zip` and download DJI-ready shapefiles and GPA data.")

uploaded_file = st.file_uploader("📁 Drop your Solvi ZIP here", type=["zip"])
spray_rate = st.number_input("💧 Spray Rate (GPA)", min_value=0.1, value=2.0, step=0.1)

def process_zip(uploaded_file, spray_rate):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "upload.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Detect base name from .shp
            base_name = next((f.split(".")[0] for f in os.listdir(temp_dir) if f.endswith(".shp")), None)
            if not base_name:
                return None, None, "No .shp file found."

            # Confirm all required extensions are present
            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            for ext in required_exts:
                if not os.path.exists(os.path.join(temp_dir, base_name + ext)):
                    return None, None, f"Missing file: {base_name + ext}"

            # Load shapefile
            shp_path = os.path.join(temp_dir, base_name + ".shp")
            reader = shapefile.Reader(shp_path)
            shapes = reader.shapes()
            fields = reader.fields[1:]
            field_names = [f[0] for f in fields]
            records = reader.records()

            # Basic area + GPA calc (fake if needed)
            acres_list, volumes = [], []
            for shape in shapes:
                points = shape.points
                area = 0
                for i in range(len(points)):
                    x1, y1 = points[i - 1]
                    x2, y2 = points[i]
                    area += (x1 * y2 - x2 * y1)
                area = abs(area) / 2.0
                acres = area * 0.000247105
                volume = round(acres * spray_rate, 2)
                acres_list.append(round(acres, 3))
                volumes.append(volume)

            df = pd.DataFrame(records, columns=field_names)
            df["Acres"] = acres_list
            df["Volume (Gal)"] = volumes
            csv_path = os.path.join(temp_dir, "spray_volumes.csv")
            df.to_csv(csv_path, index=False)

            # Repackage original shapefile
            zip_out_path = os.path.join(temp_dir, "DJI_ready.zip")
            with zipfile.ZipFile(zip_out_path, "w") as z:
                for ext in required_exts:
                    fpath = os.path.join(temp_dir, base_name + ext)
                    z.write(fpath, arcname=os.path.basename(fpath))

            with open(zip_out_path, "rb") as f1, open(csv_path, "rb") as f2:
                return f1.read(), f2.read(), None

    except Exception as e:
        return None, None, str(e)

# --- MAIN LOGIC ---
if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        with st.spinner("Processing..."):
            dji_zip, csv_data, error = process_zip(uploaded_file, spray_rate)

        if error:
            st.error(error)
        else:
            st.success("✅ Conversion complete!")

            st.download_button(
                "⬇️ Download DJI Shapefile ZIP",
                data=dji_zip,
                file_name="DJI_ready.zip",
                mime="application/zip"
            )

            st.download_button(
                "⬇️ Download Spray Volume CSV",
                data=csv_data,
                file_name="spray_volumes.csv",
                mime="text/csv"
            )
    else:
        st.warning("Please upload a ZIP. JSON support coming soon.")
