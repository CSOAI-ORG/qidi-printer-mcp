"""
QIDI 3D Printer MCP Server
Controls QIDI 4 Max Combo (and other Klipper/Moonraker printers) via Moonraker REST API.
Built by MEOK AI Labs for Sovereign Temple v3.0.
"""

import os
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote
from mcp.server.fastmcp import FastMCP

PRINTER_IP = os.environ.get("QIDI_PRINTER_IP", "192.168.1.100")
BASE_URL = "http://{}:7125".format(PRINTER_IP)

mcp = FastMCP("qidi-printer", instructions="QIDI 3D Printer MCP Server — controls QIDI 4 Max Combo via Moonraker API")


def _get(path):
    """HTTP GET to Moonraker and return parsed JSON."""
    try:
        url = BASE_URL + path
        req = Request(url, method="GET")
        req.add_header("Accept", "application/json")
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError("Moonraker HTTP {}: {} — {}".format(e.code, e.reason, body))
    except URLError as e:
        raise RuntimeError("Cannot reach printer at {}: {}".format(BASE_URL, e.reason))


def _post(path, data=None):
    """HTTP POST to Moonraker and return parsed JSON."""
    try:
        url = BASE_URL + path
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
            req = Request(url, data=payload, method="POST")
            req.add_header("Content-Type", "application/json")
        else:
            req = Request(url, data=b"", method="POST")
        req.add_header("Accept", "application/json")
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            if raw.strip():
                return json.loads(raw)
            return {"status": "ok"}
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError("Moonraker HTTP {}: {} — {}".format(e.code, e.reason, body))
    except URLError as e:
        raise RuntimeError("Cannot reach printer at {}: {}".format(BASE_URL, e.reason))


@mcp.tool()
def printer_status() -> dict:
    """Get full printer status: state, temperatures, and print progress. No parameters needed."""
    info = _get("/printer/info")
    temps = _get("/printer/objects/query?heater_bed&extruder")
    stats = _get("/printer/objects/query?print_stats")

    state = info.get("result", {}).get("state", "unknown")
    state_msg = info.get("result", {}).get("state_message", "")

    temp_data = temps.get("result", {}).get("status", {})
    bed = temp_data.get("heater_bed", {})
    ext = temp_data.get("extruder", {})

    print_data = stats.get("result", {}).get("status", {}).get("print_stats", {})

    return {
        "state": state,
        "state_message": state_msg,
        "bed_temp": bed.get("temperature", 0),
        "bed_target": bed.get("target", 0),
        "nozzle_temp": ext.get("temperature", 0),
        "nozzle_target": ext.get("target", 0),
        "print_state": print_data.get("state", "standby"),
        "filename": print_data.get("filename", ""),
        "print_duration_s": print_data.get("print_duration", 0),
        "total_duration_s": print_data.get("total_duration", 0),
        "printer_ip": PRINTER_IP,
    }


@mcp.tool()
def get_temperatures() -> dict:
    """Get current bed and nozzle temperatures with targets."""
    temps = _get("/printer/objects/query?heater_bed&extruder")
    temp_data = temps.get("result", {}).get("status", {})
    bed = temp_data.get("heater_bed", {})
    ext = temp_data.get("extruder", {})
    return {
        "bed_temp": bed.get("temperature", 0),
        "bed_target": bed.get("target", 0),
        "nozzle_temp": ext.get("temperature", 0),
        "nozzle_target": ext.get("target", 0),
    }


@mcp.tool()
def start_print(filename: str) -> dict:
    """Start printing a gcode file already uploaded to the printer.
    Args:
        filename: Name of the gcode file on the printer (e.g. 'benchy.gcode').
    """
    result = _post("/printer/print/start?filename={}".format(quote(filename)))
    return {"status": "print_started", "filename": filename, "response": result}


@mcp.tool()
def pause_print() -> dict:
    """Pause the current print job."""
    result = _post("/printer/print/pause")
    return {"status": "print_paused", "response": result}


@mcp.tool()
def resume_print() -> dict:
    """Resume a paused print job."""
    result = _post("/printer/print/resume")
    return {"status": "print_resumed", "response": result}


@mcp.tool()
def cancel_print() -> dict:
    """Cancel the current print job. The printer will stop and cool down."""
    result = _post("/printer/print/cancel")
    return {"status": "print_cancelled", "response": result}


@mcp.tool()
def list_files() -> dict:
    """List all gcode files uploaded to the printer."""
    result = _get("/server/files/list")
    files = result.get("result", [])
    summary = []
    for f in files:
        entry = {
            "filename": f.get("filename", f.get("path", "unknown")),
            "size_bytes": f.get("size", 0),
        }
        modified = f.get("modified", None)
        if modified:
            entry["modified"] = modified
        summary.append(entry)
    return {"file_count": len(summary), "files": summary}


@mcp.tool()
def send_gcode(command: str) -> dict:
    """Send a raw G-code command to the printer.
    Common commands:
      G28 — home all axes
      G1 X100 Y100 Z50 F3000 — move to position
      M104 S200 — set nozzle temp to 200C
      M140 S60 — set bed temp to 60C
      M106 S255 — fan on full
      M107 — fan off
    Args:
        command: The G-code command string to send.
    """
    result = _post("/printer/gcode/script?script={}".format(quote(command)))
    return {"status": "gcode_sent", "command": command, "response": result}


@mcp.tool()
def print_progress() -> dict:
    """Get current print progress: percentage complete, elapsed time, estimated time remaining, and filename."""
    stats = _get("/printer/objects/query?print_stats&virtual_sdcard")
    status = stats.get("result", {}).get("status", {})
    print_stats = status.get("print_stats", {})
    vsd = status.get("virtual_sdcard", {})

    progress = vsd.get("progress", 0)
    duration = print_stats.get("print_duration", 0)

    # Estimate remaining time from progress
    remaining = 0
    if progress > 0.01:
        total_est = duration / progress
        remaining = max(0, total_est - duration)

    return {
        "filename": print_stats.get("filename", ""),
        "state": print_stats.get("state", "standby"),
        "progress_pct": round(progress * 100, 1),
        "elapsed_s": round(duration, 0),
        "remaining_s": round(remaining, 0),
    }


@mcp.tool()
def preheat(bed_temp: int = 60, nozzle_temp: int = 220) -> dict:
    """Preheat the printer bed and nozzle to target temperatures.
    Defaults are PLA-friendly: bed 60C, nozzle 220C.
    Args:
        bed_temp: Target bed temperature in Celsius (default 60).
        nozzle_temp: Target nozzle temperature in Celsius (default 220).
    """
    if bed_temp < 0 or bed_temp > 120:
        raise ValueError("Bed temp must be 0-120C, got {}".format(bed_temp))
    if nozzle_temp < 0 or nozzle_temp > 300:
        raise ValueError("Nozzle temp must be 0-300C, got {}".format(nozzle_temp))

    _post("/printer/gcode/script?script={}".format(quote("M140 S{}".format(bed_temp))))
    _post("/printer/gcode/script?script={}".format(quote("M104 S{}".format(nozzle_temp))))
    return {
        "status": "preheating",
        "bed_target": bed_temp,
        "nozzle_target": nozzle_temp,
    }


def main():
    """Entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
