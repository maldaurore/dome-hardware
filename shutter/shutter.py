from machine import Pin
import time
from enum import Enum

class Actions(Enum):
  open = 0
  freeFlap = 2
  close = 3
  releaseFlapHook = 4

class DesiredActions(Enum):
  open = 0
  openWithoutFlap = 1
  close = 2

class ShutterStatus(Enum):
    open = 0
    closed = 1
    opening = 2
    closing = 3
    error = 4
    unknown = 5

class FlapStatus(Enum):
    up = 0
    down = 1
    error = 2

class Shutter:
  def __init__(self, mqtt_client):
    self.shutter_status = None
    self.flap_status = None
    self.abort_requested = False
    self.desired_action = None
    self.current_action = None
    self.error = ''
    self.client = mqtt_client
    self.last_update = time.ticks_ms()
    self.last_state_publish = time.ticks_ms()
    self.open_confirm_start = None
    self.close_confirm_start = None
    self.free_flap_confirm_start = None
    self.release_flap_hook_confirm_start = None
    self.hook_needs_release = False
    self.action_start_time = None
    self.ACTION_TIMEOUTS = {
      Actions.open: 15000,
      Actions.close: 15000,
      Actions.freeFlap: 5000,
      Actions.releaseFlapHook: 5000,
    }

    # Pines de switches
    self.bottom_switch = Pin(26, Pin.IN)
    self.middle_switch = Pin(27, Pin.IN)
    self.top_switch = Pin(32, Pin.IN)
    self.flap_switch = Pin(25, Pin.IN)
    self.flap_hook_open = Pin(28, Pin.IN)
    self.flap_hook_closed = Pin(29, Pin.IN)

    # Pines de los motores
    self.motor_open = Pin(13, Pin.OUT)
    self.motor_close = Pin(12, Pin.OUT)
    self.motor_close.value(0)
    self.motor_open.value(0)
    self.flap_motor_open = Pin(33, Pin.OUT)
    self.flap_motor_open.value(0)
    self.flap_motor_close = Pin(34, Pin.OUT)
    self.flap_motor_close.value(0)

    self.update()
    self.publishState()

  def openWithoutFlap(self):
    if self.error:
      return
    if self.shutter_status != ShutterStatus.closed:
      return
    
    print("Liberando gajo...")
    self.desired_action = DesiredActions.openWithoutFlap
    self.current_action = Actions.freeFlap
    self.action_start_time = time.ticks_ms()
    self._reset_timers()
    self._stop_motors()
    self.flap_motor_open.value(1)
    self.hook_needs_release = True
    self.error = ''
    return
  
  def abortSlew(self):    
    print('Abort slew')
    self.abort_requested = True
    return
  
  def close(self):
    if self.error:
      return
    if (self.shutter_status == ShutterStatus.closed):
      return
    
    # Si se había recibido comando de abrir sin gajo antes, regresar el gancho a 
    # posición de reposo.
    if self.current_action == Actions.freeFlap:
      self._stop_motors()
      self.desired_action = None
      self.current_action = Actions.releaseFlapHook
      self.action_start_time = time.ticks_ms()
      print("Cortina cerrada, liberando gancho de gajo.")
    else:
      print('Closing shutter')
      self._stop_motors()
      self.desired_action = DesiredActions.close
      self.current_action = Actions.close
      self.action_start_time = time.ticks_ms()
      self._reset_timers()
      self.motor_close.value(1)
      return
  
  # TO DO: agregar una validación, antes de encender el motor, de que el gancho
  # del gajo esté en la posición correcta. por si antes se hizo un abort slew y el motor del
  # gancho quedó en un estado intermedio
  def open(self):
    if self.error:
      return
    if (
      self.shutter_status == ShutterStatus.open or 
      self.shutter_status == ShutterStatus.opening or
      self.current_action == Actions.freeFlap
      ):
      return

    print("Abriendo cortina")
    
    self.desired_action = DesiredActions.open
    self._stop_motors()

    if self.hook_needs_release:
      if self.flap_switch.value() == 0:
        self.current_action = Actions.releaseFlapHook
        self.flap_motor_close.value(1)
      else:
        self.hook_needs_release = False
        self.current_action = Actions.open
        self.motor_open.value(1)
    else:
      self.current_action = Actions.open
      self.motor_open.value(1)

    self.action_start_time = time.ticks_ms()
    self._reset_timers()

    return 'Opening shutter.'
  
  def _stop_motors(self):
    self.motor_close.value(0)
    self.motor_open.value(0)
    self.flap_motor_close.value(0)
    self.flap_motor_open.value(0)
  
  def getState(self):
    self.publishState()

  def publishState(self):
    self.client.publish_message({
      "shutter_status": self.shutter_status,
      "flap_status": self.flap_status,
      "shutter_online": True,
      "error": self.error,
    })

  def update(self):
    now = time.ticks_ms()

    if time.ticks_diff(now, self.last_update) < 50:
      return
    
    self.last_update = now
    self._update_flap_status()
    self._update_shutter_status()

    if self.abort_requested:
      self._stop_motors()
      self.desired_action = None
      self.current_action = None
      self.action_start_time = None
      self._reset_timers()
      self.abort_requested = False
      if self.flap_switch.value() == 1:
        self.hook_needs_release = False
      else:
        self.hook_needs_release = True

      return
    
    if self.current_action is not None and self.action_start_time is not None:
      timeout = self.ACTION_TIMEOUTS.get(self.current_action, None)
      if timeout is not None:
        if time.ticks_diff(now, self.action_start_time) > timeout:
          print("ERROR: timeout en acción", self.current_action)
          self._stop_motors()
          self.error = f"Timeout en {self.current_action}"
          self.desired_action = None
          self.current_action = None
          self.action_start_time = None
          self._reset_timers()

    match self.current_action:
      case Actions.open:
        self._update_open()
      case Actions.close:
        self._update_close()
      case Actions.freeFlap:
        self._update_free_flap()
      case Actions.releaseFlapHook:
        self._update_release_flap_hook()

    if time.ticks_diff(now, self.last_state_publish) > 1000:
      self.publishState()
      self.last_state_publish = now

  def _update_shutter_status(self):
    if self.bottom_switch.value() == 1 and self.middle_switch.value() == 1 and self.top_switch.value() == 0:
      self.shutter_status = ShutterStatus.closed
    elif self.bottom_switch.value() == 1 and self.middle_switch.value() == 0 and self.top_switch.value() == 1:
      self.shutter_status = ShutterStatus.open
    elif self.middle_switch.value() == 0 and self.top_switch.value() == 0:
      if self.motor_open.value() == 1:
        self.shutter_status = ShutterStatus.opening
      elif self.motor_close.value() == 1:
        self.shutter_status = ShutterStatus.closing
      else:
        self.shutter_status = ShutterStatus.unknown
    else:
        self.shutter_status = ShutterStatus.unknown

  def _update_flap_status(self):
    if self.flap_switch.value() == 1:
      self.flap_status = FlapStatus.down
    else:
      self.flap_status = FlapStatus.up

  def _update_open(self):
    now = time.ticks_ms()

    if self.shutter_status == ShutterStatus.open:
      if self.open_confirm_start is None:
        self.open_confirm_start = now
      elif time.ticks_diff(now, self.open_confirm_start) > 200:
        self._stop_motors()
        self.desired_action = None
        if self.hook_needs_release:
          self.current_action = Actions.releaseFlapHook
          self.action_start_time = now
        else:
          self.current_action = None
        self.action_start_time = None
        self.open_confirm_start = None
        print('Cortina abierta.')
    else:
      self.open_confirm_start = None

  def _update_close(self):
    now = time.ticks_ms()
    if self.shutter_status == ShutterStatus.closed:
      if self.close_confirm_start is None:
        self.close_confirm_start = now
      elif time.ticks_diff(now, self.close_confirm_start) > 200:
        self._stop_motors()
        self.desired_action = None
        if self.hook_needs_release:
          self.current_action = Actions.releaseFlapHook
        else:
          self.current_action = None
        self.action_start_time = None
        self.close_confirm_start = None
        print("Cortina cerrada.")
    else:
      self.close_confirm_start = None
  
  def _update_free_flap(self):
    now = time.ticks_ms()
    if self.flap_switch.value() == 1:
      if self.free_flap_confirm_start is None:
        self.free_flap_confirm_start = now
      elif time.ticks_diff(now, self.free_flap_confirm_start) > 200:
        print("Gajo liberado, abriendo cortina...")
        self._stop_motors()
        self.current_action = Actions.open
        self.action_start_time = time.ticks_ms()
        self._reset_timers()
        self.motor_open.value(1)
        self.free_flap_confirm_start = None
    else:
      self.free_flap_confirm_start = None

  def _update_release_flap_hook(self):
    now = time.ticks_ms()
    if self.flap_switch.value() == 0:
      if self.release_flap_hook_confirm_start is None:
        self.release_flap_hook_confirm_start = now
      elif time.ticks_diff(now, self.release_flap_hook_confirm_start) > 200:
        print("Gancho en posición de reposo")
        self._stop_motors()
        self.hook_needs_release = False

        if self.desired_action == DesiredActions.open:
          self.current_action = Actions.open
          self.action_start_time = now
          self.motor_open.value(1)
        else:
          self.desired_action = None
          self.current_action = None
          self.action_start_time = None

        self.release_flap_hook_confirm_start = None
    else:
      self.release_flap_hook_confirm_start = None

  def _reset_timers(self):
    self.open_confirm_start = None
    self.close_confirm_start = None
    self.free_flap_confirm_start = None
    self.release_flap_hook_confirm_start = None

  def cleanError(self):
    self.error = ''
