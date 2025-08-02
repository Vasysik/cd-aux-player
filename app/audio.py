import locale
from typing import Optional, List, Tuple
import numpy as np
import pyaudio
from PySide6.QtCore import QObject, Signal

def _normalize_device_name(raw_name: str | bytes) -> str:
    if isinstance(raw_name, bytes):
        for enc in (
            locale.getpreferredencoding(False),
            "utf-8",
            "cp1250",
            "cp1251",
            "latin1",
        ):
            try:
                return raw_name.decode(enc)
            except UnicodeDecodeError:
                pass
        return raw_name.decode("latin1", errors="replace")
    try:
        raw_bytes = raw_name.encode("latin1")
    except UnicodeEncodeError:
        return raw_name
    for enc in ("utf-8", "cp1250", "cp1251", "latin1"):
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw_name


class AudioManager(QObject):
    rms_level_changed = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self._audio = pyaudio.PyAudio()
        self._stream: Optional[pyaudio.Stream] = None
        self._gain: float = 1.0
        self._volume_sensitivity: float = 0.5
        self._sample_rate = 44100
        self._chunk_size = 2048
        self._format = pyaudio.paInt16
        self._channels = 2

    def get_input_devices(self) -> List[Tuple[int, str]]:
        devices: List[Tuple[int, str]] = []
        try:
            default_host_api = self._audio.get_default_host_api_info()['index']
            
            for i in range(self._audio.get_device_count()):
                info = self._audio.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0 and info["hostApi"] == default_host_api:
                    name = _normalize_device_name(info["name"])
                    devices.append((i, name))
        except Exception as e:
            print("[Audio] Error querying devices:", e)
        return devices

    def start_stream(self, device_id: int) -> bool:
        try:
            self.stop_stream()
            
            device_info = self._audio.get_device_info_by_index(device_id)
            channels = min(int(device_info["maxInputChannels"]), 2)

            def audio_callback(in_data, frame_count, time_info, status):
                try:
                    audio_data = np.frombuffer(in_data, dtype=np.int16)
                    audio_float = audio_data.astype(np.float32) / 32768.0
                    
                    if channels == 2:
                        left = audio_float[0::2]
                        right = audio_float[1::2]
                        mono = (left + right) / 2
                        rms = np.sqrt(np.mean(mono**2))
                    else:
                        rms = np.sqrt(np.mean(audio_float**2))
                    
                    db_level = 20 * np.log10(max(rms, 1e-10))
                    self.rms_level_changed.emit(db_level)
                    
                    audio_float *= self._gain
                    audio_float = np.clip(audio_float, -1.0, 1.0)
                    output_data = (audio_float * 32767).astype(np.int16)
                    
                    return output_data.tobytes(), pyaudio.paContinue
                except Exception as e:
                    print(f"[Audio] Callback error: {e}")
                    return in_data, pyaudio.paContinue

            self._stream = self._audio.open(
                format=self._format,
                channels=channels,
                rate=self._sample_rate,
                input=True,
                output=True,
                input_device_index=device_id,
                frames_per_buffer=self._chunk_size,
                stream_callback=audio_callback,
            )
            self._stream.start_stream()
            print(f"[Audio] Stream started: {channels} channels, {self._sample_rate}Hz")
            return True
        except Exception as e:
            print("[Audio] Error starting stream:", e)
            return False

    def stop_stream(self) -> None:
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                print("[Audio] Error stopping stream:", e)
            finally:
                self._stream = None

    def set_gain(self, gain_percent: int) -> None:        
        if gain_percent == 0:
            self._gain = 0.0
        else:
            normalized = gain_percent / 50.0
            
            if normalized <= 1.0:
                self._gain = normalized ** 2
            else:
                max_boost = 1.0 + (self._volume_sensitivity * 1.5)
                self._gain = 1.0 + ((normalized - 1.0) * (max_boost - 1.0))

    def set_volume_sensitivity(self, sensitivity: float) -> None:
        """Установка чувствительности усиления (0.1 - 1.0)"""
        self._volume_sensitivity = sensitivity

    def is_active(self) -> bool:
        return self._stream is not None and self._stream.is_active()

    def __del__(self) -> None:
        self.stop_stream()
        if hasattr(self, "_audio"):
            self._audio.terminate()
