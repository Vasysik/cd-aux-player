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
        self._chunk_size = 2048
        self._format = QAudioFormat()
        self._channels = 2

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

    def start_stream(self, device_id: int) -> bool:
        try:
            self.stop_stream()
            
            audio_devices = QMediaDevices.audioInputs()
            if device_id < 0 or device_id >= len(audio_devices):
                return False
                
            self._input_device = audio_devices[device_id]
            self._output_device = QMediaDevices.defaultAudioOutput()
            
            format = QAudioFormat()
            format.setSampleRate(self._sample_rate)
            format.setChannelCount(self._channels)
            format.setSampleFormat(QAudioFormat.Int16)
            
            if not self._input_device.isFormatSupported(format):
                format = self._input_device.preferredFormat()
                self._channels = format.channelCount()
                self._sample_rate = format.sampleRate()
            
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

    def is_active(self) -> bool:
        return self._audio_source is not None and self._audio_source.state() == QAudio.ActiveState

    def __del__(self) -> None:
        self.stop_stream()
