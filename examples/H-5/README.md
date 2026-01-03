# H-5 Humidistat Example

This is a complete reverse engineering of a Dampp-Chaser H-5 piano humidistat control board.

## About the H-5

The Dampp-Chaser H-5 is a humidity control system used in pianos. The control board monitors:
- Water level sensor (via RJ12 jack J01)
- Humidity pads sensor (via 3.5mm jack J02)
- LED panel connection (via RJ12 jack J04)

It controls:
- Humidifier outlet (HU01)
- Dehumidifier outlet (DH01)
- Mechanical humidistat switch (HS01)

## Project Statistics

- **Components**: 81
- **Connections**: 156
- **Named Nets**: 50

## Key Circuits

### Power Supply
- T01: 120V to 9V transformer
- Q14: AMS1117-5.0 voltage regulator (5V LDO)
- C10: 470uF main filter capacitor
- D08, R35: Power clamp circuit

### Water Level Detection
- J01: RJ12 water sensor input
- Q03, Q04: Water amplifier and comparator
- Q05: BC847A water feedback transistor
- D01, D02: Dual diode protection

### Humidity Pads Detection
- J02: 3.5mm audio jack sensor input
- Q06, Q07: Pads amplifier stage
- Q08, Q09, Q10: Pads comparator and output
- D04, D05: Dual diode protection

### LED Flasher
- Q11, Q12: Oscillator transistors
- C09: 1uF timing capacitor (CRITICAL)
- R31, R32, R33: Timing resistors (330k, 470k, 220k)
- R34: 220R flasher output resistor

### AC Output Control
- Q13: MOC3063 optocoupler
- HS01: Mechanical humidistat switch
- HU01, DH01: AC outlets for humidifier/dehumidifier

## Using This Example

```bash
# Load the H-5 project
python3 ../../pcb_reverse.py H-5

# View statistics
> stats

# View all nets
> nets

# Export all formats
> all
```

## Files

| File | Description |
|------|-------------|
| `H-5_components.json` | 81 components with values and descriptions |
| `H-5_connections.json` | 156 pin-to-pin connections |
| `H-5_nets.json` | 50 named nets |

## Notes

- Components marked "TBD" have unknown values (require measurement)
- Components marked "DNP" are not populated on the board
- The NC (No Connect) component collects all unused/floating pins
