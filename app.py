import streamlit as st
import zipfile
import json
import os

def convert_solvi_to_dji(file):
    if file.name.endswith('.zip'):
        with zipfile.ZipFile(file, 'r') as zip_ref:
            zip_ref.extractall("temp_zip")
            for name in zip_ref.namelist():
                if name.endswith(".json"):
                    json_path = os.path.join("temp_zip", name)
                    break
    elif file.name.endswith('.json'):
        json_path = file.name
        with open(json_path, "wb") as f:
            f.write(file.getbuffer())
    else:
        return None, "Unsupported file type"

    with open(json_path, 'r') as f:
        data = json.load(f)

    # Example: Extract GPS points and write to KML (placeholder logic)
    kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>Converted DJI File</name>
'''

    for idx, target in enumerate(data.get("targets", [])):
        lat = target.get("lat", 0)
        lon = target.get("lon", 0)
        kml_content += f'''
  <Placemark>
    <name>Target {idx+1}</name>
    <Point>
      <coordinates>{lon},{lat},0</coordinates>
    </Point>
  </Placemark>'''

    kml_content += '''
</Document>
</kml>'''

    output_filename = "converted.kml"
    with open(output_filename, "w") as f:
        f.write(kml_content)

    return output_filename, None

st.title("Solvi to DJI Converter")

uploaded_file = st.file_uploader("Upload your Solvi .zip or .json file", type=["zip", "json"])

if uploaded_file:
    output_file, error = convert_solvi_to_dji(uploaded_file)
    if error:
        st.error(error)
    else:
        with open(output_file, "rb") as f:
            st.download_button("Download DJI KML File", f, file_name="converted.kml")

