import pyvisa
import numpy as np

class AWG_Rigol_DG922Pro():
    def __init__(self, Address='USB0::0x1AB1::0x0646::DG9R264500967::INSTR'):
        """
        Initialize Rigol DG922Pro AWG
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
        idn = inst.query('*IDN?')
        print(f"Connected to: {idn.strip()}")
        return inst

    def close(self):
        """Close connection to the instrument"""
        self.enable_output(1,False)
        self.enable_output(2,False)
        self.inst.close()

    # ---- Context manager ----
    def __enter__(self):
        if self.inst is None:
            self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        # devolver False para no suprimir excepciones
        
    def init_and_set(self, offset, channel):
        """Initialize channel and set DC offset"""
        AWG = self.inst
        
        # Set output load to 50 ohms
        AWG.write(f':OUTP{channel}:LOAD 50')
        
        # Set DC function with offset
        AWG.write(f':SOUR{channel}:APPL:DC DEF,DEF,{offset}')
        
        return AWG

    def set_DC(self, offset, channel):
        """Set DC offset for specified channel"""
        AWG = self.inst
        AWG.write(f':SOUR{channel}:APPL:DC DEF,DEF,{offset}')

    def set_sin(self, channel, frequency, amplitude, offset, phase: float = 0.0):
        """
        Set sine wave output.
        
        Parameters:
            channel (int): Channel number (1 or 2).
            frequency (float): Frequency in Hz.
            amplitude (float): Amplitude in V (>= 0.001 V).
            offset (float): DC offset in V.
            phase (float): Phase in degrees (default = 0.0).
        """
        AWG = self.inst
        
        # Validación amplitud mínima
        if amplitude < 0.001:
            amplitude = 0.001
            print("Amplitude below minimum (0.001). Setting it to 0.001.")
        
        # Configurar seno (frecuencia, amplitud, offset)
        AWG.write(f':SOUR{channel}:APPL:SIN {frequency},{amplitude},{offset}')
        
        # Configurar fase si no es cero
        if phase != 0.0:
            AWG.write(f':SOUR{channel}:PHAS {phase}')



    def set_phase(self, channel, phase):
        """Set phase for specified channel"""
        AWG = self.inst
        AWG.write(f':SOUR{channel}:PHAS {phase}')
        
    # def set_sync_phase(self):
    #     AWG=self.inst
    #     AWG.write("SOURce:PHASe:SYNChronize",encoding='utf-8')
    
    def set_sync_phase(self):
        """Synchronize phase between channels"""
        AWG = self.inst
        AWG.write(':SOUR:PHAS:SYNC')

    def set_amplitude(self, channel, amplitude):
        """Set amplitude for specified channel"""
        AWG = self.inst
        AWG.write(f':SOUR{channel}:VOLT {amplitude}')

    def set_offset(self, channel, offset):
        """Set DC offset for specified channel"""
        AWG = self.inst
        AWG.write(f':SOUR{channel}:VOLT:OFFS {offset}')

    def set_frequency(self, channel, frequency):
        """Set frequency for specified channel"""
        AWG = self.inst
        AWG.write(f':SOUR{channel}:FREQ {frequency}')

    def enable_output(self, channel, state=True):
        """Enable or disable output for specified channel"""
        AWG = self.inst
        state_str = 'ON' if state else 'OFF'
        AWG.write(f':OUTP{channel} {state_str}')

    def set_waveform(self, channel, waveform_type='SIN'):
        """Set basic waveform type (SIN, SQU, RAMP, PULS, NOIS, DC, USER)"""
        AWG = self.inst
        AWG.write(f':SOUR{channel}:FUNC {waveform_type}')

    def setup_arbitrary_waveform(self, channel, waveform_data, sample_rate, amplitude, offset, waveform_name='USER_WAV'):
        """
        Setup arbitrary waveform for single channel
        
        Parameters:
        - channel: Channel number (1 or 2)
        - waveform_data: Numpy array of waveform points (normalized -1 to +1)
        - sample_rate: Sample rate in Hz
        - amplitude: Output amplitude in volts
        - offset: DC offset in volts
        - waveform_name: Name for the waveform in instrument memory
        """
        AWG = self.inst
        
        # Set output load
        AWG.write(f':OUTP{channel}:LOAD 50')
        
        # Clear volatile memory for this channel
        AWG.write(f':SOUR{channel}:DATA:VOL:CLE')
        
        # Ensure waveform data is in correct format and range
        waveform_data = np.asarray(waveform_data, dtype=np.float32)
        waveform_data = np.clip(waveform_data, -1.0, 1.0)  # Ensure data is in range [-1, 1]
        
        # Send binary waveform data
        AWG.write_binary_values(f':SOUR{channel}:DATA:ARB {waveform_name},', 
                               waveform_data, 
                               datatype='f', 
                               is_big_endian=False)
        
        # Select the arbitrary waveform
        AWG.write(f':SOUR{channel}:FUNC ARB')
        AWG.write(f':SOUR{channel}:FUNC:ARB {waveform_name}')
        
        # Set sample rate (if supported - this might need adjustment based on actual capabilities)
        try:
            AWG.write(f':SOUR{channel}:FUNC:ARB:SRAT {sample_rate}')
        except:
            print("Warning: Sample rate setting might not be supported in this format")
        
        # Set amplitude and offset
        AWG.write(f':SOUR{channel}:VOLT {amplitude}')
        AWG.write(f':SOUR{channel}:VOLT:OFFS {offset}')

    def setup_dual_arbitrary_waveforms(self, waveform1, waveform2, sample_rate, 
                                     offset1, offset2, amplitude1, amplitude2):
        """
        Setup arbitrary waveforms for both channels (similar to original setAWG_ARBIT_2CH)
        
        Parameters:
        - waveform1, waveform2: Numpy arrays of waveform data
        - sample_rate: Sample rate in Hz
        - offset1, offset2: DC offsets for channels 1 and 2
        - amplitude1, amplitude2: Amplitudes for channels 1 and 2
        """
        AWG = self.inst
        
        # Clear volatile memory for both channels
        AWG.write(':SOUR1:DATA:VOL:CLE')
        AWG.write(':SOUR2:DATA:VOL:CLE')
        
        # Setup Channel 1
        AWG.write(':OUTP1:LOAD 50')
        waveform1 = np.asarray(waveform1, dtype=np.float32)
        waveform1 = np.clip(waveform1, -1.0, 1.0)
        
        AWG.write_binary_values(':SOUR1:DATA:ARB MYARB1,', 
                               waveform1, 
                               datatype='f', 
                               is_big_endian=False)
        
        AWG.write(':SOUR1:FUNC ARB')
        AWG.write(':SOUR1:FUNC:ARB MYARB1')
        AWG.write(f':SOUR1:VOLT {amplitude1}')
        AWG.write(f':SOUR1:VOLT:OFFS {offset1}')
        
        # Setup Channel 2
        AWG.write(':OUTP2:LOAD 50')
        waveform2 = np.asarray(waveform2, dtype=np.float32)
        waveform2 = np.clip(waveform2, -1.0, 1.0)
        
        AWG.write_binary_values(':SOUR2:DATA:ARB MYARB2,', 
                               waveform2, 
                               datatype='f', 
                               is_big_endian=False)
        
        AWG.write(':SOUR2:FUNC ARB')
        AWG.write(':SOUR2:FUNC:ARB MYARB2')
        AWG.write(f':SOUR2:VOLT {amplitude2}')
        AWG.write(f':SOUR2:VOLT:OFFS {offset2}')
        
        # Set sample rate for both channels (if supported)
        try:
            AWG.write(f':SOUR1:FUNC:ARB:SRAT {sample_rate}')
            AWG.write(f':SOUR2:FUNC:ARB:SRAT {sample_rate}')
        except:
            print("Warning: Sample rate setting might not be supported in this format")

    def setup_trigger(self, channel, trigger_source='EXT', burst_cycles=1):
        """
        Setup trigger for burst mode
        
        Parameters:
        - channel: Channel number
        - trigger_source: 'EXT', 'INT', 'MAN'
        - burst_cycles: Number of cycles per trigger
        """
        AWG = self.inst
        
        # Enable burst mode
        AWG.write(f':SOUR{channel}:BURS:STAT ON')
        AWG.write(f':SOUR{channel}:BURS:MODE TRIG')
        AWG.write(f':SOUR{channel}:BURS:NCYC {burst_cycles}')
        
        # Set trigger source
        if trigger_source == 'EXT':
            AWG.write(f':TRIG{channel}:SOUR EXT')
        elif trigger_source == 'INT':
            AWG.write(f':TRIG{channel}:SOUR INT')
        elif trigger_source == 'MAN':
            AWG.write(f':TRIG{channel}:SOUR MAN')

    def trigger_manual(self):
        """Send manual trigger"""
        AWG = self.inst
        AWG.write('*TRG')

    def get_error(self):
        """Check for instrument errors"""
        AWG = self.inst
        error = AWG.query(':SYST:ERR?')
        return error.strip()

# Example usage:
"""
# Initialize the AWG
awg = AWG_Rigol_DG922Pro()

# Set a sine wave on channel 1
awg.set_sin(channel=1, frequency=1000, amplitude=1.0, offset=0.0)
awg.enable_output(channel=1, state=True)

# Create and upload arbitrary waveform
t = np.linspace(0, 1, 1000)
waveform = np.sin(2 * np.pi * 5 * t) * 0.5  # 5 Hz sine wave
awg.setup_arbitrary_waveform(channel=2, waveform_data=waveform, 
                            sample_rate=1000, amplitude=2.0, offset=0.5)
awg.enable_output(channel=2, state=True)

# Close connection when done
awg.close()
"""