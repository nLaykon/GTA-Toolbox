import subprocess
import ctypes
import keyboard
import time
import threading
import winsound
import atexit
import queue
import configparser
from os import path
from sys import exit
import tkinter as tk
from inputs import get_gamepad, UnpluggedError

version = "v0.13"

configFile = "GTAToolbox.ini"
config = configparser.ConfigParser()

if not path.exists(configFile):
    config["Game"] = {
        "exe_name": "GTA5_Enhanced.exe"
    }
    config["Keybinds"] = {
        "suspend": "Insert",
        "nosave": "Delete"
    }
    config["ControllerKeybinds"] = {
        "suspend": "BTN_START + BTN_SELECT",
        "nosave": "BTN_THUMBL + BTN_THUMBR",
        
        "guide" : ""
    }
    config["Graphics"] = {
        "transparent_window": "on",
        "win_x": "25",
        "win_y": "25",
        "outline": "1",
        "keybind_bg": "#34495e",
        "nosave_bg": "#e74c3c",
        "warning_bg": "#e74c3c",
        "font_size": "12"
    }
    config["Settings"] = {
        "THIS IS IN DEVELOPMENT IT WILL STILL WORK BUT LOOKS UGLY": "",
        "controller_mode": "off"
    }
    config["Debug"] = {
        "version": version
    }
    with open(configFile, "w") as f:
        config.write(f)

config.read(configFile)

if version != config["Debug"]["version"]:
    print("Version mismatch, this could cause unintended behavior")
    xInput = input("Continue? (y/n): ")
    if xInput.lower() != "y":
        exit("Exiting due to version mismatch.")

process_name = config["Game"]["exe_name"]

suspendKeybind = config["Keybinds"]["suspend"]
nosaveKeybind = config["Keybinds"]["nosave"]

controller_suspend_bind = config["ControllerKeybinds"]["suspend"].split(" + ")
controller_nosave_bind = config["ControllerKeybinds"]["nosave"].split(" + ")

controller_mode = config["Settings"]["controller_mode"].lower() == "on"

keybind_bg = config["Graphics"]["keybind_bg"]
nosave_bg = config["Graphics"]["nosave_bg"]
warning_bg = config["Graphics"]["warning_bg"]

win_x = int(config["Graphics"]["win_x"])
win_y = int(config["Graphics"]["win_y"])
outline = int(config["Graphics"]["outline"])

transparent_window = config["Graphics"]["transparent_window"] == "on"

def check_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

if not check_admin():
    print("Admin privileges are required! Exiting.")
    exit()

ntdll = ctypes.WinDLL("ntdll")
kernel32 = ctypes.WinDLL("kernel32")

def get_process_handle(pid):
    return kernel32.OpenProcess(0x1F0FFF, False, pid)

def suspend_process(pid):
    handle = get_process_handle(pid)
    if handle:
        winsound.Beep(1000, 250)
        ntdll.NtSuspendProcess(handle)
        kernel32.CloseHandle(handle)

def resume_process(pid):
    handle = get_process_handle(pid)
    if handle:
        winsound.Beep(1500, 250)
        ntdll.NtResumeProcess(handle)
        kernel32.CloseHandle(handle)

