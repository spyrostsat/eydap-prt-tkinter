from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog
from copy import deepcopy
import tkinter as tk
import time
from src.utils import *
import os
from src.tools import *
import ctypes
import platform
import json
import warnings
from typing import List


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
        self.danger_bg = "#FF0000"
        self.success_bg = "#00FF00"
        self.button_bg = "#FAD5A5"
        self.button_fg = "#006994"
        
        # Let's create the root window
        self.root = tk.Tk()
        self.root.title("Pipe Replacement Tool")
        self.root.resizable(True, True)
        
        # Let's find the width and height of the screen
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
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
                scenario_folder = os.path.join(folder, name)
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
        
        self.landing_page_frame.destroy()
        self.main_page()
    

    def tv_on_double_click(self, event):
        item = self.recent_scenarios.selection()[0]
        project_folder = self.recent_scenarios.item(item, "values")[0]
        self.open_scenario(project_folder)
    
    
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
            "damage_shapefile": self.damage_shapefile
        }
        with open(os.path.join(self.project_folder, "metadata.json"), "w") as f:
            json.dump(scenario_info, f)
        
        messagebox.showinfo("Success", "Scenario saved successfully")
    

    def __init__(self) -> None:
        
        self.initial_configurations()
        
        # Initialize all class variables related to the metadata.json file to None
        self.project_folder = None
        self.project_name = None
        self.project_description = None
        self.network_shapefile = None
        self.damage_shapefile = None
        
        # Initialize all other class variables to None
        self.recent_scenarios = None
        
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
            self.recent_scenarios.bind("<Double-1>", lambda recent_scenarios: self.tv_on_double_click(recent_scenarios))
            
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
        # Add the 'Save' button to the menu bar above the Exit button
        self.fileMenu.add_command(label="Save", command=self.save_scenario)
        # self.fileMenu.add_command(label="Save as...")
        self.fileMenu.add_separator()
        self.fileMenu.add_command(label="Exit", command=self.root.quit)
        
        self.main_page_frame = tk.Frame(self.root, bg=self.bg)
        self.main_page_frame.pack(expand=True, fill='both')
        tk.Label(self.main_page_frame, text=f"{self.project_folder}\t{self.network_shapefile}\t{self.project_name}", bg=self.bg, fg=self.fg, font=(self.font, self.font_size)).pack()
