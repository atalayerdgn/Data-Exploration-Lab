import sys
import platform
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import StringIO
from PyQt5.QtWidgets import (
    QApplication, QPlainTextEdit, QWidget, QVBoxLayout, QScrollArea, QCompleter
)
from PyQt5.QtCore import (
    Qt, QProcess, QTextStream, QTextCodec, QTimer, QEvent
)
from PyQt5.QtGui import (
    QTextCursor, QColor, QTextCharFormat, QSyntaxHighlighter, QTextFormat,
    QClipboard
)
from PyQt5.Qt import QKeySequence
from qfluentwidgets import (
    ScrollArea, SearchLineEdit, CommandBar, Action, MessageBox, InfoBar,
    InfoBarPosition, setTheme, Theme, FluentIcon as FIF
)

class TerminalHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.formats = {
            'command': self.create_format('#569CD6'),
            'error': self.create_format('#FF5555'),
            'data_cmd': self.create_format('#4EC9B0'),
            'number': self.create_format('#B5CEA8'),
            'string': self.create_format('#CE9178')
        }
        self.patterns = {
            'command': r'^(\>\>\>|\$)\s.*',
            'error': r'error|warning|fail|exception',
            'data_cmd': r'\b(load|summary|plot|hist|filter|groupby|head|tail|dtypes|clean|corr)\b',
            'number': r'\b\d+\.?\d*\b',
            'string': r'\".*?\"|\'.*?\''
        }

    def create_format(self, color):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        return fmt

    def highlightBlock(self, text):
        for name, pattern in self.patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                self.setFormat(
                    match.start(), 
                    match.end() - match.start(), 
                    self.formats[name]
                )

