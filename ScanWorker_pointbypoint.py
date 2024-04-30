import PyQt5
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QMutex
import traceback
import sys
import time
import datetime
import numpy as np
import csv
from WorkerSignals import WorkerSignals

mutex = QMutex()


class ScanWorker_pointbypoint(QRunnable):
    """Runnable class to scan over 3D coordinates and record fields - scan point by point"""

    def __init__(self, HP, mc, x0, x1, dx, y0, y1, dy, z0, z1, dz, order, filename, averages):
        super(ScanWorker_pointbypoint, self).__init__()
        mutex.lock()  # lock motor controller and Teslameter classes to this function
        self.signals = WorkerSignals()
        self.isRun = True  # isRun flag = true; do not stop action

        self.HP = HP  # Teslameter class
        self.mc = mc  # motor controller class
        self.xa = mc.axis['x']  # motor controller x axis
        self.ya = mc.axis['y']  # motor controller y axis
        self.za = mc.axis['z']  # motor controller z axis
        self.x0 = float(x0)  # start x
        self.x1 = float(x1)  # end x
        self.dx = float(dx)  # x interval
        self.y0 = float(y0)  # start y
        self.y1 = float(y1)  # end y
        self.dy = float(dy)  # y interval
        self.z0 = float(z0)  # start z
        self.z1 = float(z1)  # end z
        self.dz = float(dz)  # z interval
        self.order = order  # scan order
        self.filename = filename  # filename to save csv to
        self.averages = averages  # number of samples to use in fields average

    def run(self):
        """Function to move Hall probe over 3D volume and track progress"""
        try:
            # Read current soft limits from motor controller axes
            x_lims = self.xa.getLimits()
            y_lims = self.ya.getLimits()
            z_lims = self.za.getLimits()
            x_lower = (x_lims[0])
            x_upper = (x_lims[1])
            y_lower = (y_lims[0])
            y_upper = (y_lims[1])
            z_lower = (z_lims[0])
            z_upper = (z_lims[1])
            # Check movement is in soft limit range and raise exception if not
            if self.x0 < x_lower or self.x1 > x_upper:
                raise Exception

            if self.y0 < y_lower or self.y1 > y_upper:
                raise Exception

            if self.z1 < z_lower or self.z1 > z_upper:
                raise Exception

        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))  # send error signal to main GUI
        else:  # if no exceptions - run point by point scan
            x_np = int(1 + abs(float(self.x1) - float(self.x0)) / float(self.dx))  # number of intervals along x
            x_values = np.linspace(float(self.x0), float(self.x1), x_np)  # array of x coordinate values
            y_np = int(1 + abs(float(self.y1) - float(self.y0)) / float(self.dy))  # number of intervals along x
            y_values = np.linspace(float(self.y0), float(self.y1), y_np)  # array of x coordinate values
            z_np = int(1 + abs(float(self.z1) - float(self.z0)) / float(self.dz))  # number of intervals along x
            z_values = np.linspace(float(self.z0), float(self.z1), z_np)  # array of x coordinate values

            motors = []  # list to store motor objects in
            positions = []  # list to store position coordinates in

            # Set order to scan coordinates in
            orders = {
                0: ([self.za, self.xa, self.ya], [z_values, x_values, y_values]),
                1: ([self.za, self.ya, self.xa], [z_values, y_values, x_values]),
                2: ([self.xa, self.ya, self.za], [x_values, y_values, z_values]),
                3: ([self.xa, self.za, self.ya], [x_values, z_values, y_values]),
                4: ([self.ya, self.za, self.xa], [y_values, z_values, x_values]),
                5: ([self.ya, self.xa, self.za], [y_values, x_values, z_values])
            }

            motors, positions = orders[self.order]

            self.distance = 0  # normalised distance value used to calculate % completion for progress bar
            count = 0  # number of points measured
            total_count = len(x_values) * len(y_values) * len(z_values)  # total number of points to measure

            header_list = ['Time', 'x / mm', 'y / mm', 'z / mm', 'bx / mT', 'by / mT', 'bz / mT', 'std(bx) / mT',
                           'std(by) / mT',
                           'std(bz) / mT', 'T / C',
                           'std(T) / C']

            with open(self.filename, "w", newline='') as f:  # open csv file to write data to at each point
                dw = csv.DictWriter(f, delimiter=',',
                                    fieldnames=header_list)
                dw.writeheader()
                writer = csv.writer(f, delimiter=",")

                while self.distance < 100:
                    for i in range(len(positions[2])):  # for each point along 3rd axis
                        motors[2].move(positions[2][i], wait=True)  # move motor axis 3, wait until reach position
                        for j in range(len(positions[1])):  # for each point along 2nd axis
                            motors[1].move(positions[1][j], wait=True)  # move motor 2, wait til reach position
                            for k in range(len(positions[0])):  # for each point along axis 1
                                try:
                                    motors[0].move(positions[0][k], wait=True,
                                                   tolerance=1E-3)  # move motor 1, wait til reach position
                                except ValueError as e:
                                    print('ValueError, Keep going, ', e)

                                time.sleep(0.5)  # wait for motor controllers to settle before reading fields

                                # Read actual motor controller positions
                                x = self.xa.get_position()
                                y = self.ya.get_position()
                                z = self.za.get_position()

                                # Take field measurements
                                fields = self.HP.get_fields(
                                    self.averages)  # get fields averaged from n samples from Tesla-meter

                                # Write position and field measurements to csv file
                                writer.writerow(
                                    [str(datetime.datetime.now()), "{:.3f}".format(x), "{:.3f}".format(y),
                                     "{:.3f}".format(z), fields[0], fields[1], fields[2], fields[3], fields[4],
                                     fields[5],
                                     fields[6], fields[7]])
                                print('Position = ', x, y, z)
                                print('Fields = ', fields[0], fields[1], fields[2])

                                # Format fields and temperatures to export to GUI
                                bx = "{:.3f}".format(fields[0])
                                by = "{:.3f}".format(fields[1])
                                bz = "{:.3f}".format(fields[2])
                                temp = "{:.3f}".format(fields[6])

                                # emit positions and fields to update GUI
                                self.signals.result.emit(
                                    ["{:.3f}".format(x), "{:.3f}".format(y), "{:.3f}".format(z), bx, by, bz,
                                     temp])

                                # Update step count and emit signal to update GUI progress bar
                                count += 1
                                self.distance = int(
                                    100 * (count / total_count))  # increase dummy variable to the nearest integer value
                                self.signals.progress.emit(self.distance - 1)
                                time.sleep(0.1)

                                if not self.isRun:  # check if STOP button pressed
                                    # Send STOP command to motor axes
                                    self.xa.stop()
                                    self.ya.stop()
                                    self.za.stop()
                                    break  # break out of axis 1 loop
                            else:
                                positions[0] = np.flip(
                                    positions[0])  # reverse order of axis 1 to reduce total scan time (raster scan)
                                continue
                            break  # break out of axis 2 values loop if stop button pressed
                        else:
                            positions[1] = np.flip(positions[1])  # reverse order of axis 2 to reduce total scan time
                            continue
                        break  # break out of axis 3 value loop if stop button pressed
                    else:
                        continue
                    break  # break out of while loop and end the scan if stop button pressed

        finally:
            # emit finished signal to GUI
            self.signals.finished.emit()
            mutex.unlock()  # unlock the motor controller and teslameter classes
