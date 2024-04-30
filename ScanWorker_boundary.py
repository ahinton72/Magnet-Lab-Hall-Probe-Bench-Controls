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


class ScanWorker_boundary(QRunnable):
    """Runnable class to scan over 3D coordinates and record fields - scan point by point"""

    def __init__(self, HP, mc, x0, x1, dx, y0, y1, dy, z0, z1, dz, order, filename, averages):
        super(ScanWorker_boundary, self).__init__()
        mutex.lock()
        self.signals = WorkerSignals()
        self.isRun = True  # isRun flag = true; do not stop action

        self.HP = HP
        self.mc = mc
        self.xa = mc.axis['x']
        self.ya = mc.axis['y']
        self.za = mc.axis['z']
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
        """Function to move Hall probe relative distance and track progress"""
        try:
            print('scan worker running ', datetime.datetime.now())
            x_lims = self.xa.getLimits()
            y_lims = self.ya.getLimits()
            z_lims = self.za.getLimits()
            x_lower = (x_lims[0])
            x_upper = (x_lims[1])
            y_lower = (y_lims[0])
            y_upper = (y_lims[1])
            z_lower = (z_lims[0])
            z_upper = (z_lims[1])
            print('limits found ', datetime.datetime.now())
            # Check movement is in soft limit range and raise exception if not
            if self.x0 < x_lower or self.x1 > x_upper:
                print('oh no outside soft limits')
                raise Exception

            if self.y0 < y_lower or self.y1 > y_upper:
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

            # Establish list of coordinate values
            def raster(x0, x1, dx, y0, y1, dy, z):
                """Function to raster scan over 2d plane and return list of coordinates"""

                x_np = int(1 + abs(float(x1) - float(x0)) / float(dx))  # number of intervals along x
                x_values = np.linspace(float(x0), float(x1), x_np)  # array of x coordinate values
                y_np = int(1 + abs(float(y1) - float(y0)) / float(dy))  # number of intervals along x
                y_values = np.linspace(float(y0), float(y1), y_np)  # array of x coordinate values

                coordinates = []  # list to store coordinate values in

                for y in y_values:
                    for x in x_values:
                        point = [x, y, z]
                        coordinates.append(point)

                    x_values = np.flip(x_values)  # reverse order of x value for raster scanning

                return coordinates

            def boundary(x0, x1, dx, y0, y1, dy, z):
                """Function to scan over 2d plane boundary and return list of coordinates"""

                x_np = int(1 + abs(float(x1) - float(x0)) / float(dx))  # number of intervals along x
                y_np = int(1 + abs(float(y1) - float(y0)) / float(dy))  # number of intervals along x

                if x1 < x0:
                    dx = -dx
                if y1 < y0:
                    dy = -dy

                coordinates = []  # list to store coordinate values in

                # Line1 (x0, y0) -> (x1-dx, y0)
                x_vals = np.linspace(x0, x1 - dx, x_np - 1)
                for x in x_vals:
                    coordinates.append([x, y0, z])

                # Line2 (x1, y0) -> (x1, y1-dy)
                y_vals = np.linspace(y0, y1 - dy, y_np - 1)
                for y in y_vals:
                    coordinates.append([x1, y, z])

                # Line3 (x1, y1) -> (x0+dx, y1)
                x_vals = np.linspace(x1, x0 + dx, x_np - 1)
                for x in x_vals:
                    coordinates.append([x, y1, z])

                # Line4 (x0, y1) -> (x0, y0+dy)
                y_vals = np.linspace(y1, y0 + dy, y_np - 1)
                for y in y_vals:
                    coordinates.append([x0, y, z])

                return coordinates

            # raster scan in first z plane
            rasterz0 = (raster(self.x0, self.x1, self.dx, self.y0, self.y1, self.dy, self.z0))

            # Determine z coordaintes of planes in main body (where only boundary values scanned)
            z_np = int(1 + abs(float(self.z1) - float(self.z0)) / float(self.dz))  # number of intervals along x
            z_values = np.linspace(float(self.z0), float(self.z1), z_np)  # array of x coordinate values
            z_planes = z_values[1:-1]

            all_points = rasterz0  # list of all coordinates begins with raster can on z0 plane

            y_np = int(1 + abs(float(self.y1) - float(self.y0)) / float(self.dy))

            # Add boundary data around central z planes
            for z in z_planes:
                if y_np % 2 == 0:  # if even number of y_points
                    boundary_vals = boundary(self.x0, self.x1, self.dx, self.y1, self.y0, self.dy, z)
                else:  # if order number of y_points, different starting x coordinate
                    boundary_vals = boundary(self.x1, self.x0, self.dx, self.y1, self.y0, self.dy, z)

                all_points += boundary_vals

            # Finally, add coordinates for raster scan in z1 plane
            if y_np % 2 == 0:  # if even number of y_points
                rasterz1 = raster(self.x0, self.x1, self.dx, self.y1, self.y0, self.dy, self.z1)
            else:
                rasterz1 = raster(self.x1, self.x0, self.dx, self.y1, self.y0, self.dy, self.z1)

            all_points += rasterz1

            self.distance = 0
            count = 0  # number of points measured
            total_count = len(all_points)  # total number of points to scan over

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
                    for point in all_points:  # for each coordinate to be scanned
                        try:
                            self.xa.move(point[0], wait=True)  # move x axis to x coordinate
                            self.ya.move(point[1], wait=True)  # move y axis to y coordinate
                            self.za.move(point[2], wait=True)  # move z axis to z coordinate
                        except ValueError as e:  # if value error due to incorrect response, keep going
                            print('ValueError, Keep going, ', e)

                        time.sleep(0.5)  # wait for motor controllers to settle

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
                            continue
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
