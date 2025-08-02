import numpy as np
import pyaudio
from typing import Optional, List, Tuple
from PySide6.QtCore import QObject, Signal


class AudioManager(QObject):
    rms_level_changed = Signal(float)
    
    def __init__(self) -> None:
        super().__init__()
        self._audio = pyaudio.PyAudio()
        self._stream: Optional[pyaudio.Stream] = None
        self._gain: float = 1.0
        self._sample_rate = 44100
        self._chunk_size = 1024
        self._format = pyaudio.paFloat32
        
    def get_input_devices(self) -> List[Tuple[int, str]]:
        devices = []
        try:
            for i in range(self._audio.get_device_count()):
                device_info = self._audio.get_device_info_by_index(i)
                if (device_info['maxInputChannels'] > 0 and 
                    device_info['hostApi'] == 0):
                    devices.append((i, device_info['name']))
        except Exception as e:
            print(f"Error querying audio devices: {e}")
        return devices
    
    def start_stream(self, device_id: int) -> bool:
        try:
            self.stop_stream()
            
            def audio_callback(in_data, frame_count, time_info, status):
                audio_data = np.frombuffer(in_data, dtype=np.float32)
                rms = np.sqrt(np.mean(audio_data**2))
                db_level = 20 * np.log10(max(rms, 1e-10))
                self.rms_level_changed.emit(db_level)
                output_data = (audio_data * self._gain).astype(np.float32).tobytes()
                return (output_data, pyaudio.paContinue)
            
            self._stream = self._audio.open(
                format=self._format,
                channels=1,
                rate=self._sample_rate,
                input=True,
                output=True,
                input_device_index=device_id,
                frames_per_buffer=self._chunk_size,
                stream_callback=audio_callback
            )
            self._stream.start_stream()
            return True
            
        except Exception as e:
            print(f"Error starting audio stream: {e}")
            return False
    
    def stop_stream(self) -> None:
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                print(f"Error stopping audio stream: {e}")
            finally:
                self._stream = None
    
    def set_gain(self, gain_percent: int) -> None:
        self._gain = gain_percent / 50.0
    
    def is_active(self) -> bool:
        return self._stream is not None and self._stream.is_active()
    
    def __del__(self) -> None:
        self.stop_stream()
        if hasattr(self, '_audio'):
            self._audio.terminate()
