import numpy as np
import time
import struct
import ctypes as C
import os
import sys


# Is this code needed for saving DLL in a .exe file?
# determine if application is a script file or frozen exe
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

#config_path = os.path.join(application_path, config_name)

#path = (os.getcwd())  # get working directory

#C.windll.kernel32.SetDllDirectoryW(os.getcwd().replace('\\', '/'))

C.windll.kernel32.SetDllDirectoryW(application_path.replace('\\', '/'))

#A3mtslib = C.CDLL(os.path.join(path, "A3mtslib64"))  # find software library
A3mtslib = C.CDLL("A3mtslib64")  # find software library

class teslameter_3MTS:
    """Class to establish communication with Senis 3MTS Teslameter"""

    def __init__(self):

        # Count number of connected devices
        # EXPORT  int count_devices(unsigned short* number_of_devices);
        i = C.c_ushort()  # create unsigned short variable
        result = A3mtslib.count_devices(C.byref(i))  # call function to count connected devices
        print('Number connected devices = ', i.value)

        # Get device name
        p = C.create_string_buffer(40)  # empty string buffer to store device name in
        # EXPORT  int get_device_name_ch(int *device_number, char *name );
        self.device_number = C.c_int()  # C type integer
        result = A3mtslib.get_device_name_ch(C.byref(self.device_number), C.byref(p))  # get name of device
        print('Device name = ', p.value)

        self.device_number.value = 0

        # Define available sampling rates 

        # Define available measurement ranges
        self.available_ranges = [0, 1, 2, 3]  # list of available measurement ranges
        # Measurement ranges correspond to 0.1, 0.5, 3, 20 T

    def open(self):
        """Open device"""
        A3mtslib.open_device(C.byref(self.device_number))

    def type(self):
        """Return string describing Hall probe type"""
        return '3MTS'

    def sample_rates(self):
        """Available sampling rates / Hz"""
        return [10, 20, 50, 100, 200, 500, 1E3]

    def reject_outliers(self, data, m=2):
        """Function to reject obvious outliers from data array"""
        return data[abs(data - np.mean(data)) < m * np.std(data)]

    def help(self):
        """Sends help command to teslameter and reads response"""
        pass

    def get_fields(self, samples=1000):
        """Measure B fields averaged over n samples"""

        if type(samples) == int and samples > 0:  # if samples given is integer > 0
            bx_values = [0]  # empty array to store bx values in
            by_values = [0]  # empty array to store by values in
            bz_values = [0]  # empty array to store bz values in
            th_values = [0]  # empty array to store probe temperature values in

            while len(bx_values) < samples:  # read n samples
                # Read fields
                timestamp = C.c_ulong()
                sensorx = C.c_float()
                sensory = C.c_float()
                sensorz = C.c_float()

                # read values
                A3mtslib.get_sensor_values_fl(C.byref(self.device_number), C.byref(timestamp), C.byref(sensorx),
                                              C.byref(sensory), C.byref(sensorz))
                bx = sensorx.value  # Bx sensor value / uT
                by = sensory.value  # By sensor value / uT
                bz = sensorz.value  # Bz sensor value / uT

                bx_values.append(bx / 1000)  # append Bx field / mT
                by_values.append(by / 1000)  # append By field / mT
                bz_values.append(bz / 1000)  # append Bz field / mT

            bx_ave = np.mean(bx_values)  # bx average
            bx_sd = np.std(bx_values)  # bx standard deviation
            by_ave = np.mean(by_values)  # by average
            by_sd = np.std(by_values)  # by standard deviation
            bz_ave = np.mean(bz_values)  # bz average
            bz_sd = np.std(bz_values)  # bz standard deviation
            th_ave = 0  # Hall probe temperature average not measured by 3MTS
            th_sd = 0  # Hall probe temperature standard deviation not measured by 3MTS
            return [bx_ave, by_ave, bz_ave, bx_sd, by_sd, bz_sd, th_ave, th_sd]
        else:
            print('Please enter valid number of samples to use in average')

    def set_sample_rate(self, rate):
        """Set Teslameter samples rate (samples per second)"""

        time_period = int(1000 / rate)  # time period per sample / ms

        result = A3mtslib.set_speed(C.byref(self.device_number), time_period)
        print('Set sample result = ', result)

        return self.get_sample_rate()

    def get_sample_rate(self):
        """Get current Teslameter samples rate (samples per second)"""

        period = C.c_ushort()
        A3mtslib.get_speed(C.byref(self.device_number), C.byref(period))  # get time per sample / ms

        time_period = period.value / 1000  # time per sample / seconds

        rate = 1 / time_period  # sample rate / Hz

        return rate

    def set_range(self, set_range):
        """Set Teslameter measurement range"""
        if set_range in self.available_ranges:  # if selected range is available to be set

            result = A3mtslib.set_range(C.byref(self.device_number), set_range)
            print(result)

            return self.get_range()

    def get_range(self):
        """Get current measurement range from Teslameter"""
        # get range
        range = C.c_ushort()
        A3mtslib.get_range(C.byref(self.device_number), C.byref(range))

        return range.value

    def close(self):
        """Close connection to Teslameter"""
        A3mtslib.close_device(C.byref(self.device_number))
