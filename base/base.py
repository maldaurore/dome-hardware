from machine import Pin, Encoder
import time
import ujson as json

PULSOS_POR_ROTACION = 1000
PULSOS_POR_GRADO =  PULSOS_POR_ROTACION / 360
HOME_POSITION = 0.0
FIND_HOME_TIMEOUT = 5000
DOME_STALL_ERROR = 1282
FIND_HOME_ERROR = 1283

class Base:
  def __init__(self, mqtt_client):
    self.state = {
      "dome_slewing": False,
      "at_park": False,
      "azimuth": None,
      "at_home": False,
      "base_online": True
    }
    self.last_state = None
    self.last_serialized_state = ""
    self.desiredAzimuth = None
    self.home_position = HOME_POSITION
    self.slewing_to_home = False
    self.slewing_to_azimuth = False
    self.slewing_to_park = False
    self.abort_requested = False
    self.client = mqtt_client
    self.last_update = time.ticks_ms()
    self.last_state_publish = time.ticks_ms()
    self.find_home_start_time = None

    self.encoder = Encoder(0, Pin(25), Pin(33), x=4)
    self.last_encoder_value = self.encoder.value()
    self.encoder_stall_timer = None

    self.initialized = False

    # Pines del motor
    self.motor_right = Pin(26, Pin.OUT)
    self.motor_left = Pin(27, Pin.OUT)
    self.motor_left.value(0)
    self.motor_right.value(0)

    # Pin del sensor de home
    self.home_sensor = Pin(35, Pin.IN)

    # Inicializar valores si está en home
    if self.home_sensor.value() == 1:
      self.handleAtHome()

    self.publishState()

    print(f"Pulsos por revolución: {PULSOS_POR_ROTACION}")
    print(f"Pulsos por grado: {PULSOS_POR_GRADO}")

  def _check_encoder_stall(self):
    current = self.encoder.value()
    now = time.ticks_ms()

    if current != self.last_encoder_value:
        self.encoder_stall_timer = now
        self.last_encoder_value = current
        return False

    if time.ticks_diff(now, self.encoder_stall_timer) > 2000:
        print("Encoder stall detected")
        self.abort_requested = True
        self.client.publish_error({
            "error": DOME_STALL_ERROR,
        })
        return True

    return False
  
  def _check_find_home_timeout(self):
    now = time.ticks_ms()
    if time.ticks_diff(now, self.find_home_start_time) > FIND_HOME_TIMEOUT:
      print("No se pudo encontrar home.")
      self.abort_requested = True
      self.client.publish_error({
        "error": FIND_HOME_ERROR,
        "message": "No se pudo encontrar home. Revise el sensor y cableado."
      })
      return True
    
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

  def abortSlew(self, payload):
    print('Abort slew')
    self.abort_requested = True

  def handleAtHome(self):
    self.initialized = True
    self.state["at_home"] = True
    self.state["at_park"] = True
    self.state["azimuth"] = HOME_POSITION
    self.encoder.value(int(HOME_POSITION * PULSOS_POR_GRADO))

  def findHome(self, payload):
    print('Finding home')
    
    # Si se encuentra en home, retorna.
    if self.home_sensor.value() == 1:
      print("En home, retornando")
      self.handleAtHome()
      return
    
    self.slewing_to_home = True
    self.abort_requested = False

    self.encoder_stall_timer = time.ticks_ms()
    self.last_encoder_value = self.encoder.value()
    self.find_home_start_time = time.ticks_ms()

    # Si se encontraba realizando alguna operación de slewing, se cancela dicha operación,
    # pero continúa en movimiento hasta encontrar home.
    if self.slewing_to_azimuth or self.slewing_to_park:
      self.slewing_to_azimuth = False
      self.slewing_to_park = False
      return
    
    # Si se conoce el azimut actual, se calcula la dirección de movimiento para encontrar
    # home.
    if self.initialized:

      endOfFringe = self.state["azimuth"] + 180

      if (endOfFringe > 360):
        endOfFringe -= 360
        print('endOfFringe: %f' % endOfFringe)
        if ((self.home_position > self.state["azimuth"] and self.home_position < 360) or 
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

        if (self.home_position > self.state["azimuth"] and self.home_position < endOfFringe):
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

  def park(self, payload):
    print('Parking dome')

    # Si ya se encuentra en posición de park (que es la misma que home), retorna.
    if self.home_sensor.value() == 1:
      return
    
    if self.slewing_to_azimuth or self.slewing_to_home:
      self.slewing_to_azimuth = False
      self.slewing_to_home = False
    
    self.slewing_to_park = True
    self.abort_requested = False

    self.encoder_stall_timer = time.ticks_ms()
    self.last_encoder_value = self.encoder.value()
    self.find_home_start_time = time.ticks_ms()

    endOfFringe = self.state["azimuth"] + 180

    if (endOfFringe > 360):
      endOfFringe -= 360
      print('endOfFringe: %f' % endOfFringe)
      if ((self.home_position > self.state["azimuth"] and self.home_position < 360) or 
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

      if (self.home_position > self.state["azimuth"] and self.home_position < endOfFringe):
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
    if self.state["azimuth"] == desiredAzimuth:
      return
    
    if self.slewing_to_park or self.slewing_to_home:
      self.slewing_to_park = False
      self.slewing_to_home = False

    self.encoder_stall_timer = time.ticks_ms()
    self.last_encoder_value = self.encoder.value()
    
    desiredAzimuth = float(desiredAzimuth)
    endOfFringe = self.state["azimuth"] + 180

    if (endOfFringe > 360):
      endOfFringe -= 360
      print('endOfFringe: %f' % endOfFringe)
      if ((desiredAzimuth > self.state["azimuth"] and desiredAzimuth < 360) or 
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

      if (desiredAzimuth > self.state["azimuth"] and desiredAzimuth < endOfFringe):
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

  def getState(self, payload):
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
    
    if (self.slewing_to_azimuth or self.slewing_to_home or self.slewing_to_park):
      self.state["dome_slewing"] = True
      if self.initialized:
        self._update_azimuth()

    if self.slewing_to_azimuth:
      self._update_slew_to_azimuth()
    elif self.slewing_to_home: 
      self._update_slew_to_home()
    elif self.slewing_to_park:
      self._update_slew_to_park()

    if time.ticks_diff(now, self.last_state_publish) > 1000:
      self.publishState()
      self.last_state_publish = now

  def _update_azimuth(self):
    encoder_value = self.encoder.value()
    if encoder_value >= PULSOS_POR_ROTACION:
      encoder_value = 0
      self.encoder.value(0)
    if encoder_value < 0:
      encoder_value = PULSOS_POR_ROTACION - abs(encoder_value)
      self.encoder.value(PULSOS_POR_ROTACION)

    azimuth = encoder_value / PULSOS_POR_GRADO
    self.state["azimuth"] = azimuth
    print(f"Azimuth: {azimuth}")

  def _update_slew_to_azimuth(self):
    if self._check_encoder_stall():
      return
    
    if abs(self.state["azimuth"] - self.desiredAzimuth) < 1.0:
      self._stop_motors()
      self.slewing_to_azimuth = False
      self.desiredAzimuth = None
      print('Slew complete')

  def _update_slew_to_home(self):
    if self._check_encoder_stall():
      return
    if self._check_find_home_timeout():
      return
    
    home_sensor = self.home_sensor.value()
    print('Home sensor: %d' % home_sensor)
    if home_sensor == 1:
      self._stop_motors()
      self.slewing_to_home = False
      self.handleAtHome()
      print('Home found')

  # Find home y park son equivalentes
  def _update_slew_to_park(self):
    if self._check_encoder_stall():
      return
    if self._check_find_home_timeout():
      return
    
    home_sensor = self.home_sensor.value()

    print('Azimuth: %f' % self.state["azimuth"])
    if home_sensor == 1:
      self._stop_motors()
      self.slewing_to_park = False
      self.handleAtHome()
      print('Park complete')

  def publishState(self):
    if self.state != self.last_state:
      self.last_serialized_state = json.dumps(self.state)
      self.last_state = self.state.copy()
    self.client.publish_message(self.last_serialized_state)