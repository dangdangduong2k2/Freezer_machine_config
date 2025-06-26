# ❄️ Freezer Machine Configuration Editor

This Python-based tool allows users to **edit configuration parameters** (such as temperature limits, speed levels, operating modes, etc.) directly inside the **Intel HEX firmware file** of a freezer controller. No UART, bootloader, or serial protocol is required.

---

## 📦 Key Features

- 🧠 Modify device settings by patching the `.hex` file
- 📂 Load Intel HEX files and locate config memory region
- ✏️ Change parameters via a simple Python interface
- 💾 Save updated `.hex` for direct flashing to MCU
- ❌ No need for UART/Modbus/protocol communication

---

## ⚙️ How It Works

Instead of connecting to the freezer machine and using a communication protocol, this tool lets you **manually change embedded parameters** by editing specific bytes inside the `.hex` firmware file.

Example use cases:
- Update default temperature threshold
- Change motor speed presets
- Enable/disable features at boot

---

## 🧰 Requirements

- Python ≥ 3.7  
- Packages: `intelhex`

### 📥 Install dependencies

```bash
pip install intelhex
