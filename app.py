#!/usr/bin/env python3
"""
Flask backend for MA GIS USE_CODE Analyzer
Handles GDB zip file processing and geospatial analysis
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import tempfile
import zipfile
import geopandas as gpd
import pandas as pd
import numpy as np
from collections import Counter
import json
import traceback

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Global progress tracking
processing_progress = {
    'current': 0,
    'total': 0,
    'status': 'idle',
    'message': ''
}

def load_classification_codes():
    """Load property classification codes"""
    try:
        codes_df = pd.read_csv('property_classification_codes.csv')
        # Handle different possible column names
        if 'use_code' in codes_df.columns:
            code_col, desc_col = 'use_code', 'Description'
        elif 'Code' in codes_df.columns:
            code_col, desc_col = 'Code', 'Description'
        else:
            code_col, desc_col = codes_df.columns[0], codes_df.columns[1]

        codes_dict = dict(zip(codes_df[code_col].astype(str), codes_df[desc_col]))
        print(f"Loaded {len(codes_dict)} valid classification codes")
        return codes_dict
    except Exception as e:
        print(f"Error loading classification codes: {e}")
        return {}

def extract_and_analyze_gdb(zip_file_path):
    """Extract GDB from zip and perform analysis"""
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Extract zip file
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find GDB file
            gdb_path = None
            for root, dirs, files in os.walk(temp_dir):
                for dir_name in dirs:
                    if dir_name.endswith('.gdb'):
                        gdb_path = os.path.join(root, dir_name)
                        break
                if gdb_path:
                    break

            if not gdb_path:
                raise Exception("No .gdb file found in zip")

            # Analyze the GDB
            return analyze_gdb(gdb_path)

        except Exception as e:
            raise Exception(f"Error processing GDB: {str(e)}")

def analyze_gdb(gdb_path):
    """Analyze GDB for USE_CODE mismatches and spatial suggestions"""
    try:
        # Load classification codes
        codes_dict = load_classification_codes()
        valid_codes = set(codes_dict.keys())

        # List layers
        layers_df = gpd.list_layers(gdb_path)
        print(f"Available layers: {layers_df['name'].tolist()}")

        # Find assessment and parcel layers
        assessment_layer = None
        parcel_layer = None

        for layer_name in layers_df['name']:
            if 'assess' in layer_name.lower():
                assessment_layer = layer_name
            if 'taxpar' in layer_name.lower() or 'parcel' in layer_name.lower():
                parcel_layer = layer_name

        if not assessment_layer:
            raise Exception("No assessment layer found")
        if not parcel_layer:
            raise Exception("No parcel layer found")

        print(f"Using assessment layer: {assessment_layer}")
        print(f"Using parcel layer: {parcel_layer}")

        # Load data
        assessment_df = gpd.read_file(gdb_path, layer=assessment_layer)
        parcels_gdf = gpd.read_file(gdb_path, layer=parcel_layer)

        if 'geometry' in assessment_df.columns:
            assessment_df = assessment_df.drop(columns=['geometry'])

        print(f"Loaded {len(assessment_df)} assessment records")
        print(f"Loaded {len(parcels_gdf)} parcel geometries")

        # Analyze USE_CODE matches - truncate to first 3 digits
        assessment_df['USE_CODE'] = assessment_df['USE_CODE'].astype(str).str[:3]
        total_properties = len(assessment_df)

        matching_mask = assessment_df['USE_CODE'].isin(valid_codes)
        non_matching_df = assessment_df[~matching_mask]
        non_matching_count = len(non_matching_df)

        print(f"Non-matching properties: {non_matching_count}")

        # Create spatial analysis for ALL non-matching properties
        if non_matching_count > 0:
            print(f"Processing ALL {non_matching_count} non-matching properties...")
            sample_properties = perform_spatial_analysis(
                parcels_gdf, assessment_df, non_matching_df, codes_dict, valid_codes
            )
        else:
            sample_properties = []

        # Calculate statistics
        high_confidence_count = sum(1 for p in sample_properties if p.get('confidence', 0) > 0.7)

        return {
            'success': True,
            'total_properties': total_properties,
            'non_matching_count': non_matching_count,
            'analyzed_count': len(sample_properties),
            'high_confidence_count': high_confidence_count,
            'properties': sample_properties,
            'match_percentage': ((total_properties - non_matching_count) / total_properties) * 100,
            'assessment_data': assessment_df
        }

    except Exception as e:
        print(f"Error in analyze_gdb: {str(e)}")
        traceback.print_exc()
        raise

def perform_spatial_analysis(parcels_gdf, assessment_df, non_matching_sample, codes_dict, valid_codes):
    """Perform spatial analysis on non-matching properties"""
    try:
        # Merge geometry with assessment data
        parcels_gdf['LOC_ID'] = parcels_gdf['LOC_ID'].astype(str)
        assessment_df['LOC_ID'] = assessment_df['LOC_ID'].astype(str)

        # Create complete spatial dataset
        all_parcels_gdf = parcels_gdf.merge(assessment_df, on='LOC_ID', how='inner')

        # Ensure USE_CODE is truncated to 3 digits in the spatial dataset
        all_parcels_gdf['USE_CODE'] = all_parcels_gdf['USE_CODE'].astype(str).str[:3]

        # Debug coordinate system
        print(f"Parcels CRS: {parcels_gdf.crs}")
        print(f"Sample coordinates: {parcels_gdf.geometry.iloc[0].centroid if len(parcels_gdf) > 0 else 'None'}")

        # Create spatial index for faster queries
        print("Creating spatial index for faster analysis...")
        all_parcels_gdf.sindex

        # Process sample properties
        results = []
        total_to_process = len(non_matching_sample)

        # Update global progress
        processing_progress['total'] = total_to_process
        processing_progress['status'] = 'processing'

        for count, (idx, property_row) in enumerate(non_matching_sample.iterrows(), 1):
            # Update progress
            processing_progress['current'] = count
            processing_progress['message'] = f"Analyzing property {count} of {total_to_process}"

            # Report progress less frequently for large datasets
            progress_interval = max(25, total_to_process // 100)  # Report at least every 1% or 25 properties
            if count % progress_interval == 0 or count == 1:
                percentage = (count / total_to_process) * 100
                print(f"Progress: {count}/{total_to_process} properties ({percentage:.1f}%)")
            try:
                # Find geometry for this property
                property_geom = all_parcels_gdf[all_parcels_gdf['LOC_ID'] == str(property_row['LOC_ID'])]

                if len(property_geom) == 0:
                    continue

                property_geom = property_geom.iloc[0]

                # Get centroid coordinates and transform to WGS84
                if hasattr(property_geom.geometry, 'centroid'):
                    centroid = property_geom.geometry.centroid

                    # Check if coordinates need transformation (likely in projected system)
                    x, y = centroid.x, centroid.y

                    # If coordinates are very large, they're likely in a projected system
                    if abs(x) > 1000 or abs(y) > 1000:
                        try:
                            # Transform from projected to geographic coordinates
                            # Get the CRS of the GeoDataFrame
                            if all_parcels_gdf.crs:
                                # Create a temporary GeoDataFrame with just the centroid
                                import geopandas as gpd
                                from shapely.geometry import Point

                                temp_gdf = gpd.GeoDataFrame([1], geometry=[Point(x, y)], crs=all_parcels_gdf.crs)
                                # Transform to WGS84 (EPSG:4326)
                                temp_gdf_wgs84 = temp_gdf.to_crs('EPSG:4326')
                                transformed_point = temp_gdf_wgs84.geometry.iloc[0]

                                lng, lat = transformed_point.x, transformed_point.y
                            else:
                                print(f"Warning: No CRS info for transformation: {property_row.get('SITE_ADDR', 'Unknown')}")
                                continue
                        except Exception as e:
                            print(f"Error transforming coordinates for {property_row.get('SITE_ADDR', 'Unknown')}: {e}")
                            continue
                    else:
                        # Coordinates might already be in geographic system
                        lat, lng = y, x

                    # Validate Massachusetts coordinates after transformation
                    if not (41.0 <= lat <= 43.0 and -74.0 <= lng <= -69.0):
                        print(f"Warning: Invalid coordinates after transformation for {property_row.get('SITE_ADDR', 'Unknown')}: lat={lat}, lng={lng}")
                        continue
                else:
                    # Skip if no valid geometry
                    continue

                # Analyze nearby properties
                buffer_geom = property_geom.geometry.buffer(100)  # 100 meter buffer
                nearby_mask = all_parcels_gdf.intersects(buffer_geom)
                nearby_parcels = all_parcels_gdf[nearby_mask]

                # Exclude the target property itself
                nearby_parcels = nearby_parcels[nearby_parcels['LOC_ID'] != str(property_row['LOC_ID'])]

                if len(nearby_parcels) == 0:
                    continue

                # Analyze USE_CODE distribution - only consider valid codes from reference
                nearby_valid_codes = nearby_parcels[nearby_parcels['USE_CODE'].isin(valid_codes)]

                if len(nearby_valid_codes) == 0:
                    # No valid codes in nearby properties, skip this property
                    continue

                use_code_counts = Counter(nearby_valid_codes['USE_CODE'])
                most_common = use_code_counts.most_common(1)

                if most_common:
                    suggested_code = most_common[0][0]
                    confidence = most_common[0][1] / len(nearby_valid_codes)  # Use valid codes count
                    description = codes_dict.get(suggested_code, 'Unknown')

                    # Ensure suggested code is in valid codes
                    if suggested_code not in valid_codes:
                        continue

                    results.append({
                        'id': f"prop_{len(results)}",
                        'prop_id': str(property_row.get('PROP_ID', '')),
                        'loc_id': str(property_row.get('LOC_ID', '')),
                        'address': str(property_row.get('SITE_ADDR', 'Unknown Address')),
                        'current_code': str(property_row['USE_CODE']),
                        'suggested_code': suggested_code,
                        'confidence': confidence,
                        'description': description,
                        'lat': lat,
                        'lng': lng,
                        'nearby_count': len(nearby_parcels)
                    })

            except Exception as e:
                print(f"Error processing property {idx}: {str(e)}")
                continue

        # Mark processing as complete
        processing_progress['status'] = 'complete'
        processing_progress['message'] = f"Analysis complete! Found {len(results)} properties with spatial suggestions."
        print(f"Spatial analysis complete: {len(results)} properties with valid suggestions")

        return results

    except Exception as e:
        print(f"Error in spatial analysis: {str(e)}")
        return []

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/progress')
def get_progress():
    """Get current processing progress"""
    return jsonify(processing_progress)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and analysis"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})

        if not file.filename.lower().endswith('.zip'):
            return jsonify({'success': False, 'error': 'Please upload a .zip file'})

        # Save uploaded file
        filename = f"upload_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.zip"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # Analyze the GDB
        results = extract_and_analyze_gdb(file_path)

        # Save raw data CSV first (before saving JSON results)
        raw_csv_filename = f"raw_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        raw_csv_path = os.path.join(RESULTS_FOLDER, raw_csv_filename)

        # Create cleaned dataset with replaced USE_CODEs
        cleaned_csv_filename = f"cleaned_usecodes_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        cleaned_csv_path = os.path.join(RESULTS_FOLDER, cleaned_csv_filename)

        if 'assessment_data' in results:
            # Save original raw data
            results['assessment_data'].to_csv(raw_csv_path, index=False)

            # Create cleaned version with replaced USE_CODEs
            cleaned_df = results['assessment_data'].copy()

            # Create a mapping of PROP_ID to suggested USE_CODE
            suggestions_map = {}
            for prop in results['properties']:
                if 'prop_id' in prop and 'suggested_code' in prop:
                    suggestions_map[prop['prop_id']] = prop['suggested_code']

            print(f"Replacing USE_CODEs for {len(suggestions_map)} properties with suggestions")

            # Replace USE_CODEs where we have suggestions
            for prop_id, suggested_code in suggestions_map.items():
                mask = cleaned_df['PROP_ID'].astype(str) == str(prop_id)
                if mask.any():
                    cleaned_df.loc[mask, 'USE_CODE'] = suggested_code

            # Save cleaned dataset
            cleaned_df.to_csv(cleaned_csv_path, index=False)

            # Remove assessment_data from results before JSON operations
            del results['assessment_data']

        # Add file info
        results['raw_data_file'] = raw_csv_filename
        results['cleaned_data_file'] = cleaned_csv_filename

        # Save results (now without DataFrame)
        results_filename = f"results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json"
        results_path = os.path.join(RESULTS_FOLDER, results_filename)

        with open(results_path, 'w') as f:
            json.dump(results, f)

        # Clean up uploaded file
        os.remove(file_path)

        # Add results file info
        results['results_file'] = results_filename

        return jsonify(results)

    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error processing file: {str(e)}'
        })

@app.route('/download/<filename>')
def download_results(filename):
    """Download analysis results as CSV"""
    try:
        # Load results
        results_path = os.path.join(RESULTS_FOLDER, filename)

        if not os.path.exists(results_path):
            return jsonify({'error': 'Results file not found'}), 404

        with open(results_path, 'r') as f:
            results = json.load(f)

        # Generate CSV with format matching your geospatial analysis results
        csv_content = 'PROP_ID,LOC_ID,SITE_ADDR,current_use_code,nearby_count,suggestion_1_code,suggestion_1_confidence,suggestion_1_reason,suggestion_1_description\n'

        for prop in results.get('properties', []):
            reason = f"{int(prop['confidence'] * prop['nearby_count'])}/{prop['nearby_count']} nearby properties ({prop['confidence']:.1%}); Code: {prop['description']}"
            csv_content += f'"{prop.get("prop_id", prop["id"])}","{prop.get("loc_id", "")}","{prop["address"]}",{prop["current_code"]},{prop["nearby_count"]},{prop["suggested_code"]},{prop["confidence"]:.3f},"{reason}","{prop["description"]}"\n'

        # Create CSV file
        csv_filename = filename.replace('.json', '.csv')
        csv_path = os.path.join(RESULTS_FOLDER, csv_filename)

        with open(csv_path, 'w') as f:
            f.write(csv_content)

        return send_from_directory(RESULTS_FOLDER, csv_filename, as_attachment=True)

    except Exception as e:
        return jsonify({'error': f'Error generating CSV: {str(e)}'}), 500

@app.route('/download-raw/<filename>')
def download_raw_data(filename):
    """Download raw GDB data as CSV"""
    try:
        # Check if file exists
        file_path = os.path.join(RESULTS_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'Raw data file not found'}), 404

        return send_from_directory(RESULTS_FOLDER, filename, as_attachment=True)

    except Exception as e:
        return jsonify({'error': f'Error downloading raw data: {str(e)}'}), 500

@app.route('/download-cleaned/<filename>')
def download_cleaned_data(filename):
    """Download cleaned data with replaced USE_CODEs as CSV"""
    try:
        # Check if file exists
        file_path = os.path.join(RESULTS_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'Cleaned data file not found'}), 404

        return send_from_directory(RESULTS_FOLDER, filename, as_attachment=True)

    except Exception as e:
        return jsonify({'error': f'Error downloading cleaned data: {str(e)}'}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'

    print("Starting MA GIS USE_CODE Analyzer server...")
    if debug:
        print(f"Open your browser to http://localhost:{port}")

    app.run(debug=debug, host='0.0.0.0', port=port)