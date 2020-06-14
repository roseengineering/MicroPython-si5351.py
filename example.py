
from machine import Pin, I2C
from si5351 import SI5351_I2C
from ssd1306 import SSD1306_I2C
import time

def latch2(p0, p1):
    a, b = p0.value(), p1.value()
    while True:
        a_last, b_last = a, b
        time.sleep_us(10)
        a, b = p0.value(), p1.value()
        if a == a_last and b == b_last: return a, b


class Encoder:
    """
      ---     ---     ---            ---     ---     ---
     |   |   |   |   |   |     A    |   |   |   |   |   |  
    -     ---     ---     -        -     ---     ---     --
    ---     ---     ---                ---     ---     ---
       |   |   |   |   |       B      |   |   |   |   |   | 
        ---     ---     ---        ---     ---    ---  
          Turn Left                       Turn right
          A 1 1 0 0 1                     A 1 1 0 0 1
          B 1 0 0 1 1                     B 0 1 1 0 0
    """

    def __init__(self, pina, pinb, handler):
        self.pina = pina
        self.pinb = pinb
        self.handler = handler
        self.position = 0
        self.last_a = latch2(self.pina, self.pinb)[0]
        self.pina.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.ontrigger)

    def ontrigger(self, *args):
        a, b = latch2(self.pina, self.pinb)
        if a == 1 and self.last_a == 0:
            self.position += 1 if a == b else -1
            self.handler(self.position)
        self.last_a = a


# gpio pins

PIN_SCL = 5
PIN_SDA = 4
PIN_A   = 13
PIN_B   = 12
PIN_C   = 14

# constants

center = 7000000
mult = 32
clk = 0

# functions

def onchange(value):
    freq = center + value * 10
    oled.fill(0)
    oled.text('{:d} Hz'.format(freq), 0, 0)
    oled.show()
    si.set_freq(clk, si.PLL_A, freq)

# i2c bus

i2c = I2C(-1, Pin(PIN_SCL), Pin(PIN_SDA))

# oled

oled = SSD1306_I2C(128, 32, i2c)

# si5351 frequency generator

si = SI5351_I2C(i2c)
si.setupPLL(si.PLL_A, mult)
onchange(0)
si.enableOutputs(True)

# rotary encoder

Encoder(Pin(PIN_A, Pin.IN, Pin.PULL_UP), 
        Pin(PIN_B, Pin.IN, Pin.PULL_UP),
        onchange)

while True:
   pass

