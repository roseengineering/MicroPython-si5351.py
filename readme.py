
import subprocess 

def run(command, language="bash"):
    proc = subprocess.Popen("PYTHONPATH=. " + command, shell=True, stdout=subprocess.PIPE)
    buf = proc.stdout.read().decode()
    proc.wait()
    return f"""
```{language}
$ {command}
{buf}\
```
"""

print(f"""

# SI5351 Micropython library

This repo contains another of my adaptation of the Adafruit si5351 library
at https://github.com/adafruit/Adafruit_Si5351_Library.
This time it is for micropython.

The example below sets clock output 0 to 13.703704 MHz.

```
from machine import Pin, I2C
import si5351

PIN_SCL = 5
PIN_SDA = 4

i2c = I2C(-1, Pin(PIN_SCL), Pin(PIN_SDA))

si = si5351.SI5351_I2C(i2c)

# vco = 25 MHz * (24 + 2 / 3) = 616.67 MHz
si.setupPLL(si.PLL_A, 24, 2, 3)

# out = 616.67 MHz / 45 = 13.703704 MHz 
si.setupMultisynth(0, si.PLL_A, 45)

# uncomment to divide 13.703704 by 64
# si.setupRdiv(0, si.R_DIV_64)

si.enableOutputs(True)
```

I added an addition function called set_freq.  
The function calculates and sets the multisynth and R dividers
based on the VCO frequency of the PLL in use.
It only works for frequencies below about 100Mhz.

Here is an example:

```
...
# vco = 25 MHz * 32 = 800 MHz
si.setupPLL(si.PLL_A, 32)


si.set_freq(clk, si.PLL_A, 7000000)
si.enableOutputs(True)
```

The example program example.py is also provided.  
It was designed for the Heltec ESP8266 WIFIKIT Version A.
Attach a rotary knob to GPIO pins 12 and 13.  Use GPIO
pins 4 and 5 for SDA and SCL on the SI5351.  On
boot clock 0 will output 7Mhz.  Turning the knob will change
clock 0's frequency in 10 Hz steps.

{ run("cat example.py", "python") }

""")


