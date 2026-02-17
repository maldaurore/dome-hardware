from umqtt.simple import MQTTClient
import ujson as json
import time

CLIENT_ID = "dome-base-client"
TOPIC_EVENTS = b"dome/events"
WILL_PAYLOAD = {
    "base_online": False,
}
BROKER_HOST = "192.168.1.10" 
BROKER_PORT = 1883
TOPIC_COMMANDS = b"dome/commands"

class Msg:
    pass

class SimpleMQTTWrapper:
    def __init__(self):
        self.on_message = None

        self._client = MQTTClient(
            client_id=CLIENT_ID,
            server=BROKER_HOST,
            port=BROKER_PORT,
            keepalive=60
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

        self.publish_message({"base_online": True})

    def _internal_callback(self, topic, msg):
        if self.on_message:

            m = Msg()
            m.topic = topic
            m.payload = msg

            self.on_message(self, m)

    def publish_message(self, payload):
        self._client.publish(
            TOPIC_EVENTS,
            json.dumps(payload),
            qos=1
        )

    def loop_once(self):
        self._client.check_msg()


client = SimpleMQTTWrapper()
