#!/usr/bin/env python3
"""
PCB Reverse Engineering Tool
=============================
A CLI tool for reverse engineering PCB connectivity and component values.

Features:
- Track components with values, packages, and pin counts
- Record measured values (resistance, capacitance, Vf, hFE)
- Record pin-to-pin connections
- Auto-generate and name nets
- Export: BOM, CSV netlist, KiCad netlist, named nets JSON

Usage: python3 pcb_reverse.py [project_name]

Version: v2.2.1
License: MIT
Author: R. Andrew Ballard, Blue Sky Fusion, Inc. (c) 2026
"""

import json
import csv
import os
import sys
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path


# ==================== VALUE FORMATTING ====================

def parse_resistance(value_str: str) -> float:
    """Parse resistance string to ohms. Returns None if invalid."""
    if not value_str or value_str.upper() in ['?', 'TBD', 'NC', 'DNP']:
        return None

    value_str = value_str.strip().upper().replace(' ', '')
    value_str = value_str.replace('OHM', '').replace('Ω', '').replace('R', '')

    multipliers = {'K': 1e3, 'M': 1e6, 'G': 1e9}

    for suffix, mult in multipliers.items():
        if suffix in value_str:
            try:
                return float(value_str.replace(suffix, '')) * mult
            except ValueError:
                return None

    try:
        return float(value_str)
    except ValueError:
        return None


def format_resistance(ohms: float) -> str:
    """Format ohms to human-readable string."""
    if ohms is None:
        return "?"
    if ohms >= 1e6:
        return f"{ohms/1e6:.2g}M"
    elif ohms >= 1e3:
        return f"{ohms/1e3:.2g}k"
    else:
        return f"{ohms:.2g}R"


def parse_capacitance(value_str: str) -> float:
    """Parse capacitance string to farads. Returns None if invalid."""
    if not value_str or value_str.upper() in ['?', 'TBD', 'NC', 'DNP']:
        return None

    value_str = value_str.strip().upper().replace(' ', '')
    value_str = value_str.replace('F', '').replace('FARAD', '')

    multipliers = {
        'P': 1e-12, 'N': 1e-9, 'U': 1e-6, 'µ': 1e-6, 'Μ': 1e-6,  # Note: µ and micro
        'M': 1e-3  # milli (rare but used)
    }

    for suffix, mult in multipliers.items():
        if suffix in value_str:
            try:
                return float(value_str.replace(suffix, '')) * mult
            except ValueError:
                return None

    try:
        return float(value_str)
    except ValueError:
        return None


def format_capacitance(farads: float) -> str:
    """Format farads to human-readable string."""
    if farads is None:
        return "?"
    if farads >= 1e-3:
        return f"{farads*1e3:.2g}mF"
    elif farads >= 1e-6:
        return f"{farads*1e6:.2g}µF"
    elif farads >= 1e-9:
        return f"{farads*1e9:.2g}nF"
    else:
        return f"{farads*1e12:.2g}pF"


def parse_voltage(value_str: str) -> float:
    """Parse voltage string to volts."""
    if not value_str or value_str.upper() in ['?', 'TBD']:
        return None

    value_str = value_str.strip().upper().replace(' ', '')
    value_str = value_str.replace('V', '').replace('VOLT', '')

    # Handle millivolts
    if 'M' in value_str:
        try:
            return float(value_str.replace('M', '')) / 1000
        except ValueError:
            return None

    try:
        return float(value_str)
    except ValueError:
        return None


def format_voltage(volts: float) -> str:
    """Format volts to human-readable string."""
    if volts is None:
        return "?"
    if volts < 1:
        return f"{volts*1000:.0f}mV"
    else:
        return f"{volts:.2f}V"


def smart_format_value(value_str: str, comp_type: str) -> str:
    """Smart format a value based on component type."""
    if not value_str or value_str.upper() in ['?', 'TBD', 'NC', 'DNP']:
        return value_str

    comp_type = comp_type.upper()

    if comp_type == 'R':  # Resistor
        ohms = parse_resistance(value_str)
        if ohms is not None:
            return format_resistance(ohms)
    elif comp_type == 'C':  # Capacitor
        farads = parse_capacitance(value_str)
        if farads is not None:
            return format_capacitance(farads)

    return value_str


# ==================== COMPONENT TYPE DETECTION ====================

def get_component_type(ref: str) -> str:
    """Get component type from reference designator."""
    prefix = ''.join(c for c in ref if c.isalpha()).upper()

    type_map = {
        'R': 'resistor',
        'C': 'capacitor',
        'L': 'inductor',
        'D': 'diode',
        'Q': 'transistor',
        'U': 'ic',
        'J': 'connector',
        'T': 'transformer',
        'F': 'fuse',
        'SW': 'switch',
        'LED': 'led',
        'TP': 'testpoint',
    }

    return type_map.get(prefix, 'other')


