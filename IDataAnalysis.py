import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTableWidget, QTableWidgetItem, QFileDialog, QDialog, QFormLayout,
                            QMessageBox, QComboBox, QPushButton, QSplitter, QFrame, QLabel, QCheckBox, QDialogButtonBox, QLineEdit)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

class DataAnalysisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_df = pd.DataFrame()
        self.history = []
        self.setObjectName('Data Analysis')
        self.current_step = -1
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Advanced Data Analysis Tool')
        self.setGeometry(100, 100, 1200, 800)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Toolbar
        self.toolbar = self.addToolBar('Main Toolbar')
        self.toolbar.setIconSize(QSize(24, 24))
        
        # Data controls
        self.load_btn = QPushButton(QIcon('folder.png'), 'Load Data', self)
        self.load_btn.clicked.connect(self.load_data)
        self.toolbar.addWidget(self.load_btn)
        
        self.clean_btn = QPushButton(QIcon('brush.png'), 'Clean Data', self)
        self.clean_btn.clicked.connect(self.show_cleaning_dialog)
        self.toolbar.addWidget(self.clean_btn)
        
        self.filter_btn = QPushButton(QIcon('filter.png'), 'Filter Data', self)
        self.filter_btn.clicked.connect(self.show_filter_dialog)
        self.toolbar.addWidget(self.filter_btn)
        
        # Visualization controls
        self.toolbar.addSeparator()
        self.viz_combo = QComboBox()
        self.viz_combo.addItems(['Histogram', 'Scatter Plot', 'Box Plot', 'Correlation Matrix'])
        self.toolbar.addWidget(QLabel('Visualization:'))
        self.toolbar.addWidget(self.viz_combo)
        self.viz_combo.currentIndexChanged.connect(self.update_visualization)
        
        # ML controls
        self.toolbar.addSeparator()
        self.model_combo = QComboBox()
        self.model_combo.addItems(['Linear Regression', 'Random Forest', 'Logistic Regression'])
        self.target_combo = QComboBox()
        self.train_btn = QPushButton('Train Model', self)
        self.train_btn.clicked.connect(self.train_model)
        
        self.toolbar.addWidget(QLabel('ML:'))
        self.toolbar.addWidget(self.model_combo)
        self.toolbar.addWidget(self.target_combo)
        self.toolbar.addWidget(self.train_btn)
        
        # Undo/redo
        self.toolbar.addSeparator()
        self.undo_btn = QPushButton(QIcon('undo.png'), '', self)
        self.redo_btn = QPushButton(QIcon('redo.png'), '', self)
        self.undo_btn.clicked.connect(self.undo_action)
        self.redo_btn.clicked.connect(self.redo_action)
        self.toolbar.addWidget(self.undo_btn)
        self.toolbar.addWidget(self.redo_btn)
        
        # Splitter for table and visualization
        splitter = QSplitter(Qt.Vertical)
        
        # Data table
        self.table = QTableWidget()
        splitter.addWidget(self.table)
        
        # Visualization canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        splitter.addWidget(self.canvas)
        
        main_layout.addWidget(splitter)
        
        self.update_controls()
        
    def update_controls(self):
        has_data = not self.current_df.empty
        self.clean_btn.setEnabled(has_data)
        self.filter_btn.setEnabled(has_data)
        self.viz_combo.setEnabled(has_data)
        self.model_combo.setEnabled(has_data)
        self.train_btn.setEnabled(has_data)
        self.target_combo.setEnabled(has_data)
        
        if has_data:
            self.target_combo.clear()
            self.target_combo.addItems(self.current_df.columns)

    def load_data(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Data File", "", 
                                            "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if path:
            try:
                if path.endswith('.csv'):
                    df = pd.read_csv(path)
                else:
                    df = pd.read_excel(path)
                
                self.current_df = df
                self.populate_table()
                self.save_state()
                self.update_controls()
                
            except Exception as e:
                QMessageBox.critical(self, "Loading Error", str(e))

    def populate_table(self):
        self.table.setRowCount(0)
        if self.current_df.empty:
            return
            
        self.table.setRowCount(self.current_df.shape[0])
        self.table.setColumnCount(self.current_df.shape[1])
        self.table.setHorizontalHeaderLabels(self.current_df.columns)
        
        for row in range(self.current_df.shape[0]):
            for col in range(self.current_df.shape[1]):
                val = str(self.current_df.iloc[row, col])
                self.table.setItem(row, col, QTableWidgetItem(val))

    def save_state(self):
        self.history = self.history[:self.current_step+1]
        self.history.append(self.current_df.copy())
        self.current_step += 1
        self.update_undo_redo()

    def update_undo_redo(self):
        self.undo_btn.setEnabled(self.current_step > 0)
        self.redo_btn.setEnabled(self.current_step < len(self.history)-1)

    def undo_action(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.current_df = self.history[self.current_step].copy()
            self.populate_table()
            self.update_undo_redo()

    def redo_action(self):
        if self.current_step < len(self.history)-1:
            self.current_step += 1
            self.current_df = self.history[self.current_step].copy()
            self.populate_table()
            self.update_undo_redo()

    def show_cleaning_dialog(self):
        dialog = CleaningDialog(self)
        if dialog.exec_():
            self.apply_cleaning(dialog.get_operations())

    def apply_cleaning(self, operations):
        try:
            df = self.current_df.copy()
            
            if operations['handle_missing'] == 'drop':
                df = df.dropna()
            elif operations['handle_missing'] == 'fill':
                if operations['fill_method'] == 'mean':
                    df = df.fillna(df.mean())
                elif operations['fill_method'] == 'median':
                    df = df.fillna(df.median())
            
            if operations['remove_duplicates']:
                df = df.drop_duplicates()
            
            if operations['outlier_method'] == 'zscore':
                numeric = df.select_dtypes(include=np.number)
                z = np.abs(stats.zscore(numeric))
                df = df[(z < 3).all(axis=1)]
            
            self.current_df = df
            self.save_state()
            self.populate_table()
            QMessageBox.information(self, 'Success', 'Data cleaning completed')
            
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def show_filter_dialog(self):
        dialog = FilterDialog(self.current_df.columns, self)
        if dialog.exec_():
            self.apply_filter(dialog.get_filter())

    def apply_filter(self, filter_expr):
        try:
            filtered_df = self.current_df.query(filter_expr)
            self.current_df = filtered_df
            self.save_state()
            self.populate_table()
            QMessageBox.information(self, 'Success', f'Filter applied: {len(filtered_df)} rows remaining')
        except Exception as e:
            QMessageBox.critical(self, 'Filter Error', str(e))

    def update_visualization(self):
        viz_type = self.viz_combo.currentText()
        self.figure.clear()
        
        if self.current_df.empty:
            return
            
        numeric_df = self.current_df.select_dtypes(include=np.number)
        if numeric_df.empty:
            QMessageBox.warning(self, 'Visualization Error', 'No numeric columns to visualize')
            return
            
        ax = self.figure.add_subplot(111)
        
        if viz_type == 'Histogram':
            numeric_df.hist(ax=ax, bins=15)
        elif viz_type == 'Scatter Plot':
            pd.plotting.scatter_matrix(numeric_df, ax=ax)
        elif viz_type == 'Box Plot':
            numeric_df.plot.box(ax=ax)
        elif viz_type == 'Correlation Matrix':
            sns.heatmap(numeric_df.corr(), ax=ax, annot=True)
            
        self.canvas.draw()

    def train_model(self):
        try:
            target = self.target_combo.currentText()
            df = self.current_df.dropna()
            
            X = df.drop(columns=[target])
            y = df[target]
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
            
            model = LinearRegression()
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_test)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            
            result = (f"Model Results:\n"
                     f"RMSE: {rmse:.2f}\n"
                     f"R² Score: {r2:.2f}\n"
                     f"Coefficients: {model.coef_}")
            
            QMessageBox.information(self, 'Training Results', result)
            
        except Exception as e:
            QMessageBox.critical(self, 'Training Error', str(e))

class CleaningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Data Cleaning Options')
        layout = QFormLayout(self)
        
        self.missing_combo = QComboBox()
        self.missing_combo.addItems(['Do nothing', 'Drop NA', 'Fill NA'])
        
        self.fill_combo = QComboBox()
        self.fill_combo.addItems(['Mean', 'Median'])
        
        self.duplicates_check = QCheckBox('Remove duplicates')
        self.outlier_combo = QComboBox()
        self.outlier_combo.addItems(['None', 'Z-Score'])
        
        layout.addRow('Missing Values:', self.missing_combo)
        layout.addRow('Fill Method:', self.fill_combo)
        layout.addRow(self.duplicates_check)
        layout.addRow('Outlier Handling:', self.outlier_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_operations(self):
        return {
            'handle_missing': self.missing_combo.currentText().split()[0].lower(),
            'fill_method': self.fill_combo.currentText().lower(),
            'remove_duplicates': self.duplicates_check.isChecked(),
            'outlier_method': self.outlier_combo.currentText().lower()
        }

class FilterDialog(QDialog):
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.setWindowTitle('Build Filter')
        layout = QFormLayout(self)
        
        self.column_combo = QComboBox()
        self.column_combo.addItems(columns)
        
        self.operator_combo = QComboBox()
        self.operator_combo.addItems(['==', '!=', '>', '<', '>=', '<='])
        
        self.value_edit = QLineEdit()
        
        layout.addRow('Column:', self.column_combo)
        layout.addRow('Operator:', self.operator_combo)
        layout.addRow('Value:', self.value_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_filter(self):
        col = self.column_combo.currentText()
        op = self.operator_combo.currentText()
        val = self.value_edit.text()
        return f"`{col}` {op} {val}"
