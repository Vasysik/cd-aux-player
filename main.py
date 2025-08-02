import sys
from PySide6.QtWidgets import QApplication
from app.ui import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("CD-AUX mini")
    app.setApplicationVersion("1.0.0")
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
