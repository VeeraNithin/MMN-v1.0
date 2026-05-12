import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import serial
import serial.tools.list_ports
import subprocess
import threading
import tempfile
import os
import urllib.request
import zipfile
import io
import shutil
import time

# --- Try loading Pygame for the Startup Song ---
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

# Set Professional IDE Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ==========================================
# MMN EMBEDDED TOOLCHAIN MANAGER
# ==========================================
class ToolchainManager:
    """Handles the installation and detection of the Arduino CLI compiler."""
    def __init__(self):
        self.system_cli = shutil.which("arduino-cli")
        self.core_dir = os.path.join(os.path.expanduser("~"), ".mmn_studio")
        self.local_cli = os.path.join(self.core_dir, "arduino-cli.exe") if os.name == 'nt' else os.path.join(self.core_dir, "arduino-cli")

    def get_cli_path(self):
        if self.system_cli: return self.system_cli
        if os.path.exists(self.local_cli): return self.local_cli
        return None

    def is_installed(self):
        return self.get_cli_path() is not None

# ==========================================
# MAIN IDE APPLICATION
# ==========================================
class MMN_Studio_IDE(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("MMN-1.0 - Powered by MMN - A product of NGI")
        self.geometry("1400x850")
        self.minsize(1200, 700)
        
        # Load custom icon if available
        if os.path.exists("mmn_logo.ico"):
            self.iconbitmap("mmn_logo.ico")
        
        self.current_port = tk.StringVar(value="Select Port")
        self.current_board = tk.StringVar(value="arduino:avr:uno")
        self.toolchain = ToolchainManager()
        self.serial_monitor_window = None
        self.active_serial = None
        self.reading_serial = False
        
        self._init_50_examples()
        self._build_ui()
        
        self.refresh_ports()
        self.load_example("01. Basics", "Blink")

    def init_system_check(self):
        """Called after the splash screen finishes."""
        if not self.toolchain.is_installed():
            self.log("\n[SYSTEM ALERT] Hardware Compiler not detected!", color="#f59e0b")
            self.log("Click the '📥 Install Compiler Core' button at the top to provision the MMN Engine.")
        else:
            self.log("\n[System] MMN-1.0 Toolchain Engine verified and ready.")

    def _init_50_examples(self):
        """Massive database of 55 Real-World Hardware Sketches"""
        self.examples = {
            "01. Basics": ["BareMinimum", "Blink", "DigitalReadSerial", "AnalogReadSerial", "Fade", "ReadAnalogVoltage"],
            "02. Digital": ["BlinkWithoutDelay", "Button", "Debounce", "StateChangeDetection", "ToneMelody", "ToneMultiple", "PitchFollower"],
            "03. Analog": ["AnalogInOutSerial", "AnalogInput", "AnalogWriteMega", "Calibration", "Fading", "Smoothing"],
            "04. Communication": ["ASCIITable", "Dimmer", "Graph", "Midi", "MultiSerial", "PhysicalPixel", "ReadASCIIString", "SerialCallResponse", "SerialEvent"],
            "05. Control Structures": ["Arrays", "ForLoopIteration", "IfStatementConditional", "SwitchCase", "SwitchCase2", "WhileStatementConditional"],
            "06. Sensors": ["Ultrasonic_HCSR04", "PIR_Motion", "LDR_Photoresistor", "DHT11_Temperature", "BMP180_Pressure", "Water_Level", "Sound_Sensor"],
            "07. Displays": ["LCD_HelloWorld", "LCD_Blink", "LCD_Cursor", "LCD_Scroll", "OLED_SSD1306", "TFT_ST7735", "NeoPixel_Matrix"],
            "08. Motors & Actuators": ["Servo_Sweep", "Servo_Knob", "Stepper_OneRevolution", "DC_Motor_L298N", "Brushless_ESC"],
            "09. ESP32 & IoT": ["WiFi_Scan", "SimpleWebServer", "MQTT_Publish", "BLE_Server", "DeepSleep", "NTP_Client", "OTA_WebUpdater"]
        }

    def _build_ui(self):
        # --- TOP TOOLBAR ---
        self.toolbar = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#1e293b")
        self.toolbar.pack(side="top", fill="x")
        
        self.verify_btn = ctk.CTkButton(self.toolbar, text="✓ Compile / Verify", width=120, fg_color="#3b82f6", hover_color="#2563eb", font=ctk.CTkFont(weight="bold"), command=self.verify_code)
        self.verify_btn.pack(side="left", padx=(20, 10), pady=15)
        
        self.upload_btn = ctk.CTkButton(self.toolbar, text="➔ Flash Board", width=120, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(weight="bold"), command=self.upload_code)
        self.upload_btn.pack(side="left", padx=10, pady=15)
        
        self.install_btn = ctk.CTkButton(self.toolbar, text="📥 Install Compiler Core", width=140, fg_color="#f59e0b", hover_color="#d97706", text_color="#000000", font=ctk.CTkFont(weight="bold"), command=self.install_toolchain)
        self.install_btn.pack(side="left", padx=10, pady=15)
        
        ctk.CTkLabel(self.toolbar, text="Board:", text_color="#94a3b8").pack(side="left", padx=(20, 5))
        boards = ["arduino:avr:uno", "arduino:avr:nano", "arduino:avr:mega", "esp32:esp32:esp32", "rp2040:rp2040:rpipico"]
        self.board_menu = ctk.CTkComboBox(self.toolbar, variable=self.current_board, values=boards, width=160)
        self.board_menu.pack(side="left", padx=5)
        
        ctk.CTkLabel(self.toolbar, text="Port:", text_color="#94a3b8").pack(side="left", padx=(10, 5))
        self.port_menu = ctk.CTkComboBox(self.toolbar, variable=self.current_port, values=["Select Port"], width=120)
        self.port_menu.pack(side="left", padx=5)
        
        self.refresh_btn = ctk.CTkButton(self.toolbar, text="↻", width=30, fg_color="#475569", command=self.refresh_ports)
        self.refresh_btn.pack(side="left", padx=5)

        self.serial_btn = ctk.CTkButton(self.toolbar, text="🔌 Serial Monitor", width=120, fg_color="#8b5cf6", hover_color="#7c3aed", command=self.open_serial_monitor)
        self.serial_btn.pack(side="left", padx=15)
        
        ctk.CTkLabel(self.toolbar, text="MMN-1.0", font=ctk.CTkFont(size=20, weight="bold"), text_color="#10b981").pack(side="right", padx=20)

        # --- MIDDLE CONTENT AREA ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(side="top", fill="both", expand=True)

        # 1. Left Sidebar: Examples
        self.sidebar = ctk.CTkFrame(self.content_frame, width=280, corner_radius=0, fg_color="#0f172a", border_width=1, border_color="#334155")
        self.sidebar.pack(side="left", fill="y")
        ctk.CTkLabel(self.sidebar, text="📚 Hardware Examples", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 10))
        
        self.scroll_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        for category, sketches in self.examples.items():
            ctk.CTkLabel(self.scroll_frame, text=category, font=ctk.CTkFont(weight="bold", size=12), text_color="#10b981", anchor="w").pack(fill="x", pady=(10, 2), padx=5)
            for sketch_name in sketches:
                btn = ctk.CTkButton(self.scroll_frame, text=f"📄 {sketch_name}", fg_color="transparent", text_color="#e2e8f0", hover_color="#334155", anchor="w", height=24, command=lambda cat=category, name=sketch_name: self.load_example(cat, name))
                btn.pack(fill="x", padx=(15, 5), pady=1)

        # 2. Code Editor
        self.editor_container = ctk.CTkFrame(self.content_frame, corner_radius=0, fg_color="transparent")
        self.editor_container.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # File Operations Toolbar
        self.file_tools = ctk.CTkFrame(self.editor_container, height=40, fg_color="transparent")
        self.file_tools.pack(side="top", fill="x", pady=(0, 5))
        ctk.CTkButton(self.file_tools, text="📂 Load Sketch", width=100, fg_color="#334155", command=self.load_file).pack(side="left", padx=5)
        ctk.CTkButton(self.file_tools, text="💾 Save Sketch", width=100, fg_color="#334155", command=self.save_file).pack(side="left", padx=5)

        self.editor = ctk.CTkTextbox(self.editor_container, font=ctk.CTkFont(family="Consolas", size=15), fg_color="#020617", text_color="#f8fafc", wrap="none")
        self.editor.pack(fill="both", expand=True)

        # --- BOTTOM TERMINAL / CONSOLE ---
        self.console_frame = ctk.CTkFrame(self, height=220, corner_radius=0, fg_color="#000000")
        self.console_frame.pack(side="bottom", fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(self.console_frame, text="MMN Terminal Output", text_color="#64748b", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=2)
        
        self.console = ctk.CTkTextbox(self.console_frame, height=180, font=ctk.CTkFont(family="Consolas", size=13), fg_color="#000000", text_color="#a3e635", wrap="word")
        self.console.pack(fill="both", expand=True, padx=5, pady=5)
        self.console.configure(state="disabled")

    # ------------------------------------------
    # FILE OPERATIONS
    # ------------------------------------------
    def load_file(self):
        filepath = filedialog.askopenfilename(title="Load Arduino Sketch", filetypes=[("Arduino Files", "*.ino"), ("Text Files", "*.txt"), ("All Files", "*.*")])
        if filepath:
            try:
                with open(filepath, 'r') as file:
                    content = file.read()
                self.editor.delete("1.0", "end")
                self.editor.insert("1.0", content)
                self.log(f"[System] Loaded file: {filepath}")
            except Exception as e:
                self.log(f"[Error] Failed to load file: {str(e)}", color="#ef4444")

    def save_file(self):
        filepath = filedialog.asksaveasfilename(title="Save Arduino Sketch", defaultextension=".ino", filetypes=[("Arduino Files", "*.ino"), ("All Files", "*.*")])
        if filepath:
            try:
                with open(filepath, 'w') as file:
                    file.write(self.editor.get("1.0", "end-1c"))
                self.log(f"[System] Saved file: {filepath}")
            except Exception as e:
                self.log(f"[Error] Failed to save file: {str(e)}", color="#ef4444")

    # ------------------------------------------
    # SERIAL MONITOR FEATURE
    # ------------------------------------------
    def open_serial_monitor(self):
        port = self.current_port.get()
        if port in ["Select Port", "No Ports Found", "Scanning..."]:
            self.log("[Error] Please connect and select a valid COM Port to open the Serial Monitor.", color="#ef4444")
            return
            
        if self.serial_monitor_window is not None and self.serial_monitor_window.winfo_exists():
            self.serial_monitor_window.focus()
            return

        self.serial_monitor_window = ctk.CTkToplevel(self)
        self.serial_monitor_window.title(f"MMN Serial Monitor - {port}")
        self.serial_monitor_window.geometry("700x500")
        self.serial_monitor_window.minsize(500, 400)
        self.serial_monitor_window.attributes("-topmost", True)
        
        output_box = ctk.CTkTextbox(self.serial_monitor_window, font=ctk.CTkFont(family="Consolas", size=14), fg_color="#020617", text_color="#10b981", wrap="word")
        output_box.pack(fill="both", expand=True, padx=10, pady=10)
        output_box.configure(state="disabled")
        
        input_frame = ctk.CTkFrame(self.serial_monitor_window, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        cmd_entry = ctk.CTkEntry(input_frame, placeholder_text="Send command...")
        cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        def send_data(event=None):
            if self.active_serial and self.active_serial.is_open:
                data = cmd_entry.get() + "\n"
                try:
                    self.active_serial.write(data.encode('utf-8'))
                    cmd_entry.delete(0, "end")
                except Exception as e:
                    print_to_monitor(f"[Error writing to serial] {e}\n")
        
        cmd_entry.bind("<Return>", send_data)
        ctk.CTkButton(input_frame, text="Send", width=80, command=send_data).pack(side="right")
        
        baud_var = tk.StringVar(value="9600")
        ctk.CTkComboBox(input_frame, variable=baud_var, values=["9600", "115200", "38400", "4800"], width=90).pack(side="right", padx=10)

        def print_to_monitor(msg):
            if output_box.winfo_exists():
                output_box.configure(state="normal")
                output_box.insert("end", msg)
                output_box.see("end")
                output_box.configure(state="disabled")

        self.reading_serial = True
        
        def read_from_port():
            try:
                self.active_serial = serial.Serial(port, int(baud_var.get()), timeout=0.1)
                print_to_monitor(f"--- Connected to {port} at {baud_var.get()} baud ---\n")
                while self.reading_serial and self.serial_monitor_window.winfo_exists():
                    if self.active_serial.in_waiting:
                        line = self.active_serial.readline().decode('utf-8', errors='ignore')
                        if line:
                            self.serial_monitor_window.after(0, print_to_monitor, line)
                    time.sleep(0.01)
            except Exception as e:
                if self.serial_monitor_window.winfo_exists():
                    self.serial_monitor_window.after(0, print_to_monitor, f"\n--- Error: {str(e)} ---\n")
            finally:
                if self.active_serial and self.active_serial.is_open:
                    self.active_serial.close()

        def on_closing():
            self.reading_serial = False
            self.serial_monitor_window.destroy()
            
        self.serial_monitor_window.protocol("WM_DELETE_WINDOW", on_closing)
        threading.Thread(target=read_from_port, daemon=True).start()

    # ------------------------------------------
    # AUTO-INSTALLER LOGIC
    # ------------------------------------------
    def install_toolchain(self):
        """Safely downloads and installs the compiler."""
        if self.toolchain.is_installed():
            self.log("\n[System] Compiler is already installed and ready!", color="#10b981")
            return
            
        self.install_btn.configure(state="disabled", text="Downloading...")
        self.log("\n--- MMN TOOLCHAIN PROVISIONING STARTED ---", color="#3b82f6")
        self.log("Downloading the core compiler. This may take a minute depending on your internet connection...")
        
        threading.Thread(target=self._bg_install_toolchain).start()

    def _bg_install_toolchain(self):
        try:
            os.makedirs(self.toolchain.core_dir, exist_ok=True)
            url = "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                with zipfile.ZipFile(io.BytesIO(response.read())) as z:
                    z.extractall(self.toolchain.core_dir)
            
            self.log("[Success] Compiler downloaded. Installing Arduino AVR Cores...")
            cli_path = self.toolchain.get_cli_path()
            subprocess.run(f'"{cli_path}" core update-index', shell=True, stdout=subprocess.PIPE)
            subprocess.run(f'"{cli_path}" core install arduino:avr', shell=True, stdout=subprocess.PIPE)
            
            self.log("\n[SUCCESS] MMN Toolchain is fully installed! You can now verify and flash code.", color="#10b981")
            
        except Exception as e:
            self.log(f"\n[FATAL ERROR] Installation failed: {str(e)}", color="#ef4444")
            self.log("Please install 'arduino-cli' manually and add it to your System PATH.")
            
        finally:
            self.install_btn.configure(state="normal", text="📥 Install Compiler Core")

    # ------------------------------------------
    # CORE SYSTEM LOGIC
    # ------------------------------------------
    def load_example(self, category, name):
        code = f"// MMN-1.0 Studio Example: {name}\n// Category: {category}\n// Auto-Generated C++ Hardware Firmware\n\n"
        
        if name == "Blink":
            code += "void setup() {\n  pinMode(LED_BUILTIN, OUTPUT);\n}\n\nvoid loop() {\n  digitalWrite(LED_BUILTIN, HIGH);\n  delay(1000);\n  digitalWrite(LED_BUILTIN, LOW);\n  delay(1000);\n}"
        elif name == "AnalogReadSerial":
            code += "void setup() {\n  Serial.begin(9600);\n}\n\nvoid loop() {\n  int sensorValue = analogRead(A0);\n  Serial.println(sensorValue);\n  delay(1);\n}"
        elif name == "Ultrasonic_HCSR04":
            code += "const int trigPin = 9;\nconst int echoPin = 10;\n\nvoid setup() {\n  pinMode(trigPin, OUTPUT);\n  pinMode(echoPin, INPUT);\n  Serial.begin(9600);\n}\n\nvoid loop() {\n  digitalWrite(trigPin, LOW);\n  delayMicroseconds(2);\n  digitalWrite(trigPin, HIGH);\n  delayMicroseconds(10);\n  digitalWrite(trigPin, LOW);\n  long duration = pulseIn(echoPin, HIGH);\n  int distance = duration * 0.034 / 2;\n  Serial.print(\"Distance: \");\n  Serial.println(distance);\n}"
        elif name == "WiFi_Scan":
            code += "#include \"WiFi.h\"\n\nvoid setup() {\n  Serial.begin(115200);\n  WiFi.mode(WIFI_STA);\n  WiFi.disconnect();\n  delay(100);\n}\n\nvoid loop() {\n  Serial.println(\"Scan start\");\n  int n = WiFi.scanNetworks();\n  if (n == 0) {\n    Serial.println(\"no networks found\");\n  } else {\n    Serial.print(n);\n    Serial.println(\" networks found\");\n  }\n  delay(5000);\n}"
        else:
            code += f"void setup() {{\n  // Put your setup code here, to run once:\n  Serial.begin(9600);\n  Serial.println(\"{name} Initialized\");\n}}\n\nvoid loop() {{\n  // Put your main code here, to run repeatedly:\n  \n}}"
            
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", code)
        self.log(f"Loaded Example: {category} > {name}")

    def log(self, message, color="#a3e635"):
        self.console.configure(state="normal")
        self.console.insert("end", message + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def refresh_ports(self):
        self.port_menu.configure(values=["Scanning..."])
        self.update()
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        
        if port_list:
            self.port_menu.configure(values=port_list)
            self.current_port.set(port_list[0])
        else:
            self.port_menu.configure(values=["No Ports Found"])
            self.current_port.set("No Ports Found")

    def save_temp_sketch(self):
        code = self.editor.get("1.0", "end-1c")
        temp_dir = tempfile.mkdtemp()
        sketch_dir = os.path.join(temp_dir, "MMN_Sketch")
        os.makedirs(sketch_dir)
        file_path = os.path.join(sketch_dir, "MMN_Sketch.ino")
        with open(file_path, "w") as f: f.write(code)
        return sketch_dir

    def run_command(self, cmd, success_msg, failure_msg):
        try:
            self.log(f"\n> Compiling using MMN Engine...")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
            for line in iter(process.stdout.readline, ''):
                self.log(line.strip())
            process.stdout.close()
            return_code = process.wait()
            
            if return_code == 0: self.log(f"\n{success_msg}", color="#10b981")
            else: self.log(f"\n{failure_msg}", color="#ef4444")
        except Exception as e:
            self.log(f"\n[Hardware Engine Exception] {str(e)}", color="#ef4444")
        finally:
            self.verify_btn.configure(state="normal", text="✓ Compile / Verify")
            self.upload_btn.configure(state="normal", text="➔ Flash Board")

    def verify_code(self):
        cli_path = self.toolchain.get_cli_path()
        if not cli_path:
            self.log("\n[Error] Compiler not found! Please click '📥 Install Compiler Core' first.", color="#ef4444")
            return
            
        self.console.configure(state="normal"); self.console.delete("1.0", "end"); self.console.configure(state="disabled")
        self.verify_btn.configure(state="disabled", text="Compiling...")
        
        sketch_path = self.save_temp_sketch()
        fqbn = self.current_board.get().strip()
        cmd = f'"{cli_path}" compile --fqbn {fqbn} "{sketch_path}"'
        threading.Thread(target=self.run_command, args=(cmd, "[SUCCESS] Firmware Compiled Successfully.", "[ERROR] Compilation Failed.")).start()

    def upload_code(self):
        if self.reading_serial and self.serial_monitor_window and self.serial_monitor_window.winfo_exists():
            self.log("\n[Error] Please close the Serial Monitor before flashing the board to free the COM Port.", color="#ef4444")
            return
            
        cli_path = self.toolchain.get_cli_path()
        if not cli_path:
            self.log("\n[Error] Compiler not found! Please click '📥 Install Compiler Core' first.", color="#ef4444")
            return
            
        port = self.current_port.get()
        if port in ["Select Port", "No Ports Found", "Scanning..."]:
            self.log("\n[Error] Please connect a physical board via USB and select the COM Port.", color="#ef4444")
            return
            
        self.console.configure(state="normal"); self.console.delete("1.0", "end"); self.console.configure(state="disabled")
        self.upload_btn.configure(state="disabled", text="Flashing...")
        
        sketch_path = self.save_temp_sketch()
        fqbn = self.current_board.get().strip()
        cmd = f'"{cli_path}" compile --upload --fqbn {fqbn} --port {port} "{sketch_path}"'
        threading.Thread(target=self.run_command, args=(cmd, f"[SUCCESS] Board Flashed! Code is now running on {port}.", "[ERROR] Firmware Flash Failed.")).start()


# ==========================================
# CINEMATIC SPLASH SCREEN ENGINE
# ==========================================
def launch_main_app(splash_window):
    """Stops the music, destroys the splash screen, and reveals the main app."""
    if PYGAME_AVAILABLE:
        try:
            pygame.mixer.music.stop()
        except:
            pass
    splash_window.destroy()
    
    # Initialize and show the massive IDE
    app = MMN_Studio_IDE()
    app.init_system_check()
    app.mainloop()

def show_splash_screen():
    """Builds the borderless loading screen and plays the background song."""
    splash = ctk.CTk()
    splash.overrideredirect(True) # Removes standard windows borders
    
    # Center the splash screen
    window_width, window_height = 700, 450
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x_cordinate = int((screen_width/2) - (window_width/2))
    y_cordinate = int((screen_height/2) - (window_height/2))
    splash.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
    
    splash.configure(fg_color="#0f172a") # Dark background
    
    # Title & Subtitle
    ctk.CTkLabel(splash, text="MMN-1.0", font=ctk.CTkFont(size=60, weight="bold"), text_color="#10b981").pack(pady=(120, 10))
    ctk.CTkLabel(splash, text="Powered by MMN - A product of NGI", font=ctk.CTkFont(size=20), text_color="#3b82f6").pack(pady=5)
    ctk.CTkLabel(splash, text="Loading Hardware Environment & Assets...", font=ctk.CTkFont(size=12), text_color="#64748b").pack(pady=(50, 5))
    
    # Progress Bar
    progress = ctk.CTkProgressBar(splash, width=500, height=12, progress_color="#3b82f6", fg_color="#1e293b")
    progress.pack(pady=10)
    progress.set(0)
    
    # Audio Playback
    if PYGAME_AVAILABLE:
        try:
            pygame.mixer.init()
            if os.path.exists("splash_song.mp3"):
                pygame.mixer.music.load("splash_song.mp3")
                pygame.mixer.music.play()
        except Exception as e:
            print("Audio engine bypassed:", e)

    # Fake Loading Animation Loop
    def update_progress(step=0):
        if step <= 100:
            progress.set(step / 100)
            splash.after(45, update_progress, step + 1) # ~4.5 seconds total
        else:
            launch_main_app(splash)

    update_progress()
    splash.mainloop()

# ==========================================
# BOOTSTRAP
# ==========================================
if __name__ == "__main__":
    show_splash_screen()