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

class setProbeSettingsWorker(QRunnable):
    """Worker class to set probe settings and update labels"""

    def __init__(self, HP, range, rate):
        # print('probe settings')
        super(setProbeSettingsWorker, self).__init__()
        self.signals = WorkerSignals()  # can send signals to main GUI
        self.HP = HP
        self.range = range
        self.rate = rate

    def run(self):
        """Task to read probe settings and emit signal"""
        print('running setProbeSettings')
        try:
            self.signals.progress.emit(20)  # send progress signal to GUI
            print('New range  = ', self.range)
            self.HP.set_range(self.range)  # query current measurement current_range
            self.HP.set_sample_rate(self.rate)
            self.signals.progress.emit(40)  # send progress signal to GUI
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:  # if no exceptions
            # Read new current_range and sample rates
            current_range = self.HP.get_range()  # query current measurement current_range
            self.signals.progress.emit(60)  # send progress signal to GUI
            sample_rate = "{:.0f}".format(self.HP.get_sample_rate())
            if self.HP.type() == '3MH6':
                if current_range[0:6] == 'mrng:2':  # if range 2
                    range_string = 'Measurement Range = 500 mT'
                elif current_range[0:6] == 'mrng:3':  # if range 3
                    range_string = 'Measurement Range = 2 T'
                else:  # if not range 2 or 3
                    range_string = 'Measurement Range = ?'

            elif self.HP.type() == '3MTS':
                range_list = ['100 mT', '500 mT', '3 T', '20 T']
                range_string = 'Measurement Range = ' + range_list[current_range]

            elif self.HP.type() == '3MH3':
                range_list = ['2 T']
                range_string = 'Measurement Range = ' + range_list[current_range]


            # Emit signal
            self.signals.result.emit([range_string, sample_rate])  # emit fields
            self.signals.progress.emit(80)  # send progress signal to GUI
        finally:
            self.signals.progress.emit(99)  # send progress signal to GUI
            self.signals.finished.emit()
            print('worker ran ok')
