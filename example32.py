
from micropython import const
from machine import Pin, I2C
from si5351 import SI5351_I2C
import bluetooth
import struct
import time


# gatt advertising

_ADV_APPEARANCE_GENERIC_COMPUTER = const(128)
_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_UUID32_COMPLETE = const(0x5)
_ADV_TYPE_UUID128_COMPLETE = const(0x7)
_ADV_TYPE_APPEARANCE = const(0x19)

def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    payload = bytearray()
    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack("BB", len(value) + 1, adv_type) + value
    _append(
        _ADV_TYPE_FLAGS,
        struct.pack("B", (0x01 if limited_disc else 0x02) + (0x18 if br_edr else 0x04)),
    )
    if name:
        _append(_ADV_TYPE_NAME, name)
    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(_ADV_TYPE_UUID16_COMPLETE, b)
            elif len(b) == 4:
                _append(_ADV_TYPE_UUID32_COMPLETE, b)
            elif len(b) == 16:
                _append(_ADV_TYPE_UUID128_COMPLETE, b)
    _append(_ADV_TYPE_APPEARANCE, struct.pack("<h", appearance))
    return payload


# gatt uart service

_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX = (
    bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"),
    bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
)
_UART_RX = (
    bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"),
    bluetooth.FLAG_WRITE,
)
_UART_SERVICE = (
    _UART_UUID,
    (_UART_TX, _UART_RX,),
)

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(4)

class BLEUART:
    def __init__(self, ble, name="bluefo"):
        self._handler = None
        self._connections = set()
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(handler=self._irq)
        ((self._tx_handle, self._rx_handle,),) = self._ble.gatts_register_services((_UART_SERVICE,))
        self._payload = advertising_payload(
            name=name, 
            appearance=_ADV_APPEARANCE_GENERIC_COMPUTER)
        self._advertise()

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle in self._connections:
                self._connections.remove(conn_handle)
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            data = self._ble.gatts_read(value_handle)
            if self._handler:
                self._handler(data)

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)

    def irq(self, handler):
        self._handler = handler

    def write(self, data):
        self._ble.gatts_write(self._tx_handle, data)
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._tx_handle, data)


# rotary encoder

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

    def __init__(self, pina, pinb):
        self.pina = pina
        self.pinb = pinb
        self.position = 0
        self._handler = None
        self.last_a = latch2(self.pina, self.pinb)[0]
        self.pina.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._on_trigger)

    def _on_trigger(self, *args):
        a, b = latch2(self.pina, self.pinb)
        if a == 1 and self.last_a == 0:
            self.position += 1 if a == b else -1
            if self._handler:
                self._handler(self.position)
        self.last_a = a

    def irq(self, handler):
        self._handler = handler


# gpio pins

PIN_SDA = 23
PIN_SCL = 22

PIN_A   = 13
PIN_B   = 12

# constants

fd = 7000000
mult = 32
clk = 0

# functions

def on_encoder(position):
    on_uart(position * 10)

def on_uart(freq):
    try:
        freq = int(float(freq))
        si.set_freq(clk, si.PLL_A, freq)
        encoder.position = freq // 10
        uart.write(str(freq).encode())
    except ValueError:
        pass

i2c = I2C(-1, Pin(PIN_SCL), Pin(PIN_SDA))
si = SI5351_I2C(i2c)
si.setupPLL(si.PLL_A, mult)

encoder = Encoder(Pin(PIN_A, Pin.IN, Pin.PULL_UP), Pin(PIN_B, Pin.IN, Pin.PULL_UP))
ble = bluetooth.BLE()
uart = BLEUART(ble)

uart.irq(handler=on_uart)
encoder.irq(handler=on_encoder)

on_uart(fd)
si.enableOutputs(True)

while True:
   pass

