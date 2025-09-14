from fastapi import FastAPI, Request    
from fastapi.middleware.cors import CORSMiddleware
import psutil
import GPUtil
import platform
import subprocess
import os 
import requests
from dotenv import load_dotenv

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # ✅ permite cualquier origen
    allow_credentials=True,
    allow_methods=["*"],        # permite GET, POST, PUT, DELETE...
    allow_headers=["*"]         # permite cualquier cabecera
)

load_dotenv()

TANDEM_API_URL = "https://api.tandemn.com/api/v1/chat/completions"
TANDEM_API_KEY = os.getenv("TANDEM_API_KEY")



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

@app.post("/ai")
async def ai_endpoint(request: Request):
    body = await request.json()

    headers = {
        "Authorization": f"Bearer {TANDEM_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(TANDEM_API_URL, headers=headers, json=body)

    try:
        return response.json()
    except Exception:
        return {
            "error": "Invalid response",
            "status": response.status_code,
            "text": response.text
        }