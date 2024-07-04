# Import necessary modules
import network
import socket
import time
import random
from machine import Pin, ADC

# Create an LED object on pin 'LED'
led = Pin('LED', Pin.OUT)

# Wi-Fi credentials
ssid = 'WIFI NAME'
password = 'WIFI PASSWORD'

# HTML for the webpage
def webpage(random_value, state, temperatureC, temperatureF, ip_address):
    html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pico Web Server</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                form {{ margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <h1>Raspberry Pi Pico Web Server</h1>
            <h2>Information</h2>
            <p>IP address: {ip_address}</p>
            <h2>LED Control</h2>
            <form action="./lighton">
                <input type="submit" value="Light on" />
            </form>
            <form action="./lightoff">
                <input type="submit" value="Light off" />
            </form>
            <form action="./lightblink">
                <input type="submit" value="Light blink" />
            </form>
            <p>LED state: {state}</p>
            <h2>Fetch New Value</h2>
            <form action="./value">
                <input type="submit" value="Fetch value" />
            </form>
            <p>Fetched value: {random_value}</p>
            <h2>Temperature Measurement</h2>
            <p>Temperature in Celsius: {temperatureC:.2f}</p>
            <p>Temperature in Fahrenheit: {temperatureF:.2f}</p>
            <h2>Shutdown</h2>
            <form action="./shutdown">
                <input type="submit" value="Shutdown" />
            </form>
        </body>
        </html>
        """
    return str(html)

# Connect to WLAN
def connect_to_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    connection_timeout = 10
    while connection_timeout > 0:
        if wlan.status() >= 3:
            break
        connection_timeout -= 1
        print('Waiting for Wi-Fi connection ...')
        time.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('Failed to establish a network connection')
    else:
        print('Connection successful!')
        print('IP address:', wlan.ifconfig()[0])
    return wlan

# Initialize the web server
def init_web_server():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen()
    print('Listening on', addr)
    return s

# Read internal temperature
def read_internal_temperature(temp_sensor):
    adc_value = temp_sensor.read_u16()
    voltage = adc_value * (3.3 / 65535.0)
    temperature_celsius = 27 - (voltage - 0.706) / 0.001721
    return temperature_celsius

# Convert Celsius to Fahrenheit
def celsius_to_fahrenheit(temp_celsius):
    return temp_celsius * (9/5) + 32

# Main loop to listen for connections
def main_loop(s, temp_sensor, wlan):
    state = "OFF"
    random_value = 0

    while True:
        try:
            conn, addr = s.accept()
            print('Got a connection from', addr)
            
            request = conn.recv(1024)
            request = str(request)
            print('Request content = %s' % request)

            try:
                request = request.split()[1]
                print('Request:', request)
            except IndexError:
                pass

            if request == '/lighton?':
                print("LED on")
                led.value(1)
                state = "ON"
            elif request == '/lightoff?':
                led.value(0)
                state = 'OFF'
            elif request == '/lightblink?':
                for i in range(3):
                    led.value(1)
                    time.sleep(0.5)
                    led.value(0)
                    time.sleep(0.5)
                state = "BLINKING"
            elif request == '/value?':
                led.value(1)
                random_value = random.randint(0, 20)
                time.sleep(0.25)
                led.value(0)
            elif request == '/shutdown?':
                print("Shutting down")
                conn.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                conn.send('<h1>Shutting down</h1>')
                conn.close()
                time.sleep(1)
                machine.reset()

            temperatureC = read_internal_temperature(temp_sensor)
            temperatureF = celsius_to_fahrenheit(temperatureC)
            ip_address = wlan.ifconfig()[0]
            response = webpage(random_value, state, temperatureC, temperatureF, ip_address)

            conn.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            conn.send(response)
            conn.close()

        except OSError as e:
            conn.close()
            print('Connection closed')
        except Exception as ex:
            print('Exception:', ex)
            conn.close()

# Setup
wlan = connect_to_wifi(ssid, password)
s = init_web_server()
temp_sensor = ADC(4)

# Run the main loop
main_loop(s, temp_sensor, wlan)
