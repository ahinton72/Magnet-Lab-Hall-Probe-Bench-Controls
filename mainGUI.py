from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QMutex, QCoreApplication, \
    QEvent
from PyQt5.QtWidgets import QFileDialog


from HP_bench_GUI import Ui_MainWindow  # import MainWindow created from designer and exported to .py file
from teslameter_select_GUI import Ui_SelectionWindow  # import Mainwindow for selecting probe type
from teslameter_3MH6 import teslameter_3MH6  # import 3MH6 Teslameter class to read field
from teslameter_3MTS import teslameter_3MTS  # import teslameter 3MTS class
from teslameter_3MH3 import teslameter_3MH3  # import teslameter 3MH3 class
from teslameter_blank import teslameter_blank  # import blank teslameter class
import motor_controller_PM1000
import traceback, sys
import numpy as np
import csv
import time
import re
import datetime
import serial

import pyqtgraph as pg
from random import randint

mutex = QMutex
from os.path import exists
from FieldsWorker import FieldsWorker
from PositionsWorker import PositionsWorker
from RelativeMoveWorker import RelativeMoveWorker
from GlobalMoveWorker import GlobalMoveWorker
from ScanWorker import ScanWorker
from ScanWorker_pointbypoint import ScanWorker_pointbypoint
from ScanWorker_onthefly import ScanWorker_onthefly
from ScanWorker_boundary import ScanWorker_boundary
from ScanWorker_random_sample import ScanWorker_random_sample
from MultipoleScanWorker import MultipoleScanWorker
from ProbeSettingsWorker import ProbeSettingsWorker
from setProbeSettingsWorker import setProbeSettingsWorker
from MotorSettingsWorker import MotorSettingsWorker
from setMotorSettingsWorker import setMotorSettingsWorker
from ResetAxesWorker import ResetAxesWorker

# HP = teslameter_3MH6('COM3')  # create Hall probe class and open serial port
# HP = teslameter_3MTS()
# HP = teslameter_blank()


mc = motor_controller_PM1000.MotorController()
xa = mc.axis['x']  # x axis on Hall probe bench
ya = mc.axis['y']
za = mc.axis['z']


