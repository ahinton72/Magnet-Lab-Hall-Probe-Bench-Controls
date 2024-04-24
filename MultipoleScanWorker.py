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


class MultipoleScanWorker(QRunnable):
    """Runnable class to scan over 3D coordinates and record fields"""

    def __init__(self, HP, mc, x0, y0, r0, steps, z0, z1, dz, filename, averages):
        super(MultipoleScanWorker, self).__init__()
        mutex.lock()
        self.signals = WorkerSignals()
        self.isRun = True  # isRun flag = true; do not stop action

        self.HP = HP
        self.mc = mc
        self.xa = mc.axis['x']
        self.ya = mc.axis['y']
        self.za = mc.axis['z']
        self.x0 = float(x0)  # x centre of circle
        self.y0 = float(y0)  # y centre of circle
        self.r0 = r0  # radius of circle
        self.steps = steps  # number of steps around circle
        self.z0 = float(z0)  # start z
        self.z1 = float(z1)  # end z
        self.dz = float(dz)  # z interval
        self.filename = filename  # filename to save csv to
        self.averages = averages  # number of samples to use in fields average

        print('scan worker initialised')

    def run(self):
        """Function to move Hall probe relative distance and track progress"""
        try:
            print('scan worker running')
            x_lims = self.xa.getLimits()
            y_lims = self.ya.getLimits()
            z_lims = self.za.getLimits()
            x_lower = (x_lims[0])
            x_upper = (x_lims[1])
            y_lower = (y_lims[0])
            y_upper = (y_lims[1])
            z_lower = (z_lims[0])
            z_upper = (z_lims[1])
            print('limits found')
            # Check movement is in soft limit range and raise exception if not
            if self.x0 - self.r0 < x_lower or self.x0 + self.r0 > x_upper:
                print('oh no outside soft limits')
                raise Exception

            if self.y0 - self.r0 < y_lower or self.y0 + self.r0 > y_upper:
                print('oh no outside soft limits')
                raise Exception

            if self.z1 < z_lower or self.z1 > z_upper:
                print('oh no outside soft limits')
                raise Exception

        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:  # if no exceptions
            print('starting scan')

            theta_values = np.linspace(0, 2 * np.pi, int(self.steps), endpoint=False)  # values of theta

            z_np = int(1 + abs(float(self.z1) - float(self.z0)) / float(self.dz))  # number of intervals along x

            print('z0, z1, dz, np = ', self.z0, self.z1, self.dz, z_np)

            z_values = np.linspace(float(self.z0), float(self.z1), z_np)  # array of x coordinate values

            print('z values = ', z_values)

            self.distance = 0
            count = 0  # number of points measured
            total_count = len(theta_values) * len(z_values)

            header_list = ['Time', 'theta / rad', 'x / mm', 'y / mm', 'z / mm', 'bx / mT', 'by / mT', 'bz / mT',
                           'std(bx) / mT',
                           'std(by) / mT',
                           'std(bz) / mT', 'T / C',
                           'std(T) / C']

            with open(self.filename, "w", newline='') as f:  # write data to csv file
                dw = csv.DictWriter(f, delimiter=',',
                                    fieldnames=header_list)
                dw.writeheader()
                writer = csv.writer(f, delimiter=",")

                while self.distance < 100:
                    for i in range(len(z_values)):
                        print('Move to z coordinate')
                        self.za.move(z_values[i], wait=True)
                        for j in range(len(theta_values)):
                            print('Move to angular position!')

                            x_pos = round(self.x0 + self.r0 * np.cos(theta_values[j]), 3)  # new x coordinate to 3 d.p.
                            y_pos = round(self.y0 + self.r0 * np.sin(theta_values[j]), 3)  # new y coordinate to 3 d.p.

                            print('x pos = ', x_pos)
                            print('y pos = ', y_pos)

                            if 0 < theta_values[j] < np.pi / 2 or np.pi < theta_values[j] < 3 * np.pi / 2:
                                self.xa.move(x_pos, wait=True)  # move x axis, wait til reach position
                                self.ya.move(y_pos, wait=True)  # move y axis, wait til reach position
                            else:
                                self.ya.move(y_pos, wait=True)  # move y axis, wait til reach position
                                self.xa.move(x_pos, wait=True)  # move x axis, wait til reach position

                            print('read the positions')
                            # Read motor controller positions
                            x = self.xa.get_position()
                            y = self.ya.get_position()
                            z = self.za.get_position()

                            print('positions read - get the fields')

                            # Take field measurements
                            fields = self.HP.get_fields(
                                self.averages)  # get fields averaged from n samples from Tesla-meter

                            print('got the fields - write to csv')

                            # Write positions measurements to csv file
                            writer.writerow(
                                [datetime.datetime.now(), "{:.3f}".format(theta_values[j]), "{:.3f}".format(x),
                                 "{:.3f}".format(y), "{:.3f}".format(z), fields[0], fields[1], fields[2], fields[3],
                                 fields[4], fields[5],
                                 fields[6], fields[7]])
                            print('Position = ', x, y, z)
                            print('Fields = ', fields[0], fields[1], fields[2])

                            bx = "{:.3f}".format(fields[0])
                            by = "{:.3f}".format(fields[1])
                            bz = "{:.3f}".format(fields[2])
                            temp = "{:.3f}".format(fields[6])

                            self.signals.result.emit(
                                ["{:.3f}".format(x), "{:.3f}".format(y), "{:.3f}".format(z), bx, by, bz,
                                 temp])  # emit positions and fields to update GUI

                            print('positions and fields emitted')

                            count += 1
                            self.distance = int(
                                100 * (count / total_count))  # increase dummy variable to the nearest integer value
                            self.signals.progress.emit(self.distance - 1)
                            time.sleep(0.1)

                            if not self.isRun:  # check if STOP button pressed
                                print('Scan cancelled!')  # print to console
                                # Send STOP command to motor
                                self.xa.stop()
                                self.ya.stop()
                                self.za.stop()
                                break  # break out of loop
                        else:
                            continue
                        break  # break out of w value loop if stop button pressed
                    else:
                        continue
                    break  # break out of while loop

            # Emit signal
            print('no errors')
        finally:
            print('emit finished signal')
            self.signals.finished.emit()
            print('finish signal emitted')
            mutex.unlock()
