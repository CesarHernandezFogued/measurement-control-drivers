"""
Example: Set a CW LO tone using an AnaPico APSIN20G signal generator.

Edit the VISA resource string before running.
"""

from measurement_control_drivers import SignalGenerator


def main() -> None:
    # --- Connection ---
    resource = "TCPIP0::192.168.0.20::INSTR"  # <-- change to your SG VISA resource
    sg = SignalGenerator(resource)

    # --- LO settings ---
    lo_freq_hz = 10.0e9
    lo_power_dbm = -5.0

    sg.set_frequency(lo_freq_hz)   # Hz
    sg.set_power(lo_power_dbm)     # dBm
    sg.rf_on()

    print(f"LO ON: f = {lo_freq_hz/1e9:.6f} GHz, P = {lo_power_dbm:.2f} dBm")
    input("Press Enter to turn RF OFF and exit...")

    sg.rf_off()
    sg.close()


if __name__ == "__main__":
    main()
