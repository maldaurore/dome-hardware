import json
import time
from shutter import Shutter
from mqtt_client import client

device = Shutter(client)

COMMANDS = {
    "get_state": device.getState,
    "abortslew": device.abortSlew,
    "open_without_flap": device.openWithoutFlap,
    "closeshutter": device.close,
    "opnshutter": device.open,
}

def on_message(client, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print(payload)

        cmd = payload.get("cmd")
    
        if cmd in COMMANDS:
            handler = COMMANDS[cmd]
            return handler(payload)
        else:
            print(f"Comando desconocido: {payload['cmd']}")
    
    except Exception as e:
        print(f"Error procesando mensaje: {e}")

def main():
    client.on_message = on_message

    print("shutter device corriendo...")

    try:
        while True:
            client.loop_once()
            device.update()
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("Cerrando...")
        device.abortSlew()

if __name__ == "__main__":
    main()
