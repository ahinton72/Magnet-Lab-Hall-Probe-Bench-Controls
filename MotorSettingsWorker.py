import PyQt5
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QMutex
import traceback
import sys
import time
import datetime
from WorkerSignals import WorkerSignals
mutex = QMutex()
import numpy as np
import csv

class MotorSettingsWorker(QRunnable):
    """Worker class to read and update motor positions"""

    def __init__(self, mc):
        # print('motor settings')
        super(MotorSettingsWorker, self).__init__()
        self.signals = WorkerSignals()  # can send signals to main GUI
        self.mc = mc
        self.xa = mc.axis['x'] # x-axis on stretched wire stage 2
        self.ya = mc.axis['y']
        self.za = mc.axis['z']

    def run(self):
        """Task to read motor positions and emit signal"""
        global mc
        mutex.lock()  # lock access to motor controller class
        try:
            x_speed = "{:.1f}".format(self.xa.getSpeed())
            y_speed = "{:.1f}".format(self.ya.getSpeed())
            z_speed = "{:.1f}".format(self.za.getSpeed())
            x_lims = self.xa.getLimits()
            y_lims = self.ya.getLimits()
            z_lims = self.za.getLimits()
            x_lower = str(x_lims[0])
            x_upper = str(x_lims[1])
            y_lower = str(y_lims[0])
            y_upper = str(y_lims[1])
            z_lower = str(z_lims[0])
            z_upper = str(z_lims[1])
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:  # if no exceptions
            # Emit signal
            self.signals.result.emit(
                [x_speed, y_speed, z_speed, x_lower, x_upper, y_lower, y_upper, z_lower, z_upper])  # emit fields
        finally:
            mutex.unlock()
            self.signals.finished.emit()