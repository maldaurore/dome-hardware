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
    "openshutter": device.open,
}

def on_message(client, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))

        cmd = payload.get("cmd")
    
        if cmd in COMMANDS:
            handler = COMMANDS[cmd]
            return handler()
    
    except Exception as e:
        print(f"Error procesando mensaje: {e}")

def main():
    client.on_message = on_message

    print("shutter device corriendo...")

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
        device.abortSlew()

if __name__ == "__main__":
    main()
