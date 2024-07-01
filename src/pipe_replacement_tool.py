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
    def initial_configurations(self) -> None:
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


    def __init__(self) -> None:
        
        self.initial_configurations()
        
        # Initialize all class variables related to the metadata.json file to None
        self.project_opened = False
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
        self.best_square_size = None
        self.cell_lower_bound = None
        self.cell_upper_bound = None
        self.combined_metric_weight = None
        self.failures_weight = None
        self.step2_finished = False
        
        self.select_square_size = None
        self.sorted_fishnet_df = None
        self.results_pipe_clusters = None
        self.fishnet_index = None
        self.path_fishnet = None
        self.step2b_finished = False
        
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


    def close_app(self):
        if self.project_opened: 
            self.save_scenario()
        
        self.root.destroy()
        self.root.quit()
        exit()


    def on_app_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.close_app()


    def tv_on_double_click(self, event):
        try:
            item = self.recent_scenarios.selection()[0]
            project_folder = self.recent_scenarios.item(item, "values")[0]
            self.open_scenario(project_folder)
        except IndexError:
            pass


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
        
        self.edges = gpd.read_file(os.path.join(self.project_folder, metadata["edges"])) if metadata.get("edges") else None
        self.df_metrics = pd.read_csv(os.path.join(self.project_folder, metadata["df_metrics"])) if metadata.get("df_metrics") else None
        
        self.step2_output_path = metadata.get("step2_output_path")
        self.best_square_size = metadata.get("best_square_size")
        self.cell_lower_bound = metadata.get("cell_lower_bound")
        self.cell_upper_bound = metadata.get("cell_upper_bound")
        self.combined_metric_weight = metadata.get("combined_metric_weight")
        self.failures_weight = metadata.get("failures_weight")
        self.step2_finished = metadata.get("step2_finished")
        
        self.select_square_size = metadata.get("select_square_size")
        self.sorted_fishnet_df = pd.read_csv(os.path.join(self.project_folder, metadata["sorted_fishnet_df"])) if metadata.get("sorted_fishnet_df") else None
        self.results_pipe_clusters = metadata.get("results_pipe_clusters")
        self.fishnet_index = pd.read_csv(os.path.join(self.project_folder, metadata["fishnet_index"])) if metadata.get("fishnet_index") else None
        
        if self.fishnet_index is not None:
            # If fishnet_index is a DataFrame, convert it to a Series
            if isinstance(self.fishnet_index, pd.DataFrame):
                self.fishnet_index = self.fishnet_index.squeeze()
        
        self.path_fishnet = metadata.get("path_fishnet")
        self.step2b_finished = metadata.get("step2b_finished")
        
        self.landing_page_frame.destroy()
        self.main_page()
    

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
            "edges": "edges.gpkg" if self.topological_analysis_finished else None,
            "df_metrics": "df_metrics.csv" if self.topological_analysis_finished else None,
            "unique_pipe_materials_names": list(self.unique_pipe_materials_names),
            "topological_analysis_result_shapefile": self.topological_analysis_result_shapefile,
            "pipe_materials": self.pipe_materials,
            "step2_output_path": self.step2_output_path,
            "best_square_size": self.best_square_size,
            "cell_lower_bound": self.cell_lower_bound,
            "cell_upper_bound": self.cell_upper_bound,
            "combined_metric_weight": self.combined_metric_weight,
            "failures_weight": self.failures_weight,
            "step2_finished": self.step2_finished,
            "select_square_size": self.select_square_size,
            "sorted_fishnet_df": "sorted_fishnet_df.csv" if self.step2b_finished else None,
            "results_pipe_clusters": self.results_pipe_clusters,
            "fishnet_index": "fishnet_index.csv" if self.step2b_finished else None,
            "path_fishnet": self.path_fishnet,
            "step2b_finished": self.step2b_finished
        }
        with open(os.path.join(self.project_folder, "metadata.json"), "w") as f:
            json.dump(scenario_info, f)
        
        # Save the geodataframe as files
        if self.topological_analysis_finished:
            self.edges.to_file(os.path.join(self.project_folder, scenario_info['edges']), driver='GPKG')
        
        # Save the fishnet dataframe as a csv file
        if self.step2b_finished:
            self.sorted_fishnet_df.to_csv(os.path.join(self.project_folder, scenario_info['sorted_fishnet_df']), index=False)                
            self.fishnet_index.to_csv(os.path.join(self.project_folder, scenario_info['fishnet_index']), index=False)
        
        messagebox.showinfo("Success", "Scenario saved successfully")


    def handle_menu_click(self, event):
        try:
            item = self.menu_tree.selection()[0]
            selected_item = self.menu_tree.item(item, "text")
            
            if selected_item == "Pipe network":
                self.update_middle_frame('network')
            
            if selected_item == "Damages":
                self.update_middle_frame('damages')
            
            if selected_item == "Risk assessment (topological metrics)":
                if not self.step2_finished:
                    self.topological_metrics()
                else:
                    messagebox.showerror("Error", "You have already run the topological analysis")
            
            if selected_item == "Betweeness metric" and self.betweeness_metric:
                self.update_middle_frame('betweeness', os.path.join(self.project_folder, "bc_map.png"))
            if selected_item == "Closeness metric" and self.closeness_metric:
                self.update_middle_frame('closeness', os.path.join(self.project_folder, "cc_map.png"))
            if selected_item == "Bridges metric" and self.bridges_metric:
                self.update_middle_frame('bridges', os.path.join(self.project_folder, "bridge_map.png"))
            if selected_item == "Composite metric" and self.betweeness_metric:
                self.update_middle_frame('composite', os.path.join(self.project_folder, "cm_map.png"))
            
            if selected_item == "Risk assessment (Combined metrics/damages)":
                if not self.topological_analysis_finished:
                    messagebox.showerror("Error", "You need to run the topological analysis first")
                    return
                if self.step2b_finished:
                    messagebox.showerror("Error", "You have already run the risk assessment")
                    return
                
                self.combined_metrics()
                
            if selected_item == "Criticality maps per cell size" and self.step2_finished:
                self.update_middle_frame('criticality_maps_per_cell_size')
            
            if selected_item == "LISA results" and self.step2_finished:
                self.update_middle_frame('lisa', os.path.join(self.step2_output_path, "square_size_comparison_diagram.png"))
            
            if selected_item == "Risk assessment (Optimal / Selected cell size)" and self.step2_finished:
                self.selected_cell_size()
            
            if selected_item == 'Criticality map for selected cell size' and self.step2b_finished:
                img_path = [f for f in os.listdir(self.step2_output_path) if f.endswith("map.png") and 'lisa' in f][0]
                self.update_middle_frame('criticality_map_selected_cell_size', os.path.join(self.step2_output_path, img_path))
            
            if selected_item == "LCC optimization":
                if not self.step2b_finished:
                    messagebox.showerror("Error", "You need to run the risk assessment first")
                    return
                self.lcc_optimization()
            
        except IndexError:
            pass
    

    def handle_pipe_line_click(self, canvas_path: CanvasPath):
        pipe_index = int(canvas_path.name)
        pipe_id = self.network_shapefile_attributes['ID'][pipe_index]
        pipe_label = self.network_shapefile_attributes['LABEL'][pipe_index]
        pipe_material = self.network_shapefile_attributes['MATERIAL'][pipe_index]
        messagebox.showinfo(f"Pipe with ID={pipe_id} clicked", f"Pipe Label: {pipe_label}\nPipe Material: {pipe_material}")
      

    def handle_marker_click(self, marker):
        for i, row in self.damages_shapefile_attributes.iterrows():
            if row['KOD_VLAVIS'] == marker.data:
                damage_id = int(self.damages_shapefile_attributes['KOD_VLAVIS'][i])
                damage_date = self.damages_shapefile_attributes['DATE_EIDOP'][i]
                damage_desc = self.damages_shapefile_attributes['PERIGRAF__'][i]
                messagebox.showinfo(f"Damage with ID={damage_id}", f"Reported at: {damage_date}\n\nDescription: {damage_desc}")
                break


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
        self.project_opened = True
        self.network_bounding_box, self.network_shp_centroid, self.network_pipes_lines_paths, self.network_shapefile_attributes = extract_network_shapefile_data(self.network_shapefile)
        self.damages_bounding_box, self._damages_bbox_centroid, self.damages_points, self.damages_shapefile_attributes = extract_damages_shapefile_data(self.damage_shapefile)
        
        # Add the 'Save' button to the menu bar above the Exit button
        self.fileMenu.add_command(label="Save", command=self.save_scenario)
        # self.fileMenu.add_command(label="Save as...")
        self.fileMenu.add_separator()
        self.fileMenu.add_command(label="Exit", command=self.close_app)
        
        top_frame = tk.Frame(self.root, width=self.width, height=int(self.height * 0.15))
        top_frame.grid(row=0, column=0, columnspan=3, sticky="nsew")
        
        # Insert the project name and description
        label_text = f"{self.project_name}\n{self.project_description}"
        tk.Label(top_frame, text=label_text, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size / 1.7)), padx=10, pady=10).pack(expand=True, fill='both')
    
        # Create and place the frames
        self.top_height = int(self.height * 0.7)
        
        left_frame_width_mult = 0.2
        self.map_width_multiplier = 0.6
        right_frame_width_mult = 1 - left_frame_width_mult - self.map_width_multiplier

        left_frame = tk.Frame(self.root, width=int(self.width * left_frame_width_mult), height=self.top_height)
        left_frame.grid(row=1, column=0, sticky="nsew")

        self.middle_frame = tk.Frame(self.root, width=int(self.width * self.map_width_multiplier), height=self.top_height, bg=self.bg, border=1, borderwidth=1, relief="solid")
        self.middle_frame.grid(row=1, column=1, sticky="nsew")
        
        self.update_middle_frame('network')

        self.right_frame = tk.Frame(self.root, width=int(self.width *right_frame_width_mult), height=self.top_height, bg=self.white, border=1, borderwidth=1, relief="solid")
        self.right_frame.grid(row=1, column=2, sticky="nsew")
        self.update_right_frame()

        bottom_frame = tk.Frame(self.root, width=self.width, height=int(self.height * 0.15), bg=self.bg)
        bottom_frame.grid(row=2, column=0, columnspan=3, sticky="nsew")

        # Configure grid weights to allow expansion
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        
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
        
        # Add the bottom frame widgets
        tk.Label(bottom_frame, text="Message Window", fg=self.fg, bg=self.bg, font=(self.font, int(self.font_size // 1.5))).pack(pady=30)

    
    def update_right_frame(self):
        # Clear the right frame
        for widget in self.right_frame.winfo_children():
            widget.destroy()
        
        # Add the right frame widgets
        tk.Label(self.right_frame, text="     Scenario Properties     ", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 1.5))).pack(pady=10)
        
        if self.closeness_metric: tk.Label(self.right_frame, text=f"Closeness metric: {self.closeness_metric:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 2))).pack(pady=5)
        if self.betweeness_metric: tk.Label(self.right_frame, text=f"Betweeness metric: {self.betweeness_metric:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 2))).pack(pady=5)
        if self.bridges_metric: tk.Label(self.right_frame, text=f"Bridges metric: {self.bridges_metric:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 2))).pack(pady=5)
        if self.cell_lower_bound: tk.Label(self.right_frame, text=f"Cell lower bound: {self.cell_lower_bound}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 2))).pack(pady=5)
        if self.cell_upper_bound: tk.Label(self.right_frame, text=f"Cell upper bound: {self.cell_upper_bound}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 2))).pack(pady=5)
        if self.combined_metric_weight: tk.Label(self.right_frame, text=f"Combined metric weight: {self.combined_metric_weight:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 2))).pack(pady=5)
        if self.failures_weight: tk.Label(self.right_frame, text=f"Failures weight: {self.failures_weight:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 2))).pack(pady=5)
        if self.select_square_size: tk.Label(self.right_frame, text=f"Selected square size: {self.select_square_size}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 2))).pack(pady=5)


    def update_middle_frame(self, display_type: str, *args):
        # Clear the middle frame
        for widget in self.middle_frame.winfo_children():
            widget.destroy()
        
        if display_type == 'network':
            map_widget = tkintermapview.TkinterMapView(self.middle_frame, width=int(self.width * self.map_width_multiplier), height=self.top_height)
            map_widget.pack(expand=True, fill='both', padx=50, pady=50)
            
            map_widget.fit_bounding_box((self.network_bounding_box[3], self.network_bounding_box[0]), (self.network_bounding_box[1], self.network_bounding_box[2]))
                    
            for index, line_path in enumerate(self.network_pipes_lines_paths):
                pipe_color = MATERIAL_COLORS[self.network_shapefile_attributes['MATERIAL'][index]]
                map_widget.set_path(position_list=line_path, color=pipe_color, width=3, name=index, command=self.handle_pipe_line_click)
        
        if display_type == 'damages':
            map_widget = tkintermapview.TkinterMapView(self.middle_frame, width=int(self.width * self.map_width_multiplier), height=self.top_height)
            map_widget.pack(expand=True, fill='both', padx=50, pady=50)
            
            map_widget.fit_bounding_box((self.damages_bounding_box[3], self.damages_bounding_box[0]), (self.damages_bounding_box[1], self.damages_bounding_box[2]))
                        
            for index, point in enumerate(self.damages_points):
                map_widget.set_marker(point[0], point[1], data=int(self.damages_shapefile_attributes['KOD_VLAVIS'][index]), command=self.handle_marker_click)
        
        if display_type == 'betweeness':
            img = Image.open(args[0])
            img_resized = img.resize((800, 800))
            photo_image = ImageTk.PhotoImage(img_resized)
            
            img_label = tk.Label(self.middle_frame, image=photo_image)
            img_label.image = photo_image
            img_label.pack(expand=True, fill='both')
        
        if display_type == 'closeness':
            img = Image.open(args[0])
            img_resized = img.resize((800, 800))
            photo_image = ImageTk.PhotoImage(img_resized)
            
            img_label = tk.Label(self.middle_frame, image=photo_image)
            img_label.image = photo_image
            img_label.pack(expand=True, fill='both')
        
        if display_type == 'bridges':
            img = Image.open(args[0])
            img_resized = img.resize((800, 800))
            photo_image = ImageTk.PhotoImage(img_resized)
            
            img_label = tk.Label(self.middle_frame, image=photo_image)
            img_label.image = photo_image
            img_label.pack(expand=True, fill='both')
        
        if display_type == 'composite':
            img = Image.open(args[0])
            img_resized = img.resize((800, 800))
            photo_image = ImageTk.PhotoImage(img_resized)
            
            img_label = tk.Label(self.middle_frame, image=photo_image)
            img_label.image = photo_image
            img_label.pack(expand=True, fill='both')
        
        if display_type == 'lisa':
            img = Image.open(args[0])
            img_resized = img.resize((800, 480))
            photo_image = ImageTk.PhotoImage(img_resized)
            
            img_label = tk.Label(self.middle_frame, image=photo_image)
            img_label.image = photo_image
            img_label.pack(expand=True, fill='both')
        
        if display_type == 'criticality_maps_per_cell_size':
            self.criticality_maps_per_cell_size()

        if display_type == 'criticality_map_selected_cell_size':
            img = Image.open(args[0])
            img_resized = img.resize((800, 800))
            photo_image = ImageTk.PhotoImage(img_resized)
            
            img_label = tk.Label(self.middle_frame, image=photo_image)
            img_label.image = photo_image
            img_label.pack(expand=True, fill='both')


    def criticality_maps_per_cell_size(self):
        
        
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
        
        
        # Find all files in the Fishnet_Grids folder that are .png files
        files = [f for f in os.listdir(self.step2_output_path) if f.endswith("map.png") and 'lisa' not in f]
        files = sorted(files, key=lambda x: int(x.split("_")[0]))
        
        all_images = []            

        cell_boundaries = [str(cell_size) for cell_size in range(self.cell_lower_bound, self.cell_upper_bound + 1, 100)]

        for file in files:

            if not any(cell_boundary in file for cell_boundary in cell_boundaries):
                continue
            
            img = Image.open(os.path.join(self.step2_output_path, file))
            img_resized = img.resize((800, 800))
            photo_image = ImageTk.PhotoImage(img_resized)
            all_images.append(photo_image)
        
        count = 0
        
        img_label = tk.Label(self.middle_frame, image=all_images[0])
        img_label.image = all_images[count]
        img_label.pack()             

        previous_button = tk.Button(self.middle_frame, text="Previous", width=15, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)), command=previous_image)
        next_button = tk.Button(self.middle_frame, text="Next", width=15, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)), command=next_image)
        
        # DIsplay the two buttons next to each other
        previous_button.pack(side=tk.LEFT, padx=10, pady=10)
        next_button.pack(side=tk.RIGHT, padx=10, pady=10)
        

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

            if self.pipe_materials is None: self.pipe_materials = {}

            for material_name in self.unique_pipe_materials_names:
                self.pipe_materials[material_name] = self.const_pipe_materials.get(material_name)

            self.topological_analysis_result_shapefile = output_path
            
            run_button.config(state=tk.NORMAL)
            info_label.config(text="Topological analysis finished", fg=self.success_bg)
            self.update_right_frame()

        
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
            self.best_square_size = best_square_size
            self.step2_finished = True
        
            info_label.config(text=f"Calculations are finished!", fg=self.success_bg)
            run_button.config(state=tk.NORMAL)
            window.update()
            self.update_right_frame()
            
        
        window = tk.Toplevel(self.root)
        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)
        
        # Center the window
        window_width = self.screen_width // 1.5
        window_height = self.screen_height // 2.2
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
    
    
    def selected_cell_size(self):
        
        
        def run_analysis():
            info_label.config(text="Running analysis...", fg=self.fg)
            run_button.config(state=tk.DISABLED)
            window.update()
            
            self.select_square_size = selected_cell_size_slider.get()
            
            self.sorted_fishnet_df, self.results_pipe_clusters, self.fishnet_index = local_spatial_autocorrelation(self.topological_analysis_result_shapefile, self.damage_shapefile, self.combined_metric_weight, self.failures_weight, self.select_square_size, self.step2_output_path)
            
            self.path_fishnet = os.path.join(self.project_folder, "Fishnet_Grids", f"{self.select_square_size}_fishnets_sorted.shp")
            self.step2b_finished = True
            
            info_label.config(text="Calculations are finished!", fg=self.success_bg)
            run_button.config(state=tk.NORMAL)
            window.update()
            self.update_right_frame()
            
        
        window = tk.Toplevel(self.root)
        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)
        
        # Center the window
        window_width = self.screen_width // 2.8
        window_height = self.screen_height // 3.2
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")

        best_cell_size_label = tk.Label(window_frame, text=f"The best cell size found by the analysis is: {self.best_square_size} m.", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        best_cell_size_label.grid(row=0, column=0, padx=5, pady=20, columnspan=2)
                
        selected_cell_size_label = tk.Label(window_frame, text="Final cell size", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        selected_cell_size_label.grid(row=1, column=0, padx=5, pady=20)
        selected_cell_size_slider = tk.Scale(window_frame, from_=self.cell_lower_bound, to=self.cell_upper_bound, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=100)
        selected_cell_size_slider.grid(row=1, column=1, padx=5, pady=20)        
        
        selected_cell_size_slider.set(self.best_square_size)
        
        # Add the 'Run' button to the window
        run_button = tk.Button(window_frame, text="Run", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=run_analysis)
        run_button.grid(row=2, column=1, padx=5, pady=10, columnspan=2)
        
        # Info label
        info_label = tk.Label(window_frame, text="", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        info_label.grid(row=3, column=1, padx=5, pady=10, columnspan=2)


    def lcc_optimization(self):
        
        
        def optimize_cell():
            cell_index = cell_index_entry.get()
            if not cell_index:
                info_label.config(text="Please insert a cell index", fg=self.danger_bg)
                run_button.config(state=tk.NORMAL)
                return
            
            cell_index = int(cell_index)  # TODO: Make sure the user has inserted the correct values
            
            pipe_materials_lifespan = {}
            for material_name in self.unique_pipe_materials_names:
                pipe_materials_lifespan[material_name] = pipe_materials[material_name].get()
            
            contract_lifespan = contract_lifespan_slider.get()
            time_relaxation = time_relaxation_slider.get()
            
            message, is_valid = check_items_in_key(self.results_pipe_clusters, self.fishnet_index, cell_index)
            
            if not is_valid:
                info_label.config(text=message, fg=self.danger_bg)
                run_button.config(state=tk.NORMAL)
                return
            
            os.makedirs(os.path.join(self.project_folder, "Cell_optimization_results", f"Cell_Priority_{cell_index}"), exist_ok=True)

            # Run functions
            pipes_gdf_cell = process_pipes_cell_data(self.topological_analysis_result_shapefile, self.path_fishnet, self.fishnet_index, cell_index, self.results_pipe_clusters, self.pipe_materials)
            pipe_table_trep, LLCCn, ann_budg, xl, xu = calculate_investment_timeseries(pipes_gdf_cell, contract_lifespan, 50, time_relaxation)

            # Run optimization
            # number of pipes in this cell
            number_of_pipes = pipe_table_trep.count()[0]

            # define 3 hyperparameters for optimization
            pop_size = int(round((7.17 * number_of_pipes - 1.67), -1))  # linear equation going through (10,70) and (70,500)
            n_gen = int(round((1.33 * number_of_pipes + 6.67), -1))  # linear equation going through (70,100) and (10,20)
            n_offsprings = int(max(round((pop_size / 5), -1), 5))
            problem = MyProblem(pipe_table_trep, contract_lifespan, LLCCn, xl, xu)
            algorithm = NSGA2(pop_size=pop_size, n_offsprings=n_offsprings, sampling=IntegerRandomSampling(), crossover=SBX(prob=0.9, eta=15, repair=RoundingRepair()), mutation=PM(eta=20, repair=RoundingRepair()), eliminate_duplicates=True)
            
            info_label.config(text=f"Optimizing cell {cell_index}. This may take a while.", fg=self.fg)
            run_button.config(state=tk.DISABLED)
            window.update()
            
            res = minimize(problem, algorithm, seed=1, termination=('n_gen', 1), save_history=True, verbose=True)
            
            print("Optimization finished. You can close this window and proceed to the next step.")
            X = res.X
            F = res.F

            pipes_gdf_cell_merged = manipulate_opt_results(self.edges, X, F, pipe_table_trep, pipes_gdf_cell)  # Run function for making final geodataframe

            pre_path = os.path.join(self.project_folder, "Cell_optimization_results", f"Cell_Priority_{cell_index}")
            pipes_gdf_cell_merged.to_file(pre_path + f"/Priority_{cell_index}_cell_optimal_replacement.shp")  # Save the shape file into Cell_optimization_results/Cell_Priority_#
            
            info_label.config(text=f"Calculation for Cell {cell_index} is finished.\nContinue with another cell or close the window and proceed.", fg=self.success_bg)
            run_button.config(state=tk.NORMAL)
            window.update()
            self.update_right_frame()
        
        
        window = tk.Toplevel(self.root)
        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)
        
        # Center the window
        window_width = self.screen_width // 2.2
        window_height = self.screen_height // 1.4
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")

        self.results_pipe_clusters = optimize_pipe_clusters(self.results_pipe_clusters, self.df_metrics, self.sorted_fishnet_df)
        os.makedirs(os.path.join(self.project_folder, "Cell_optimization_results"), exist_ok=True)

        pipe_materials_label = tk.Label(window_frame, text=f"Insert pipe materials and their lifespan", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        pipe_materials_label.grid(row=0, column=0, padx=5, pady=20, columnspan=2)
                
        pipe_materials = {}
        for index, material_name in enumerate(self.unique_pipe_materials_names):
            material_label = tk.Label(window_frame, text=material_name, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
            material_label.grid(row=index+1, column=0, padx=5, pady=10)
            
            pipe_materials[material_name] = tk.Entry(window_frame)
            pipe_materials[material_name].grid(row=index+1, column=1, padx=5, pady=10)
            pipe_materials[material_name].insert(0, self.pipe_materials[material_name])
        
        contract_lifespan_label = tk.Label(window_frame, text="Insert lifespan of contract work", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        contract_lifespan_label.grid(row=index+2, column=0, padx=5, pady=20)
        contract_lifespan_slider = tk.Scale(window_frame, from_=5, to=15, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=1)
        contract_lifespan_slider.grid(row=index+2, column=1, padx=5, pady=20)
        contract_lifespan_slider.set(10)
        
        time_relaxation_label = tk.Label(window_frame, text="Allowable time span relaxation", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        time_relaxation_label.grid(row=index+3, column=0, padx=5, pady=20)
        time_relaxation_slider = tk.Scale(window_frame, from_=2, to=5, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=1)
        time_relaxation_slider.grid(row=index+3, column=1, padx=5, pady=20)
        time_relaxation_slider.set(3)        

        # Add a label and an input for the user to select the cell index to optimize
        cell_index_label = tk.Label(window_frame, text="Select the cell index to optimize", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_index_label.grid(row=index+4, column=0, padx=5, pady=20)
        cell_index_entry = tk.Entry(window_frame)
        cell_index_entry.grid(row=index+4, column=1, padx=5, pady=20)
        
        # Add the 'Run' button to the window
        run_button = tk.Button(window_frame, text="Run", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=optimize_cell)
        run_button.grid(row=index+5, column=0, padx=5, pady=10, columnspan=2)
        
        # Info label
        info_label = tk.Label(window_frame, text="", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        info_label.grid(row=index+6, column=0, padx=5, pady=10, columnspan=2)
    