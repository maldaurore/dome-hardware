from umqtt.simple import MQTTClient
import ujson as json
import time
import network
from config import CONFIG

CLIENT_ID = "dome-shutter-client"
TOPIC_EVENTS = b"dome/events"
WILL_PAYLOAD = {
    "shutter_online": False,
}
BROKER_HOST = CONFIG["mqtt_broker_host"]
BROKER_PORT = CONFIG["mqtt_broker_port"]
TOPIC_COMMANDS = b"dome/shutter/commands"

class Msg:
    pass

class SimpleMQTTWrapper:
    def __init__(self):
        self.on_message = None

        self._client = MQTTClient(
            client_id=CLIENT_ID,
            server=BROKER_HOST,
            port=BROKER_PORT,
            keepalive=30
        )

        self._client.set_last_will(
            TOPIC_EVENTS,
            json.dumps(WILL_PAYLOAD),
            retain=True,
            qos=1
        )

        self._client.set_callback(self._internal_callback)

        print("Conectando al broker...")
        self._client.connect()
        print("✅ Conectado al broker MQTT")

        self._client.subscribe(TOPIC_COMMANDS)
        print("📡 Suscrito a", TOPIC_COMMANDS)

        self.publish_message(json.dumps({"base_online": True}))

    def _internal_callback(self, topic, msg):
        if self.on_message:

            m = Msg()
            m.topic = topic
            m.payload = msg

            self.on_message(self, m)

    def publish_message(self, payload):
        self._client.publish(
            TOPIC_EVENTS,
            payload,
            qos=0
        )

    def publish_error(self, payload):
        self._client.publish(
            TOPIC_EVENTS,
            json.dumps(payload),
            qos=1
        )

    def loop_once(self):
        self._client.check_msg()

    def reconnect(self):
        wlan = network.WLAN(network.STA_IF)

        print("Reconectando MQTT...")

        while not wlan.isconnected():
            print("Esperando WiFi...")
            time.sleep(1)

        try:
            self._client.disconnect()
        except:
            pass

        time.sleep(2)

        while True:
            try:
                self._client.connect()
                self._client.set_callback(self._internal_callback)
                self._client.subscribe(TOPIC_COMMANDS)
                self.publish_message({"base_online": True})
                print("Reconectado")
                break
            except OSError:
                print("Reintento conexión MQTT...")
                time.sleep(2)

client = SimpleMQTTWrapper()
