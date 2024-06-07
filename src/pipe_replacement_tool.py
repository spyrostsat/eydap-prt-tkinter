from tkinter import messagebox
from tkinter import ttk
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
        
        screen_multiplier = 0.90  # we will use this variable to adjust the size of the root window
        
        # Let's adjust the size of the root window
        self.width = int(screen_multiplier * self.screen_width)  # this will be the width of the root window 
        self.height = int(screen_multiplier * self.screen_height)  # this will be the height of the root window
        width_offset = int((self.screen_width - self.width) / 2)  # this will be the offset of the root window in the x axis
        height_offset = int((self.screen_height - self.height) / 2)  # this will be the offset of the root window in the y axis
        
        self.root.geometry(f"{self.width}x{self.height}+{width_offset}+{height_offset}")
        
        self.root.configure(bg=self.bg, cursor='watch')
        self.root.iconphoto(True, tk.PhotoImage(file="./src/img/icon.png"))


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
        
        fileMenu.add_command(label="New", command=self.initial_configurations)
        fileMenu.add_command(label="Open", command=self.initial_configurations)
        fileMenu.add_command(label="Save", command=self.initial_configurations)
        fileMenu.add_command(label="Save as...", command=self.initial_configurations)
        fileMenu.add_separator()
        fileMenu.add_command(label="Exit", command=self.root.quit)
        self.landing_page()
        self.root.mainloop()
        

    def landing_page(self):
        self.landing_frame = tk.Frame(self.root, bg=self.bg)
        self.landing_frame.pack(expand=True, fill='both')
        
        self.landing_label = tk.Label(self.landing_frame, text="Welcome to Pipe Replacement Tool", bg="blue", fg="white", font=(self.font, self.font_size), image=tk.PhotoImage(file='./src/img/logo.png'), compound='left')
        self.landing_label.pack()
