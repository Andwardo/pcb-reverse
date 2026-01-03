# PCB Reverse Engineering Tool

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![No Dependencies](https://img.shields.io/badge/dependencies-none-green.svg)]()

A powerful CLI tool for reverse engineering PCB connectivity. Record components, measure values, trace connections, name nets, and export to multiple formats including KiCad.

**Zero dependencies** - uses Python 3 standard library only.

## Features

- **Component Database**: Add/edit/delete components with values, packages, pin counts, and descriptions
- **Measurement Recording**: Record measured values for resistors, capacitors, diodes, and transistors
- **Smart Value Parsing**: Auto-formats values (e.g., `4700` → `4.7k`, `0.1u` → `100nF`)
- **Connection Tracking**: Record pin-to-pin connections from continuity testing
- **Net Building**: Automatically groups connected pins into nets using union-find algorithm
- **Net Naming**: Assign meaningful names to nets (GND, VCC, SENSOR_IN, etc.)
- **Multiple Export Formats**:
  - BOM (Bill of Materials) as CSV with quantities
  - Netlist as CSV
  - Named nets as JSON
  - KiCad-compatible netlist
  - Component list with measurements

## Installation

```bash
# Clone the repository
git clone https://github.com/Andwardo/pcb-reverse.git
cd pcb-reverse

# Run (no installation needed!)
python3 pcb_reverse.py [project_name]

# Or make executable
chmod +x pcb_reverse.py
./pcb_reverse.py my_project
```

### Requirements

- Python 3.6 or higher
- No external dependencies

## Quick Start

```bash
# Start a new project
python3 pcb_reverse.py my_board

# Add components
> cadd R01 2 10k 0805 "Pull-up resistor"
> cadd C01 2 100nF 0805 "Bypass capacitor"
> cadd U01 8 ATtiny85 DIP-8 "Microcontroller"

# Record measurements
> m R01 10.2k          # Measure resistance (auto-detected)
> mr R02 4700          # Measure resistance (explicit)
> mc C01 98n           # Measure capacitance
> mv D01 0.65          # Measure diode forward voltage
> mh Q01 150           # Measure transistor hFE/gain

# Add connections (quick mode - just type two pins)
> R01-1 VCC-1
> R01-2 U01-5
> C01-1 GND-1

# Name nets
> name VCC-1 VCC
> name GND-1 GND

# Export everything
> all
```

## Commands Reference

### Component Commands

| Command | Description | Example |
|---------|-------------|---------|
| `cadd <ref> <pins> [value] [pkg] [desc]` | Add component | `cadd R01 2 10k 0805 "Pull-up"` |
| `cedit <ref> <field> <value>` | Edit component field | `cedit R01 value 4.7k` |
| `cdel <ref>` | Delete component and connections | `cdel R01` |
| `clist [prefix]` | List components (optional filter) | `clist R` |

### Measurement Commands

| Command | Description | Example |
|---------|-------------|---------|
| `m <ref> <value>` | Quick measure (auto-detect type) | `m R01 4.7k` |
| `mr <ref> <value>` | Measure resistance | `mr R01 4700` |
| `mc <ref> <value>` | Measure capacitance | `mc C01 100n` |
| `mv <ref> <value>` | Measure voltage (diode Vf) | `mv D01 0.65` |
| `mh <ref> <value>` | Measure hFE/gain (transistor) | `mh Q01 150` |
| `mt <ref> <value>` | Record component type/marking | `mt Q01 NPN` |

#### Smart Value Parsing

The tool automatically formats values for readability:

| Input | Interpreted As | Displayed As |
|-------|----------------|--------------|
| `4700` | 4700 ohms | `4.7k` |
| `4.7k` | 4700 ohms | `4.7k` |
| `1M` | 1000000 ohms | `1M` |
| `100n` | 100 nanofarads | `100nF` |
| `0.1u` | 100 nanofarads | `100nF` |
| `10u` | 10 microfarads | `10uF` |

### Connection Commands

| Command | Description | Example |
|---------|-------------|---------|
| `<pin1> <pin2>` | Quick add connection | `R1-1 C2-2` |
| `add <pin1> <pin2>` | Add connection | `add R1-1 C2-2` |
| `del <pin>` | Delete ALL connections for a pin | `del Q13-2` |
| `del <pin1> <pin2>` | Delete specific connection | `del R1-1 C2-2` |
| `merge <from> <to>` | Merge duplicate pins | `merge Q14-4 Q14-TAB` |
| `find <pin_or_ref>` | Find connections for pin/component | `find R01` |

### Net Commands

| Command | Description | Example |
|---------|-------------|---------|
| `name <pin> <net_name>` | Name the net containing a pin | `name C01-2 GND` |
| `nets` | Show all nets with their pins | |

### Export Commands

| Command | Output File | Description |
|---------|-------------|-------------|
| `bom` | `{project}_BOM.csv` | Bill of Materials with quantities |
| `csv` | `{project}_netlist.csv` | Connection list |
| `kicad` | `{project}.net` | KiCad netlist format |
| `named` | `{project}_named_nets.json` | Named nets as JSON |
| `components` | `{project}_component_list.csv` | Component details with measurements |
| `all` | All of the above | Export all formats |

### Utility Commands

| Command | Description |
|---------|-------------|
| `remaining [prefix]` | Show unconnected pins |
| `stats` | Show project statistics |
| `save` | Save project |
| `help` | Show help |
| `quit` / `exit` / `q` | Exit (auto-saves) |

## Pin Format

- **Standard**: `REF-PIN` (e.g., `R01-1`, `U01-5`, `C02-2`)
- **TAB pins**: `REF-TAB` (e.g., `Q14-TAB`)
- **Single-pin nets**: Just the ref (e.g., `GND`, `VCC`)

## Project Files

Each project creates three JSON files for persistent storage:

| File | Contents |
|------|----------|
| `{project}_components.json` | Component database with values, packages, measurements |
| `{project}_connections.json` | Pin-to-pin connections |
| `{project}_nets.json` | Named net assignments |

## Typical Workflow

1. **Photograph the board**: Take high-res photos of both sides for reference
2. **Document components**: Use `cadd` to add all visible components
3. **Measure values**: Use multimeter and record with `m`, `mr`, `mc`, `mv`, `mh`
4. **Trace connections**: Use continuity tester, enter connections as you find them
5. **Check remaining**: Use `remaining` to see what pins still need tracing
6. **Name nets**: Use `name` to label power rails and signal nets
7. **Export**: Use `all` to generate BOM and netlists

## Example Session

```
$ python3 pcb_reverse.py power_supply
==================================================
PCB Reverse Engineering Tool v2.2
Project: power_supply
==================================================
Loaded: 0 components, 0 connections

> cadd C01 2 100uF Radial "Main filter"
  Added: C01 (100uF, Radial, 2 pins) - Main filter

> cadd D01 2 1N4007 DO-41 "Rectifier"
  Added: D01 (1N4007, DO-41, 2 pins) - Rectifier

> cadd R01 2 TBD 0805 "Current limit"
  Added: R01 (TBD, 0805, 2 pins) - Current limit

> mr R01 47.2
  R01: Measured resistance = 47.2R

> mc C01 95u
  C01: Measured capacitance = 95uF

> mv D01 0.62
  D01: Measured Vf = 0.62V

> C01-1 D01-2
  Added: C01-1 <-> D01-2

> C01-2 GND-1
  Added: C01-2 <-> GND-1

> name C01-2 GND
  Named net: GND (2 pins)

> stats
  Components: 3
  Connections: 2
  Named nets: 1
  Measured: 3/3 (100%)

> all
  Exported: power_supply_BOM.csv
  Exported: power_supply_netlist.csv
  Exported: power_supply_named_nets.json
  Exported: power_supply.net
  Exported: power_supply_component_list.csv

> quit
Saved: 3 components, 2 connections
Goodbye!
```

## Examples

See the `examples/` directory for sample projects:

- `demo/` - Simple example with 8 components and 12 connections

## Tips and Best Practices

- **Use consistent reference designators**: R01 not R1, C01 not C1
- **Add GND and VCC first**: Create single-pin components for power rails
- **Save often**: The tool auto-saves on exit, but `save` works too
- **Use descriptions**: Add context with the description field
- **Check remaining**: Regularly run `remaining` to track progress
- **Name as you go**: Don't wait until the end to name nets

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

R. Andrew Ballard - [Blue Sky Fusion, Inc.](https://blueskyfusion.com) - 2026

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
