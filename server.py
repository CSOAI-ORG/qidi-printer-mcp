"""
QIDI 3D Printer MCP Server
Controls QIDI Max4 (and other Klipper/Moonraker printers) via the Moonraker REST API.
Built by MEOK AI Labs for Sovereign Temple v3.0.

Docstring policy: each tool states honestly whether it is READ-ONLY (idempotent, no
side effects) or MUTATING (real-world side effects on the physical printer). Do NOT
trust a mutating tool to be safe to retry blindly.
"""

import os
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote
from mcp.server.fastmcp import FastMCP
import urllib.request as _meter_urlreq
import urllib.error as _meter_urlerr

# Default to the MEOK lab printer; override with QIDI_PRINTER_IP for any other unit.
PRINTER_IP = os.environ.get("QIDI_PRINTER_IP", "192.168.50.21")
BASE_URL = "http://{}:7125".format(PRINTER_IP)

mcp = FastMCP("qidi-printer", instructions="QIDI 3D Printer MCP Server — controls a QIDI Max4 via the Moonraker API")


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


def _server_meter_check(api_key: str = "") -> dict:
    """Calls the live /verify endpoint for server-side metering. Fail-open."""
    try:
        data = json.dumps({"api_key": api_key, "tool": ""}).encode()
        req = _meter_urlreq.Request(_METER_URL, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        with _meter_urlreq.urlopen(req, timeout=2.5) as r:
            d = json.loads(r.read())
            if isinstance(d, dict) and "allowed" in d:
                return d
    except Exception:
        pass
    return {"allowed": True, "tier": "anonymous", "remaining": 200, "upgrade_url": "https://meok.ai/pricing"}


_METER_URL = "https://proofof.ai/verify"


# ─────────────────────────────── READ-ONLY tools ───────────────────────────────
# Idempotent, no side effects, safe to retry. Free tier 10/day; Pro unlimited (MEOK_API_KEY).

@mcp.tool()
def printer_status() -> dict:
    """Full printer status: state, bed/nozzle temps, and current print info.
    READ-ONLY · idempotent · no side effects."""
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
    """Current bed and nozzle temperatures with targets.
    READ-ONLY · idempotent · no side effects."""
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
def list_files() -> dict:
    """List all gcode files uploaded to the printer.
    READ-ONLY · idempotent · no side effects."""
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
def print_progress() -> dict:
    """Current print progress: % complete, elapsed, estimated remaining, filename.
    READ-ONLY · idempotent · no side effects."""
    stats = _get("/printer/objects/query?print_stats&virtual_sdcard")
    status = stats.get("result", {}).get("status", {})
    print_stats = status.get("print_stats", {})
    vsd = status.get("virtual_sdcard", {})
    progress = vsd.get("progress", 0)
    duration = print_stats.get("print_duration", 0)
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
def box_humidity() -> dict:
    """QIDI Box filament-dryer humidity, temperature, and drying state (AHT20 sensor).
    READ-ONLY · idempotent · no side effects. Use before a moisture-sensitive print
    (nylon / PA-CF / PETG) to confirm the filament is dry.
    Returns: humidity_pct (% RH), box_temp_c, drying_active (bool), printer_ip."""
    q = _get("/printer/objects/query?aht20_f%20heater_box1&box_extras")
    st = q.get("result", {}).get("status", {})
    aht = st.get("aht20_f heater_box1", {})
    drying = st.get("box_extras", {}).get("box_drying_state", {})
    return {
        "humidity_pct": aht.get("humidity"),
        "box_temp_c": aht.get("temperature"),
        "drying_active": bool((drying.get("box1") or {}).get("dry_state", 0)),
        "printer_ip": PRINTER_IP,
    }


@mcp.tool()
def humidity_gate(max_humidity: float = 20.0, material: str = "PA-CF") -> dict:
    """Pre-print humidity gate — call BEFORE starting a moisture-sensitive print.
    READ-ONLY / advisory: reads Box humidity and returns a GO / NO-GO verdict so a
    wet-filament print can't start by accident. It does NOT stop the printer itself —
    only call start_print when safe_to_print is True. Fail-safe: returns NO-GO/UNKNOWN
    if the Box can't be read (a network blip can't green-light a wet print).
    Args:
        max_humidity: max safe % RH (default 20.0; nylon / PA-CF want < 20%).
        material: filament name, for the advice string.
    Returns: safe_to_print (bool), humidity_pct, threshold, verdict, advice."""
    try:
        q = _get("/printer/objects/query?aht20_f%20heater_box1")
        aht = q.get("result", {}).get("status", {}).get("aht20_f heater_box1", {})
        h = aht.get("humidity")
    except Exception as e:
        return {"safe_to_print": False, "verdict": "UNKNOWN", "humidity_pct": None,
                "advice": "Could not read Box humidity ({}). Do not start a CF print blind.".format(e)}
    if h is None:
        return {"safe_to_print": False, "verdict": "UNKNOWN", "humidity_pct": None,
                "advice": "Box humidity sensor returned no value — check the Box / AHT20 wiring."}
    safe = h <= max_humidity
    advice = ("Dry — OK to print {}.".format(material) if safe
              else "TOO WET for {} ({}% RH > {}%). Deep-dry 80-90C / 8-12h before printing.".format(material, h, max_humidity))
    return {"safe_to_print": safe, "humidity_pct": h, "threshold": max_humidity,
            "verdict": "GO" if safe else "NO-GO", "advice": advice}


# ───────────────────────── MUTATING tools (real side effects) ─────────────────────────
# These command the physical printer. NOT read-only, NOT idempotent — call deliberately.

@mcp.tool()
def start_print(filename: str) -> dict:
    """Start printing a gcode file already uploaded to the printer.
    ⚠️ MUTATING — starts a physical print. Real-world side effects, NOT idempotent,
    NOT read-only. For moisture-sensitive filament, call humidity_gate first and only
    proceed if safe_to_print is True.
    Args:
        filename: name of the gcode file on the printer (e.g. 'benchy.gcode')."""
    result = _post("/printer/print/start?filename={}".format(quote(filename)))
    return {"status": "print_started", "filename": filename, "response": result}


@mcp.tool()
def pause_print() -> dict:
    """Pause the current print job.
    ⚠️ MUTATING — changes printer state. NOT read-only, NOT idempotent."""
    result = _post("/printer/print/pause")
    return {"status": "print_paused", "response": result}


@mcp.tool()
def resume_print() -> dict:
    """Resume a paused print job.
    ⚠️ MUTATING — changes printer state. NOT read-only, NOT idempotent."""
    result = _post("/printer/print/resume")
    return {"status": "print_resumed", "response": result}


@mcp.tool()
def cancel_print() -> dict:
    """Cancel the current print job (printer stops and cools down).
    ⚠️ MUTATING & DESTRUCTIVE — aborts the running print, losing progress. NOT read-only,
    NOT idempotent. Only call with clear intent."""
    result = _post("/printer/print/cancel")
    return {"status": "print_cancelled", "response": result}


@mcp.tool()
def send_gcode(command: str) -> dict:
    """Send a raw G-code command to the printer.
    ⚠️ MUTATING & potentially DESTRUCTIVE — moves the head, sets temps, drives motors.
    NOT read-only, NOT idempotent. Validate commands before sending.
    Common: G28 home · G1 X100 Y100 Z50 F3000 move · M104 S200 nozzle · M140 S60 bed ·
    M106 S255 fan on · M107 fan off.
    Args:
        command: the G-code command string."""
    result = _post("/printer/gcode/script?script={}".format(quote(command)))
    return {"status": "gcode_sent", "command": command, "response": result}


@mcp.tool()
def preheat(bed_temp: int = 60, nozzle_temp: int = 220) -> dict:
    """Preheat bed and nozzle to target temperatures (defaults PLA-friendly: bed 60C, nozzle 220C).
    ⚠️ MUTATING — turns on heaters. NOT read-only, NOT idempotent.
    Args:
        bed_temp: target bed C (0-120, default 60).
        nozzle_temp: target nozzle C (0-300, default 220)."""
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


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/aFa7sNcgAdQS0ZT1Uc8k91t"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
