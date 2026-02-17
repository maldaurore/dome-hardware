import network
import esp
import gc

esp.osdebug(None)
gc.collect()

ssid = "INFINITUM3C47_2.4"
password= "Ge4H6Z2HJ9"

print("Conectando a internet...")

station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(ssid, password)

while station.isconnected() == False:
    pass

print ("Conexión exitosa")
print(station.ifconfig())