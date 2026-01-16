# -*- coding: utf-8 -*-
"""
Created on Mon Oct 13 14:03:52 2025

@author: usuario
"""
import pyvisa
from pyvisa import VisaIOError
from typing import List, Tuple, Optional, Union

class SpectrumAnalyzer:
    """
    Control básico de un Analizador de Espectros vía VISA (TCPIP/HiSLIP o VXI-11).
    Probado con SCPI genérico (R&S FSV/FSW/ZNL-SA, Keysight X-Series). Implementa
    helpers para probar variantes SCPI cuando difieren por fabricante.
    """
    def __init__(self,
                 resource: Optional[str] = None,
                 ip: Optional[str] = None,
                 backend: Optional[str] = None,
                 timeout_ms: int = 10000):
        """
        resource: cadena VISA completa (p.ej. 'TCPIP0::169.254.35.97::hislip0::INSTR')
        ip: si la das, intentará hislip0 y luego inst0 automáticamente
        backend: '@py' para pyvisa-py; None usa backend por defecto del sistema
        """
        self.rm = pyvisa.ResourceManager(backend) if backend else pyvisa.ResourceManager()
        self.sa = None

        if resource is None and ip:
            for suffix in ("hislip0", "inst0"):
                candidate = f"TCPIP0::{ip}::{suffix}::INSTR"
                try:
                    self.sa = self.rm.open_resource(candidate)
                    resource = candidate
                    break
                except Exception:
                    continue
            if self.sa is None:
                raise RuntimeError(f"No pude abrir VISA en {ip} (hislip0 ni inst0)")
        elif resource:
            self.sa = self.rm.open_resource(resource)
        else:
            raise ValueError("Proporciona 'resource' o 'ip'")

        # Sesión
        self.sa.read_termination = '\n'
        self.sa.write_termination = '\n'
        self.sa.timeout = timeout_ms
        self.sa.chunk_size = 1024 * 1024

        # Limpieza e identificación
        self.write("*CLS")
        self.idn = self.query("*IDN?").strip()
        self.vendor = (self.idn.split(',')[0] if ',' in self.idn else self.idn).upper()

    # ---------- Context manager ----------
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        self.close()

    # ---------- Básicos ----------
    def write(self, cmd: str) -> None:
        try:
            self.sa.write(cmd)
        except VisaIOError as e:
            raise RuntimeError(f"VISA write error en '{cmd}': {e}")

    def query(self, cmd: str) -> str:
        try:
            return self.sa.query(cmd)
        except VisaIOError as e:
            raise RuntimeError(f"VISA query error en '{cmd}': {e}")

    def _try_write_any(self, cmds: List[str]) -> None:
        """
        Prueba a ejecutar la primera variante SCPI que no dé error (para compatibilidad).
        """
        last_err = None
        for c in cmds:
            try:
                self.write(c)
                return
            except Exception as e:
                last_err = e
        raise last_err if last_err else RuntimeError("No SCPI variant worked")

    def _try_query_any(self, cmds: List[str]) -> str:
        last_err = None
        for c in cmds:
            try:
                return self.query(c)
            except Exception as e:
                last_err = e
        raise last_err if last_err else RuntimeError("No SCPI variant worked")

    def check_errors(self, max_reads: int = 20) -> List[str]:
        errs = []
        for _ in range(max_reads):
            err = self.query("SYST:ERR?")
            errs.append(err.strip())
            if err.startswith("0"):
                break
        return errs

    def close(self):
        try:
            if self.sa:
                self.sa.close()
        finally:
            try:
                self.rm.close()
            except Exception:
                pass

    # ---------- Inicialización ----------
    def reset(self, wait: bool = True):
        self.write("*CLS")
        self.write("*RST")
        if wait:
            _ = self.query("*OPC?")   # espera a fin de reset

    # ---------- Barridos / frecuencia ----------
    def set_span(self, start_hz: float, stop_hz: float, points: int = 1001):
        if stop_hz <= start_hz:
            raise ValueError("stop_hz debe ser mayor que start_hz")
        self._try_write_any([f"FREQ:STAR {start_hz}", f"SENS:FREQ:STAR {start_hz}"])
        self._try_write_any([f"FREQ:STOP {stop_hz}", f"SENS:FREQ:STOP {stop_hz}"])
        # puntos (varía SENS: / SWE: según vendor)
        self._try_write_any([f"SWE:POIN {points}", f"SENS:SWE:POIN {points}"])

    def set_center_span(self, center_hz: float, span_hz: float, points: int = 1001):
        if span_hz <= 0:
            raise ValueError("span_hz debe ser > 0")
        self._try_write_any([f"FREQ:CENT {center_hz}", f"SENS:FREQ:CENT {center_hz}"])
        self._try_write_any([f"FREQ:SPAN {span_hz}", f"SENS:FREQ:SPAN {span_hz}"])
        self._try_write_any([f"SWE:POIN {points}", f"SENS:SWE:POIN {points}"])

    def get_start_stop(self) -> Tuple[float, float]:
        f_start = float(self._try_query_any(["FREQ:STAR?", "SENS:FREQ:STAR?"]))
        f_stop  = float(self._try_query_any(["FREQ:STOP?", "SENS:FREQ:STOP?"]))
        return f_start, f_stop

    def set_sweep_time(self, seconds: float, auto: bool = False):
        if auto:
            self._try_write_any(["SWE:TIME:AUTO ON", "SENS:SWE:TIME:AUTO ON"])
        else:
            self._try_write_any(["SWE:TIME:AUTO OFF", "SENS:SWE:TIME:AUTO OFF"])
            self._try_write_any([f"SWE:TIME {seconds}", f"SENS:SWE:TIME {seconds}"])

    def set_points(self, points: int):
        self._try_write_any([f"SWE:POIN {points}", f"SENS:SWE:POIN {points}"])

    # ---------- Resolución / Detector ----------
    def set_rbw_vbw(self, rbw_hz: Optional[float] = None,
                    vbw_hz: Optional[float] = None,
                    rbw_auto: Optional[bool] = None,
                    vbw_auto: Optional[bool] = None):
        if rbw_auto is not None:
            self._try_write_any([f"BAND:AUTO {'ON' if rbw_auto else 'OFF'}",
                                 f"SENS:BAND:AUTO {'ON' if rbw_auto else 'OFF'}"])
        if rbw_hz is not None:
            self._try_write_any([f"BAND {rbw_hz}", f"SENS:BAND {rbw_hz}"])
        if vbw_auto is not None:
            self._try_write_any([f"BAND:VID:AUTO {'ON' if vbw_auto else 'OFF'}",
                                 f"SENS:BAND:VID:AUTO {'ON' if vbw_auto else 'OFF'}"])
        if vbw_hz is not None:
            self._try_write_any([f"BAND:VID {vbw_hz}", f"SENS:BAND:VID {vbw_hz}"])

    def set_detector(self, mode: str = "POS"):
        """
        mode: 'POS' (positive), 'NEG', 'SAMP', 'AVER', 'RMS', 'QPE'...
        """
        mode = mode.upper()
        self._try_write_any([f"DET {mode}", f"SENS:DET {mode}"])

    # ---------- Nivel / Entrada ----------
    def set_reference_level(self, level_dbm: float):
        self._try_write_any([f"DISP:WIND:TRAC:Y:RLEV {level_dbm}",
                             f"DISP:TRAC:Y:RLEV {level_dbm}",
                             f"DISP:WIND1:TRAC1:Y:RLEV {level_dbm}"])

    def set_attenuation(self, att_db: Optional[float] = None, auto: Optional[bool] = None):
        if auto is not None:
            self._try_write_any([f"INP:ATT:AUTO {'ON' if auto else 'OFF'}",
                                 f"SENS:POW:ATT:AUTO {'ON' if auto else 'OFF'}"])
        if att_db is not None:
            self._try_write_any([f"INP:ATT {att_db}", f"SENS:POW:ATT {att_db}"])

    def set_preamp(self, on: bool = True):
        # R&S: INP:GAIN:STAT ON; Keysight: PREENable/POW:GAIN?
        if "ROHDE" in self.vendor or "R&S" in self.vendor:
            self._try_write_any([f"INP:GAIN:STAT {'ON' if on else 'OFF'}"])
        else:
            # Muchas Keysight usan "POW:GAIN" o "POW:GAIN:STAT"
            self._try_write_any([f"POW:GAIN {'ON' if on else 'OFF'}",
                                 f"POW:GAIN:STAT {'ON' if on else 'OFF'}"])

    # ---------- Promedios ----------
    def set_averaging(self, on: bool, count: Optional[int] = None, clear: bool = False):
        self._try_write_any([f"AVER:STAT {'ON' if on else 'OFF'}", f"SENS:AVER:STAT {'ON' if on else 'OFF'}"])
        if count is not None:
            self._try_write_any([f"AVER:COUN {count}", f"SENS:AVER:COUN {count}"])
        if clear:
            self._try_write_any(["AVER:CLE", "SENS:AVER:CLE"])

    # ---------- Trigger / Barrido ----------
    def continuous(self, on: bool = True):
        self._try_write_any([f"INIT:CONT {'ON' if on else 'OFF'}", f"SENS:INIT:CONT {'ON' if on else 'OFF'}"])

    def single_sweep(self, wait: bool = True):
        # Desactiva continuo, lanza barrido y espera
        self.continuous(False)
        self._try_write_any(["INIT:IMM", "INIT"])
        if wait:
            _ = self.query("*OPC?")

    # ---------- Lectura de traza ----------
    def fetch_trace(self, trace: Union[int, str] = 1) -> List[float]:
        """
        Lee amplitud de la traza (normalmente en dBm). Devuelve lista de floats.
        Nota: muchas SAs sólo devuelven Y; X se reconstruye con start/stop/puntos.
        """
        trc = f"TRACE{trace}" if isinstance(trace, int) else str(trace)
        data_str = self._try_query_any([f"TRAC:DATA? {trc}", f"TRAC? {trc}", "TRAC:DATA?"])
        # Puede venir separado por comas o espacios
        parts = data_str.replace('\n', ',').replace(';', ',').split(',')
        vals = []
        for p in parts:
            p = p.strip()
            if p:
                try:
                    vals.append(float(p))
                except ValueError:
                    # Algunos equipos devuelven cabeceras binarias si no están en ASCII
                    # En ese caso se debe configurar formato ASCII:
                    # self.write("FORM ASC")
                    pass
        if not vals:
            # Forzar formato ASCII y reintentar una vez
            self._try_write_any(["FORM ASC", "FORM:DATA ASC"])
            data_str = self._try_query_any([f"TRAC:DATA? {trc}", f"TRAC? {trc}", "TRAC:DATA?"])
            vals = [float(x) for x in data_str.replace('\n', ',').split(',') if x.strip()]
        return vals

    def get_frequency_axis(self) -> List[float]:
        """
        Reconstruye el eje X lineal con start/stop/puntos actuales.
        """
        f_start, f_stop = self.get_start_stop()
        points = int(float(self._try_query_any(["SWE:POIN?", "SENS:SWE:POIN?"])))
        if points < 2:
            return [f_start]
        step = (f_stop - f_start) / (points - 1)
        return [f_start + i * step for i in range(points)]

    # ---------- Marcadores ----------
    def set_marker(self, idx: int, on: bool = True):
        self._try_write_any([f"CALC:MARK{idx}:STAT {'ON' if on else 'OFF'}",
                             f"CALC:MARKER{idx}:STATE {'ON' if on else 'OFF'}"])

    def set_marker_x(self, idx: int, freq_hz: float):
        f_start, f_stop = self.get_start_stop()
        if not (f_start <= freq_hz <= f_stop):
            raise ValueError(f"Frecuencia {freq_hz} fuera de span [{f_start}, {f_stop}]")
        self._try_write_any([f"CALC:MARK{idx}:X {freq_hz}",
                             f"CALC:MARKER{idx}:X {freq_hz}"])

    def get_marker_xy(self, idx: int) -> Tuple[float, float]:
        x = float(self._try_query_any([f"CALC:MARK{idx}:X?", f"CALC:MARKER{idx}:X?"]))
        y = float(self._try_query_any([f"CALC:MARK{idx}:Y?", f"CALC:MARKER{idx}:Y?"]))
        return x, y

    def clear_markers(self, max_markers: int = 10):
        for i in range(1, max_markers + 1):
            try:
                self.set_marker(i, False)
            except Exception:
                break

    def peak_search(self, idx: int = 1):
        """
        Coloca el marcador idx en el pico máximo de la traza actual.
        """
        # R&S y Keysight soportan CALC:MARKn:MAX
        self._try_write_any([f"CALC:MARK{idx}:MAX", f"CALC:MARKER{idx}:MAX"])
        # asegúrate de que esté ON
        self.set_marker(idx, True)

    def next_peak(self, idx: int = 1, direction: str = "NEXT"):
        """
        Salta al siguiente/previo pico. direction: 'NEXT' o 'LEFT'/'PREV'
        """
        direction = direction.upper()
        if direction in ("NEXT", "RIGHT"):
            self._try_write_any([f"CALC:MARK{idx}:MAX:NEXT", f"CALC:MARKER{idx}:MAX:NEXT"])
        else:
            self._try_write_any([f"CALC:MARK{idx}:MAX:LEFT", f"CALC:MARKER{idx}:MAX:LEFT"])
        self.set_marker(idx, True)

    def marker_delta_mode(self, on: bool = True, ref_idx: int = 1, del_idx: int = 2):
        """
        Activa modo delta (Mdel = Mdel - Mref). En muchos equipos se hace
        activando 'DELT' sobre el marcador secundario.
        """
        if on:
            # Selección de marcador delta y habilitar función DELT
            self._try_write_any([
                f"CALC:MARK{del_idx}:FUNC:TYPE DELT; CALC:MARK{del_idx}:FUNC:STAT ON",
                f"CALC:MARKER{del_idx}:FUNC:TYPE DELT; CALC:MARKER{del_idx}:FUNC:STATE ON",
                f"CALC:MARK{del_idx}:MODE DELT",  # variante
            ])
            # Posiciona el ref por si acaso (no todos requieren referenciar explícitamente)
            self.set_marker(ref_idx, True)
            self.set_marker(del_idx, True)
        else:
            self._try_write_any([
                f"CALC:MARK{del_idx}:FUNC:STAT OFF",
                f"CALC:MARKER{del_idx}:FUNC:STATE OFF",
            ])

    def get_delta_reading(self, ref_idx: int = 1, del_idx: int = 2) -> Tuple[float, float]:
        """
        Devuelve (DeltaFreq_Hz, DeltaAmp_dB) entre Mdel y Mref. En equipos sin
        lectura directa, se calcula restando coordenadas.
        """
        # Intento de lectura directa (no todos la tienen)
        try:
            df = float(self._try_query_any([
                f"CALC:MARK{del_idx}:DELT:X?",
                f"CALC:MARKER{del_idx}:DELTA:X?"
            ]))
            da = float(self._try_query_any([
                f"CALC:MARK{del_idx}:DELT:Y?",
                f"CALC:MARKER{del_idx}:DELTA:Y?"
            ]))
            return df, da
        except Exception:
            # Cálculo manual
            x1, y1 = self.get_marker_xy(ref_idx)
            x2, y2 = self.get_marker_xy(del_idx)
            return (x2 - x1, y2 - y1)

    def active_markers(self, max_markers: int = 10) -> List[int]:
        actives = []
        for i in range(1, max_markers + 1):
            try:
                st = float(self._try_query_any([f"CALC:MARK{i}:STAT?", f"CALC:MARKER{i}:STATE?"]))
                if int(st) == 1:
                    actives.append(i)
            except Exception:
                break
        return actives

    # ---------- Utilidades varias ----------
    def set_unit_power(self, unit: str = "DBM"):
        unit = unit.upper()
        self._try_write_any([f"UNIT:POW {unit}", f"SENS:UNIT:POW {unit}"])

    def set_trace_detector_view(self, trace: int = 1, average_display: bool = False):
        """
        Control del modo de visualización de traza (si el equipo lo soporta).
        average_display=True muestra traza promediada (si hay averaging activo).
        """
        mode = "AVER" if average_display else "WRIT"
        self._try_write_any([
            f"DISP:TRAC{trace}:MODE {mode}",
            f"DISP:WIND1:TRAC{trace}:MODE {mode}",
        ])

    def screenshot_png(self, filepath: str = "sa_screenshot.png"):
        """
        Intenta guardar una captura en el instrumento y transferirla (si soportado).
        Ajusta rutas SCPI según equipo si fuese necesario.
        """
        try:
            # En muchos R&S:
            self.write("HCOP:DEV:LANG PNG")
            self.write(f"MMEM:NAME '{filepath}'")
            self.write("HCOP:IMM")
            _ = self.query("*OPC?")
        except Exception:
            pass
        # Nota: transferir archivo desde el equipo puede requerir MMEM:DATA? o conexión SFTP.

