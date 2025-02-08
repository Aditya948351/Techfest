import requests
import time
from twilio.rest import Client
import pyttsx3

RPI_IP = "192.168.1.100"  # Replace with your Raspberry Pi's IP
DATA_PORT = 5000
account_sid = 'replace with the sid'
auth_token = 'replace with twilio auth token'
twilio_phone = 'Add generated Twilio phone number'
user_phone = 'Add your registered number'

client = Client(account_sid, auth_token)
engine = pyttsx3.init()

def speak(message):
    engine.say(message)
    engine.runAndWait()

def send_alert():
    """Send an SMS alert using Twilio"""
    message = client.messages.create(
        body="🚨 Gas leak detected! Please check immediately.",
        from_=twilio_phone,
        to=user_phone
    )
    print(f"Alert Sent. SID: {message.sid}")

def get_sensor_data():
    """Fetch sensor data from Raspberry Pi"""
    try:
        url = f'http://{RPI_IP}:{DATA_PORT}/get_data'
        response = requests.get(url)
        data = response.json()

        if data['gas_detected']:  # Only process if gas is detected
            return data['distance'], data['gas_detected'], data.get('gas_value', 0)
        else:
            return None, False, None  # No gas detected
    except requests.RequestException as e:
        print(f"Error retrieving sensor data: {e}")
        return None, None, None

def control_raspberry(action):
    """Control Raspberry Pi buzzer and LED"""
    if action == "buzzer":
        requests.post(f'http://{RPI_IP}:{DATA_PORT}/control_buzzer')
    elif action == "led_on":
        requests.post(f'http://{RPI_IP}:{DATA_PORT}/control_led', json={'state': 'on'})
    elif action == "led_off":
        requests.post(f'http://{RPI_IP}:{DATA_PORT}/control_led', json={'state': 'off'})

def main():
    gas_alert_sent = False

    while True:
        distance, gas_detected, gas_value = get_sensor_data()
        
        if gas_detected:
            print(f"⚠️ Gas detected! Distance: {distance} cm | Gas Level: {gas_value}")

            if not gas_alert_sent:
                send_alert()
                control_raspberry("buzzer")
                control_raspberry("led_on")
                speak("Gas detected! Alert sent.")
                gas_alert_sent = True
        else:
            gas_alert_sent = False
            control_raspberry("led_off")

        time.sleep(5)

if __name__ == "__main__":
    main()
