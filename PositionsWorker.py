import PyQt5
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QMutex
import traceback
import sys
from WorkerSignals import WorkerSignals
mutex = QMutex()



class PositionsWorker(QRunnable):
    """Worker class to read and update motor positions"""

    def __init__(self, mc):
        # print('Positions')
        super(PositionsWorker, self).__init__()
        self.mc = mc
        self.xa = mc.axis['x'] # x axis on stretched wire stage 2
        self.ya = mc.axis['y']
        self.za = mc.axis['z']
        self.signals = WorkerSignals()  # can send signals to main GUI

    def run(self):
        """Task to read motor positions and emit signal"""
        #global mc
        #mutex.lock()  # lock access to motor controller class
        try:
            x_pos = "{:.3f}".format(self.xa.get_position())
            y_pos = "{:.3f}".format(self.ya.get_position())
            z_pos = "{:.3f}".format(self.za.get_position())
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:  # if no exceptions
            # Emit signal
            self.signals.result.emit([x_pos, y_pos, z_pos])  # emit fields
        finally:
            #mutex.unlock()
            self.signals.finished.emit()
