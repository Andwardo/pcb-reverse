# Demo Project

A simple example showing how the PCB Reverse Engineering Tool stores data.

## Components

- 2 resistors (R01, R02)
- 1 capacitor (C01)
- 1 diode (D01)
- 1 transistor (Q01)
- 1 IC (U01 - ATtiny85)
- Power nets (GND, VCC)

## Usage

```bash
cd examples/demo
python3 ../../pcb_reverse.py demo

> stats
> clist
> find Q01
> quit
```

## Files

| File | Description |
|------|-------------|
| `demo_components.json` | Component database with measured values |
| `demo_connections.json` | Pin-to-pin connections |
| `demo_nets.json` | Named net assignments |