class mywindow(QtWidgets.QMainWindow):
    def __init__(self, HP):
        print('Open main window')
        super(mywindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.HP = HP
        self.HP.open()  # open connection to probe

        self.ui.label_23.setText('Magnet Lab Controls - Hall Probe v7.3')

        self.ui.tabWidget.tabBarClicked.connect(self.sleepGUI)  # sleep GUI

        # Infinite Loop for continuously updating probe position and field measurements
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(False)
        self.timer.setInterval(100)  # in milliseconds, so 5000 = 5 seconds
        # self.timer.timeout.connect(self.update_current_measurements)
        if self.HP.type() != 'blank':
            self.timer.timeout.connect(self.ReadFields)  # connect timer to read fields function
        self.timer.timeout.connect(self.ReadPositions)  # connect timer to read positions function
        self.timer.start()

        # Second timer for updating settings
        self.timer2 = QtCore.QTimer(self)
        self.timer2.setSingleShot(False)
        self.timer2.setInterval(5000)  # in milliseconds, so 5000 = 5 seconds
        if self.HP.type() != 'blank':
            self.timer2.timeout.connect(self.ReadProbeSettings)  # connect timer to read probe settings function
        # self.timer2.timeout.connect(self.ReadMotorSettings)  ###Connect timer to read motor settings function
        # self.timer2.timeout.connect(self.ReadPositions)
        self.timer2.start()

        # Connect Radio buttons on movement tab to MovementRadio function
        self.ui.relativeRadio.toggled.connect(self.movement_radio)  # connect relative movement radio button to function
        self.ui.globalRadio.toggled.connect(self.movement_radio)  # connect global movement radio button to function
        self.ui.relativeRadio.toggled.connect(self.sleepGUI)  # connect relative movement radio button to sleep function
        self.ui.globalRadio.toggled.connect(self.sleepGUI)

        # Connect fixed point radio buttons on scan tab to the functions to block out line edits
        self.ui.xplaneRadio.toggled.connect(self.fixed_x_radio)
        self.ui.yplaneRadio.toggled.connect(self.fixed_y_radio)
        self.ui.zplaneRadio.toggled.connect(self.fixed_z_radio)
        self.ui.xplaneRadio.toggled.connect(self.sleepGUI)
        self.ui.yplaneRadio.toggled.connect(self.sleepGUI)
        self.ui.zplaneRadio.toggled.connect(self.sleepGUI)

        self.ui.on_the_fly_radioButton.toggled.connect(self.onthefly_radio)
        # self.ui.boundary_data_radioButton.toggled.connect(self.sleepGUI)
        self.ui.random_points_checkBox.toggled.connect(self.random_points_check)

        # Connect Push Buttons on Movement Tab to functions to execute movement
        self.ui.relativemoveButton.clicked.connect(
            self.relative_move_click)  # Connect relative move push button to function
        self.ui.globalmoveButton.clicked.connect(self.global_move_click)  # connect global move push button to function
        self.ui.reset_axes_Button.clicked.connect(self.reset_axes_click)

        # Connect select file Push button to file dialog
        self.ui.selectfileButton.clicked.connect(self.select_file_click)

        self.ui.scanorder_Combo.currentIndexChanged.connect(self.sleepGUI)
        self.ui.samplerateCombo.currentIndexChanged.connect(self.sleepGUI)
        self.ui.rangeCombo.currentIndexChanged.connect(self.sleepGUI)

        # Connect Push button on Scan tab to scan function
        self.ui.scanButton.clicked.connect(self.scan_click)
        self.ui.scanButton.clicked.connect(self.sleepGUI)
        self.ui.multipoles_selectfileButton.clicked.connect(self.multipoles_select_file_click)
        self.ui.multipoles_scanButton.clicked.connect(self.multipoles_scan_click)

        # Connect push buttons on multipoles tab
        self.ui.multipoles_z_radio.toggled.connect(self.sleepGUI)
        self.ui.multipoles_z_radio.toggled.connect(self.fixed_multipoles_z_radio)

        # Initialise probe settings page
        if self.HP.type() == '3MH3':
            self.averages = 100
        else:
            self.averages = 1000  # Set default number of field samples per average

        # Determine initial measurement range - probe dependant
        initial_range = self.HP.get_range()  # determine initial range
        if self.HP.type() == '3MH6':
            range_list = ['500 mT', '2 T']  # available ranges for 3MH6 Teslameter
            self.ui.rangeCombo.addItems(range_list)
            if initial_range[0:6] == 'mrng:2':  # if range 2
                self.ui.rangeCombo.setCurrentIndex(0)
            elif initial_range[0:6] == 'mrng:3':  # if range 3
                self.ui.rangeCombo.setCurrentIndex(1)
        elif self.HP.type() == '3MTS':
            range_list = ['100 mT', '500 mT', '3 T', '20 T']  # available ranges for 3MTS Teslameter
            self.ui.rangeCombo.addItems(range_list)
            self.ui.rangeCombo.setCurrentIndex(initial_range)
        elif self.HP.type() == '3MH3':
            range_list = ['2 T']  # available ranges for 3MH3 Teslameter
            self.ui.rangeCombo.addItems(range_list)
            self.ui.rangeCombo.setCurrentIndex(initial_range)

        self.available_rates = self.HP.sample_rates()  # available sample rates
        string_rates = ["{:.0f}".format(i) for i in self.available_rates]  # list where rates are strings
        self.ui.samplerateCombo.addItems(string_rates)  # add string items to combo box
        initial_rate = self.HP.get_sample_rate()
        if initial_rate in self.available_rates:
            index = self.available_rates.index(initial_rate)
            self.ui.samplerateCombo.setCurrentIndex(index)
        self.ui.averagesEdit.setText("{:.0f}".format(self.averages))
        self.ui.probesettingsButton.clicked.connect(self.probe_settings_click)
        if self.HP.type() == 'blank':
            self.ui.probesettingsButton.setEnabled(False)  # no need to update if no probe
        # self.ReadProbeSettings() # read initial probe settings

        print('ok here')

        # Initialise motor settings page
        vx0 = "{:.1f}".format(xa.getSpeed())
        print('still ok')
        self.ui.xspeedEdit.setText(vx0)  # set line edit to current x speed
        self.ui.xspeedLabel.setText(vx0)
        vy0 = "{:.1f}".format(ya.getSpeed())
        self.ui.yspeedEdit.setText(vy0)  # set line edit to current y speed
        self.ui.yspeedLabel.setText(vy0)
        vz0 = "{:.1f}".format(za.getSpeed())
        self.ui.zspeedEdit.setText(vz0)  # set line edit to current z speed
        self.ui.zspeedLabel.setText(vz0)

        # Initialise un-enabled line edits on scan page
        self.ui.scan_speedEdit.setText(vz0)
        self.ui.scan_speedEdit.setEnabled(False)
        self.ui.random_sample_Edit.setEnabled(False)

        # Read starting soft limits
        x_limits = xa.getLimits()
        x_lower = str(x_limits[0])
        self.ui.xlowerEdit.setText(x_lower)
        self.ui.xlowerLabel.setText(x_lower)
        x_upper = str(x_limits[1])
        self.ui.xupperEdit.setText(x_upper)
        self.ui.xupperLabel.setText(x_upper)
        y_limits = ya.getLimits()
        y_lower = str(y_limits[0])
        self.ui.ylowerEdit.setText(y_lower)
        self.ui.ylowerLabel.setText(y_lower)
        y_upper = str(y_limits[1])
        self.ui.yupperEdit.setText(y_upper)
        self.ui.yupperLabel.setText(y_upper)
        z_limits = za.getLimits()
        z_lower = str(z_limits[0])
        self.ui.zlowerEdit.setText(z_lower)
        self.ui.zlowerLabel.setText(z_lower)
        z_upper = str(z_limits[1])
        self.ui.zupperEdit.setText(z_upper)
        self.ui.zupperLabel.setText(z_upper)
        self.max_speeds = [xa.max_speed, ya.max_speed, za.max_speed]
        # Connect push button with function
        self.ui.motorsettingsButton.clicked.connect(self.motor_settings_click)

        # Initialise QThreadPool
        self.pool = QThreadPool.globalInstance()
        print('max thread count before = ', self.pool.maxThreadCount())
        self.pool.setMaxThreadCount(1)
        print('max thread count after = ', self.pool.maxThreadCount())
        print('active threads= ', self.pool.activeThreadCount())
        self.worker = None  # initial global worker
        print('all good so far')

    def sleepGUI(self):
        """Set GUI to sleep for short time after button click to try to avoid crashing"""
        dt = 0.2
        print('sleeping for ', dt)
        self.setEnabled(False)
        time.sleep(dt)
        self.setEnabled(True)

    def create_progress(self, label):
        """Create a progress bar for a function with a given label"""
        # Set window text, stop button text, minimum value, maximum value
        self.progress = QtWidgets.QProgressDialog(label, "STOP", 0, 100, self)
        self.progress.setWindowTitle('Please wait...')
        self.progress.setAutoClose(True)  # Automatically close dialog once progress completed
        self.progress.setWindowModality(
            QtCore.Qt.WindowModal)  # Make window modal so processes can take place in background
        self.progress.canceled.connect(self.progress.close)  # Close dialog when close button pressed
        self.progress.show()  # Show progress dialog

    def track_progess(self, value):
        """Update progress bar to track progress of actions"""
        if self.progress.wasCanceled():  # if cancel button has been pressed on progress bar GUI
            self.worker.isRun = False  # stop current worker from running further by changing Flag value
        else:  # if progress not cancelled
            self.progress.setValue(value - 1)  # set progress bar value
            if value == 99:
                self.progress.setValue(100)  # if thread completed, set progress bar value to 100 to close it

    def check_float(self, values, edits):
        """Function to check values entered into line edits are float type"""
        for i in range(len(edits)):  # for all values in list of line edits
            edits[i].setStyleSheet('background-color: rgb(255, 255, 255);')  # reset line edit colour to white
        try:
            for i in range(len(values)):  # for all values entered
                values[i] = float(values[i])  # check values can be converted to floats
        except ValueError:  # if any entered values are not floats
            warning = QtWidgets.QMessageBox.warning(self, 'Invalid Numbers',
                                                    "Please type valid numbers into the boxes",
                                                    QtWidgets.QMessageBox.Ok)  # Create warning message box to user
        else:  # if no value errors
            return values
        finally:  # after error loop completed, needed because loop stops after encountering first error
            for i in range(len(edits)):  # for all line edits
                try:
                    values[i] = float(values[i])  # check values are numbers
                except ValueError:  # if value is not a number
                    edits[i].setStyleSheet('background-color: rgb(255, 0, 0);')  # set line edit colour to red

    def movement_radio(self):
        """Function to Select correct page of stacked widget for selected movement type"""
        if self.ui.relativeRadio.isChecked():  # if Relative Radio checked
            self.ui.movementStack.setCurrentIndex(0)  # set stacked widget to relative motion page
        else:  # if Global radio checked
            self.ui.movementStack.setCurrentIndex(1)  # set stacked widget to global motion page

    def fixed_x_radio(self):
        """Function to block out line edits if x scan at fixed coordinate"""
        if self.ui.xplaneRadio.isChecked():
            self.ui.scan_x1Edit.setEnabled(False)
            self.ui.scan_dxEdit.setEnabled(False)
        else:
            self.ui.scan_x1Edit.setEnabled(True)
            self.ui.scan_dxEdit.setEnabled(True)

    def fixed_y_radio(self):
        """Function to block out line edits if y scan at fixed coordinate"""
        if self.ui.yplaneRadio.isChecked():
            self.ui.scan_y1Edit.setEnabled(False)
            self.ui.scan_dyEdit.setEnabled(False)
        else:
            self.ui.scan_y1Edit.setEnabled(True)
            self.ui.scan_dyEdit.setEnabled(True)

    def fixed_z_radio(self):
        """Function to block out line edits if z scan at fixed coordinate"""
        if self.ui.zplaneRadio.isChecked():
            self.ui.scan_z1Edit.setEnabled(False)
            self.ui.scan_dzEdit.setEnabled(False)
        else:
            self.ui.scan_z1Edit.setEnabled(True)
            self.ui.scan_dzEdit.setEnabled(True)

    def fixed_multipoles_z_radio(self):
        """Function to block out line edits if multipole scan at fixed z coordinate"""
        if self.ui.multipoles_z_radio.isChecked():
            self.ui.multipoles_z1_Edit.setEnabled(False)
            self.ui.multipoles_dz_Edit.setEnabled(False)
        else:
            self.ui.multipoles_z1_Edit.setEnabled(True)
            self.ui.multipoles_dz_Edit.setEnabled(True)

    def onthefly_radio(self):
        """Function to block out line edits if on-the-fly scan selected"""
        if self.ui.on_the_fly_radioButton.isChecked():
            self.ui.scan_speedEdit.setEnabled(True)
        else:
            self.ui.scan_speedEdit.setEnabled(False)

    def random_points_check(self):
        """Function to block out line edits if random points check button not checked"""
        if self.ui.random_points_checkBox.isChecked():
            self.ui.random_sample_Edit.setEnabled(True)
        else:
            self.ui.random_sample_Edit.setEnabled(False)

    def SoftLimitWarning(self, value):
        """Raise warning message if movement values outside soft limits"""
        print('Raised an exception, create warning')
        self.progress.close()  # close progress bar
        # print('value = ', value)
        if value[0] == 'MissedTrigger':
            print('missed trigger warning')
            warning = QtWidgets.QMessageBox.warning(self, 'Missed Trigger',
                                                    "A trigger was missed - try reducing axis speed or number of averages",
                                                    QtWidgets.QMessageBox.Ok)  # Create warning message box to user

        elif value[0] == 'Timeout':
            warning = QtWidgets.QMessageBox.warning(self, 'Timeout Error',
                                                    "Axis timed out waiting for a trigger pulse",
                                                    QtWidgets.QMessageBox.Ok)  # Create warning message box to user

        else:
            warning = QtWidgets.QMessageBox.warning(self, 'Movement Outside Limits',
                                                    "Please change movement distance or soft limit settings",
                                                    QtWidgets.QMessageBox.Ok)  # Create warning message box to user

    def thread_complete(self):
        """Function to be executed when a QRunnable thread is completed"""
        print('Thread complete')
        print('thread complete activation state = ', self.isActiveWindow())
        print('current worker = ', self.worker)
        # time.sleep(2)
        self.worker = None  # reset worker class to none - does this help prevent GUI crashing between scans?
        print('now current worker = ', self.worker)
        self.sleepGUI()
        try:  # restart timers if they been paused for running the thread
            self.timer.start()
            self.timer2.start()
            print('timers restarted')
        except:
            print('timers not restarted')
            pass
        try:
            self.progress.close()  # close progress bar if open
        except:
            print('Progress bar not closed')

    def pause_timers(self):
        """Pause timers to allow methods to be run"""
        # Stop timers
        self.timer.stop()  # stop timers to recurring threads
        self.timer2.stop()
        time.sleep(0.1)
        count0 = self.pool.activeThreadCount()  # number of active threads when program termination started
        self.pool.clear()  # clear thread pool
        time.sleep(0.2)
        while self.pool.activeThreadCount() > 0:  # wait until thread count is 0
            count_i = self.pool.activeThreadCount()  # current number of active threads

    def UpdateFields(self, fields):
        """Update fields labels on GUI"""
        self.ui.BxLabel.setText('Bx = ' + fields[0] + ' mT')
        self.ui.ByLabel.setText('By = ' + fields[1] + ' mT')
        self.ui.BzLabel.setText('Bz = ' + fields[2] + ' mT')
        self.ui.tempLabel.setText('Temperature = ' + fields[3] + ' degrees C')

    def ReadFields(self):
        """Read fields using QThread Object"""
        worker = FieldsWorker(self.HP, self.averages)  # connect to FieldsWorker object
        worker.setAutoDelete(True)  # make worker auto-deletable so can be cleared
        worker.signals.result.connect(self.UpdateFields)
        self.pool.start(worker)  # start the FieldsWorker object

    def UpdatePositions(self, positions):
        """Update position labels on GUI"""
        self.ui.xposLabel.setText('x = ' + positions[
            0] + ' mm')  # Reset x position label; note Syntax; variable is string, use of "+" to concatenate
        self.ui.yposLabel.setText('y = ' + positions[1] + ' mm')
        self.ui.zposLabel.setText('z = ' + positions[2] + ' mm')

    def ReadPositions(self):
        """Read position using QThread Object"""
        # print('read positions now')
        worker = PositionsWorker(mc)  # connect to FieldsWorker object
        worker.signals.result.connect(self.UpdatePositions)
        worker.setAutoDelete(True)  # make worker auto-deletable so can be cleared
        self.pool.start(worker)

    def relative_move_click(self):
        """Function to be executed when relative movement button is clicked"""
        print('Selected Relative Movement')
        self.pause_timers()  # pause timers for updating GUI whilst function is executed

        x = (self.ui.xrelativeEdit.text())  # x value is current value in line Edit
        y = (self.ui.yrelativeEdit.text())  # y value is current value in line Edit
        z = (self.ui.zrelativeEdit.text())  # z value is current value in line Edit

        edits = [self.ui.xrelativeEdit, self.ui.yrelativeEdit,
                 self.ui.zrelativeEdit]  # group all line edit names together in a list
        values = [x, y, z]  # create empty list to store values from line edits in

        check_values = self.check_float(values, edits)  # check if entered values were floats

        if check_values is not None:  # if values are floats, execute command
            print('Move stage')
            print('Values = ', values)

            print('x=', str(x) + ' y=', str(y) + ' z=', str(z))

            # Create worker thread to handle moving motor and tracking progress
            print('create worker')
            x = values[0]
            y = values[1]
            z = values[2]
            self.worker = RelativeMoveWorker(mc, x, y, z)

            print('worker = ', print(self.worker))

            print('created')
            # worker.signals.result.connect(self.UpdateMotorSettings)
            self.worker.setAutoDelete(True)  # automatically delete QRunnable object after execution
            self.worker.signals.result.connect(self.UpdatePositions)  # function to execute with result signal
            print('connect progress')
            self.worker.signals.progress.connect(self.track_progess)  # function to execute with progress signal
            print('progress connected')
            self.worker.signals.error.connect(self.SoftLimitWarning)  # function to execute if exception raised

            self.worker.signals.finished.connect(self.thread_complete)

            # Create progress bar
            self.create_progress("Moving Relative Distance")

            self.pool.start(self.worker, priority=5)  # start pool after initialising progress bar

    def global_move_click(self):
        """Function to be executed when global movement button is clicked"""
        self.pause_timers()  # pause timers for updating GUI to avoid interfering with movement

        x1 = self.ui.xglobalEdit.text()  # x value is current value in line Edit
        y1 = self.ui.yglobalEdit.text()  # y value is current value in line Edit
        z1 = self.ui.zglobalEdit.text()  # z value is current value in line Edit

        edits = [self.ui.xglobalEdit, self.ui.yglobalEdit,
                 self.ui.zglobalEdit]  # store all relevant line edits in a list
        values = [x1, y1, z1]  # store all relevant values in a list

        check_values = self.check_float(values, edits)  # check if entered values were floats

        if check_values is not None:  # if values are floats, execute command
            x1 = values[0]
            y1 = values[1]
            z1 = values[2]

            # Create worker thread to handle moving motor and tracking progress
            print('create worker')
            self.worker = GlobalMoveWorker(mc, x1, y1, z1)  # connect to GlobalMoveWorker QRunnable Object
            print('created')
            # worker.signals.result.connect(self.UpdateMotorSettings)
            self.worker.setAutoDelete(True)
            print('connect progress')
            self.worker.signals.progress.connect(self.track_progess)
            print('progress connected')
            self.worker.signals.error.connect(self.SoftLimitWarning)
            # self.worker.signals.finished.connect(self.worker.delete)
            self.worker.signals.finished.connect(self.thread_complete)

            # Create progress bar
            self.create_progress("Moving to Position")

            self.pool.start(self.worker, priority=5)  # start pool after initialising progress bar

    def reset_axes_click(self):
        """Function to be executed when reset axes button is clicked"""
        self.pause_timers()  # pause timers for updating GUI so that the function can be executed

        # Create worker thread to handle sending reset command to motor axes
        self.worker = ResetAxesWorker(mc)  # connect to QRunnable object
        self.worker.setAutoDelete(True)
        self.worker.signals.progress.connect(self.track_progess)
        self.worker.signals.error.connect(self.SoftLimitWarning)
        self.worker.signals.finished.connect(self.thread_complete)

        # Create progress bar
        self.create_progress("Resetting Motor Controller Axes")

        self.pool.start(self.worker, priority=5)  # start pool after initialising progress bar

    def select_file_click(self):
        """Function to select file name and location to save scan data"""
        self.sleepGUI()

        self.pause_timers()  # pause timers for updating GUI so not to interfere with this function

        # Create FileDialog widget for selecting file name and location
        filedialog = QtWidgets.QFileDialog(self)
        filedialog.setDefaultSuffix("csv")
        filedialog.setNameFilter("Text Files (*.csv);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        filedialog.DontUseNativeDialog
        time.sleep(0.5)  # try adding short pause before executing file??
        selected = filedialog.exec_()
        if selected:
            filename = filedialog.selectedFiles()[0]
            self.ui.filenameEdit.setText(filename)
            self.thread_complete()
        else:
            return

    def multipoles_select_file_click(self):
        """Function to select file name and location to save multipole scan data"""
        self.sleepGUI()

        self.pause_timers()  # pause timers for updating GUI so not to interfere with this function

        # Create FileDialog widget for selecting file name and location
        filedialog = QtWidgets.QFileDialog(self)
        filedialog.setDefaultSuffix("csv")
        filedialog.setNameFilter("Text Files (*.csv);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        filedialog.DontUseNativeDialog
        time.sleep(0.5)  # try adding short pause before executing file??
        selected = filedialog.exec_()
        if selected:
            filename = filedialog.selectedFiles()[0]
            self.ui.multipoles_filenameEdit.setText(filename)
            self.thread_complete()
        else:
            return

    def ScanUpdateGUI(self, data):
        """Update positions and fields in GUI during scan using data emitted from QRunnable Object"""

        # Update the position and field screen on the GUI
        self.ui.xposLabel.setText('x = ' + data[
            0] + ' mm')  # Reset x position label; note Syntax; variable is string, use of "+" to concatenate
        self.ui.yposLabel.setText('y = ' + data[1] + ' mm')
        self.ui.zposLabel.setText('z = ' + data[2] + ' mm')
        self.ui.BxLabel.setText('Bx = ' + data[3] + ' mT')
        self.ui.ByLabel.setText('By = ' + data[4] + ' mT')
        self.ui.BzLabel.setText('Bz = ' + data[5] + ' mT')
        self.ui.tempLabel.setText('Temperature = ' + data[6] + ' degrees C')

        # Update the scan graph
        self.graph_x.append(self.graph_x[-1] + 1)  # Add a new value 1 higher than the last.
        self.graph_bx.append(float(data[3]))  # Add new Bx value value.
        self.graph_by.append(float(data[4]))  # Add new By value value.
        self.graph_bz.append(float(data[5]))  # Add new Bz value value.

        self.data_line_bx.setData(self.graph_x, self.graph_bx)  # Update the Bx data.
        self.data_line_by.setData(self.graph_x, self.graph_by)  # Update the By data.
        self.data_line_bz.setData(self.graph_x, self.graph_bz)  # Update the Bz data.

    def scan_click(self):
        """Function to be executed when scan button pressed"""

        self.pause_timers()  # Pause timers for updating GUI so not to interfere with running this function

        # Retrieve values stored in line edits
        x0 = self.ui.scan_x0Edit.text()  # Get x0 value
        if self.ui.xplaneRadio.isChecked():  # if fixed x point
            x1 = x0
            dx = 1
        else:  # if range of x values
            x1 = self.ui.scan_x1Edit.text()  # Get x1 value
            dx = self.ui.scan_dxEdit.text()  # Get dx value
        y0 = self.ui.scan_y0Edit.text()  # Get y0 value
        if self.ui.yplaneRadio.isChecked():  # if fixed y point
            y1 = y0
            dy = 1
        else:  # if range of y values
            y1 = self.ui.scan_y1Edit.text()  # Get y1 value
            dy = self.ui.scan_dyEdit.text()  # Get dy value
        z0 = self.ui.scan_z0Edit.text()  # Get z0 value
        if self.ui.zplaneRadio.isChecked():  # if fixed y coordinate
            z1 = z0
            dz = 1
        else:  # if range of y values
            z1 = self.ui.scan_z1Edit.text()  # Get z1 value
            dz = self.ui.scan_dzEdit.text()  # Get dz value

        edits = [self.ui.scan_x0Edit, self.ui.scan_x1Edit, self.ui.scan_dxEdit, self.ui.scan_y0Edit,
                 self.ui.scan_y1Edit, self.ui.scan_dyEdit, self.ui.scan_z0Edit, self.ui.scan_z1Edit,
                 self.ui.scan_dzEdit]  # store all relevant line edits in a list
        values = [x0, x1, dx, y0, y1, dy, z0, z1, dz]  # store all relevant values in a list

        if self.ui.on_the_fly_radioButton.isChecked(): # if on the fly selected, check selected speed is real number
            scan_speed = self.ui.scan_speedEdit.text()
            edits.append(self.ui.scan_speedEdit)
            values.append(scan_speed)
        elif self.ui.random_points_checkBox.isChecked():  # if random points selected, check number of points is float
            number_points = self.ui.random_sample_Edit.text()
            edits.append(self.ui.random_sample_Edit)
            values.append(number_points)

        check_values = self.check_float(values, edits)  # check if entered values were floats

        if check_values is not None:  # if values are floats, execute scan

            order = self.ui.scanorder_Combo.currentIndex()  # get axis order from combo box
            filename = self.ui.filenameEdit.text()  # get filename from filename edit
            on_the_fly = self.ui.on_the_fly_radioButton.isChecked()  # boolean to represent on-the-fly scanning choice
            boundary_data = self.ui.boundary_data_checkBox.isChecked()  # boolean to represent boundary data scan choice
            random_points = self.ui.random_points_checkBox.isChecked()  # boolean to represent random sample points choice

            # Check if file can be written to
            try:
                print(exists(filename))
                if exists(filename):
                    my_file = open(filename, "r+")
            except:
                warning = QtWidgets.QMessageBox.warning(self, 'Cannot Access File',
                                                        "Please check file is not open or choose different file",
                                                        QtWidgets.QMessageBox.Ok)  # Create warning message box to user

            else:  # if file can be written to, execute code

                # Create worker thread to handle moving motor and tracking progress
                if boundary_data:
                    self.worker = ScanWorker_boundary(self.HP, mc, x0, x1, dx, y0, y1, dy, z0, z1, dz, order,
                                                          filename, self.averages)
                elif random_points:
                    self.worker = ScanWorker_random_sample(self.HP, mc, x0, x1, dx, y0, y1, dy, z0, z1, dz, order,
                                                          filename, self.averages, number_points)
                else: # can this be an elif block?
                    if on_the_fly:
                        self.worker = ScanWorker_onthefly(self.HP, mc, x0, x1, dx, y0, y1, dy, z0, z1, dz, order, filename,
                                                          self.averages, scan_speed)
                    else:
                        self.worker = ScanWorker_pointbypoint(self.HP, mc, x0, x1, dx, y0, y1, dy, z0, z1, dz, order,
                                                              filename, self.averages)
                print('created')
                # worker.signals.result.connect(self.UpdateMotorSettings)
                self.worker.setAutoDelete(True)
                self.worker.signals.result.connect(self.ScanUpdateGUI)  # update GUI at each scan step
                print('connect progress')
                self.worker.signals.progress.connect(self.track_progess)
                print('progress connected')
                self.worker.signals.error.connect(self.SoftLimitWarning)  # function to call if error raised
                self.worker.signals.finished.connect(self.thread_complete)

                # Create progress bar
                self.create_progress("Performing Scan")

                # Create graph object to display fields during scan
                self.graphWidget = pg.PlotWidget()
                # self.setCentralWidget(self.graphWidget)

                # Set graph axis titles and legend
                styles = {"color": "black", "font-size": "18px"}
                self.graphWidget.setLabel("left", "B / mT", **styles)
                self.graphWidget.setLabel("bottom", "Step Count", **styles)
                self.graphWidget.addLegend()

                self.graph_x = [0]  # starting array
                self.graph_bx = [np.nan]  # starting array
                self.graph_by = [np.nan]  # starting array
                self.graph_bz = [np.nan]  # starting array
                self.graphWidget.setBackground('w')
                pen_bx = pg.mkPen(color=(255, 0, 0), width=3)
                pen_by = pg.mkPen(color=(0, 255, 0), width=3)
                pen_bz = pg.mkPen(color=(0, 0, 255), width=3)
                self.data_line_bx = self.graphWidget.plot(self.graph_x, self.graph_bx, pen=pen_bx, name='Bx')
                self.data_line_by = self.graphWidget.plot(self.graph_x, self.graph_by, pen=pen_by, name='By')
                self.data_line_bz = self.graphWidget.plot(self.graph_x, self.graph_bz, pen=pen_bz, name='Bz')
                self.graphWidget.show()  # show the graph widget

                self.pool.start(self.worker, priority=5)  # start pool after initialising progress bar

    def multipoles_scan_click(self):
        """Function to be executed when multipoles scan button pressed"""
        print('Multipoles Scan function selected')

        self.pause_timers()

        # Retrieve values stored in line edits
        x0 = self.ui.multipole_x_Centre_Edit.text()  # Get x centre value

        y0 = self.ui.multipole_y_centre_Edit.text()  # Get ycentre  value

        r0 = self.ui.multipole_radius_Edit.text()  # get radius value

        steps = self.ui.multipoles_steps_Edit.text()  # get number of steps

        z0 = self.ui.multipoles_z0_Edit.text()  # Get z0 value
        if self.ui.multipoles_z_radio.isChecked():  # if fixed z coordinate
            z1 = z0
            dz = 1
        else:  # if range of y values
            z1 = self.ui.multipoles_z1_Edit.text()  # Get z1 value
            dz = self.ui.multipoles_dz_Edit.text()  # Get dz value

        edits = [self.ui.multipole_x_Centre_Edit, self.ui.multipole_y_centre_Edit, self.ui.multipole_radius_Edit,
                 self.ui.multipoles_steps_Edit, self.ui.multipoles_z0_Edit, self.ui.multipoles_z1_Edit,
                 self.ui.multipoles_dz_Edit]  # store all relevant line edits in a list
        values = [x0, y0, r0, steps, z0, z1, dz]  # store all relevant values in a list

        check_values = self.check_float(values, edits)  # check if entered values were floats

        if check_values is not None:  # if values are floats, execute command
            print('No errors')

            x0 = values[0]
            y0 = values[1]
            r0 = values[2]
            steps = values[3]
            z0 = values[4]
            z1 = values[5]
            dz = values[6]

            filename = self.ui.multipoles_filenameEdit.text()  # get filename from filename edit

            # Check if file can be written to
            try:
                print(exists(filename))
                if exists(filename):
                    my_file = open(filename, "r+")
            except:
                print('cant write to file')
                warning = QtWidgets.QMessageBox.warning(self, 'Cannot Access File',
                                                        "Please check file is not open or choose different file",
                                                        QtWidgets.QMessageBox.Ok)  # Create warning message box to user

            else:  # if file can be written to, execute code

                # Create worker thread to handle moving motor and tracking progress
                print('create worker')
                self.worker = MultipoleScanWorker(self.HP, mc, x0, y0, r0, steps, z0, z1, dz, filename, self.averages)
                print('created')
                # worker.signals.result.connect(self.UpdateMotorSettings)
                self.worker.setAutoDelete(True)
                self.worker.signals.result.connect(self.ScanUpdateGUI)
                print('connect progress')
                self.worker.signals.progress.connect(self.track_progess)
                print('progress connected')
                self.worker.signals.error.connect(self.SoftLimitWarning)
                self.worker.signals.finished.connect(self.thread_complete)

                # Create progress bar
                self.create_progress("Performing Scan")

                # Create graph object to display fields during scan
                self.graphWidget = pg.PlotWidget()
                # self.setCentralWidget(self.graphWidget)

                # Set graph axis titles and legend
                styles = {"color": "black", "font-size": "18px"}
                self.graphWidget.setLabel("left", "B / mT", **styles)
                self.graphWidget.setLabel("bottom", "Step Count", **styles)
                self.graphWidget.addLegend()

                self.graph_x = [0]  # starting array
                self.graph_bx = [np.nan]  # starting array
                self.graph_by = [np.nan]  # starting array
                self.graph_bz = [np.nan]  # starting array
                self.graphWidget.setBackground('w')
                pen_bx = pg.mkPen(color=(255, 0, 0), width=3)
                pen_by = pg.mkPen(color=(0, 255, 0), width=3)
                pen_bz = pg.mkPen(color=(0, 0, 255), width=3)
                self.data_line_bx = self.graphWidget.plot(self.graph_x, self.graph_bx, pen=pen_bx, name='Bx')
                self.data_line_by = self.graphWidget.plot(self.graph_x, self.graph_by, pen=pen_by, name='By')
                self.data_line_bz = self.graphWidget.plot(self.graph_x, self.graph_bz, pen=pen_bz, name='Bz')
                self.graphWidget.show()  # show the graph widget

                self.pool.start(self.worker, priority=5)  # start pool after initialising progress bar

    def UpdateProbeSettings(self, settings):
        """Update probe settings on GUI"""
        self.ui.rangeLabel.setText(settings[0])
        self.ui.rateLabel.setText("Sample Rate (Hz) = " + settings[1])
        self.ui.averageLabel.setText("Samples per average = " + str(self.averages))

    def ReadProbeSettings(self):
        """Read probe settings using QThread Object"""
        worker = ProbeSettingsWorker(self.HP)  # connect to FieldsWorker object
        worker.signals.result.connect(self.UpdateProbeSettings)
        worker.setAutoDelete(True)  # make worker auto-deletable so can be cleared
        self.pool.start(worker)

    def probe_settings_click(self):
        """Function to apply changes in probe settings"""
        self.pause_timers()
        # Set measurement range
        if self.HP.type() == '3MH6':
            if self.ui.rangeCombo.currentIndex() == 0:  # if 500mT selected
                new_range = 2  # set to measurement range 2
            else:  # if 2 T selected
                new_range = 3  # set to measurement range 3
        elif self.HP.type() == '3MTS':
            new_range = self.ui.rangeCombo.currentIndex()
        elif self.HP.type() == '3MH3':
            new_range = self.ui.rangeCombo.currentIndex()
        else:
            print('Invalid Hall probe type')

        # Set sample rate
        index = self.ui.samplerateCombo.currentIndex()
        rate = self.available_rates[index]

        # Set new averages
        new_averages = self.ui.averagesEdit.text()
        # Check values if integer > 0
        try:
            int(new_averages)
        except ValueError:
            warning = QtWidgets.QMessageBox.warning(self, 'Invalid Numbers',
                                                    "Please type positive integer values into averages box",
                                                    QtWidgets.QMessageBox.Ok)
        else:  # if no error in value
            self.averages = int(new_averages)

        worker = setProbeSettingsWorker(self.HP, new_range, rate)  # connect to setProbeSettingsWorker object
        worker.signals.result.connect(self.UpdateProbeSettings)
        worker.setAutoDelete(True)  # make worker auto-deletable so can be cleared
        worker.signals.finished.connect(self.thread_complete)

        worker.signals.progress.connect(self.track_progess)

        # Create progress bar
        self.create_progress("Updating Probe Settings")

        self.pool.start(worker, priority=5)  # start worker

    def UpdateMotorSettings(self, settings):
        """Update motor settings on GUI"""
        self.ui.xspeedLabel.setText(settings[0])
        self.ui.yspeedLabel.setText(settings[1])
        self.ui.zspeedLabel.setText(settings[2])
        self.ui.xlowerLabel.setText(settings[3])
        self.ui.xupperLabel.setText(settings[4])
        self.ui.ylowerLabel.setText(settings[5])
        self.ui.yupperLabel.setText(settings[6])
        self.ui.zlowerLabel.setText(settings[7])
        self.ui.zupperLabel.setText(settings[8])

    def ReadMotorSettings(self):
        """Read probe settings using QThread object"""
        worker = MotorSettingsWorker(mc)
        worker.signals.result.connect(self.UpdateMotorSettings)
        worker.setAutoDelete(True)
        self.pool.start(worker)

    def motor_settings_click(self):
        """Function to be executed when motor settings are updated"""
        self.pause_timers()  # pause timers for updating GUI whilst function is executed

        x_speed = self.ui.xspeedEdit.text()  # get x axis speed from GUI
        y_speed = self.ui.yspeedEdit.text()  # get y axis speed from GUI
        z_speed = self.ui.zspeedEdit.text()  # get z axis speed from GUI

        values = [x_speed, y_speed, z_speed]  # list of values to check if valid numbers
        edits = [self.ui.xspeedEdit, self.ui.yspeedEdit, self.ui.zspeedEdit]  # list of GUI line edits

        x_lower = self.ui.xlowerEdit.text()  # get x lower soft limit from GUI
        x_upper = self.ui.xupperEdit.text()  # get x upper soft limit from GUI
        values.append(x_lower)
        values.append(x_upper)
        edits.append(self.ui.xlowerEdit)
        edits.append(self.ui.xupperEdit)

        y_lower = self.ui.ylowerEdit.text()  # get y lower soft limit from GUI
        y_upper = self.ui.yupperEdit.text()  # get y upper soft limit from GUI
        values.append(y_lower)
        values.append(y_upper)
        edits.append(self.ui.ylowerEdit)
        edits.append(self.ui.yupperEdit)

        z_lower = self.ui.zlowerEdit.text()  # get z lower soft limit from GUI
        z_upper = self.ui.zupperEdit.text()  # get z upper soft limit from GUI
        values.append(z_lower)
        values.append(z_upper)
        edits.append(self.ui.zlowerEdit)
        edits.append(self.ui.zupperEdit)

        check_values = self.check_float(values, edits)  # call function to check if user has entered valid values

        if check_values is not None:
            print('No errors')
            # Check speeds are not greater than maximum
            if float(x_speed) > self.max_speeds[0]:
                warning = QtWidgets.QMessageBox.warning(self, 'Out of Range', (
                    f'Requested x speed {float(x_speed)} mm/s is higher than maximum {self.max_speeds[0]} mm/s.'),
                                                        QtWidgets.QMessageBox.Ok)
            elif float(y_speed) > self.max_speeds[1]:
                warning = QtWidgets.QMessageBox.warning(self, 'Out of Range', (
                    f'Requested y speed {float(y_speed)} mm/s is higher than maximum {self.max_speeds[1]} mm/s.'),
                                                        QtWidgets.QMessageBox.Ok)
            elif float(z_speed) > self.max_speeds[2]:
                warning = QtWidgets.QMessageBox.warning(self, 'Out of Range', (
                    f'Requested z speed {float(z_speed)} mm/s is higher than maximum {self.max_speeds[2]} mm/s.'),
                                                        QtWidgets.QMessageBox.Ok)
            else:
                print('create worker class and set new speeds')

                worker = setMotorSettingsWorker(mc, float(x_speed), float(y_speed), float(z_speed), x_lower, x_upper,
                                                y_lower, y_upper, z_lower,
                                                z_upper)  # connect to setProbeSettingsWorker object
                worker.signals.result.connect(self.UpdateMotorSettings)
                worker.setAutoDelete(True)  # make worker auto-deletable so can be cleared
                worker.signals.finished.connect(self.thread_complete)

                worker.signals.progress.connect(self.track_progess)

                # Create progress bar
                self.create_progress("Updating Motor Settings")

                self.pool.start(worker, priority=5)  # start worker

    def changeEvent(self, event):
        """Function to be executed when GUI window minimised"""
        # does this function reduce likelihood of GUI freezing after being minimised?
        if event.type() == QtCore.QEvent.WindowStateChange:
            if event.oldState() and QtCore.Qt.WindowMinimized:
                print("WindowMinimized")
            elif event.oldState() == QtCore.Qt.WindowNoState or self.windowState() == QtCore.Qt.WindowMaximized:
                print("WindowMaximized")
            else:
                print('Other Window Change')

        if event.type() == QtCore.QEvent.ActivationChange:  # if e.g. other programme clicked on
            print('activation state = ', self.isActiveWindow())
            event.accept()  # accept event - helps with crashing ??
            QCoreApplication.processEvents()  # try processing all events?

            '''if self.windowState() & QtCore.Qt.WindowMinimized:
                print('window minimised')
                # event.ignore()
                return
            elif self.windowState() & QtCore.Qt.WindowMaximized:
                print('window maximised')
                # event.ignore()
                return'''

    def closeEvent(self, event):
        """Function to check that user wants to exit program when close button pressed"""
        self.sleepGUI()
        # Raise message box to check user wants to quit application
        choice = QtWidgets.QMessageBox.question(self, 'Magnet Lab Controls',
                                                "Do you want to exit the program?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if choice == QtWidgets.QMessageBox.Yes:
            self.timer.stop()  # stop timers to recurring threads
            self.timer2.stop()
            time.sleep(0.1)

            count0 = self.pool.activeThreadCount()  # number of active threads when program termination started

            self.pool.clear()  # clear thread pool
            time.sleep(0.2)

            # Set window text, stop button text, minimum value, maximum value
            self.progress = QtWidgets.QProgressDialog("Closing down", "STOP", 0, 100, self)
            self.progress.setWindowTitle('Please wait...')
            self.progress.setAutoClose(True)  # Automatically close dialog once progress completed
            self.progress.setWindowModality(
                QtCore.Qt.WindowModal)  # Make window modal so processes can take place in background
            self.progress.canceled.connect(self.progress.close)  # Close dialog when close button pressed
            self.progress.show()  # Show progress dialog

            while self.pool.activeThreadCount() > 0:
                count_i = self.pool.activeThreadCount()  # current number of active threads
                closed_threads = count0 - count_i
                progress = int(100 * closed_threads / count0)
                self.track_progess(progress - 1)

            self.pool.waitForDone()  # wait for all active threads to be closed

            self.HP.close()  # close serial port connection with tesla-meter
            mc.close()  # close serial connection with motor controller

            sys.exit()  # close the app
        else:
            event.ignore()


class PickProbeWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(PickProbeWindow, self).__init__()
        self.ui = Ui_SelectionWindow()
        self.ui.setupUi(self)

        self.ui.LaunchAppButton.clicked.connect(self.show_new_window)

    def show_new_window(self, checked):
        """Select Teslameter and launch app"""

        self.ui.selection_warning_label.setText('Please wait...')
        # self.ui.selection_warning_label.setStyleSheet("")

        teslameter_list = [teslameter_3MH6('COM3'), teslameter_3MTS(), teslameter_3MH3('COM4'),
                           teslameter_blank()]  # list of possible Teslameters

        index = self.ui.teslameter_comboBox.currentIndex()
        HP = teslameter_list[index]

        try: # launch main app with selected Teslameter connected
            self.w = mywindow(HP)
            self.w.show()
            self.hide()
        except:  # raise exception if selected Teslameter not connected to PC
            self.ui.selection_warning_label.setText('Please check Teslameter is connected')
            self.ui.selection_warning_label.setStyleSheet("background-color: red")


app = QtWidgets.QApplication([])
application = PickProbeWindow()
# application = mywindow()
application.show()
sys.exit(app.exec())  # create window
