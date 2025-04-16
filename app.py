import streamlit as st
import zipfile
import tempfile
import os
import shapefile  # pyshp
import pandas as pd

st.set_page_config(page_title="Solvi to DJI Converter", layout="centered")
st.title("Solvi to DJI Converter")
st.caption("Upload your Solvi `.zip` or `.json` file and download DJI-compatible shapefiles.")

uploaded_file = st.file_uploader("Drag and drop file here", type=["zip", "json"], help="Limit 200MB per file • ZIP, JSON")

# Spray rate input
spray_rate = st.number_input("Enter Spray Rate (Gallons per Acre)", min_value=0.1, step=0.1, value=1.0)

def process_zip(uploaded_file, spray_rate):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded zip to disk
            zip_path = os.path.join(temp_dir, "upload.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            # Extract files
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find .shp file
            shp_path = None
            for file in os.listdir(temp_dir):
                if file.endswith(".shp"):
                    shp_path = os.path.join(temp_dir, file)
                    base_name = os.path.splitext(file)[0]
                    break

            if not shp_path:
                return None, None, "No .shp file found in archive."

            # Required files check
            required_exts = [".shp", ".shx", ".dbf", ".prj"]
            for ext in required_exts:
                if not os.path.exists(os.path.join(temp_dir, base_name + ext)):
                    return None, None, f"Missing required file: {base_name + ext}"

            # Read shapefile
            sf = shapefile.Reader(shp_path)
            shapes = sf.shapes()
            fields = [f[0] for f in sf.fields[1:]]  # skip DeletionFlag
            records = sf.records()

            # Estimate area per shape (rough) and calculate volume
            acres_list = []
            volumes = []
            for shape in shapes:
                points = shape.points
                area = 0
                for i in range(len(points)):
                    x1, y1 = points[i - 1]
                    x2, y2 = points[i]
                    area += (x1 * y2 - x2 * y1)
                area = abs(area) / 2.0  # m²
                acres = area * 0.000247105  # m² to acres
                volume = round(acres * spray_rate, 2)
                acres_list.append(round(acres, 3))
                volumes.append(volume)

            # Build CSV
            df = pd.DataFrame(records, columns=fields)
            df["Acres"] = acres_list
            df["Volume (Gal)"] = volumes
            csv_path = os.path.join(temp_dir, "spray_volumes.csv")
            df.to_csv(csv_path, index=False)

            # Repackage shapefile for DJI
            output_zip_path = os.path.join(temp_dir, "DJI_ready.zip")
            with zipfile.ZipFile(output_zip_path, 'w') as zip_out:
                for ext in required_exts:
                    path = os.path.join(temp_dir, base_name + ext)
                    zip_out.write(path, arcname=os.path.basename(path))

            with open(output_zip_path, "rb") as f:
                zip_bytes = f.read()
            with open(csv_path, "rb") as f:
                csv_bytes = f.read()

            return zip_bytes, csv_bytes, None
    except Exception as e:
        return None, None, str(e)

# --- HANDLE FILE UPLOAD ---
if uploaded_file:
    if uploaded_file.name.endswith(".zip"):
        zip_data, csv_data, error = process_zip(uploaded_file, spray_rate)

        if error:
            st.error(f"Unexpected error: {error}")
        else:
            st.success("ZIP file uploaded. Processing complete!")

            st.download_button(
                label="📦 Download DJI Shapefile ZIP",
                data=zip_data,
                file_name="DJI_ready.zip",
                mime="application/zip"
            )

            st.download_button(
                label="📄 Download Spray Volume CSV",
                data=csv_data,
                file_name="spray_volumes.csv",
                mime="text/csv"
            )

    elif uploaded_file.name.endswith(".json"):
        st.warning("JSON file support coming soon. Please upload a `.zip` from Solvi.")
