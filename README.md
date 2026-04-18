# QIDI 3D Printer MCP Server

Controls QIDI 4 Max Combo (and other Klipper/Moonraker printers) via Moonraker REST API.

Built by [MEOK AI Labs](https://meok.ai).

## Tools

| Tool | Description |
|------|-------------|
| `printer_status` | Full printer status: state, temps, print progress |
| `get_temperatures` | Bed and nozzle temperatures |
| `start_print` | Start printing a file on the printer |
| `pause_print` | Pause current print |
| `resume_print` | Resume paused print |
| `cancel_print` | Cancel current print |
| `list_files` | List uploaded gcode files |
| `send_gcode` | Send raw G-code (G28, G1, M104, etc.) |
| `print_progress` | Print %, time elapsed, time remaining |
| `preheat` | Preheat bed and nozzle (defaults: 60C/220C) |

## Setup

### Environment Variable

Set your printer's IP address:

```bash
export QIDI_PRINTER_IP=192.168.1.100
```

The Moonraker API must be accessible at `http://<printer_ip>:7125`. No API key required.

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "qidi-printer": {
      "command": "python",
      "args": ["/path/to/qidi-printer-mcp/server.py"],
      "env": {
        "QIDI_PRINTER_IP": "192.168.1.100"
      }
    }
  }
}
```

### Using uvx (after PyPI publish)

```json
{
  "mcpServers": {
    "qidi-printer": {
      "command": "uvx",
      "args": ["qidi-printer-mcp"],
      "env": {
        "QIDI_PRINTER_IP": "192.168.1.100"
      }
    }
  }
}
```

### Docker

```bash
docker build -t qidi-printer-mcp .
docker run -e QIDI_PRINTER_IP=192.168.1.100 qidi-printer-mcp
```

## Requirements

- Python 3.9+
- `mcp>=1.0.0`
- Network access to printer running Moonraker (port 7125)

## License

MIT
