import serial
import numpy as np
import time
import struct


class teslameter_3MH6:
    """Class to open serial connection and communicate with Senis 3MH6 Teslameter"""

    def __init__(self, port):
        self.port = port  # set serial port name

        self.ser = serial.Serial()
        self.ser.port = self.port  # set serial port name
        self.ser.baudrate = 3E6  # set baud rate
        self.ser.timeout = 1  # set timeout

        # Define available sampling rates and corresponding hex codes
        self.available_rates = [10, 30, 50, 60, 100, 500, 1E3, 2E3, 3.75E3, 7.5E3,
                                15E3]  # list of possible sampling rates
        self.rate_codes = ["23", "53", "63", "72", "82", "92", "A1", "B0", "C0", "D0", "E0"]  # corresponding hex codes
        self.rate_return_codes = ["23", "53", "63", "72", "82", "92", "a1", "b0", "c0", "d0",
                                  "e0"]  # corresponding hex codes

        # Define available measurement ranges:
        self.available_ranges = [1, 2, 3, 4]  # list of available measurement ranges


    def open(self):
        self.ser.open()  # open serial port
        self.ser.write(b'S')  # stop any broadcast
        self.ser.write(b'C')  # set device to calibrated mode
        time.sleep(0.1)  # wait for calibration message to be sent and responded to
        self.ser.flushInput()  # Clear input buffer

    def type(self):
        """Return string describing Hall probe type"""
        return '3MH6'

    def sample_rates(self):
        """Available sampling rates / Hz"""
        return [10, 30, 50, 60, 100, 500, 1E3, 2E3, 3.75E3, 7.5E3,
                                15E3]

    def reject_outliers(self, data, m=6):
        """Function to reject obvious outliers from data array"""
        return data[abs(data - np.mean(data)) < m * np.std(data)]

    def help(self):
        """Sends help command to teslameter and reads response"""
        self.ser.flushInput()  # Clear input buffer
        self.ser.write(b'h')  # send help command
        response = self.ser.readall().decode('ascii')  # read response from Tesla-meter and decode to ascii
        print(response)  # print response to console

    def get_fields(self, samples):
        """Measure B fields averaged over n samples"""
        self.ser.write(b'S')  # stop any broadcasting before sending broadcast signal
        # print('Getting fields')
        time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer
        self.ser.flushInput()
        time.sleep(0.2)
        # print('Check if buffer clear')

        # sample_rate = self.get_sample_rate()

        # print('waiting = ', self.ser.in_waiting)
        while self.ser.in_waiting != 0:  # while waiting bytes not equal to zero, flush input buffer
            #print('waiting to clear HP buffer')
            self.ser.write(b'S')
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer
            self.ser.flushInput()  # clear input buffer
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer
            # print(self.ser.in_waiting)

        # print('sample rate =', sample_rate)

        if type(samples) == int and samples > 0:  # if samples given is integer > 0
            bx_values = []  # empty array to store bx values in
            by_values = []  # empty array to store by values in
            bz_values = []  # empty array to store bz values in
            th_values = []  # empty array to store probe temperature values in
            # print('writing to tesla-meter')
            self.ser.write(b'B')  # send broadcast command to tesla-meter
            # print('wrote to tesla-meter')
            #for i in range(samples):  # read n data packets
            while len(bx_values) < samples: # read n samples
                # print('i = ', i)
                if self.ser.in_waiting == 0:  # if whole number of signals read, wait
                    time.sleep(0.1)  # wait long enough for more data to be sent
                    #print('wait')
                else:
                    pass
                    #print('do not wait')
                packet = self.ser.read(25).hex()  # read 25 bytes as hex value (one data package)
                # print('read packet', packet)
                start_character_hex = packet[0:2] # expect data packet to start with "42"
                end_character_hex = packet[-2:]  # expect data packet to end with "0d"
                if start_character_hex == '42' and end_character_hex == '0d': #if correct starting and end character
                    # Separate bx data and calculate float value
                    bx_hex = packet[2:10]  # separate bx byte values from string
                    bx = struct.unpack('>f', bytes.fromhex(bx_hex))[0]  # convert Hex value to float
                    bx_values.append(bx)  # store value in array
                    # Separate Hall probe temperature data
                    th_hex = packet[10:18]  # separate th byte values from string
                    th = struct.unpack('>f', bytes.fromhex(th_hex))[0]  # convert Hex value to float
                    th_values.append(th)  # store value in array
                    # Separate by data and calculate float value
                    by_hex = packet[18:26]  # separate by byte values from string
                    by = struct.unpack('>f', bytes.fromhex(by_hex))[0]  # convert Hex value to float
                    by_values.append(by)  # store value in array
                    # Separate bz data and calculate float value
                    bz_hex = packet[26:34]  # Separate bz byte values from string
                    bz = struct.unpack('>f', bytes.fromhex(bz_hex))[0]  # convert Hex value to float
                    bz_values.append(bz)
                else: # if not correct starting byte - clear buffer
                    while self.ser.in_waiting != 0:  # while waiting bytes not equal to zero, flush input buffer
                        self.ser.write(b'S') # stop broadcast so can clear input buffer
                        time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer
                        self.ser.flushInput()  # clear input buffer
                        time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer
                    self.ser.write(b'B')  # re-send broadcast command to tesla-meter

            self.ser.write(b'S')  # stop broadcast
            # print('Stopped broadcast')

            # reject outliers from arrays
            bx_values = np.asarray(bx_values) # turn list to array
            bx_values = self.reject_outliers(bx_values) # reject obvious outliers
            by_values = np.asarray(by_values) # turn list to array
            by_values = self.reject_outliers(by_values) # reject outliers
            bz_values = np.asarray(bz_values) # list to array
            bz_values = self.reject_outliers(bz_values) # reject outliers
            th_values = np.asarray(th_values) # list to array
            th_values = self.reject_outliers(th_values) # reject outliers

            bx_ave = np.mean(bx_values)  # bx average
            bx_sd = np.std(bx_values)  # bx standard deviation
            by_ave = np.mean(by_values)  # by average
            by_sd = np.std(by_values)  # by standard deviation
            bz_ave = np.mean(bz_values)  # bz average
            bz_sd = np.std(bz_values)  # bz standard deviation
            th_ave = np.mean(th_values)  # Hall probe temperature average
            th_sd = np.std(th_values)  # Hall probe temperature standard deviation
            return [bx_ave, by_ave, bz_ave, bx_sd, by_sd, bz_sd, th_ave, th_sd]
        else:
            print('Please enter valid number of samples to use in average')

    def set_sample_rate(self, rate):
        """Set Teslameter samples rate (samples per second)"""
        time.sleep(0.1)
        while self.ser.in_waiting != 0:  # while waiting bytes not equal to zero, flush input buffer
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer
            self.ser.flushInput()  # clear input buffer
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer

        if rate in self.available_rates:  # if selected rate is available to be set
            index = self.available_rates.index(rate)  # get index of selected range from list
            message = bytes('K' + self.rate_codes[index],
                            encoding='ascii')  # set message in binary for as "K+rate code"
            self.ser.write(message)  # write message to Tesla-meter to set sampling rate
            time.sleep(0.1)
            response = self.ser.read_all().hex()  # read response as hex value
            code = str(response)[2:4]  # extract rate code value
            set_rate = self.available_rates[self.rate_return_codes.index(code)]  # get corresponding sample rate
            # print('Sample rate set to ', set_rate) #print sample rate to console
            return set_rate
        else:
            print('Please choose one of available sample rates: ', self.available_rates)

    def get_sample_rate(self):
        """Get current Teslameter samples rate (samples per second)"""
        time.sleep(0.1)
        while self.ser.in_waiting != 0:  # while waiting bytes not equal to zero, flush input buffer
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer
            self.ser.flushInput()  # clear input buffer
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer

        self.ser.write(b"K?")  # write message to Tesla-meter to query sampling rate
        time.sleep(0.1)
        response = self.ser.read_all().hex()  # read response as hex value
        code = str(response)[2:4]  # extract rate code value
        set_rate = self.available_rates[self.rate_return_codes.index(code)]  # get corresponding sample rate
        # print('Sample rate is currently ', set_rate)  # print sample rate to console
        return set_rate

    def set_range(self, set_range):
        """Set Teslameter measurement range"""
        time.sleep(0.1)
        while self.ser.in_waiting != 0:  # while waiting bytes not equal to zero, flush input buffer
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer
            self.ser.flushInput()  # clear input buffer
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer

        if set_range in self.available_ranges:  # if selected range is available to be set
            index = self.available_ranges.index(set_range)  # get index of selected range from list
            message = bytes('mr' + str(self.available_ranges[index]),
                            encoding='ascii')  # set message in binary for as "mr+range number"
            self.ser.write(message)  # write message to Tesla-meter to set measurement range
            time.sleep(1)
            response = self.ser.read_all().decode('ascii')  # read response as hex value
            # print('Range set to: ', response)
            return response

    def get_range(self):
        """Get current measurement range from Teslameter"""
        time.sleep(0.1)
        while self.ser.in_waiting != 0:  # while waiting bytes not equal to zero, flush input buffer
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer
            self.ser.flushInput()  # clear input buffer
            time.sleep(0.2)  # Sleep long enough to add waiting commands to input buffer

        self.ser.write(b"amr?")  # write message to Tesla-meter to query measurement range
        time.sleep(0.1)
        response = self.ser.read_all().decode('ascii')  # read response as ascii value
        # print('Current measurement range = ', response)
        return response

    def port_open(self):
        return self.ser.is_open


    def close(self):
        self.ser.close()  # closes serial port