# -------------------- Ejemplo de uso --------------------
if __name__ == "__main__":
    # Cambia IP o resource según tu equipo:
    ip = "169.254.35.97"
    with SpectrumAnalyzer(ip=ip) as sa:
        print("IDN:", sa.idn)

        # Config básico
        sa.reset(wait=True)
        sa.set_center_span(center_hz=5e9, span_hz=200e6, points=2001)
        sa.set_rbw_vbw(rbw_hz=100e3, vbw_hz=100e3)  # RBW/VBW 100 kHz
        sa.set_detector("POS")
        sa.set_reference_level(-10)  # dBm
        sa.set_attenuation(auto=True)
        sa.set_preamp(on=False)
        sa.set_averaging(on=False)

        # Barrido único y lectura de traza
        sa.single_sweep(wait=True)
        y = sa.fetch_trace(trace=1)
        x = sa.get_frequency_axis()
        print(f"Trace len = {len(y)}, X len = {len(x)}, X[0]={x[0]:.1f} Hz, X[-1]={x[-1]:.1f} Hz")

        # Marcadores: pico principal y siguientes
        sa.set_marker(1, True)
        sa.peak_search(1)
        f1, a1 = sa.get_marker_xy(1)
        print(f"Peak @ M1: {f1/1e9:.6f} GHz, {a1:.2f} dBm")

        sa.set_marker(2, True)
        sa.next_peak(1, "NEXT")  # mueve M1 al siguiente pico
        f2, a2 = sa.get_marker_xy(1)
        print(f"Next peak (M1): {f2/1e9:.6f} GHz, {a2:.2f} dBm")

        # Delta marker M2 respecto M1
        sa.set_marker_x(2, f2)   # coloca M2 donde estaba el segundo pico
        sa.marker_delta_mode(on=True, ref_idx=1, del_idx=2)
        df, da = sa.get_delta_reading(ref_idx=1, del_idx=2)
        print(f"Delta: dF={df/1e6:.3f} MHz, dA={da:.2f} dB")

        # Limpia marcadores
        sa.clear_markers()
