from tkintermapview.canvas_path import CanvasPath
from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog
from PIL import ImageTk, Image
from shapely.geometry import Point
from src.map_utils import *
from copy import deepcopy
import tkinter as tk
import tkintermapview
import time
from src.utils import *
from src.const import MATERIAL_COLORS, LEFT_MENU
import os
from src.tools import *
import ctypes
import platform
import json
import warnings
from typing import List
import geopandas as gpd
import numpy as np
import pandas as pd


class PipeReplacementTool:
    def initial_configurations(self):        
        self.font = "Sans"
        self.font_size = 18
        
        self.box_width = 1
        self.box_height = 1
        
        self.base_padding = 10
        self.base_entry_width = 10
        
        self.bg = "#F0F0F0"
        self.fg = "#000000"
        self.blue_bg = "#1d2b59"
        self.light_blue_bg = "#4d648d"
        self.danger_bg = "#FF0000"
        self.success_bg = "#00FF00"
        self.button_bg = "#FAD5A5"
        self.button_fg = "#006994"
        self.border_color = "#dddddd"
        self.tk_grey = "#d9d9d9"
        self.white = "#ffffff"
        
        # Let's create the root window
        self.root = tk.Tk()
        self.root.title("Pipe Replacement Tool")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_app_closing)
        
        # Let's find the width and height of the screen
        
        # self.screen_width = self.root.winfo_width()
        # self.screen_height = self.root.winfo_height()
        self.screen_width = 1920
        self.screen_height = 1080
        
        screen_multiplier = 1  # we will use this variable to adjust the size of the root window
        
        # Let's adjust the size of the root window
        self.width = int(screen_multiplier * self.screen_width)  # this will be the width of the root window 
        self.height = int(screen_multiplier * self.screen_height)  # this will be the height of the root window
        width_offset = int((self.screen_width - self.width) / 2)  # this will be the offset of the root window in the x axis
        height_offset = int((self.screen_height - self.height) / 2)  # this will be the offset of the root window in the y axis
        
        self.root.geometry(f"{self.width}x{self.height}+{width_offset}+{height_offset}")
        self.root.iconphoto(True, tk.PhotoImage(file="./src/img/icon.png", height=170))

        # Images section
        self.logo_image = tk.PhotoImage(file='./src/img/logo.png')


    def on_app_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.root.destroy()


    def new_scenario(self) -> None:
        def browse(shp_type: str) -> None:
            filename = filedialog.askopenfilename(filetypes=[("Shapefiles", "*.shp")])
            if filename:
                if shp_type == "network":
                    network_entry.delete(0, tk.END)
                    network_entry.insert(tk.END, filename)
                elif shp_type == "damage":
                    damage_entry.delete(0, tk.END)
                    damage_entry.insert(tk.END, filename)
        
        
        def create_scenario():
            folder = filedialog.askdirectory()
            if not folder:
                return
            
            name = name_entry.get().strip()
            description = description_text.get("1.0", tk.END).strip()
            network = network_entry.get().strip()
            damage = damage_entry.get().strip()
            
            if name and description and network and damage and network.endswith(".shp") and damage.endswith(".shp"):
                # Create a folder with the scenario name inside the selected folder
                scenario_folder = os.path.join(folder, name, "")
                os.makedirs(scenario_folder, exist_ok=True)
                
                network_shp = os.path.join(scenario_folder, os.path.basename(network))
                damage_shp = os.path.join(scenario_folder, os.path.basename(damage))
                                    
                if not is_valid_project_name(name):
                    messagebox.showerror("Error", "Invalid project name")
                    return
                
                self.project_folder = scenario_folder
                self.project_name = name
                self.project_description = description
                self.network_shapefile = copy_shapefile("network", network, scenario_folder)
                self.damage_shapefile = copy_shapefile("damage", damage, scenario_folder)

                # Save the scenario information to a json file
                scenario_info = {
                    "project_folder": self.project_folder,
                    "project_name": self.project_name,
                    "project_description": self.project_description,
                    "network_shapefile": self.network_shapefile,
                    "damage_shapefile": self.damage_shapefile
                }
                with open(os.path.join(scenario_folder, "metadata.json"), "w") as f:
                    json.dump(scenario_info, f)
                    
                # Update the scenarios config file
                updates_scenarios_config_file(scenario_folder, name, description)

                window.destroy()
                messagebox.showinfo("Success", "Scenario created successfully")
                self.landing_page_frame.destroy()
                self.main_page()
            else:
                messagebox.showerror("Error", "Please fill in all the fields and make sure the files are shapefiles (.shp)")
                
        window = tk.Toplevel(self.root)
        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)
        
        # Center the window
        window_width = self.screen_width // 3
        window_height = self.screen_height // 2
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")
                
        name_label = tk.Label(window_frame, text="Scenario name")
        name_label.grid(row=0, column=0, padx=5, pady=20)
        name_entry = tk.Entry(window_frame, width=50)
        name_entry.grid(row=0, column=1, padx=5, pady=20, columnspan=2)
        
        description_label = tk.Label(window_frame, text="Scenario description")
        description_label.grid(row=1, column=0, padx=5, pady=20)
        description_text = tk.Text(window_frame, height=5, width=50)
        description_text.grid(row=1, column=1, padx=5, pady=20, columnspan=2)
        
        network_label = tk.Label(window_frame, text="Network shapefile")
        network_label.grid(row=2, column=0, padx=5, pady=20)
        network_entry = tk.Entry(window_frame, width=40)
        network_entry.grid(row=2, column=1, padx=5, pady=20)
        network_button = tk.Button(window_frame, text="Browse", command=lambda: browse("network"))
        network_button.grid(row=2, column=2, padx=5, pady=20)
        
        damage_label = tk.Label(window_frame, text="Damage shapefile")
        damage_label.grid(row=3, column=0, padx=5, pady=20)
        damage_entry = tk.Entry(window_frame, width=40)
        damage_entry.grid(row=3, column=1, padx=5, pady=20)
        damage_button = tk.Button(window_frame, text="Browse", command=lambda: browse("damage"))
        damage_button.grid(row=3, column=2, padx=5, pady=20)
        
        create_button = tk.Button(window_frame, text="Create", width=30, command=create_scenario, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)))
        create_button.grid(row=4, column=0, padx=5, pady=20, columnspan=2)
        cancel_button = tk.Button(window_frame, text="Cancel", command=window.destroy, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)))
        cancel_button.grid(row=4, column=2, padx=5, pady=20)
    
    
    def open_scenario(self, project_folder = None) -> None:
        if not project_folder:
            folder = filedialog.askdirectory()
            if not folder:
                return
        else: 
            folder = project_folder
        
        metadata_file = os.path.join(folder, "metadata.json")
        if not os.path.exists(metadata_file):
            messagebox.showerror("Error", "Invalid scenario folder")
            return
        
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        self.project_folder = metadata["project_folder"]
        self.project_name = metadata["project_name"]
        self.project_description = metadata["project_description"]
        self.network_shapefile = metadata["network_shapefile"]
        self.damage_shapefile = metadata["damage_shapefile"]
        self.topological_analysis_finished = metadata.get("topological_analysis_finished")
        self.betweeness_metric = metadata.get("betweeness_metric")
        self.closeness_metric = metadata.get("closeness_metric")
        self.bridges_metric = metadata.get("bridges_metric")
        self.unique_pipe_materials_names = np.array(metadata.get("unique_pipe_materials_names"))
        self.topological_analysis_result_shapefile = metadata.get("topological_analysis_result_shapefile")
        self.pipe_materials = metadata.get("pipe_materials")
        
        self.edges = gpd.read_file(os.path.join(self.project_folder, metadata["edges"]))
        self.df_metrics = pd.read_csv(os.path.join(self.project_folder, metadata["df_metrics"]))
        
        self.landing_page_frame.destroy()
        self.main_page()
    

    def tv_on_double_click(self, event):
        try:
            item = self.recent_scenarios.selection()[0]
            project_folder = self.recent_scenarios.item(item, "values")[0]
            self.open_scenario(project_folder)
        except IndexError:
            pass
    
    
    def topological_metrics(self):
        
        
        def run_topological_analysis():
            info_label.config(text="Running topological analysis...", fg=self.fg)
            run_button.config(state=tk.DISABLED)
            
            window.update()  # Refresh the window
            
            closeness = closeness_slider.get()
            betweeness = betweeness_slider.get()
            bridges = bridges_slider.get()
            
            # Normalize the values
            total = closeness + betweeness + bridges
            if total == 0:
                closeness, betweeness, bridges = 1/3, 1/3, 1/3
            else:
                closeness /= total            
                betweeness /= total
                bridges /= total
            
            self.closeness_metric = closeness
            self.betweeness_metric = betweeness
            self.bridges_metric = bridges
            
            output_path = self.project_folder
            
            gdf, G, nodes, edges, df_metrics = process_shapefile(self.network_shapefile, closeness, betweeness, bridges, output_path)
            self.edges = edges
            
            plot_metrics(gdf, G, nodes, edges, ["closeness", "betweenness", "bridge", "composite"], 8, False, output_path)
            output_path = os.path.join(output_path, "shp_with_metrics", "Pipes_WG_export_with_metrics.shp")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            save_edge_gdf_shapefile(edges, output_path)
            
            self.topological_analysis_finished = True
            self.df_metrics = df_metrics
            self.unique_pipe_materials_names = df_metrics["MATERIAL"].unique()

            for material_name in self.unique_pipe_materials_names:
                self.pipe_materials[material_name] = self.const_pipe_materials.get(material_name)

            self.topological_analysis_result_shapefile = output_path
            
            run_button.config(state=tk.NORMAL)
            info_label.config(text="Topological analysis finished", fg=self.success_bg)

        
        window = tk.Toplevel(self.root)
        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)
        
        # Center the window
        window_width = self.screen_width // 3
        window_height = self.screen_height // 2.5
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")
                
        closeness_label = tk.Label(window_frame, text="Closeness metric", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        closeness_label.grid(row=0, column=0, padx=5, pady=20)
        closeness_slider = tk.Scale(window_frame, from_=0, to=1, orient=tk.HORIZONTAL, length=int(0.7 * window_width), resolution=0.01)
        closeness_slider.grid(row=0, column=1, padx=5, pady=20)
        
        betweeness_label = tk.Label(window_frame, text="Betweeness metric", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        betweeness_label.grid(row=1, column=0, padx=5, pady=20)
        betweeness_slider = tk.Scale(window_frame, from_=0, to=1, orient=tk.HORIZONTAL, length=int(0.7 * window_width), resolution=0.01)
        betweeness_slider.grid(row=1, column=1, padx=5, pady=20)
        
        bridges_label = tk.Label(window_frame, text="Bridges metric", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        bridges_label.grid(row=2, column=0, padx=5, pady=20)
        bridges_slider = tk.Scale(window_frame, from_=0, to=1, orient=tk.HORIZONTAL, length=int(0.7 * window_width), resolution=0.01)
        bridges_slider.grid(row=2, column=1, padx=5, pady=20)
        
        # Add the 'Run' button to the window
        run_button = tk.Button(window_frame, text="Run", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=run_topological_analysis)
        run_button.grid(row=3, column=0, padx=5, pady=20, columnspan=2)
        
        # Info label
        info_label = tk.Label(window_frame, text="", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        info_label.grid(row=4, column=0, padx=5, pady=20, columnspan=2)
        
    
    def combined_metrics(self):
        
        def run_combined_analysis():
            
            def next_image():
                nonlocal count
                count += 1
                if count >= len(all_images):
                    count = 0
                img_label.config(image=all_images[count])
                img_label.image = all_images[count]
            
            
            def previous_image():
                nonlocal count
                count -= 1
                if count < 0:
                    count = len(all_images) - 1
                img_label.config(image=all_images[count])
                img_label.image = all_images[count]
                

            info_label.config(text="Running combined analysis...", fg=self.fg)
            run_button.config(state=tk.DISABLED)            
            window.update()
            
            combined_metric_failures = combined_metric_failures_slider.get()
            
            self.cell_lower_bound = cell_lower_bound_slider.get()
            self.cell_upper_bound = cell_upper_bound_slider.get()
            
            self.combined_metric_weight = 1 - combined_metric_failures
            self.failures_weight = combined_metric_failures
            
            bounds = (self.cell_lower_bound, self.cell_upper_bound)
            os.makedirs(os.path.join(self.project_folder, "Fishnet_Grids"), exist_ok=True)
            
            self.step2_output_path = os.path.join(self.project_folder, "Fishnet_Grids", "")
            results, best_square_size = spatial_autocorrelation_analysis(pipe_shapefile_path=self.topological_analysis_result_shapefile, failures_shapefile_path=self.damage_shapefile, lower_bound_cell=self.cell_lower_bound, upper_bound_cell=self.cell_upper_bound, weight_avg_combined_metric=self.combined_metric_weight, weight_failures=self.failures_weight, output_path=self.step2_output_path)
        
            info_label.config(text=f"The best square is {best_square_size}. You can change it if you want before proceeding", fg=self.success_bg)
            run_button.config(state=tk.NORMAL)
            window.update()
            
            # Find all files in the Fishnet_Grids folder that are .png files
            files = [f for f in os.listdir(self.step2_output_path) if f.endswith("map.png")]            
            files = sorted(files, key=lambda x: int(x.split("_")[0]))
            
            all_images = []            

            for file in files:
                img = Image.open(os.path.join(self.step2_output_path, file))
                img_resized = img.resize((300, 300))
                photo_image = ImageTk.PhotoImage(img_resized)
                all_images.append(photo_image)
            
            count = 0
                        
            previous_button = tk.Button(window_frame, text="Previous", width=15, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)), command=previous_image)
            previous_button.grid(row=5, column=0, padx=5, pady=10)

            img_label = tk.Label(window_frame, image=all_images[0])
            img_label.image = all_images[count]
            img_label.grid(row=5, column=1, pady=10)

            next_button = tk.Button(window_frame, text="Next", width=15, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)), command=next_image)
            next_button.grid(row=5, column=2, pady=10)
        
        
        window = tk.Toplevel(self.root)
        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)
        
        # Center the window
        window_width = self.screen_width // 1.5
        window_height = self.screen_height // 1.5
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")
                
        combined_metric_failures_label_1 = tk.Label(window_frame, text="Weighted average combined metric", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        combined_metric_failures_label_1.grid(row=0, column=0, padx=5, pady=20)
        combined_metric_failures_slider = tk.Scale(window_frame, from_=0, to=1, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=0.01)
        combined_metric_failures_slider.grid(row=0, column=1, padx=5, pady=20)
        combined_metric_failures_label_2 = tk.Label(window_frame, text="Failures weight", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        combined_metric_failures_label_2.grid(row=0, column=2, padx=5, pady=20)
        
        cell_lower_bound_label = tk.Label(window_frame, text="Cell lower bound", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_lower_bound_label.grid(row=1, column=0, padx=5, pady=20)
        cell_lower_bound_slider = tk.Scale(window_frame, from_=100, to=1000, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=100)
        cell_lower_bound_slider.grid(row=1, column=1, padx=5, pady=20)
        
        cell_upper_bound_label = tk.Label(window_frame, text="Cell upper bound", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_upper_bound_label.grid(row=2, column=0, padx=5, pady=20)
        cell_upper_bound_slider = tk.Scale(window_frame, from_=200, to=1000, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=100)
        cell_upper_bound_slider.grid(row=2, column=1, padx=5, pady=20)
        
        # Add the 'Run' button to the window
        run_button = tk.Button(window_frame, text="Run", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=run_combined_analysis)
        run_button.grid(row=3, column=1, padx=5, pady=20)
        
        # Info label
        info_label = tk.Label(window_frame, text="", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        info_label.grid(row=4, column=1, padx=5, pady=20)
            
    
    def handle_menu_click(self, event):
        try:
            item = self.menu_tree.selection()[0]
            selected_item = self.menu_tree.item(item, "text")
            if selected_item == "Risk assessment (topological metrics)":
                self.topological_metrics()
            if selected_item == "Risk assessment (Combined metrics/damages)":
                self.combined_metrics()
        except IndexError:
            pass

    
    def handle_pipe_line_click(self, canvas_path: CanvasPath):
        pipe_index = int(canvas_path.name)
        pipe_id = self.network_shapefile_attributes['ID'][pipe_index]
        pipe_label = self.network_shapefile_attributes['LABEL'][pipe_index]
        pipe_material = self.network_shapefile_attributes['MATERIAL'][pipe_index]
        messagebox.showinfo(f"Pipe with ID={pipe_id} clicked", f"Pipe Label: {pipe_label}\nPipe Material: {pipe_material}")
    
    
    def save_scenario(self):
        if not self.project_folder:
            messagebox.showerror("Error", "No scenario to save")
            return
        
        # Save the scenario information to a json file
        scenario_info = {
            "project_folder": self.project_folder,
            "project_name": self.project_name,
            "project_description": self.project_description,
            "network_shapefile": self.network_shapefile,
            "damage_shapefile": self.damage_shapefile,
            "topological_analysis_finished": self.topological_analysis_finished,
            "closeness_metric": self.closeness_metric,
            "betweeness_metric": self.betweeness_metric,
            "bridges_metric": self.bridges_metric,
            "edges": "edges.gpkg",
            "df_metrics": "df_metrics.csv",
            "unique_pipe_materials_names": list(self.unique_pipe_materials_names),
            "topological_analysis_result_shapefile": self.topological_analysis_result_shapefile,
            "pipe_materials": self.pipe_materials
        }
        with open(os.path.join(self.project_folder, "metadata.json"), "w") as f:
            json.dump(scenario_info, f)
        
        # Save the geodataframe as files
        self.edges.to_file(os.path.join(self.project_folder, scenario_info['edges']), driver='GPKG')
        
        messagebox.showinfo("Success", "Scenario saved successfully")
    

    def __init__(self) -> None:
        
        self.initial_configurations()
        
        # Initialize all class variables related to the metadata.json file to None
        self.project_folder = None
        self.project_name = None
        self.project_description = None
        self.network_shapefile = None
        self.damage_shapefile = None
        self.topological_analysis_finished = False
        self.closeness_metric = None
        self.betweeness_metric = None
        self.bridges_metric = None
        self.edges = None
        self.df_metrics = None
        self.unique_pipe_materials_names = None
        self.topological_analysis_result_shapefile = None
        self.pipe_materials = {}
        
        self.step2_output_path = None
        self.cell_lower_bound = None
        self.cell_upper_bound = None
        self.combined_metric_weight = None
        self.failures_weight = None
        
        # Initialize all other class variables to None
        self.const_pipe_materials = {"Asbestos Cement": 50, "Steel": 40, "PVC": 30, "HDPE": 12, "Cast iron": 40}
        self.recent_scenarios = None
        self.network_shapefile_attributes = None
        
        
        self.menuBar = tk.Menu(self.root)
        self.root.config(menu=self.menuBar)
        self.fileMenu = tk.Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label="File", menu=self.fileMenu)
        
        # Add a Help menu which opens a messagebox with information about the application
        self.helpMenu = tk.Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label="Help", menu=self.helpMenu)
        self.helpMenu.add_command(label="About", command=lambda: messagebox.showinfo("About", "Pipe Replacement Tool\nVersion 1.0\nDeveloped by: UWMH"))
        
        self.fileMenu.add_command(label="New", command=self.new_scenario)
        self.fileMenu.add_command(label="Open", command=self.open_scenario)

        self.landing_page()
        self.root.mainloop()
        

    def landing_page(self):
        self.landing_page_frame = tk.Frame(self.root, bg=self.bg)
        self.landing_page_frame.pack(expand=True, fill='both')
        
        self.top_logo_frame = tk.Frame(self.landing_page_frame, bg=self.blue_bg, width=self.width, height=170)
        self.top_logo_frame.pack()
        self.top_logo_frame.grid_propagate(False)
        
        self.logo_label = tk.Label(self.top_logo_frame, text="   Welcome to Pipe Replacement Tool", bg="#1d2b59", fg="#ffffff", font=(self.font, self.font_size), image=self.logo_image, compound='left')
        self.logo_label.grid(row=0, column=0)
        
        self.scenarios_frame = tk.Frame(self.landing_page_frame, bg=self.bg, width=self.width, height=200, pady=20)
        self.scenarios_frame.pack()
        self.scenarios_frame.grid_propagate(False)
        
        tk.Label(self.scenarios_frame, text="Create a new scenario or manage existing", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size))).grid(row=0, column=0, columnspan=3, padx=10, pady=10)
        tk.Button(self.scenarios_frame, text="Create New Scenario", bg=self.button_bg, fg=self.button_fg, font=(self.font, int(self.font_size // 1.5)), activebackground=self.button_bg, activeforeground=self.button_fg, command=self.new_scenario).grid(row=1, column=0, padx=10, pady=10)
        tk.Button(self.scenarios_frame, text="Open scenario", bg=self.button_bg, fg=self.button_fg, font=(self.font, int(self.font_size // 1.5)), activebackground=self.button_bg, activeforeground=self.button_fg, command=self.open_scenario).grid(row=1, column=1, padx=10, pady=10)
        
        self.recent_scenarios_frame = tk.Frame(self.landing_page_frame, bg=self.bg, width=self.width, height=300)
        self.recent_scenarios_frame.pack()
        self.recent_scenarios_frame.grid_propagate(False)
        
        tk.Label(self.recent_scenarios_frame, text="Recent scenarios", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size))).grid(row=0, column=0, padx=10)
        
        # Display a datatable with the recent scenarios
        scenarios: List[Dict] = read_scenarios_config_file()
        if scenarios:
            self.recent_scenarios = ttk.Treeview(self.recent_scenarios_frame, columns=['project_folder', 'name', 'timestamp'], show="headings")
            self.recent_scenarios.bind("<Double-1>", lambda event: self.tv_on_double_click(event))
            
            self.recent_scenarios.heading('project_folder', text='Project Path', anchor='center')
            self.recent_scenarios.heading('name', text='Project Name', anchor='center')
            self.recent_scenarios.heading('timestamp', text='Timestamp', anchor='center')
            self.recent_scenarios.grid(row=1, column=0, padx=10, pady=10)
            self.recent_scenarios.column('project_folder', width=int(self.width * 0.25), anchor='center')
            self.recent_scenarios.column('name', width=int(self.width * 0.25), anchor='center')
            self.recent_scenarios.column('timestamp', width=int(self.width * 0.25), anchor='center')
            
            for scenario in scenarios:
                self.recent_scenarios.insert('', 'end', values=(scenario["project_folder"], scenario["name"], time.ctime(scenario["timestamp"])))
        else:
            tk.Label(self.recent_scenarios_frame, text="No recent scenarios available", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size/2))).grid(row=1, column=0, padx=10, pady=10)
    
    
    def main_page(self):
        bounding_box, network_shp_centroid, pipes_lines_paths, self.network_shapefile_attributes = extract_shapefile_data(self.network_shapefile)
        
        # Add the 'Save' button to the menu bar above the Exit button
        self.fileMenu.add_command(label="Save", command=self.save_scenario)
        # self.fileMenu.add_command(label="Save as...")
        self.fileMenu.add_separator()
        self.fileMenu.add_command(label="Exit", command=self.root.quit)
        
        top_frame = tk.Frame(self.root, width=self.width, height=int(self.height * 0.15))
        top_frame.grid(row=0, column=0, columnspan=3, sticky="nsew")
        
        # Insert the project name and description
        label_text = f"{self.project_name}\n{self.project_description}"
        tk.Label(top_frame, text=label_text, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size / 1.7)), padx=10, pady=10).pack(expand=True, fill='both')
    
        # Create and place the frames
        top_height = int(self.height * 0.7)
        
        left_frame_width_mult = 0.2
        map_width_multiplier = 0.6
        right_frame_width_mult = 1 - left_frame_width_mult - map_width_multiplier

        left_frame = tk.Frame(self.root, width=int(self.width * left_frame_width_mult), height=top_height)
        left_frame.grid(row=1, column=0, sticky="nsew")

        middle_frame = tk.Frame(self.root, width=int(self.width * map_width_multiplier), height=top_height, bg=self.bg, border=1, borderwidth=1, relief="solid")
        middle_frame.grid(row=1, column=1, sticky="nsew")

        right_frame = tk.Frame(self.root, width=int(self.width *right_frame_width_mult), height=top_height, bg=self.white, border=1, borderwidth=1, relief="solid")
        right_frame.grid(row=1, column=2, sticky="nsew")

        bottom_frame = tk.Frame(self.root, width=self.width, height=int(self.height * 0.15), bg=self.bg)
        bottom_frame.grid(row=2, column=0, columnspan=3, sticky="nsew")

        # Configure grid weights to allow expansion
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        
        map_widget = tkintermapview.TkinterMapView(middle_frame, width=int(self.width * map_width_multiplier), height=top_height)
        map_widget.pack(expand=True, fill='both', padx=50, pady=50)
        
        map_widget.fit_bounding_box((bounding_box[3], bounding_box[0]), (bounding_box[1], bounding_box[2]))
                
        for index, line_path in enumerate(pipes_lines_paths):
            pipe_color = MATERIAL_COLORS[self.network_shapefile_attributes['MATERIAL'][index]]
            map_widget.set_path(position_list=line_path, color=pipe_color, width=3, name=index, command=self.handle_pipe_line_click)

        self.menu_tree = ttk.Treeview(left_frame, show="tree")
        
        self.menu_tree.bind("<Double-1>", lambda event: self.handle_menu_click(event))
        
        self.menu_tree.column("#0", width=int(self.width * left_frame_width_mult))
        self.menu_tree.heading("#0", text="Setup")
        self.menu_tree.pack(expand=True, fill='both')
        
        # Add vertical padding to Treeview items
        style = ttk.Style()
        style.configure("Treeview", rowheight=35)  # Adjust rowheight as needed
        style.configure("Treeview", font=(self.font, int(self.font_size // 2.5)))

        # Add items to Treeview
        # Disable the ability to collapse or hide the children
        parent_nodes = {}
        for item in LEFT_MENU:
            if not item["leaf"]:
                parent_node = self.menu_tree.insert("", "end", text=item["name"], open=True)
                parent_nodes[item["step"]] = parent_node
            else:
                self.menu_tree.insert(parent_nodes[item["step"]], "end", text=item["name"])
        
        # Add the right frame widgets
        tk.Label(right_frame, text="     Scenario Properties     ", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 1.5))).pack(pady=10)
        
        if self.closeness_metric: tk.Label(right_frame, text=f"Closeness metric: {self.closeness_metric:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 2))).pack(pady=5)
        if self.betweeness_metric: tk.Label(right_frame, text=f"Betweeness metric: {self.betweeness_metric:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 2))).pack(pady=5)
        if self.bridges_metric: tk.Label(right_frame, text=f"Bridges metric: {self.bridges_metric:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 2))).pack(pady=5)
        
        # Add the bottom frame widgets
        tk.Label(bottom_frame, text="Message Window", fg=self.fg, bg=self.bg, font=(self.font, int(self.font_size // 1.5))).pack(pady=30)
