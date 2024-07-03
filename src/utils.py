from typing import List, Dict
import glob
import string
import os
import json
import shutil
import time


def is_valid_project_name(project_name: str) -> bool:
    """Check if the given project name is valid."""
    project_name = project_name.strip()
    allowed_chars = set(string.ascii_letters + string.digits + "_- ")
    return all(char in allowed_chars for char in project_name)


def copy_shapefile(shp_type: str, src_path: str, project_folder: str) -> str:
    if shp_type not in ["network", "damage"]:
        raise ValueError("Invalid shapefile type")

    src_file_name = os.path.basename(src_path)
    shape_file_bare_name, _ = os.path.splitext(src_file_name)

    dst_file_dir = os.path.join(project_folder, shp_type)
    os.makedirs(dst_file_dir, exist_ok=True)

    shapefile_files = glob.glob(
        os.path.join(os.path.dirname(src_path), shape_file_bare_name + ".*")
    )

    for file in shapefile_files:
        shutil.copy(file, dst_file_dir)

    return os.path.join(dst_file_dir, src_file_name)


def shapefile_bare_name(src_path: str) -> str:
    return os.popen(f"ls {src_path}").readlines()[0].split("\n")[0].split(".")[0]


def updates_scenarios_config_file(scenario_folder: str, name: str, description: str) -> None:
    # Open a json file called .prt.conf or create one if it doesn't exist and save the project folder path and update timestamp
    # This file should already contain the info of other previous projects if they exist so we need to read the file first
    config_file = os.path.join(os.path.expanduser("~"), ".prt.conf")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            data = json.load(f)
    else:
        data = []
        
    # Check if the project folder is already in the list
    project_exists = False
    for project in data:
        if project["project_folder"] == scenario_folder:
            project_exists = True
            break
            
    if not project_exists:
        data.append({
            "project_folder": scenario_folder,
            "name": name,
            "description": description,
            "timestamp": time.time()
        })
    else:
        for project in data:
            if project["project_folder"] == scenario_folder:
                project["timestamp"] = time.time()
                break

    with open(config_file, "w") as f:
        json.dump(data, f)


def read_scenarios_config_file() -> List[Dict]:
    # Open a json file called .prt.conf or create one if it doesn't exist and save the project folder path and update timestamp
    # This file should already contain the info of other previous projects if they exist so we need to read the file first
    config_file = os.path.join(os.path.expanduser("~"), ".prt.conf")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            data = json.load(f)
    else:
        data = []
        
    return data


def generate_distinct_colors(start: int, end: int) -> Dict[str, str]:
    """
    Generates a dictionary with keys from `start` to `end` and values as distinct hex color codes.
    
    :param start: The starting integer value.
    :param end: The ending integer value.
    :return: A dictionary with integers as keys and hex color codes as values.
    """
    # Predefined list of distinct colors
    distinct_colors = [
        "#0000FF",  # Blue
        "#00FFFF",  # Cyan
        "#00FF00",  # Lime
        "#FFFF00",  # Yellow
        "#FFA500",  # Orange
        "#FF0000",  # Red
        "#FF00FF",  # Magenta
        "#800080",  # Purple
        "#008000",  # Green
        "#800000",  # Maroon
        "#808000",  # Olive
        "#000080",  # Navy
        "#008080",  # Teal
        "#808080",  # Gray
        "#C0C0C0",  # Silver
    ]
    
    num_colors = len(distinct_colors)
    num_steps = end - start + 1
    
    if num_steps > num_colors:
        raise ValueError(f"The range [{start}, {end}] requires more than {num_colors} distinct colors.")
    
    gradient_dict = {}
    
    for i in range(start, end + 1):
        color_index = (i - start) % num_colors
        gradient_dict[str(i)] = distinct_colors[color_index]
    
    return gradient_dict