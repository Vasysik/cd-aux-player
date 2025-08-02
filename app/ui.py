import math
import os
from typing import Optional
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QComboBox, QSlider, QPushButton, QLabel, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QPainter, QPixmap, QTransform, QPalette, QColor
from .audio import AudioManager


class RotatingDisc(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.rotation_angle = 0.0
        self.target_speed = 0.0
        self.current_speed = 0.0
        self._disc_pixmap: Optional[QPixmap] = None
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_rotation)
        self.timer.start(33)
        
        self._load_disc_image()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
    
    def _load_disc_image(self) -> None:
        disc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "disc.png")
        if os.path.exists(disc_path):
            self._disc_pixmap = QPixmap(disc_path)
        else:
            self._disc_pixmap = QPixmap(200, 200)
            self._disc_pixmap.fill(Qt.transparent)
            painter = QPainter(self._disc_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor(100, 100, 100))
            painter.drawEllipse(10, 10, 180, 180)
            painter.setBrush(QColor(50, 50, 50))
            painter.drawEllipse(80, 80, 40, 40)
            painter.end()
    
    def set_audio_level(self, db_level: float) -> None:
        if db_level < -60:
            self.target_speed = 0.0
        else:
            normalized = min(1.0, max(0.0, (db_level + 60) / 60))
            self.target_speed = normalized * 10.0
    
    def _update_rotation(self) -> None:
        speed_diff = self.target_speed - self.current_speed
        self.current_speed += speed_diff * 0.1
        
        self.rotation_angle += self.current_speed
        if self.rotation_angle >= 360:
            self.rotation_angle -= 360
        
        self.update()
    
    def paintEvent(self, event) -> None:
        if not self._disc_pixmap:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        widget_size = min(self.width(), self.height())
        disc_size = int(widget_size * 0.8)
        
        x = (self.width() - disc_size) // 2
        y = (self.height() - disc_size) // 2
        
        transform = QTransform()
        transform.translate(x + disc_size/2, y + disc_size/2)
        transform.rotate(self.rotation_angle)
        transform.translate(-disc_size/2, -disc_size/2)
        painter.setTransform(transform)
        
        scaled_pixmap = self._disc_pixmap.scaled(disc_size, disc_size, 
                                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(0, 0, scaled_pixmap)


class ControlPanel(QWidget):
    def __init__(self, audio_manager: AudioManager) -> None:
        super().__init__()
        self.audio_manager = audio_manager
        self._setup_ui()
        self._connect_signals()
        self._refresh_devices()
    
    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        
        self.device_combo = QComboBox()
        self.device_combo.addItem("Select Input Device", -1)
        layout.addWidget(QLabel("Input:"))
        layout.addWidget(self.device_combo)
        
        layout.addStretch()
        
        layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(150)
        layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel("50%")
        self.volume_label.setFixedWidth(30)
        layout.addWidget(self.volume_label)
        
        layout.addStretch()
        
        self.eq_button = QPushButton("EQ")
        self.eq_button.setFixedWidth(40)
        layout.addWidget(self.eq_button)
    
    def _connect_signals(self) -> None:
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.eq_button.clicked.connect(self._on_eq_clicked)
    
    def _refresh_devices(self) -> None:
        self.device_combo.clear()
        self.device_combo.addItem("Select Input Device", -1)
        
        devices = self.audio_manager.get_input_devices()
        for device_id, device_name in devices:
            self.device_combo.addItem(device_name, device_id)
    
    def _on_device_changed(self) -> None:
        device_id = self.device_combo.currentData()
        if device_id == -1:
            self.audio_manager.stop_stream()
        else:
            if not self.audio_manager.start_stream(device_id):
                QMessageBox.warning(self, "Audio Error", 
                                  f"Failed to start audio stream for selected device.")
                self.device_combo.setCurrentIndex(0)
    
    def _on_volume_changed(self) -> None:
        volume = self.volume_slider.value()
        self.volume_label.setText(f"{volume}%")
        self.audio_manager.set_gain(volume)
    
    def _on_eq_clicked(self) -> None:
        QMessageBox.information(self, "EQ", "Equalizer feature coming soon!")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CD-AUX mini")
        self.setMinimumSize(400, 300)
        self.resize(600, 500)
        
        self._apply_dark_theme()
        self.audio_manager = AudioManager()
        self._setup_ui()
        self._connect_signals()
    
    def _apply_dark_theme(self) -> None:
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QComboBox, QSlider, QPushButton, QLabel {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
                font-size: 12px;
            }
            ControlPanel {
                background-color: #252525;
                border-bottom: 1px solid #404040;
            }
            QComboBox:hover, QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #505050;
            }
            QSlider::groove:horizontal {
                background-color: #404040;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #0078d4;
                width: 16px;
                border-radius: 8px;
                margin: -5px 0;
            }
        """)
    
    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.control_panel = ControlPanel(self.audio_manager)
        self.control_panel.setFixedHeight(50)
        main_layout.addWidget(self.control_panel)
        
        self.disc_widget = RotatingDisc()
        main_layout.addWidget(self.disc_widget)
    
    def _connect_signals(self) -> None:
        self.audio_manager.rms_level_changed.connect(self.disc_widget.set_audio_level)
    
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
    
    def closeEvent(self, event) -> None:
        self.audio_manager.stop_stream()
        event.accept()
