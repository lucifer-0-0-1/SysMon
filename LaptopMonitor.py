""" Create a monitoring app for laptops with consitent effect and database if needed. Should be able to ship and work in all linux systems with minimal RAM usage"""
""" Currently the commands are targetted with acer laptops, may change for different laptop"""
import os
import subprocess
import time

cpu_temperature = subprocess.run("cat /sys/class/hwmon/hwmon5/temp1_input", shell=True)
gpu_temperature = subprocess.run("cat /sys/class/hwmon/hwmon5/temp3_input", shell=True)

cpuFanControl = input("CPUSpeed:")
GpuFanControl = input("GPUSpeed:")
#See how to use sudo commands without password, may create a env variable
subprocess.run("echo 1 | sudo tee /sys/class/hwmon/hwmon5/pwm1_enable",shell=True)
subprocess.run("echo 1 | sudo tee /sys/class/hwmon/hwmon5/pwm2_enable",shell=True)
time.sleep(2)
subprocess.run(f"echo {cpuFanControl} | sudo tee /sys/class/hwmon/hwmon5/pwm1", shell=True)
subprocess.run(f"echo {GpuFanControl} | sudo tee /sys/class/hwmon/hwmon5/pwm2", shell=True)

#Check how to show processes also in the app

process = ...

kill = ... #Button maybe

CpuUsage = ...
GpuUsage = ...

if kill:  #pressed
    subprocess.run(f"kill {process}", shell=True) # may be id

""" Can add some more functionality"""
