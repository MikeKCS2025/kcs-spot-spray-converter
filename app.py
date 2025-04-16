import streamlit as st
import zipfile
import tempfile
import os
import shapefile  # pyshp
import pandas as pd

st.set_page_config(page_title="Solvi to DJI Converter", layout="centered")
st.title("Solvi to DJI Converter")
st.caption("Upload your Solvi `.zip` and download DJI-ready shapefiles and spray volume data.")

uploaded_file = st.file_uploader("Drop your Solvi ZIP here", type=["zip"])
spray_rate = st.number_input("Spray Rate (GPA)", min_value=0.1, value=2.0, step=0.1)

def process_zip(uploaded_file, spray_rate):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "input.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Detect base name
            base_name = next((f.split(".")[0] for f in os.listdir(temp_dir) if f.endswith(".shp")), None)
            if not base_name:
                return None, None, "No .shp file found."

            # Confirm all required extensions are present
            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            for ext in required_exts:
                file_path = os.path.join(temp_dir, base_name + ext)
                if not os.path.exists(file_path):
                    return None, None, f"Missing required file: {base_name + ext}"

            # Read shapefile
            reader = shapefile.Reader(os.path.join(temp_dir, base_name + ".shp"))
            fields = [f[0] for f in reader.fields[1:]]
            records = reader.records()
            shapes = reader.shapes()

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

            # Build CSV
            df = pd.DataFrame(records, columns=fields)
            df["Acres"] = acres_list
            df["Volume (Gal)"] = volumes
            csv_path = os.path.join(temp_dir, "spray_volumes.csv")
            df.to_csv(csv_path, index=False)

            # Repack original files into a ZIP
            output_zip_path = os.path.join(temp_dir, "DJI_ready.zip")
            with zipfile.ZipFile(output_zip_path, 'w') as z:
                for ext in required_exts:
                    fpath = os.path.join(temp_dir, base_name + ext)
                    z.write(fpath, arcname=os.path.basename(fpath))

            with open(output_zip_path, "rb") as zipf, open(csv_path, "rb") as csvf:
                return zipf.read(), csvf.read(), None

    except Exception as e:
        return None, None, str(e)

# --- MAIN LOGIC ---
if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        with st.spinner("Processing your file..."):
            dji_zip, csv_data, error = process_zip(uploaded_file, spray_rate)

        if error:
            st.error(f"❌ {error}")
        else:
            st.success("✅ All done! Files are ready for download.")

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