def find_pid_by_name(process_name):
    result = subprocess.run(["tasklist"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if process_name.lower() in line.lower():
            parts = line.split()
            return int(parts[1])
    return None

class Overlay(tk.Toplevel):
    def __init__(self, master, text, background_color, text_color, width, height):
        super().__init__(master)
        self.geometry(f"{width}x{height}+{win_x}+{win_y}")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.9)
        if transparent_window:
            self.wm_attributes("-transparentcolor", background_color)
        self.config(bg=background_color)

        self.label = tk.Label(self, text=text, fg=text_color, bg=background_color, font=("Aharoni", 12), highlightthickness=outline)
        self.label.pack(expand=True, fill="both")

    def show_overlay(self):
        self.deiconify()

    def hide_overlay(self):
        self.withdraw()

class WarningOverlay(tk.Toplevel):
    def __init__(self, master, text, background_color, text_color, width, height):
        super().__init__(master)
        self.geometry(f"{width}x{height}+{(master.winfo_screenwidth() // 2) - (width // 2)}+{(master.winfo_screenheight() // 2) - (height // 2)}")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.9)
        if (transparent_window):
            self.wm_attributes("-transparentcolor", background_color)
        self.config(bg=background_color)
        
        canvas = tk.Canvas(self, width=width, height=height, bg=background_color, bd=0, highlightthickness=outline)
        
        
        canvas.pack()
        
        canvas.create_polygon(10, height-10, width//2, 10, width-10, height-10, 
                              fill="red", outline="red", width=2)
        
        canvas.create_text(width//2, height//2, text="!", font=("Aharoni", 36, "bold"), fill="white")
        
        self.label = tk.Label(self, text=text, fg=text_color, bg=background_color, font=("Aharoni", 14))
        self.label.place(relx=0.5, rely=0.85, anchor="center")
        self.withdraw()

    def show_overlay(self):
        self.deiconify()

    def hide_overlay(self):
        self.withdraw()

def add_firewall_rule():
    cmd = r'netsh advfirewall firewall add rule name="123456" dir=out action=block remoteip="192.81.241.171"'
    subprocess.run(cmd, shell=True)

def delete_firewall_rule():
    cmd = r'netsh advfirewall firewall delete rule name="123456"'
    subprocess.run(cmd, shell=True)

delete_firewall_rule()

no_save_active = False
command_queue = queue.Queue()

def cleanup():
    global no_save_active
    if no_save_active:
        delete_firewall_rule()
    try:
        nosave_overlay.hide_overlay()
    except Exception:
        pass

atexit.register(cleanup)

def process_commands():
    global no_save_active
    try:
        while True:
            cmd = command_queue.get_nowait()
            if cmd == "toggle_no_save":
                if not no_save_active:
                    nosave_overlay.show_overlay()
                    add_firewall_rule()
                    no_save_active = True
                    keybind_overlay.hide_overlay()
                else:
                    nosave_overlay.hide_overlay()
                    delete_firewall_rule()
                    no_save_active = False
                    keybind_overlay.show_overlay()
    except queue.Empty:
        pass
    root.after(100, process_commands)

def suspend_and_resume():
    pid = find_pid_by_name(process_name)
    if pid:
        warning_overlay.show_overlay()
        keybind_overlay.hide_overlay()
        suspend_process(pid)
        time.sleep(8)
        resume_process(pid)
        warning_overlay.hide_overlay()
        keybind_overlay.show_overlay()

def listen_for_suspend_resume():
    while True:
        keyboard.wait(suspendKeybind)
        suspend_and_resume()

def listen_for_no_save_toggle():
    while True:
        keyboard.wait(nosaveKeybind)
        command_queue.put("toggle_no_save")

controller_state = set()

def listen_for_controller():
    global controller_state
    while True:
        try:
            events = get_gamepad()
            for event in events:
                if event.ev_type == "Key":
                    if event.state == 1:
                        controller_state.add(event.code)
                    elif event.state == 0:
                        controller_state.discard(event.code)

                    if all(btn in controller_state for btn in controller_suspend_bind):
                        suspend_and_resume()

                    if all(btn in controller_state for btn in controller_nosave_bind):
                        command_queue.put("toggle_no_save")
        except UnpluggedError:
            time.sleep(1)
            continue

root = tk.Tk()
root.withdraw()
root.geometry("300x150+10+10")
root.attributes("-topmost", True)
root.config(bg="#2c3e50")

if controller_mode:
    overlay_text = f"{process_name}\n\nController Keybinds:\nSuspend: {' + '.join(controller_suspend_bind)}\nNo Save: {' + '.join(controller_nosave_bind)}"
else:
    overlay_text = f"{process_name}\n\nKeybinds:\nSuspend: {suspendKeybind}\nNo Save: {nosaveKeybind}"

keybind_overlay = Overlay(root, overlay_text, keybind_bg, "white", 200, 120)
keybind_overlay.show_overlay()

warning_overlay = WarningOverlay(root, 
                                 "Process suspended!", 
                                 warning_bg, "white", 200, 200)

nosave_overlay = Overlay(root, "No Save Activated", nosave_bg, "white", 150, 50)
nosave_overlay.withdraw()

threading.Thread(target=listen_for_suspend_resume, daemon=True).start()
threading.Thread(target=listen_for_no_save_toggle, daemon=True).start()
threading.Thread(target=listen_for_controller, daemon=True).start()

process_commands()

root.mainloop()
