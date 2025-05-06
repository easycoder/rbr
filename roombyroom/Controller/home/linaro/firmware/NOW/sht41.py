from machine import I2C, Pin
import time

# Initialize I2C
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)

def read_sht41(i2c):
    # Send measurement command
    i2c.writeto(0x44, bytes([0xFD]))
    time.sleep_ms(12)
    data = i2c.readfrom(0x44, 6)

    # Process temperature
    temp_raw = (data[0] << 8) | data[1]
    temp = -45 + 175 * (temp_raw / 65535)

    # Process humidity
    hum_raw = (data[3] << 8) | data[4]
    hum = -6 + 125 * (hum_raw / 65535)

    return temp, hum

# Main loop
while True:
    temperature, humidity = read_sht41(i2c)
    print(f"Temperature: {temperature:.2f}°C, Humidity: {humidity:.2f}%")
    time.sleep(2)
