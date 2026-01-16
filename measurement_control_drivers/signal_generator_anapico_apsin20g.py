import pyvisa
import time

class AnaPico_sin20G():
    def __init__(self, Address='USB0::0x03EB::0xAFFF::121-4396D0002-1156::INSTR'):
        """
        Initialize AnaPico sin20G Signal Generator
        Address: Full VISA address string for USB connection
        """
        self.Address = Address
        self.open()

    def open(self):
        """Open connection to the instrument"""
        rm = pyvisa.ResourceManager()
        inst = rm.open_resource(self.Address)
        inst.timeout = 10000  # 10 second timeout
        self.inst = inst
        
        # Get instrument identification
        try:
            idn = inst.query('*IDN?')
            print(f"Connected to: {idn.strip()}")
        except:
            print("Connected to AnaPico sin20G (IDN query might not be supported)")
        
        return inst

    def close(self):
        """Close connection to the instrument"""
        self.enable_output(False)
        self.inst.close()

    # ==== Context manager ====
    def __enter__(self):
        # Por si alguien instancia con 'with' sin llamar a open()
        if self.inst is None:
            self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        # No suprimimos excepciones (devolvemos False)

    def set_frequency(self, frequency):
        """
        Set output frequency
        
        Parameters:
        - frequency: Frequency in Hz (typical range: ~100 kHz to 20 GHz)
        """
        LO = self.inst
        LO.write(f':FREQ {frequency}')

    def set_power(self, power):
        """
        Set output power level
        
        Parameters:
        - power: Power level in dBm
        """
        LO = self.inst
        LO.write(f':POW {power}')

    def set_amplitude(self, amplitude):
        """
        Set output amplitude (alternative to power)
        
        Parameters:
        - amplitude: Amplitude in volts (if supported)
        """
        LO = self.inst
        LO.write(f':VOLT {amplitude}')

    def enable_output(self, state=True):
        """
        Enable or disable RF output
        
        Parameters:
        - state: True to enable output, False to disable
        """
        LO = self.inst
        state_str = 'ON' if state else 'OFF'
        LO.write(f':OUTP {state_str}')

    def get_frequency(self):
        """Get current frequency setting"""
        LO = self.inst
        try:
            freq = LO.query(':FREQ?')
            return float(freq.strip())
        except:
            print("Error reading frequency")
            return None

    def get_power(self):
        """Get current power setting"""
        LO = self.inst
        try:
            power = LO.query(':POW?')
            return float(power.strip())
        except:
            print("Error reading power")
            return None

    def get_output_state(self):
        """Get current output state"""
        LO = self.inst
        try:
            state = LO.query(':OUTP?')
            return bool(int(state.strip()))
        except:
            print("Error reading output state")
            return None

    def set_reference_source(self, source='INT'):
        """
        Set reference clock source
        
        Parameters:
        - source: 'INT' for internal, 'EXT' for external reference
        """
        LO = self.inst
        LO.write(f':ROSC:SOUR {source}')

    def set_reference_frequency(self, frequency=10e6):
        """
        Set external reference frequency (if using external reference)
        
        Parameters:
        - frequency: Reference frequency in Hz (typically 10 MHz)
        """
        LO = self.inst
        LO.write(f':ROSC:EXT:FREQ {frequency}')

    def reset(self):
        """Reset instrument to default settings"""
        LO = self.inst
        LO.write('*RST')
        time.sleep(1)  # Wait for reset to complete

    def get_error(self):
        """Check for instrument errors"""
        LO = self.inst
        try:
            error = LO.query(':SYST:ERR?')
            return error.strip()
        except:
            return "Error query not supported"

    def preset(self):
        """Set instrument to preset state"""
        LO = self.inst
        try:
            LO.write(':SYST:PRES')
        except:
            print("Preset command might not be supported")

    def set_phase(self, phase):
        """
        Set output phase
        
        Parameters:
        - phase: Phase in degrees
        """
        LO = self.inst
        LO.write(f':PHAS {phase}')

    def get_phase(self):
        """Get current phase setting"""
        LO = self.inst
        try:
            phase = LO.query(':PHAS?')
            return float(phase.strip())
        except:
            print("Error reading phase")
            return None

    def configure_sine_output(self, frequency, power, enable=True):
        """
        Configure the sine wave output in one command
        
        Parameters:
        - frequency: Output frequency in Hz
        - power: Output power in dBm
        - enable: Whether to enable output (default: True)
        """
        self.set_frequency(frequency)
        self.set_power(power)
        if enable:
            self.enable_output(True)

    def get_status(self):
        """
        Get current instrument status
        Returns dictionary with frequency, power, and output state
        """
        status = {
            'frequency': self.get_frequency(),
            'power': self.get_power(),
            'output_enabled': self.get_output_state(),
            'phase': self.get_phase()
        }
        return status

    def frequency_sweep(self, start_freq, stop_freq, step_freq, dwell_time=0.1):
        """
        Perform a simple frequency sweep
        
        Parameters:
        - start_freq: Starting frequency in Hz
        - stop_freq: Stopping frequency in Hz
        - step_freq: Frequency step size in Hz
        - dwell_time: Time to wait at each frequency in seconds
        """
        current_freq = start_freq
        
        while current_freq <= stop_freq:
            self.set_frequency(current_freq)
            #self.enable_output(True)
            print(f"Frequency: {current_freq/1e6:.3f} MHz")
            time.sleep(dwell_time)
            current_freq += step_freq

    def power_sweep(self, start_power, stop_power, step_power, dwell_time=0.1):
        """
        Perform a simple power sweep
        
        Parameters:
        - start_power: Starting power in dBm
        - stop_power: Stopping power in dBm
        - step_power: Power step size in dBm
        - dwell_time: Time to wait at each power level in seconds
        """
        current_power = start_power
        
        while current_power <= stop_power:
            self.set_power(current_power)
            time.sleep(dwell_time)
            print(f"Power: {current_power} dBm")
            current_power += step_power

# Example usage:
"""
# Initialize the signal generator
lo = AnaPico_sin20G()

# Configure for 1 GHz at -10 dBm
lo.configure_sine_output(frequency=1e9, power=-10, enable=True)

# Check current settings
status = lo.get_status()
print(f"Current settings: {status}")

# Perform frequency sweep from 1 to 2 GHz
lo.frequency_sweep(start_freq=1e9, stop_freq=2e9, step_freq=100e6, dwell_time=0.5)

# Turn off output and close connection
lo.enable_output(False)
lo.close()
"""