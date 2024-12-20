from tkintermapview.canvas_path import CanvasPath
from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog
from copy import deepcopy
from PIL import ImageTk, Image
from src.map_utils import *
import tkinter as tk
import tkintermapview
import time
from src.utils import *
from src.const import *
import os
import platform
from src.tools import *
from src.custom_tooltip import make_tt
import datetime
import sys
import json
from typing import List
import geopandas as gpd
import numpy as np
import pandas as pd


class PipeReplacementTool:
    
    def __init__(self):
        self.ui_elements()
        self.reset_all()
        self.root_window_stuff()
        self.create_menu()
        self.splash_screen()
        self.root.mainloop()


    def ui_elements(self):
        self.font = "Sans"
        self.courier_font = "Courier 10 Pitch"
        self.font_size = 18

        self.tooltip_font_full = (self.font, int(self.font_size // 1.8), 'italic')

        self.box_width = 1
        self.box_height = 1
        
        self.base_padding = 10
        self.base_entry_width = 10
        
        self.bg = "#F0F0F0"
        self.fg = "#000000"
        self.gray_fg = "#777"
        self.blue_bg = "#1d2b59"
        self.light_blue_bg = "#4d648d"
        self.danger_bg = "#FF0000"
        self.success_bg = "#28a745"
        self.button_bg = "#9CA4B5"
        self.button_fg = "#000"
        self.border_color = "#dddddd"
        self.tk_grey = "#d9d9d9"
        self.white = "#ffffff"


    def reset_all(self):
        self.menuBar = None
        self.fileMenu = None
        self.helpMenu = None
        
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
        
        self.contract_lifespan = None
        self.time_relaxation = None
        self.step3_finished = False
        
        self.const_pipe_materials = {"Asbestos Cement": 50, "Steel": 40, "PVC": 30, "HDPE": 12, "Cast iron": 40}
        self.recent_scenarios = None
        self.network_shapefile_attributes = None


    def root_window_stuff(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Don't show the root window yet
        
        self.root.title("Pipe Replacement Tool")
        self.root.resizable(True, True)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_app_closing)  # Behavior when the 'X' button is clicked
        
        self.screen_width = 1920
        self.screen_height = 1080
                
        self.width = self.screen_width
        self.height = self.screen_height
        
        self.root.geometry(f"{self.width}x{self.height}")
        self.root.iconphoto(True, tk.PhotoImage(file="logo.png", height=170))

        self.logo_image = tk.PhotoImage(file='logo.png')
        self.info_image = tk.PhotoImage(file='info.png').subsample(9, 9)


    def create_menu(self):
        self.root.config(menu=None)
        
        self.menuBar = tk.Menu(self.root)
        self.root.config(menu=self.menuBar)
        
        self.fileMenu = tk.Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label="File", menu=self.fileMenu)
        self.fileMenu.add_command(label="Open", command=self.open_scenario)
        
        self.helpMenu = tk.Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label="Help", menu=self.helpMenu)
        self.helpMenu.add_command(label="About", command=self.show_about_info)


    def close_app(self):
        if self.project_opened: 
            self.save_scenario(show_message=False)
        
        self.root.destroy()
        self.root.quit()
        
        try: sys.exit()
        except: pass


    def return_to_landing_page(self):
        self.save_scenario(show_message=False)
        
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.reset_all()
        self.create_menu()
        self.root.update()
        
        self.landing_page(from_splash=False)


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
        
        
        def browse(browse_type: str) -> None:
            if browse_type == "save_folder":
                folder = filedialog.askdirectory(parent=window, title="Select a folder to save the project")
                
                if folder:
                    save_folder_entry.delete(0, tk.END)
                    save_folder_entry.insert(tk.END, folder)
            
            elif browse_type in ["network", "failures"]:
                filename = filedialog.askopenfilename(parent=window, filetypes=[("Shapefiles", "*.shp")])
                
                if filename:
                    if browse_type == "network":
                        network_entry.delete(0, tk.END)
                        network_entry.insert(tk.END, filename)
                    elif browse_type == "failures":
                        damage_entry.delete(0, tk.END)
                        damage_entry.insert(tk.END, filename)
        
        
        def create_scenario():
            name = name_entry.get().strip()
            description = description_text.get("1.0", tk.END).strip()
            network = network_entry.get().strip()
            damage = damage_entry.get().strip()
            save_folder = save_folder_entry.get().strip()
            
            if not name or not description or not network or not damage or not save_folder:
                messagebox.showerror("Error", "Please fill in all the fields")
                return
            
            if not is_valid_project_name(name):
                messagebox.showerror("Error", "Invalid project name")
                return
            
            if not network.endswith(".shp") or not damage.endswith(".shp") or not os.path.isdir(save_folder):
                messagebox.showerror("Error", "Invalid paths provided")
                return
            
            # Create a folder with the scenario name inside the selected folder
            scenario_folder = os.path.join(save_folder, name, "")
            os.makedirs(scenario_folder, exist_ok=True)
            
            # Delete every file and inner folder inside the scenario folder
            for file in os.listdir(scenario_folder):
                file_path = os.path.join(scenario_folder, file)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                else:
                    shutil.rmtree(file_path)
            
            network_shp = os.path.join(scenario_folder, os.path.basename(network))
            damage_shp = os.path.join(scenario_folder, os.path.basename(damage))
            
            self.project_folder = scenario_folder
            self.project_name = name
            self.project_description = description
            self.network_shapefile = copy_shapefile("network", network, scenario_folder)
            self.damage_shapefile = copy_shapefile("failures", damage, scenario_folder)

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
            
            update_scenarios_config_file(scenario_folder, name, description)  # Update the scenarios config file

            window.destroy()
            messagebox.showinfo("Success", "Project created successfully")
            self.landing_page_frame.destroy()
            self.main_page()

                
        window = tk.Toplevel(self.root)
        
        window.update()
        window.transient(self.root)
        window.grab_set()

        # Center the window
        window_width = self.screen_width // 2.3
        window_height = self.screen_height // 1.7
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")
        
        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)

        name_label = tk.Label(window_frame, text="Project name", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        name_label.grid(row=0, column=0, padx=5, pady=20, sticky='w')
        name_entry = tk.Entry(window_frame, width=50, font=(self.font, int(self.font_size // 1.5)))
        name_entry.grid(row=0, column=1, padx=5, pady=20, columnspan=2, sticky='w')
        
        description_label = tk.Label(window_frame, text="Project description", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        description_label.grid(row=1, column=0, padx=5, pady=20, sticky='w')
        description_text = tk.Text(window_frame, height=5, width=50, font=(self.font, int(self.font_size // 1.5)))
        description_text.grid(row=1, column=1, padx=5, pady=20, columnspan=2, sticky='w')
        
        network_label = tk.Label(window_frame, text="Network shapefile", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        network_label.grid(row=2, column=0, padx=5, pady=20, sticky='w')
        network_entry = tk.Entry(window_frame, width=40, font=(self.font, int(self.font_size // 1.5)))
        network_entry.grid(row=2, column=1, padx=5, pady=20, sticky='w')
        network_button = tk.Button(window_frame, text="Browse", command=lambda: browse("network"), font=(self.font, int(self.font_size // 1.5)))
        network_button.grid(row=2, column=2, padx=5, pady=20, sticky='w')
        
        damage_label = tk.Label(window_frame, text="Failures shapefile", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        damage_label.grid(row=3, column=0, padx=5, pady=20, sticky='w')
        damage_entry = tk.Entry(window_frame, width=40, font=(self.font, int(self.font_size // 1.5)))
        damage_entry.grid(row=3, column=1, padx=5, pady=20, sticky='w')
        damage_button = tk.Button(window_frame, text="Browse", command=lambda: browse("failures"), font=(self.font, int(self.font_size // 1.5)))
        damage_button.grid(row=3, column=2, padx=5, pady=20, sticky='w')
        
        save_folder_label = tk.Label(window_frame, text="Project save folder", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        save_folder_label.grid(row=4, column=0, padx=5, pady=20, sticky='w')
        save_folder_entry = tk.Entry(window_frame, width=40, font=(self.font, int(self.font_size // 1.5)))
        save_folder_entry.grid(row=4, column=1, padx=5, pady=20, sticky='w')
        save_folder_button = tk.Button(window_frame, text="Browse", command=lambda: browse("save_folder"), font=(self.font, int(self.font_size // 1.5)))
        save_folder_button.grid(row=4, column=2, padx=5, pady=20, sticky='w')
        
        create_button = tk.Button(window_frame, text="Create", width=30, command=create_scenario, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)))
        create_button.grid(row=5, column=0, padx=5, pady=20, columnspan=2)
        
        cancel_button = tk.Button(window_frame, text="Cancel", command=window.destroy, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)))
        cancel_button.grid(row=5, column=2, padx=5, pady=20)
    
        window.wait_window()

    
    def open_scenario(self, project_folder = None) -> None:
        if not project_folder:
            folder = filedialog.askdirectory()
            if not folder:
                return
        else:
            folder = project_folder
        
        metadata_file = os.path.join(folder, "metadata.json")
        
        if not os.path.exists(metadata_file):
            messagebox.showerror("Error", "Invalid project folder")
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
        self.unique_pipe_materials_names = np.array(metadata.get("unique_pipe_materials_names")) if self.topological_analysis_finished else None
        self.topological_analysis_result_shapefile = metadata.get("topological_analysis_result_shapefile")
        self.pipe_materials = metadata.get("pipe_materials")
        
        self.edges = gpd.read_file(os.path.join(self.project_folder, metadata["edges"])) if metadata.get("edges") else None
        self.df_metrics = pd.read_csv(os.path.join(self.project_folder, metadata["df_metrics"]), index_col=0) if metadata.get("df_metrics") else None
        
        self.step2_output_path = metadata.get("step2_output_path")
        self.best_square_size = metadata.get("best_square_size")
        self.cell_lower_bound = metadata.get("cell_lower_bound")
        self.cell_upper_bound = metadata.get("cell_upper_bound")
        self.combined_metric_weight = metadata.get("combined_metric_weight")
        self.failures_weight = metadata.get("failures_weight")
        self.step2_finished = metadata.get("step2_finished")
        
        self.select_square_size = metadata.get("select_square_size")
        self.sorted_fishnet_df = pd.read_csv(os.path.join(self.project_folder, metadata["sorted_fishnet_df"]), index_col=0) if metadata.get("sorted_fishnet_df") else None
        self.results_pipe_clusters = metadata.get("results_pipe_clusters")
        self.fishnet_index = pd.read_csv(os.path.join(self.project_folder, metadata["fishnet_index"]), index_col=0) if metadata.get("fishnet_index") else None
        
        self.path_fishnet = metadata.get("path_fishnet")
        self.step2b_finished = metadata.get("step2b_finished")
        
        self.contract_lifespan = metadata.get("contract_lifespan")
        self.time_relaxation = metadata.get("time_relaxation")
        self.step3_finished = metadata.get("step3_finished")
        
        if self.fishnet_index is not None:
            self.fishnet_index = self.fishnet_index.squeeze()
        
        if self.results_pipe_clusters:
            self.results_pipe_clusters = {int(k): v for k, v in self.results_pipe_clusters.items()}
        
        self.landing_page_frame.destroy()
        self.main_page()
    

    def save_scenario(self, show_message=True):
        if not self.project_folder:
            messagebox.showerror("Error", "No project to save")
            return
        
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
            "unique_pipe_materials_names": list(self.unique_pipe_materials_names) if self.topological_analysis_finished else None,
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
            "step2b_finished": self.step2b_finished,
            "contract_lifespan": self.contract_lifespan,
            "time_relaxation": self.time_relaxation,
            "step3_finished": self.step3_finished
        }
        
        with open(os.path.join(self.project_folder, "metadata.json"), "w") as f:
            json.dump(scenario_info, f)
        
        # Save the geodataframe as files
        if self.topological_analysis_finished:
            self.edges.to_file(os.path.join(self.project_folder, scenario_info['edges']), driver='GPKG')
        
        # Save the fishnet dataframe as a csv file
        if self.step2b_finished:
            self.sorted_fishnet_df.to_csv(os.path.join(self.project_folder, scenario_info['sorted_fishnet_df']), index=True)                
            self.fishnet_index.to_csv(os.path.join(self.project_folder, scenario_info['fishnet_index']), index=True)
        
        update_scenarios_config_file(self.project_folder, self.project_name, self.project_description)
        
        if show_message:
            messagebox.showinfo("Success", "Project saved successfully")


    def delete_scenario(self):
        scenario_folder = filedialog.askdirectory(initialdir=os.path.expanduser("~"))

        if not scenario_folder:
            return
        
        if not os.path.exists(os.path.join(scenario_folder, "metadata.json")):
            messagebox.showerror("Error", "Invalid project folder")
            return
        
        # There must also be a folder with the name 'failures' and 'network' inside the scenario folder
        if not os.path.exists(os.path.join(scenario_folder, "network")):
            messagebox.showerror("Error", "Invalid project folder")
            return
        
        # Read the metadata file to get the project name
        with open(os.path.join(scenario_folder, "metadata.json"), "r") as f:
            metadata = json.load(f)
        
        scenario_name = metadata["project_name"]
        
        # The scenario_name must be the same as the folder name
        if not os.path.basename(scenario_folder) == scenario_name:
            messagebox.showerror("Error", "Invalid project folder")
            return
        
        all_scenarios = read_scenarios_config_file()
        
        # The scenario must be in the scenarios config file
        if not any([scenario["name"] == scenario_name for scenario in all_scenarios]):
            messagebox.showerror("Error", "Invalid project folder")
            return
        
        if messagebox.askokcancel("Delete Project", f"Are you sure you want to delete the project '{scenario_name}' in '{scenario_folder}'?"):
            shutil.rmtree(scenario_folder)
            messagebox.showinfo("Success", "Project deleted successfully")


    def handle_menu_click(self, event):
        try:
            item = self.menu_tree.selection()[0]
            selected_item = self.menu_tree.item(item, "text")
            
            # Update the topology is not allowed
            if selected_item == "Setting the topology":
                messagebox.showerror("Error", "You cannot change the topology. Instead, you can create a new project")
                return
            
            # Network shapefile
            if selected_item == f"{MENU_SPACES} Pipe network":
                self.update_middle_frame('network')
            
            # Failures shapefile
            if selected_item == f"{MENU_SPACES} Failures":
                self.update_middle_frame('failures')
            
            # Topological analysis
            if selected_item == "Risk assessment (topological metrics)":
                if not self.step2_finished:
                    self.topological_metrics()
                else:
                    messagebox.showerror("Error", "You have already run the topological analysis")
            
            if selected_item == f"{MENU_SPACES} Betweeness metric" and self.topological_analysis_finished:
                self.update_middle_frame('betweeness', os.path.join(self.project_folder, "bc_map.png"))
            
            elif selected_item == f"{MENU_SPACES} Closeness metric" and self.topological_analysis_finished:
                self.update_middle_frame('closeness', os.path.join(self.project_folder, "cc_map.png"))
            
            elif selected_item == f"{MENU_SPACES} Bridges metric" and self.topological_analysis_finished:
                self.update_middle_frame('bridges', os.path.join(self.project_folder, "bridge_map.png"))
            
            elif selected_item == f"{MENU_SPACES} Composite metric" and self.topological_analysis_finished:
                self.update_middle_frame('composite', os.path.join(self.project_folder, "cm_map.png"))
            
            # Combined metrics/failures
            if selected_item == "Risk assessment (Combined metrics/failures)":
                if not self.topological_analysis_finished:
                    messagebox.showerror("Error", "You need to run the topological analysis first")
                    return
                
                elif self.step2b_finished:
                    messagebox.showerror("Error", "You have already run the risk assessment")
                    return

                else:
                    self.combined_metrics()
                
            if selected_item == f"{MENU_SPACES} Criticality maps per cell size" and self.step2_finished:
                self.update_middle_frame('criticality_maps_per_cell_size')
            
            if selected_item == f"{MENU_SPACES} LISA results" and self.step2_finished:
                self.update_middle_frame('lisa', os.path.join(self.step2_output_path, "square_size_comparison_diagram.png"))
            
            # Optimal / Selected cell size
            if selected_item == "Risk assessment (Optimal / Selected cell size)":
                if not self.step2_finished:
                    messagebox.showerror("Error", "You need to run the risk assessment first")
                    return
                
                elif self.step3_finished:
                    messagebox.showerror("Error", "You have already run the risk assessment for the selected cell size")
                    return
                
                else:
                    self.selected_cell_size()
            
            if selected_item == f'{MENU_SPACES} Criticality map for selected cell size' and self.step2b_finished:
                img_path = [f for f in os.listdir(self.step2_output_path) if (f.endswith("map.png")) and ('lisa' in f) and (f"{self.select_square_size}_" in f)][0]
                self.update_middle_frame('criticality_map_selected_cell_size', os.path.join(self.step2_output_path, img_path))
            
            # LCC optimization
            if selected_item == "LCC optimization":
                if not self.step2b_finished:
                    messagebox.showerror("Error", "You need to run the risk assessment first")
                    return
                
                else:
                    self.lcc_optimization()
            
            if selected_item == f'{MENU_SPACES} Optimized cells' and self.step3_finished:
                self.update_middle_frame('optimized_cells')
                
            # Decision support tool
            if selected_item == "Decision support tool for pipe replacement":
                if not self.step3_finished:
                    messagebox.showerror("Error", "You need to run a cell optimization first")
                    return
                
                else:
                    self.decision_support_tool()
            
            if selected_item == f"{MENU_SPACES} Pipe grouping" and self.step3_finished:
                self.pipe_grouping()
        
        except IndexError:
            pass


    def handle_pipe_line_click(self, canvas_path: CanvasPath):
        pipe_index = int(canvas_path.name)
        pipe_id = self.network_shapefile_attributes['ID'][pipe_index]
        pipe_label = self.network_shapefile_attributes['LABEL'][pipe_index]
        pipe_material = self.network_shapefile_attributes['MATERIAL'][pipe_index]
        messagebox.showinfo(f"Pipe clicked", f"Pipe ID: {pipe_id}\n\nPipe Label: {pipe_label}\n\nPipe Material: {pipe_material}")


    def handle_marker_click(self, marker):
        for i, row in self.damages_shapefile_attributes.iterrows():
            if row['KOD_VLAVIS'] == marker.data:
                damage_id = int(self.damages_shapefile_attributes['KOD_VLAVIS'][i])
                damage_date = self.damages_shapefile_attributes['DATE_EIDOP'][i]
                damage_desc = self.damages_shapefile_attributes['PERIGRAF__'][i]
                messagebox.showinfo(f"Failure point clicked", f"Failure ID: {damage_id}\n\nReported at: {damage_date}\n\nDescription: {damage_desc}")
                break


    def handle_optimized_cell_click(self, pipe):
        pipe_label = pipe.data[0]
        t_opt = pipe.data[1]
        cell = pipe.data[2]
        messagebox.showinfo(title=f"Pipe clicked", message=f"Cell: {cell}\n\nPipe ID: {pipe_label}\n\nReplacement Year: {t_opt}")


    def handle_pipe_grouping_click(self, pipe):
        pipe_label = pipe.data[0]
        cluster = int(pipe.data[1])
        cell = pipe.data[2]
        messagebox.showinfo(title=f"Pipe clicked", message=f"Cell: {cell}\n\nPipe ID: {pipe_label}\n\nGroup: {cluster}")


    def show_pipe_grouping_info(self, info_path):
        with open(info_path, "r") as f:
            info = f.read()
        
        window = tk.Toplevel(self.root)
        window.title("Pipe Grouping Info")
        window.resizable(False, False)
        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)

        # Center the window
        window_width = self.screen_width // 1.5
        window_height = self.screen_height // 2.3
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")

        tk.Label(window_frame, text=info, bg=self.bg, fg=self.fg, font=(self.courier_font, int(self.font_size // 1.5))).pack(expand=True, fill='both')

        window.transient(self.root)
        window.grab_set()
        window.wait_window()


    def show_scenario_info(self):
        scenario_timestamp = None

        for scenario in read_scenarios_config_file():
            if scenario["project_folder"] == self.project_folder and scenario["name"] == self.project_name:
                scenario_timestamp = scenario["timestamp"]
                break
        
        window = tk.Toplevel(self.root)
        window.title("Project Information")
        window.resizable(False, False)
        
        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)

        window_width = self.screen_width // 1.5
        window_height = self.screen_height // 3.5
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")
        
        tk.Label(window_frame, text="Project Name:", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6), 'bold')).grid(row=0, column=0, padx=15, pady=5, sticky='w')
        tk.Label(window_frame, text=self.project_name, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6))).grid(row=0, column=1, padx=15, pady=5, sticky='w')
        
        tk.Label(window_frame, text="Description:", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6), 'bold')).grid(row=1, column=0, padx=15, pady=5, sticky='w')
        tk.Label(window_frame, text=self.project_description, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6))).grid(row=1, column=1, padx=15, pady=5, sticky='w')
        
        tk.Label(window_frame, text="Project Folder:", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6), 'bold')).grid(row=2, column=0, padx=15, pady=5, sticky='w')
        tk.Label(window_frame, text=self.project_folder, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6))).grid(row=2, column=1, padx=15, pady=5, sticky='w')
        
        tk.Label(window_frame, text="Network Shapefile:", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6), 'bold')).grid(row=3, column=0, padx=15, pady=5, sticky='w')
        tk.Label(window_frame, text=self.network_shapefile, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6))).grid(row=3, column=1, padx=15, pady=5, sticky='w')
        
        tk.Label(window_frame, text="Failures Shapefile:", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6), 'bold')).grid(row=4, column=0, padx=15, pady=5, sticky='w')
        tk.Label(window_frame, text=self.damage_shapefile, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6))).grid(row=4, column=1, padx=15, pady=5, sticky='w')
        
        tk.Label(window_frame, text="Timestamp:", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6), 'bold')).grid(row=5, column=0, padx=15, pady=5, sticky='w')
        tk.Label(window_frame, text=time.ctime(scenario_timestamp), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6))).grid(row=5, column=1, padx=15, pady=5, sticky='w')

        tk.Label(window_frame, text="Coordinate System:", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6), 'bold')).grid(row=6, column=0, padx=15, pady=5, sticky='w')
        tk.Label(window_frame, text=TARGET_CRS, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6))).grid(row=6, column=1, padx=15, pady=5, sticky='w')

        # Require the user to close the window before interacting with the main window
        window.transient(self.root)
        window.grab_set()
        window.wait_window()


    def show_about_info(self):
        window = tk.Toplevel(self.root, bg=self.bg)
        window.title("About")
        window.resizable(False, False)

        # Center the window
        window_width = self.screen_width // 3
        window_height = self.screen_height // 6
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")

        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)
        
        padx = 20
        pady = 10
        
        tk.Label(window_frame, text="Pipe Replacement Tool Version 2.0", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6))).pack(padx=padx, pady=pady)
        tk.Label(window_frame, text="Developed by UWMH", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6))).pack(padx=padx, pady=pady)
        tk.Label(window_frame, text="Map data © OpenStreetMap contributors", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.6))).pack(padx=padx, pady=pady)

        # Require the user to close the window before interacting with the main window
        window.transient(self.root)
        window.grab_set()
        window.wait_window()


    def splash_screen(self):
        self.splash = tk.Toplevel()
        self.screen_width = self.splash.winfo_screenwidth()
        self.screen_height = self.splash.winfo_screenheight()

        # Set the size and position of the splash screen
        window_width = self.screen_width // 5
        window_height = self.screen_height // 3.5
        
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        
        self.splash.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")
        
        self.splash.configure(bg=self.blue_bg)
        self.splash.config(cursor="watch")
        self.splash.overrideredirect(True)  # Remove the close, maximize, and minimize buttons
        self.splash_logo_image = tk.PhotoImage(file='logo.png')
        
        self.logo_label = tk.Label(self.splash, bg=self.blue_bg, image=self.splash_logo_image)
        self.logo_label.pack(expand=True)
        
        label = tk.Label(self.splash, text="Loading...", font=("Sans", 18), fg="white", bg=self.blue_bg)
        label.pack(expand=True)

        # Make sure the root window is not visible and the splash screen is visible
        self.root.withdraw()
        self.root.update()
        
        self.splash.update()
        self.splash.deiconify()

        self.landing_page(from_splash=True)
        
    
    def destroy_splash_screen(self):
        # Maximize the root window
        if "Windows" in platform.system():
            self.root.state('zoomed')
        else:
            self.root.attributes('-zoomed', True)
        
        self.splash.destroy()
        self.root.deiconify()


    def landing_page(self, from_splash: bool):
        
        if from_splash:
            self.splash.after(3000, self.destroy_splash_screen)
        
        self.landing_page_frame = tk.Frame(self.root, bg=self.bg)
        self.landing_page_frame.pack(expand=True, fill='both')
        
        self.top_logo_frame = tk.Frame(self.landing_page_frame, bg=self.blue_bg, width=self.width, height=170)
        self.top_logo_frame.pack()
        self.top_logo_frame.grid_propagate(False)
        
        self.logo_label = tk.Label(self.top_logo_frame, text="   Welcome to Pipe Replacement Tool", bg=self.blue_bg, fg="#ffffff", font=(self.font, self.font_size), image=self.logo_image, compound='left')
        self.logo_label.grid(row=0, column=0)
        
        self.scenarios_frame = tk.Frame(self.landing_page_frame, bg=self.bg, width=self.width, height=200, pady=20)
        self.scenarios_frame.pack()
        self.scenarios_frame.grid_propagate(False)
        
        tk.Label(self.scenarios_frame, text="Create a new project or manage existing", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size))).grid(row=0, column=0, columnspan=3, padx=10, pady=10)
        tk.Button(self.scenarios_frame, text="Create New Project", bg=self.button_bg, fg=self.button_fg, font=(self.font, int(self.font_size // 1.7)), activebackground=self.button_bg, activeforeground=self.button_fg, command=self.new_scenario).grid(row=1, column=0, padx=5, pady=10)
        tk.Button(self.scenarios_frame, text="Open Project", bg=self.button_bg, fg=self.button_fg, font=(self.font, int(self.font_size // 1.7)), activebackground=self.button_bg, activeforeground=self.button_fg, command=self.open_scenario).grid(row=1, column=1, padx=5, pady=10)
        tk.Button(self.scenarios_frame, text="Delete Project", bg=self.button_bg, fg=self.button_fg, font=(self.font, int(self.font_size // 1.7)), activebackground=self.button_bg, activeforeground=self.button_fg, command=self.delete_scenario).grid(row=1, column=2, padx=5, pady=10)
        
        self.recent_scenarios_frame = tk.Frame(self.landing_page_frame, bg=self.bg, width=self.width, height=300)
        self.recent_scenarios_frame.pack(padx=10, pady=10)
        self.recent_scenarios_frame.grid_propagate(False)
        
        tk.Label(self.recent_scenarios_frame, text="Recent projects", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size))).grid(row=0, column=0, pady=15, sticky='w')
        
        refresh_scenarios_config_file()  # Make sure the .prt.conf file is up to date
        
        scenarios: List[Dict] = read_scenarios_config_file()  # Display a datatable with the recent scenarios

        self.recent_scenarios = ttk.Treeview(self.recent_scenarios_frame, columns=['project_folder', 'name', 'timestamp'], show="headings")
        self.recent_scenarios.bind("<Double-1>", lambda event: self.tv_on_double_click(event))
        
        anchor_side = 'w'
        
        self.recent_scenarios.heading('project_folder', text='Project Path', anchor=anchor_side)
        self.recent_scenarios.heading('name', text='Project Name', anchor=anchor_side)
        self.recent_scenarios.heading('timestamp', text='Timestamp', anchor=anchor_side)
        self.recent_scenarios.grid(row=1, column=0)
        self.recent_scenarios.column('project_folder', width=int(self.width * 0.25), anchor=anchor_side)
        self.recent_scenarios.column('name', width=int(self.width * 0.25), anchor=anchor_side)
        self.recent_scenarios.column('timestamp', width=int(self.width * 0.25), anchor=anchor_side)
        
        if scenarios:
            scenarios = sorted(scenarios, key=lambda x: x["timestamp"], reverse=True)
            
            for scenario in scenarios:
                self.recent_scenarios.insert('', 'end', values=(scenario["project_folder"], scenario["name"], time.ctime(scenario["timestamp"])))
    
    
    def main_page(self):
        
        self.fileMenu.delete(0)  # Remove the 'Open' option from the File menu
        
        self.helpMenu.add_command(label="Project Information", command=self.show_scenario_info)
        
        self.fileMenu.add_command(label="Save Project", command=self.save_scenario)
        self.fileMenu.add_separator()
        self.fileMenu.add_command(label="Close Project", command=self.return_to_landing_page)
        self.fileMenu.add_command(label="Exit", command=self.close_app)
        
        self.project_opened = True
        self.menu_tree = None
        
        self.network_bounding_box, self.network_shp_centroid, self.network_pipes_lines_paths, self.network_shapefile_attributes = extract_network_shapefile_data(self.network_shapefile)
        self.damages_bounding_box, self._damages_bbox_centroid, self.damages_points, self.damages_shapefile_attributes = extract_damages_shapefile_data(self.damage_shapefile)
        
        top_frame = tk.Frame(self.root, width=self.width, height=int(self.height * 0.15))
        top_frame.grid(row=0, column=0, columnspan=3, sticky="nsew")
        
        label_text = f"{self.project_name}"
        tk.Label(top_frame, text=label_text, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size / 1.7), 'bold'), padx=10, pady=10).pack(expand=True, fill='both')
    
        # Create and place the frames
        self.top_height = int(self.height * 0.7)
        
        left_frame_width_mult = 0.2
        self.map_width_multiplier = 0.45
        right_frame_width_mult = 1 - left_frame_width_mult - self.map_width_multiplier

        left_frame = tk.Frame(self.root, width=int(self.width * left_frame_width_mult), height=self.top_height)
        left_frame.grid(row=1, column=0, sticky="nsew")

        self.middle_frame = tk.Frame(self.root, width=int(self.width * self.map_width_multiplier), height=self.top_height, bg=self.bg, border=1, borderwidth=1, relief="solid")
        self.middle_frame.grid(row=1, column=1, sticky="nsew")
        
        self.my_images_size = (int(self.width * self.map_width_multiplier / IMAGES_DIV), int(self.width * self.map_width_multiplier / IMAGES_DIV))
        self.my_images_size_2 = (int(self.width * self.map_width_multiplier / IMAGES_DIV_2), int(self.width * self.map_width_multiplier / IMAGES_DIV_2))
        
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
        
        # Left menu section
        self.menu_tree = ttk.Treeview(left_frame, show="tree")
        self.menu_tree.bind("<<TreeviewSelect>>", lambda event: self.handle_menu_click(event))
        
        self.menu_tree.column("#0", width=int(self.width * left_frame_width_mult))
        self.menu_tree.heading("#0", text="Setup")
        self.menu_tree.pack(expand=True, fill='both')
        
        # Add vertical padding to Treeview items
        style = ttk.Style()
        style.configure("Treeview", rowheight=LEFT_MENU_ROW_HEIGHT)
        style.configure("Treeview", font=(self.font, int(self.font_size // 2)))
        
        self.update_left_frame()
        
        # Footer section
        tk.Label(bottom_frame, text=f"Pipe Replacement Tool (v.2.0)      © {datetime.datetime.now().year} Urban Water Management & Hydroinformatics Group", fg="#444444", bg=self.bg, font=(self.font, int(self.font_size // 1.8))).pack(pady=10)

        self.root.after(1000, self.check_internet_or_popup)


    def update_left_frame(self):
        for item in self.menu_tree.get_children():
            self.menu_tree.delete(item)
        
        menu_options = self.update_left_menu_options()
        
        for option in menu_options:
            if not option["leaf"]:
                self.menu_tree.insert("", "end", text=option['name'], tags=('active', 'bold-large'))
            else:
                if option['active']:
                    self.menu_tree.insert("", "end", text=f"{MENU_SPACES} {option['name']}", tags=('active', 'normal-medium'))
                else:
                    self.menu_tree.insert("", "end", text=f"{MENU_SPACES} {option['name']}", tags=('inactive', 'normal-medium'))
        
        self.menu_tree.tag_configure('bold-large', font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_TITLE_DIV), 'bold'))
        self.menu_tree.tag_configure('normal-medium', font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_CONTENT_DIV)))
        self.menu_tree.tag_configure('active', foreground='black')
        self.menu_tree.tag_configure('inactive', foreground='#bfbfbf')


    def update_left_menu_options(self) -> List[Dict]:
        
        menu_options: List[Dict] = deepcopy(INIT_MENU_OPTIONS)
        
        if self.topological_analysis_finished:
            menu_options[find_option_index(menu_options, "Betweeness metric")]['active'] = True
            menu_options[find_option_index(menu_options, "Closeness metric")]['active'] = True
            menu_options[find_option_index(menu_options, "Bridges metric")]['active'] = True
            menu_options[find_option_index(menu_options, "Composite metric")]['active'] = True
            menu_options[find_option_index(menu_options, "Risk assessment (Combined metrics/failures)")]['active'] = True
        
        if self.step2_finished:
            menu_options[find_option_index(menu_options, "Criticality maps per cell size")]['active'] = True
            menu_options[find_option_index(menu_options, "LISA results")]['active'] = True
            menu_options[find_option_index(menu_options, "Risk assessment (topological metrics)")]['active'] = False
            menu_options[find_option_index(menu_options, "Risk assessment (Optimal / Selected cell size)")]['active'] = True
        
        if self.step2b_finished:
            menu_options[find_option_index(menu_options, "Criticality map for selected cell size")]['active'] = True
            menu_options[find_option_index(menu_options, "Risk assessment (Combined metrics/failures)")]['active'] = False
            menu_options[find_option_index(menu_options, "LCC optimization")]['active'] = True
        
        if self.step3_finished:
            menu_options[find_option_index(menu_options, "Optimized cells")]['active'] = True
            menu_options[find_option_index(menu_options, "Pipe grouping")]['active'] = True
            menu_options[find_option_index(menu_options, "Risk assessment (Optimal / Selected cell size)")]['active'] = False
            menu_options[find_option_index(menu_options, "Decision support tool for pipe replacement")]['active'] = True
        
        return menu_options


    def update_right_frame(self):
        
        if self.menu_tree: self.update_left_frame()  # Each time the right frame is updated, the left menu should be updated as well

        for widget in self.right_frame.winfo_children():
            widget.destroy()
        
        padx_title = 15
        padx_content = 40
        pady = 10
        
        tk.Label(self.right_frame, text="Project Properties", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // 1.5), 'bold')).pack(padx=padx_title, pady=pady, anchor='w')
        
        if self.closeness_metric or self.betweeness_metric or self.bridges_metric:
            tk.Label(self.right_frame, text=f"Topological metrics", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_TITLE_DIV), 'bold')).pack(padx=padx_title, pady=pady, anchor='w')
            tk.Label(self.right_frame, text=f"Normalised closeness metric: {self.closeness_metric:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_CONTENT_DIV))).pack(padx=padx_content, pady=pady, anchor='w')
            tk.Label(self.right_frame, text=f"Normalised betweeness metric: {self.betweeness_metric:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_CONTENT_DIV))).pack(padx=padx_content, pady=pady, anchor='w')
            tk.Label(self.right_frame, text=f"Normalised bridges metric: {self.bridges_metric:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_CONTENT_DIV))).pack(padx=padx_content, pady=pady, anchor='w')
        
        else:
            tk.Label(self.right_frame, text=f"-", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_CONTENT_DIV), 'bold')).pack(padx=5)
        
        if self.cell_lower_bound: 
            tk.Label(self.right_frame, text="Combined metrics/failures", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_TITLE_DIV), 'bold')).pack(padx=padx_title, pady=pady, anchor='w')
            tk.Label(self.right_frame, text=f"Cell lower bound: {self.cell_lower_bound}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_CONTENT_DIV))).pack(padx=padx_content, pady=pady, anchor='w')
        
        if self.cell_upper_bound: tk.Label(self.right_frame, text=f"Cell upper bound: {self.cell_upper_bound}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_CONTENT_DIV))).pack(padx=padx_content, pady=pady, anchor='w')
        if self.combined_metric_weight: tk.Label(self.right_frame, text=f"Combined metric weight: {self.combined_metric_weight:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_CONTENT_DIV))).pack(padx=padx_content, pady=pady, anchor='w')
        if self.failures_weight: tk.Label(self.right_frame, text=f"Failures weight: {self.failures_weight:.2f}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_CONTENT_DIV))).pack(padx=padx_content, pady=pady, anchor='w')
        
        if self.select_square_size: 
            tk.Label(self.right_frame, text="Optimal / Selected cell size", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_TITLE_DIV), 'bold')).pack(padx=padx_title, pady=pady, anchor='w')
            tk.Label(self.right_frame, text=f"Selected square size: {self.select_square_size}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_CONTENT_DIV))).pack(padx=padx_content, pady=pady, anchor='w')

        if self.step3_finished:
            tk.Label(self.right_frame, text="LCC optimization", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_TITLE_DIV), 'bold')).pack(padx=padx_title, pady=pady, anchor='w')
            base_folder = os.path.join(self.project_folder, "Cell_optimization_results")
            optimized_cells = [f.split('_')[-1] for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f))]
            
            self.right_frame.update_idletasks()
            right_frame_width = self.right_frame.winfo_width()
            tk.Label(self.right_frame, text=f"Optimized cells: {', '.join(optimized_cells)}", fg=self.fg, bg=self.white, font=(self.font, int(self.font_size // LEFT_RIGHT_FRAME_CONTENT_DIV)), wraplength=int(right_frame_width* 0.9)).pack(padx=padx_content, pady=pady, anchor='w')


    def update_middle_frame(self, display_type: str, *args):
        map_mult = 0.77
        map_mult_no_legend = 0.83
        
        # Clear the middle frame
        for widget in self.middle_frame.winfo_children():
            widget.destroy()
        
        if display_type == 'network':
            map_widget = tkintermapview.TkinterMapView(self.middle_frame, width=int(self.width * self.map_width_multiplier), height=int(self.top_height * map_mult))
            map_widget.pack()
            
            map_widget.fit_bounding_box((self.network_bounding_box[3], self.network_bounding_box[0]), (self.network_bounding_box[1], self.network_bounding_box[2]))
                    
            for index, line_path in enumerate(self.network_pipes_lines_paths):
                pipe_color = MATERIAL_COLORS[self.network_shapefile_attributes['MATERIAL'][index]]
                map_widget.set_path(position_list=line_path, color=pipe_color, width=3, name=index, command=self.handle_pipe_line_click)

            # Reset map button
            tk.Button(self.middle_frame, text=RESET_MAP_TEXT, command=lambda: map_widget.fit_bounding_box((self.network_bounding_box[3], self.network_bounding_box[0]), (self.network_bounding_box[1], self.network_bounding_box[2])), bg=self.blue_bg, fg="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 2))).pack(anchor=RESET_MAP_ANCHOR, padx=RESET_MAP_PADX, pady=RESET_MAP_PADY)
        
            tk.Label(self.middle_frame, text="Pipe Material", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 2), 'bold')).pack(side='left', padx=60)
            
            for material, color in MATERIAL_COLORS.items():
                tk.Label(self.middle_frame, text="    ", bg=color, font=(self.font, int(self.font_size // 2))).pack(side='left', padx=10)
                tk.Label(self.middle_frame, text=material, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 2))).pack(side='left')
        
        if display_type == 'failures':
            map_widget = tkintermapview.TkinterMapView(self.middle_frame, width=int(self.width * self.map_width_multiplier), height=int(self.top_height * map_mult_no_legend))
            map_widget.pack()
            
            map_widget.fit_bounding_box((self.damages_bounding_box[3], self.damages_bounding_box[0]), (self.damages_bounding_box[1], self.damages_bounding_box[2]))
            
            marker_img = tk.PhotoImage(file="marker.png").subsample(9, 9)
            for index, point in enumerate(self.damages_points):
                map_widget.set_marker(point[0], point[1], data=int(self.damages_shapefile_attributes['KOD_VLAVIS'][index]), command=self.handle_marker_click, icon=marker_img, marker_color_circle=None, marker_color_outside=None)
        
            # Reset map button
            tk.Button(self.middle_frame, text=RESET_MAP_TEXT, command=lambda: map_widget.fit_bounding_box((self.damages_bounding_box[3], self.damages_bounding_box[0]), (self.damages_bounding_box[1], self.damages_bounding_box[2])), bg=self.blue_bg, fg="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 2))).pack(anchor=RESET_MAP_ANCHOR, padx=RESET_MAP_PADX, pady=RESET_MAP_PADY)
        
        if display_type == "optimized_cells":
            data = extract_optimized_cells_data(os.path.join(self.project_folder, "Cell_optimization_results"))
            map_widget = tkintermapview.TkinterMapView(self.middle_frame, width=int(self.width * self.map_width_multiplier), height=int(self.top_height * map_mult))
            map_widget.pack()
            
            map_widget.fit_bounding_box((self.network_bounding_box[3], self.network_bounding_box[0]), (self.network_bounding_box[1], self.network_bounding_box[2]))
            
            replacement_times: List[int] = []
            for key, value in data.items():
                replacement_times.extend([t_opt for t_opt in value['attributes']['t_opt']])
            
            min_time = min(replacement_times)
            max_time = max(replacement_times)
            pipes_colors = generate_distinct_colors(min_time, max_time)

            for key, value in data.items():
                cell_number = key.split("_")[-1]
                for index, line_path in enumerate(value['pipes_lines_paths']):
                    pipe_color = pipes_colors[str(value['attributes']['t_opt'][index])]
                    map_widget.set_path(position_list=line_path, width=3, color=pipe_color, data=(value['attributes']['ID'][index], value['attributes']['t_opt'][index], cell_number), command=self.handle_optimized_cell_click)

            # Reset map button
            tk.Button(self.middle_frame, text=RESET_MAP_TEXT, command=lambda: map_widget.fit_bounding_box((self.network_bounding_box[3], self.network_bounding_box[0]), (self.network_bounding_box[1], self.network_bounding_box[2])), bg=self.blue_bg, fg="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 2))).pack(anchor=RESET_MAP_ANCHOR, padx=RESET_MAP_PADX, pady=RESET_MAP_PADY)

            tk.Label(self.middle_frame, text="Replacement Year", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 2), 'bold')).pack(side='left', padx=60)
            
            for material, color in pipes_colors.items():
                tk.Label(self.middle_frame, text="    ", bg=color, font=(self.font, int(self.font_size // 2))).pack(side='left', padx=10)
                tk.Label(self.middle_frame, text=material, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 2))).pack(side='left')

        if display_type == "pipe_grouping":
            pipe_grouping_shp = args[0]
            cell_number = args[1]
            
            info_path = pipe_grouping_shp.replace(".shp", ".txt")

            pipes_lines_paths, attributes = extract_pipe_grouping_data(pipe_grouping_shp)
            map_widget = tkintermapview.TkinterMapView(self.middle_frame, width=int(self.width * self.map_width_multiplier), height=int(self.top_height * map_mult))
            map_widget.pack()
            
            map_widget.fit_bounding_box((self.network_bounding_box[3], self.network_bounding_box[0]), (self.network_bounding_box[1], self.network_bounding_box[2]))
            
            clusters = np.unique(attributes['cluster'])
            clusters = [int(c) for c in clusters]
            pipes_colors = generate_distinct_colors(min(clusters), max(clusters))

            for index, line_path in enumerate(pipes_lines_paths):
                pipe_color = pipes_colors[str(int(attributes['cluster'][index]))]
                map_widget.set_path(position_list=line_path, width=3, color=pipe_color, data=(attributes['ID'][index], attributes['cluster'][index], cell_number), command=self.handle_pipe_grouping_click)

            # Reset map button
            tk.Button(self.middle_frame, text=RESET_MAP_TEXT, command=lambda: map_widget.fit_bounding_box((self.network_bounding_box[3], self.network_bounding_box[0]), (self.network_bounding_box[1], self.network_bounding_box[2])), bg=self.blue_bg, fg="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 2))).pack(anchor=RESET_MAP_ANCHOR, padx=RESET_MAP_PADX, pady=RESET_MAP_PADY)

            tk.Label(self.middle_frame, text="Group", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 2), 'bold')).pack(side='left', padx=60)
            
            for material, color in pipes_colors.items():
                tk.Label(self.middle_frame, text="    ", bg=color, font=(self.font, int(self.font_size // 2))).pack(side='left', padx=10)
                tk.Label(self.middle_frame, text=material, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 2))).pack(side='left')
            
            tk.Button(self.middle_frame, text="Continuous Pipe Segments Results", command=lambda: self.show_pipe_grouping_info(info_path), bg=self.blue_bg, fg="#ffffff", font=(self.font, int(self.font_size // 2)), activebackground=self.blue_bg, activeforeground="#ffffff").pack(side='right', padx=RESET_MAP_PADX)

        if display_type == 'betweeness':
            img = Image.open(args[0])
            img_resized = img.resize(self.my_images_size)
            photo_image = ImageTk.PhotoImage(img_resized)
            
            img_label = tk.Label(self.middle_frame, image=photo_image)
            img_label.image = photo_image
            img_label.pack(expand=True, fill='both')
        
        if display_type == 'closeness':
            img = Image.open(args[0])
            img_resized = img.resize(self.my_images_size)
            photo_image = ImageTk.PhotoImage(img_resized)
            
            img_label = tk.Label(self.middle_frame, image=photo_image)
            img_label.image = photo_image
            img_label.pack(expand=True, fill='both')
        
        if display_type == 'bridges':
            img = Image.open(args[0])
            img_resized = img.resize(self.my_images_size)
            photo_image = ImageTk.PhotoImage(img_resized)
            
            img_label = tk.Label(self.middle_frame, image=photo_image)
            img_label.image = photo_image
            img_label.pack(expand=True, fill='both')
        
        if display_type == 'composite':
            img = Image.open(args[0])
            img_resized = img.resize(self.my_images_size)
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
            img_resized = img.resize(self.my_images_size)
            photo_image = ImageTk.PhotoImage(img_resized)
            
            img_label = tk.Label(self.middle_frame, image=photo_image)
            img_label.image = photo_image
            img_label.pack(expand=True, fill='both')


    def check_internet_or_popup(self) -> None:
        if not check_internet_connection():
            messagebox.showwarning("Warning", "Map tiles might not load properly due to lack of internet connection")


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
            img_resized = img.resize(self.my_images_size_2)
            photo_image = ImageTk.PhotoImage(img_resized)
            all_images.append(photo_image)
        
        count = 0
        
        img_label = tk.Label(self.middle_frame, image=all_images[0])
        img_label.image = all_images[count]
        img_label.pack(pady=20)
                
        tk.Label(self.middle_frame, text="Explore the results for the defined range of cell sizes", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.3))).pack(pady=10)
        
        previous_button = tk.Button(self.middle_frame, text="Previous", width=15, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)), command=previous_image)
        next_button = tk.Button(self.middle_frame, text="Next", width=15, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)), command=next_image)

        previous_button.pack(side='left', padx=20, pady=10)
        next_button.pack(side='right', padx=20, pady=10)


    def topological_metrics(self):
        
        
        def run_topological_analysis():
            if self.step2_finished:
                messagebox.showerror("Error", "You have already run the topological analysis")
                return
            
            info_label.config(text="Running topological analysis...", fg=self.fg)
            run_button.config(state=tk.DISABLED)
            
            window.update()
            
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
            self.save_scenario(show_message=False)
            self.update_right_frame()
            
            window.after(WIN_WAIT_BEFORE_CLOSE, window.destroy)
            
        
        window = tk.Toplevel(self.root)
        
        window_width = self.screen_width // 1.7
        window_height = self.screen_height // 1.7
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")
        
        window.update()
        window.transient(self.root)
        window.grab_set()

        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)
        
        lowest_value = 0
        highest_value = 1
        step = 0.01
        slider_percentage = 0.6
        
        closeness_label = tk.Label(window_frame, text="Closeness metric", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        closeness_label.grid(row=0, column=0, padx=5, pady=20, sticky=tk.SE)
        
        closeness_info = tk.Label(window_frame, text="", image=self.info_image, compound=tk.LEFT, bg=self.bg)
        closeness_info.grid(row=0, column=1, padx=5, pady=20, sticky=tk.SW)
        
        closeness_lower_bound = tk.Label(window_frame, text=str(lowest_value), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        closeness_lower_bound.grid(row=0, column=2, padx=5, pady=20, sticky=tk.SE)
        
        closeness_slider = tk.Scale(window_frame, from_=lowest_value, to=highest_value, orient=tk.HORIZONTAL, length=int(slider_percentage * window_width), resolution=step)
        closeness_slider.grid(row=0, column=3, padx=5, pady=20)

        closeness_upper_bound = tk.Label(window_frame, text=str(highest_value), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        closeness_upper_bound.grid(row=0, column=4, padx=5, pady=20, sticky=tk.SW)
        
        betweeness_label = tk.Label(window_frame, text="Betweeness metric", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        betweeness_label.grid(row=1, column=0, padx=5, pady=20, sticky=tk.SE)
        
        betweeness_info = tk.Label(window_frame, text="", image=self.info_image, compound=tk.LEFT, bg=self.bg)
        betweeness_info.grid(row=1, column=1, padx=5, pady=20, sticky=tk.SW)
        
        betweeness_lower_bound = tk.Label(window_frame, text=str(lowest_value), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        betweeness_lower_bound.grid(row=1, column=2, padx=5, pady=20, sticky=tk.SE)
        
        betweeness_slider = tk.Scale(window_frame, from_=lowest_value, to=highest_value, orient=tk.HORIZONTAL, length=int(slider_percentage * window_width), resolution=step)
        betweeness_slider.grid(row=1, column=3, padx=5, pady=20)
        
        betweeness_upper_bound = tk.Label(window_frame, text=str(highest_value), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        betweeness_upper_bound.grid(row=1, column=4, padx=5, pady=20, sticky=tk.SW)
        
        bridges_label = tk.Label(window_frame, text="Bridges metric", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        bridges_label.grid(row=2, column=0, padx=5, pady=20, sticky=tk.SE)
        
        bridges_info = tk.Label(window_frame, text="", image=self.info_image, compound=tk.LEFT, bg=self.bg)
        bridges_info.grid(row=2, column=1, padx=5, pady=20, sticky=tk.SW)
        
        bridges_lower_bound = tk.Label(window_frame, text=str(lowest_value), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        bridges_lower_bound.grid(row=2, column=2, padx=5, pady=20, sticky=tk.SE)
        
        bridges_slider = tk.Scale(window_frame, from_=lowest_value, to=highest_value, orient=tk.HORIZONTAL, length=int(slider_percentage * window_width), resolution=step)
        bridges_slider.grid(row=2, column=3, padx=5, pady=20)
        
        bridges_upper_bound = tk.Label(window_frame, text=str(highest_value), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        bridges_upper_bound.grid(row=2, column=4, padx=5, pady=20, sticky=tk.SW)
        
        composite_label = tk.Label(window_frame, text=COMPOSITE_TOOLTIP, bg=self.bg, fg=self.gray_fg, font=self.tooltip_font_full, wraplength=int(0.9*window_width), justify='left')
        composite_label.grid(row=3, column=0, padx=5, pady=20, columnspan=5, sticky='w')
        
        run_button = tk.Button(window_frame, text="Run", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)), command=run_topological_analysis)
        run_button.grid(row=4, column=0, padx=5, pady=20, columnspan=5)
        
        # Info label
        info_label = tk.Label(window_frame, text="", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        info_label.grid(row=5, column=0, padx=5, pady=20, columnspan=5)
        
        window.after_idle(lambda : make_tt(closeness_info, CLOSENESS_TOOLTIP, 'right'))
        window.after_idle(lambda : make_tt(betweeness_info, BETWEENESS_TOOLTIP, 'right'))
        window.after_idle(lambda : make_tt(bridges_info, BRIDGES_TOOLTIP, 'right'))
        
        window.wait_window()
    
    
    def combined_metrics(self):
        
        
        def run_combined_analysis():
            if self.step2b_finished:
                messagebox.showerror("Error", "You have already run the combined analysis")
                return
            
            combined_metric_failures = combined_metric_failures_slider.get()
            cell_lower_bound = cell_lower_bound_slider.get()
            cell_upper_bound = cell_upper_bound_slider.get()
            
            if cell_lower_bound >= cell_upper_bound:
                messagebox.showerror("Error", "Cell lower bound should be less than cell upper bound")
                return
            
            info_label.config(text="Running combined analysis...", fg=self.fg)
            run_button.config(state=tk.DISABLED)            
            window.update()
            
            self.cell_lower_bound = cell_lower_bound
            self.cell_upper_bound = cell_upper_bound
            
            self.combined_metric_weight = 1 - combined_metric_failures
            self.failures_weight = combined_metric_failures
            
            os.makedirs(os.path.join(self.project_folder, "Fishnet_Grids"), exist_ok=True)
            
            self.step2_output_path = os.path.join(self.project_folder, "Fishnet_Grids", "")
            results, best_square_size = spatial_autocorrelation_analysis(self.topological_analysis_result_shapefile, self.damage_shapefile, self.cell_lower_bound, self.cell_upper_bound, self.combined_metric_weight, self.failures_weight, self.step2_output_path, self.edges)
            self.best_square_size = best_square_size
            self.step2_finished = True
        
            info_label.config(text=f"Calculations are finished!", fg=self.success_bg)
            self.save_scenario(show_message=False)
            run_button.config(state=tk.NORMAL)
            window.update()
            self.update_right_frame()
            
            window.after(WIN_WAIT_BEFORE_CLOSE, window.destroy)
            
        
        window = tk.Toplevel(self.root)
        
        window_width = self.screen_width // 1.2
        window_height = self.screen_height // 2.2
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")

        window.update()
        window.transient(self.root)
        window.grab_set()

        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)
        
        weight_lower_bound = 0
        weight_upper_bound = 1
                
        combined_metric_failures_label_1 = tk.Label(window_frame, text="Weighted average combined metric", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        combined_metric_failures_label_1.grid(row=0, column=0, padx=5, pady=20, sticky=tk.SE)

        combined_info_1 = tk.Label(window_frame, text="", image=self.info_image, compound=tk.LEFT, bg=self.bg)
        combined_info_1.grid(row=0, column=1, padx=5, pady=20, sticky=tk.SW)
        
        combined_lower_value = tk.Label(window_frame, text=str(weight_lower_bound), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        combined_lower_value.grid(row=0, column=2, padx=5, pady=20, sticky=tk.SE)
        
        combined_metric_failures_slider = tk.Scale(window_frame, from_=weight_lower_bound, to=weight_upper_bound, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=0.01)
        combined_metric_failures_slider.grid(row=0, column=3, padx=5, pady=20)
        combined_metric_failures_slider.set(0.5)
        
        combined_upper_value = tk.Label(window_frame, text=str(weight_upper_bound), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        combined_upper_value.grid(row=0, column=4, padx=5, pady=20, sticky=tk.SW)
        
        combined_metric_failures_label_2 = tk.Label(window_frame, text="Failures weight", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        combined_metric_failures_label_2.grid(row=0, column=5, padx=5, pady=20, sticky=tk.SE)

        combined_info_2 = tk.Label(window_frame, text="", image=self.info_image, compound=tk.LEFT, bg=self.bg)
        combined_info_2.grid(row=0, column=6, padx=5, pady=20, sticky=tk.SW)
        
        cell_min_size = 100
        cell_max_size = 1000
        resolution = 100
        
        cell_lower_bound_label = tk.Label(window_frame, text="Cell lower bound", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_lower_bound_label.grid(row=1, column=0, padx=5, pady=20, sticky=tk.SE)

        cell_lower_info = tk.Label(window_frame, text="", image=self.info_image, compound=tk.LEFT, bg=self.bg)
        cell_lower_info.grid(row=1, column=1, padx=5, pady=20, sticky=tk.SW)
        
        cell_lower_bound_low_value = tk.Label(window_frame, text=str(cell_min_size), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_lower_bound_low_value.grid(row=1, column=2, padx=5, pady=20, sticky=tk.SE)
        
        cell_lower_bound_slider = tk.Scale(window_frame, from_=cell_min_size, to=cell_max_size, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=resolution)
        cell_lower_bound_slider.grid(row=1, column=3, padx=5, pady=20)
        cell_lower_bound_slider.set(cell_min_size)
        
        cell_lower_bound_upper_value = tk.Label(window_frame, text=str(cell_max_size), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_lower_bound_upper_value.grid(row=1, column=4, padx=5, pady=20, sticky=tk.SW)
        
        cell_upper_bound_label = tk.Label(window_frame, text="Cell upper bound", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_upper_bound_label.grid(row=2, column=0, padx=5, pady=20, sticky=tk.SE)

        cell_upper_info = tk.Label(window_frame, text="", image=self.info_image, compound=tk.LEFT, bg=self.bg)
        cell_upper_info.grid(row=2, column=1, padx=5, pady=20, sticky=tk.SW)
        
        cell_upper_bound_low_value = tk.Label(window_frame, text=str(cell_min_size + resolution), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_upper_bound_low_value.grid(row=2, column=2, padx=5, pady=20, sticky=tk.SE)
        
        cell_upper_bound_slider = tk.Scale(window_frame, from_=cell_min_size + resolution, to=cell_max_size, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=resolution)
        cell_upper_bound_slider.grid(row=2, column=3, padx=5, pady=20)
        cell_upper_bound_slider.set(cell_max_size)
        
        cell_upper_bound_upper_value = tk.Label(window_frame, text=str(cell_max_size), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_upper_bound_upper_value.grid(row=2, column=4, padx=5, pady=20, sticky=tk.SW)
        
        run_button = tk.Button(window_frame, text="Run", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=run_combined_analysis)
        run_button.grid(row=3, column=0, columnspan=6, padx=5, pady=20)
        
        info_label = tk.Label(window_frame, text="", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        info_label.grid(row=4, column=0, columnspan=6, padx=5, pady=20)
        
        window.after_idle(lambda : make_tt(combined_info_1, COMBINED_METRIC_FAILURES_TOOLTIP, 'right'))
        window.after_idle(lambda : make_tt(combined_info_2, COMBINED_METRIC_FAILURES_TOOLTIP, 'left'))
        window.after_idle(lambda : make_tt(cell_lower_info, CELL_LOWER_BOUND_TOOLTIP, 'right'))
        window.after_idle(lambda : make_tt(cell_upper_info, CELL_UPPER_BOUND_TOOLTIP, 'right'))

        window.wait_window()
    
    
    def selected_cell_size(self):
        
        
        def run_analysis():
            if self.step3_finished:
                messagebox.showerror("Error", "You have already run the selected cell size analysis")
                return
            
            info_label.config(text="Running analysis...", fg=self.fg)
            run_button.config(state=tk.DISABLED)
            window.update()
            
            self.select_square_size = selected_cell_size_slider.get()
            
            self.sorted_fishnet_df, self.results_pipe_clusters, self.fishnet_index = local_spatial_autocorrelation(self.topological_analysis_result_shapefile, self.edges, self.damage_shapefile, self.combined_metric_weight, self.failures_weight, self.select_square_size, self.step2_output_path)
            
            self.path_fishnet = os.path.join(self.project_folder, "Fishnet_Grids", f"{self.select_square_size}_fishnets_sorted.shp")
            self.step2b_finished = True
            
            info_label.config(text="Calculations are finished!", fg=self.success_bg)
            self.save_scenario(show_message=False)
            run_button.config(state=tk.NORMAL)
            window.update()
            self.update_right_frame()
            
            window.after(WIN_WAIT_BEFORE_CLOSE, window.destroy)
            
        
        window = tk.Toplevel(self.root)
        
        window_width = self.screen_width // 2.8
        window_height = self.screen_height // 3.2
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")
        
        window.update()
        window.transient(self.root)
        window.grab_set()

        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)

        best_cell_size_label = tk.Label(window_frame, text=f"The best cell size found by the analysis is: {self.best_square_size} m.", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        best_cell_size_label.grid(row=0, column=0, padx=5, pady=20, columnspan=4)
        
        selected_cell_size_label = tk.Label(window_frame, text="Final cell size", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        selected_cell_size_label.grid(row=1, column=0, padx=5, pady=20, sticky=tk.SW)
        
        cell_size_lower_value = tk.Label(window_frame, text=str(self.cell_lower_bound), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_size_lower_value.grid(row=1, column=1, padx=5, pady=20, sticky=tk.SE)
        
        selected_cell_size_slider = tk.Scale(window_frame, from_=self.cell_lower_bound, to=self.cell_upper_bound, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=100)
        selected_cell_size_slider.grid(row=1, column=2, padx=5, pady=20)
        selected_cell_size_slider.set(self.best_square_size)
        
        cell_size_upper_value = tk.Label(window_frame, text=str(self.cell_upper_bound), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_size_upper_value.grid(row=1, column=3, padx=5, pady=20, sticky=tk.SW)
        
        # Add the 'Run' button to the window
        run_button = tk.Button(window_frame, text="Run", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=run_analysis)
        run_button.grid(row=2, column=0, padx=5, pady=10, columnspan=4)
        
        # Info label
        info_label = tk.Label(window_frame, text="", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        info_label.grid(row=3, column=0, padx=5, pady=10, columnspan=4)
        
        window.wait_window()


    def lcc_optimization(self):
        
        
        def optimize_cell():
            os.makedirs(os.path.join(self.project_folder, "Cell_optimization_results"), exist_ok=True)
            self.results_pipe_clusters = optimize_pipe_clusters(self.results_pipe_clusters, self.df_metrics, self.sorted_fishnet_df)
        
            cell_index = cell_index_entry.get()
            if not cell_index:
                info_label.config(text="Please insert a cell index", fg=self.danger_bg)
                run_button.config(state=tk.NORMAL)
                return
            
            cell_index = int(cell_index)
            
            pipe_materials_lifespan = {}
            for material_name in self.unique_pipe_materials_names:
                try:
                    pipe_materials_lifespan[material_name] = int(pipe_materials[material_name].get())
                except:
                    info_label.config(text="Please insert a valid value for each pipe material", fg=self.danger_bg)
                    run_button.config(state=tk.NORMAL)
                    return
            
            contract_lifespan = contract_lifespan_slider.get()
            time_relaxation = time_relaxation_slider.get()
            
            message, is_valid = check_items_in_key(self.results_pipe_clusters, self.fishnet_index, cell_index)
            
            if not is_valid:
                info_label.config(text=message, fg=self.danger_bg)
                run_button.config(state=tk.NORMAL)
                return
            
            # If this is the first time running the optimization, we save the values and proceed
            if not self.step3_finished:
                self.contract_lifespan = contract_lifespan
                self.time_relaxation = time_relaxation
                self.pipe_materials = pipe_materials_lifespan
            
            else:
                # Make sure the values are the same
                if self.contract_lifespan != contract_lifespan or self.time_relaxation != time_relaxation:
                    info_label.config(text="Please use the same contract lifespan and time relaxation as before", fg=self.danger_bg)
                    run_button.config(state=tk.NORMAL)
                    return
                
                for material_name in self.unique_pipe_materials_names:
                    if self.pipe_materials[material_name] != pipe_materials_lifespan[material_name]:
                        info_label.config(text="Please use the same material lifespans as before", fg=self.danger_bg)
                        run_button.config(state=tk.NORMAL)
                        return
                
                # Make sure the user doesn't optimize the same cell twice
                base_folder = os.path.join(self.project_folder, "Cell_optimization_results")
                optimized_cells = [f.split('_')[-1] for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f))]
                
                if str(cell_index) in optimized_cells:
                    info_label.config(text="This cell has already been optimized", fg=self.danger_bg)
                    run_button.config(state=tk.NORMAL)
                    return
            
            # Run functions
            pipes_gdf_cell = process_pipes_cell_data(self.topological_analysis_result_shapefile, self.path_fishnet, self.fishnet_index, cell_index, self.results_pipe_clusters, self.pipe_materials)
            
            pipe_table_trep, LLCCn, ann_budg, xl, xu = calculate_investment_timeseries(pipes_gdf_cell, self.contract_lifespan, 50, self.time_relaxation)

            # Run optimization
            # number of pipes in this cell
            number_of_pipes = pipe_table_trep.count()[0]

            # define 3 hyperparameters for optimization
            pop_size = int(round((7.17 * number_of_pipes - 1.67), -1))  # linear equation going through (10,70) and (70,500)
            n_gen = int(round((1.33 * number_of_pipes + 6.67), -1))  # linear equation going through (70,100) and (10,20)
            # n_gen = 2  # TODO: Remove this when deploying

            n_offsprings = int(max(round((pop_size / 5), -1), 5))
            
            problem = MyProblem(pipe_table_trep, xl, xu, contract_lifespan, LLCCn)
            
            algorithm = NSGA2(pop_size=pop_size, n_offsprings=n_offsprings, sampling=IntegerRandomSampling(), crossover=SBX(prob=0.9, eta=15, repair=RoundingRepair()), mutation=PM(eta=20, repair=RoundingRepair()), eliminate_duplicates=True)
            
            info_label.config(text=f"Optimizing cell {cell_index}. This will take some time. Total number of generations: {n_gen}", fg=self.fg)
            run_button.config(state=tk.DISABLED)
            window.update()
            
            res = minimize(problem, algorithm, seed=1, termination=('n_gen', n_gen), save_history=True, verbose=True)
            X = res.X
            F = res.F

            pipes_gdf_cell_merged = manipulate_opt_results(self.edges, X, F, pipe_table_trep, pipes_gdf_cell)  # Run function for making final geodataframe
            
            os.makedirs(os.path.join(self.project_folder, "Cell_optimization_results", f"Cell_Priority_{cell_index}"), exist_ok=True)
            pre_path = os.path.join(self.project_folder, "Cell_optimization_results", f"Cell_Priority_{cell_index}")
            pipes_gdf_cell_merged.to_file(pre_path + f"/Priority_{cell_index}_cell_optimal_replacement.shp")  # Save the shape file into Cell_optimization_results/Cell_Priority_#
            
            info_label.config(text=f"Calculation for Cell {cell_index} has finished!", fg=self.success_bg)
            self.step3_finished = True
            self.save_scenario(show_message=False)
            window.update()
            self.update_right_frame()
            
            window.after(WIN_WAIT_BEFORE_CLOSE, window.destroy)
        
        
        window = tk.Toplevel(self.root)

        window_width = self.screen_width // 2
        window_height = self.screen_height // 1.15
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 1.85)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")

        window.update()
        window.transient(self.root)
        window.grab_set()

        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)

        pipe_materials_label = tk.Label(window_frame, text=f"Insert lifespan of pipe materials", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        pipe_materials_label.grid(row=0, column=0, padx=5, pady=20, columnspan=5)
        
        pipe_materials = {}
        for index, material_name in enumerate(self.unique_pipe_materials_names):
            material_label = tk.Label(window_frame, text=material_name, bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
            material_label.grid(row=index+1, column=0, padx=5, pady=10, sticky=tk.SE)
            
            pipe_materials[material_name] = tk.Entry(window_frame, width=70)
            pipe_materials[material_name].grid(row=index+1, column=3, padx=5, pady=10, columnspan=2, sticky='w')
            pipe_materials[material_name].insert(0, self.pipe_materials[material_name])
        
        contract_work_lower_bound = 5
        contract_work_upper_bound = 15
        
        contract_lifespan_label = tk.Label(window_frame, text="Insert lifespan of contract work", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        contract_lifespan_label.grid(row=index+2, column=0, padx=5, pady=20, sticky=tk.SW)

        lifespan_info = tk.Label(window_frame, text="", image=self.info_image, compound=tk.LEFT, bg=self.bg)
        lifespan_info.grid(row=index+2, column=1, padx=5, pady=20, sticky=tk.SW)
        
        contract_lifespan_lower_bound = tk.Label(window_frame, text=str(contract_work_lower_bound), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        contract_lifespan_lower_bound.grid(row=index+2, column=2, padx=5, pady=20, sticky=tk.SW)
        
        contract_lifespan_slider = tk.Scale(window_frame, from_=contract_work_lower_bound, to=contract_work_upper_bound, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=1)
        contract_lifespan_slider.grid(row=index+2, column=3, padx=5, pady=20)
        
        contract_lifespan_upper_bound = tk.Label(window_frame, text=str(contract_work_upper_bound), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        contract_lifespan_upper_bound.grid(row=index+2, column=4, padx=5, pady=20, sticky=tk.SW)
        
        if self.contract_lifespan:
            contract_lifespan_slider.set(self.contract_lifespan)
        else:
            contract_lifespan_slider.set(10)
        
        time_relax_lower_bound = 2
        time_relax_upper_bound = 5
        
        time_relaxation_label = tk.Label(window_frame, text="Allowable time span relaxation", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        time_relaxation_label.grid(row=index+3, column=0, padx=5, pady=20, sticky=tk.SW)

        relaxation_info = tk.Label(window_frame, text="", image=self.info_image, compound=tk.LEFT, bg=self.bg)
        relaxation_info.grid(row=index+3, column=1, padx=5, pady=20, sticky=tk.SW)
        
        time_lower = tk.Label(window_frame, text=str(time_relax_lower_bound), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        time_lower.grid(row=index+3, column=2, padx=5, pady=20, sticky=tk.SW)
        
        time_relaxation_slider = tk.Scale(window_frame, from_=time_relax_lower_bound, to=time_relax_upper_bound, orient=tk.HORIZONTAL, length=int(0.5 * window_width), resolution=1)
        time_relaxation_slider.grid(row=index+3, column=3, padx=5, pady=20, sticky=tk.SW)
        
        time_upper = tk.Label(window_frame, text=str(time_relax_upper_bound), bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        time_upper.grid(row=index+3, column=4, padx=5, pady=20, sticky=tk.SW)
        
        if self.time_relaxation:
            time_relaxation_slider.set(self.time_relaxation)
        else:
            time_relaxation_slider.set(3)

        # Add a label and an input for the user to select the cell index to optimize
        cell_index_label = tk.Label(window_frame, text="Cell index to optimize", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        cell_index_label.grid(row=index+4, column=0, padx=5, pady=20, sticky=tk.SE)

        cell_index_info = tk.Label(window_frame, text="", image=self.info_image, compound=tk.LEFT, bg=self.bg)
        cell_index_info.grid(row=index+4, column=1, padx=5, pady=20, sticky=tk.SW)

        cell_index_entry = tk.Entry(window_frame, width=70)
        cell_index_entry.grid(row=index+4, column=3, padx=5, pady=20, columnspan=2, sticky='w')
        
        # Add the 'Run' button to the window
        run_button = tk.Button(window_frame, text="Run", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=optimize_cell)
        run_button.grid(row=index+5, column=0, padx=5, pady=10, columnspan=5)
        
        # Info label
        info_label = tk.Label(window_frame, text="", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        info_label.grid(row=index+6, column=0, padx=5, pady=5, columnspan=5)
        
        # Create a Text widget
        redirected_output = tk.Text(window_frame, wrap='word', height=5, fg=self.fg, font=(self.font, int(self.font_size // 2)))
        redirected_output.grid(row=index+7, column=0, padx=5, columnspan=5)
        sys.stdout = RedirectOutput(redirected_output)
        
        window.after_idle(lambda : make_tt(lifespan_info, LIFESPAN_TOOLTIP, 'right'))
        window.after_idle(lambda : make_tt(relaxation_info, RELAXATION_TOOLTIP, 'right'))
        window.after_idle(lambda : make_tt(cell_index_info, CELL_INDEX_TOOLTIP, 'right'))
        
        window.wait_window()


    def decision_support_tool(self):


        def cell_click():
            nonlocal cell_shp_path, selected_optimized_cell
            
            selected_optimized_cell = cell_entry.get()
            cell_shp_path = os.path.join(self.project_folder, "Cell_optimization_results", f"Cell_Priority_{selected_optimized_cell}", f"Priority_{selected_optimized_cell}_cell_optimal_replacement.shp")
            
            # Empty the window and add two new buttons
            for widget in window_frame.winfo_children():
                widget.destroy()
            
            time_button = tk.Button(window_frame, text="Proceed with time", background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)), command=time_click)
            time_button.pack(side='left', padx=10)
            
            pipes_button = tk.Button(window_frame, text="Proceed with pipe IDs", background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)), command=pipes_click)
            pipes_button.pack(side='right', padx=10)
            
            window.update()


        def time_click():
            nonlocal proceedTime, start_time_entry, end_time_entry
            
            proceedTime = True
            for widget in window_frame.winfo_children():
                widget.destroy()

            start_time_label = tk.Label(window_frame, text="Start time", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
            start_time_label.grid(row=0, column=0, padx=5, pady=20)
            start_time_entry = tk.Entry(window_frame)
            start_time_entry.grid(row=0, column=1, padx=5, pady=20)
            
            end_time_label = tk.Label(window_frame, text="End time", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
            end_time_label.grid(row=1, column=0, padx=5, pady=20)
            end_time_entry = tk.Entry(window_frame)
            end_time_entry.grid(row=1, column=1, padx=5, pady=20)

            # Add the 'Run' button to the window
            run_button = tk.Button(window_frame, text="Proceed", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=run_click)
            run_button.grid(row=2, column=0, padx=5, pady=10, columnspan=2)


        def pipes_click():
            nonlocal proceedTime, pipe_ids_checkboxes
            
            proceedTime = False
            for widget in window_frame.winfo_children():
                widget.destroy()
            
            gdf = gpd.read_file(cell_shp_path)
            gdf.set_crs(epsg=2100, inplace=True)
            gdf = reproject_shp(gdf)
            
            # Read the pipe IDs
            pipe_ids = list(gdf["ID"].unique())
            pipe_ids.sort()
            
            pipe_ids_per_row = 7
            # Create checkboxes for each pipe ID
            pipe_ids_checkboxes = {}
            for index, pipe_id in enumerate(pipe_ids):
                pipe_ids_checkboxes[pipe_id] = tk.IntVar()
                new_checkbox = tk.Checkbutton(window_frame, text=pipe_id, variable=pipe_ids_checkboxes[pipe_id], bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
                new_checkbox.grid(row=index // pipe_ids_per_row, column=index % pipe_ids_per_row, padx=5, pady=5)
            
            # Add the 'Run' button to the window
            run_button = tk.Button(window_frame, text="Proceed", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=run_click)
            run_button.grid(row=index+1, column=0, padx=5, pady=10, columnspan=pipe_ids_per_row)


        def run_click():
            nonlocal min_distance_entry, output_shp_name_entry, start_time, end_time, selected_pipe_ids
            
            if proceedTime:
                start_time = start_time_entry.get()
                end_time = end_time_entry.get()
                
                if not start_time or not end_time:
                    messagebox.showerror("Error", "Please insert start and end times correctly")
                    return
                try:
                    start_time = float(start_time)
                    end_time = float(end_time)
                    
                except ValueError:
                    messagebox.showerror("Error", "Please insert start and end times correctly")
                    return
                
                if start_time >= end_time:
                    messagebox.showerror("Error", "Start time should be less than end time")
                    return
            
            else:
                selected_pipe_ids = []
                for pipe_id, var in pipe_ids_checkboxes.items():
                    if var.get():
                        selected_pipe_ids.append(int(pipe_id))
                
                if not selected_pipe_ids:
                    messagebox.showerror("Error", "Please select at least one pipe")
                    return
   
            for widget in window_frame.winfo_children():
                widget.destroy()

            min_distance_label = tk.Label(window_frame, text="Contract work min distance (m)", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
            min_distance_label.grid(row=0, column=0, padx=5, pady=20, sticky='w')
            min_distance_entry = tk.Entry(window_frame, width=60)
            min_distance_entry.grid(row=0, column=1, padx=5, pady=20)

            output_shp_name_label = tk.Label(window_frame, text="Output shapefile name", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
            output_shp_name_label.grid(row=1, column=0, padx=5, pady=20, sticky='w')
            output_shp_name_entry = tk.Entry(window_frame, width=60)
            output_shp_name_entry.grid(row=1, column=1, padx=5, pady=20)
            output_shp_name_entry.insert(0, "custom_selection_replacement_v2")

            run_button = tk.Button(window_frame, text="Calculate", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=calculate_click)
            run_button.grid(row=2, column=0, padx=5, pady=10, columnspan=2)
        
        
        def calculate_click():
            if not min_distance_entry.get():
                messagebox.showerror("Error", "Please insert a valid minimum distance")
                return
            
            try:
                min_distance = float(min_distance_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Please insert a valid minimum distance")
                return
            
            if not output_shp_name_entry.get():
                messagebox.showerror("Error", "Please insert a valid output shapefile name")
                return
            else:
                shp_name = output_shp_name_entry.get()

            row_number_to_keep = selected_optimized_cell
            
            if proceedTime:
                filter_list = [start_time, end_time]
            else:
                filter_list = selected_pipe_ids

            # Info label for the user
            info_label = tk.Label(window_frame, text="Calculating...", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
            info_label.grid(row=3, column=0, padx=5, pady=20, columnspan=2)
            window.update()

            red_subgraph, red_edges_df = create_subgraph_from_threshold(cell_shp_path, proceedTime, filter_list)
            red_edges_df, results_df, overall_weighted_average_cost, total_length_under, accept_condition, perc, total_length_all = analyze_graph(red_subgraph, red_edges_df, min_distance, 0.9)
            
            shp_file_path = os.path.join(self.project_folder, "Cell_optimization_results", f"Cell_Priority_{row_number_to_keep}", f"{shp_name}.shp")
            red_edges_df.to_file(shp_file_path)
            
            text_filename = os.path.join(self.project_folder, "Cell_optimization_results", f"Cell_Priority_{row_number_to_keep}", f"{shp_name}.txt")
            export_df_and_sentence_to_file(red_edges_df, results_df, total_length_under, row_number_to_keep, shp_name, overall_weighted_average_cost, accept_condition, perc, total_length_all, min_distance, text_filename)
        
            info_label.config(text="Calculations finished!", fg=self.success_bg)
            window.update()
            
            window.after(WIN_WAIT_BEFORE_CLOSE, window.destroy)
        
        
        selected_optimized_cell = None
        cell_shp_path = None
        proceedTime = None
        start_time_entry = None
        end_time_entry = None
        start_time = None
        end_time = None
        pipe_ids_checkboxes = None
        selected_pipe_ids = None
        min_distance_entry = None
        output_shp_name_entry = None
        
        window = tk.Toplevel(self.root)
        
        window_width = self.screen_width // 2.2
        window_height = self.screen_height // 2.2
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")

        window.update()
        window.transient(self.root)
        window.grab_set()

        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)
        
        base_folder = os.path.join(self.project_folder, "Cell_optimization_results")
        optimized_cells = [f.split('_')[-1] for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f))]
        
        dropdown_label = tk.Label(window_frame, text="Select optimised cell", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        dropdown_label.grid(row=0, column=0, padx=5, pady=20)
        cell_entry = ttk.Combobox(window_frame, values=optimized_cells, state='readonly', width=70)
        cell_entry.grid(row=0, column=1, padx=5, pady=20)
        cell_entry.set(optimized_cells[0])

        aim_label = tk.Label(window_frame, text=DECISION_SUPPORT_TOOLTIP, bg=self.bg, fg=self.gray_fg, font=self.tooltip_font_full, wraplength=int(0.9*window_width), justify='left')
        aim_label.grid(row=1, column=0, padx=5, pady=20, columnspan=2, sticky='w')

        # Add the 'Run' button to the window
        run_button = tk.Button(window_frame, text="Proceed", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=cell_click)
        run_button.grid(row=2, column=0, padx=5, pady=10, columnspan=2)

        window.wait_window()


    def pipe_grouping(self):
        
        
        def cell_click():
            nonlocal run_button, selected_cell
            
            selected_cell = cell_entry.get()
            folder_path = os.path.join(self.project_folder, "Cell_optimization_results", f"Cell_Priority_{selected_cell}")
            all_shp_files = [f for f in os.listdir(folder_path) if f.endswith(".shp") and f"Priority_{selected_cell}_cell_optimal_replacement" not in f]
            
            if not all_shp_files:
                messagebox.showerror("Error", "No shapefiles found in the selected cell")
                return
            
            dropdown_label.config(text="Select shapefile", fg=self.fg)
            cell_entry.config(values=all_shp_files, width=70)
            cell_entry.set(all_shp_files[0])
            
            # Destroy the info label and the 'Run' button
            aim_label.destroy()
            run_button.destroy()
            
            run_button = tk.Button(window_frame, text="Proceed", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=run_click)
            run_button.grid(row=1, column=0, padx=5, pady=10, columnspan=3)
            window.update()
            
            
        def run_click():
            folder_path = os.path.join(self.project_folder, "Cell_optimization_results", f"Cell_Priority_{selected_cell}")
            selected_shp = os.path.join(folder_path, cell_entry.get())
            self.update_middle_frame('pipe_grouping', selected_shp, selected_cell)
            window.destroy()
            
        
        selected_cell = None
        
        window = tk.Toplevel(self.root)
        window_frame = tk.Frame(window, bg=self.bg)
        window_frame.pack(expand=True, fill='both')
        window_frame.grid_propagate(False)
        
        # Center the window
        window_width = self.screen_width // 2.4
        window_height = self.screen_height // 3.9
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")
        
        base_folder = os.path.join(self.project_folder, "Cell_optimization_results")
        optimized_cells = [f.split('_')[-1] for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f))]
        
        dropdown_label = tk.Label(window_frame, text="Select optimised cell", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size // 1.5)))
        dropdown_label.grid(row=0, column=0, padx=5, pady=20)
        cell_entry = ttk.Combobox(window_frame, values=optimized_cells, state='readonly', width=60)
        cell_entry.grid(row=0, column=1, padx=5, pady=20)
        cell_entry.set(optimized_cells[0])

        aim_label = tk.Label(window_frame, text=PIPE_GROUPING_TOOLTIP, bg=self.bg, fg=self.gray_fg, font=self.tooltip_font_full, wraplength=int(0.9*window_width), justify='left')
        aim_label.grid(row=1, column=0, padx=5, pady=20, columnspan=2, sticky='w')

        # Add the 'Run' button to the window
        run_button = tk.Button(window_frame, text="Proceed", width=30, background=self.blue_bg, foreground="#ffffff", activebackground=self.blue_bg, activeforeground="#ffffff", font=(self.font, int(self.font_size // 1.5)),command=cell_click)
        run_button.grid(row=2, column=0, padx=5, pady=10, columnspan=2)
