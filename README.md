# measurement-control-drivers

Python drivers (PyVISA/SCPI) and small helpers to control common microwave lab instruments from a measurement computer. This repository was used to automate acquisitions for cavity transmission characterization and proof-of-principle frequency-conversion tests (LO/RF/AWG + mixer).

## Supported instruments

- **Rohde & Schwarz ZNL20** (VNA) — `vna_rs_znl20.py`
- **AnaPico APSIN20G** (Microwave Signal Generator / LO) — `signal_generator_anapico_apsin20g.py`
- **Rigol DG922 Pro** (AWG) — `awg_rigol_dg922pro.py`
- **Generic SCPI Spectrum Analyzer** (template/interface) — `spectrum_analyzer_scpi.py`

> Note: SCPI command sets can vary across firmware revisions and across spectrum analyzer models. The spectrum analyzer module is intended as a lightweight SCPI wrapper that you can adapt to your specific unit.

## Installation

1) Create and activate a virtual environment (recommended).
2) Install dependencies:

```bash
pip install -r requirements.txt
