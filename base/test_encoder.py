from machine import Pin, I2C, Encoder
import time

# Configuración de los pines para los canales A y B

"""
pin_a = Pin(25, Pin.IN, Pin.PULL_UP)  
pin_b = Pin(33, Pin.IN, Pin.PULL_UP)   

# Variables para almacenar el estado y el conteo de pulsos
last_state_a = pin_a.value()
position = 0

def encoder_callback(pin):
    global last_state_a, position
    state_a = pin_a.value()
    state_b = pin_b.value()
    
    # Detecta cambios en el estado del canal A
    if state_a != last_state_a:
        if state_a == 1:
            # Determina la dirección en función del estado del canal B
            if state_b == 0:
                position += 1  # Dirección positiva
            else:
                position -= 1  # Dirección negativa
        last_state_a = state_a  # Actualiza el estado anterior de A

# Configura la interrupción en el pin A para detectar cambios
pin_a.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=encoder_callback)

# Bucle principal para monitorear la posición
try:
    while True:
        print("Posición actual:", position)
        time.sleep(0.1)  # Ajusta el tiempo de espera según tus necesidades
except KeyboardInterrupt:
    print("Programa terminado.")

    """

enc = Encoder(0, Pin(25), Pin(33), x=4)

try:
    while True:
        print("Posición actual:", enc.value())
        time.sleep(0.1)  # Ajusta el tiempo de espera según tus necesidades
except KeyboardInterrupt:
    print("Programa terminado.")
