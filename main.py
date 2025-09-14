from fastapi import FastAPI, Request    
from fastapi.middleware.cors import CORSMiddleware
import psutil
import GPUtil
import platform
import subprocess
import os 
import requests
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # ✅ permite cualquier origen
    allow_credentials=True,
    allow_methods=["*"],        # permite GET, POST, PUT, DELETE...
    allow_headers=["*"]         # permite cualquier cabecera
)

# --- Endpoints ---
@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/mystats")
def read_mystats():
    cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
    cpu_times = psutil.cpu_times_percent(interval=1, percpu=False)

    memory = psutil.virtual_memory()
    memory_total_gb = round(memory.total / (1024 ** 3), 2)
    memory_used_gb = round(memory.used / (1024 ** 3), 2)
    memory_percent = memory.percent

    gpus = GPUtil.getGPUs()
    gpu_stats = []
    for gpu in gpus:
        gpu_stats.append({
            "id": gpu.id,
            "name": gpu.name,
            "gpu_percent": round(gpu.load * 100, 2),
            "gpu_mem_total_gb": round(gpu.memoryTotal / 1024, 2),
            "gpu_mem_used_gb": round(gpu.memoryUsed / 1024, 2),
            "gpu_mem_percent": round(gpu.memoryUtil * 100, 2),
            "temperature": gpu.temperature
        })

    temps = psutil.sensors_temperatures()
    motherboard_temp = None
    if "acpitz" in temps:
        acpitz_entries = [entry.current for entry in temps["acpitz"] if entry.current is not None]
        if acpitz_entries:
            motherboard_temp = round(sum(acpitz_entries) / len(acpitz_entries), 2)

    return {
        "cpu": {
            "percent": cpu_percent,
            "times": {
                "user": cpu_times.user,
                "system": cpu_times.system,
                "idle": cpu_times.idle,
                "iowait": getattr(cpu_times, "iowait", None)
            }
        },
        "memory": {
            "total_gb": memory_total_gb,
            "used_gb": memory_used_gb,
            "percent": memory_percent
        },
        "gpu": gpu_stats if gpu_stats else "GPU unavailable",
        "motherboard_temperature": motherboard_temp
    }
def get_device_name():
    system = platform.system()

    # --- Windows ---
    if system == "Windows":
        try:
            output = subprocess.check_output(
                ["wmic", "computersystem", "get", "manufacturer,model"],
                text=True
            ).splitlines()
            if len(output) >= 2:
                parts = output[1].split()
                manufacturer = parts[0]
                model = " ".join(parts[1:]) if len(parts) > 1 else ""
                return f"{manufacturer} {model}"
        except Exception:
            return platform.node()  # fallback to hostname

    # --- Linux (no sudo) ---
    elif system == "Linux":
        manufacturer = ""
        model = ""
        try:
            if os.path.exists("/sys/class/dmi/id/sys_vendor"):
                with open("/sys/class/dmi/id/sys_vendor") as f:
                    manufacturer = f.read().strip()
            if os.path.exists("/sys/class/dmi/id/product_name"):
                with open("/sys/class/dmi/id/product_name") as f:
                    model = f.read().strip()
            if manufacturer or model:
                return f"{manufacturer} {model}".strip()
        except Exception:
            return platform.node()

    # --- MacOS ---
    elif system == "Darwin":
        try:
            output = subprocess.check_output(
                ["system_profiler", "SPHardwareDataType"], text=True
            )
            manufacturer = "Apple"
            model = ""
            for line in output.splitlines():
                if "Model Name" in line:
                    model = line.split(":")[1].strip()
            return f"{manufacturer} {model}".strip()
        except Exception:
            return platform.node()

    # --- Fallback ---
    return platform.node()


@app.get("/device-name")
def device_name():
    device_name = get_device_name()
    hostname = platform.node()
    return {
        "device_name": device_name,
        "hostname": hostname
    }

#Get the global computer stats 
@app.get("/systemstats")
def system_stats():
    response = requests.get("http://127.0.0.1:8080/sys")
    data = response.json()

    processed_data = {
        "cpu_avg": round(data["cpu_avg"], 1),
        "gpu": data["gpu"],  
        "ram_usage_percent": round(data["ram_usage_percent"], 1)
    }

    return processed_data
#Get all the computers stats connected in the same network
@app.get("/allsystem")
def all_system_stats():
    response = requests.get("http://127.0.0.1:8080/allsys")
    return response.json()
