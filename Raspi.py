from flask import Flask, jsonify, request
import RPi.GPIO as GPIO
import spidev
import time
import threading

app = Flask(__name__)

# GPIO Pins
TRIG_PIN = 17  # Trigger for Ultrasonic Sensor
ECHO_PIN = 27  # Echo for Ultrasonic Sensor
BUZZER_PIN = 23  # Buzzer for alert
LED_PIN = 18  # LED indicator
GAS_SENSOR_PIN = 22  # Digital output from MQ-2
SPI_CHANNEL = 0  # MCP3008 Channel 0 for Analog Gas Sensor

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(GAS_SENSOR_PIN, GPIO.IN)  # Digital input

# SPI setup for MCP3008
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000

def read_adc(channel):
    """Read analog value from MCP3008 ADC"""
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    return ((adc[1] & 3) << 8) + adc[2]

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
    """Check if gas is detected"""
    return GPIO.input(GAS_SENSOR_PIN) == 0  # LOW means gas detected

@app.route('/get_data', methods=['GET'])
def get_data():
    """Send sensor data to desktop"""
    distance = measure_distance()
    gas_status = gas_detected()
    gas_value = read_adc(SPI_CHANNEL)  # Read analog gas level

    return jsonify({
        'distance': distance,
        'gas_detected': gas_status,
        'gas_value': gas_value
    })

@app.route('/control_buzzer', methods=['POST'])
def control_buzzer():
    """Activate buzzer"""
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(5)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    return "Buzzer activated", 200

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

def sensor_monitoring():
    """Monitor gas levels and trigger buzzer if gas detected"""
    while True:
        if gas_detected():
            print("⚠️ Gas detected! Triggering buzzer!")
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            time.sleep(3)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(3)

if __name__ == "__main__":
    sensor_thread = threading.Thread(target=sensor_monitoring)
    sensor_thread.daemon = True
    sensor_thread.start()

    app.run(host='0.0.0.0', port=5000)
