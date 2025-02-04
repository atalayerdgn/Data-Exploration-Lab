from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, 
                            QColorDialog, QCheckBox, QSpinBox)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
import scipy.stats as stats
import pyqtgraph as pg
from pandas.api.types import is_datetime64_any_dtype
from sklearn.linear_model import LinearRegression
from implementations import (ComboBox, PrimaryPushButton, ToolButton, CaptionLabel, 
                            InfoBar, InfoBarPosition, isDarkTheme)
from qfluentwidgets import (FluentIcon as FIF, ComboBox, PrimaryPushButton, ToolButton, InfoBar, InfoBarPosition, CaptionLabel)

class EnhancedVisualizationInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("EnhancedVisualizationInterface")
        self.current_color = '#1f77b4'
        self.current_style = 'ggplot'
        self.initUI()
        self.setupConnections()

    def initUI(self):
        # Plot components
        self.figure = Figure(facecolor='#FFFFFF' if isDarkTheme() else '#1E1E1E', dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Widgets
        self.plotType = ComboBox(self)
        self.plotType.addItems(['Scatter', 'Line', 'Bar', 'Histogram', 'Boxplot', 'Time Series', 'Heatmap'])
        
        self.xAxis = ComboBox(self)
        self.yAxis = ComboBox(self)
        
        # Time series controls
        self.freqCombo = ComboBox(self)
        self.freqCombo.addItems(['Raw', 'Daily (D)', 'Weekly (W)', 'Monthly (M)', 'Quarterly (Q)', 'Yearly (Y)'])
        self.freqCombo.setVisible(False)
        
        # Style controls
        self.styleCombo = ComboBox(self)
        self.styleCombo.addItems(plt.style.available)
        self.styleCombo.setCurrentText(self.current_style)
        
        # Buttons
        self.plotBtn = PrimaryPushButton('Generate Plot', self, FIF.ADD)
        self.exportBtn = ToolButton(FIF.SHARE, self)
        self.colorBtn = ToolButton(FIF.BRUSH, self)
        
        # Layout
        controlLayout = QHBoxLayout()
        controlLayout.addWidget(CaptionLabel('Plot Type:'))
        controlLayout.addWidget(self.plotType)
        controlLayout.addWidget(CaptionLabel('X:'))
        controlLayout.addWidget(self.xAxis)
        controlLayout.addWidget(CaptionLabel('Y:'))
        controlLayout.addWidget(self.yAxis)
        controlLayout.addWidget(CaptionLabel('Freq:'))
        controlLayout.addWidget(self.freqCombo)
        controlLayout.addWidget(self.colorBtn)
        controlLayout.addWidget(self.styleCombo)
        controlLayout.addWidget(self.plotBtn)
        controlLayout.addWidget(self.exportBtn)
        
        mainLayout = QVBoxLayout(self)
        mainLayout.addLayout(controlLayout)
        mainLayout.addWidget(self.canvas)
        mainLayout.addWidget(self.toolbar)

    def setupConnections(self):
        self.plotType.currentTextChanged.connect(self.updateAxes)
        self.plotBtn.clicked.connect(self.generatePlot)
        self.exportBtn.clicked.connect(self.exportPlot)
        self.colorBtn.clicked.connect(self.chooseColor)
        self.styleCombo.currentTextChanged.connect(self.updateStyle)

    def updateStyle(self, style):
        self.current_style = style
        plt.style.use(style)
        self.generatePlot()

    def chooseColor(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_color = color.name()
            self.generatePlot()

    def updateAxes(self):
        if self.parent.current_df is None:
            return
            
        plot_type = self.plotType.currentText()
        df = self.parent.current_df
        cols = df.columns.tolist()
        
        self.xAxis.clear()
        self.yAxis.clear()
        self.freqCombo.setVisible(plot_type == 'Time Series')

        if plot_type == 'Time Series':
            datetime_cols = [c for c in cols if is_datetime64_any_dtype(df[c])]
            numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
            self.xAxis.addItems(datetime_cols)
            self.yAxis.addItems(numeric_cols)
        elif plot_type in ['Histogram', 'Boxplot']:
            self.xAxis.addItems(cols)
            self.yAxis.setEnabled(False)
        elif plot_type == 'Heatmap':
            self.xAxis.addItems(cols)
            self.yAxis.addItems(cols)
        else:
            self.xAxis.addItems(cols)
            self.yAxis.addItems(cols)
            self.yAxis.setEnabled(True)

    def generatePlot(self):
        if self.parent.current_df is None:
            self.showError('No Data', 'Please load data first')
            return
            
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            plot_type = self.plotType.currentText()
            df = self.parent.current_df
            
            if plot_type == 'Time Series':
                self.handleTimeSeriesPlot(ax)
            elif plot_type == 'Heatmap':
                self.handleHeatmapPlot(ax)
            else:
                self.handleBasicPlots(ax, plot_type, df)
            
            ax.grid(True)
            self.canvas.draw()
            
        except Exception as e:
            self.showError('Plot Error', str(e))

    def handleTimeSeriesPlot(self, ax):
        x_col = self.xAxis.currentText()
        y_col = self.yAxis.currentText()
        df = self.parent.current_df
        
        if not is_datetime64_any_dtype(df[x_col]):
            self.showError('Invalid Data', 'X axis must be datetime for time series')
            return
        
        freq = self.freqCombo.currentText().split('(')[-1].split(')')[0].strip()
        ts_data = df.set_index(x_col)[y_col]
        
        if freq != 'Raw':
            ts_data = ts_data.resample(freq).mean().dropna()
        
        ax.plot(ts_data.index, ts_data.values, color=self.current_color)
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
        ax.figure.autofmt_xdate()
        ax.set_title(f'Time Series: {y_col}', color='white' if isDarkTheme() else 'black')

    def handleHeatmapPlot(self, ax):
        df = self.parent.current_df.select_dtypes(include=np.number)
        corr = df.corr()
        cax = ax.matshow(corr, cmap='coolwarm')
        self.figure.colorbar(cax)
        ax.set_xticks(np.arange(len(corr.columns)))
        ax.set_yticks(np.arange(len(corr.columns)))
        ax.set_xticklabels(corr.columns, rotation=45)
        ax.set_yticklabels(corr.columns)
        ax.set_title('Correlation Heatmap')

    def handleBasicPlots(self, ax, plot_type, df):
        x = df[self.xAxis.currentText()]
        y = df[self.yAxis.currentText()] if self.yAxis.currentText() else None
        
        if plot_type == 'Scatter':
            ax.scatter(x, y, c=self.current_color)
            self.addRegression(ax, x, y)
        elif plot_type == 'Line':
            ax.plot(x, y, color=self.current_color)
        elif plot_type == 'Bar':
            y.value_counts().plot(kind='bar', ax=ax, color=self.current_color)
        elif plot_type == 'Histogram':
            x.hist(ax=ax, color=self.current_color)
        elif plot_type == 'Boxplot':
            df.boxplot(column=x.name, ax=ax)
        
        ax.set_title(f'{plot_type} Plot', color='white' if isDarkTheme() else 'black')

    def addRegression(self, ax, x, y):
        try:
            model = LinearRegression().fit(x.values.reshape(-1,1), y)
            ax.plot(x, model.predict(x.values.reshape(-1,1)), color='red')
            r, p = stats.pearsonr(x, y)
            text_color = 'white' if isDarkTheme() else 'black'
            ax.text(0.05, 0.95, 
                    f'R² = {model.score(x.values.reshape(-1,1), y):.2f}\np = {p:.4f}',
                    transform=ax.transAxes,
                    color=text_color,
                    bbox=dict(facecolor='#404040' if isDarkTheme() else '#f0f0f0', 
                             alpha=0.8))
        except Exception as e:
            self.showError('Regression Error', str(e))

    def exportPlot(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg)")
        if path:
            self.figure.savefig(path, facecolor=self.figure.get_facecolor())
            self.showInfo('Export Successful', f'Plot saved to {path}')

    def showInfo(self, title, content):
        InfoBar.success(
            title=title,
            content=content,
            parent=self.parent,
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def showError(self, title, content):
        InfoBar.error(
            title=title,
            content=content,
            parent=self.parent,
            position=InfoBarPosition.TOP,
            duration=5000
        )


class InteractiveTimeSeries(EnhancedVisualizationInterface):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initPyQtGraph()
        self.rolling_window = 0

    def initPyQtGraph(self):
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.setBackground('#1E1E1E' if isDarkTheme() else '#FFFFFF')
        self.plotWidget.setMinimumHeight(400)
        
        # Rolling mean controls
        self.rollingSpin = QSpinBox()
        self.rollingSpin.setRange(0, 365)
        self.rollingSpin.setValue(0)
        self.rollingSpin.setPrefix("Window: ")
        
        # Add to layout
        self.layout().insertWidget(1, self.plotWidget)
        self.layout().insertWidget(2, self.rollingSpin)
        
        # Connections
        self.rollingSpin.valueChanged.connect(self.updateRolling)

    def updateRolling(self, value):
        self.rolling_window = value
        self.generatePlot()

    def handleTimeSeriesPlot(self, ax):
        super().handleTimeSeriesPlot(ax)
        self.updateInteractivePlot()

    def updateInteractivePlot(self):
        try:
            self.plotWidget.clear()
            x_col = self.xAxis.currentText()
            y_col = self.yAxis.currentText()
            df = self.parent.current_df
            
            ts_data = df.set_index(x_col)[y_col]
            freq = self.freqCombo.currentText().split('(')[-1].split(')')[0].strip()
            
            if freq != 'Raw':
                ts_data = ts_data.resample(freq).mean().dropna()
            
            if self.rolling_window > 0:
                ts_data = ts_data.rolling(self.rolling_window).mean().dropna()
            
            # Convert datetime to timestamp
            x = ts_data.index.view(np.int64) // 10**9  # Convert nanoseconds to seconds
            y = ts_data.values
            
            # Create plot
            self.plotWidget.plot(x, y, 
                               pen=pg.mkPen(color=self.current_color, width=2),
                               symbol='o',
                               symbolSize=5,
                               symbolBrush=self.current_color)
            
            # Date axis formatting
            date_axis = pg.DateAxisItem(orientation='bottom')
            self.plotWidget.setAxisItems({'bottom': date_axis})
            self.plotWidget.setLabel('left', y_col)
            self.plotWidget.setLabel('bottom', x_col)
            self.plotWidget.showGrid(x=True, y=True)
            
        except Exception as e:
            self.showError('Interactive Plot Error', str(e))
