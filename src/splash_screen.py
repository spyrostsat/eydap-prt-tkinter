import tkinter as tk


class SplashScreen:
    def __init__(self):
        self.splash = tk.Tk()
        self.splash.title("Pipe Replacement Tool")
        self.screen_width = self.splash.winfo_screenwidth()
        self.screen_height = self.splash.winfo_screenheight()

        # Set the size and position of the splash screen
        # Center the window
        window_width = self.screen_width // 6
        window_height = self.screen_height // 4
        x = (self.screen_width / 2) - (window_width / 2)
        y = (self.screen_height / 2) - (window_height / 2)
        self.splash.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")
        
        self.splash.configure(bg="#1d2b59")
        
        self.splash.config(cursor="watch")

        self.logo_image = tk.PhotoImage(file='./src/img/logo.png')
        
        
        self.logo_label = tk.Label(self.splash, bg="#1d2b59", image=self.logo_image)
        self.logo_label.pack(expand=True)
        
        # Add a label to the splash screen
        label = tk.Label(self.splash, text="Loading...", font=("Sans", 18), fg="white", bg="#1d2b59")
        label.pack(expand=True)

        # Run the splash screen
        self.splash.mainloop()