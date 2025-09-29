# MA GIS USE_CODE Analyzer

A web-based tool for analyzing property USE_CODE mismatches in Massachusetts GIS data using geospatial analysis.

## 🚀 Quick Start

### Local Development
```bash
pip install -r requirements.txt
python app.py
```
Visit: http://localhost:8080

### Deploy to Render
1. Fork this repository
2. Connect to Render: https://render.com
3. Create a new Web Service
4. Connect your GitHub repository
5. Render will automatically detect `render.yaml` and deploy

## 📋 Features

- **Interactive Map**: Centered on Massachusetts with property markers
- **Drag & Drop Upload**: Simply drop your .gdb.zip files
- **Spatial Analysis**: Analyzes nearby properties to suggest USE_CODE corrections
- **Three Export Options**: Analysis results, raw data, and cleaned data
- **Confidence Scoring**: Color-coded markers based on suggestion confidence

## 🛠️ How It Works

1. Upload a `.gdb.zip` file containing Massachusetts property data
2. System extracts and analyzes USE_CODEs against reference classification
3. For non-matching codes, creates 100m buffer around each property
4. Analyzes nearby properties' USE_CODEs to suggest corrections
5. Calculates confidence based on neighborhood consensus
6. Visualizes results on interactive map with downloadable exports

## 📊 Confidence Calculation

```
Confidence = (Count of Most Common USE_CODE) / (Total Nearby Properties with Valid Codes)
```

- 🟢 **High (>70%)**: Strong neighborhood consensus
- 🟡 **Medium (50-70%)**: Moderate agreement
- 🔴 **Low (<50%)**: Mixed patterns

## 📁 File Structure

- `app.py` - Flask backend with GIS analysis
- `index.html` - Web interface with Leaflet map
- `property_classification_codes.csv` - USE_CODE reference data
- `requirements.txt` - Python dependencies
- `render.yaml` - Render deployment configuration

## 🗺️ Data Requirements

Upload `.gdb.zip` files containing:
- Assessment layer with property data
- Parcel geometry layer
- USE_CODE field for analysis

## 🔧 Technical Stack

- **Backend**: Flask + GeoPandas + Shapely
- **Frontend**: Leaflet.js + HTML5
- **Analysis**: Spatial buffers + coordinate transformation
- **Deployment**: Render (production) / Local (development)