# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2026-01-03

### Added
- `merge <from_pin> <to_pin>` - Merge duplicate pins (e.g., Q14-4 = Q14-TAB)
- `pdel <pin>` - Delete all connections for a specific pin

### Fixed
- Delete connection now handles single-pin components (GND vs GND-1 format mismatch)
- Improved pin parsing for backwards compatibility with imported data

## [2.1.0] - 2026-01-03

### Added
- Measurement recording for components
  - `m <ref> <value>` - Quick measure with auto-detection
  - `mr <ref> <value>` - Measure resistance
  - `mc <ref> <value>` - Measure capacitance
  - `mv <ref> <value>` - Measure diode forward voltage
  - `mh <ref> <value>` - Measure transistor hFE/gain
  - `mt <ref> <type>` - Record component type/marking
- Smart value parsing and formatting
  - Resistance: Accepts `4700`, `4.7k`, `4k7`, `1M`, outputs `4.7k`
  - Capacitance: Accepts `100n`, `0.1u`, `100nF`, outputs `100nF`
- Component list export (`components` command) with measured values
- Statistics now show measured vs unmeasured component counts
- Measurements stored in component JSON with type-specific fields

### Changed
- Statistics output includes measurement progress percentage

## [2.0.0] - 2026-01-03

### Added
- Complete rewrite with project-agnostic design
- Dynamic component management (add/edit/delete)
- Separate JSON files for components, connections, and nets
- Component descriptions field
- BOM export with automatic quantity calculation
- Quick connection entry mode (just type two pins)
- `remaining` command to show unconnected pins
- `find` command to search for connections by pin or component
- `clist` command with optional prefix filter
- Multiple exit commands: `quit`, `exit`, `q`

### Changed
- Project files now use `{project}_components.json`, `{project}_connections.json`, `{project}_nets.json`
- Improved CLI interface with better feedback
- KiCad export includes component values and footprints

### Removed
- Hardcoded component definitions (now fully dynamic)

## [1.0.0] - 2026-01-02

### Added
- Initial release
- Basic component database with hardcoded example components
- Connection tracking with pin-to-pin links
- Union-find algorithm for net building
- CSV netlist export
- Named nets with JSON export
- Basic CLI interface

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 2.2.0 | 2026-01-03 | Pin merge/delete, delete connection fix |
| 2.1.0 | 2026-01-03 | Measurement recording, smart value parsing |
| 2.0.0 | 2026-01-03 | Complete rewrite, dynamic components, BOM export |
| 1.0.0 | 2026-01-02 | Initial release |
