import serial
import numpy as np
import time
import struct


class teslameter_blank:
    """Blank teslameter class"""

    def __init__(self):
        pass

        # Define available sampling rates 

        # Define available measurement ranges

    def type(self):
        """Return string describing Hall probe type"""
        return 'blank'

    def sample_rates(self):
        """Available sampling rates / Hz"""
        return []

    def reject_outliers(self, data, m=2):
        """Function to reject obvious outliers from data array"""
        return data[abs(data - np.mean(data)) < m * np.std(data)]

    def help(self):
        """Sends help command to teslameter and reads response"""
        pass

    def get_fields(self, samples=0):
        """Measure B fields averaged over n samples"""
        return 8*[0]


    def set_sample_rate(self, rate):
        """Set Teslameter samples rate (samples per second)"""
        
        if rate in self.available_rates:  # if selected rate is available to be set
            # Set sample rate
            set_rate = 0
            return set_rate
        else:
            print('Please choose one of available sample rates: ', self.available_rates)

    def get_sample_rate(self):
        """Get current Teslameter samples rate (samples per second)"""
        
        set_rate = 0

        return set_rate

    def set_range(self, set_range):
        """Set Teslameter measurement range"""
        if set_range in self.available_ranges:  # if selected range is available to be set
            #set range
            response = 0 # response from teslameter
            return response

    def get_range(self):
        """Get current measurement range from Teslameter"""
        # get range
        response = 0 #response from teslameter
        return response

    def port_open(self):
        return self.ser.is_open

    def open(self):
        """Open connection to Teslameter"""
        pass

    def close(self):
        """Close connection to Teslamater"""
        pass