import utime
import network
import socket
import urandom
from machine import Pin, I2C
from dht import DHT11
from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd

# --- LCD Setup ---
I2C_ADDR     = 0x27
I2C_NUM_ROWS = 4
I2C_NUM_COLS = 20

try:
    i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
    lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)
    # Initial LCD test
    lcd.clear()
    lcd.putstr("LiveGrow")
    utime.sleep(2)
except Exception as e:
    print("LCD initialization error:", e)
    raise

# --- DHT11 Setup ---
dataPin = 16
sensorPin = Pin(dataPin, Pin.OUT, Pin.PULL_DOWN)
sensor = DHT11(sensorPin)

# --- Wi-Fi Setup ---
SSID = ""
PASSWORD = ""

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(SSID, PASSWORD)
        max_wait = 15
        while max_wait > 0:
            if wlan.status() >= 3:  # Connected
                break
            print("Waiting for connection...")
            max_wait -= 1
            utime.sleep(1)

    if wlan.status() != 3:
        print("WiFi connection failed, retrying...")
        return None
    else:
        print("Connected. IP:", wlan.ifconfig()[0])
        return wlan

def setup_socket():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    s.settimeout(1)
    print("Socket ready on port 80")
    return s

# --- Initialize ---
wlan = connect_wifi()
s = setup_socket() if wlan else None

# --- Message Storage ---
LCD_COLS = 16
LCD_ROWS = 2
message = "No message"


def split_message(msg, cols=16):
    if not msg.strip():
        return [""]
    words = msg.split()
    lines = []
    current_line = ""
    for word in words:
        if len(word) > cols:
            if current_line:
                lines.append(current_line.rstrip())
                current_line = ""
            lines.append(word[:cols])
            continue
        space_needed = len(current_line) + (1 if current_line else 0) + len(word)
        if space_needed <= cols:
            current_line = current_line + " " + word if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def display_scrolling_message(msg, delay=3):
    try:
        lines = split_message(msg, LCD_COLS)
        if not lines:
            lcd.clear()
            lcd.putstr("No message")
            return
        if len(lines) <= LCD_ROWS:
            lcd.clear()
            for i, line in enumerate(lines):
                lcd.move_to(0, i)
                lcd.putstr(line[:LCD_COLS])
            utime.sleep(delay)
            return
        for start in range(0, len(lines), LCD_ROWS):
            lcd.clear()
            for i in range(LCD_ROWS):
                if start + i < len(lines):
                    lcd.move_to(0, i)
                    line = lines[start + i]
                    lcd.putstr(line[:LCD_COLS])
            utime.sleep(delay)
    except Exception as e:
        print(f"Display scrolling error: {e}")
        lcd.clear()
        lcd.putstr("Display Error")
        utime.sleep(2)

def display_sensor_readings():
    try:
        sensor.measure()
        tempC = sensor.temperature()
        tempF = int(tempC * 9 / 5 + 32)
        hum = sensor.humidity()
        lcd.clear()
        lcd.putstr("Temp: {} F\n".format(tempF))
        lcd.putstr("Humidity: {} %".format(hum))
        utime.sleep(5)
    except Exception as e:
        print("Sensor Error:", e)
        lcd.clear()
        lcd.putstr("Sensor Error")
        utime.sleep(2)

# --- Main Loop ---
while True:
    try:
        # 🔹 Reconnect Wi-Fi if dropped
        if not wlan or wlan.status() != 3:
            print("Reconnecting WiFi...")
            wlan = connect_wifi()
            if wlan:
                s = setup_socket()
            else:
                utime.sleep(5)
                continue

        # 🔹 Socket handling
        try:
            cl, addr = s.accept()
            print('Client connected from', addr)
            request = cl.recv(1024).decode()

              # Parse GET request for user and message
            if 'GET /' in request:
                # --- Extract 'user' ---
                user = ""
                start = request.find('user=')
                if start != -1:
                    start += len('user=')
                    end_amp = request.find('&', start)
                    end_space = request.find(' ', start)
                    if end_amp != -1:
                        end = end_amp
                    elif end_space != -1:
                        end = end_space
                    else:
                        end = len(request)
                    user = request[start:end].replace('+', ' ').replace('%20', ' ')

                # --- Extract 'message' ---
                msg = ""
                start = request.find('message=')
                if start != -1:
                    start += len('message=')
                    end_amp = request.find('&', start)
                    end_space = request.find(' ', start)
                    if end_amp != -1:
                        end = end_amp
                    elif end_space != -1:
                        end = end_space
                    else:
                        end = len(request)
                    msg = request[start:end].replace('+', ' ').replace('%20', ' ')

                if msg:
                    message = msg
                    print(f"{user}: {message}")
                    display_scrolling_message(f"{user}: {message}")

            cl.send('HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n')
            cl.send('Message received')
            cl.close()

        except OSError as e:
            if e.args[0] == 110:  # timeout
                pass
            else:
                print("Socket error:", e)
                s.close()
                s = setup_socket()  # 🔹 Reset socket

        # --- Random display selection ---
        r = urandom.getrandbits(7) % 100
        if r < 5:
            display_scrolling_message(message)
        elif r < 15:
            lcd.clear()
            lcd.putstr("LiveGrow")
            utime.sleep(5)
        else:
            display_sensor_readings()

    except Exception as e:
        print("Main loop error:", e)
        lcd.clear()
        lcd.putstr("Main Error")
        utime.sleep(2)
