from machine import Pin, Encoder
import time
import ujson as json

# TO DO: Mapear los valores del encoder a azimuth.
# TO DO: protección por si el encoder se queda colgado.

class Base:
  def __init__(self, mqtt_client):

    self.at_park = False
    self.azimuth = 0.0
    self.desiredAzimuth = None
    self.home_position = 0.0
    self.at_home = False
    self.slewing_to_home = False
    self.slewing_to_azimuth = False
    self.slewing_to_park = False
    self.abort_requested = False
    self.client = mqtt_client
    self.last_update = time.ticks_ms()
    self.last_state_publish = time.ticks_ms()

    self.encoder = Encoder(0, Pin(25), Pin(33), x=4)
    self.last_encoder_value = self.encoder.value()
    self.encoder_stall_timer = time.ticks_ms()

    self.initialized = False

    # Pines de los motores
    self.motor_right = Pin(26, Pin.OUT)
    self.motor_left = Pin(27, Pin.OUT)
    self.motor_left.value(0)
    self.motor_right.value(0)

    # Pin del sensor de home
    self.home_sensor = Pin(35, Pin.IN)

    # Interrupciones del sensor home
    # self.home_sensor.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._updateHomeStatus)

    self.client.publish_message({
      "dome_slewing": self.slewing_to_park or self.slewing_to_home or self.slewing_to_azimuth,
      "at_park": self.at_park,
      "azimuth": self.azimuth,
      "at_home": self.at_home,
      "base_online": True
    })

  def _updateHomeStatus(self, pin):
    if self.home_sensor.value() == 1:
      print('Home detected')
      self.AtHome = True
      self.AtPark = False
      if self.FindingHome:
        self.motor_left.value(0)
        self.motor_right.value(0)
        self.Slewing = False
        self.FindingHome = False
    else:
      print('Home lost')
      self.AtHome = False

  def _check_encoder_stall(self):
    current = self.encoder.value()

    if current == self.last_encoder_value:
        if time.ticks_diff(time.ticks_ms(), self.encoder_stall_timer) > 2000:
            print("Encoder stall detected")
            self.abort_requested = True
            return True
    else:
        self.encoder_stall_timer = time.ticks_ms()

    self.last_encoder_value = current
    self.azimuth = current
    return False

    
  def _stop_motors(self):
    self.motor_left.value(0)
    self.motor_right.value(0)
  
  def setSlaved(self, value):
    value = value.lower()
    if value == 'true':
      self.Slaved = True
    else: 
      self.Slaved = False

  def abortSlew(self):
    print('Abort slew')
    self.abort_requested = True

  def findHome(self):
    print('Finding home')
    
    # Si se encuentra en home, retorna.
    if self.home_sensor.value() == 1:
      return
    
    self.slewing_to_home = True
    self.abort_requested = False

    # Si se encontraba realizando alguna operación de slewing, se cancela dicha operación,
    # pero continúa en movimiento hasta encontrar home.
    if self.slewing_to_azimuth or self.slewing_to_park:
      self.slewing_to_azimuth = False
      self.slewing_to_park = False
      return
    
    # Si se conoce el azimut actual, se calcula la dirección de movimiento para encontrar
    # home.
    if self.initialized:

      endOfFringe = self.azimuth + 180

      if (endOfFringe > 360):
        endOfFringe -= 360
        print('endOfFringe: %f' % endOfFringe)
        if ((self.home_position > self.azimuth and self.home_position < 360) or 
            (self.home_position > 0 and self.home_position < endOfFringe) or
            self.home_position == 0 or self.home_position == 360):
          print('derecha')
          self._stop_motors()
          self.motor_right.value(1)
        else:
          print('izquierda')
          self._stop_motors()
          self.motor_left.value(1)
      
      else:

        if (self.home_position > self.azimuth and self.home_position < endOfFringe):
          print('derecha')
          self._stop_motors()
          self.motor_right.value(1)
        else:
          print('izquierda')
          self._stop_motors()
          self.motor_left.value(1)
          
    else:
      self._stop_motors()
      self.motor_right.value(1)

    return

  def park(self):
    print('Parking dome')

    # Si ya se encuentra en posición de park (que es la misma que home), retorna.
    if self.home_sensor.value() == 1:
      return
    
    if self.slewing_to_azimuth or self.slewing_to_home:
      self.slewing_to_azimuth = False
      self.slewing_to_home = False
    
    self.slewing_to_park = True
    self.abort_requested = False

    endOfFringe = self.azimuth + 180

    if (endOfFringe > 360):
      endOfFringe -= 360
      print('endOfFringe: %f' % endOfFringe)
      if ((self.home_position > self.azimuth and self.home_position < 360) or 
          (self.home_position > 0 and self.home_position < endOfFringe) or
          self.home_position == 0 or self.home_position == 360):
        print('derecha')
        self._stop_motors()
        self.motor_right.value(1)
      else:
        print('izquierda')
        self._stop_motors()
        self.motor_left.value(1)
    
    else:

      if (self.home_position > self.azimuth and self.home_position < endOfFringe):
        print('derecha')
        self._stop_motors()
        self.motor_right.value(1)
      else:
        print('izquierda')
        self._stop_motors()
        self.motor_left.value(1)

    return

  def slewToAzimuth(self, payload):

    desiredAzimuth = payload["azimuth"]
    if self.azimuth == desiredAzimuth:
      return
    
    if self.slewing_to_park or self.slewing_to_home:
      self.slewing_to_park = False
      self.slewing_to_home = False
    
    desiredAzimuth = float(desiredAzimuth)
    endOfFringe = self.azimuth + 180

    if (endOfFringe > 360):
      endOfFringe -= 360
      print('endOfFringe: %f' % endOfFringe)
      if ((desiredAzimuth > self.azimuth and desiredAzimuth < 360) or 
          (desiredAzimuth > 0 and desiredAzimuth < endOfFringe) or
          desiredAzimuth == 0 or desiredAzimuth == 360):
        print('derecha')
        self._stop_motors()
        self.motor_right.value(1)
      else:
        print('izquierda')
        self._stop_motors()
        self.motor_left.value(1)
    
    else:

      if (desiredAzimuth > self.azimuth and desiredAzimuth < endOfFringe):
        print('derecha')
        self._stop_motors()
        self.motor_right.value(1)
      else:
        print('izquierda')
        self._stop_motors()
        self.motor_left.value(1)

    self.slewing_to_azimuth = True
    self.desiredAzimuth = desiredAzimuth
    self.abort_requested = False

    return 'Slewing to azimuth'

  def getState(self):
    self.publishState()

  def update(self):
    now = time.ticks_ms()

    if time.ticks_diff(now, self.last_update) < 50:
      return
    
    self.last_update = now

    if self.abort_requested:
      self._stop_motors()
      self.slewing_to_azimuth = False
      self.slewing_to_home = False
      self.slewing_to_park = False
      self.abort_requested = False
      return

    if self.slewing_to_azimuth:
      self._update_slew_to_azimuth()
    elif self.slewing_to_home: 
      self._update_slew_to_home()
    elif self.slewing_to_park:
      self._update_slew_to_park()

    if time.ticks_diff(now, self.last_state_publish) > 1000:
      self.publishState()
      self.last_state_publish = now

  def _update_slew_to_azimuth(self):
    if self._check_encoder_stall():
      return
    
    print('Azimuth: %f' % self.azimuth)

    if abs(self.azimuth - self.desiredAzimuth) < 1.0:
      self._stop_motors()
      self.slewing_to_azimuth = False
      self.desiredAzimuth = None
      print('Slew complete')

  def _update_slew_to_home(self):
    if self._check_encoder_stall():
      return
    
    home_sensor = self.home_sensor.value()
    print('Home sensor: %d' % home_sensor)
    if home_sensor == 1:
      self._stop_motors()
      self.slewing_to_home = False
      self.at_home = True
      self.at_park = True
      self.azimuth = self.home_position
      self.initialized = True
      print('Home found')

  # Find home y park son equivalentes
  def _update_slew_to_park(self):
    if self._check_encoder_stall():
      return
    
    home_sensor = self.home_sensor.value()

    print('Azimuth: %f' % self.azimuth)
    if home_sensor == 1:
      self._stop_motors()
      self.slewing_to_park = False
      self.at_park = True
      self.at_home = True
      self.azimuth = self.home_position
      self.initialized = True
      print('Park complete')

  def publishState(self):
    self.client.publish_message({
      "dome_slewing": self.slewing_to_park or self.slewing_to_home or self.slewing_to_azimuth,
      "at_park": self.at_park,
      "azimuth": self.azimuth,
      "at_home": self.at_home,
      "base_online": True
    })