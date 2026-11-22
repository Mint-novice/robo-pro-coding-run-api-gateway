import fischertechnik.factories as txt_factory
from fischertechnik.control.RemoteControl import RemoteControl
from fischertechnik.control.VoiceControl import VoiceControl

voice_control = None
remote_control = None


def get_voice_control():
  global voice_control
  if voice_control is None:
    voice_control = VoiceControl()
  return voice_control


def get_remote_control():
  global remote_control
  if remote_control is None:
    remote_control = RemoteControl()
  return remote_control


txt_factory.init()


TXT_M = txt_factory.controller_factory.create_graphical_controller()

txt_factory.initialized()