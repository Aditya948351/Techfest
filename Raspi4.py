from flask import Flask, jsonify, request
import RPi.GPIO as GPIO
import time
import threading
import requests

app = Flask(__name__)

# GPIO Pins
TRIG_PIN = 17  # Ultrasonic Sensor Trigger
ECHO_PIN = 27  # Ultrasonic Sensor Echo
BUZZER_PIN = 23  # Buzzer for Gas Alert
LED_PIN = 18  # LED Indicator
GAS_SENSOR_PIN = 22  # Digital output from MQ-2 sensor (DO pin)

# Desktop Script IP (Replace with your actual desktop IP)
DESKTOP_IP = "192.168.137.109"  
DESKTOP_PORT = 5000  # Port where your desktop script is running

# GAS DETECTION DELAY (15 seconds)
GAS_DETECTION_DELAY = 15  # Gas must be detected continuously for 15 seconds

# Setup GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(GAS_SENSOR_PIN, GPIO.IN)  # Digital input from MQ-2 sensor

def measure_distance():
    """Measure distance using Ultrasonic Sensor"""
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    start_time = time.time()
    stop_time = time.time()

    while GPIO.input(ECHO_PIN) == 0:
        start_time = time.time()

    while GPIO.input(ECHO_PIN) == 1:
        stop_time = time.time()

    elapsed_time = stop_time - start_time
    distance = (elapsed_time * 34300) / 2  # Convert to cm
    return round(distance, 2)

def gas_detected():
    """Check if gas is detected (LOW = Gas detected)"""
    return GPIO.input(GAS_SENSOR_PIN) == 0

def monitor_gas():
    """Continuously check gas sensor and trigger alert only after 15 seconds"""
    gas_start_time = None
    while True:
        if gas_detected():
            if gas_start_time is None:  # First detection
                gas_start_time = time.time()
            elif time.time() - gas_start_time >= GAS_DETECTION_DELAY:
                send_gas_alert()
                gas_start_time = None  # Reset timer after alert
        else:
            gas_start_time = None  # Reset timer if no gas detected
        time.sleep(1)  # Check every second

def send_gas_alert():
    """Trigger buzzer and send alert to desktop"""
    distance = measure_distance()
    
    # Send data to desktop script
    try:
        requests.post(f"http://{DESKTOP_IP}:{DESKTOP_PORT}/gas_alert", json={
            'distance': distance
        })
        print("🚀 Sent gas alert to desktop script!")
    except requests.RequestException as e:
        print(f"❌ Error sending data to desktop: {e}")

    # Activate buzzer for 5 seconds
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(5)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

@app.route('/control_led', methods=['POST'])
def control_led():
    """Control LED"""
    data = request.get_json()
    if 'state' in data:
        if data['state'] == 'on':
            GPIO.output(LED_PIN, GPIO.HIGH)
            return "LED turned on", 200
        elif data['state'] == 'off':
            GPIO.output(LED_PIN, GPIO.LOW)
            return "LED turned off", 200

    return "Invalid request", 400

if __name__ == "__main__":
    gas_thread = threading.Thread(target=monitor_gas)
    gas_thread.daemon = True
    gas_thread.start()

    app.run(host='0.0.0.0', port=5000)
