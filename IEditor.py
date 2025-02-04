from qfluentwidgets import (
    PlainTextEdit, CommandBar, Action, FluentIcon as FIF, PrimaryPushButton,
    ToolButton, MessageBox, InfoBar, InfoBarPosition
)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTabWidget, QTableWidget, QTableWidgetItem,
    QScrollArea, QFileDialog, QDialog, QPushButton, QComboBox, QShortcut
)
from PyQt5.QtCore import Qt, QRegularExpression
from PyQt5.QtGui import QTextCharFormat, QFont, QColor, QSyntaxHighlighter
import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
import sys
from io import StringIO
import traceback
import black

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlight_rules = []
        self.initHighlightRules()

    def initHighlightRules(self):
        # Anahtar kelimeler
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
            'elif', 'else', 'except', 'False', 'finally', 'for', 'from', 'global',
            'if', 'import', 'in', 'is', 'lambda', 'None', 'nonlocal', 'not', 'or',
            'pass', 'raise', 'return', 'True', 'try', 'while', 'with', 'yield'
        ]
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor('#569CD6'))
        keyword_format.setFontWeight(QFont.Bold)
        self.addRules(keywords, keyword_format)

        # Veri analizi anahtar kelimeleri
        data_keywords = [
            'pd', 'np', 'plt', 'df', 'read_csv', 'read_excel', 'DataFrame',
            'Series', 'figure', 'plot', 'head', 'describe', 'iloc', 'loc'
        ]
        data_keyword_format = QTextCharFormat()
        data_keyword_format.setForeground(QColor('#4EC9B0'))
        self.addRules(data_keywords, data_keyword_format)

        # Stringler
        string_format = QTextCharFormat()
        string_format.setForeground(QColor('#CE9178'))
        self.addRegexRule(r'"[^"]*"', string_format)
        self.addRegexRule(r"'[^']*'", string_format)

        # Yorumlar
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor('#6A9955'))
        self.addRegexRule(r'#[^\n]*', comment_format)

    def addRules(self, keywords, fmt):
        for keyword in keywords:
            pattern = QRegularExpression(r'\b{}\b'.format(keyword))
            self.highlight_rules.append((pattern, fmt))

    def addRegexRule(self, pattern, fmt):
        self.highlight_rules.append(
            (QRegularExpression(pattern), fmt)
        )

    def highlightBlock(self, text):
        for pattern, fmt in self.highlight_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    fmt
                )

class VariableExplorer(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(['Name', 'Type', 'Shape', 'Sample'])
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)

    def update_variables(self, namespace):
        self.setRowCount(0)
        for name, value in namespace.items():
            if not name.startswith('_') and not callable(value):
                self.add_variable_row(name, value)

    def add_variable_row(self, name, value):
        row = self.rowCount()
        self.insertRow(row)
        
        self.setItem(row, 0, QTableWidgetItem(name))
        self.setItem(row, 1, QTableWidgetItem(type(value).__name__))
        
        shape_info = self.get_shape_info(value)
        sample_info = self.get_sample_info(value)
        
        self.setItem(row, 2, QTableWidgetItem(shape_info))
        self.setItem(row, 3, QTableWidgetItem(sample_info))

    def get_shape_info(self, value):
        try:
            if hasattr(value, 'shape'):
                return str(value.shape)
            elif hasattr(value, '__len__'):
                return f'Length: {len(value)}'
            return ''
        except:
            return ''

    def get_sample_info(self, value):
        try:
            if isinstance(value, pd.DataFrame):
                return str(value.columns.tolist())
            elif isinstance(value, pd.Series):
                return str(value.head(3).to_dict())
            elif isinstance(value, (list, tuple)):
                return str(value[:3]) + '...' if len(value) > 3 else str(value)
            return str(value)[:50]
        except:
            return ''

class CodeEditorInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.namespace = {'pd': pd, 'np': np, 'plt': None}
        self.setObjectName('CodeEditorInterface')
        self.initUI()
        self.setupShortcuts()

    def initUI(self):
        self.setupEditor()
        self.setupToolbar()
        self.setupOutput()
        self.setupLayout()
        
    def setupEditor(self):
        self.editor = PlainTextEdit()
        self.editor.setPlaceholderText("Enter Python code here...")
        self.highlighter = PythonHighlighter(self.editor.document())
        
    def setupToolbar(self):
        self.commandBar = CommandBar(self)
        actions = [
            Action(FIF.SAVE, 'Save', triggered=self.saveCode),
            Action(FIF.FOLDER, 'Open', triggered=self.openFile),
            Action(FIF.DOCUMENT, 'Import Data', triggered=self.importData),
            Action(FIF.VIEW, 'Visualize', triggered=self.showVisualizationWizard),
            Action(FIF.ALIGNMENT, 'Format', triggered=self.formatCode),
        ]
        self.commandBar.addActions(actions)
        
    def setupOutput(self):
        self.outputTabs = QTabWidget()
        
        # Console Output
        self.consoleOutput = PlainTextEdit()
        self.consoleOutput.setReadOnly(True)
        self.outputTabs.addTab(self.consoleOutput, "Console")
        
        # Plot Area
        self.plotContainer = QWidget()
        self.plotLayout = QVBoxLayout(self.plotContainer)
        self.plotScroll = QScrollArea()
        self.plotScroll.setWidgetResizable(True)
        self.plotScroll.setWidget(self.plotContainer)
        self.outputTabs.addTab(self.plotScroll, "Visualizations")
        
        # Variable Explorer
        self.variableExplorer = VariableExplorer()
        self.outputTabs.addTab(self.variableExplorer, "Variables")

    def setupLayout(self):
        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(self.commandBar)
        mainLayout.addWidget(self.editor)
        
        # Button Layout
        btnLayout = QHBoxLayout()
        self.runBtn = PrimaryPushButton('Run', self, FIF.PLAY)
        self.runBtn.clicked.connect(self.executeCode)
        btnLayout.addWidget(self.runBtn)
        
        btnLayout.addWidget(ToolButton(FIF.DELETE, self))
        btnLayout.addWidget(ToolButton(FIF.SAVE, self))
        mainLayout.addLayout(btnLayout)
        
        mainLayout.addWidget(QLabel('Execution Results:'))
        mainLayout.addWidget(self.outputTabs)

    def setupShortcuts(self):
        QShortcut("Ctrl+Return", self).activated.connect(self.executeCode)
        QShortcut("Ctrl+S", self).activated.connect(self.saveCode)
        QShortcut("Ctrl+L", self).activated.connect(self.clearOutput)

    def executeCode(self):
        code = self.editor.toPlainText()
        with Capturing() as output:
            try:
                # Reset plt reference in namespace
                import matplotlib.pyplot as plt
                plt.close('all')
                self.namespace['plt'] = plt
                
                exec(code, self.namespace)
                self.processFigures()
                self.showInfo('Execution Completed', 'Code ran successfully')
            except Exception as e:
                traceback.print_exc()
                self.showError('Execution Error', str(e))
        
        self.consoleOutput.setPlainText('\n'.join(output))
        self.variableExplorer.update_variables(self.namespace)

    def processFigures(self):
        import matplotlib.pyplot as plt
        while self.plotLayout.count():
            widget = self.plotLayout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
                
        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            canvas = FigureCanvas(fig)
            self.plotLayout.addWidget(canvas)
        plt.close('all')

    def importData(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Data", "",
            "Data Files (*.csv *.xlsx *.parquet);;All Files (*)"
        )
        if path:
            template = self.generateImportTemplate(path)
            self.insertCode(template)

    def generateImportTemplate(self, path):
        if path.endswith('.csv'):
            return f"df = pd.read_csv(r'{path}')\nprint(df.head())"
        elif path.endswith('.xlsx'):
            return f"df = pd.read_excel(r'{path}')\nprint(df.head())"
        elif path.endswith('.parquet'):
            return f"df = pd.read_parquet(r'{path}')\nprint(df.head())"
        return f"# Unsupported file format: {path}"

    def insertCode(self, text):
        cursor = self.editor.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText('\n' + text)
        self.editor.setTextCursor(cursor)

    def formatCode(self):
        try:
            code = self.editor.toPlainText()
            formatted = black.format_str(code, mode=black.FileMode())
            self.editor.setPlainText(formatted)
            self.showInfo('Code Formatted', 'Using Black formatter')
        except Exception as e:
            self.showError('Formatting Error', str(e))

    def showVisualizationWizard(self):
        wizard = VisualizationWizard(self.namespace, self)
        wizard.exec_()

    def saveCode(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Code", "", "Python Files (*.py)")
        if path:
            with open(path, 'w') as f:
                f.write(self.editor.toPlainText())
            self.showInfo('Code Saved', f'Code saved to {path}')

    def openFile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Python Files (*.py)")
        if path:
            with open(path, 'r') as f:
                self.editor.setPlainText(f.read())
            self.showInfo('File Opened', f'File opened from {path}')

    def clearOutput(self):
        self.consoleOutput.clear()
        while self.plotLayout.count():
            widget = self.plotLayout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        self.variableExplorer.setRowCount(0)

    def showInfo(self, title, content):
        InfoBar.success(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def showError(self, title, content):
        InfoBar.error(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        sys.stdout = self._stdout

class VisualizationWizard(QDialog):
    def __init__(self, namespace, parent=None):
        super().__init__(parent)
        self.namespace = namespace
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Visualization Wizard')
        layout = QVBoxLayout()
        
        # DataFrame Selector
        self.dfSelector = QComboBox()
        self.populateDataFrames()
        layout.addWidget(QLabel('Select DataFrame:'))
        layout.addWidget(self.dfSelector)
        
        # Chart Type Selector
        self.chartType = QComboBox()
        self.chartType.addItems(['Line', 'Bar', 'Scatter', 'Histogram', 'Boxplot'])
        layout.addWidget(QLabel('Chart Type:'))
        layout.addWidget(self.chartType)
        
        # Generate Button
        self.generateBtn = QPushButton('Generate Template')
        self.generateBtn.clicked.connect(self.insertTemplate)
        layout.addWidget(self.generateBtn)
        
        self.setLayout(layout)

    def populateDataFrames(self):
        self.dfSelector.clear()
        for name, obj in self.namespace.items():
            if isinstance(obj, pd.DataFrame):
                self.dfSelector.addItem(f"{name} ({obj.shape[0]}x{obj.shape[1]})", name)

    def insertTemplate(self):
        df_name = self.dfSelector.currentData()
        chart_type = self.chartType.currentText().lower()
        
        templates = {
            'line': "df.plot(x='column', y='value', kind='line')",
            'bar': "df['column'].value_counts().plot(kind='bar')",
            'scatter': "df.plot(x='x_col', y='y_col', kind='scatter')",
            'histogram': "df['column'].plot(kind='hist', bins=20)",
            'boxplot': "df.plot(y='column', kind='box')"
        }
        
        template = templates[chart_type].replace('df', df_name)
        self.parent().insertCode(f"\n# Visualization Template\n{template}\nplt.show()")
        self.close()
