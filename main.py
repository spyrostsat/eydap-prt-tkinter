import tkinter as tk
import multiprocessing
import sys
from src import globals




def splash_screen():
    splash = tk.Tk()
    splash.title("Pipe Replacement Tool")

    # Set the size and position of the splash screen
    width = 600
    height = 200
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)
    splash.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

    # Set the background color of the splash screen
    splash.configure(bg='#64778d')

    # Add a label to the splash screen
    label = tk.Label(splash, text="The Pipe Replacement Tool is starting...", font=("Helvetica", 18), bg='#64778d', fg='white')
    label.pack(expand=True)

    # Close splash screen after a delay
    splash.after(10000, splash.destroy)

    # Run the splash screen
    splash.mainloop()

def start_main_script():
    from src.pipe_replacement_tool import PipeReplacementTool
    globals.prt = PipeReplacementTool()
    # globals.prt.run()
    sys.exit()  # Ensure the script exits properly

if __name__ == '__main__':
    # Start the splash screen in a separate process
    # splash_process = multiprocessing.Process(target=splash_screen)
    # splash_process.start()

    # Run the main script in the primary process
    start_main_script()

    # Ensure the splash screen process ends
    # splash_process.join()
    # print("Splash screen process ended.")
