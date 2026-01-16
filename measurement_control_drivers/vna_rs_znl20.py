import pyvisa
from pyvisa import VisaIOError
from typing import List, Tuple, Optional


######

### Probar con 'Ch2Trc2' en vez de 'Trc2'

######
class VNA:
    """
    Control básico de un VNA vía VISA (TCPIP/HiSLIP o VXI-11).
    """
    def __init__(self, resource: Optional[str] = None, ip: Optional[str] = None, backend: Optional[str] = None, timeout_ms: int = 5000):
        """
        resource: cadena VISA completa (p.ej. 'TCPIP0::169.254.35.96::hislip0::INSTR')
        ip: si la das, intentará hislip0 y luego inst0 automáticamente
        backend: p.ej. '@py' para pyvisa-py; None usa el backend por defecto del sistema
        """
        self.rm = pyvisa.ResourceManager(backend) if backend else pyvisa.ResourceManager()
        self.vna = None

        if resource is None and ip:
            for suffix in ("hislip0", "inst0"):
                candidate = f"TCPIP0::{ip}::{suffix}::INSTR"
                try:
                    self.vna = self.rm.open_resource(candidate)
                    resource = candidate
                    break
                except Exception:
                    continue
            if self.vna is None:
                raise RuntimeError(f"No pude abrir VISA en {ip} (hislip0 ni inst0)")
        elif resource:
            self.vna = self.rm.open_resource(resource)
        else:
            raise ValueError("Proporciona 'resource' o 'ip'")

        # Configuración de sesión
        self.vna.read_termination = '\n'
        self.vna.write_termination = '\n'
        self.vna.timeout = timeout_ms
        self.vna.chunk_size = 1024*1024  # por si luego lees trazas

        # Limpia errores previos
        self.write("*CLS")
        # Identifica y guarda perfil
        idn = self.query("*IDN?").strip()
        self.idn = idn
        self.vendor = idn.split(',')[0].upper() if ',' in idn else idn.upper()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # --- utilidades básicas ---
    def write(self, cmd: str) -> None:
        try:
            self.vna.write(cmd)
        except VisaIOError as e:
            raise RuntimeError(f"VISA write error en '{cmd}': {e}")

    def query(self, cmd: str) -> str:
        try:
            return self.vna.query(cmd)
        except VisaIOError as e:
            raise RuntimeError(f"VISA query error en '{cmd}': {e}")

    def check_errors(self) -> List[str]:
        """Drena la cola de errores SCPI."""
        errors = []
        for _ in range(20):  # evita bucles infinitos
            err = self.query("SYST:ERR?")
            errors.append(err.strip())
            if err.startswith("0"):
                break
        return errors

    def close(self):
        try:
            if self.vna:
                self.vna.close()
        finally:
            try:
                self.rm.close()
            except Exception:
                pass

    # --- flujo típico de inicialización ---
    def reset(self, wait: bool = True):
        self.write("*CLS")
        self.write("*RST")
        if wait:
            _ = self.query("*OPC?")  # espera a que termine el reset

    def get_trace_name(self, window: int = 1, trace: int = 1) -> str:
        """
        Devuelve el nombre de la medida asociada a una traza en la ventana.
        """
        return self.query("CALC1:PAR:CAT?")


    # --- canal/traza/marker ---
    def select_or_create_trace(self, name="Trc1", sparam="S21", window=1, trace=1):
        """
        R&S ZNL/ZNB: define un parámetro Sxx y lo vincula a una traza visible. 
        - name: nombre lógico del parámetro/trace ('Trc1') 
        - sparam: 'S11', 'S21', 'S12', 'S22' (SIN comillas en SCPI) 
        - window: índice de ventana DISPLAY (normalmente 1) 
        """ 
    
        # Crear y mostrar la medida (nota: sparam entre comillas para MEAS)
        self.write(f"CALC{window}:PAR:MEAS '{name}','{sparam}'")
        self.write(f"CALC{window}:PAR:SEL '{name}'")
        return self.query("SYST:ERR?")


    # def select_or_create_trace(self, name: str = "Trc1", sparam: str = "S12", window: int = 1, trace: int = 1): 
    #     """ R&S ZNL/ZNB: define un parámetro Sxx y lo vincula a una traza visible. 
    #     - name: nombre lógico del parámetro/trace ('Trc1') 
    #     - sparam: 'S11', 'S21', 'S12', 'S22' (SIN comillas en SCPI) 
    #     - window: índice de ventana DISPLAY (normalmente 1) 
    #     - trace: índice de traza en esa ventana (1..N) """ 
    #     # 0) Ventana ON (por si acaso) 
    #     self.write(f"DISP:WIND{window}:STATE ON") 
    #     # 1) Asegura que hay, como mínimo, 'trace' trazas en el canal 
    #     self.write(f"CALC{window}:PAR:COUN {max(1, trace)}") 
    #     # 2) Define el parámetro (OJO: Sxx SIN comillas en R&S) 
    #     self.write(f"CALC{window}:PAR:DEF '{name}', {sparam}") 
    #     # 3) Selección del parámetro (opcional) 
    #     self.write(f"CALC{window}:PAR:SEL '{name}'") 
    #     # 4) Alimenta la traza visible de esa ventana con el parámetro 
    #     self.write(f"DISP:WIND{window}:TRAC{trace}:FEED '{name}'") 
    #     # 5) Comprobar que no quedan errores 
    #     err = self.query("SYST:ERR?") 
    #     return err
        
        

    def set_span(self, start_freq: float, stop_freq: float, points: int = 201):
        """
        Configure the frequency span of the sweep.
        
        Parameters:
            start_freq (float): Start frequency in Hz.
            stop_freq (float): Stop frequency in Hz.
            points (int): Number of sweep points (default: 201).
        """
        if stop_freq <= start_freq:
            raise ValueError("Stop frequency must be greater than start frequency")
    
        self.write(f"SENS:FREQ:STAR {start_freq}")
        self.write(f"SENS:FREQ:STOP {stop_freq}")
        self.write(f"SENS:SWE:POIN {points}")

    def set_marker(self, idx: int, on: bool = True):
        self.write(f"CALC:MARK{idx}:STAT {'ON' if on else 'OFF'}")

    def set_marker_x(self, idx: int, freq_hz: float):
        # opcional: validar contra sweep
        f_start = float(self.query("SENS:FREQ:STAR?"))
        f_stop  = float(self.query("SENS:FREQ:STOP?"))
        if not (f_start <= freq_hz <= f_stop):
            raise ValueError(f"Frecuencia {freq_hz} fuera del sweep [{f_start}, {f_stop}]")
        self.write(f"CALC:MARK{idx}:X {freq_hz}")

    def get_marker_xy(self, idx: int) -> Tuple[float, float]:
        x = float(self.query(f"CALC:MARK{idx}:X?"))
        y = float(self.query(f"CALC:MARK{idx}:Y?"))
        return x, y

    def active_markers(self) -> List[int]:
        # intenta descubrir cuántos marcadores soporta/activos (método sencillo)
        actives = []
        for i in range(1, 11):  # prueba 1..10
            try:
                state = int(float(self.query(f"CALC:MARK{i}:STAT?")))
                if state == 1:
                    actives.append(i)
            except Exception:
                break
        return actives

    def get_all_marker_xy(self) -> List[Tuple[int, float, float]]:
        """
        Devuelve una lista con las coordenadas (frecuencia, valor)
        de todos los marcadores activos.
    
        Returns:
            List[Tuple[int, float, float]]:
                [(número, frecuencia_Hz, valor_Y), ...]
        """
        results = []
        actives = self.active_markers()
        for idx in actives:
            x, y = self.get_marker_xy(idx)
            results.append((idx, x, y))
        return results

    def clear_markers(self, max_markers: int = 10):
        """
        Apaga/borrra todos los marcadores hasta max_markers.
        
        Parameters:
            max_markers (int): Número máximo de marcadores a probar (default = 10).
        """
        for i in range(1, max_markers + 1):
            try:
                self.write(f"CALC:MARK{i}:STAT OFF")
            except Exception as e:
                print(f"Error al intentar borrar marcador {i}: {e}")
                break



