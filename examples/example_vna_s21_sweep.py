"""
Example: Acquire an S21 sweep from a Rohde & Schwarz ZNL20 VNA.

Edit the IP (or VISA resource string) before running.
"""

from measurement_control_drivers import VNA


def main() -> None:
    # --- Connection ---
    vna_ip = "192.168.0.30"  # <-- change to your VNA IP
    vna = VNA(ip=vna_ip)

    # --- Basic sweep configuration ---
    center_hz = 6.0e9
    span_hz = 200e6
    npoints = 1601

    vna.set_center_frequency(center_hz)
    vna.set_span(span_hz)
    vna.set_sweep_points(npoints)

    # Optional (if your driver supports it)
    # vna.set_if_bandwidth(1e3)   # Hz
    # vna.set_power(-20)          # dBm

    # --- Acquisition ---
    # Expected: (freq_Hz, complex_S21) or (freq_Hz, mag, phase), depending on your implementation
    data = vna.get_trace_data()

    # Print a small preview
    try:
        freq_hz, s21 = data
        print(f"Acquired {len(freq_hz)} points.")
        print(f"f[0]={freq_hz[0]:.3e} Hz, f[-1]={freq_hz[-1]:.3e} Hz")
        print(f"S21[0]={s21[0]}")
    except Exception:
        print("Trace acquired. Driver returned:", type(data), "with length/shape:", getattr(data, "shape", None))

    vna.close()


if __name__ == "__main__":
    main()
