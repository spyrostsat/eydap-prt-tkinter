import glob
import string
import os
import shutil


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
