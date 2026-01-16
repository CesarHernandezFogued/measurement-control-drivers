"""
Example: Output a sine wave on a Rigol DG922 Pro.

Edit the IP before running.
"""

from measurement_control_drivers import RigolDG922Pro


def main() -> None:
    # --- Connection ---
    awg_ip = "192.168.0.40"  # <-- change to your AWG IP
    awg = RigolDG922Pro(ip=awg_ip)

    # --- Output settings ---
    ch = 1
    freq_hz = 1_000.0
    amp_vpp = 1.0

    awg.set_waveform(channel=ch, waveform="SIN")
    awg.set_frequency(channel=ch, frequency=freq_hz)   # Hz
    awg.set_amplitude(channel=ch, amplitude=amp_vpp)   # Vpp (typical)
    awg.output_on(channel=ch)

    print(f"AWG CH{ch} ON: SIN, f = {freq_hz:.2f} Hz, A = {amp_vpp:.3f} Vpp")
    input("Press Enter to turn output OFF and exit...")

    awg.output_off(channel=ch)
    awg.close()


if __name__ == "__main__":
    main()
