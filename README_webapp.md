# MA GIS USE_CODE Analyzer - Web Application

A web-based tool for analyzing property USE_CODE mismatches in Massachusetts GIS data using geospatial analysis.

## Features

🗺️ **Interactive Map**: Centered on Massachusetts with property markers
📁 **Drag & Drop Upload**: Simply drop your .gdb.zip files
🔍 **Spatial Analysis**: Analyzes nearby properties to suggest USE_CODE corrections
📊 **Real-time Stats**: Shows analysis progress and results
📋 **Property List**: Browse properties with confidence scores
💾 **CSV Export**: Download complete analysis results
🎯 **Confidence Scoring**: Color-coded markers based on suggestion confidence

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Ensure Required Files
Make sure you have:
- `property_classification_codes.csv` - Reference file with valid USE_CODEs
- `app.py` - Flask backend server
- `index.html` - Frontend interface

### 3. Run the Application
```bash
python app.py
```

The server will start at: http://localhost:5000

## How to Use

### 1. Upload GDB File
- Drag and drop a `.gdb.zip` file onto the upload area
- Or click to select a file from your computer
- The system supports both M035 and M049 format GDB files

### 2. View Analysis Results
- **Statistics Panel**: Shows total properties, non-matching codes, and analysis progress
- **Property List**: Browse properties with USE_CODE suggestions
- **Interactive Map**: Click on colored markers to see property details

### 3. Interpret Results
- 🟢 **Green markers**: High confidence suggestions (>70%)
- 🟡 **Yellow markers**: Medium confidence suggestions (50-70%)
- 🔴 **Red markers**: Low confidence suggestions (<50%)

### 4. Download Results
- Click "📊 Download Results" to get a CSV file
- Contains all analyzed properties with suggestions and coordinates

## Analysis Process

1. **Extract GDB**: Unzips and locates the GDB database
2. **Load Data**: Reads assessment and parcel geometry layers
3. **Find Mismatches**: Compares USE_CODEs against reference file
4. **Spatial Analysis**: For each non-matching property:
   - Creates 100-meter buffer around property
   - Analyzes nearby properties' USE_CODEs
   - Suggests most common valid code in vicinity
   - Calculates confidence based on nearby consensus

## File Structure

```
MA_GIS_data_clean/
├── app.py                              # Flask backend
├── index.html                          # Web interface
├── requirements.txt                    # Python dependencies
├── property_classification_codes.csv   # Reference codes
├── uploads/                           # Temporary upload storage
└── results/                           # Analysis results storage
```

## API Endpoints

### POST `/upload`
Uploads and analyzes a GDB zip file
- **Input**: Multipart form with 'file' field
- **Output**: JSON with analysis results

### GET `/download/<filename>`
Downloads analysis results as CSV
- **Input**: Results filename
- **Output**: CSV file download

## Sample Output

The CSV export includes:
- Property address
- Current USE_CODE
- Suggested USE_CODE
- Confidence score (0-1)
- Code description
- Number of nearby properties analyzed
- Latitude/Longitude coordinates

## Troubleshooting

### Common Issues

1. **"No .gdb file found"**: Ensure your zip contains a `.gdb` folder
2. **"No assessment layer found"**: GDB must have assessment data layer
3. **"Error loading classification codes"**: Check that `property_classification_codes.csv` exists

### Performance Notes

- Analysis is limited to 100 sample properties for performance
- Large GDB files may take 2-5 minutes to process
- Results are cached for download

## Browser Compatibility

- ✅ Chrome/Chromium 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Security Notes

- Files are temporarily stored and deleted after processing
- No data is permanently retained on the server
- CORS is enabled for development (disable in production)

## Development

To modify the analysis:
1. Edit `analyze_gdb()` function in `app.py`
2. Update frontend in `index.html`
3. Restart Flask server to apply changes

The application combines powerful GIS analysis with an intuitive web interface for efficient property USE_CODE validation and correction.