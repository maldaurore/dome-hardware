import network
import esp
import gc
import json
from config import CONFIG

esp.osdebug(None)
gc.collect()

ssid = CONFIG["ssid"]
password= CONFIG["password"]

print("Conectando a internet...")

station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(ssid, password)

while station.isconnected() == False:
    pass

print ("Conexión exitosa")
print(station.ifconfig())