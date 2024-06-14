from shapely.geometry import box
from src.const import TARGET_CRS
from typing import List, Tuple
import geopandas as gpd


def reproject_shp(gdf: gpd.GeoDataFrame, target_crs: str = TARGET_CRS) -> gpd.GeoDataFrame:
    return gdf.to_crs(target_crs)


def extract_shapefile_data(shapefile_path: str):
    gdf = reproject_shp(gpd.read_file(shapefile_path))
    # Calculate the bounding box
    bounding_box = gdf.total_bounds
    minx, miny, maxx, maxy = bounding_box

    # Create a bounding box polygon
    bbox_polygon = box(minx, miny, maxx, maxy)

    # Calculate the centroid of the bounding box
    bbox_centroid = bbox_polygon.centroid
    
    pipes_lines_paths: List[List[Tuple[float, float]]] = []
    
    # Extract the geometry of the shapefile and for each geometry extract the coordinates of the line and append them to the list
    for geometry in gdf.geometry:
        pipes_lines_paths.append([])
        for point in geometry.coords:
            pipes_lines_paths[-1].append((point[1], point[0]))
    
    attributes = gdf.drop(columns='geometry')

    return bounding_box, bbox_centroid, pipes_lines_paths, attributes