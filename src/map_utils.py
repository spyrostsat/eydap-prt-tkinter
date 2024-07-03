from shapely.geometry import box
from src.const import TARGET_CRS
from typing import List, Tuple
import geopandas as gpd
import os


def reproject_shp(gdf: gpd.GeoDataFrame, target_crs: str = TARGET_CRS) -> gpd.GeoDataFrame:
    return gdf.to_crs(target_crs)


def extract_network_shapefile_data(network_shp_path: str):
    gdf = reproject_shp(gpd.read_file(network_shp_path))
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


def extract_damages_shapefile_data(dmg_shp_path: str):
    gdf = gpd.read_file(dmg_shp_path)
    gdf.set_crs(epsg=2100, inplace=True)
    gdf = reproject_shp(gdf)
    
    # Calculate the bounding box
    bounding_box = gdf.total_bounds
    minx, miny, maxx, maxy = bounding_box

    # Create a bounding box polygon
    bbox_polygon = box(minx, miny, maxx, maxy)

    # Calculate the centroid of the bounding box
    bbox_centroid = bbox_polygon.centroid
    
    damages_points: List[Tuple[float, float]] = []
    
    # Extract the geometry of the shapefile and for each geometry extract the coordinates of the point and append them to the list
    for point in gdf.geometry:
        damages_points.append((point.y, point.x))
    
    attributes = gdf.drop(columns='geometry')

    return bounding_box, bbox_centroid, damages_points, attributes


def extract_optimized_cells_data(base_folder: str):
    # The base_folder has several inner folders, each one containing a shapefile inside. I want to extract the data from all of them
	# First I want to use the os module to get the list of all the inner folders
	inner_folders = [f for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f))]
	data = {}  # I will store the data in a dictionary where the key will be the folder name and the value will be the extracted data
	
	for folder in inner_folders:
		folder_path = os.path.join(base_folder, folder)
		# Find the .shp file inside the folder
		for file in os.listdir(folder_path):
			if file.endswith('.shp'):
				shp_path = os.path.join(folder_path, file)
				break
		
		gdf = gpd.read_file(shp_path)
		gdf.set_crs(epsg=2100, inplace=True)
		gdf = reproject_shp(gdf)

		pipes_lines_paths: List[List[Tuple[float, float]]] = []
		
		# Extract the geometry of the shapefile and for each geometry extract the coordinates of the line and append them to the list
		for geometry in gdf.geometry:
			pipes_lines_paths.append([])
			for point in geometry.coords:
				pipes_lines_paths[-1].append((point[1], point[0]))
		
		attributes = gdf.drop(columns='geometry')

		data[folder] = {'pipes_lines_paths': pipes_lines_paths, 'attributes': attributes}
	
	return data