def get_default_pins(ref: str) -> int:
    """Get default pin count for component type."""
    comp_type = get_component_type(ref)

    defaults = {
        'resistor': 2,
        'capacitor': 2,
        'inductor': 2,
        'diode': 2,
        'led': 2,
        'fuse': 2,
        'transistor': 3,
        'testpoint': 1,
    }

    return defaults.get(comp_type, 2)


# ==================== MAIN PROJECT CLASS ====================

class PCBProject:
    """Manages a PCB reverse engineering project"""

    def __init__(self, project_dir: str = None, project_name: str = "project"):
        if project_dir:
            self.project_dir = Path(project_dir)
        else:
            self.project_dir = Path.cwd()

        self.project_name = project_name
        self.components_file = self.project_dir / f"{project_name}_components.json"
        self.connections_file = self.project_dir / f"{project_name}_connections.json"
        self.nets_file = self.project_dir / f"{project_name}_nets.json"

        # Data structures
        self.components = {}  # ref -> {pins, value, package, measured, ...}
        self.connections = set()  # set of (pin1, pin2) tuples
        self.net_names = {}  # net_id -> custom_name

        self.load()

    def load(self):
        """Load project data from files"""
        # Load components
        if self.components_file.exists():
            with open(self.components_file) as f:
                data = json.load(f)
                self.components = data.get("components", {})
            print(f"Loaded {len(self.components)} components")

        # Load connections
        if self.connections_file.exists():
            with open(self.connections_file) as f:
                data = json.load(f)
                self.connections = set(tuple(c) for c in data.get("connections", []))
            print(f"Loaded {len(self.connections)} connections")

        # Load net names
        if self.nets_file.exists():
            with open(self.nets_file) as f:
                data = json.load(f)
                self.net_names = data.get("net_names", {})

    def save(self):
        """Save project data to files"""
        # Save components
        comp_data = {
            "project": self.project_name,
            "timestamp": datetime.now().isoformat(),
            "component_count": len(self.components),
            "components": self.components
        }
        with open(self.components_file, 'w') as f:
            json.dump(comp_data, f, indent=2)

        # Save connections
        conn_data = {
            "project": self.project_name,
            "timestamp": datetime.now().isoformat(),
            "connection_count": len(self.connections),
            "connections": sorted(list(self.connections))
        }
        with open(self.connections_file, 'w') as f:
            json.dump(conn_data, f, indent=2)

        # Save net names
        if self.net_names:
            nets_data = {
                "project": self.project_name,
                "timestamp": datetime.now().isoformat(),
                "net_names": self.net_names
            }
            with open(self.nets_file, 'w') as f:
                json.dump(nets_data, f, indent=2)

        print(f"Saved: {len(self.components)} components, {len(self.connections)} connections")

    # ==================== COMPONENT MANAGEMENT ====================

    def normalize_ref(self, ref: str) -> str:
        """Normalize component ref: D4 -> D04, Q5 -> Q05"""
        ref = ref.upper().strip()
        prefix = ''.join(c for c in ref if c.isalpha())
        num_str = ''.join(c for c in ref if c.isdigit())
        if prefix and num_str:
            num = int(num_str)
            if num < 10:
                return f"{prefix}{num:02d}"
        return ref

    def add_component(self, ref: str, pins: int = None, value: str = "?",
                      package: str = "?", description: str = ""):
        """Add or update a component"""
        ref = self.normalize_ref(ref)
        comp_type = get_component_type(ref)

        if pins is None:
            pins = get_default_pins(ref)

        # Smart format the value
        prefix = ''.join(c for c in ref if c.isalpha())
        value = smart_format_value(value, prefix)

        self.components[ref] = {
            "pins": pins,
            "value": value,
            "package": package,
            "description": description,
            "type": comp_type,
            "measured": {},  # Store measured values here
        }
        print(f"  Added: {ref} ({value}, {pins} pins, {package})")

    def measure_component(self, ref: str, measurement_type: str, value: str):
        """Record a measurement for a component"""
        ref = self.normalize_ref(ref)

        if ref not in self.components:
            print(f"  Component {ref} not found. Add it first.")
            return False

        comp_type = get_component_type(ref)
        measurement_type = measurement_type.lower()

        # Initialize measured dict if needed
        if "measured" not in self.components[ref]:
            self.components[ref]["measured"] = {}

        # Parse and format based on measurement type
        if measurement_type in ['r', 'resistance', 'ohms']:
            ohms = parse_resistance(value)
            if ohms is not None:
                self.components[ref]["measured"]["resistance"] = ohms
                self.components[ref]["value"] = format_resistance(ohms)
                print(f"  {ref}: Resistance = {format_resistance(ohms)}")
                return True
            else:
                print(f"  Invalid resistance value: {value}")
                return False

        elif measurement_type in ['c', 'capacitance', 'cap']:
            farads = parse_capacitance(value)
            if farads is not None:
                self.components[ref]["measured"]["capacitance"] = farads
                self.components[ref]["value"] = format_capacitance(farads)
                print(f"  {ref}: Capacitance = {format_capacitance(farads)}")
                return True
            else:
                print(f"  Invalid capacitance value: {value}")
                return False

        elif measurement_type in ['vf', 'forward', 'diode']:
            volts = parse_voltage(value)
            if volts is not None:
                self.components[ref]["measured"]["vf"] = volts
                self.components[ref]["value"] = f"Vf={format_voltage(volts)}"
                print(f"  {ref}: Forward Voltage = {format_voltage(volts)}")
                return True
            else:
                print(f"  Invalid voltage value: {value}")
                return False

        elif measurement_type in ['hfe', 'gain', 'beta']:
            try:
                hfe = float(value)
                self.components[ref]["measured"]["hfe"] = hfe
                print(f"  {ref}: hFE = {hfe:.0f}")
                return True
            except ValueError:
                print(f"  Invalid hFE value: {value}")
                return False

        elif measurement_type in ['vbe', 'vgs', 'vth']:
            volts = parse_voltage(value)
            if volts is not None:
                self.components[ref]["measured"]["vbe"] = volts
                print(f"  {ref}: Vbe/Vth = {format_voltage(volts)}")
                return True
            else:
                print(f"  Invalid voltage value: {value}")
                return False

        elif measurement_type in ['type', 'polarity']:
            value = value.upper()
            if value in ['NPN', 'PNP', 'NFET', 'PFET', 'N-FET', 'P-FET', 'NMOS', 'PMOS']:
                self.components[ref]["measured"]["transistor_type"] = value
                print(f"  {ref}: Type = {value}")
                return True
            else:
                print(f"  Invalid transistor type: {value} (use NPN/PNP/NFET/PFET)")
                return False

        elif measurement_type in ['marking', 'mark', 'label']:
            self.components[ref]["measured"]["marking"] = value
            print(f"  {ref}: Marking = {value}")
            return True

        else:
            print(f"  Unknown measurement type: {measurement_type}")
            print(f"  Valid types: r/resistance, c/capacitance, vf/diode, hfe/gain, vbe, type, marking")
            return False

    def quick_measure(self, ref: str, value: str):
        """Quick measure - auto-detect measurement type from component"""
        ref = self.normalize_ref(ref)

        if ref not in self.components:
            # Auto-add component
            self.add_component(ref)

        comp_type = get_component_type(ref)

        if comp_type == 'resistor':
            return self.measure_component(ref, 'r', value)
        elif comp_type == 'capacitor':
            return self.measure_component(ref, 'c', value)
        elif comp_type == 'diode' or comp_type == 'led':
            return self.measure_component(ref, 'vf', value)
        elif comp_type == 'transistor':
            # Check if it looks like a type or a measurement
            if value.upper() in ['NPN', 'PNP', 'NFET', 'PFET', 'N-FET', 'P-FET']:
                return self.measure_component(ref, 'type', value)
            else:
                return self.measure_component(ref, 'hfe', value)
        else:
            # Store as marking
            return self.measure_component(ref, 'marking', value)

    def edit_component(self, ref: str, field: str, value):
        """Edit a component field"""
        ref = self.normalize_ref(ref)
        if ref not in self.components:
            print(f"  Component {ref} not found")
            return False

        if field == "pins":
            value = int(value)
        elif field == "value":
            prefix = ''.join(c for c in ref if c.isalpha())
            value = smart_format_value(value, prefix)

        self.components[ref][field] = value
        print(f"  Updated {ref}.{field} = {value}")
        return True

    def delete_component(self, ref: str):
        """Delete a component and its connections"""
        ref = self.normalize_ref(ref)
        if ref not in self.components:
            print(f"  Component {ref} not found")
            return False

        # Remove connections involving this component
        to_remove = [c for c in self.connections
                     if c[0].startswith(ref + "-") or c[1].startswith(ref + "-")]
        for conn in to_remove:
            self.connections.remove(conn)

        del self.components[ref]
        print(f"  Deleted {ref} and {len(to_remove)} connections")
        return True

    def list_components(self, filter_prefix: str = None, show_measured: bool = True):
        """List all components with values"""
        for ref in sorted(self.components.keys()):
            if filter_prefix and not ref.startswith(filter_prefix.upper()):
                continue
            info = self.components[ref]

            # Build value string
            value_str = info.get('value', '?')
            measured = info.get('measured', {})

            # Add measured info
            measured_parts = []
            if 'resistance' in measured:
                measured_parts.append(f"R={format_resistance(measured['resistance'])}")
            if 'capacitance' in measured:
                measured_parts.append(f"C={format_capacitance(measured['capacitance'])}")
            if 'vf' in measured:
                measured_parts.append(f"Vf={format_voltage(measured['vf'])}")
            if 'hfe' in measured:
                measured_parts.append(f"hFE={measured['hfe']:.0f}")
            if 'vbe' in measured:
                measured_parts.append(f"Vbe={format_voltage(measured['vbe'])}")
            if 'transistor_type' in measured:
                measured_parts.append(measured['transistor_type'])
            if 'marking' in measured:
                measured_parts.append(f"'{measured['marking']}'")

            if show_measured and measured_parts:
                measured_str = f" [{', '.join(measured_parts)}]"
            else:
                measured_str = ""

            # Add predicted flag if present
            predicted_str = " [PREDICTED]" if info.get('predicted') else ""

            print(f"  {ref}: {value_str} ({info['pins']} pins, {info['package']}){measured_str}{predicted_str}")

            if info.get('description'):
                print(f"       {info['description']}")

    def show_component(self, ref: str):
        """Show detailed info for a component"""
        ref = self.normalize_ref(ref)
        if ref not in self.components:
            print(f"  Component {ref} not found")
            return

        info = self.components[ref]
        print(f"\n  === {ref} ===")
        print(f"  Type: {info.get('Type', info.get('type', 'unknown'))}")
        print(f"  Value: {info.get('value', '?')}")
        print(f"  Package: {info.get('package', '?')}")
        print(f"  Pins: {info.get('pins', '?')}")
        if info.get('predicted'):
            print(f"  Status: PREDICTED (not yet measured)")

        if info.get('description'):
            print(f"  Description: {info['description']}")

        measured = info.get('measured', {})
        if measured:
            print(f"  Measurements:")
            for key, val in measured.items():
                if key == 'resistance':
                    print(f"    Resistance: {format_resistance(val)}")
                elif key == 'capacitance':
                    print(f"    Capacitance: {format_capacitance(val)}")
                elif key == 'vf':
                    print(f"    Forward Voltage: {format_voltage(val)}")
                elif key == 'hfe':
                    print(f"    hFE (gain): {val:.0f}")
                elif key == 'vbe':
                    print(f"    Vbe/Vth: {format_voltage(val)}")
                else:
                    print(f"    {key}: {val}")

        # Show connections
        conns = self.find_connections(ref)
        if conns:
            print(f"  Connections:")
            for c in conns:
                print(f"    {c[0]} <-> {c[1]}")

    # ==================== CONNECTION MANAGEMENT ====================

    def parse_pin(self, pin_str: str):
        """Parse pin string like 'Q12-2' into ('Q12', '2') or just 'GND' for single-pin"""
        pin_str = pin_str.upper().strip()

        # Handle special single-pin nets (GND, VCC, etc.) - return just the ref
        if pin_str in self.components and self.components[pin_str].get("pins") == 1:
            return (pin_str, None)  # None means single-pin, use ref directly

        # Handle formats: Q12-2, Q12.2
        for sep in ["-", ".", "_"]:
            if sep in pin_str:
                parts = pin_str.split(sep, 1)
                if len(parts) == 2:
                    ref = self.normalize_ref(parts[0])
                    pin = parts[1].strip()
                    if pin.upper() == "TAB":
                        pin = "TAB"
                    # Check if this is a single-pin component with -1 suffix
                    if ref in self.components and self.components[ref].get("pins") == 1:
                        return (ref, None)
                    return (ref, pin)

        # Also check if bare ref is a single-pin component
        normalized = self.normalize_ref(pin_str)
        if normalized in self.components and self.components[normalized].get("pins") == 1:
            return (normalized, None)

        return None

    def format_pin(self, parsed_pin):
        """Format parsed pin tuple back to string"""
        if parsed_pin is None:
            return None
        ref, pin = parsed_pin
        if pin is None:
            return ref  # Single-pin component
        return f"{ref}-{pin}"

    def add_connection(self, pin1: str, pin2: str):
        """Add a connection between two pins"""
        p1 = self.parse_pin(pin1)
        p2 = self.parse_pin(pin2)

        if not p1 or not p2:
            print(f"  Invalid pin format: {pin1} or {pin2}")
            return False

        # Auto-add components if they don't exist
        for ref, pin in [p1, p2]:
            if ref not in self.components:
                print(f"  Auto-adding component {ref}")
                self.add_component(ref)

        # Format pins (handles single-pin components)
        pin1_str = self.format_pin(p1)
        pin2_str = self.format_pin(p2)

        # Normalize connection order
        conn = tuple(sorted([pin1_str, pin2_str]))

        if conn in self.connections:
            print(f"  Already exists: {conn[0]} <-> {conn[1]}")
            return False

        self.connections.add(conn)
        print(f"  Added: {conn[0]} <-> {conn[1]}")
        return True

    def delete_connection(self, pin1: str, pin2: str):
        """Remove a connection"""
        p1 = self.parse_pin(pin1)
        p2 = self.parse_pin(pin2)

        if not p1 or not p2:
            print(f"  Invalid pin format")
            return False

        # Format pins (handles single-pin components)
        pin1_str = self.format_pin(p1)
        pin2_str = self.format_pin(p2)
        conn = tuple(sorted([pin1_str, pin2_str]))

        if conn in self.connections:
            self.connections.remove(conn)
            print(f"  Removed: {conn[0]} <-> {conn[1]}")
            return True

        # Also try with -1 suffix for backwards compatibility
        alt_variants = []
        for p, ps in [(p1, pin1_str), (p2, pin2_str)]:
            if p[1] is None:  # Single-pin component
                alt_variants.append([ps, f"{p[0]}-1"])
            else:
                alt_variants.append([ps])

        # Try all combinations
        for v1 in alt_variants[0]:
            for v2 in alt_variants[1]:
                alt_conn = tuple(sorted([v1, v2]))
                if alt_conn in self.connections:
                    self.connections.remove(alt_conn)
                    print(f"  Removed: {alt_conn[0]} <-> {alt_conn[1]}")
                    return True

        print(f"  Connection not found: {pin1_str} <-> {pin2_str}")
        return False

    def merge_pins(self, from_pin: str, to_pin: str):
        """Merge all connections from one pin to another (for duplicate pins like Q14-4 = Q14-TAB)"""
        p_from = self.parse_pin(from_pin)
        p_to = self.parse_pin(to_pin)

        if not p_from or not p_to:
            print(f"  Invalid pin format")
            return False

        from_str = self.format_pin(p_from)
        to_str = self.format_pin(p_to)

        # Find all connections involving from_pin
        to_update = []
        for conn in list(self.connections):
            if from_str in conn or (p_from[1] is None and f"{p_from[0]}-1" in conn):
                to_update.append(conn)

        if not to_update:
            print(f"  No connections found for {from_str}")
            return False

        # Update connections
        count = 0
        for conn in to_update:
            self.connections.remove(conn)
            # Replace from_pin with to_pin
            new_conn = []
            for pin in conn:
                if pin == from_str or pin == f"{p_from[0]}-1":
                    new_conn.append(to_str)
                else:
                    new_conn.append(pin)
            new_conn = tuple(sorted(new_conn))

            # Don't add self-connections
            if new_conn[0] != new_conn[1]:
                if new_conn not in self.connections:
                    self.connections.add(new_conn)
                    count += 1

        print(f"  Merged {from_str} -> {to_str}: {count} connections updated")
        return True

    def delete_pin_connections(self, pin: str):
        """Delete all connections for a specific pin"""
        p = self.parse_pin(pin)
        if not p:
            print(f"  Invalid pin format: {pin}")
            return False

        pin_str = self.format_pin(p)

        # Find all connections involving this pin
        to_remove = []
        for conn in self.connections:
            if pin_str in conn or (p[1] is None and f"{p[0]}-1" in conn):
                to_remove.append(conn)

        if not to_remove:
            print(f"  No connections found for {pin_str}")
            return False

        for conn in to_remove:
            self.connections.remove(conn)

        print(f"  Deleted {len(to_remove)} connections for {pin_str}")
        return True

    def find_connections(self, pin_or_ref: str):
        """Find connections for a pin or component"""
        original = pin_or_ref.upper().strip()

        if "-" in original or "." in original:
            p = self.parse_pin(original)
            if p:
                search_terms = [self.format_pin(p)]
                # Also try with -1 suffix for single-pin
                if p[1] is None:
                    search_terms.append(f"{p[0]}-1")
            else:
                search_terms = [original]
        else:
            # Search both normalized and original forms
            normalized = self.normalize_ref(original)
            search_terms = [normalized, original]
            if normalized != original:
                search_terms.append(original)

        matches = []
        for conn in self.connections:
            for search in search_terms:
                if search in conn[0] or search in conn[1]:
                    if conn not in matches:
                        matches.append(conn)
                    break

        return sorted(matches)

    # ==================== NET BUILDING ====================

    def build_nets(self):
        """Build nets from connections using union-find"""
        parent = {}

        def find(x):
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        for conn in self.connections:
            union(conn[0], conn[1])

        nets = defaultdict(set)
        for conn in self.connections:
            for pin in conn:
                root = find(pin)
                nets[root].add(pin)

        return dict(nets)

    def name_net(self, pin: str, name: str):
        """Assign a name to the net containing a pin"""
        p = self.parse_pin(pin)
        if not p:
            print(f"  Invalid pin: {pin}")
            return False

        nets = self.build_nets()
        pin_str = f"{p[0]}-{p[1]}"

        for root, pins in nets.items():
            if pin_str in pins:
                self.net_names[root] = name
                print(f"  Named net: {name} ({len(pins)} pins)")
                return True

        print(f"  Pin {pin_str} not in any net")
        return False

    # ==================== EXPORTS ====================

    def export_bom(self, filename: str = None):
        """Export Bill of Materials"""
        if not filename:
            filename = self.project_dir / f"{self.project_name}_BOM.csv"

        bom = defaultdict(lambda: {"refs": [], "count": 0})

        for ref, info in sorted(self.components.items()):
            if info.get("package") in ["-", "Virtual", ""]:
                continue

            # Use measured value if available, else marked value
            value = info.get("value", "?")

            key = (value, info.get("package", "?"))
            bom[key]["refs"].append(ref)
            bom[key]["count"] += 1
            bom[key]["value"] = value
            bom[key]["package"] = info.get("package", "?")
            bom[key]["description"] = info.get("description", "")

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Qty", "Value", "Package", "References", "Description"])

            for key in sorted(bom.keys()):
                item = bom[key]
                refs_str = ", ".join(sorted(item["refs"]))
                writer.writerow([
                    item["count"],
                    item["value"],
                    item["package"],
                    refs_str,
                    item["description"]
                ])

        print(f"  Exported BOM: {filename} ({len(bom)} unique parts)")

    def export_component_list(self, filename: str = None):
        """Export detailed component list with measurements"""
        if not filename:
            filename = self.project_dir / f"{self.project_name}_components.csv"

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Ref", "Type", "Value", "Package", "Pins",
                           "Measured_R", "Measured_C", "Measured_Vf",
                           "Measured_hFE", "Marking", "Description"])

            for ref in sorted(self.components.keys()):
                info = self.components[ref]
                measured = info.get("measured", {})

                writer.writerow([
                    ref,
                    info.get("type", ""),
                    info.get("value", "?"),
                    info.get("package", "?"),
                    info.get("pins", ""),
                    format_resistance(measured.get("resistance")) if "resistance" in measured else "",
                    format_capacitance(measured.get("capacitance")) if "capacitance" in measured else "",
                    format_voltage(measured.get("vf")) if "vf" in measured else "",
                    f"{measured['hfe']:.0f}" if "hfe" in measured else "",
                    measured.get("marking", ""),
                    info.get("description", "")
                ])

        print(f"  Exported component list: {filename}")

    def export_netlist_csv(self, filename: str = None):
        """Export connections as CSV"""
        if not filename:
            filename = self.project_dir / f"{self.project_name}_netlist.csv"

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Pin1", "Pin2", "Ref1", "Pin1#", "Ref2", "Pin2#"])

            for conn in sorted(self.connections):
                p1 = self.parse_pin(conn[0])
                p2 = self.parse_pin(conn[1])
                if p1 and p2:
                    writer.writerow([conn[0], conn[1], p1[0], p1[1], p2[0], p2[1]])

        print(f"  Exported netlist CSV: {filename}")

    def export_named_nets(self, filename: str = None):
        """Export named nets with pin assignments"""
        if not filename:
            filename = self.project_dir / f"{self.project_name}_named_nets.json"

        nets = self.build_nets()
        output = {"nets": {}}

        for root, pins in nets.items():
            name = self.net_names.get(root, f"NET_{root.replace('-', '_')}")
            output["nets"][name] = {
                "description": "",
                "pin_count": len(pins),
                "pins": sorted(list(pins))
            }

        output["source"] = str(self.connections_file)
        output["timestamp"] = datetime.now().isoformat()
        output["total_connections"] = len(self.connections)

        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"  Exported named nets: {filename} ({len(nets)} nets)")

    def export_kicad_netlist(self, filename: str = None):
        """Export KiCad-style netlist"""
        if not filename:
            filename = self.project_dir / f"{self.project_name}.net"

        nets = self.build_nets()

        with open(filename, 'w') as f:
            f.write(f"# {self.project_name} Netlist\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write(f"# Connections: {len(self.connections)}\n")
            f.write(f"# Nets: {len(nets)}\n\n")

            for root, pins in sorted(nets.items()):
                name = self.net_names.get(root, f"Net_{root}")
                f.write(f"{name}:\n")
                for pin in sorted(pins):
                    f.write(f"  {pin}\n")
                f.write("\n")

        print(f"  Exported KiCad netlist: {filename}")

    # ==================== UTILITIES ====================

    def get_remaining_pins(self, filter_prefix: str = None):
        """Get unconnected pins"""
        connected = set()
        for conn in self.connections:
            connected.add(conn[0])
            connected.add(conn[1])

        remaining = []
        for ref, info in sorted(self.components.items()):
            if info.get("pins", 0) <= 1:
                continue
            if filter_prefix and not ref.startswith(filter_prefix.upper()):
                continue

            for pin_num in range(1, info["pins"] + 1):
                pin_str = f"{ref}-{pin_num}"
                if pin_str not in connected:
                    remaining.append((ref, pin_num, info.get("value", "?")))

        return remaining

    def print_remaining(self, filter_prefix: str = None):
        """Print unconnected pins"""
        remaining = self.get_remaining_pins(filter_prefix)

        if not remaining:
            print("  All pins connected!")
            return

        by_comp = defaultdict(list)
        for ref, pin, value in remaining:
            by_comp[ref].append(pin)

        print(f"\n=== Remaining: {len(remaining)} pins ===")
        for ref in sorted(by_comp.keys()):
            pins = by_comp[ref]
            value = self.components[ref].get("value", "?")
            pin_list = ", ".join(str(p) for p in sorted(pins, key=str))
            print(f"  {ref} ({value}): pins {pin_list}")

    def print_stats(self):
        """Print project statistics"""
        nets = self.build_nets()

        print(f"\n=== {self.project_name} Statistics ===")
        print(f"Components: {len(self.components)}")
        print(f"Connections: {len(self.connections)}")
        print(f"Nets: {len(nets)}")

        # Count measured vs unmeasured
        measured_count = sum(1 for c in self.components.values() if c.get("measured"))
        print(f"Measured: {measured_count}/{len(self.components)}")

        by_type = defaultdict(int)
        for ref in self.components:
            prefix = ''.join(c for c in ref if c.isalpha())
            by_type[prefix] += 1

        print(f"\nBy type:")
        for prefix in sorted(by_type.keys()):
            print(f"  {prefix}: {by_type[prefix]}")


# ==================== CLI ====================

def print_help():
    print("""
=== PCB Reverse Engineering Tool v2.2 ===

COMPONENT COMMANDS:
  cadd <ref> [pins] [value] [package]   Add component (pins auto-detected)
  cedit <ref> <field> <value>           Edit field (pins/value/package/description)
  cdel <ref>                            Delete component
  clist [prefix]                        List components
  cshow <ref>                           Show component details

MEASUREMENT COMMANDS:
  m <ref> <value>                       Quick measure (auto-detect type)
  mr <ref> <ohms>                       Measure resistance (e.g., mr R1 4.7k)
  mc <ref> <farads>                     Measure capacitance (e.g., mc C1 100n)
  mv <ref> <volts>                      Measure diode Vf (e.g., mv D1 0.65)
  mh <ref> <hfe>                        Measure transistor hFE (e.g., mh Q1 150)
  mt <ref> <type>                       Set transistor type (NPN/PNP/NFET/PFET)

CONNECTION COMMANDS:
  <pin1> <pin2>                         Quick add (e.g., R1-1 C2-2)
  add <pin1> <pin2>                     Add connection
  del <pin>                             Delete ALL connections for a pin
  del <pin1> <pin2>                     Delete specific connection
  merge <from_pin> <to_pin>             Merge pins (e.g., merge Q14-4 Q14-TAB)
  find <pin_or_ref>                     Find connections

NET COMMANDS:
  name <pin> <net_name>                 Name net containing pin
  nets                                  Show all nets

EXPORT COMMANDS:
  bom                                   Export BOM (CSV)
  csv                                   Export connections (CSV)
  parts                                 Export component list with measurements
  kicad                                 Export KiCad netlist
  named                                 Export named nets (JSON)
  all                                   Export all formats

UTILITIES:
  remaining [prefix]                    Show unconnected pins
  stats                                 Show statistics
  save                                  Save project
  help                                  Show this help
  quit                                  Exit (auto-saves)

VALUE FORMATS:
  Resistance: 4.7k, 10M, 470, 4700 -> auto-formats
  Capacitance: 100n, 10u, 0.1u, 100pF -> auto-formats
  Voltage: 0.65, 650m, 3.3V -> auto-formats
""")


def main():
    project_name = sys.argv[1] if len(sys.argv) > 1 else "pcb_project"

    print("=" * 50)
    print(f"PCB Reverse Engineering Tool v2.2")
    print(f"Project: {project_name}")
    print("=" * 50)

    proj = PCBProject(project_name=project_name)
    print_help()

    while True:
        try:
            cmd = input("\n> ").strip()
            if not cmd:
                continue

            parts = cmd.split()
            action = parts[0].lower()

            # Quick connection: two pins with "-"
            if len(parts) == 2 and "-" in parts[0] and "-" in parts[1]:
                proj.add_connection(parts[0], parts[1])
                continue

            # Quick measure: m <ref> <value>
            if action == "m" and len(parts) >= 3:
                proj.quick_measure(parts[1], parts[2])
                continue

            # Specific measurements
            if action == "mr" and len(parts) >= 3:
                proj.measure_component(parts[1], 'r', parts[2])
            elif action == "mc" and len(parts) >= 3:
                proj.measure_component(parts[1], 'c', parts[2])
            elif action == "mv" and len(parts) >= 3:
                proj.measure_component(parts[1], 'vf', parts[2])
            elif action == "mh" and len(parts) >= 3:
                proj.measure_component(parts[1], 'hfe', parts[2])
            elif action == "mt" and len(parts) >= 3:
                proj.measure_component(parts[1], 'type', parts[2])

            # Component commands
            elif action == "cadd" and len(parts) >= 2:
                ref = parts[1]
                pins = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
                value = parts[3] if len(parts) > 3 else "?"
                package = parts[4] if len(parts) > 4 else "?"
                proj.add_component(ref, pins, value, package)

            elif action == "cedit" and len(parts) >= 4:
                proj.edit_component(parts[1], parts[2], " ".join(parts[3:]))

            elif action == "cdel" and len(parts) >= 2:
                proj.delete_component(parts[1])

            elif action == "clist":
                proj.list_components(parts[1] if len(parts) > 1 else None)

            elif action == "cshow" and len(parts) >= 2:
                proj.show_component(parts[1])

            # Connection commands
            elif action == "add" and len(parts) >= 3:
                proj.add_connection(parts[1], parts[2])

            elif action == "del" and len(parts) >= 2:
                if len(parts) >= 3:
                    # del <pin1> <pin2> - delete specific connection
                    proj.delete_connection(parts[1], parts[2])
                else:
                    # del <pin> - delete all connections for pin
                    proj.delete_pin_connections(parts[1])

            elif action == "merge" and len(parts) >= 3:
                proj.merge_pins(parts[1], parts[2])

            elif action == "pdel" and len(parts) >= 2:
                # Alias for del <pin>
                proj.delete_pin_connections(parts[1])

            elif action in ["find", "comp"] and len(parts) >= 2:
                matches = proj.find_connections(parts[1])
                if matches:
                    print(f"  {parts[1].upper()} connections:")
                    for c in matches:
                        print(f"    {c[0]} <-> {c[1]}")
                else:
                    print(f"  No connections found for {parts[1]}")

            # Net commands
            elif action == "name" and len(parts) >= 3:
                proj.name_net(parts[1], parts[2])

            elif action == "nets":
                nets = proj.build_nets()
                print(f"\n=== Nets ({len(nets)}) ===")
                for root, pins in sorted(nets.items()):
                    name = proj.net_names.get(root, "(unnamed)")
                    print(f"  {name}: {len(pins)} pins")
                    for pin in sorted(pins):
                        print(f"    {pin}")

            # Export commands
            elif action == "bom":
                proj.export_bom()

            elif action == "csv":
                proj.export_netlist_csv()

            elif action == "parts":
                proj.export_component_list()

            elif action == "kicad":
                proj.export_kicad_netlist()

            elif action == "named":
                proj.export_named_nets()

            elif action == "all":
                proj.export_bom()
                proj.export_netlist_csv()
                proj.export_component_list()
                proj.export_kicad_netlist()
                proj.export_named_nets()

            # Utilities
            elif action in ["remaining", "rem", "todo"]:
                proj.print_remaining(parts[1] if len(parts) > 1 else None)

            elif action == "stats":
                proj.print_stats()

            elif action == "save":
                proj.save()

            elif action == "help":
                print_help()

            elif action in ["quit", "exit", "q"]:
                proj.save()
                print("Goodbye!")
                break

            else:
                print("  Unknown command. Type 'help' for commands.")

        except KeyboardInterrupt:
            print("\n")
            proj.save()
            print("Goodbye!")
            break
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    main()
