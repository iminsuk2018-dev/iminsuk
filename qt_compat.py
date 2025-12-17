"""
Qt Compatibility Layer
Provides compatibility between PySide6 and PyQt5
"""
import sys

# Try PySide6 first, fallback to PyQt5
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtCore import Signal, Slot
    QT_API = "PySide6"
except ImportError:
    try:
        from PyQt5 import QtCore, QtGui, QtWidgets
        from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
        QT_API = "PyQt5"

        # PyQt5 compatibility adjustments
        # exec_ is deprecated in PySide6, use exec instead
        if not hasattr(QtWidgets.QDialog, 'exec'):
            QtWidgets.QDialog.exec = QtWidgets.QDialog.exec_
        if not hasattr(QtWidgets.QApplication, 'exec'):
            QtWidgets.QApplication.exec = QtWidgets.QApplication.exec_
        if not hasattr(QtCore.QThread, 'exec'):
            QtCore.QThread.exec = QtCore.QThread.exec_

    except ImportError:
        print("Error: Neither PySide6 nor PyQt5 is installed.")
        print("Please install one of them using:")
        print("  pip install PySide6")
        print("  or")
        print("  pip install PyQt5")
        sys.exit(1)

print(f"Using {QT_API}")

# Export commonly used classes for convenience
QApplication = QtWidgets.QApplication
QMainWindow = QtWidgets.QMainWindow
QWidget = QtWidgets.QWidget
QDialog = QtWidgets.QDialog
QVBoxLayout = QtWidgets.QVBoxLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QFormLayout = QtWidgets.QFormLayout
QGridLayout = QtWidgets.QGridLayout
QSplitter = QtWidgets.QSplitter
QLabel = QtWidgets.QLabel
QPushButton = QtWidgets.QPushButton
QLineEdit = QtWidgets.QLineEdit
QTextEdit = QtWidgets.QTextEdit
QPlainTextEdit = QtWidgets.QPlainTextEdit
QTextBrowser = QtWidgets.QTextBrowser
QListWidget = QtWidgets.QListWidget
QListWidgetItem = QtWidgets.QListWidgetItem
QTreeWidget = QtWidgets.QTreeWidget
QTreeWidgetItem = QtWidgets.QTreeWidgetItem
QTableWidget = QtWidgets.QTableWidget
QTableWidgetItem = QtWidgets.QTableWidgetItem
QComboBox = QtWidgets.QComboBox
QCheckBox = QtWidgets.QCheckBox
QRadioButton = QtWidgets.QRadioButton
QSpinBox = QtWidgets.QSpinBox
QDoubleSpinBox = QtWidgets.QDoubleSpinBox
QSlider = QtWidgets.QSlider
QProgressBar = QtWidgets.QProgressBar
QGroupBox = QtWidgets.QGroupBox
QTabWidget = QtWidgets.QTabWidget
QTabBar = QtWidgets.QTabBar
QScrollArea = QtWidgets.QScrollArea
QScrollBar = QtWidgets.QScrollBar
QMenu = QtWidgets.QMenu
QMenuBar = QtWidgets.QMenuBar
QToolBar = QtWidgets.QToolBar
QStatusBar = QtWidgets.QStatusBar

# QAction location differs between PySide6 and PyQt5
if QT_API == "PySide6":
    QAction = QtGui.QAction
else:
    QAction = QtWidgets.QAction

QFileDialog = QtWidgets.QFileDialog
QMessageBox = QtWidgets.QMessageBox
QInputDialog = QtWidgets.QInputDialog
QColorDialog = QtWidgets.QColorDialog
QFontDialog = QtWidgets.QFontDialog
QDialogButtonBox = QtWidgets.QDialogButtonBox
QGraphicsView = QtWidgets.QGraphicsView
QGraphicsScene = QtWidgets.QGraphicsScene
QGraphicsPixmapItem = QtWidgets.QGraphicsPixmapItem
QGraphicsRectItem = QtWidgets.QGraphicsRectItem
QGraphicsTextItem = QtWidgets.QGraphicsTextItem
QFrame = QtWidgets.QFrame
QCompleter = QtWidgets.QCompleter

# QtCore
Qt = QtCore.Qt
QStringListModel = QtCore.QStringListModel
QThread = QtCore.QThread
QTimer = QtCore.QTimer
QSettings = QtCore.QSettings
QUrl = QtCore.QUrl
QPoint = QtCore.QPoint
QPointF = QtCore.QPointF
QRect = QtCore.QRect
QRectF = QtCore.QRectF
QSize = QtCore.QSize
QSizeF = QtCore.QSizeF
QEvent = QtCore.QEvent
QObject = QtCore.QObject

# QtGui
QPixmap = QtGui.QPixmap
QImage = QtGui.QImage
QIcon = QtGui.QIcon
QPainter = QtGui.QPainter
QBrush = QtGui.QBrush
QPen = QtGui.QPen
QColor = QtGui.QColor
QFont = QtGui.QFont
QKeySequence = QtGui.QKeySequence
QCursor = QtGui.QCursor
QTransform = QtGui.QTransform
QPalette = QtGui.QPalette
QTextCursor = QtGui.QTextCursor
QTextDocument = QtGui.QTextDocument

# QShortcut location differs between PySide6 and PyQt5
if QT_API == "PySide6":
    QShortcut = QtGui.QShortcut
else:
    QShortcut = QtWidgets.QShortcut

__all__ = [
    'QtCore', 'QtGui', 'QtWidgets',
    'Signal', 'Slot', 'QT_API',
    # Widgets
    'QApplication', 'QMainWindow', 'QWidget', 'QDialog',
    'QVBoxLayout', 'QHBoxLayout', 'QFormLayout', 'QGridLayout',
    'QSplitter', 'QLabel', 'QPushButton', 'QLineEdit',
    'QTextEdit', 'QPlainTextEdit', 'QTextBrowser',
    'QListWidget', 'QListWidgetItem', 'QTreeWidget', 'QTreeWidgetItem',
    'QTableWidget', 'QTableWidgetItem', 'QComboBox', 'QCheckBox',
    'QRadioButton', 'QSpinBox', 'QDoubleSpinBox', 'QSlider',
    'QProgressBar', 'QGroupBox', 'QTabWidget', 'QTabBar',
    'QScrollArea', 'QScrollBar', 'QMenu', 'QMenuBar',
    'QToolBar', 'QStatusBar', 'QAction', 'QFileDialog',
    'QMessageBox', 'QInputDialog', 'QColorDialog', 'QFontDialog',
    'QDialogButtonBox', 'QGraphicsView', 'QGraphicsScene', 'QGraphicsPixmapItem',
    'QGraphicsRectItem', 'QGraphicsTextItem', 'QFrame', 'QCompleter',
    # Core
    'Qt', 'QStringListModel', 'QThread', 'QTimer', 'QSettings', 'QUrl',
    'QPoint', 'QPointF', 'QRect', 'QRectF', 'QSize', 'QSizeF',
    'QEvent', 'QObject',
    # Gui
    'QPixmap', 'QImage', 'QIcon', 'QPainter', 'QBrush', 'QPen',
    'QColor', 'QFont', 'QKeySequence', 'QCursor', 'QTransform',
    'QPalette', 'QTextCursor', 'QTextDocument', 'QShortcut'
]
