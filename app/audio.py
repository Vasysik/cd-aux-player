import locale
from typing import Optional, List, Tuple
import numpy as np
from PySide6.QtCore import QObject, Signal, QByteArray
from PySide6.QtMultimedia import QMediaDevices, QAudioFormat, QAudioDevice, QAudioSource, QAudioSink, QAudio


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
        self._audio_source: Optional[QAudioSource] = None
        self._audio_sink: Optional[QAudioSink] = None
        self._input_device: Optional[QAudioDevice] = None
        self._output_device: Optional[QAudioDevice] = None
        self._io_device_out = None
        self._gain: float = 1.0
        self._volume_sensitivity: float = 0.5
        self._sample_rate = 44100
        self._format = QAudioFormat()
        self._channels = 2
        self._eq_frequencies = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
        self._eq_gains: List[float] = [0.0] * len(self._eq_frequencies)
        self._fft_freqs_cache = {}

    def get_eq_frequencies(self) -> List[int]:
        return self._eq_frequencies.copy()

    def get_input_devices(self) -> List[Tuple[int, str]]:
        devices: List[Tuple[int, str]] = []
        try:
            audio_devices = QMediaDevices.audioInputs()
            for i, device in enumerate(audio_devices):
                name = _normalize_device_name(device.description())
                devices.append((i, name))
        except Exception as e:
            print("[Audio] Error querying devices:", e)
        return devices

    def get_output_devices(self) -> List[Tuple[int, str]]:
        devices: List[Tuple[int, str]] = []
        try:
            audio_devices = QMediaDevices.audioOutputs()
            for i, device in enumerate(audio_devices):
                name = _normalize_device_name(device.description())
                devices.append((i, name))
        except Exception as e:
            print("[Audio] Error querying output devices:", e)
        return devices

    def start_stream(self, device_id: int, output_id: Optional[int] = None) -> bool:
        try:
            audio_devices = QMediaDevices.audioInputs()
            if device_id < 0 or device_id >= len(audio_devices):
                return False
            
            new_input_device = audio_devices[device_id]
            
            if output_id is None:
                new_output_device = QMediaDevices.defaultAudioOutput()
            else:
                output_devices = QMediaDevices.audioOutputs()
                if output_id < 0 or output_id >= len(output_devices):
                    new_output_device = QMediaDevices.defaultAudioOutput()
                else:
                    new_output_device = output_devices[output_id]
            
            if (self._input_device == new_input_device and 
                self._output_device == new_output_device and
                self._audio_source is not None and
                self._audio_source.state() != QAudio.StoppedState):
                return True
                
            self.stop_stream()
            
            self._input_device = new_input_device
            self._output_device = new_output_device
            
            format = QAudioFormat()
            format.setSampleRate(self._sample_rate)
            format.setChannelCount(self._channels)
            format.setSampleFormat(QAudioFormat.Int16)
            
            if not self._input_device.isFormatSupported(format):
                format = self._input_device.preferredFormat()
                self._channels = format.channelCount()
                self._sample_rate = format.sampleRate()
                self._fft_freqs_cache.clear()
            
            self._format = format
            self._channels = min(format.channelCount(), 2)
            
            self._audio_source = QAudioSource(self._input_device, format, self)
            self._audio_sink = QAudioSink(self._output_device, format, self)
            
            self._io_device_out = self._audio_sink.start()
            io_device_in = self._audio_source.start()
            
            io_device_in.readyRead.connect(lambda: self._process_audio(io_device_in))
            
            print(f"[Audio] Stream started: {self._channels} channels, {self._sample_rate}Hz")
            return True
            
        except Exception as e:
            print("[Audio] Error starting stream:", e)
            return False

    def stop_stream(self) -> None:
        try:
            if self._audio_source:
                self._audio_source.stop()
                self._audio_source = None
                
            if self._audio_sink:
                self._audio_sink.stop()
                self._audio_sink = None
                
            self._io_device_out = None
                
        except Exception as e:
            print("[Audio] Error stopping stream:", e)

    def _apply_eq(self, audio_data: np.ndarray) -> np.ndarray:
        if all(g == 0.0 for g in self._eq_gains):
            return audio_data
        
        try:
            data_len = len(audio_data)
            
            if data_len not in self._fft_freqs_cache:
                self._fft_freqs_cache[data_len] = np.fft.rfftfreq(data_len, 1.0 / self._sample_rate)
            
            freqs = self._fft_freqs_cache[data_len]
            fft_data = np.fft.rfft(audio_data)
            
            for i, (center_freq, gain_db) in enumerate(zip(self._eq_frequencies, self._eq_gains)):
                if gain_db == 0.0:
                    continue
                
                q_factor = 1.414
                bandwidth = center_freq / q_factor
                lower = center_freq - bandwidth / 2
                upper = center_freq + bandwidth / 2
                
                mask = (freqs >= lower) & (freqs <= upper)
                gain_linear = 10 ** (gain_db / 20)
                fft_data[mask] *= gain_linear
            
            return np.fft.irfft(fft_data, n=data_len)
        except Exception as e:
            print(f"[Audio] EQ error: {e}")
            return audio_data

    def _process_audio(self, io_device_in) -> None:
        try:
            data: QByteArray = io_device_in.readAll()
            if data.isEmpty():
                return
                
            audio_bytes = data.data()
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            if self._channels == 2:
                left = audio_float[0::2]
                right = audio_float[1::2]
                mono = (left + right) / 2
                rms = np.sqrt(np.mean(mono**2))
            else:
                rms = np.sqrt(np.mean(audio_float**2))
            
            db_level = 20 * np.log10(max(rms, 1e-10))
            self.rms_level_changed.emit(db_level)
            
            audio_float *= self._gain
            
            if self._channels == 2:
                left_eq = self._apply_eq(audio_float[0::2])
                right_eq = self._apply_eq(audio_float[1::2])
                audio_float[0::2] = left_eq
                audio_float[1::2] = right_eq
            else:
                audio_float = self._apply_eq(audio_float)
            
            audio_float = np.clip(audio_float, -1.0, 1.0)
            output_data = (audio_float * 32767).astype(np.int16)
            
            if self._io_device_out:
                self._io_device_out.write(output_data.tobytes())
                
        except Exception as e:
            print(f"[Audio] Callback error: {e}")

    def set_gain(self, gain_percent: int) -> None:        
        if gain_percent == 0:
            self._gain = 0.0
        else:
            normalized = gain_percent / 50.0
            sensitivity_factor = 0.3 + (self._volume_sensitivity * 0.7)
            
            if normalized <= 1.0:
                self._gain = (normalized ** 2) * sensitivity_factor
            else:
                max_boost = 1.0 + (self._volume_sensitivity * 3.0)
                self._gain = sensitivity_factor + ((normalized - 1.0) * (max_boost - sensitivity_factor))

    def set_volume_sensitivity(self, sensitivity: float) -> None:
        self._volume_sensitivity = sensitivity

    def set_eq_gains(self, gains: List[float]) -> None:
        if len(gains) == len(self._eq_gains):
            self._eq_gains = gains.copy()

    def is_active(self) -> bool:
        return self._audio_source is not None and self._audio_source.state() == QAudio.ActiveState

    def __del__(self) -> None:
        self.stop_stream()
