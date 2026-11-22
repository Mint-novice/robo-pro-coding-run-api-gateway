from lib.controller import *

import time
from fischertechnik.controller.Motor import Motor

PIN = 0
SPEED = 100

M1 = txt_factory.motor_factory.create_motor(TXT_M, PIN)

while True:
  M1.set_speed(int(SPEED), Motor.CW)
  M1.start()
  time.sleep(1)

  M1.set_speed(int(SPEED), Motor.CCW)
  M1.start()
  time.sleep(1)

  M1.stop()
  time.sleep(0.5)
