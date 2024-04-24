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

class ProbeSettingsWorker(QRunnable):
    """Worker class to read probe settings and update labels"""

    def __init__(self, HP):
        # print('probe settings')
        super(ProbeSettingsWorker, self).__init__()
        self.HP = HP
        self.signals = WorkerSignals()  # can send signals to main GUI

    def run(self):
        """Task to read probe settings and emit signal"""
        try:
            range = self.HP.get_range()  # query current measurement range
            sample_rate = "{:.0f}".format(self.HP.get_sample_rate())
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:  # if no exceptions

            if self.HP.type() == '3MH6':
                if range[0:6] == 'mrng:2':  # if range 2
                    range_string = 'Measurement Range = 500 mT'
                elif range[0:6] == 'mrng:3':  # if range 3
                    range_string = 'Measurement Range = 2 T'
                else:  # if not range 2 or 3
                    range_string = 'Measurement Range = ?'

            elif self.HP.type() == '3MTS':
                print('3mts probe')
                range_list = ['100 mT', '500 mT', '3 T', '20 T']
                print('range = ', range)
                range_string = 'Measurement Range = ' + range_list[range]

            elif self.HP.type() == '3MH3':
                print('3MH3 teslameter')
                range_list = ['2 T']
                print('range = ', range)
                range_string = 'Measurement Range = ' + range_list[range]

            # Emit signal
            self.signals.result.emit([range_string, sample_rate])  # emit fields
        finally:
            self.signals.finished.emit()
