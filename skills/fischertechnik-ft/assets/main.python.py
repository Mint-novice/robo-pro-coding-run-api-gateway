from lib.controller import *
from fischertechnik.controller.Motor import Motor
import time


# ================== 配置区 ==================
PIN = 0               # 电机接在 Motor-0 上（M1）
SPEED = 100           # 速度
RUN_SECONDS = 1.0     # 每个方向运行时间
PAUSE_SECONDS = 0.5   # 两次往返之间停止时间
REPEAT = 3            # 往返次数
# ============================================


M1 = txt_factory.motor_factory.create_motor(TXT_M, PIN)


def drive(speed, direction, seconds):
  M1.set_speed(int(speed), direction)
  M1.start()
  time.sleep(seconds)


print("{{NAME}} start")
for i in range(REPEAT):
  print("round", i + 1, "/", REPEAT)
  drive(SPEED, Motor.CW, RUN_SECONDS)
  drive(SPEED, Motor.CCW, RUN_SECONDS)
  M1.stop()
  time.sleep(PAUSE_SECONDS)

print("{{NAME}} done")
