"""
Example: Read marker power on a (generic) SCPI spectrum analyzer.

Edit the IP before running.
"""

from measurement_control_drivers import SpectrumAnalyzer


def main() -> None:
    # --- Connection ---
    sa_ip = "192.168.0.50"  # <-- change to your spectrum analyzer IP
    sa = SpectrumAnalyzer(ip=sa_ip)

    # --- Basic settings ---
    center_hz = 10.0e9
    span_hz = 50.0e6
    rbw_hz = 100e3

    sa.set_center_frequency(center_hz)
    sa.set_span(span_hz)
    sa.set_rbw(rbw_hz)

    # Put marker at center (if your driver supports it)
    try:
        sa.set_marker_frequency(center_hz)
    except Exception:
        pass

    power_dbm = sa.read_marker_power()
    print(f"Marker power at ~{center_hz/1e9:.6f} GHz: {power_dbm:.2f} dBm")

    sa.close()


if __name__ == "__main__":
    main()
