import serial
from time import sleep, time
import re
from typing import Union

qa_pair = re.compile(r' {2,}(?![= \-\d])')
pair_split = re.compile('[:=]')
query_params = re.compile(r'\s+([\w\s]+?) *?[=:]\s*([\w\d-]+)')
truthy_dict = {'enabled': True, 'disabled': False, 'on': True, 'off': False}
name_map = {'actual pos': 'actual position', 'command pos': 'command position', 'autoexec': 'auto execute',
            'fast jog': 'fast jog speed', 'lower limit': 'lower soft limit', 'upper limit': 'upper soft limit',
            'settling': 'settling time', 'settle time': 'settling time', 'tracking': 'tracking window'}


class OutOfRangeException(Exception):
    """Raise when the user tries to set a parameter out of range."""


class Axis:
    def __init__(self, serial_port, axis_id, scale_factor, max_speed, acceleration, axis_type='linear',
                 version='PM1000'):
        """Initialise axis with some parameters."""
        self.serial_port = serial_port
        self.id = axis_id  # axis id number starting with 1
        self.scale_factor = scale_factor  # steps per mm or steps per degree
        self.max_speed = max_speed  # mm/s or deg/s
        self.acceleration = acceleration  # mm/s/s or deg/s/s
        self.type = axis_type  # 'linear' or 'rotation'
        self.units = 'mm' if type == 'linear' else 'degrees'
        self.version = version  # motor controller version
        # What prefix do we expect to see on responses? PM341: 01# etc. PM600: 10: etc. PM304: nothing
        if version == 'PM304':
            self.prefix = ''
        elif version == 'SCL':
            self.prefix = str(self.id)
        else:
            self.prefix = '{:02d}{}'.format(self.id, '#' if version == 'PM341' else ':')
        self.line_end = b'\r' if version == 'SCL' else b'\r\n'  ###carriage return value
        self.echo = True if self.version == 'PM1000' else False  # version != 'SCL'

    def talk(self, command: str, parameter: Union[str, int, float] = '',
             multi_line: bool = False, check_ok: bool = False, bytes = 16384):
        """Send a command to the motor controller and wait for a response."""
        command = command.upper()  # need upper for SCL, other versions don't care
        # Coerce floats to ints (assuming there aren't any float-type commands!)
        if isinstance(parameter, float):
            parameter = round(parameter)
        send = '{}{}{}'.format(self.id, command, parameter)
        self.serial_port.write(send.encode('utf-8') + self.line_end)

        # Old read method - some data loss
        """reply = ''
        while reply.count(self.line_end.decode('utf-8')) < (1):
            sleep(2 if command.lower() in ('qa', 'he', 'hc') else 0.2)  # longer for certain commands
            reply += self.serial_port.read_all().decode('utf-8')
        lines = reply.splitlines()"""

        # New read method - needs to set timeout = 1 s
        rx_buf = [self.serial_port.read(bytes).decode('utf-8')]  # Try reading a large chunk of data, blocking for timeout secs.
        while True:  # Loop to read remaining data, to end of receive buffer.
            pending = self.serial_port.inWaiting()
            if pending:
                rx_buf.append(self.serial_port.read(pending).decode('utf-8'))  # Append read chunks to the list.
            else:
                break
        rx_data = ''.join(rx_buf)  # Join the chunks, to get a string of serial data.
        lines = rx_data.splitlines() # split data into lines
        lines[1: 3] = [''.join(lines[1: 3])]

        #print('reply = ', lines)

        if self.echo:
            echo = lines.pop(0)
            if not echo == send:  # check the command echo
                # maybe retry?
                raise ValueError('Incorrect command echo: sent "{}", received "{}"'.format(send, echo))
        if check_ok and not lines[0] == self.prefix + ('%' if self.version == 'SCL' else 'OK'):
            raise ValueError('Error response on command "{}": received "{}"'.format(send, lines[0]))
        return lines if multi_line else lines[0]

    def get_position(self, set_value=True):  # ask for the set value by default, otherwise the read value
        """Query the motor controller for the axis position (set or read)."""
        if self.version == 'SCL':
            command = 'ie'  # TODO: set position?
        else:
            command = 'oc' if set_value else 'oa'  # "output command", "output actual"

        while True:
            try:
                reply = self.talk(command, bytes=22)  # "output command", "output actual", #only need to read 22 bytes to get position
                #print(reply)
                # reply should begin either CP=, AP= or 01#, 02#, ...
                if self.version == 'PM304':
                    prefix = 'CP=' if set_value else 'AP='
                else:
                    prefix = self.prefix
                if not reply.startswith(prefix):
                    raise ValueError('Bad reply from axis {}: "{}" does not begin "{}"'.format(self.id, reply, prefix))
                if self.version == 'SCL':
                    answer = reply[4:]
                else:
                    answer = reply[3:]
                try:
                    value = int(answer)
                except ValueError:
                    value = 0
                #print('value = ', value)
                #print('scale factor = ', self.scale_factor)
                return value / self.scale_factor
            except:
                print('was a value error - try again')
                pass

    def move(self, position, relative=False, wait=False, tolerance=0.01, timeout='auto'):
        """Instruct the motor controller to move the axis by the specified amount."""
        init_pos = self.get_position()
        final_pos = position + (init_pos if relative else 0)
        if wait and timeout == 'auto':
            timeout = abs(final_pos - init_pos) / self.max_speed + 60  # allow extra time  # TODO: should query speed

        steps = int(position * self.scale_factor)
        if self.version == 'SCL':
            command = 'fl' if relative else 'fp'  # "feed to length", "feed to position"
        else:
            command = 'mr' if relative else 'ma'  # "move relative", "move absolute"
        try:
            self.talk(command, steps, check_ok=True)
        except ValueError as e:
            print('Raised value error: ', e)
            raise ValueError

        if wait:
            start = time()
            sleep(0.1)
            while abs(self.get_position() - final_pos) > tolerance:
                #print(self.get_position())
                sleep(0.1)
                if time() - start > timeout:
                    raise TimeoutError('Timed out waiting for axis {} to reach position {}'.format(self.id, final_pos))
            # sleep(0.2)  # extra delay so we don't confuse the controller

    def stop(self):
        """Stop the motor immediately."""
        self.talk('st')  # "stop"

    def resetPosition(self, position=0):
        """Reset the command and actual positions to the value specified."""
        try:
            steps = int(position * self.scale_factor)
            self.talk('cp', steps, check_ok=True)  # "command position"
            self.talk('ap', steps, check_ok=True)  # "actual position"
        except ValueError: # raised when trying to reset posiiton in closed loop mode
            print('Cannot reset position when using absolute encoder')

    def setLimits(self, limits=None):
        """Set soft limits, or instruct the controller to ignore them."""
        if limits is None:  # turn limits off
            if self.version == 'PM600':  # can't disable limits - just set them really big
                limits = (-9999999, 9999999)
            elif self.version == 'PM1000':
                print('Cannot turn soft limits off')
                return
            else:
                self.talk('il', check_ok=True)  # "inhibit limits"
                return
        print(limits)
        lower_limit = min(limits) * self.scale_factor
        upper_limit = max(limits) * self.scale_factor
        if self.version != 'PM600' and self.version != 'PM1000':
            self.talk('al', check_ok=True)  # "allow limits"
        try:
            self.talk('ll', lower_limit, check_ok=True)  # "lower limit"
        except ValueError:
            print('Lower limit out of range')
        try:
            self.talk('ul', upper_limit, check_ok=True)  # "upper limit"
        except ValueError:
            print('Upper limit out of range')

    def getSpeed(self):
        """Return the slew speed."""
        if self.version == 'SCL':
            return abs(float(self.talk('ve')[4:]) * float(self.talk('er')[4:]) / self.scale_factor)
        else:
            while True:
                try:
                    return self.queryAll()['slew speed'] / self.scale_factor
                except:
                    pass

    def setSpeed(self, speed=2):
        """Set the slew speed; the default None sets the maximum speed."""
        if speed is None:
            speed = self.max_speed
        elif speed > self.max_speed:
            raise OutOfRangeException(f'Requested speed {speed} mm/s is higher than maximum {self.max_speed} mm/s.')
        try:
            self.talk('sv', speed * self.scale_factor, check_ok=True)
        except:
            print('Value error on response - is this a problem?')

    def queryAll(self):
        """Query all axis parameters and return the result as a dict."""
        while True:  # loop until dictionary output is successful
            try:
                reply = self.talk('qa', multi_line=True)  # "query all"
                # ('reply = ', reply)
                sleep(0.1)
                output_dict = {}
                for line in reply[1:]:  # skip the first line
                    # print('line =', line)
                    pairs = qa_pair.split(line.strip())  # split the line into pairs of params (usu 2 but can be more)
                    # print('pairs = ', pairs)
                    for pair in pairs:
                        pair_array = pair_split.split(pair)
                        # print('pair_array = ', pair_array)
                        if len(pair_array) < 2:  # no "=" or ":" found
                            pair_array = pair.rsplit(' ',
                                                     maxsplit=1)  # Use only the last word as the value, and the rest as the name
                        name = pair_array[0].strip().lower()  # use lowercase names in the dict
                        try:
                            name = name_map[name]  # try to standardise names across MC versions
                        except KeyError:
                            pass  # no translation? just use the name as provided
                        # print(pair_array)
                        value = pair_array[1].strip()
                        try:
                            base = 2 if name in ('read port', 'last write') else 10  # these two are binary values
                            out_value = int(value, base)  # try to interpret as an integer
                        except ValueError:
                            try:
                                out_value = truthy_dict[
                                    value.lower()]  # try to interpret Enabled/Disabled/On/Off as True/False
                            except KeyError:
                                out_value = value.lower()  # just use the string value
                        output_dict[name] = out_value
                # print('That worked!')
                return output_dict
            except:
                # print('error here')
                pass

    def getLimits(self):
        """Return the soft limits, or None if they are off."""
        while True:  # loop until limits returned successfully
            try:
                qa = self.queryAll()
                # can't turn limits off on PM600
                if self.version == 'PM600' or 'PM1000' or qa['soft limits']:
                    return qa['lower soft limit'] / self.scale_factor, qa['upper soft limit'] / self.scale_factor
                else:
                    return None
            except:
                print('name error')
                pass

    def hardLimits(self):
        """Return True if axis is at hard limit"""
        reply = self.talk('os', bytes=18) # send "output status" command to controller
        if reply[5] == '0':
            return False # axis not at hard limit
        elif reply[5] == '1':
            return True # axis is at hard limit


