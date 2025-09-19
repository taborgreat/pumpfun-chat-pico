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

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

# Wait for connection
max_wait = 10
while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print('Waiting for connection...')
    utime.sleep(1)

if wlan.status() != 3:
    raise RuntimeError('Network connection failed')
else:
    print('Connected')
    status = wlan.ifconfig()
    print('IP address:', status[0])

# --- Web Server Setup ---
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
s.settimeout(0.5)  # Non-blocking socket with 100ms timeout

# --- Message Storage ---
message = "No message"

# LCD Word Wrapping System for 2x16 Display

# Configuration
LCD_COLS = 16
LCD_ROWS = 2

# Message storage
message = "No message"

def split_message(msg, cols=16):
    """
    Split a message into lines that fit LCD display with word wrapping.
    
    Rules:
    - Fit as many words on one line as possible without cutting words
    - Spaces count as one character
    - If a word is longer than 16 characters, give it one line and truncate
    
    Args:
        msg: The message string to split
        cols: Number of columns (default 16)
    
    Returns:
        List of strings, each representing one line
    """
    if not msg.strip():
        return [""]
    
    words = msg.split()
    lines = []
    current_line = ""
    
    for word in words:
        # If word is longer than available columns, truncate it and give it its own line
        if len(word) > cols:
            # If current line has content, save it first
            if current_line:
                lines.append(current_line.rstrip())
                current_line = ""
            # Add truncated word as its own line
            lines.append(word[:cols])
            continue
        
        # Calculate space needed: current line + space (if needed) + word
        space_needed = len(current_line) + (1 if current_line else 0) + len(word)
        
        if space_needed <= cols:
            # Word fits on current line
            if current_line:
                current_line += " " + word
            else:
                current_line = word
        else:
            # Word doesn't fit, start new line
            if current_line:
                lines.append(current_line)
            current_line = word
    
    # Add final line if it has content
    if current_line:
        lines.append(current_line)
    
    return lines

def display_scrolling_message(msg, delay=3):
    """
    Display message scrolling 2 lines at a time until done.
    
    Args:
        msg: Message to display
        delay: Delay between screen updates in seconds
    """
    try:
        lines = split_message(msg, LCD_COLS)
        
        # If no lines or empty message
        if not lines:
            lcd.clear()
            lcd.putstr("No message")
            return
        
        # If message fits in 2 lines or less, display once
        if len(lines) <= LCD_ROWS:
            lcd.clear()
            for i, line in enumerate(lines):
                lcd.move_to(0, i)
                lcd.putstr(line[:LCD_COLS])  # Ensure we don't exceed column limit
            utime.sleep(delay)
            return
        
        # Scroll through message 2 lines at a time
        for start in range(0, len(lines), LCD_ROWS):
            lcd.clear()
            # Display up to 2 lines starting from 'start' index
            for i in range(LCD_ROWS):
                if start + i < len(lines):
                    lcd.move_to(0, i)
                    line = lines[start + i]
                    lcd.putstr(line[:LCD_COLS])  # Ensure line fits
            utime.sleep(delay)
            
    except Exception as e:
        print(f"Display scrolling error: {e}")
        lcd.clear()
        lcd.putstr("Display Error")
        utime.sleep(2)


def display_sensor_readings():
    """Display temperature and humidity readings."""
    try:
        sensor.measure()
        tempC = sensor.temperature()
        tempF = int(tempC * 9 / 5 + 32)  # Convert to Fahrenheit
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
                    end = request.find(' ', start)
                    if end == -1:
                        end = request.find('\r', start)
                    user = request[start:end].replace('+', ' ').replace('%20', ' ')

              # --- Extract 'user' ---
                user = ""
                start = request.find('user=')
                if start != -1:
                    start += len('user=')
                    end_amp = request.find('&', start)   # Stop at & if present
                    end_space = request.find(' ', start) # Stop at space if no &
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


                # If message is present, store it and display
                if msg:
                    message = msg
                    print(f"{user}: {message}")
                    display_scrolling_message(f"{user}: {message}")

            # Send minimal HTTP response
            cl.send('HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n')
            cl.send('Message received')
            cl.close()

        except OSError as e:
            if e.args[0] == 110:  # Timeout
                pass
            else:
                print("Socket error:", e)

        
        # --- Random display selection ---
        r = urandom.getrandbits(7) % 100  # random number 0–99

        if r < 5:  # 5% chance
            display_scrolling_message(message)
        elif r < 15:  # next 10% chance
            lcd.clear()
            lcd.putstr("LiveGrow")
            utime.sleep(5)
        else:  # remaining 85% chance
            display_sensor_readings()
    except Exception as e:
        print("Main loop error:", e)
        lcd.clear()
        lcd.putstr("Main Error")
        utime.sleep(2)
