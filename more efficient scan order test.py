import numpy as np

order = 0

x0 = 10
x1 = 20
dx = 2

y0 = 5
y1 = 10
dy = 1

z0 = 100
z1 = 500
dz = 100

x_np = int(1 + abs(float(x1) - float(x0)) / float(dx))  # number of intervals along x
x_values = np.linspace(float(x0), float(x1), x_np)  # array of x coordinate values
y_np = int(1 + abs(float(y1) - float(y0)) / float(dy))  # number of intervals along x
y_values = np.linspace(float(y0), float(y1), y_np)  # array of x coordinate values
z_np = int(1 + abs(float(z1) - float(z0)) / float(dz))  # number of intervals along x
z_values = np.linspace(float(z0), float(z1), z_np)  # array of x coordinate values

print('x values = ', x_values)
print('y values = ', y_values)
print('z values = ', z_values)

if order == 0:  # xyz
    positions = [x_values, y_values, z_values]
elif order == 1:  # xzy
    positions = [x_values, z_values, y_values]
elif order == 2:  # yzx
    positions = [z_values, y_values, x_values]
elif order == 3:  # yxz
    positions = [y_values, x_values, z_values]
elif order == 4:  # zxy
    positions = [z_values, x_values, y_values]
elif order == 5:  # zyx
    positions = [z_values, y_values, x_values]

for i in range(len(positions[2])):
    print('Move motor 3! to ', positions[2][i])
    for j in range(len(positions[1])):
        print('Move motor 2! to ', positions[1][j])
        for k in range(len(positions[0])):
            print('Move motor 1! to position = ', positions[0][k])
        positions[0] = np.flip(positions[0])  # reverse order of axis 1 to reduce total distance and time
    positions[1] = np.flip(positions[1]) # reverse order of axis 2 to reduce total distance and time
