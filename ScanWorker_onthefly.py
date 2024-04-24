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


def arange(start, stop=None, step=1.0):
    """Use numpy's arange with a slightly higher stop value to ensure the specified stop value is included.
    If no stop value is specified, just return a length-1 array containing only the start value."""
    if stop is not None:
        step = np.copysign(step, stop - start)
    return np.array([start]) if stop is None else np.arange(start, stop + np.copysign(0.002, stop - start), step)


class MissedTriggerError(Exception):
    """Raise when a trigger has been missed (by moving too fast)."""


class ScanWorker_onthefly(QRunnable):
    """Runnable class to scan over 3D coordinates and record fields - scan axis 1 on the fly"""

    def __init__(self, HP, mc, x0, x1, dx, y0, y1, dy, z0, z1, dz, order, filename, averages, scan_speed):
        super(ScanWorker_onthefly, self).__init__()
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
        self.scan_speed = scan_speed # speed selected by user to perform scan

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

            x_np = int(1 + abs(float(self.x1) - float(self.x0)) / float(self.dx))  # number of intervals along x
            x_values = np.linspace(float(self.x0), float(self.x1), x_np)  # array of x coordinate values
            y_np = int(1 + abs(float(self.y1) - float(self.y0)) / float(self.dy))  # number of intervals along x
            y_values = np.linspace(float(self.y0), float(self.y1), y_np)  # array of x coordinate values
            z_np = int(1 + abs(float(self.z1) - float(self.z0)) / float(self.dz))  # number of intervals along x
            z_values = np.linspace(float(self.z0), float(self.z1), z_np)  # array of x coordinate values

            motors = []  # list to store motor objects in
            positions = []  # list to store position coordinates in

            # Set order to scan coordinates in
            # 0=zxy, 1=zyx, 2=xyz, 3=xzy, 4=yzx, 5=yxz
            # Scan u,v,w arrays
            if self.order == 0:  # zxy
                motors = [self.za, self.xa, self.ya]
                positions = [z_values, x_values, y_values]
            elif self.order == 1:  # zyx
                motors = [self.za, self.ya, self.xa]
                positions = [z_values, y_values, x_values]
            elif self.order == 2:  # xyz
                motors = [self.xa, self.ya, self.za]
                positions = [x_values, y_values, z_values]
            elif self.order == 3:  # xzy
                motors = [self.xa, self.za, self.ya]
                positions = [x_values, z_values, y_values]
            elif self.order == 4:  # yzx
                motors = [self.ya, self.za, self.xa]
                positions = [y_values, z_values, x_values]
            elif self.order == 5:  # yxz
                motors = [self.ya, self.xa, self.za]
                positions = [y_values, x_values, z_values]

            self.distance = 0
            count = 0  # number of points measured
            total_count = len(x_values) * len(y_values) * len(z_values)

            header_list = ['Time', 'x / mm', 'y / mm', 'z / mm', 'bx / mT', 'by / mT', 'bz / mT', 'std(bx) / mT',
                           'std(by) / mT',
                           'std(bz) / mT', 'T / C',
                           'std(T) / C']

            # Initialise write port output settings
            on_time = 20  # pulse on time / ms
            port = 1
            step = positions[0][1] - positions[0][0]
            print('write port modulus step = ', step)
            motors[0].initialiseTrigger(0, step, on_time, port)

            # Calculate reasonable timeout for wait for pulse function
            timeout = abs(10*(step/float(self.scan_speed)))  # timeout = 10 times expected time between pulses
            print('timeout = ', timeout)

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

                            start = positions[0][0]  # start of on the fly scan
                            stop = positions[0][-1]  # end of on the fly scan

                            print('Move to start')
                            motors[0].move(start, wait=True, tolerance=0.005, timeout=3600)

                            time.sleep(1)  # wait 1 second

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
                                 "{:.3f}".format(z), fields[0], fields[1], fields[2], fields[3], fields[4], fields[5],
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

                            direction_sign = np.copysign(1, stop - start)

                            speed0 = motors[0].getSpeed() # current speed of motor before scan
                            print('current speed = ', speed0)
                            print('setting speed to ', self.scan_speed)

                            motors[0].setSpeed(float(self.scan_speed))

                            print('Moving to:', stop)
                            motors[0].move(
                                stop + direction_sign * 0.1)  # move a tiny bit further so we definitely hit the last trigger point

                            time.sleep(0.05)  # short sleep so first trigger is not at start point

                            for k, pos in enumerate(positions[0][1:]):  # for each position in array, wait for trigger, measure fields
                                trigger_at = pos
                                pos_now = motors[0].get_position()
                                print(f'Waiting for position {trigger_at}, now at {pos_now}')
                                try:
                                    if np.copysign(1,
                                                   trigger_at - pos_now) != direction_sign:  # already passed the trigger!
                                        raise MissedTriggerError(
                                            f'Missed trigger at {trigger_at}, already at {pos_now}')
                                except MissedTriggerError:
                                    print('oh no, missed trigger!')
                                    self.isRun = False  # stop scan
                                    self.signals.error.emit(
                                        ("MissedTrigger", "MissedTrigger",
                                         traceback.format_exc()))  # raise warning to user
                                    writer.writerow(['Missed Trigger'])  # write line in csv file

                                try:
                                    motors[0].waitforPulse(port, timeout)
                                except TimeoutError:
                                    print('oh no, timed out waiting for trigger!')
                                    self.isRun = False  # stop scan
                                    self.signals.error.emit(
                                        ("Timeout", "Timeout",
                                         traceback.format_exc()))  # raise warning to user
                                    writer.writerow(['Timeout Waiting for Trigger'])  # write line in csv file

                                fields = self.HP.get_fields(
                                    self.averages)  # get fields averaged from n samples from Tesla-meter

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

                                    time.sleep(1) # sleep for a second to let axes settle

                                    break  # break out of loop

                                current_cmd_positions = positions[0][k + 1], positions[1][j], positions[2][
                                    i]  # current command positions

                                if self.order == 0:
                                    z, x, y = current_cmd_positions
                                elif self.order == 1:
                                    z, y, x = current_cmd_positions
                                elif self.order == 2:
                                    x, y, z = current_cmd_positions
                                elif self.order == 3:
                                    x, z, y = current_cmd_positions
                                elif self.order == 4:
                                    y, z, x = current_cmd_positions
                                elif self.order == 5:
                                    y, x, z = current_cmd_positions

                                # Write positions measurements to csv file
                                writer.writerow(
                                    [str(datetime.datetime.now()), "{:.3f}".format(x), "{:.3f}".format(y),
                                     "{:.3f}".format(z), fields[0], fields[1], fields[2], fields[3], fields[4],
                                     fields[5],
                                     fields[6], fields[7]])

                            else:
                                print('line scan successful')
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

            try:
                print('resetting speed to ', speed0)
                motors[0].setSpeed(speed0)
                print('speed reset')
            except:
                print('error resetting speed')

        finally:
            print('emit finished signal')
            self.signals.finished.emit()
            print('finish signal emitted')
            mutex.unlock()
