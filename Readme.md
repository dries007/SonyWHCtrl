# SonyWHCtrl

A **third party** control application for Sony wireless headsets.

Tested on hardware:

+ WH-1000XM3 

## Disclaimer

This software is not affiliated with Sony. Use at your own risk.

## Acknowledgment

This package would not be possible without the code from [Plutoberth's SonyHeadphonesClient](https://github.com/Plutoberth/SonyHeadphonesClient).

## Dependencies

Install the packages listed in [requirements.txt](./requirements.txt).
You may have to install a few system dependencies to get some of them to compile, see their respective websites for more info.

## Documentation

Run script with --help for documentation, but here is a printout for the lazy:

```
usage: SonyHWCtrl [-h] [--fov] [--asl ASL] [--mac MAC]

Control your Sony Headphones from the command line.

optional arguments:
  -h, --help  show this help message and exit
  --fov       Enable 'Focus on Voice' mode. Only available if asm >= 2.
  --asl ASL   Set 'Ambient Sound Level'. 0 and 1 are marked as 'noise
              suppression' in the app. Maximum is 19.
  --mac MAC   Specify the mac address of the device you want to control. Not
              required if there is only 1 valid device connected.

DISCLAIMER: USE AT OWN RISK. THIRD PARTY TOOL. NOT AFFILIATED WITH SONY.

Process finished with exit code 0
```

For developers, read the script.
