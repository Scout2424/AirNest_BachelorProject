import select
import board
import adafruit_dht
import requests
import spidev
import RPi.GPIO as GPIO
from datetime import datetime
from gpiozero import LED, Button
from signal import pause
from threading import Thread, Event
import csv
import os
import math


def wait(seconds):
    select.select([], [], [], seconds)

#  SPI Setup (for MCP3208)
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000

def read_mcp3208(channel):
    if channel < 0 or channel > 7:
        raise ValueError("Channel must be between 0 and 7")
    cmd = [0x06 | (channel >> 2),
           (channel & 0x03) << 6,
           0x00]
    reply = spi.xfer2(cmd)
    value = ((reply[1] & 0x0F) << 8) | reply[2]
    return value

def adc_to_voltage(raw_value, vref=3.3):
    return (raw_value / 4095.0) * vref

#  MCP3208 Channel Map
CHANNEL_MQ135 = 0
CHANNEL_MQ3   = 1
CHANNEL_MQ6   = 2
CHANNEL_MQ7   = 3
CHANNEL_MQ8   = 4
CHANNEL_SOUND = 5   #background level

#  LED and Button
led  = LED(4)    # Blue 
led2 = LED(5)    # Red  

button = Button(17, pull_up=False)


SOUND_PIN = 24
GPIO.setmode(GPIO.BCM)
GPIO.setup(SOUND_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

sound_event_count = 0

def on_sound_detected(channel):
    global sound_event_count
    sound_event_count += 1

GPIO.add_event_detect(
    SOUND_PIN,
    GPIO.BOTH,
    callback=on_sound_detected,
    bouncetime=50
)

#  Neighbourhood (runs once at startup)
print("─" * 40)
user_input = input("Enter your neighbourhood (or press Enter to skip): ").strip()
NEIGHBOURHOOD = user_input if user_input else "empty"
print(f"Neighbourhood set to: {NEIGHBOURHOOD}")
print("─" * 40)


SENSOR_PARAMS = {
    "MQ135": {
        "a": 110.47, "b": -2.862,
        "Ro": 47059,
        "label": "eCO2",
        "unit": "ppm"
    },
    "MQ3": {
        "a": 0.3934, "b": -1.504,
        "Ro": 9870,
        "label": "Alcohol/Benzene",
        "unit": "ppm"
    },
    "MQ6": {
        "a": 1000.5, "b": -2.180,
        "Ro": 8880,
        "label": "LPG/Butane",
        "unit": "ppm"
    },
    "MQ7": {
        "a": 99.042, "b": -1.518,
        "Ro": 28712,
        "label": "Carbon Monoxide",
        "unit": "ppm"
    },
    "MQ8": {
        "a": 976.97, "b": -0.688,
        "Ro": 54886,
        "label": "Hydrogen",
        "unit": "ppm"
    },
}


PPM_THRESHOLDS = {
    "MQ135": 1200,
    "MQ3":   50,
    "MQ6":   1600,
    "MQ7":   35,
    "MQ8":   1000,
}

TEMP_REF = 20.0   # °C — reference temperature for correction
HUM_REF  = 65.0   # %  — reference humidity for correction

def temperature_humidity_correction(temp_c, humidity):
    #derived from Hanwei sensor application notes.
    try:
        return (
            math.pow(temp_c / TEMP_REF, -0.0103) *
            math.pow(humidity / HUM_REF, -0.0182) *
            0.9987
        )
    except (ValueError, ZeroDivisionError):
        return 1.0

def compute_ppm(vread, sensor_key, temp_c, humidity, RL=2000, Vc=5.0):
    """
     PPM computation
    1. Correct Vread for the 1kΩ+2kΩ voltage divider  (× 1.5)
    2. Derive Rs from the corrected output voltage
    3. Apply temperature/humidity correction to Rs
    4. Compute Rs/Ro ratio
    5. Apply curve: PPM = a × (Rs/Ro)^b
    """
    params = SENSOR_PARAMS[sensor_key]
    vout_actual = vread * 1.5

    if vout_actual < 0.01:
        return None                         # signal too low => sensor not ready

    Rs = ((Vc * RL) / vout_actual) - RL
    if Rs <= 0:
        return None                         # sensor output saturated

    Rs_corrected = Rs * temperature_humidity_correction(temp_c, humidity)
    ppm = params["a"] * math.pow(Rs_corrected / params["Ro"], params["b"])

    if ppm < 0 or ppm > 100000:
        return None                         # outside detection range

    return round(ppm, 2)

#  Weather API
OPENWEATHER_API_KEY = "api_key_here"  # only visible corectly in the original code on the local machine

def get_location():
    try:
        response = requests.get("https://ipinfo.io", timeout=3.5)
        data = response.json()
        return data.get("city", "Unknown city"), data.get("country", "Unknown country")
    except Exception as e:
        print("Could not get location:", e)
    return "Unknown city", "Unknown country"

def interpret_weather(description):
    desc = description.lower()
    if "clear"   in desc: return "Sunny"
    elif "cloud"  in desc: return "Cloudy"
    elif "rain"   in desc or "drizzle" in desc: return "Rainy"
    elif "storm"  in desc or "thunder" in desc: return "Stormy"
    elif "snow"   in desc: return "Snowy"
    elif "mist"   in desc or "fog" in desc or "haze" in desc: return "Misty"
    else: return "Unknown"

def get_weather_description(city, country_code):
    try:
        url = (f"http://api.openweathermap.org/data/2.5/weather"
               f"?q={city},{country_code}&appid={OPENWEATHER_API_KEY}&units=metric")
        response = requests.get(url, timeout=4)
        data = response.json()
        return interpret_weather(data["weather"][0]["description"])
    except Exception as e:
        print("Weather API error:", e)
        return "Unknown"

CITY, COUNTRY = get_location()

#  AWS endpoint
#AWS_ENDPOINT = "http://13.61.152.65:8080/api/sensor"
AWS_ENDPOINT = "https://airnest.duckdns.org/api/sensor"


def send_to_aws(data):
    """
    POST sensor data as JSON to  AWS Flask endpoint
    Return True on success or False on error
    Blue LED lights 2 seconds on a successful upload
    """
    try:
        response = requests.post(AWS_ENDPOINT, json=data, timeout=5)
        if response.status_code == 200:
            led.on()
            wait(2)
            led.off()
            return True
        else:
            print(f"  AWS upload failed — status {response.status_code}")
            return False
    except Exception as e:
        print(f"  AWS upload error: {e}")
        return False

#  DHT11
dhtDevice = adafruit_dht.DHT11(board.D23, use_pulseio=False)

#  Button Toggle
run_event = Event()

def toggle_data_sending():
    if run_event.is_set():
        print("Stopping data sending...")
        run_event.clear()
        led.off()
    else:
        print("Starting data sending...")
        run_event.set()

button.when_pressed = toggle_data_sending

#  CSV Setup
csv_file = "sensor_data_log.csv"
csv_headers = [
    "Year", "Month", "Day", "Time",
    "Neighbourhood", "City", "Country",
    "Temperature_C", "Temperature_F", "Humidity", "Weather",
    "MQ135_raw", "MQ3_raw", "MQ6_raw", "MQ7_raw", "MQ8_raw",
    "MQ135_V", "MQ3_V", "MQ6_V", "MQ7_V", "MQ8_V",
    "MQ135_ppm", "MQ3_ppm", "MQ6_ppm", "MQ7_ppm", "MQ8_ppm",
    "Sound_raw", "Sound_V", "Sound_events",
    "Warning"
]

if not os.path.exists(csv_file):
    with open(csv_file, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()

#  Timing
READING_INTERVAL  = 30 * 60   # 30 minutes in seconds
DHT_RETRY_DELAY   = 2         # seconds between DHT11 retry attempts
WARNING_LED_HOLD  = 5         # seconds red LED warning
AWS_LED_HOLD      = 2         # seconds blue LED on

#  Main Data Collection Loop
def read_and_send_data():
    global sound_event_count
    while True:
        if run_event.is_set():
            try:
                # DHT11 with retries
                MAX_RETRIES   = 5
                temperature_c = None
                humidity      = None

                for attempt in range(MAX_RETRIES):
                    try:
                        temperature_c = dhtDevice.temperature
                        humidity      = dhtDevice.humidity
                        if temperature_c is not None and humidity is not None:
                            break
                    except RuntimeError:
                        wait(DHT_RETRY_DELAY)

                if temperature_c is None or humidity is None:
                    print("DHT11 failed after all retries, skipping cycle")
                    wait(READING_INTERVAL)
                    continue

                temperature_f = temperature_c * (9 / 5) + 32

                now           = datetime.now()
                current_year  = now.strftime("%Y")
                current_month = now.strftime("%B")
                current_day   = now.strftime("%A %d")
                current_time  = now.strftime("%H:%M:%S")

                weather_condition = get_weather_description(CITY, COUNTRY)

                mq135_raw = read_mcp3208(CHANNEL_MQ135)
                mq3_raw   = read_mcp3208(CHANNEL_MQ3)
                mq6_raw   = read_mcp3208(CHANNEL_MQ6)
                mq7_raw   = read_mcp3208(CHANNEL_MQ7)
                mq8_raw   = read_mcp3208(CHANNEL_MQ8)
                sound_raw = read_mcp3208(CHANNEL_SOUND)

                mq135_v = adc_to_voltage(mq135_raw)
                mq3_v   = adc_to_voltage(mq3_raw)
                mq6_v   = adc_to_voltage(mq6_raw)
                mq7_v   = adc_to_voltage(mq7_raw)
                mq8_v   = adc_to_voltage(mq8_raw)
                sound_v = adc_to_voltage(sound_raw)

                \
                current_sound_events = sound_event_count
                sound_event_count = 0

                #  PPM Computation
                mq135_ppm = compute_ppm(mq135_v, "MQ135", temperature_c, humidity)
                mq3_ppm   = compute_ppm(mq3_v,   "MQ3",   temperature_c, humidity)
                mq6_ppm   = compute_ppm(mq6_v,   "MQ6",   temperature_c, humidity)
                mq7_ppm   = compute_ppm(mq7_v,   "MQ7",   temperature_c, humidity)
                mq8_ppm   = compute_ppm(mq8_v,   "MQ8",   temperature_c, humidity)

                #  Console Output
                print(f"\n  {current_day} {current_month} {current_year}  |  {current_time}")
                print(f"  {NEIGHBOURHOOD}, {CITY}, {COUNTRY}")
                print(f"  Temp      : {temperature_f:.1f} F / {temperature_c:.1f} C")
                print(f"  Humidity  : {humidity}%")
                print(f"  Weather   : {weather_condition}")
                print(f"  T/H correction: "
                      f"{temperature_humidity_correction(temperature_c, humidity):.4f}")
                print(f"  {'Sensor':<8} {'Raw':>6}  {'Voltage':>8}  {'PPM':>10}  Description")
                print(f"  {'─'*62}")
                for name, raw, v, ppm in [
                    ("MQ135", mq135_raw, mq135_v, mq135_ppm),
                    ("MQ3",   mq3_raw,   mq3_v,   mq3_ppm),
                    ("MQ6",   mq6_raw,   mq6_v,   mq6_ppm),
                    ("MQ7",   mq7_raw,   mq7_v,   mq7_ppm),
                    ("MQ8",   mq8_raw,   mq8_v,   mq8_ppm),
                ]:
                    ppm_str   = f"{ppm:.2f}" if ppm is not None else "N/A"
                    label     = SENSOR_PARAMS[name]["label"]
                    threshold = PPM_THRESHOLDS[name]
                    flag      = " !!" if ppm is not None and ppm > threshold else ""
                    print(f"  {name:<8} {raw:>6}  {v:>7.3f}V  {ppm_str:>10}  "
                          f"{label}  (threshold: {threshold}){flag}")
                print(f"  {'─'*62}")
                print(f"  {'Sound':<8} {sound_raw:>6}  {sound_v:>7.3f}V  "
                      f"{'':>10}  AOUT background level")
                print(f"  {'Sound':<8} {'DOUT':>6}  {'':>8}  "
                      f"{current_sound_events:>10}  events in last 30 min")

                #  Warning Conditions
                ppm_values = {
                    "MQ135": mq135_ppm,
                    "MQ3":   mq3_ppm,
                    "MQ6":   mq6_ppm,
                    "MQ7":   mq7_ppm,
                    "MQ8":   mq8_ppm,
                }
                triggered = [
                    name for name, ppm in ppm_values.items()
                    if ppm is not None and ppm > PPM_THRESHOLDS[name]
                ]

                weather_warning = weather_condition in ["Stormy", "Snowy", "Unknown"]
                heat_warning    = temperature_c > 35 and weather_condition == "Sunny"
                cold_warning    = temperature_c < 0

                warning_message = ""
                if triggered:
                    warning_message = (
                        f"Warning: High PPM detected — {', '.join(triggered)}"
                    )
                elif heat_warning or cold_warning or weather_warning:
                    warning_message = (
                        "Warning: Weather conditions may be harmful to the body"
                    )

                if warning_message:
                    print(f"  !!  {warning_message}")
                    led2.on()
                    wait(WARNING_LED_HOLD)
                    led2.off()

                #  Build Data Dict
                data = {
                    "Year"          : current_year,
                    "Month"         : current_month,
                    "Day"           : current_day,
                    "Time"          : current_time,
                    "Neighbourhood" : NEIGHBOURHOOD,
                    "City"          : CITY,
                    "Country"       : COUNTRY,
                    "Temperature_C" : temperature_c,
                    "Temperature_F" : round(temperature_f, 1),
                    "Humidity"      : humidity,
                    "Weather"       : weather_condition,
                    "MQ135_raw"     : mq135_raw,
                    "MQ3_raw"       : mq3_raw,
                    "MQ6_raw"       : mq6_raw,
                    "MQ7_raw"       : mq7_raw,
                    "MQ8_raw"       : mq8_raw,
                    "MQ135_V"       : round(mq135_v, 3),
                    "MQ3_V"         : round(mq3_v, 3),
                    "MQ6_V"         : round(mq6_v, 3),
                    "MQ7_V"         : round(mq7_v, 3),
                    "MQ8_V"         : round(mq8_v, 3),
                    "MQ135_ppm"     : mq135_ppm if mq135_ppm is not None else "N/A",
                    "MQ3_ppm"       : mq3_ppm   if mq3_ppm   is not None else "N/A",
                    "MQ6_ppm"       : mq6_ppm   if mq6_ppm   is not None else "N/A",
                    "MQ7_ppm"       : mq7_ppm   if mq7_ppm   is not None else "N/A",
                    "MQ8_ppm"       : mq8_ppm   if mq8_ppm   is not None else "N/A",
                    "Sound_raw"     : sound_raw,
                    "Sound_V"       : round(sound_v, 3),
                    "Sound_events"  : current_sound_events,
                    "Warning"       : warning_message
                }

                #  AWS Upload
                if send_to_aws(data):
                    print("  ✅ Data sent to AWS")
                else:
                    print("  ❌ AWS upload failed — data saved to CSV only")

                #  CSV Log
                with open(csv_file, mode='a', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=csv_headers)
                    writer.writerow(data)

            except RuntimeError as error:
                print("Sensor read error (will retry):", error.args[0])
                led.off()
                led2.off()

            except Exception as error:
                dhtDevice.exit()
                spi.close()
                GPIO.cleanup()
                led.off()
                led2.off()
                raise error
        else:
            led.off()
            led2.off()

        wait(READING_INTERVAL)

#  Start
sensor_thread = Thread(target=read_and_send_data, daemon=True)
sensor_thread.start()

print("Station ready. Press the button to start.")
pause()

spi.close()
GPIO.cleanup()