class AdvancedTerminal(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: Consolas;
                font-size: 12pt;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.highlighter = TerminalHighlighter(self.document())
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setUndoRedoEnabled(False)
        self.setReadOnly(True)

class TerminalInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("TerminalInterface")
        self.data_env = {'pd': pd, 'np': np, 'plt': plt, 'df': None}
        self.current_df = None
        self.history = []
        self.history_index = -1
        self.plot_count = 0
        self.process = None
        self.initUI()
        self.startShell()

    def initUI(self):
        self.setWidgetResizable(True)
        self.container = QWidget()
        self.vBox = QVBoxLayout(self.container)
        
        # Terminal widget
        self.terminal = AdvancedTerminal()
        
        # Input with autocompletion
        self.input = SearchLineEdit()
        self.input.setPlaceholderText("Enter command or data expression...")
        self.input.setClearButtonEnabled(True)
        self.input.returnPressed.connect(self.executeCommand)
        
        # Autocompleter setup
        self.completer = QCompleter([
            'load', 'summary', 'plot', 'hist',
            'filter', 'groupby', 'head', 'tail',
            'columns', 'dtypes', 'clean', 'corr',
            'np.', 'pd.', 'plt.', '='
        ])
        self.input.setCompleter(self.completer)
        
        # Command bar
        self.commandBar = CommandBar(self)
        self.commandBar.addAction(Action(FIF.COPY, 'Copy', triggered=self.copyTerminal))
        self.commandBar.addAction(Action(FIF.CLEAR_SELECTION, 'Clear', triggered=self.clearTerminal))
        self.commandBar.addAction(Action(FIF.HISTORY, 'History', triggered=self.showHistory))
        self.commandBar.addAction(Action(FIF.POWER_BUTTON, 'Stop', triggered=self.stopProcess))
        
        # Layout setup
        self.vBox.addWidget(self.commandBar)
        self.vBox.addWidget(self.terminal)
        self.vBox.addWidget(self.input)
        self.setWidget(self.container)
        
        # Terminal settings
        self.terminal.setMaximumBlockCount(10000)
        self.input.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                self.navigateHistory(-1)
                return True
            elif event.key() == Qt.Key_Down:
                self.navigateHistory(1)
                return True
        return super().eventFilter(obj, event)

    def navigateHistory(self, direction):
        if not self.history:
            return
        self.history_index = max(0, min(self.history_index + direction, len(self.history)-1))
        self.input.setText(self.history[self.history_index])

    def handleDataCommand(self, command):
        """Handle advanced data analysis commands"""
        try:
            if command.startswith('load '):
                self.loadData(command[5:])
            elif command == 'summary':
                self.showSummary()
            elif command.startswith('plot '):
                self.generatePlot(command[5:])
            elif command.startswith('hist '):
                self.generateHist(command[5:])
            elif command.startswith('filter '):
                self.filterData(command[7:])
            elif command.startswith('groupby '):
                self.groupBy(command[8:])
            elif command == 'head':
                self.showHead()
            elif command == 'tail':
                self.showTail()
            elif command == 'columns':
                self.showColumns()
            elif command == 'dtypes':
                self.showDtypes()
            elif command == 'clean':
                self.cleanData()
            elif command == 'corr':
                self.showCorrelation()
            elif command.startswith('='):
                self.evalMath(command[1:])
            else:
                self.appendOutput(f"✗ Unknown command: {command}\n")
        except Exception as e:
            self.appendOutput(f"✗ Error processing command: {str(e)}\n")

    # Data analysis functions
    def loadData(self, filepath):
        try:
            self.current_df = pd.read_csv(filepath.strip())
            self.data_env['df'] = self.current_df
            self.appendOutput(f"✓ Loaded {len(self.current_df)} rows\n")
            self.appendOutput(str(self.current_df.head()) + "\n")
        except Exception as e:
            self.appendOutput(f"✗ Load error: {str(e)}\n")

    def showSummary(self):
        if self.current_df is not None:
            buffer = StringIO()
            self.current_df.info(buf=buffer)
            self.appendOutput(buffer.getvalue() + "\n")
            self.appendOutput(str(self.current_df.describe(include='all')) + "\n")

    def generatePlot(self, args):
        if self.current_df is not None:
            try:
                plt.figure(figsize=(10, 6))
                if ' ' in args:
                    x, y, plot_type = args.split()
                    self.current_df.plot(x=x, y=y, kind=plot_type)
                else:
                    self.current_df.plot()
                self.plot_count += 1
                plt.savefig(f'plot_{self.plot_count}.png', bbox_inches='tight')
                plt.close()
                self.appendOutput(f"✓ Plot saved as plot_{self.plot_count}.png\n")
            except Exception as e:
                self.appendOutput(f"✗ Plot error: {str(e)}\n")

    def generateHist(self, column):
        if self.current_df is not None:
            try:
                plt.figure(figsize=(10, 6))
                self.current_df[column.strip()].hist()
                self.plot_count += 1
                plt.savefig(f'hist_{self.plot_count}.png', bbox_inches='tight')
                plt.close()
                self.appendOutput(f"✓ Histogram saved as hist_{self.plot_count}.png\n")
            except Exception as e:
                self.appendOutput(f"✗ Hist error: {str(e)}\n")

    def filterData(self, condition):
        if self.current_df is not None:
            try:
                self.current_df = self.current_df.query(condition)
                self.appendOutput(f"✓ Filter applied. Remaining rows: {len(self.current_df)}\n")
            except Exception as e:
                self.appendOutput(f"✗ Filter error: {str(e)}\n")

    def groupBy(self, args):
        if self.current_df is not None:
            try:
                group_col, agg_col = args.split()
                result = self.current_df.groupby(group_col)[agg_col].agg(['mean', 'sum', 'count'])
                self.appendOutput(f"Grouped results:\n{result.to_string()}\n")
            except Exception as e:
                self.appendOutput(f"✗ Groupby error: {str(e)}\n")

    def showHead(self):
        if self.current_df is not None:
            self.appendOutput(f"{self.current_df.head().to_string()}\n")

    def showTail(self):
        if self.current_df is not None:
            self.appendOutput(f"{self.current_df.tail().to_string()}\n")

    def showColumns(self):
        if self.current_df is not None:
            self.appendOutput(f"Columns: {', '.join(self.current_df.columns)}\n")

    def showDtypes(self):
        if self.current_df is not None:
            self.appendOutput(f"Data types:\n{self.current_df.dtypes.to_string()}\n")

    def cleanData(self):
        if self.current_df is not None:
            initial_rows = len(self.current_df)
            self.current_df.dropna(inplace=True)
            new_rows = len(self.current_df)
            self.appendOutput(f"✓ Data cleaned. Removed {initial_rows - new_rows} rows\n")

    def showCorrelation(self):
        if self.current_df is not None:
            numeric_df = self.current_df.select_dtypes(include=np.number)
            if not numeric_df.empty:
                corr = numeric_df.corr()
                self.appendOutput(f"Correlation matrix:\n{corr.to_string()}\n")
            else:
                self.appendOutput("✗ No numeric columns to calculate correlations\n")

    def evalMath(self, expr):
        try:
            result = eval(expr, {'np': np, 'pd': pd, 'df': self.current_df}, self.data_env)
            self.appendOutput(f"= {result}\n")
        except Exception as e:
            self.appendOutput(f"✗ Math error: {str(e)}\n")

    # System functions
    def executeCommand(self):
        command = self.input.text().strip()
        if not command:
            return
            
        self.history.append(command)
        self.history_index = len(self.history)
        
        if command.startswith(('load', 'summary', 'plot', 'hist', 'filter', 
                             'groupby', 'head', 'tail', 'columns', 'dtypes', 
                             'clean', 'corr', '=')):
            self.terminal.appendPlainText(f">>> {command}\n")
            self.handleDataCommand(command)
        else:
            self.terminal.appendPlainText(f"$ {command}\n")
            self.process.write((command + '\n').encode())
        
        self.input.clear()

    def appendOutput(self, text):
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()

    def copyTerminal(self):
        QApplication.clipboard().setText(self.terminal.toPlainText())
        InfoBar.success(
            title='Copied',
            content='Terminal content copied to clipboard',
            parent=self,
            position=InfoBarPosition.TOP_RIGHT
        )

    def clearTerminal(self):
        self.terminal.clear()
        InfoBar.info(
            title='Cleared',
            content='Terminal content cleared',
            parent=self,
            position=InfoBarPosition.TOP_RIGHT
        )

    def showHistory(self):
        history = "\n".join([f"{i+1}. {cmd}" for i, cmd in enumerate(self.history[-10:])])
        MessageBox('Command History', history, self).exec_()

    def stopProcess(self):
        if self.process and self.process.state() == QProcess.Running:
            self.process.kill()
            self.appendOutput("\n✗ Process terminated by user\n")
            InfoBar.warning(
                title='Process Stopped',
                content='Current process has been terminated',
                parent=self,
                position=InfoBarPosition.TOP_RIGHT
            )

    def startShell(self):
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.readOutput)
        self.process.readyReadStandardError.connect(self.readOutput)
        
        if platform.system() == 'Windows':
            self.process.start('cmd')
        else:
            self.process.start('bash', ['-i'])

    def readOutput(self):
        codec = QTextCodec.codecForLocale()
        text = codec.toUnicode(self.process.readAll())
        self.appendOutput(text)
