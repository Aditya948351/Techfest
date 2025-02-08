from flask import Flask, jsonify, request
import RPi.GPIO as GPIO
import time
import threading
import requests

app = Flask(__name__)

# GPIO Pins
TRIG_PIN = 17  # Ultrasonic Sensor Trigger
ECHO_PIN = 27  # Ultrasonic Sensor Echo
BUZZER_PIN = 23  # Buzzer for Alarm
IR_SENSOR_PIN = 21  # IR Sensor (instead of Gas Sensor)
LED_PIN = 18  # LED control pin

# Desktop Script IP (Change this to your actual desktop IP)
DESKTOP_IP = "192.168.137.109"
DESKTOP_PORT = 5000  # Port where your desktop script is running

# IR SENSOR DETECTION DELAY
IR_DETECTION_DELAY = 15  # Must detect continuously for 15 seconds

# Setup GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(IR_SENSOR_PIN, GPIO.IN)  # Digital input from IR sensor
GPIO.setup(LED_PIN, GPIO.OUT)  # Setup LED pin

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

def ir_detected():
    """Check if IR sensor detects an object (LOW = Detected)"""
    return GPIO.input(IR_SENSOR_PIN) == 0

def monitor_ir():
    """Continuously check IR sensor and trigger alert only after 15 seconds"""
    ir_start_time = None
    while True:
        if ir_detected():
            if ir_start_time is None:  # First detection
                ir_start_time = time.time()
            elif time.time() - ir_start_time >= IR_DETECTION_DELAY:
                send_ir_alert()
                ir_start_time = None  # Reset timer after alert
        else:
            ir_start_time = None  # Reset timer if no object detected
        time.sleep(1)  # Check every second

def send_ir_alert():
    """Trigger buzzer and send alert to desktop"""
    distance = measure_distance()

    # Send data to desktop script
    try:
        requests.post(f"http://{DESKTOP_IP}:{DESKTOP_PORT}/ir_alert", json={
            'distance': distance
        })
        print("🚀 Sent IR detection alert to desktop script!")
    except requests.RequestException as e:
        print(f"❌ Error sending data to desktop: {e}")

    # Activate buzzer for 5 seconds
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(5)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

def send_distance_continuously():
    """Send distance data to desktop every 5 seconds"""
    while True:
        distance = measure_distance()
        try:
            requests.post(f"http://{DESKTOP_IP}:{DESKTOP_PORT}/update_distance", json={
                'distance': distance
            })
            print(f"📡 Sent distance: {distance} cm to desktop")
        except requests.RequestException as e:
            print(f"❌ Error sending distance to desktop: {e}")
        time.sleep(5)  # Send every 5 seconds

@app.route('/control_led', methods=['POST'])
def control_led():
    """Control LED on Raspberry Pi"""
    data = request.get_json()
    if 'state' in data:
        if data['state'] == 'on':
            GPIO.output(LED_PIN, GPIO.HIGH)
            print("💡 LED Turned ON")
            return jsonify({"status": "LED turned on"}), 200
        elif data['state'] == 'off':
            GPIO.output(LED_PIN, GPIO.LOW)
            print("💡 LED Turned OFF")
            return jsonify({"status": "LED turned off"}), 200

    return jsonify({"error": "Invalid request"}), 400

if __name__ == "__main__":
    ir_thread = threading.Thread(target=monitor_ir)
    ir_thread.daemon = True
    ir_thread.start()

    distance_thread = threading.Thread(target=send_distance_continuously)
    distance_thread.daemon = True
    distance_thread.start()

    app.run(host='0.0.0.0', port=5000)
