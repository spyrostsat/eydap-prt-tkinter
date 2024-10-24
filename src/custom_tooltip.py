
import tkinter as tk


def popup(wdgt: tk.Widget, txt: str, pos: str) -> None:
    pop = tk.Toplevel(wdgt, bg='lightyellow', bd=1, relief='solid')  # Create a new popup window
    pop.overrideredirect(True)

    # Set a fixed width for the label and enable wrapping of the text
    fixed_width = 400  # Change this to your desired width
    label = tk.Label(pop, text=txt, wraplength=fixed_width)  # Set wraplength for text wrapping
    label.pack()

    # Destroy the popup when the mouse leaves the widget
    wdgt.bind('<Leave>', lambda x: pop.destroy())

    # Position the popup
    x_center = wdgt.winfo_rootx() + wdgt.winfo_width() 
    y_center = wdgt.winfo_rooty() + wdgt.winfo_height()

    if pos == 'right':
        pass  # Default position
    elif pos == 'left':
        x_center -= fixed_width
    elif pos == 'top':
        y_center -= wdgt.winfo_height()
    elif pos == 'bottom':
        y_center += wdgt.winfo_height()
    
    pop.geometry(f"+{x_center}+{y_center}")


def make_tt(wdgt: tk.Widget, txt: str, pos: str) -> None:
    wdgt.bind('<Enter>', lambda x: popup(wdgt, txt, pos))
