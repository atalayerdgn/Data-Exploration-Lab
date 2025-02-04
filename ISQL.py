from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QToolBar, QFileDialog, QShortcut,
    QPlainTextEdit, QListWidget, QListWidgetItem, QApplication, QLabel, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QRegExp, QTimer
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor, QPainter, QKeySequence
from pyqtgraph.parametertree import Parameter, ParameterTree
from qfluentwidgets import (
    RoundMenu, Action, PrimaryToolButton, InfoBar, InfoBarPosition,
    TableWidget, FluentIcon as FIF, SubtitleLabel, BodyLabel
)
import sqlite3
import pandas as pd
import time
import re

class SQLHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlight_rules = []
        
        # SQL keywords
        keywords = [
            'SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'UPDATE', 'DELETE',
            'JOIN', 'INNER', 'OUTER', 'LEFT', 'RIGHT', 'CREATE', 'TABLE',
            'INDEX', 'DROP', 'ALTER', 'CASE', 'WHEN', 'THEN', 'END', 'AS',
            'AND', 'OR', 'LIKE', 'IN', 'IS', 'NULL', 'ORDER', 'BY', 'GROUP',
            'HAVING', 'DISTINCT', 'LIMIT', 'OFFSET'
        ]
        
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor('#569CD6'))
        keyword_format.setFontWeight(QFont.Bold)
        self.add_rules(keywords, keyword_format)
        
        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor('#CE9178'))
        self.highlight_rules.append((QRegExp("'[^']*'"), string_format))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor('#B5CEA8'))
        self.highlight_rules.append((QRegExp(r'\b\d+\b'), number_format))
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor('#57A64A'))
        self.highlight_rules.append((QRegExp('--[^\n]*'), comment_format))

    def add_rules(self, keywords, fmt):
        for keyword in keywords:
            pattern = QRegExp(r'\b' + keyword + r'\b', Qt.CaseInsensitive)
            self.highlight_rules.append((pattern, fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlight_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length)
        self.setCurrentBlockState(0)

class SQLInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.query_history = []
        self.current_history_index = -1
        self.initUI()
        self.setObjectName("SQLInterface")
        self.initSampleDB()
        self.last_execution_time = 0
        self.setup_shortcuts()
        self.update_schema_browser()
        self.setup_history_context_menu()

    def initUI(self):
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Schema Browser
        self.schema_tree = ParameterTree(showHeader=False)
        left_layout.addWidget(SubtitleLabel('Schema Browser'))
        left_layout.addWidget(self.schema_tree)
        
        # Query History
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.load_history_query)
        left_layout.addWidget(SubtitleLabel('Query History'))
        left_layout.addWidget(self.history_list)
        
        # Right Panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Editor with line numbers
        self.editor = CodeEditor()
        self.editor.setPlaceholderText("Enter SQL query here... (Ctrl+Enter to execute)")
        self.highlighter = SQLHighlighter(self.editor.document())
        
        # Toolbar
        toolbar = QToolBar()
        self.executeBtn = PrimaryToolButton(FIF.SYNC, self)
        self.executeBtn.clicked.connect(self.executeQuery)
        
        self.exportBtn = PrimaryToolButton(FIF.SAVE, self)
        self.exportBtn.clicked.connect(self.export_results)
        
        self.formatBtn = PrimaryToolButton(FIF.ALIGNMENT, self)
        self.formatBtn.clicked.connect(self.format_sql)
        
        toolbar.addWidget(self.executeBtn)
        toolbar.addWidget(self.exportBtn)
        toolbar.addWidget(self.formatBtn)
        
        right_layout.addWidget(toolbar)
        right_layout.addWidget(self.editor)
        
        # Result Section
        self.resultTable = TableWidget()
        self.stats_label = BodyLabel()
        
        right_layout.addWidget(self.resultTable)
        right_layout.addWidget(self.stats_label)
        
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(right_panel)
        self.main_splitter.setSizes([200, 600])
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.main_splitter)

    def dict_factory(self,cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def initSampleDB(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = self.dict_factory
        self.cursor = self.conn.cursor()
        
        # Örnek tablolar
        tables = {
            'employees': [
                ('id', 'INTEGER PRIMARY KEY'),
                ('name', 'TEXT'),
                ('age', 'INTEGER'),
                ('department', 'TEXT')
            ],
            'sales': [
                ('id', 'INTEGER PRIMARY KEY'),
                ('employee_id', 'INTEGER'),
                ('amount', 'REAL'),
                ('date', 'TEXT')
            ]
        }
        
        # Tabloları oluştur
        for name, cols in tables.items():
            cols_str = ', '.join([f'{n} {t}' for n, t in cols])
            self.cursor.execute(f'CREATE TABLE {name} ({cols_str})')
            
            # Örnek veri ekleme
            if name == 'employees':
                self.cursor.executemany(
                    f'INSERT INTO {name} (name, age, department) VALUES (?, ?, ?)',
                    [('Employee{}'.format(i), 20 + i, 'Department{}'.format(i % 3)) for i in range(10)]
                )
            elif name == 'sales':
                self.cursor.executemany(
                    f'INSERT INTO {name} (employee_id, amount, date) VALUES (?, ?, ?)',
                    [(i % 10 + 1, 100.0 * i, '2023-01-{:02d}'.format(i % 30 + 1)) for i in range(10)]
                )
        
        self.conn.commit()


    def executeQuery(self):
        query = self.editor.toPlainText().strip()
        if not query:
            return

        start_time = time.time()
        try:
            # Performans izleme
            self.cursor.execute("EXPLAIN QUERY PLAN " + query)
            explain_result = self.cursor.fetchall()
            
            self.cursor.execute(query)
            
            if query.upper().startswith('SELECT'):
                df = pd.read_sql_query(query, self.conn)
                self.showResults(df)
            else:
                self.conn.commit()
                self.showError('Success', f'Query executed successfully. Rows affected: {self.cursor.rowcount}')
            
            # Performans istatistikleri
            self.last_execution_time = time.time() - start_time
            self.update_stats()
            
            # Şema değişikliklerini takip et
            if any(cmd in query.upper() for cmd in ['CREATE', 'ALTER', 'DROP']):
                self.update_schema_browser()
                
            # Query history
            self.add_to_history(query)
            
        except sqlite3.Error as e:
            self.showError('SQL Error', str(e))
            error_line = self.find_error_line(str(e))
            self.highlight_error_line(error_line)

    def showResults(self, df):
        self.resultTable.setRowCount(len(df))
        self.resultTable.setColumnCount(len(df.columns))
        self.resultTable.setHorizontalHeaderLabels(df.columns.tolist())

        for row in range(len(df)):
            for col in range(len(df.columns)):
                self.resultTable.setItem(row, col, QTableWidgetItem(str(df.iat[row, col])))

    def showError(self, title, content):
        InfoBar.error(
            title=title,
            content=content,
            parent=self.parent,
            position=InfoBarPosition.TOP
        )

    def find_error_line(self, error_msg):
        match = re.search(r'\(line (\d+)\)', error_msg)
        return int(match.group(1)) if match else 1

    def highlight_error_line(self, line_number):
        text_cursor = self.editor.textCursor()
        text_cursor.movePosition(QTextCursor.Start)
        
        for _ in range(line_number - 1):
            text_cursor.movePosition(QTextCursor.Down)
            
        text_cursor.select(QTextCursor.LineUnderCursor)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor('#FFB6C1'))
        text_cursor.mergeCharFormat(fmt)
        
        QTimer.singleShot(2000, lambda: 
            text_cursor.mergeCharFormat(QTextCharFormat()))

    def load_history_query(self, item):
        query = item.text()
        self.editor.setPlainText(query)
        self.current_history_index = self.history_list.row(item)

    def add_to_history(self, query):
        if query not in self.query_history:
            if len(self.query_history) >= 100:
                self.query_history.pop(0)
                self.history_list.takeItem(0)
                
            self.query_history.append(query)
            item = QListWidgetItem(query)
            
            if query.upper().startswith('SELECT'):
                item.setIcon(FIF.SEARCH.icon())
            elif any(query.upper().startswith(cmd) for cmd in ['INSERT', 'UPDATE', 'DELETE']):
                item.setIcon(FIF.EDIT.icon())
            else:
                item.setIcon(FIF.DOCUMENT.icon())
                
            self.history_list.addItem(item)
            self.current_history_index = len(self.query_history) - 1

    def clear_history(self):
        self.query_history.clear()
        self.history_list.clear()
        self.current_history_index = -1

    def setup_history_context_menu(self):
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_history_menu)

    def show_history_menu(self, pos):
        menu = RoundMenu(parent=self)
        
        if self.history_list.itemAt(pos):
            menu.addAction(Action(FIF.COPY, 'Copy', triggered=self.copy_history_item))
            menu.addAction(Action(FIF.DELETE, 'Delete', triggered=self.delete_history_item))
            menu.addSeparator()
        
        menu.addAction(Action(FIF.CLOSE, 'Clear History', triggered=self.clear_history))
        menu.exec_(self.history_list.mapToGlobal(pos))

    def copy_history_item(self):
        if item := self.history_list.currentItem():
            QApplication.clipboard().setText(item.text())

    def delete_history_item(self):
        if item := self.history_list.currentItem():
            index = self.history_list.row(item)
            self.history_list.takeItem(index)
            self.query_history.pop(index)
            self.current_history_index = min(self.current_history_index, len(self.query_history) - 1)

    def format_sql(self):
        text = self.editor.toPlainText().strip()
        if not text:
            return
        
        keywords = [
            'SELECT', 'FROM', 'WHERE', 'JOIN', 
            'ORDER BY', 'GROUP BY', 'HAVING', 'LIMIT'
        ]
        
        formatted = []
        indent_level = 0
        for line in text.split('\n'):
            line = line.strip()
            upper_line = line.upper()
            
            if any(upper_line.startswith(kw) for kw in ['END', 'ELSE']):
                indent_level = max(0, indent_level - 1)
            
            formatted.append(' ' * (4 * indent_level) + line)
            
            if any(upper_line.startswith(kw) for kw in ['CASE', 'WHEN', 'ELSE']):
                indent_level += 1
    
        self.editor.setPlainText('\n'.join(formatted))

    def export_results(self):
        if self.resultTable.rowCount() == 0:
            self.showError("Export Error", "No data to export")
            return
            
        path = QFileDialog.getSaveFileName(
            self, "Export Results", "", 
            "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json)"
        )[0]
        
        if not path:
            return
            
        data = []
        for i in range(self.resultTable.rowCount()):
            row = []
            for j in range(self.resultTable.columnCount()):
                item = self.resultTable.item(i, j)
                row.append(item.text() if item else "")
            data.append(row)
        
        df = pd.DataFrame(data, columns=[
            self.resultTable.horizontalHeaderItem(j).text() 
            for j in range(self.resultTable.columnCount())
        ])
        
        if path.endswith('.csv'):
            df.to_csv(path, index=False)
        elif path.endswith('.xlsx'):
            df.to_excel(path, index=False)
        elif path.endswith('.json'):
            df.to_json(path, orient='records')

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Return"), self.editor, self.executeQuery)
        QShortcut(QKeySequence("Ctrl+Up"), self, self.history_prev)
        QShortcut(QKeySequence("Ctrl+Down"), self, self.history_next)

    def history_prev(self):
        if self.query_history:
            self.current_history_index = max(0, self.current_history_index - 1)
            self.editor.setPlainText(self.query_history[self.current_history_index])

    def history_next(self):
        if self.query_history:
            self.current_history_index = min(len(self.query_history)-1, self.current_history_index + 1)
            self.editor.setPlainText(self.query_history[self.current_history_index])

    def update_stats(self):
        stats_text = f"""
        Execution time: {self.last_execution_time:.2f}s | 
        Rows returned: {self.resultTable.rowCount()} | 
        Columns: {self.resultTable.columnCount()}
        """
        self.stats_label.setText(stats_text)

    def update_schema_browser(self):
        self.schema_tree.clear()
        tables = self.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """).fetchall()
        
        for table in tables:
            table_node = Parameter.create(name=table['name'], type='group')
            columns = self.cursor.execute(f"PRAGMA table_info({table['name']})").fetchall()
            
            for col in columns:
                col_info = f"{col['name']} ({col['type']})"
                if col['pk']:
                    col_info += " 🔑"
                table_node.addChild({'name': col_info, 'type': 'str'})
            
            self.schema_tree.addParameters(table_node)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width()

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num /= 10
            digits += 1
        return 15 + self.fontMetrics().width('9') * digits

    def update_line_number_area_width(self):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), 
                self.lineNumberArea.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(
            cr.left(), cr.top(),
            self.line_number_area_width(), cr.height()
        )

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#f0f0f0"))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#606060"))
                painter.drawText(
                    0, int(top), 
                    self.lineNumberArea.width(), 
                    self.fontMetrics().height(),
                    Qt.AlignCenter, number
                )
            
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)
