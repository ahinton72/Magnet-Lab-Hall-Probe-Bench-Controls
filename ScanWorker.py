import numpy as np
import csv
import PyQt5
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QMutex
import traceback
import sys
import time
import datetime
from WorkerSignals import WorkerSignals

mutex = QMutex()  # imported so that Teslameter and motor controller classes only accessed by this function


class ScanWorker(QRunnable):
    """Runnable class to scan over 3D coordinate volume and record fields in csv folder"""

    def __init__(self, HP, mc, x0, x1, dx, y0, y1, dy, z0, z1, dz, order, filename, averages):
        super(ScanWorker, self).__init__()
        mutex.lock()
        self.signals = WorkerSignals()
        self.isRun = True  # isRun flag = true; do not stop action

        self.HP = HP  # set Teslameter class
        self.mc = mc
        self.xa = mc.axis['x']  # define motor controller x axis
        self.ya = mc.axis['y']  # define motor controller y axis
        self.za = mc.axis['z']  # define motor controller z axis
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

        print('scan worker initialised ', datetime.datetime.now())

    def run(self):
        """Function to move Hall probe over 3D volume and track progress"""
        try:  # check if entered measurement volume is within motor controller soft limits
            x_lims = self.xa.getLimits()
            y_lims = self.ya.getLimits()
            z_lims = self.za.getLimits()
            x_lower = (x_lims[0])
            x_upper = (x_lims[1])
            y_lower = (y_lims[0])
            y_upper = (y_lims[1])
            z_lower = (z_lims[0])
            z_upper = (z_lims[1])

            # raise exception if volume outside of soft limits
            if self.x0 < x_lower or self.x1 > x_upper:
                raise Exception

            if self.y0 < y_lower or self.y1 > y_upper:
                raise Exception

            if self.z0 < z_lower or self.z1 > z_upper:
                raise Exception

        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:  # if no exceptions
            print('starting scan')

            x_np = int(1 + abs(float(self.x1) - float(self.x0)) / float(self.dx))  # number of intervals along x
            x_values = np.linspace(float(self.x0), float(self.x1), x_np)  # array of x coordinate values
            y_np = int(1 + abs(float(self.y1) - float(self.y0)) / float(self.dy))  # number of intervals along x
            y_values = np.linspace(float(self.y0), float(self.y1), y_np)  # array of x coordinate values
            z_np = int(1 + abs(float(self.z1) - float(self.z0)) / float(self.dz))  # number of intervals along x
            z_values = np.linspace(float(self.z0), float(self.z1), z_np)  # array of x coordinate values

            motors = []  # list to store motor objects in
            positions = []  # list to store position coordinates in

            # Set order to scan coordinates in
            # 0=xyz, 1=xzy, 2=yzx, 3=yxz, 4=zxy, 5=zyx
            # Scan u,v,w arrays
            if self.order == 0:  # xyz
                motors = [self.xa, self.ya, self.za]
                positions = [x_values, y_values, z_values]
            elif self.order == 1:  # xzy
                motors = [self.xa, self.za, self.ya]
                positions = [x_values, z_values, y_values]
            elif self.order == 2:  # yzx
                motors = [self.za, self.ya, self.xa]
                positions = [z_values, y_values, x_values]
            elif self.order == 3:  # yxz
                motors = [self.ya, self.xa, self.za]
                positions = [y_values, x_values, z_values]
            elif self.order == 4:  # zxy
                motors = [self.za, self.xa, self.ya]
                positions = [z_values, x_values, y_values]
            elif self.order == 5:  # zyx
                motors = [self.za, self.ya, self.xa]
                positions = [z_values, y_values, x_values]

            self.distance = 0
            count = 0  # number of points measured
            total_count = len(x_values) * len(y_values) * len(z_values)

            header_list = ['Time', 'x / mm', 'y / mm', 'z / mm', 'bx / mT', 'by / mT', 'bz / mT', 'std(bx) / mT',
                           'std(by) / mT',
                           'std(bz) / mT', 'T / C',
                           'std(T) / C']

            with open(self.filename, "w", newline='') as f:  # write data to csv file
                dw = csv.DictWriter(f, delimiter=',',
                                    fieldnames=header_list)
                dw.writeheader()
                writer = csv.writer(f, delimiter=",")

                while self.distance < 100:
                    for i in range(len(positions[2])):
                        print('Move motor 3!')
                        motors[2].move(positions[2][i], wait=True)
                        for j in range(len(positions[1])):
                            print('Move motor 2!')
                            motors[1].move(positions[1][j], wait=True)  # move motor 2, wait til reach position
                            for k in range(len(positions[0])):
                                print('Move motor 1!')
                                print('position = ', positions[0][k])
                                try:
                                    motors[0].move(positions[0][k], wait=True)  # move motor 1, wait til reach position
                                except ValueError as e:
                                    print('ValueError, Keep going, ', e)

                                time.sleep(0.1)  # wait for motor controllers to settle

                                print('read the positions ', datetime.datetime.now())
                                # Read motor controller positions
                                x = self.xa.get_position()
                                y = self.ya.get_position()
                                z = self.za.get_position()

                                print('positions read - get the fields', datetime.datetime.now())

                                # Take field measurements
                                fields = self.HP.get_fields(
                                    self.averages)  # get fields averaged from n samples from Tesla-meter

                                print('got the fields - write to csv ', datetime.datetime.now())

                                # Write positions measurements to csv file
                                writer.writerow(
                                    [str(datetime.datetime.now()), "{:.3f}".format(x), "{:.3f}".format(y),
                                     "{:.3f}".format(z), fields[0], fields[1], fields[2], fields[3], fields[4],
                                     fields[5],
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

                                print('positions and fields emitted ', datetime.datetime.now())

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
                                positions[0] = np.flip(
                                    positions[0])  # reverse order of axis 1 to reduce total scan time
                                continue
                            break  # break out of v values loop if stop button pressed
                        else:
                            positions[1] = np.flip(positions[1])  # reverse order of axis 2 to reduce total scan time
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
