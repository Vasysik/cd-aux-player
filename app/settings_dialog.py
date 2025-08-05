import json
import os
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QGroupBox,
    QDialogButtonBox,
    QCheckBox,
)
from PySide6.QtCore import Qt, Signal


class SettingsDialog(QDialog):
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Настройки")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        self.settings_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "settings.json"
        )
        
        self.settings = self._load_settings()
        self._setup_ui()
        self._apply_dark_theme()
        
    def _load_settings(self) -> dict:
        default_settings = {
            "disc_sensitivity": 50,
            "disc_inertia": 50,
            "volume_sensitivity": 50,
            "tray_enabled": True,
            "tray_notification": True
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                    default_settings.update(loaded)
            except Exception:
                pass
                
        return default_settings
    
    def _save_settings(self) -> None:
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"[Settings] Error saving: {e}")
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        disc_group = QGroupBox("💿 Чувствительность скорости диска")
        disc_layout = QVBoxLayout(disc_group)
        
        disc_info = QLabel("Настройка реакции диска на уровень звука")
        disc_info.setWordWrap(True)
        disc_info.setStyleSheet("color: #888888; font-size: 12px;")
        disc_layout.addWidget(disc_info)
        
        disc_slider_layout = QHBoxLayout()
        disc_slider_layout.addWidget(QLabel("Низкая"))
        
        self.disc_slider = QSlider(Qt.Horizontal)
        self.disc_slider.setRange(10, 100)
        self.disc_slider.setValue(self.settings["disc_sensitivity"])
        self.disc_slider.setTickPosition(QSlider.TicksBelow)
        self.disc_slider.setTickInterval(10)
        disc_slider_layout.addWidget(self.disc_slider, stretch=1)
        
        disc_slider_layout.addWidget(QLabel("Высокая"))
        self.disc_value_label = QLabel(f"{self.settings['disc_sensitivity']}%")
        self.disc_value_label.setMinimumWidth(40)
        disc_slider_layout.addWidget(self.disc_value_label)
        
        disc_layout.addLayout(disc_slider_layout)
        layout.addWidget(disc_group)
        
        inertia_group = QGroupBox("⏱️ Инерция диска")
        inertia_layout = QVBoxLayout(inertia_group)
        
        inertia_info = QLabel("Настройка плавности ускорения и замедления")
        inertia_info.setWordWrap(True)
        inertia_info.setStyleSheet("color: #888888; font-size: 12px;")
        inertia_layout.addWidget(inertia_info)
        
        inertia_slider_layout = QHBoxLayout()
        inertia_slider_layout.addWidget(QLabel("Быстрая"))
        
        self.inertia_slider = QSlider(Qt.Horizontal)
        self.inertia_slider.setRange(10, 100)
        self.inertia_slider.setValue(self.settings.get("disc_inertia", 50))
        self.inertia_slider.setTickPosition(QSlider.TicksBelow)
        self.inertia_slider.setTickInterval(10)
        inertia_slider_layout.addWidget(self.inertia_slider, stretch=1)
        
        inertia_slider_layout.addWidget(QLabel("Медленная"))
        self.inertia_value_label = QLabel(f"{self.settings.get('disc_inertia', 50)}%")
        self.inertia_value_label.setMinimumWidth(40)
        inertia_slider_layout.addWidget(self.inertia_value_label)
        
        inertia_layout.addLayout(inertia_slider_layout)
        layout.addWidget(inertia_group)
        
        volume_group = QGroupBox("🔊 Чувствительность усиления")
        volume_layout = QVBoxLayout(volume_group)
        
        volume_info = QLabel("Настройка диапазона усиления громкости")
        volume_info.setWordWrap(True)
        volume_info.setStyleSheet("color: #888888; font-size: 12px;")
        volume_layout.addWidget(volume_info)
        
        volume_slider_layout = QHBoxLayout()
        volume_slider_layout.addWidget(QLabel("Низкая"))
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(10, 100)
        self.volume_slider.setValue(self.settings["volume_sensitivity"])
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.volume_slider.setTickInterval(10)
        volume_slider_layout.addWidget(self.volume_slider, stretch=1)
        
        volume_slider_layout.addWidget(QLabel("Высокая"))
        self.volume_value_label = QLabel(f"{self.settings['volume_sensitivity']}%")
        self.volume_value_label.setMinimumWidth(40)
        volume_slider_layout.addWidget(self.volume_value_label)
        
        volume_layout.addLayout(volume_slider_layout)
        layout.addWidget(volume_group)
        
        tray_group = QGroupBox("🔔 Поведение приложения")
        tray_layout = QVBoxLayout(tray_group)
        
        self.tray_enabled_checkbox = QCheckBox("Разрешить сворачивание в системный трей")
        self.tray_enabled_checkbox.setChecked(self.settings.get("tray_enabled", True))
        tray_layout.addWidget(self.tray_enabled_checkbox)
        
        self.tray_notification_checkbox = QCheckBox("Показывать уведомление при сворачивании")
        self.tray_notification_checkbox.setChecked(self.settings.get("tray_notification", True))
        self.tray_notification_checkbox.setEnabled(self.settings.get("tray_enabled", True))
        tray_layout.addWidget(self.tray_notification_checkbox)
        
        layout.addWidget(tray_group)
        
        reset_button = QPushButton("🔄 Сбросить настройки")
        reset_button.clicked.connect(self._reset_settings)
        layout.addWidget(reset_button)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.disc_slider.valueChanged.connect(
            lambda v: self.disc_value_label.setText(f"{v}%")
        )
        self.inertia_slider.valueChanged.connect(
            lambda v: self.inertia_value_label.setText(f"{v}%")
        )
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_value_label.setText(f"{v}%")
        )
        self.tray_enabled_checkbox.toggled.connect(
            self.tray_notification_checkbox.setEnabled
        )
    
    def _apply_dark_theme(self) -> None:
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #ffffff; }
            QGroupBox { 
                background-color: #252525; 
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QSlider::groove:horizontal { 
                background: #404040; 
                height: 6px; 
                border-radius: 3px; 
            }
            QSlider::handle:horizontal { 
                background: #0078d4; 
                width: 16px; 
                height: 16px;
                border-radius: 8px; 
                margin: -5px 0; 
            }
            QSlider::handle:horizontal:hover { 
                background: #1084e8; 
            }
            QPushButton { 
                background: #404040; 
                border: none; 
                padding: 8px 16px; 
                border-radius: 4px; 
            }
            QPushButton:hover { 
                background: #505050; 
            }
            QLabel { color: #ffffff; }
            QCheckBox { color: #ffffff; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QCheckBox::indicator:unchecked { background: #404040; border: 1px solid #606060; border-radius: 3px; }
            QCheckBox::indicator:checked { background: #0078d4; border: 1px solid #0078d4; border-radius: 3px; }
            QCheckBox::indicator:checked:disabled { background: #505050; }
        """)
    
    def _reset_settings(self) -> None:
        self.disc_slider.setValue(50)
        self.inertia_slider.setValue(50)
        self.volume_slider.setValue(50)
        self.tray_enabled_checkbox.setChecked(True)
        self.tray_notification_checkbox.setChecked(True)
    
    def _on_accept(self) -> None:
        self.settings["disc_sensitivity"] = self.disc_slider.value()
        self.settings["disc_inertia"] = self.inertia_slider.value()
        self.settings["volume_sensitivity"] = self.volume_slider.value()
        self.settings["tray_enabled"] = self.tray_enabled_checkbox.isChecked()
        self.settings["tray_notification"] = self.tray_notification_checkbox.isChecked()
        self._save_settings()
        self.settings_changed.emit(self.settings)
        self.accept()
    
    def get_settings(self) -> dict:
        return self.settings
