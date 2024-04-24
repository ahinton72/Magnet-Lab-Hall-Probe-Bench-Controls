import serial
import numpy as np
import time
import struct
import sys


class teslameter_3MH3:
    """Class to open serial connection and communicate with 3MH3 Teslameter"""

    def __init__(self, port='COM4'):
        self.port = port  # set serial port name

        self.ser = serial.Serial()
        self.ser.port = self.port  # set serial port name
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.parity = serial.PARITY_NONE
        self.ser.baudrate = 115200
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.timeout = 1

        # Define available sampling rates
        self.available_rates = [90, 150, 300, 500, 800, 1000]  # list of possible sampling rates / samples per second
        self.rate_codes = ["128", "64", "32", "16", "8", "4"]  # corresponding hex codes

        self.set_rate = 300 # store set rate as variable

        # Define available measurement ranges
        self.available_ranges = [1] # only one range available, +/- 2T

    def unsigned_to_signed(self, value):
        """Take a signed integer and convert to unsigned integer"""
        value_bytes = value.to_bytes(1, byteorder=sys.byteorder, signed=False)
        value_signed = int.from_bytes(value_bytes, byteorder=sys.byteorder, signed=True)
        return value_signed

    def open(self):
        self.ser.open()  # open serial port
        self.ser.write(b'S')  # stop any broadcast
        time.sleep(0.1)
        self.ser.write(b'C')  # set device to calibrated mode
        self.ser.read_until(b'!')  # read response to 'C' command
        self.ser.flushInput()  # Clear input buffer

        self.set_sample_rate(self.set_rate)  # set starting sample rate to default 300 Samples / S

    def type(self):
        """Return string describing Hall probe type"""
        return '3MH3'

    def sample_rates(self):
        """Available sampling rates / Hz"""
        return self.available_rates

    def reject_outliers(self, data, m=6):
        """Function to reject obvious outliers from data array"""
        return data[abs(data - np.mean(data)) < m * np.std(data)]

    def help(self):
        """Sends help command to teslameter and reads response"""
        pass

    def get_fields(self, samples=100):
        """Measure B fields averaged over n samples"""
        message_end = f'{13:02x}'  # end of expected message as hex

        bx_values = []  # empty array to store bx values in
        by_values = []  # empty array to store by values in
        bz_values = []  # empty array to store bz values in
        th_values = []  # empty array to store probe temperature values in

        self.ser.write(b'B') # send broadcast command to read fields

        for i in range(samples):
            t0 = time.time()
            message = []  # list to store bytes of response message in

            self.ser.read_until(b'B')  # read up to first character of message

            for i in range(7):  # read next 7 bytes - full length of expected message
                byte = self.ser.read(1).hex()  # read 1 hexadecimal character
                message.append(byte)
            if message[-1] == message_end:  # if correct last character
                # Calculate Bx field
                Bxl = int(message[0], 16)  # 'Bxl' byte as 16 bit integer
                Bxh = int(message[1], 16)
                Bxh = self.unsigned_to_signed(Bxh)  # transfer high byte into signed integer

                # print(Bxl, Bxh)
                Bx = ((Bxh * 256) + Bxl) / 10
                bx_values.append(Bx)

                # Calculate By field
                Byl = int(message[2], 16)
                Byh = int(message[3], 16)
                Byh = self.unsigned_to_signed(Byh)  # transfer high byte into signed integer
                By = ((Byh * 256) + Byl) / 10
                by_values.append(By)

                # Calculate Bz field
                Bzl = int(message[4], 16)
                Bzh = int(message[5], 16)
                Bzh = self.unsigned_to_signed(Bzh)  # transfer high byte into signed integer
                Bz = ((Bzh * 256) + Bzl) / 10
                bz_values.append(Bz)

                dt = time.time() - t0

        self.ser.write(b'S')  # stop broadcasting data
        time.sleep(0.1)
        self.ser.flushInput()  # Clear input buffer

        bx_ave = np.mean(bx_values)  # bx average
        bx_sd = np.std(bx_values)  # bx standard deviation
        by_ave = np.mean(by_values)  # by average
        by_sd = np.std(by_values)  # by standard deviation
        bz_ave = np.mean(bz_values)  # bz average
        bz_sd = np.std(bz_values)  # bz standard deviation
        th_ave = 0  # Hall probe temperature average not measured by 3MH3
        th_sd = 0  # Hall probe temperature standard deviation not measured by 3MH3
        return [bx_ave, by_ave, bz_ave, bx_sd, by_sd, bz_sd, th_ave, th_sd]


    def set_sample_rate(self, rate):
        """Set Teslameter samples rate (samples per second)"""
        time.sleep(0.1)
        while self.ser.in_waiting != 0:  # while waiting bytes not equal to zero, flush input buffer
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer
            self.ser.flushInput()  # clear input buffer
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer

        if rate in self.available_rates:  # if selected rate is available to be set
            index = self.available_rates.index(rate)  # get index of selected range from list
            message = bytes('A' + self.rate_codes[index] + '\r',
                            encoding='ascii')  # set message in binary for as "A+rate code+termination character"
            # print('message = ', message)
            self.ser.write(message)  # write message to Tesla-meter to set sampling rate
            time.sleep(0.1)
            response = self.ser.read_all().hex()  # read response as hex value
            # print('response = ', response)

            self.set_rate = rate # update internally stored value of sample rate

            return response
        else:
            print('Please choose one of available sample rates: ', self.available_rates)
        pass


    def get_sample_rate(self):
        """Get current Teslameter samples rate (samples per second)"""
        print('currently set same rate = ', self.set_rate)
        return self.set_rate

    def set_range(self, set_range):
        """Set Teslameter measurement range"""
        if set_range in self.available_ranges:  # if selected range is available to be set
            # set range
            response = 0  # response from teslameter
            return response

    def get_range(self):
        """Get current measurement range from Teslameter"""
        # get range
        response = 0  # response from teslameter
        return response

    def port_open(self):
        return self.ser.is_open

    def close(self):
        self.ser.close()  # closes serial port
