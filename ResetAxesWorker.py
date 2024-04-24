import PyQt5
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QMutex
import traceback
import sys
import datetime
from WorkerSignals import WorkerSignals
mutex = QMutex()

class ResetAxesWorker(QRunnable):
    def __init__(self, mc):
        super(ResetAxesWorker, self).__init__()
        print('reset called ', datetime.datetime.now())
        self.signals = WorkerSignals()
        self.isRun = True  # isRun flag = true; do not stop action

        self.mc = mc
        self.xa = mc.axis['x'] # x axis on SW stage 2
        self.ya = mc.axis['y'] # y axis on SW stage 2
        self.za = mc.axis['z'] # z axis on SW stage 2

        print('initialised', datetime.datetime.now())

    def run(self):
        """Function to move Hall probe relative distance and track progress"""
        print('running', datetime.datetime.now())
        try:
            self.xa.reset()
            self.distance = 25
            self.signals.progress.emit(self.distance - 1)

            self.ya.reset()
            self.distance = 50
            self.signals.progress.emit(self.distance - 1)

            self.za.reset()
            self.distance = 75
            self.signals.progress.emit(self.distance - 1)

        except: # if Value error raised by soft limits exception
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))

        else:  # if no exceptions
            print('no errors')

            self.distance = 100
            self.signals.progress.emit(self.distance - 1)


        finally:
            print('emit finished signal')
            self.signals.finished.emit()
            print('finish signal emitted', datetime.datetime.now())