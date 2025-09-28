import geopandas as gpd
import pandas as pd
import os

def shapefile_to_excel(shapefile_path, output_path=None):
    """
    Convert shapefile to Excel format

    Args:
        shapefile_path: Path to the .shp file
        output_path: Output Excel file path (optional)
    """
    # Read shapefile
    gdf = gpd.read_file(shapefile_path)

    # Generate output filename if not provided
    if output_path is None:
        base_name = os.path.splitext(shapefile_path)[0]
        output_path = f"{base_name}.xlsx"

    # Drop geometry column for Excel export (keep only attributes)
    df = gdf.drop(columns=['geometry'])

    # Save to Excel
    df.to_excel(output_path, index=False)
    print(f"Converted {shapefile_path} to {output_path}")
    print(f"Columns: {list(df.columns)}")
    print(f"Records: {len(df)}")
    return output_path

def convert_all_shapefiles():
    """Convert all Boston shapefiles to Excel"""
    shapefile_dir = "./L3_SHP_M035_Boston/"

    # Find all .shp files
    shp_files = [f for f in os.listdir(shapefile_dir) if f.endswith('.shp')]

    for shp_file in shp_files:
        shapefile_path = os.path.join(shapefile_dir, shp_file)
        print(f"\nProcessing: {shp_file}")
        try:
            shapefile_to_excel(shapefile_path)
        except Exception as e:
            print(f"Error processing {shp_file}: {e}")

if __name__ == "__main__":
    # Convert all shapefiles
    convert_all_shapefiles()

    # Also check the assessment data which likely contains landuse info
    assessment_file = "./L3_SHP_M035_Boston/M035Assess_CY22_FY23.dbf"
    if os.path.exists(assessment_file):
        print("\nConverting assessment data (contains landuse attributes):")
        try:
            from dbfread import DBF
            table = DBF(assessment_file, encoding='latin1')
            df = pd.DataFrame(iter(table))
        except ImportError:
            # Fallback: try using geopandas to read the DBF
            import geopandas as gpd
            df = gpd.read_file(assessment_file)
            if 'geometry' in df.columns:
                df = df.drop(columns=['geometry'])

        df.to_excel("./L3_SHP_M035_Boston/M035Assess_CY22_FY23.xlsx", index=False)
        print(f"Assessment data converted. Records: {len(df)}")

        # Show landuse-related columns
        landuse_cols = [col for col in df.columns if any(keyword in col.lower()
                       for keyword in ['use', 'land', 'zone', 'class', 'type', 'desc'])]
        if landuse_cols:
            print(f"Landuse-related columns found: {landuse_cols}")
        else:
            print("All available columns:", list(df.columns)[:20])  # Show first 20 columns