import PyQt5
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QMutex
import traceback
import sys
import datetime
from WorkerSignals import WorkerSignals
mutex = QMutex()

class GlobalMoveWorker(QRunnable):
    """Runnable class to move motors to global position"""

    def __init__(self, mc, x1, y1, z1):
        super(GlobalMoveWorker, self).__init__()
        self.signals = WorkerSignals()
        self.isRun = True  # isRun flag = true; do not stop action

        self.mc = mc
        self.xa = mc.axis['x'] # x axis on stretched wire stage 2
        self.ya = mc.axis['y'] # y axis on stretched wire stage 2
        self.za = mc.axis['z'] # z axis on stretched wire stage 2
        self.x1 = float(x1)  # x distance to travel
        self.y1 = float(y1)  # y distance to travel
        self.z1 = float(z1)  # z_distance to travel
        print('Moving to, ', self.x1, self.y1, self.z1)

    def run(self):
        """Function to move Hall probe relative distance and track progress"""
        try:
            x0 = self.xa.get_position()  # get starting x position
            y0 = self.ya.get_position()  # get starting y position
            z0 = self.za.get_position()  # get starting z position

            total_distance = abs(float(self.x1) - x0) + abs(float(self.y1) - y0) + abs(
                float(self.z1) - z0)  # total distance for probe to travel

            self.xa.move(float(self.x1), relative=False)
            self.ya.move(float(self.y1), relative=False)
            self.za.move(float(self.z1), relative=False)

        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:  # if no exceptions
            # Emit signal
            print('no errors')

            self.distance = 0  # dummy variable, starts at 0

            while self.distance < 100:  # while total distance travelled less than 100%

                if not self.isRun:  # check if STOP button pressed
                    print('Movement cancelled!')  # print to console
                    # Send STOP command to motor
                    self.xa.stop()
                    self.ya.stop()
                    self.za.stop()
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
                if abs(self.xa.get_position() - (float(self.x1))) < tolerance and abs(
                        self.ya.get_position() - (float(self.y1))) < tolerance and abs(
                        self.za.get_position() - (float(self.z1))) < tolerance:
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
            print('finish signal emitted')