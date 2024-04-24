function MatlabTest

% warning off MATLAB:loadlibrary:functionnotfound

loadlibrary A3mtslib64 A3mtsdll.h

number_of_devices = 0;
[Status, number_of_devices] = calllib( 'A3mtslib64', 'count_devices', number_of_devices);

if ~Status
    DeviceNr   = 0;
    DeviceName = blanks(100);
    [Status, DeviceNr, DeviceName] = calllib( 'A3mtslib64', 'get_device_name_ch', DeviceNr, DeviceName );
end
if ~Status
 fprintf(1,'DeviceNr   = %d\n', double(DeviceNr));
 fprintf(1,'DeviceName = \"%s\"\n', DeviceName);
%  DeviceNr   = 0;
%  FWert = blanks(100);
%  [Status, DeviceNr, FWert] = calllib( 'A3mtslib64', 'get_firmware_version_ch', DeviceNr, FWert );
end
if ~Status
      [Status, DeviceNr] = calllib( 'A3mtslib64', 'open_device', DeviceNr );  
end
if ~Status
%  fprintf(1,'DeviceNr = %d\n', double(DeviceNr));
%  fprintf(1,'Firmware = \"%s\"\n', FWert);
 Zeit = 0;
 X = 0;
 Y = 0;
 Z = 0;
 [Status, DeviceNr, Zeit, X, Y, Z ] = calllib( 'A3mtslib64', 'get_sensor_values_fl', DeviceNr, Zeit, X, Y, Z  );
end
if ~Status
 fprintf(1,'DeviceNr = %d\n', double(DeviceNr));
 fprintf(1,'Zeit     = %d\n', double(Zeit));
 fprintf(1,'X        = %d\n', double(X));
 fprintf(1,'Y        = %d\n', double(Y));
 fprintf(1,'Z        = %d\n', double(Z));
end
if ~Status
      [Status, DeviceNr] = calllib( 'A3mtslib64', 'close_device', DeviceNr );  
end

unloadlibrary A3mtslib64