from tkinter import messagebox
from src.scenarios import Scenario
from tkinter import ttk
from tkinter import filedialog
from copy import deepcopy
import tkinter as tk
import random


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


    def create_scenario(self):
        def browse(shp_type: str):
            filename = filedialog.askopenfilename(filetypes=[("Shapefiles", "*.shp")])
            if filename:
                if shp_type == "network":
                    network_entry.delete(0, tk.END)
                    network_entry.insert(tk.END, filename)
                elif shp_type == "damage":
                    damage_entry.delete(0, tk.END)
                    damage_entry.insert(tk.END, filename)
                
            
        window = tk.Toplevel(self.root)
        
        # Center the window
        window_width = self.screen_width // 2
        window_height = self.screen_height // 2
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        window.geometry(f"{window_width}x{window_height}+{int(x)}+{int(y)}")
        
        
        name_label = ttk.Label(window, text="Scenario name")
        name_label.pack(pady=5)
        name_entry = ttk.Entry(window)
        name_entry.pack(pady=5)
        
        description_label = ttk.Label(window, text="Scenario description")
        description_label.pack(pady=5)
        description_text = tk.Text(window, height=5, width=50)
        description_text.pack(pady=5)
        
        network_label = ttk.Label(window, text="Network shapefile")
        network_label.pack(pady=5)
        network_entry = ttk.Entry(window)
        network_entry.pack(side=tk.LEFT, padx=5)
        network_button = ttk.Button(window, text="Browse", command=lambda: browse("network"))
        network_button.pack(side=tk.LEFT, padx=5)
        
        damage_label = ttk.Label(window, text="Damage shapefile")
        damage_label.pack(pady=5)
        damage_entry = ttk.Entry(window)
        damage_entry.pack(side=tk.LEFT, padx=5)
        damage_button = ttk.Button(window, text="Browse", command=lambda: browse("damage"))
        damage_button.pack(side=tk.LEFT, padx=5)
        
        button_frame = ttk.Frame(window)
        button_frame.pack(pady=20)
        create_button = ttk.Button(self.button_frame, text="Create Scenario")
        create_button.pack(side=tk.LEFT, padx=10)
        cancel_button = ttk.Button(self.button_frame, text="Cancel", command=window.destroy)
        cancel_button.pack(side=tk.LEFT, padx=10)
        
    
    def open_scenario(self):
        pass
    
    
    def delete_scenario(self):
        pass
    
    
    def save_scenario(self):
        pass
    

    def __init__(self) -> None:
        
        self.initial_configurations()
        
        menuBar = tk.Menu(self.root)
        self.root.config(menu=menuBar)
        fileMenu = tk.Menu(menuBar, tearoff=0)
        menuBar.add_cascade(label="File", menu=fileMenu)
        
        # Add a Help menu which opens a messagebox with information about the application
        helpMenu = tk.Menu(menuBar, tearoff=0)
        menuBar.add_cascade(label="Help", menu=helpMenu)
        helpMenu.add_command(label="About", command=lambda: messagebox.showinfo("About", "Pipe Replacement Tool\nVersion 1.0\nDeveloped by: UWMH"))
        
        fileMenu.add_command(label="New", command=self.create_scenario)
        fileMenu.add_command(label="Open", command=self.open_scenario)
        fileMenu.add_command(label="Save", command=self.save_scenario)
        fileMenu.add_command(label="Save as...", command=self.initial_configurations)
        fileMenu.add_separator()
        fileMenu.add_command(label="Exit", command=self.root.quit)
        self.landing_page()
        self.root.mainloop()
        

    def landing_page(self):
        self.landing_page_frame = tk.Frame(self.root, bg=self.bg)
        self.landing_page_frame.pack(expand=True, fill='both')
        
        self.top_logo_frame = tk.Frame(self.landing_page_frame, bg="#1d2b59", width=self.width, height=170)
        self.top_logo_frame.pack()
        self.top_logo_frame.grid_propagate(False)
        
        self.logo_label = tk.Label(self.top_logo_frame, text="   Welcome to Pipe Replacement Tool", bg="#1d2b59", fg="#ffffff", font=(self.font, self.font_size), image=self.logo_image, compound='left')
        self.logo_label.grid(row=0, column=0)
        
        self.scenarios_frame = tk.Frame(self.landing_page_frame, bg=self.bg, width=self.width, height=200, pady=20)
        self.scenarios_frame.pack()
        self.scenarios_frame.grid_propagate(False)
        
        tk.Label(self.scenarios_frame, text="Create a new scenario or manage existing", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size))).grid(row=0, column=0, columnspan=3, padx=10, pady=10)
        tk.Button(self.scenarios_frame, text="Create New Scenario", bg=self.button_bg, fg=self.button_fg, font=(self.font, int(self.font_size // 1.5)), activebackground=self.button_bg, activeforeground=self.button_fg, command=self.create_scenario).grid(row=1, column=0, padx=10, pady=10)
        tk.Button(self.scenarios_frame, text="Open scenario", bg=self.button_bg, fg=self.button_fg, font=(self.font, int(self.font_size // 1.5)), activebackground=self.button_bg, activeforeground=self.button_fg, command=self.open_scenario).grid(row=1, column=1, padx=10, pady=10)
        tk.Button(self.scenarios_frame, text="Delete scenario", bg=self.button_bg, fg=self.button_fg, font=(self.font, int(self.font_size // 1.5)), activebackground=self.button_bg, activeforeground=self.button_fg, command=self.delete_scenario).grid(row=1, column=2, padx=10, pady=10)
        
        self.recent_scenarios_frame = tk.Frame(self.landing_page_frame, bg=self.bg, width=self.width, height=300)
        self.recent_scenarios_frame.pack()
        self.recent_scenarios_frame.grid_propagate(False)
        
        tk.Label(self.recent_scenarios_frame, text="Recent scenarios", bg=self.bg, fg=self.fg, font=(self.font, int(self.font_size))).grid(row=0, column=0, padx=10)
        
        # Display a datatable with the recent scenarios
        recent_scenarios = ttk.Treeview(self.recent_scenarios_frame, columns=['ID', 'Title', 'Active', 'Status', 'Timestamp'], show="headings")
        recent_scenarios.heading('ID', text='ID')
        recent_scenarios.heading('Title', text='Title')
        recent_scenarios.heading('Active', text='Active')
        recent_scenarios.heading('Status', text='Status')
        recent_scenarios.heading('Timestamp', text='Timestamp')
        recent_scenarios.grid(row=1, column=0, padx=10, pady=10)
        
        # Insert some data into the datatable
        scenarios = Scenario.get_all()
        
        for scenario in scenarios:
            recent_scenarios.insert('', 'end', values=(scenario.scenario_id, scenario.short_name, scenario.active, scenario.status, scenario.timestamp))