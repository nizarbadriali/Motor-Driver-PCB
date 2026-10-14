#!/usr/bin/env python3

import glob
import sys
import numpy as np

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

DAT_FILES_PATTERN = 'workdir/*.dat'

# ===== Design parameters =====
# PLACEHOLDERS: the schematic labels these parts only as "R" / "R_Shunt".
# Replace with the real values before trusting any output.
R_SHUNT = 0.1        # R1, R2 sense resistors (ohms), Vishay WSKW0612 footprint
R_IN = 10e3          # Difference-amp input resistors (ohms)
R_F = 100e3          # Difference-amp feedback / reference resistors (ohms)
VCC = 5.0            # LM358 supply (V)

# Datasheet figures
DRV8833_ISEN_TRIP = 0.200   # V: DRV8833 starts current chopping when xISEN reaches 200 mV
LM358_HEADROOM = 1.5        # V: LM358 output typically swings to about VCC - 1.5 V
LM358_V_OL = 0.02           # V: approximate output low level with a light load


def sense_chain(current: np.ndarray, r_shunt: float, r_in: float, r_f: float, vcc: float):
    """
    Low-side shunt followed by a 4-resistor difference amplifier.

    Vsense = I * Rshunt
    Vout   = (Rf / Rin) * Vsense, clamped to the LM358 output swing

    Args:
        current: Motor winding current array (A)
        r_shunt: Sense resistor (ohms)
        r_in: Difference-amp input resistor (ohms)
        r_f: Difference-amp feedback resistor (ohms)
        vcc: Op-amp supply (V)

    Returns:
        Tuple: (v_sense, v_out_ideal, v_out, p_shunt)
    """
    gain = r_f / r_in
    v_sense = current * r_shunt
    v_out_ideal = gain * v_sense
    v_out = np.clip(v_out_ideal, LM358_V_OL, vcc - LM358_HEADROOM)
    p_shunt = current ** 2 * r_shunt
    return v_sense, v_out_ideal, v_out, p_shunt


def main():
    """Main entry point - runs every current sweep in workdir/ through the sense chain."""

    print(f"\n{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════╗")
    print(f"║   Motor Driver Current-Sense Model   ║")
    print(f"║   DRV8833 shunt + LM358 diff amp     ║")
    print(f"╚══════════════════════════════════════╝{Colors.ENDC}\n")

    datFiles = glob.glob(DAT_FILES_PATTERN)

    if not datFiles:
        print(f"{Colors.RED}✗ No data files found matching: \"{DAT_FILES_PATTERN}\"{Colors.ENDC}")
        print(f"  Make sure .dat files are in: workdir/")
        sys.exit(1)

    print(f"{Colors.GREEN}✓ Found {len(datFiles)} data file(s){Colors.ENDC}\n")

    gain = R_F / R_IN
    i_trip = DRV8833_ISEN_TRIP / R_SHUNT
    i_sat = (VCC - LM358_HEADROOM) / (gain * R_SHUNT)

    print(f"{Colors.BOLD}Parameters (placeholders until confirmed):{Colors.ENDC}")
    print(f"  Rshunt = {R_SHUNT:g} Ω   Rin = {R_IN:g} Ω   Rf = {R_F:g} Ω   VCC = {VCC:g} V")
    print(f"  Amplifier gain:            {gain:.2f} V/V  ({gain * R_SHUNT:.3f} V/A)")
    print(f"  DRV8833 chopping current:  {i_trip:.3f} A  (200 mV / Rshunt)")
    print(f"  LM358 saturation current:  {i_sat:.3f} A  (output reaches VCC - {LM358_HEADROOM} V)\n")

    for datFile in datFiles:
        print(f"{Colors.BLUE}Processing:{Colors.ENDC} {datFile}")

        try:
            current = np.atleast_1d(np.loadtxt(datFile, ndmin=2)[:, 0])
            v_sense, v_ideal, v_out, p_shunt = sense_chain(current, R_SHUNT, R_IN, R_F, VCC)

            print(f"  {'I (A)':>8} {'Vsense (mV)':>12} {'Vout (V)':>10} {'Pshunt (mW)':>12}  Notes")
            for i, vs, vi, vo, p in zip(current, v_sense, v_ideal, v_out, p_shunt):
                notes = []
                if i >= i_trip:
                    notes.append(f"{Colors.YELLOW}DRV8833 chopping{Colors.ENDC}")
                if vi > vo:
                    notes.append(f"{Colors.RED}op-amp saturated{Colors.ENDC}")
                print(f"  {i:8.3f} {vs * 1e3:12.1f} {vo:10.3f} {p * 1e3:12.1f}  {', '.join(notes)}")
            print()

        except Exception as e:
            print(f"{Colors.RED}✗ Error processing {datFile}: {str(e)}{Colors.ENDC}\n")
            continue

if __name__ == '__main__':
    main()
