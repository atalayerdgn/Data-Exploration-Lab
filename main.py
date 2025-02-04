from implementations import *
from AIDE import AdvancedIDE

if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = AdvancedIDE()
    window.show()
    sys.exit(app.exec_())