# Define the interface to the McLennan motor controller


class MotorController:
    def __init__(self):
        serial_port = serial.Serial()
        self.serial_port = serial_port
        serial_port.port = 'COM1'
        serial_port.bytesize = 7
        serial_port.parity = serial.PARITY_EVEN
        serial_port.baudrate = 38400
        serial_port.timeout = 1 # needs short timeout for read without data loss
        # serial_port.timeout = 0.1 # returns all bytes received until timeout - small number = quick response
        serial_port.open()

        hpx = Axis(serial_port, 3, 3200, 6,
                   0.5)  # serial_port, axis_id, scale_factor, max_speed, acceleration, axis_type='linear', version='PM341'
        hpy = Axis(serial_port, 4, 3200, 6, 0.75)
        hpz = Axis(serial_port, 5, 1000, 50, 10)

        # all lowercase
        self.axis = {'hp y': hpy, 'hp x': hpx, 'hp z': hpz, 'y': hpy, 'x': hpx, 'z': hpz,  # allow aliases for HP axes
                     'fc x2': Axis(serial_port, 8, 3200, 5, 2.5),
                     'fc y2': Axis(serial_port, 9, 3200, 3, 1.5),
                     'fc x1': Axis(serial_port, 6, 3200, 5, 2.5),
                     'fc y1': Axis(serial_port, 7, 3200, 3, 1.5),
                     'fc theta 2': Axis(serial_port, 12, 1048576 / 360, 12, 30, axis_type='rotation'),
                     'fc theta 1': Axis(serial_port, 11, 1048576 / 360, 12, 30, axis_type='rotation'),
                     'py': Axis(serial_port, 2, 3200, 6, 6),
                     'px': Axis(serial_port, 1, 3200, 6, 6),
                     'fc z2': Axis(serial_port, 10, 4000, 6, 2)}

    def close(self):
        """Close the serial port - we're finished with it."""
        self.serial_port.close()

    def __del__(self):
        self.close()


class ZeptoDipoleController(MotorController):
    def __init__(self):
        serial_port = serial.Serial()
        self.serial_port = serial_port
        serial_port.port = 'COM8'
        serial_port.bytesize = 8
        serial_port.parity = serial.PARITY_NONE
        serial_port.open()

        # speed is 2 rev/s (VE command)
        # accel is 50 rev/s/s (AC command)
        # 20000 steps/rev
        # 240000 steps/mm
        # so speed = 1/6 mm/s, accel = 50 / 12 mm/s/s
        self.axis = {'s': Axis(serial_port, 1, -240000, 1 / 6, 50 / 12, version='SCL')}
