import sys
import subprocess
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3
import platform
from io import StringIO
from functools import partial
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, 
                            QPlainTextEdit, QLineEdit, QTextEdit, QSizePolicy, QTableWidgetItem, QColorDialog)
from PyQt5.QtCore import Qt, QProcess, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QTextCursor, QTextFormat, QFont, QSyntaxHighlighter, QTextCharFormat
from qfluentwidgets import (FluentWindow, NavigationItemPosition, MessageBox, PrimaryPushButton, 
                           PlainTextEdit, TableWidget, InfoBar, InfoBarPosition, FluentIcon as FIF,
                           SplitTitleBar, ComboBox, CheckBox, SpinBox, ToolButton, ToggleButton,
                           CommandBar, Action, ToolTipFilter, StateToolTip, LineEdit, CaptionLabel,
                           setTheme, Theme, isDarkTheme, ScrollArea, TabBar, TabItem, PushButton,
                           EditableComboBox, SearchLineEdit, Pivot, setFont, FlowLayout)
from qfluentwidgets.components import LineEdit
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from sklearn.linear_model import LinearRegression
from scipy import stats
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
