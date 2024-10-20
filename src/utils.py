from typing import List, Dict
import tkinter as tk
import requests
import glob
import string
import os
import json
import shutil
import time


def check_internet_connection(url="http://www.google.com/", timeout=5) -> bool:
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code in [200, 301]:
            return True
        else:
            return False
    except (requests.ConnectionError, requests.Timeout):
        return False


def is_valid_project_name(project_name: str) -> bool:
    """Check if the given project name is valid."""
    project_name = project_name.strip()
    allowed_chars = set(string.ascii_letters + string.digits + "_- ")
    return all(char in allowed_chars for char in project_name)


def copy_shapefile(shp_type: str, src_path: str, project_folder: str) -> str:
    '''
    Copy the shapefile to the project folder and return the new path of the shapefile.
    '''
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


def update_scenarios_config_file(scenario_folder: str, name: str, description: str) -> None:
    '''
    The function opens a json file called .prt.conf or creates one if it doesn't exist and saves the project folder path and updates timestamp
    This file should already contain the info of other previous projects if they exist so we need to read the file first    
    '''
    config_file = os.path.join(os.path.expanduser("~"), ".prt.conf")
    
    data: List[Dict] = []
    
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            data = json.load(f)
    
    project_exists = False   # Check if the project folder is already in the list
    
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
                project["name"] = name
                project["description"] = description
                project["timestamp"] = time.time()
                break

    with open(config_file, "w") as f:
        json.dump(data, f)


def refresh_scenarios_config_file() -> None:
    data = read_scenarios_config_file()
    
    if not data: return
    
    updated_data: List[Dict] = []
    
    for project in data:
        if os.path.exists(os.path.join(project["project_folder"], "metadata.json")):
            updated_data.append(project)

    config_file = os.path.join(os.path.expanduser("~"), ".prt.conf")
    
    with open(config_file, "w") as f:
        json.dump(updated_data, f)


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


def find_option_index(list_to_search: List[Dict], name: str) -> int:
    if not list_to_search or not isinstance(list_to_search, list): return -1
    
    if 'name' not in list_to_search[0]: return -1
    
    for i, option in enumerate(list_to_search):
        if option['name'] == name:
            return i

    return -1

class RedirectOutput:
    def __init__(self, text_widget):
        self.text_widget = text_widget


    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)  # Scroll to the end        
        self.text_widget.update_idletasks()  # Force the GUI to update


    def flush(self):
        pass
