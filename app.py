import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import subprocess
from intelhex import IntelHex
import os
from PIL import Image, ImageTk  # PIL is actually installed as Pillow
import sys
import tempfile
import shutil

class FlashToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Microcontroller Flash Tool")
        self.root.geometry("570x480")  # Increased height for new frame
        self.root.resizable(False, False)

        self.tool_path = self.detect_tool_path()
        self.file_path = tk.StringVar()
        self.output_hex_name = tk.StringVar(value="output.hex")  # Default output name
        self.eeprom_entries = []
        self.multi_byte_entries = {}  # Track entries that need byte splitting
        self.EEPROM_START_ADDRESS = 0x7F01  # Skip init byte
        self.checkbox_vars = []  # Thêm list để lưu các BooleanVar của checkbox

        # Khởi tạo tooltips
        self.tooltips = {}

        # File selection frame
        file_frame = ttk.LabelFrame(root, text="File Selection")
        file_frame.pack(fill="x", padx=5, pady=5)
        
        # Make frame use grid weights
        file_frame.grid_columnconfigure(1, weight=1)
        
        # Input hex row
        tk.Label(file_frame, text="Hex File:", width=10).grid(row=0, column=0, padx=5, pady=5)
        tk.Entry(file_frame, textvariable=self.file_path).grid(row=0, column=1, sticky="ew", padx=5)
        browse_btn = ttk.Button(file_frame, text="Browse", command=self.browse_file, width=10)
        browse_btn.grid(row=0, column=2, padx=5)
        
        # Output hex row - match style with input row
        tk.Label(file_frame, text="Output Hex:", width=10).grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(file_frame, textvariable=self.output_hex_name).grid(row=1, column=1, sticky="ew", padx=5)
        gen_btn = ttk.Button(file_frame, text="Generate", command=self.generate_hex, width=10)
        gen_btn.grid(row=1, column=2, padx=5)

        # Connect status row
        status_frame = ttk.Frame(file_frame)
        status_frame.grid(row=2, column=0, columnspan=3, sticky="e", padx=5, pady=(0,5))
        self.connect_status = tk.Label(status_frame, text="Status: Disconnected", fg="red")
        self.connect_status.pack(side="left")
        self.mcu_info = tk.Label(status_frame, text="")
        self.mcu_info.pack(side="left", padx=(5,0))

        # Control buttons frame
        btn_frame = ttk.Frame(root)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        # Left side buttons
        ttk.Button(btn_frame, text="Flash", command=self.flash_microcontroller).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Erase", command=self.erase_microcontroller).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Reset", command=self.reset_microcontroller).pack(side="left", padx=5)
        
        # Fixed width spacer to create consistent spacing
        spacer = ttk.Frame(btn_frame, width=5)  # Width matches padx of other buttons
        spacer.pack(side="left")
        spacer.pack_propagate(False)  # Prevent the frame from shrinking
        
        # Right side buttons
        ttk.Button(btn_frame, text="Save & Flash", command=self.save_and_flash).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Connect", command=self.connect_device).pack(side="left", padx=5)

        # EEPROM data frames
        left_frame = ttk.LabelFrame(root, text="Parameters Setup")
        left_frame.pack(side="left", fill="both", expand=True, padx=1, pady=1)

        right_frame = ttk.LabelFrame(root, text="Mode Setup") 
        right_frame.pack(side="left", fill="both", expand=True, padx=1, pady=1)

        # Configure columns
        left_frame.grid_columnconfigure(0, minsize=65)
        left_frame.grid_columnconfigure(1, minsize=30)
        right_frame.grid_columnconfigure(0, minsize=100)
        right_frame.grid_columnconfigure(1, minsize=100)

        self.eeprom_entries = []
        row_left = row_right = 0

        # Map EEPROM fields in exact struct order
        # 1. time[2][2] array
        self.add_entry_field(left_frame, row_left, "Chạy lạnh CL :", 1, is_uint16=True, default="5", align="w", min_val=1, max_val=999, 
                            tooltip="Thời gian chạy lạnh CL (1-999)")
        row_left += 1
        self.add_entry_field(left_frame, row_left, "Chạy lạnh OP :", 1, is_uint16=True, default="5", align="w", min_val=1, max_val=999,
                            tooltip="Thời gian chạy lạnh OP (1-999)")
        row_left += 1
        self.add_entry_field(left_frame, row_left, "Xả đá CL :", 1, is_uint16=True, default="200", align="w", min_val=1, max_val=200,
                            tooltip="Thời gian xả đá CL (1-200)")
        row_left += 1
        self.add_entry_field(left_frame, row_left, "Xả đá OP :", 1, is_uint16=True, default="60", align="w", min_val=1, max_val=60,
                            tooltip="Thời gian xả đá OP (1-60)")
        row_left += 1

        # 2. delayST, ST
        self.add_entry_field(left_frame, row_left, "Delay ST(100ms) :", 1, is_uint8=True, default="70", align="w", min_val=1, max_val=999,
                            tooltip="Thời gian delay relay (1-999, đơn vị 0.1s)")
        row_left += 1
        self.add_entry_field(left_frame, row_left, "ST(100ms) :", 1, is_uint8=True, default="50", align="w", min_val=1, max_val=999,
                            tooltip="Thời gian bật relay (1-999, đơn vị 0.1s)")
        row_left += 1

        # 3. Mode settings
        self.add_entry_field(right_frame, row_right, "Mode DF :", 1, is_combo=True, values=["OFF", "ON"], default="OFF", align="w",
                            tooltip="ON/OFF: Bật/tắt điều khiển kéo theo Relay 3")
        row_right += 1
        self.add_entry_field(right_frame, row_right, "Mode END :", 1, is_combo=True, values=["OFF", "ON"], default="ON", align="w",
                            tooltip="ON/OFF: Bật tắt Relay 3 tại end OP chạy lạnh")
        row_right += 1
        self.add_entry_field(right_frame, row_right, "Mode chạy lạnh :", 1, is_combo=True, values=["CL", "OP"], default="CL", align="w",
                            tooltip="CL: Mặc định CL, OP: Mặc định OP")
        row_right += 1
        self.add_entry_field(right_frame, row_right, "Mode xả đá :", 1, is_combo=True, values=["CL", "OP"], default="CL", align="w",
                            tooltip="CL: Xả đá theo CL, OP: Xả đá theo OP")
        row_right += 1
        self.add_entry_field(right_frame, row_right, "Mode SL :", 1, is_combo=True, values=["LCD", "LED"], default="LCD", align="w",
                            tooltip="LCD: Hiển thị LCD, LED: Hiển thị LED")
        row_right += 1

        # 4. lock_time through tried_time
        self.add_entry_field(left_frame, row_left, "Auto lock (Lock time) :", 1, is_uint16=True, default="6", align="w", min_val=1, max_val=999,
                            tooltip="Thời gian tự động khóa (1-999)")
        row_left += 1
        self.add_entry_field(left_frame, row_left, "Độ sáng led xanh :", 1, is_uint8=True, default="0", align="w", min_val=0, max_val=7,
                            tooltip="Điều chỉnh độ sáng LED xanh (0-7)")
        row_left += 1
        self.add_entry_field(left_frame, row_left, "Độ sáng led đỏ :", 1, is_uint8=True, default="0", align="w", min_val=0, max_val=7,
                            tooltip="Điều chỉnh độ sáng LED đỏ (0-7)")
        row_left += 1
        self.add_entry_field(right_frame, row_right, "Mode HCF :", 1, is_combo=True, values=["CF", "H"], default="CF", align="w",
                            tooltip="CF: Mode Cold Fast, H: Mode Hot")
        row_right += 1
        self.add_entry_field(right_frame, row_right, "On time Mode LED :", 1, is_combo=True, values=["1", "2"], default="1", align="w",
                            tooltip="1: Mode LED 1, 2: Mode LED 2")
        row_right += 1
        self.add_entry_field(right_frame, row_right, "Touch Num :", 1, is_combo=True, values=["1", "2"], default="1", align="w",
                            tooltip="1: Chạm 1 lần, 2: Chạm 2 lần")
        row_right += 1
        self.add_entry_field(left_frame, row_left, "Try time :", 1, is_uint16=True, default="1", align="w", min_val=1, max_val=999, has_unit_toggle=True,
                            tooltip="Thời gian thử (1-999 giờ/ngày)")
        row_left += 1

        # Note: check_box[6] is handled by the checkboxes
        # Note: shutdown and tried_time are handled as extra fields

        # Add contact text and QR code at bottom right
        try:
            # Create a container frame to hold both elements
            contact_frame = ttk.Frame(right_frame)
            contact_frame.grid(row=row_right + 1, column=0, columnspan=2, pady=10, sticky="e")
            
            # Add support contact text
            contact_label = tk.Label(contact_frame, text="Liên hệ hỗ trợ:", font=("Arial", 10))
            contact_label.pack(side="left", padx=(0, 10))

            # Get QR path from bundle
            if getattr(sys, 'frozen', False):
                bundle_dir = sys._MEIPASS
            else:
                bundle_dir = os.path.dirname(os.path.abspath(__file__))
                
            qr_path = os.path.join(bundle_dir, "qr_duong.jpg")
            
            if not os.path.exists(qr_path):
                raise FileNotFoundError("Không tìm thấy file qr_duong.jpg")
                
            qr_image = Image.open(qr_path)
            qr_image = qr_image.resize((75, 75))
            qr_photo = ImageTk.PhotoImage(qr_image)
            
            qr_label = tk.Label(contact_frame, image=qr_photo)
            qr_label.image = qr_photo
            qr_label.pack(side="left", padx=(0, 5))
            
        except Exception as e:
            print(f"Lỗi khi tải QR code: {e}")

    def add_entry_field(self, parent, row, label, display_width=1, column=0, is_uint16=False, 
                       is_uint32=False, is_uint8=False, is_combo=False, values=None, default="0", 
                       align="e", min_val=None, max_val=None, has_unit_toggle=False, tooltip=None):
        lbl = tk.Label(parent, text=label)
        lbl.grid(row=row, column=column, padx=(1,1), pady=2, sticky=align)  # Thêm pady=2
        
        # Add tooltip if provided
        if tooltip:
            self.create_tooltip(lbl, tooltip)

        frame = ttk.Frame(parent)
        frame.grid(row=row, column=column+1, pady=2, sticky="w")  # Thêm pady=2
        
        if is_combo:
            entry = ttk.Combobox(frame, width=6, values=values, state="readonly")  # Increased from 5
            entry.pack(side="left")
            entry.set(default)
            self.eeprom_entries.append(entry)
            
            # Add checkbox with consistent spacing
            if "Mode" in label and "On time" not in label and "chạy lạnh" not in label and "xả đá" not in label:
                var = tk.BooleanVar()
                chk = tk.Checkbutton(frame, variable=var)
                chk.pack(side="left", padx=(10,0))
                lbl_status = tk.Label(frame, text="hide")
                lbl_status.pack(side="left", padx=(2,0))
                var.trace('w', lambda *args, l=lbl_status: 
                         l.config(text="show" if var.get() else "hide"))
                self.checkbox_vars.append(var)  # Thêm vào list để map sau
            
        else:
            entry = tk.Entry(frame, width=8)
            entry.pack(side="left")
            entry.delete(0, tk.END)
            entry.insert(0, default)
            
            # Add unit label for xả đá OP with matching spacing
            if "Xả đá OP" in label:
                var = tk.BooleanVar()
                chk = tk.Checkbutton(frame, variable=var)
                chk.pack(side="left", padx=(10,0))
                lbl_unit = tk.Label(frame, text="minute")
                lbl_unit.pack(side="left", padx=(2,0))
                var.trace('w', lambda *args, l=lbl_unit: 
                         l.config(text="second" if var.get() else "minute"))
                self.checkbox_vars.append(var)  # Thêm vào list để map
            
            # Add unit toggle for try time
            if has_unit_toggle:
                var = tk.BooleanVar() 
                chk = tk.Checkbutton(frame, variable=var)
                chk.pack(side="left", padx=(10,0))
                lbl_unit = tk.Label(frame, text="hours")
                lbl_unit.pack(side="left", padx=(2,0))
                var.trace('w', lambda *args, l=lbl_unit: 
                         l.config(text="days" if var.get() else "hours"))
                self.checkbox_vars.append(var)  # Thêm vào list để map
            
            if min_val is not None and max_val is not None:
                entry.bind('<FocusOut>', lambda e, ent=entry, min_v=min_val, max_v=max_val, def_v=default: 
                         self.validate_entry_range(ent, min_v, max_v, def_v))
            
            if is_uint16 or is_uint32 or is_uint8:
                self.multi_byte_entries[len(self.eeprom_entries)] = {
                    'entry': entry,
                    'bytes': 4 if is_uint32 else (2 if is_uint16 else 1),
                    'default': default  # Store default value
                }
                # Add placeholder entries for the actual bytes
                for _ in range(4 if is_uint32 else (2 if is_uint16 else 1)):
                    self.eeprom_entries.append(None)
            else:
                self.eeprom_entries.append(entry)

    def create_tooltip(self, widget, text):
        def enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
            label.pack()
            
            self.tooltips[widget] = tooltip
            
        def leave(event):
            if widget in self.tooltips:
                self.tooltips[widget].destroy()
                del self.tooltips[widget]
                
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def validate_entry_range(self, entry, min_val, max_val, default):
        """Validate and correct entry value to be within min-max range"""
        try:
            value = int(entry.get())
            if value < min_val:
                value = min_val
            elif value > max_val:
                value = max_val
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
        except ValueError:
            entry.delete(0, tk.END)
            entry.insert(0, default)

    def get_entry_bytes(self, value, num_bytes):
        """Convert decimal input to specified number of bytes in big endian"""
        try:
            value = int(value)
            # Check value ranges based on number of bytes
            if num_bytes == 1 and value > 255:  # uint8_t
                return [0] * num_bytes
            elif num_bytes == 2 and value > 65535:  # uint16_t 
                return [0] * num_bytes
            elif num_bytes == 4 and value > 4294967295:  # uint32_t
                return [0] * num_bytes
                
            bytes_list = []
            for i in range(num_bytes):
                bytes_list.append(value & 0xFF)
                value >>= 8
            return bytes_list[::-1]  # Reverse list for big endian
        except ValueError:
            return [0] * num_bytes

    def detect_tool_path(self):
        try:
            # Get path when running as exe
            if getattr(sys, 'frozen', False):
                bundle_dir = sys._MEIPASS
            else:
                bundle_dir = os.path.dirname(os.path.abspath(__file__))
                
            tool_path = os.path.join(bundle_dir, "NuLink_8051OT.exe")
            
            if os.path.exists(tool_path):
                # Extract tool to temp folder
                temp_dir = tempfile.gettempdir()
                temp_tool = os.path.join(temp_dir, "NuLink_8051OT.exe") 
                shutil.copy2(tool_path, temp_tool)
                return temp_tool
                
            # Fallback to default install path
            default_path = r"C:\Program Files (x86)\Nuvoton Tools\NuLink Command Tool\NuLink_8051OT.exe"
            if os.path.exists(default_path):
                return default_path
                
            messagebox.showerror("Error", "NuLink tool không tìm thấy. Vui lòng chọn file NuLink_8051OT.exe")
            return filedialog.askopenfilename(filetypes=[("Executable files", "*.exe")])
            
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi khi tải NuLink tool: {e}")
            return None

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Hex files", "*.hex")])
        if file_path:
            self.file_path.set(file_path)
            messagebox.showinfo("Success", "Hex file selected")

    def save_and_flash(self):
        hex_file_path = self.file_path.get()
        if not hex_file_path:
            messagebox.showerror("Error", "Please select a HEX file first.")
            return

        try:
            # Process all entries and convert multi-byte values
            new_data = []
            current_idx = 0
            
            # Add init byte = 2 at 0x7F00
            new_data.append(2)
            
            while current_idx < len(self.eeprom_entries):
                if isinstance(self.eeprom_entries[current_idx], ttk.Combobox):
                    # Convert combo values to numbers
                    value = self.eeprom_entries[current_idx].get()
                    if value in ["OP", "LED", "ON"]:  # Normal cases
                        value = 1
                    elif value == "CF":  # Special case for HCF mode
                        value = 1
                    elif value == "H":
                        value = 0
                    elif value == "2":  # Special case for On time
                        value = 1
                    elif value == "1":
                        value = 0
                    else:  # CL, LCD, OFF
                        value = 0
                    new_data.append(value)
                    current_idx += 1
                elif current_idx in self.multi_byte_entries:
                    entry_info = self.multi_byte_entries[current_idx]
                    value = entry_info['entry'].get().strip()
                    bytes_list = self.get_entry_bytes(value, entry_info['bytes'])
                    new_data.extend(bytes_list)
                    current_idx += entry_info['bytes']
                else:
                    if self.eeprom_entries[current_idx]:
                        value = self.eeprom_entries[current_idx].get().strip()
                        new_data.append(int(value, 16) if value else 0)
                    current_idx += 1

            # Add checkbox values after try time
            for var in self.checkbox_vars:
                new_data.append(1 if var.get() else 0)
                current_idx += 1

            # Add extra uint8 and uint32 values = 0
            new_data.append(0)  # uint8_t = 0
            new_data.extend([0, 0, 0, 0])  # uint32_t = 0
            
            # Continue with existing hex file handling...
            hex_file = IntelHex(hex_file_path)
            
            # Write all data including init byte
            for i, value in enumerate(new_data):
                addr = self.EEPROM_START_ADDRESS - 1 + i  # Start from 0x7F00
                hex_file[addr] = value

            # Create temporary file with merged data
            temp_file = hex_file_path.replace('.hex', '_merged.hex')
            hex_file.write_hex_file(temp_file)

            # Flash the merged file
            if self.tool_path:
                self.erase_microcontroller()
                self.reset_microcontroller()
                command = [self.tool_path, "-w", "APROM", temp_file]
                result = self.run_command(command)
                if result:
                    messagebox.showinfo("Success", "File flashed successfully!")
                
            # Clean up
            if os.path.exists(temp_file):
                os.remove(temp_file)

        except ValueError as e:
            messagebox.showerror("Error", "Invalid input value")
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge and flash:\n{e}")

    def erase_microcontroller(self):
        if self.tool_path:
            command = [self.tool_path, "-e", "ALL"]
            self.run_command(command)

    def reset_microcontroller(self):
        if self.tool_path:
            command = [self.tool_path, "-reset"]
            self.run_command(command)

    def flash_microcontroller(self):
        self.erase_microcontroller()
        self.reset_microcontroller()
        hex_file = self.file_path.get()
        if hex_file and self.tool_path:
            command = [self.tool_path, "-w", "APROM", hex_file]
            self.run_command(command)

    def connect_device(self):
        try:
            command = [self.tool_path, "-p"]
            info = self.run_command(command)
            if info:
                # Extract MCU info after second >>>
                info_parts = info.split('>>>')
                if len(info_parts) > 2:
                    # Get only alphanumeric chars, limit to 9 chars
                    mcu_info = ''.join(c for c in info_parts[2] if c.isalnum())[:9]
                    self.connect_status.config(text="Status: Connected", fg="green")
                    self.mcu_info.config(text=f"MCU: {mcu_info}")
                else:
                    self.connect_status.config(text="Status: Connected", fg="green")
                    self.mcu_info.config(text="")
            else:
                self.connect_status.config(text="Status: Disconnected", fg="red")
                self.mcu_info.config(text="")
        except Exception as e:
            self.connect_status.config(text="Status: Disconnected", fg="red")
            self.mcu_info.config(text="")

    def get_info(self):
        pass

    def run_command(self, command):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(command, 
                                  check=True,
                                  capture_output=True,
                                  text=True,
                                  startupinfo=startupinfo)
            return result.stdout
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", e.stderr)
            return ""

    def generate_hex(self):
        """Generate merged hex file without flashing"""
        try:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".hex",
                initialfile=self.output_hex_name.get(),
                filetypes=[("Hex files", "*.hex")]
            )
            if not save_path:
                return

            hex_file_path = self.file_path.get()
            if not hex_file_path:
                messagebox.showerror("Error", "Please select input HEX file first.")
                return

            # Process entries and create merged hex file
            new_data = []
            current_idx = 0
            new_data.append(2)  # Init byte
            
            # Reuse existing conversion logic
            while current_idx < len(self.eeprom_entries):
                if isinstance(self.eeprom_entries[current_idx], ttk.Combobox):
                    # Convert combo values to numbers
                    value = self.eeprom_entries[current_idx].get()
                    if value in ["OP", "LED", "ON"]:  # Normal cases
                        value = 1
                    elif value == "CF":  # Special case for HCF mode
                        value = 1
                    elif value == "H":
                        value = 0
                    elif value == "2":  # Special case for On time
                        value = 1
                    elif value == "1":
                        value = 0
                    else:  # CL, LCD, OFF
                        value = 0
                    new_data.append(value)
                    current_idx += 1
                elif current_idx in self.multi_byte_entries:
                    entry_info = self.multi_byte_entries[current_idx]
                    value = entry_info['entry'].get().strip()
                    bytes_list = self.get_entry_bytes(value, entry_info['bytes'])
                    new_data.extend(bytes_list)
                    current_idx += entry_info['bytes']
                else:
                    if self.eeprom_entries[current_idx]:
                        value = self.eeprom_entries[current_idx].get().strip()
                        new_data.append(int(value, 16) if value else 0)
                    current_idx += 1

            # Add checkbox values after try time
            for var in self.checkbox_vars:
                new_data.append(1 if var.get() else 0)
                current_idx += 1
                
            # Add extra uint8 and uint32 values = 0  
            new_data.append(0)  # uint8_t = 0
            new_data.extend([0, 0, 0, 0])  # uint32_t = 0

            hex_file = IntelHex(hex_file_path)
            for i, value in enumerate(new_data):
                addr = self.EEPROM_START_ADDRESS - 1 + i
                hex_file[addr] = value

            hex_file.write_hex_file(save_path)
            messagebox.showinfo("Success", f"Generated hex file: {save_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate hex file:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FlashToolGUI(root)
    root.mainloop()