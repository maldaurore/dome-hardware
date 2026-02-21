import json
import time
from base import Base
from mqtt_client import client

device = Base(client)

COMMANDS = {
    "abortslew": device.abortSlew,
    "findhome": device.findHome,
    "park": device.park,
    "slewtoazimuth": device.slewToAzimuth,
    "get_state": device.getState
}

def on_message(client, msg):
    payload = msg.payload.decode("utf-8")
    payload = json.loads(payload)
    
    if payload["cmd"] in COMMANDS:
        handler = COMMANDS[payload["cmd"]]
        return handler(payload)
    else:
        print(f"Comando desconocido: {payload['cmd']}")
        return

def main():
    client.on_message = on_message

    print("base device corriendo...")

    try:
        while True:
            try:
                client.loop_once()
                device.update()
            except OSError as e:
                print("Error MQTT:", e)
                client.reconnect()

            time.sleep(0.01)
    except KeyboardInterrupt:
        print("Cerrando...")

if __name__ == "__main__":
    main()
