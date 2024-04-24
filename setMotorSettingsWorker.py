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

class setMotorSettingsWorker(QRunnable):
    """Worker class to read and update motor positions"""

    def __init__(self, mc, x_speed, y_speed, z_speed, x_lower, x_upper, y_lower, y_upper, z_lower, z_upper):
        print('motor settings')
        super(setMotorSettingsWorker, self).__init__()
        self.signals = WorkerSignals()  # can send signals to main GUI
        self.mc = mc
        self.xa = mc.axis['x'] # x axis on stretched wire stage 2
        self.ya = mc.axis['y']
        self.za = mc.axis['z']
        self.x_speed = x_speed
        self.y_speed = y_speed
        self.z_speed = z_speed
        self.x_lower = x_lower
        self.x_upper = x_upper
        self.y_lower = y_lower
        self.y_upper = y_upper
        self.z_lower = z_lower
        self.z_upper = z_upper

    def run(self):
        """Task to read motor positions and emit signal"""
        try:
            self.signals.progress.emit(10)  # send progress signal to GUI
            # Set new speeds
            print('set speeds')
            self.xa.setSpeed(self.x_speed)
            self.ya.setSpeed(self.y_speed)
            self.za.setSpeed(self.z_speed)
            time.sleep(0.1)

            self.signals.progress.emit(30)

            print('set limits')
            self.xa.setLimits((float(self.x_lower), float(self.x_upper)))
            self.ya.setLimits((float(self.y_lower), float(self.y_upper)))
            self.za.setLimits((float(self.z_lower), float(self.z_upper)))

            self.signals.progress.emit(50)

        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:  # if no exceptions
            # Emit signal
            x_speed = "{:.1f}".format(self.xa.getSpeed())
            y_speed = "{:.1f}".format(self.ya.getSpeed())
            z_speed = "{:.1f}".format(self.za.getSpeed())

            self.signals.progress.emit(70)

            x_lims = self.xa.getLimits()
            y_lims = self.ya.getLimits()
            z_lims = self.za.getLimits()
            x_lower = str(x_lims[0])
            x_upper = str(x_lims[1])
            y_lower = str(y_lims[0])
            y_upper = str(y_lims[1])
            z_lower = str(z_lims[0])
            z_upper = str(z_lims[1])

            self.signals.result.emit(
                [x_speed, y_speed, z_speed, x_lower, x_upper, y_lower, y_upper, z_lower, z_upper])  # emit fields
            print('speeds emitted')
        finally:
            self.signals.progress.emit(99)
            self.signals.finished.emit()