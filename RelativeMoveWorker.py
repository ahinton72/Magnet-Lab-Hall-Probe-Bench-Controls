import PyQt5
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QMutex
import traceback
import sys
import datetime
from WorkerSignals import WorkerSignals
mutex = QMutex()

class RelativeMoveWorker(QRunnable):
    def __init__(self, mc, x, y, z):
        super(RelativeMoveWorker, self).__init__()
        print('Move called ', datetime.datetime.now())
        self.signals = WorkerSignals()
        self.isRun = True  # isRun flag = true; do not stop action

        self.mc = mc
        self.xa = mc.axis['x'] # x axis on SW stage 2
        self.ya = mc.axis['y'] # y axis on SW stage 2
        self.za = mc.axis['z'] # z axis on SW stage 2
        self.x = x  # x distance to travel
        self.y = y  # y distance to travel
        self.z = z  # z_distance to travel
        print('Moving, ', self.x, self.y, self.z)
        print('initialised', datetime.datetime.now())

    def run(self):
        """Function to move Hall probe relative distance and track progress"""
        print('running', datetime.datetime.now())
        try:
            print('get positions', datetime.datetime.now())
            x0 = self.xa.get_position()  # get starting x position
            y0 = self.ya.get_position()  # get starting y position
            z0 = self.za.get_position()  # get starting z position

            total_distance = abs(float(self.x)) + abs(float(self.y)) + abs(
                float(self.z))  # total distance for probe to travel
            # total_distance = 0

            # Move motors
            self.xa.move(float(self.x), relative=True)
            self.ya.move(float(self.y), relative=True)
            self.za.move(float(self.z), relative=True)

        except: # if Value error raised by soft limits exception
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))

        else:  # if no exceptions
            print('no errors')

            self.distance = 0  # dummy variable, starts at 0

            if total_distance == 0:  # if total move distance = 0, skip loop
                self.distance = 100
                self.signals.progress.emit(self.distance - 1)

            while self.distance < 100:  # while total distance travelled less than 100%

                if not self.isRun:  # check if STOP button pressed
                    print('Movement cancelled!')  # print to console
                    # Send STOP command to motor
                    self.xa.stop()
                    self.ya.stop()
                    self.za.stop()
                    print('Movement stopped')
                    break  # break out of loop

                if self.xa.hardLimits():  # check if x axis at Hard limit
                    print('x axis at Hard limit!')
                    self.signals.error.emit((None, None, traceback.format_exc()))  # raise warning to user
                    break  # break out of loop
                elif self.ya.hardLimits():  # check if y axis at hard limit
                    print('y axis at Hard limit!')
                    self.signals.error.emit((None, None, traceback.format_exc()))  # raise warning to user
                    break  # break out of loop
                elif self.za.hardLimits():
                    print('z axis at Hard limit!')
                    self.signals.error.emit((None, None, traceback.format_exc()))  # raise warning to user
                    break  # break out of loop

                # Determine distances travelled in x, y, z
                current_x_position = self.xa.get_position()
                x_distance_travelled = abs(current_x_position - x0)
                current_y_position = self.ya.get_position()
                y_distance_travelled = abs(current_y_position - y0)
                current_z_position = self.za.get_position()
                z_distance_travelled = abs(current_z_position - z0)

                self.signals.result.emit(["{:.3f}".format(current_x_position), "{:.3f}".format(current_y_position), "{:.3f}".format(current_z_position)])

                # Determine distance travelled as fraction of total distance to travel
                self.distance = int(
                    100 * (x_distance_travelled + y_distance_travelled + z_distance_travelled) / total_distance)
                print('progress=', self.distance)

                self.signals.progress.emit(self.distance)  # send progress signal to GUI

                # Set progress bar to 100% when current probe readings are as expected
                tolerance = 0.1  # tolerance on expected vs desired final position
                if abs(self.xa.get_position() - (x0 + float(self.x))) < tolerance and abs(
                        self.ya.get_position() - (y0 + float(self.y))) < tolerance and abs(
                    self.za.get_position() - (z0 + float(self.z))) < tolerance:
                    self.distance = 100
                    print('set progress bar to 100')
                    self.signals.progress.emit(
                        self.distance - 1)  # Finally, set progress bar value to target maximum'''
                    current_x_position = self.xa.get_position()
                    current_y_position = self.ya.get_position()
                    current_z_position = self.za.get_position()
                    self.signals.result.emit(["{:.3f}".format(current_x_position), "{:.3f}".format(current_y_position),
                                              "{:.3f}".format(current_z_position)])

        finally:
            print('emit finished signal')
            self.signals.finished.emit()
            print('finish signal emitted', datetime.datetime.now())