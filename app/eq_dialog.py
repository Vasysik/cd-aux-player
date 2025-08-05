from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal
from typing import List


class EqDialog(QDialog):
    eq_changed = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎛️ Эквалайзер")
        self.setModal(False)
        self.setMinimumWidth(800)
        self.setMinimumHeight(400)
        
        from .audio import AudioManager
        audio_manager = parent.audio_manager if hasattr(parent, 'audio_manager') else AudioManager()
        self._frequencies = audio_manager.get_eq_frequencies()
        self._freq_labels = self._create_freq_labels()
        self._sliders: List[QSlider] = []
        self._value_labels: List[QLabel] = []
        
        self._setup_ui()
        self._apply_dark_theme()
    
    def _create_freq_labels(self) -> List[str]:
        labels = []
        for freq in self._frequencies:
            if freq < 1000:
                labels.append(f"{freq} Hz")
            else:
                labels.append(f"{freq // 1000} kHz")
        return labels
    
    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        
        title_label = QLabel("Настройка частотных полос")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        sliders_layout = QHBoxLayout()
        sliders_layout.setSpacing(20)
        
        for i, freq_label in enumerate(self._freq_labels):
            freq_layout = QVBoxLayout()
            freq_layout.setSpacing(5)
            
            value_label = QLabel("0 dB")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet("font-size: 12px; font-weight: bold;")
            self._value_labels.append(value_label)
            freq_layout.addWidget(value_label)
            
            slider = QSlider(Qt.Vertical)
            slider.setRange(-12, 12)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksLeft)
            slider.setTickInterval(3)
            slider.setMinimumHeight(200)
            slider.valueChanged.connect(lambda v, idx=i: self._on_slider_changed(idx, v))
            self._sliders.append(slider)
            freq_layout.addWidget(slider, alignment=Qt.AlignHCenter)
            
            freq_name_label = QLabel(freq_label)
            freq_name_label.setAlignment(Qt.AlignCenter)
            freq_name_label.setStyleSheet("font-size: 11px;")
            freq_layout.addWidget(freq_name_label)
            
            sliders_layout.addLayout(freq_layout)
        
        main_layout.addLayout(sliders_layout)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        reset_button = QPushButton("🔄 Сброс")
        reset_button.clicked.connect(self._reset_eq)
        buttons_layout.addWidget(reset_button)
        
        buttons_layout.addStretch()
        
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        buttons_layout.addWidget(close_button)
        
        main_layout.addLayout(buttons_layout)
    
    def _apply_dark_theme(self) -> None:
        self.setStyleSheet("""
            QDialog { 
                background-color: #1e1e1e; 
                color: #ffffff; 
            }
            QLabel { 
                color: #ffffff; 
            }
            QSlider::groove:vertical { 
                background: #404040; 
                width: 6px; 
                border-radius: 3px; 
            }
            QSlider::handle:vertical { 
                background: #0078d4; 
                height: 16px; 
                width: 16px;
                border-radius: 8px; 
                margin: 0 -5px; 
            }
            QSlider::handle:vertical:hover { 
                background: #1084e8; 
            }
            QSlider::add-page:vertical {
                background: #606060;
                border-radius: 3px;
            }
            QPushButton { 
                background: #404040; 
                border: none; 
                padding: 8px 16px; 
                border-radius: 4px; 
                color: #ffffff;
            }
            QPushButton:hover { 
                background: #505050; 
            }
        """)
    
    def _on_slider_changed(self, index: int, value: int) -> None:
        self._value_labels[index].setText(f"{value:+d} dB" if value != 0 else "0 dB")
        gains = [slider.value() for slider in self._sliders]
        self.eq_changed.emit(gains)
    
    def _reset_eq(self) -> None:
        for slider in self._sliders:
            slider.setValue(0)
    
    def get_gains(self) -> List[float]:
        return [float(slider.value()) for slider in self._sliders]
