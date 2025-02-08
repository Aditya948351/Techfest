import RPi.GPIO as GPIO
from flask import Flask, jsonify, request
import time
import threading

app = Flask(__name__)

# Define GPIO pins
TRIG_PIN = 17  # Trigger pin
ECHO_PIN = 27  # Echo pin
BUZZER_PIN = 23  # Buzzer pin
LED_PIN = 18  # LED pin

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(LED_PIN, GPIO.OUT)

def measure_distance():
    """Measure the distance using the HC-SR04 ultrasonic sensor."""
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)  # 10μs pulse
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

def rain_detected():
    """Simulate rain detection (Replace with actual sensor logic if available)."""
    return True  # Simulating constant rain detection

@app.route('/get_data', methods=['GET'])
def get_data():
    distance = measure_distance()
    is_raining = rain_detected()
    return jsonify({'distance': distance, 'rain': is_raining})

@app.route('/control_buzzer', methods=['GET'])
def control_buzzer():
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(5)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    return "Buzzer activated for 5 seconds", 200

@app.route('/control_led', methods=['POST'])
def control_led():
    data = request.get_json()
    if 'state' in data:
        if data['state'] == 'on':
            GPIO.output(LED_PIN, GPIO.HIGH)
            return "LED turned on", 200
        elif data['state'] == 'off':
            GPIO.output(LED_PIN, GPIO.LOW)
            return "LED turned off", 200
    return "Invalid request", 400

def sensor_monitoring():
    """Thread to monitor rain detection and activate the buzzer."""
    while True:
        if rain_detected():
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            time.sleep(3)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(3)

if __name__ == "__main__":
    sensor_thread = threading.Thread(target=sensor_monitoring)
    sensor_thread.daemon = True
    sensor_thread.start()

    try:
        app.run(host='0.0.0.0', port=5000)
    finally:
        GPIO.cleanup()  # Clean up GPIO on exit
