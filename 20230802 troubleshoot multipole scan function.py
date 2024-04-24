import motor_controller_PM1000
import numpy as np

mc = motor_controller_PM1000.MotorController()
xa = mc.axis['x']  # x axis on Hall probe bench
ya = mc.axis['y']
za = mc.axis['z']

xa = mc.axis['x']
ya = mc.axis['y']
za = mc.axis['z']
x0 = -16.663  # x centre of circle
y0 = 14.216  # y centre of circle
r0 = 0.3  # radius of circle
steps = 16  # number of steps around circle
z0 = 3780  # start z
z1 = 3780  # end z
dz = 1  # z interval

x_lims = xa.getLimits()
y_lims = ya.getLimits()
z_lims = za.getLimits()
x_lower = (x_lims[0])
x_upper = (x_lims[1])
y_lower = (y_lims[0])
y_upper = (y_lims[1])
z_lower = (z_lims[0])
z_upper = (z_lims[1])
print('limits found')
# Check movement is in soft limit range and raise exception if not
if x0 - r0 < x_lower or x0 + r0 > x_upper:
    print('oh no outside soft limits')
    raise Exception

if y0 - r0 < y_lower or y0 + r0 > y_upper:
    print('oh no outside soft limits')
    raise Exception

if z1 < z_lower or z1 > z_upper:
    print('oh no outside soft limits')
    raise Exception


theta_values = np.linspace(0, 2 * np.pi, int(steps), endpoint=False)  # values of theta
z_np = int(1 + abs(float(z1) - float(z0)) / float(dz))  # number of intervals along x
print('z0, z1, dz, np = ', z0, z1, dz, z_np)
z_values = np.linspace(float(z0), float(z1), z_np)  # array of x coordinate values
print('z values = ', z_values)

for j in range(len(theta_values)):
    print('Move to angular position!')

    x_pos = round(x0 + r0 * np.cos(theta_values[j]), 3)  # new x coordinate to 3 d.p.
    y_pos = round(y0 + r0 * np.sin(theta_values[j]), 3)  # new y coordinate to 3 d.p.

    print('x pos = ', x_pos)
    print('y pos = ', y_pos)

    # try:
    #     # if 0 < theta_values[j] < np.pi / 2 or np.pi < theta_values[j] < 3 * np.pi / 2:
    #     #     xa.move(x_pos, wait=True)  # move x axis, wait til reach position
    #     #     # ya.move(y_pos, wait=True)  # move y axis, wait til reach position
    #     # else:
    #     #     # ya.move(y_pos, wait=True)  # move y axis, wait til reach position
    #     #     xa.move(x_pos, wait=True)  # move x axis, wait til reach position
    # except ValueError:
    #     print('hmm')

    xa.move(x_pos, wait=True)  # move x axis, wait til reach position
    ya.move(y_pos, wait=True)  # move y axis, wait til reach position

    print('read the positions')
    # Read motor controller positions
    x = xa.get_position()
    y = ya.get_position()
    z = za.get_position()

    print('Position = ', x, y, z)






mc.close()