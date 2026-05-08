<div align="center">

# Qidi Printer MCP

**QIDI 3D Printer MCP Server**

[![PyPI](https://img.shields.io/pypi/v/meok-qidi-printer-mcp)](https://pypi.org/project/meok-qidi-printer-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

QIDI 3D Printer MCP Server
Controls QIDI 4 Max Combo (and other Klipper/Moonraker printers) via Moonraker REST API.
Built by MEOK AI Labs for Sovereign Temple v3.0.

## Tools

| Tool | Description |
|------|-------------|
| `printer_status` | Get full printer status: state, temperatures, and print progress. No parameters  |
| `get_temperatures` | Get current bed and nozzle temperatures with targets. |
| `start_print` | Start printing a gcode file already uploaded to the printer. |
| `pause_print` | Pause the current print job. |
| `resume_print` | Resume a paused print job. |
| `cancel_print` | Cancel the current print job. The printer will stop and cool down. |
| `list_files` | List all gcode files uploaded to the printer. |
| `send_gcode` | Send a raw G-code command to the printer. |
| `print_progress` | Get current print progress: percentage complete, elapsed time, estimated time re |
| `preheat` | Preheat the printer bed and nozzle to target temperatures. |

## Installation

```bash
pip install meok-qidi-printer-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "qidi-printer": {
      "command": "python",
      "args": ["-m", "meok_qidi_printer_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 10 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