'''
# Versión previa
class VNA_DisplayControl:
    def __init__(self, ip_address='169.254.35.96'):
        self.address = f'TCPIP0::{ip_address}::hislip0::INSTR'
        self.rm = pyvisa.ResourceManager()
        self.vna = self.rm.open_resource(self.address)
        self.vna.read_termination = '\n'
        self.vna.write_termination = '\n'

    def close(self):
        self.vna.close()

    def identify(self):
        return self.vna.query("*IDN?")

    def reset(self):
        self.vna.write("*RST")

    def clear_markers(self):
        for i in range(1, 4):
            self.vna.write(f"CALC:MARK{i}:STAT OFF")

    def setup_markers(self):
        # Turn on three markers on trace 1
        for i in range(1, 4):
            self.vna.write(f"CALC:MARK{i}:STAT ON")

    def set_marker_position(self, marker_number, frequency_hz):
        self.vna.write(f"CALC:MARK{marker_number}:X {frequency_hz}")

    def get_marker_position(self, marker_number):
        freq = self.vna.query(f"CALC:MARK{marker_number}:X?")
        return float(freq)

    def get_marker_amplitude(self, marker_number):
        amp = self.vna.query(f"CALC:MARK{marker_number}:Y?")
        return float(amp)

    def get_all_marker_data(self):
        marker_data = []
        for i in range(1, 4):
            freq = self.get_marker_position(i)
            amp = self.get_marker_amplitude(i)
            marker_data.append((i, freq, amp))
        return marker_data
'''