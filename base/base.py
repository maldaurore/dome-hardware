from machine import Pin, Encoder
import uasyncio as asyncio

class Base:
  def __init__(self):
    self.AtHome = False
    self.AtPark = False
    self.park_position = 20
    self.Azimuth = 0
    self.Slewing = False
    self.Slaved = False
    self.FindingHome = False
    self.encoder = Encoder(0, Pin(25), Pin(33), x=4)
    self.initialized = False
    self.abort_requested = False
    self.slewing_to_azimuth = False
    self.home_position = 0
    self.slewing_to_park = False
    self.slew_task = None

    # Pines de los motores
    self.motor_right = Pin(26, Pin.OUT)
    self.motor_left = Pin(27, Pin.OUT)
    self.motor_left.value(0)
    self.motor_right.value(0)
    self.desiredAzimuth = 0

    # Pin del sensor de home
    self.home_sensor = Pin(35, Pin.IN)

    if self.home_sensor.value() == 1:
      self.AtHome = True
      self.initialized = True
    else:
      self.AtHome = False
      self.initialized = False

    # Interrupciones del sensor home
    # self.home_sensor.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._updateHomeStatus)

  async def track_slew_to_azimuth(self):
    try:
        while self.slewing_to_azimuth and not self.abort_requested:
          self.Azimuth = self.encoder.value()
          print('Azimuth: %f' % self.Azimuth)

          if abs(self.Azimuth - self.desiredAzimuth) < 1.0:
              self.motor_left.value(0)
              self.motor_right.value(0)
              self.Slewing = False
              self.slewing_to_azimuth = False
              print('Slew complete')
              break

          await asyncio.sleep(0.1)
    except Exception as e:
      print("Error en track_slew_to_azimuth:", e)

  async def track_slew_to_park(self):
    try:
        while self.slewing_to_park and not self.abort_requested:
          self.Azimuth = self.encoder.value()
          print('Azimuth: %f' % self.Azimuth)

          if abs(self.Azimuth - self.park_position) < 1.0:
              self.motor_left.value(0)
              self.motor_right.value(0)
              self.Slewing = False
              self.slewing_to_park = False
              print('Park complete')
              break

          await asyncio.sleep(0.1)
    except Exception as e:
      print("Error en track_slew_to_park:", e)

  async def track_find_home(self):
    try:
        while self.FindingHome and not self.abort_requested:
          home_sensor = self.home_sensor.value()
          print('Home sensor: %d' % home_sensor)
          if self.home_sensor.value() == 1:
              self.motor_left.value(0)
              self.motor_right.value(0)
              self.Slewing = False
              self.FindingHome = False
              self.AtHome = True
              self.initialized = True
              print(self.initialized)
              print('Home found')
              break

          await asyncio.sleep(0.1)
    except Exception as e:
      print("Error en track_find_home:", e)

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

  def getAtHome(self):

    if self.home_sensor.value() == 1:
      self.AtHome = True
      return True
    else:
      self.AtHome = False
      return False
  
  def getAtPark(self):
    
    if abs(self.park_position - self.Azimuth) < 1.0:
      self.AtPark = True
      return True
    else:
      self.AtPark = False
      return False
  
  def getAzimuth(self):
    azimuth = self.encoder.value()
    if azimuth < 0:
      azimuth += 360
    elif azimuth > 360:
      azimuth -= 360
    self.Azimuth = azimuth
    return self.Azimuth
  
  def getSlewing(self):
    return self.Slewing
  
  def getSlaved(self):
    return self.Slaved
  
  def getInitialized(self):
    return self.initialized
  
  def setSlaved(self, value):
    value = value.lower()
    if value == 'true':
      self.Slaved = True
    else: 
      self.Slaved = False

  def setPark(self):
    
    self.park_position = self.Azimuth
    self.AtPark = True
    return 'Park position set to current azimuth.'

  def abortSlew(self):
    print('Abort slew')
    self.motor_left.value(0)
    self.motor_right.value(0)
    self.Slewing = False
    self.abort_requested = True

  def findHome(self):
    print('Finding home')
    if self.Slewing:
      raise Exception('Dome is slewing.')
    
    if self.home_sensor.value() == 1:
      self.AtHome = True
      if not self.initialized:
        self.initialize()
      raise Exception('Dome is already at home position.')
    
    if self.initialized:
      self.FindingHome = True

      endOfFringe = self.Azimuth + 180

      if (endOfFringe > 360):
        endOfFringe -= 360
        print('endOfFringe: %f' % endOfFringe)
        if ((self.home_position > self.Azimuth and self.home_position < 360) or 
            (self.home_position > 0 and self.home_position < endOfFringe) or
            self.home_position == 0 or self.home_position == 360):
          print('derecha')
          self.motor_right.value(1)
        else:
          print('izquierda')
          self.motor_left.value(1)
      
      else:

        if (self.home_position > self.Azimuth and self.home_position < endOfFringe):
          print('derecha')
          self.motor_right.value(1)
        else:
          print('izquierda')
          self.motor_left.value(1)

      self.Slewing = True
      self.FindingHome = True
      self.abort_requested = False
      
      if self.slew_task is None or self.slew_task.done():
        self.slew_task = asyncio.create_task(self.track_find_home())
        return 'Dome is finding home.'
    
    self.FindingHome = True
    self.Slewing = True
    self.motor_right.value(1)

    if self.slew_task is None or self.slew_task.done():
      self.slew_task = asyncio.create_task(self.track_find_home())

    return 'Dome is finding home.'

  def park(self):
    print('Parking dome')
    if self.Slewing:
      raise Exception('Dome is slewing.')
    
    if abs(self.Azimuth - self.park_position) < 1.0:
      self.AtPark = True
      raise Exception('Dome is already at park position.')

    endOfFringe = self.Azimuth + 180

    if (endOfFringe > 360):
      endOfFringe -= 360
      print('endOfFringe: %f' % endOfFringe)
      if ((self.park_position > self.Azimuth and self.park_position < 360) or 
          (self.park_position > 0 and self.park_position < endOfFringe) or
          self.park_position == 0 or self.park_position == 360):
        print('derecha')
        self.motor_right.value(1)
      else:
        print('izquierda')
        self.motor_left.value(1)
    
    else:

      if (self.park_position > self.Azimuth and self.park_position < endOfFringe):
        print('derecha')
        self.motor_right.value(1)
      else:
        print('izquierda')
        self.motor_left.value(1)

    self.Slewing = True
    self.slewing_to_park = True
    self.abort_requested = False
    
    if self.slew_task is None or self.slew_task.done():
      self.slew_task = asyncio.create_task(self.track_slew_to_park())

    return 'Dome is parking.'

  def slewToAzimuth(self, desiredAzimuth):

    ## Levantar error si ya se esta slewing?
    if self.Slewing:
      raise Exception('Dome is slewing.')

    if self.Azimuth == desiredAzimuth:
      return 'Dome is already at the desired azimuth.'
    
    try:
      desiredAzimuth = float(desiredAzimuth)
    except ValueError:
      raise Exception('Desired azimuth must be a float or numeric string.')

    endOfFringe = self.Azimuth + 180

    if (endOfFringe > 360):
      endOfFringe -= 360
      print('endOfFringe: %f' % endOfFringe)
      if ((desiredAzimuth > self.Azimuth and desiredAzimuth < 360) or 
          (desiredAzimuth > 0 and desiredAzimuth < endOfFringe) or
          desiredAzimuth == 0 or desiredAzimuth == 360):
        print('derecha')
        self.motor_right.value(1)
      else:
        print('izquierda')
        self.motor_left.value(1)
    
    else:

      if (desiredAzimuth > self.Azimuth and desiredAzimuth < endOfFringe):
        print('derecha')
        self.motor_right.value(1)
      else:
        print('izquierda')
        self.motor_left.value(1)

    self.Slewing = True
    self.desiredAzimuth = desiredAzimuth
    self.slewing_to_azimuth = True
    self.abort_requested = False

    # Iniciar tarea asincrona de rastreo de posicion
    if self.slew_task is None or self.slew_task.done():
      self.slew_task = asyncio.create_task(self.track_slew_to_azimuth())

    return 'Slewing to azimuth'

  def initialize(self):
    
    self.initialized = True
    self.Azimuth = 0
    self.encoder.value(0)

    print('Dome initialized')