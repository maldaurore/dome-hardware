from machine import Pin
import uasyncio as asyncio

class Shutter:
  def __init__(self):
    self.Slewing = False
    self.ShutterStatus = 0  # 0: open, 1: closed, 2: opening, 3: closing, 4: error
    self.flapStatus = 0     # 0: down, 1: up, 2: opening, 3: closing, 4: error
    self.abort_requested = False
    self.error = ''
    self.abort_requested = False
    self.Slewing = False
    self.slew_task = None

    # Pines de switches
    self.bottom_switch = Pin(26, Pin.IN)
    self.middle_switch = Pin(27, Pin.IN)
    self.top_switch = Pin(32, Pin.IN)
    self.flap_switch = Pin(25, Pin.IN)

    # Pines de los motores
    self.motor_open = Pin(13, Pin.OUT)
    self.motor_close = Pin(12, Pin.OUT)
    self.motor_close.value(0)
    self.motor_open.value(0)
    self.flap_motor = Pin(33, Pin.OUT)

  async def track_open_without_flap(self):
    try:
      while self.Slewing and not self.abort_requested:
        if (self.flap_switch.value() == 1):
          self.flap_motor.value(0)
          print('Mecanismo libero gajo. Deteniendo motor de gajo.')
          break
        
        await asyncio.sleep(0.1)

      if self.abort_requested:
        print ("Abort solicitado, terminando hilo")
        self.abort_requested = False
        return
      
      print("Gajo liberado, encendiendo motor de cortina para abrir.")
      self.motor_open.value(1)
      print("Esperando 5 segundos...")
      await asyncio.sleep(5)
      print("Verificando estado de los switches")
      if (self.bottom_switch.value() == 1 and self.middle_switch.value() == 1):
        print("No se abrió la cortina")
        self.motor_open.value(0)
        self.ShutterStatus = 4
        self.flapStatus = 4
        self.error = 'No se pudo abrir la cortina.'
        self.Slewing = False
        raise Exception('No se pudo abrir la cortina.')
      
      if (self.bottom_switch.value() == 0 and self.middle_switch.value() == 0):
        print("No se separo el gajo.")
        self.motor_open.value(0)
        self.ShutterStatus = 4
        self.flapStatus = 4
        self.error = 'No se separó el gajo de la cortina.'
        self.Slewing = False
        return
      
      while self.Slewing and not self.abort_requested:

        if self.top_switch.value() == 1:
          self.motor_open.value(0)
          self.Slewing = False
          self.ShutterStatus = 1
          self.flapStatus = 0
          print("Cortina abierta.")
          break
        
        await asyncio.sleep(0.1)
    except Exception as e:
      print("Error in track_open_without_flap:", e)

  async def track_close(self):
    print("Entrando en tarea track")
    try:

      while self.Slewing and not self.abort_requested:
        print("Verificando estado de switch")
        print(self.middle_switch.value())
        if (self.middle_switch.value() == 1):
          self.motor_close.value(0)
          self.motor_open.value(0)
          self.Slewing = False
          self.ShutterStatus = 1
          self.flapStatus = 0
          print('Cortina cerrada.')
          break
        
        await asyncio.sleep(0.1)
    except Exception as e:
      print("Error in track_close:", e)

  async def track_open(self):
    try:
      while self.Slewing and not self.abort_requested:
        print("Verificando estado de switch")
        if self.top_switch.value() == 1:
          self.motor_open.value(0)
          self.motor_close.value(0)
          self.Slewing = False
          self.ShutterStatus = 1
          self.flapStatus = 0
          print('Cortina abierta.')
          break
        await asyncio.sleep(0.1)

    except Exception as e:
      print("Error in track_open:", e)

  def getShutterStatus(self):
    if self.ShutterStatus == 4:
      return {'status': 4, 'error': self.error}
    else:
      if self.bottom_switch.value() == 1 and self.middle_switch.value() == 1 and self.top_switch.value() == 0:
        return 1
      elif self.bottom_switch.value() == 1 and self.middle_switch.value() == 0 and self.top_switch.value() == 1:
        return 0
      elif self.middle_switch.value() == 0 and self.top_switch.value() == 0:
        if self.motor_open.value() == 1:
          return 2
        elif self.motor_close.value() == 1:
          return 3
        
      else: return {'status': 4, 'error': self.error}
  
  def getFlapStatus(self):
    # abajo arriba abriendo cerrando error
    if self.flapStatus == 4:
      return {'status': 4, 'error': self.error}
    
    else:
      if self.bottom_switch.value() == 1:
        return {'status': 0}
      elif self.bottom_switch.value() == 0:
        if self.Slewing:
          if self.motor_open.value() == 1:
            return {'status': 2}
          elif self.motor_close.value() == 1:
            return {'status': 3}
        else:
          return {'status': 1}
        
      else: return {'status': 4, 'error': self.error}
  
  def getSlewing(self):
    slewing = self.motor_close.value() or self.motor_open.value() or self.flap_motor.value()
    if slewing:
      self.Slewing = True
      return True
    else:
      self.Slewing = False
      return False

  def openWithoutFlap(self):
    if self.Slewing:
      if self.motor_open.value() == 1:
        raise Exception('Shutter is already opening.')
      elif self.motor_close.value() == 1:
        raise Exception('Shutter is already closing.')
      else:
        raise Exception('Shutter is already slewing.')
      
    if (self.bottom_switch.value() == 1 and self.middle_switch.value() == 0):
      raise Exception('Shutter is already open without flap.')
    if (self.bottom_switch.value() == 0 and self.middle_switch.value() == 0):
      raise Exception('Shutter must be closed before opening without flap.')
    
    self.Slewing = True
    self.flap_motor.value(1)
    self.error = ''
    self.ShutterStatus = 1
    self.flapStatus = 0
    if self.slew_task is None or self.slew_task.done():
      self.slew_task = asyncio.create_task(self.track_open_without_flap())
    return 'Opening shutter without flap.'
  
  def abortSlew(self):
    if (self.motor_open.value() == 0 and self.motor_close.value() == 0 and self.flap_motor.value() == 0):
      raise Exception('Shutter is not opening or closing.')
    
    print('Abort slew')
    self.motor_close.value(0)
    self.motor_open.value(0)
    self.flap_motor.value(0)
    self.Slewing = False
    self.abort_requested = True
    return 'Abort requested.'
  
  def close(self):
    if (self.middle_switch.value() == 1):
      raise Exception('Shutter is already closed.')
    
    print('Closing shutter')
    self.ShutterStatus = 3
    self.flapStatus = 0
    self.motor_close.value(1)
    self.Slewing = True
    if self.slew_task is None or self.slew_task.done():
      print("No hay tarea creada")
      self.slew_task = asyncio.create_task(self.track_close())
    return 'Closing shutter.'
  
  def open(self):
    if (self.top_switch.value() == 1):
      raise Exception('Shutter is already open.')

    print("Abriendo cortina")
    
    self.ShutterStatus = 2
    self.flapStatus = 0
    self.motor_open.value(1)
    self.Slewing = True
    if self.slew_task is None or self.slew_task.done():
      self.slew_task = asyncio.create_task(self.track_open())
    return 'Opening shutter.'