from implementations import *
from IDataAnalysis import DataAnalysisApp
from IVisualization import EnhancedVisualizationInterface
from ISQL import SQLInterface
from ITerminal import TerminalInterface
from IEditor import CodeEditorInterface

class AdvancedIDE(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Data Exploration Lab')
        self.resize(1600, 900)
        
        # Initialize interfaces
        self.codeInterface = CodeEditorInterface(self)
        self.dataInterface = DataAnalysisApp()
        self.visualizationInterface = EnhancedVisualizationInterface(self)
        self.sqlInterface = SQLInterface(self)
        self.terminalInterface = TerminalInterface(self)

        
        # Navigation setup
        self.initNavigation()
        
        # Initialize style
        self.setCustomStyle()
        
        # Initialize sample data
        self.current_df = None
        self.original_df = None
        self.current_page = 0
        self.rows_per_page = 1000

    def initNavigation(self):
        self.addSubInterface(self.codeInterface, FIF.CODE, 'Code Editor')
        self.addSubInterface(self.visualizationInterface, FIF.PIE_SINGLE, 'Visualization')  # Grafik için alternatif
        self.addSubInterface(self.dataInterface, FIF.DOCUMENT, 'Data Analysis')  # Veri için alternatif
        self.addSubInterface(self.sqlInterface, FIF.CLOUD, 'SQL Query')  # Database için alternatif
        self.addSubInterface(self.terminalInterface, FIF.COMMAND_PROMPT, 'Terminal')
        
        self.navigationInterface.addItem(
            routeKey='settings',
            icon=FIF.SETTING,
            text='Settings',
            onClick=self.showSettings,
            position=NavigationItemPosition.BOTTOM
        )

    def setCustomStyle(self):
        self.setStyleSheet("""
            QTableWidget {
                font-size: 12px;
                border: 1px solid #e0e0e0;
            }
            QTextEdit {
                font-family: Consolas;
                font-size: 13px;
            }
            FigureCanvas {
                background: white;
                border-radius: 8px;
            }
        """)

    def showSettings(self):
        MessageBox('Settings', 'Coming soon!', self).exec_()
