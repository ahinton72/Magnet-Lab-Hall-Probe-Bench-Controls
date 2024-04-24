import PyQt5
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QMutex
import traceback
import sys
from WorkerSignals import WorkerSignals
from teslameter_3MH6 import teslameter_3MH6


mutex = QMutex()


class FieldsWorker(QRunnable):
    """Worker class to read and update fields"""

    def __init__(self, HP, averages):
        super(FieldsWorker, self).__init__()
        self.HP = HP #set Hall probe class
        self.averages = averages
        self.signals = WorkerSignals()  # can send signals to main GUI

        self.locked = False


    def run(self):
        """Task to read Hall probe fields and emit signal"""
        try:
            fields = self.HP.get_fields(self.averages)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:  # if no exceptions
            bx = "{:.3f}".format(fields[0])  # Set bx as string value with 3 decimal points
            by = "{:.3f}".format(fields[1])  # Set by as string value with 3 decimal points
            bz = "{:.3f}".format(fields[2])  # Set bz as string value with 3 decimal points
            temp = "{:.3f}".format(fields[6])  # Set temperature as string value, 3 decimal places
            # Emit signal
            # print('Measured fields =', bx, by, bz, temp)
            self.signals.result.emit([bx, by, bz, temp])  # emit fields

        finally:
            self.signals.finished.emit()