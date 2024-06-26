from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QMutex, QCoreApplication, \
    QEvent
from PyQt5.QtWidgets import QFileDialog

from HP_bench_GUI import Ui_MainWindow  # import MainWindow created from designer and exported to .py file
from teslameter_3MH6 import teslameter_3MH6  # import 3MH6 Teslameter class to read field
from teslameter_3MTS import teslameter_3MTS # import teslameter 3MTS class
from teslameter_blank import teslameter_blank # import blank teslameter class
import motor_controller_PM1000
import traceback, sys
import numpy as np
import csv
import time
import re
import datetime
import serial

mutex = QMutex
from os.path import exists
from FieldsWorker import FieldsWorker
from PositionsWorker import PositionsWorker
from RelativeMoveWorker import RelativeMoveWorker
from GlobalMoveWorker import GlobalMoveWorker
from ScanWorker import ScanWorker
from MultipoleScanWorker import MultipoleScanWorker
from ProbeSettingsWorker import ProbeSettingsWorker
from setProbeSettingsWorker import setProbeSettingsWorker
from MotorSettingsWorker import MotorSettingsWorker
from setMotorSettingsWorker import setMotorSettingsWorker

#HP = teslameter_3MH6('COM3')  # create Hall probe class and open serial port
#HP = teslameter_3MTS()
HP = teslameter_blank()

mc = motor_controller_PM1000.MotorController()
xa = mc.axis['x'] # x axis on Hall probe bench
ya = mc.axis['y']
za = mc.axis['z']



class mywindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(mywindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.label_23.setText('Magnet Lab Controls - Hall Probe v3.0')

        self.ui.tabWidget.tabBarClicked.connect(self.sleepGUI)  # sleep GUI

        # Infinite Loop for continuously updating probe position and field measurements
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(False)
        self.timer.setInterval(100)  # in milliseconds, so 5000 = 5 seconds
        # self.timer.timeout.connect(self.update_current_measurements)
        if HP.type() != 'blank':
            self.timer.timeout.connect(self.ReadFields)  # connect timer to read fields function
        #self.timer.timeout.connect(self.ReadPositions)  # connect timer to read positions function
        self.timer.start()

        # Second timer for updating settings
        self.timer2 = QtCore.QTimer(self)
        self.timer2.setSingleShot(False)
        self.timer2.setInterval(5000)  # in milliseconds, so 5000 = 5 seconds
        if HP.type() != 'blank':
            self.timer2.timeout.connect(self.ReadProbeSettings)  # connect timer to read probe settings function
        # self.timer2.timeout.connect(self.ReadMotorSettings)  ###Connect timer to read motor settings function
        self.timer2.timeout.connect(self.ReadPositions)
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

        # Connect Push Buttons on Movement Tab to functions to execute movement
        self.ui.relativemoveButton.clicked.connect(
            self.relative_move_click)  # Connect relative move push button to function
        self.ui.globalmoveButton.clicked.connect(self.global_move_click)  # connect global move push button to function

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
        self.averages = 1000  # Set default number of field samples per average

        # Determine initial measurement range - probe dependant
        initial_range = HP.get_range() # determine initial range
        if HP.type() == '3MH6':
            range_list = ['500 mT', '2 T'] # available ranges for 3MH6 Teslameter
            self.ui.rangeCombo.addItems(range_list)
            if initial_range[0:6] == 'mrng:2':  # if range 2
                self.ui.rangeCombo.setCurrentIndex(0)
            elif initial_range[0:6] == 'mrng:3':  # if range 3
                self.ui.rangeCombo.setCurrentIndex(1)
        elif HP.type() == '3MTS':
            range_list = ['100 mT', '500 mT', '3 T', '20 T']  # available ranges for 3MH6 Teslameter
            self.ui.rangeCombo.addItems(range_list)
            self.ui.rangeCombo.setCurrentIndex(initial_range)


        self.available_rates = HP.sample_rates()  # available sample rates
        string_rates = ["{:.0f}".format(i) for i in self.available_rates] # list where rates are strings
        self.ui.samplerateCombo.addItems(string_rates) # add string items to combo box
        initial_rate = HP.get_sample_rate()
        if initial_rate in self.available_rates:
            index = self.available_rates.index(initial_rate)
            self.ui.samplerateCombo.setCurrentIndex(index)
        self.ui.averagesEdit.setText("{:.0f}".format(self.averages))
        self.ui.probesettingsButton.clicked.connect(self.probe_settings_click)
        if HP.type() == 'blank':
            self.ui.probesettingsButton.setEnabled(False) # no need to update if no probe
        # self.ReadProbeSettings() # read initial probe settings

        # Initialise motor settings page
        vx0 = "{:.1f}".format(xa.getSpeed())
        self.ui.xspeedEdit.setText(vx0)  # set line edit to current x speed
        self.ui.xspeedLabel.setText(vx0)
        vy0 = "{:.1f}".format(ya.getSpeed())
        self.ui.yspeedEdit.setText(vy0)  # set line edit to current y speed
        self.ui.yspeedLabel.setText(vy0)
        vz0 = "{:.1f}".format(za.getSpeed())
        self.ui.zspeedEdit.setText(vz0)  # set line edit to current z speed
        self.ui.zspeedLabel.setText(vz0)
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

    def track_progess(self, value):
        """Create progress bar to track progress of actions"""
        if self.progress.wasCanceled():  # if cancel button has been pressed
            print('Movement cancelled!!!')
            self.worker.isRun = False  # stop current worker from running further
        else:  # if progress not cancelled
            self.progress.setValue(value - 1)  # set progress bar value
            if value == 99:
                self.progress.setValue(100)

    def check_float(self, values, edits):
        """Function to check values entered into line edits are float type"""
        print('Checking if float')
        for i in range(len(edits)):  # for all values in edits list
            edits[i].setStyleSheet('background-color: rgb(255, 255, 255);')  # reset line edit colour to white
        try:
            for i in range(len(values)):  # for all values entered
                values[i] = float(values[i])  # check values are numbers
        except ValueError:  # if any entered values are not numbers
            print('Invalid Numbers Entered')
            warning = QtWidgets.QMessageBox.warning(self, 'Invalid Numbers',
                                                    "Please type valid numbers into the boxes",
                                                    QtWidgets.QMessageBox.Ok)  # Create warning message box to user
        else:  # if no value errors
            print('No errors')
            return values
        finally:  # after error loop completed, needed because loop stops after encountering first error
            for i in range(len(edits)):  # for all line edits
                try:
                    values[i] = float(values[i])  # check values are numbers
                except ValueError:  # if value is not a number
                    edits[i].setStyleSheet('background-color: rgb(255, 0, 0);')  # reset line edit colour to red

    def movement_radio(self):
        """Function to Select correct page of stacked widget for selected movement type"""
        if self.ui.relativeRadio.isChecked():  # if Relative Radio checked
            self.ui.movementStack.setCurrentIndex(0)  # set stacked widget to relative motion page
        else:  # if Global radio checked
            self.ui.movementStack.setCurrentIndex(1)  # set stacked widget to global motion page

    def fixed_x_radio(self):
        """Function to block out line edits if x scan at fixed coordinate"""
        print('Radio toggled')
        if self.ui.xplaneRadio.isChecked():
            print('Button checked')
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
        """Function to block out line edits if z scan at fixed coordinate"""
        if self.ui.multipoles_z_radio.isChecked():
            self.ui.multipoles_z1_Edit.setEnabled(False)
            self.ui.multipoles_dz_Edit.setEnabled(False)
        else:
            self.ui.multipoles_z1_Edit.setEnabled(True)
            self.ui.multipoles_dz_Edit.setEnabled(True)

    def SoftLimitWarning(self):
        """Raise warning message if movement values outside soft limits"""
        print('Raised on exception, create warning')
        self.progress.close()  # close progress bar
        warning = QtWidgets.QMessageBox.warning(self, 'Movement Outside Soft Limits',
                                                "Please change movement distance or soft limit settings",
                                                QtWidgets.QMessageBox.Ok)  # Create warning message box to user

    def thread_complete(self):
        """Function to be executed when a thread is completed"""
        print('Thread complete')
        print('thread complete activation state = ', self.isActiveWindow())
        print('current worker = ', self.worker)
        # time.sleep(2)
        self.worker = None  # reset worker class to none - does this help prevent GUI crashing between scans?
        print('now current worker = ', self.worker)
        self.sleepGUI()
        try: # restart timers if been paused
            self.timer.start()
            self.timer2.start()
            print('timers restarted')
        except:
            print('timers not restarted')
            pass

    def pause_timers(self):
        """Pause timers to allow methods to be run"""
        # Stop timers
        self.timer.stop()  # stop timers to recurring threads
        self.timer2.stop()
        time.sleep(0.1)
        count0 = self.pool.activeThreadCount()  # number of active threads when program termination started
        print('Number of threads to close = ', count0)
        self.pool.clear()  # clear thread pool
        time.sleep(0.2)
        while self.pool.activeThreadCount() > 0:
            count_i = self.pool.activeThreadCount()  # current number of active threads
        print('new count = ', self.pool.activeThreadCount())

    def UpdateFields(self, fields):
        """Update fields labels on GUI"""
        self.ui.BxLabel.setText('Bx = ' + fields[0] + ' mT')
        self.ui.ByLabel.setText('By = ' + fields[1] + ' mT')
        self.ui.BzLabel.setText('Bz = ' + fields[2] + ' mT')
        self.ui.tempLabel.setText('Temperature = ' + fields[3] + ' degrees C')

    def ReadFields(self):
        """Read fields using QThread Object"""
        worker = FieldsWorker(HP, self.averages)  # connect to FieldsWorker object
        worker.setAutoDelete(True)  # make worker auto-deletable so can be cleared
        worker.signals.result.connect(self.UpdateFields)
        self.pool.start(worker)

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
        self.pause_timers()

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
            self.worker.setAutoDelete(True)
            self.worker.signals.result.connect(self.UpdatePositions)
            print('connect progress')
            self.worker.signals.progress.connect(self.track_progess)
            print('progress connected')
            self.worker.signals.error.connect(self.SoftLimitWarning)

            self.worker.signals.finished.connect(self.thread_complete)

            # Create progress bar
            # Set window text, stop button text, minimum value, maximum value
            print('create progress bar')
            self.progress = QtWidgets.QProgressDialog("Moving Relative Distance", "STOP", 0, 100, self)
            self.progress.setWindowTitle('Please wait...')
            self.progress.setAutoClose(True)  # Automatically close dialog once progress completed
            self.progress.setWindowModality(
                QtCore.Qt.WindowModal)  # Make window modal so processes can take place in background
            self.progress.canceled.connect(self.progress.close)  # Close dialog when close button pressed
            self.progress.show()  # Show progress dialog

            self.pool.start(self.worker, priority=5)  # start pool after initialising progress bar

            print('worker now =', self.worker)

    def global_move_click(self):
        """Function to be executed when global movement button is clicked"""
        print('Selected Global Movement')
        self.pause_timers()

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
            print('Moving to position (', str(x1) + ',', str(y1) + ',', str(z1) + ')')  # print new position

            # Create worker thread to handle moving motor and tracking progress
            print('create worker')
            self.worker = GlobalMoveWorker(mc, x1, y1, z1)
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
            # Set window text, stop button text, minimum value, maximum value
            self.progress = QtWidgets.QProgressDialog("Moving To Position", "STOP", 0, 100, self)
            self.progress.setWindowTitle('Please wait...')
            self.progress.setAutoClose(True)  # Automatically close dialog once progress completed
            self.progress.setWindowModality(
                QtCore.Qt.WindowModal)  # Make window modal so processes can take place in background
            self.worker.signals.result.connect(self.UpdatePositions)
            self.progress.canceled.connect(self.progress.close)  # Close dialog when close button pressed
            self.progress.show()  # Show progress dialog

            self.pool.start(self.worker, priority=5)  # start pool after initialising progress bar



    def select_file_click(self):
        """Function to select file name and location to save scan data"""
        print('Select a file')
        self.sleepGUI()
        print('select file activation state = ', self.isActiveWindow())

        self.pause_timers()

        print('create filedialog')
        filedialog = QtWidgets.QFileDialog(self)
        print('ok here 1')
        filedialog.setDefaultSuffix("csv")
        filedialog.setNameFilter("Text Files (*.csv);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        filedialog.DontUseNativeDialog
        print('ok here 2')
        time.sleep(0.5) # try adding short pause before executing file??
        print('current threads = ', self.pool.activeThreadCount())
        selected = filedialog.exec_()
        print('ok here 3')
        if selected:
            filename = filedialog.selectedFiles()[0]
            print('filename = ', filename)
            self.ui.filenameEdit.setText(filename)
            self.thread_complete()
        else:
            return



    def multipoles_select_file_click(self):
        """Function to select file name and location to save theta scan data"""
        print('Select a file')
        self.sleepGUI()
        print('select file activation state = ', self.isActiveWindow())

        self.pause_timers()

        print('create filedialog')
        filedialog = QtWidgets.QFileDialog(self)
        print('ok here 1')
        filedialog.setDefaultSuffix("csv")
        filedialog.setNameFilter("Text Files (*.csv);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        filedialog.DontUseNativeDialog
        print('ok here 2')
        time.sleep(0.5)  # try adding short pause before executing file??
        print('current threads = ', self.pool.activeThreadCount())
        selected = filedialog.exec_()
        print('ok here 3')
        if selected:
            filename = filedialog.selectedFiles()[0]
            print('filename = ', filename)
            self.ui.multipoles_filenameEdit.setText(filename)
            self.thread_complete()
        else:
            return


        '''if filename[1] == 'Text Files (*.csv)' and filename[0][-4:] != '.csv':
            filename = filename[0] + '.csv'
        else:
            filename = filename[0]
        self.ui.filenameEdit.setText(filename)'''

    def ScanUpdateGUI(self, data):
        """Update positions and fields in GUI during scan"""
        print('update the GUI')
        self.ui.xposLabel.setText('x = ' + data[
            0] + ' mm')  # Reset x position label; note Syntax; variable is string, use of "+" to concatenate
        self.ui.yposLabel.setText('y = ' + data[1] + ' mm')
        self.ui.zposLabel.setText('z = ' + data[2] + ' mm')
        self.ui.BxLabel.setText('Bx = ' + data[3] + ' mT')
        self.ui.ByLabel.setText('By = ' + data[4] + ' mT')
        self.ui.BzLabel.setText('Bz = ' + data[5] + ' mT')
        self.ui.tempLabel.setText('Temperature = ' + data[6] + ' degrees C')



    def scan_click(self):
        """Function to be executed when scan button pressed"""
        print('Scan function selected')

        self.pause_timers()

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

        check_values = self.check_float(values, edits)  # check if entered values were floats

        if check_values is not None:  # if values are floats, execute command
            print('No errors')

            x0 = values[0]
            x1 = values[1]
            dx = values[2]
            y0 = values[3]
            y1 = values[4]
            dy = values[5]
            z0 = values[6]
            z1 = values[7]
            dz = values[8]

            order = self.ui.scanorder_Combo.currentIndex()  # get axis order from combo box
            filename = self.ui.filenameEdit.text()  # get filename from filename edit

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
                self.worker = ScanWorker(HP, mc, x0, x1, dx, y0, y1, dy, z0, z1, dz, order, filename, self.averages)
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
                # Set window text, stop button text, minimum value, maximum value
                self.progress = QtWidgets.QProgressDialog("Performing Scan", "STOP", 0, 100, self)
                self.progress.setWindowTitle('Please wait...')
                self.progress.setAutoClose(True)  # Automatically close dialog once progress completed
                self.progress.setWindowModality(
                    QtCore.Qt.WindowModal)  # Make window modal so processes can take place in background
                self.progress.canceled.connect(self.progress.close)  # Close dialog when close button pressed
                self.progress.show()  # Show progress dialog

                self.pool.start(self.worker, priority=5)  # start pool after initialising progress bar



    def multipoles_scan_click(self):
        """Function to be executed when multipoles scan button pressed"""
        print('Multipoles Scan function selected')

        self.pause_timers()

        # Retrieve values stored in line edits
        x0 = self.ui.multipole_x_Centre_Edit.text()  # Get x centre value

        y0 = self.ui.multipole_y_centre_Edit.text()  # Get ycentre  value

        r0 = self.ui.multipole_radius_Edit.text() # get radius value

        steps = self.ui.multipoles_steps_Edit.text() # get number of steps

        z0 = self.ui.multipoles_z0_Edit.text()  # Get z0 value
        if self.ui.multipoles_z_radio.isChecked():  # if fixed z coordinate
            z1 = z0
            dz = 1
        else:  # if range of y values
            z1 = self.ui.multipoles_z1_Edit.text()  # Get z1 value
            dz = self.ui.multipoles_dz_Edit.text()  # Get dz value

        edits = [self.ui.multipole_x_Centre_Edit, self.ui.multipole_y_centre_Edit, self.ui.multipole_radius_Edit, self.ui.multipoles_steps_Edit, self.ui.multipoles_z0_Edit, self.ui.multipoles_z1_Edit, self.ui.multipoles_dz_Edit]  # store all relevant line edits in a list
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
                self.worker = MultipoleScanWorker(HP, mc, x0, y0, r0, steps, z0, z1, dz, filename, self.averages)
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
                # Set window text, stop button text, minimum value, maximum value
                self.progress = QtWidgets.QProgressDialog("Performing Scan", "STOP", 0, 100, self)
                self.progress.setWindowTitle('Please wait...')
                self.progress.setAutoClose(True)  # Automatically close dialog once progress completed
                self.progress.setWindowModality(
                    QtCore.Qt.WindowModal)  # Make window modal so processes can take place in background
                self.progress.canceled.connect(self.progress.close)  # Close dialog when close button pressed
                self.progress.show()  # Show progress dialog

                self.pool.start(self.worker, priority=5)  # start pool after initialising progress bar

    def UpdateProbeSettings(self, settings):
        """Update probe settings on GUI"""
        self.ui.rangeLabel.setText(settings[0])
        self.ui.rateLabel.setText("Sample Rate (SPS) = " + settings[1])
        self.ui.averageLabel.setText("Samples per average = " + str(self.averages))

    def ReadProbeSettings(self):
        """Read probe settings using QThread Object"""
        worker = ProbeSettingsWorker(HP)  # connect to FieldsWorker object
        worker.signals.result.connect(self.UpdateProbeSettings)
        worker.setAutoDelete(True)  # make worker auto-deletable so can be cleared
        self.pool.start(worker)

    def probe_settings_click(self):
        """Function to apply changes in probe settings"""
        print('Changing probe settings')
        self.pause_timers()
        # Set measurement range
        if HP.type() == '3MH6':
            if self.ui.rangeCombo.currentIndex() == 0:  # if 500mT selected
                new_range = 2  # set to measurement range 2
            else:  # if 2 T selected
                new_range = 3  # set to measurement range 3
        elif HP.type() == '3MTS':
            new_range = self.ui.rangeCombo.currentIndex()

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

        worker = setProbeSettingsWorker(HP, new_range, rate)  # connect to setProbeSettingsWorker object
        worker.signals.result.connect(self.UpdateProbeSettings)
        worker.setAutoDelete(True)  # make worker auto-deletable so can be cleared
        worker.signals.finished.connect(self.thread_complete)

        worker.signals.progress.connect(self.track_progess)

        # Create progress bar
        # Set window text, stop button text, minimum value, maximum value
        self.progress = QtWidgets.QProgressDialog("Updating Probe Settings", "STOP", 0, 100, self)
        self.progress.setWindowTitle('Please wait...')
        self.progress.setAutoClose(True)  # Automatically close dialog once progress completed
        self.progress.setWindowModality(
            QtCore.Qt.WindowModal)  # Make window modal so processes can take place in background
        self.progress.canceled.connect(self.progress.close)  # Close dialog when close button pressed
        self.progress.show()  # Show progress dialog

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
        """Function to be executed when motor settings updated"""
        print('Update motor settings')
        self.pause_timers()

        x_speed = self.ui.xspeedEdit.text()  # get x speed
        y_speed = self.ui.yspeedEdit.text()  # get y speed
        z_speed = self.ui.zspeedEdit.text()  # get z speed

        values = [x_speed, y_speed, z_speed]
        edits = [self.ui.xspeedEdit, self.ui.yspeedEdit, self.ui.zspeedEdit]

        x_lower = self.ui.xlowerEdit.text()  # get x lower limit
        x_upper = self.ui.xupperEdit.text()  # get x upper limit
        values.append(x_lower)
        values.append(x_upper)
        edits.append(self.ui.xlowerEdit)
        edits.append(self.ui.xupperEdit)

        y_lower = self.ui.ylowerEdit.text()  # get y lower limit
        y_upper = self.ui.yupperEdit.text()  # get y upper limit
        values.append(y_lower)
        values.append(y_upper)
        edits.append(self.ui.ylowerEdit)
        edits.append(self.ui.yupperEdit)

        z_lower = self.ui.zlowerEdit.text()  # get x lower limit
        z_upper = self.ui.zupperEdit.text()  # get x upper limit
        values.append(z_lower)
        values.append(z_upper)
        edits.append(self.ui.zlowerEdit)
        edits.append(self.ui.zupperEdit)

        check_values = self.check_float(values, edits)
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
                # Set window text, stop button text, minimum value, maximum value
                self.progress = QtWidgets.QProgressDialog("Updating Motor Settings", "STOP", 0, 100, self)
                self.progress.setWindowTitle('Please wait...')
                self.progress.setAutoClose(True)  # Automatically close dialog once progress completed
                self.progress.setWindowModality(
                    QtCore.Qt.WindowModal)  # Make window modal so processes can take place in background
                self.progress.canceled.connect(self.progress.close)  # Close dialog when close button pressed
                self.progress.show()  # Show progress dialog

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

        if event.type() == QtCore.QEvent.ActivationChange: #if e.g. other programme clicked on
            print('activation state = ', self.isActiveWindow())
            event.accept() # accept event - helps with crashing ??
            QCoreApplication.processEvents() # try processing all events?


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
        choice = QtWidgets.QMessageBox.question(self, 'Magnet Lab Controls',
                                                "Do you want to exit the program?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if choice == QtWidgets.QMessageBox.Yes:

            print(datetime.datetime.now())
            self.timer.stop()  # stop timers to recurring threads
            self.timer2.stop()
            time.sleep(0.1)

            count0 = self.pool.activeThreadCount()  # number of active threads when program termination started
            print('Number of threads to close = ', count0)

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

            print('new count = ', self.pool.activeThreadCount())

            self.pool.waitForDone()

            print('final count = ', self.pool.activeThreadCount())

            HP.close()  # close serial port connection with tesla-meter
            mc.close()  # close serial connection with motor controller

            print('Closing down...')
            print(datetime.datetime.now())
            sys.exit()
        else:
            print('Do not quit')
            event.ignore()


app = QtWidgets.QApplication([])
application = mywindow()
application.show()
sys.exit(app.exec())  # create window
