# microStabilaze - GUI based software for in-plane microstructure stabilization in optical microscopy via normalized correlation coefficient matching method
- Author: Marek Burakowski (email: marek.burakowski@pwr.edu.pl)
- Coding language: Python

# Hardware compatibility
The microStabilize software is tested with two types of actuators from Thorlabs: Z925B Motorized Actuator controlled by KDC101 and 3-Axis NanoMax™ Flexure Stage controlled by MDT693B - 3-Channel, Open-Loop Piezo Controller. Camera (WAT-902B Watec) is connected to PC via S-Video to USB 2.0 adapter.

# Reqirements, calibration, and installation
microStabilize requires:
- [python](https://www.python.org/downloads/) >= 3.10

The following python packages have to be installed:
- PySimpleGUI (4.60.5)
- opencv-python (4.9.0.80)
- thorlabs_apt (0.2)
- NumPy (1.24.3)
- imutils (0.5.4)
- pygame (2.5.2)

The software was tested with these versions.

A package can be installed with following command:
```
pip install PySimpleGUI==4.60.5 opencv-python==4.9.0.80 thorlabs_apt==0.2 NumPy==1.24.3 imutils==0.5.4 pygame==2.5.2 
```

Calibration:
- If using servo motors from Thorlabs, in microStabilize_settings.txt update serial numbers of motors.

Run software using:
- microStabilize.py


# License
This project is licensed under the GNU General Public License v3.0
See [LICENSE](LICENSE) for details.
