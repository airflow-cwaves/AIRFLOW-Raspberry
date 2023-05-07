#!/usr/bin/python3
import Adafruit_DHT
import RPi.GPIO as GPIO
import time
import smbus
import serial
import string
import pynmea2
from datetime import datetime

GPIO.setmode(GPIO.BCM) # GPIO BCM


LED = 25 # BCM P21
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# humidity & temperature
GPIO.setwarnings(False)
sensor = Adafruit_DHT.DHT11

pin = 11

# gas, dust
bus = smbus.SMBus(1)

DEVICE_ADDR = 0x48  # PCF8591 모듈의 I2C 주소 (기본값: 0x48)
GP2Y1014AU_PIN = 0   # PCF8591 AIN0 pin
MQ5_PIN = 1

def read_adc(pin):
    """Read analog input from the specified pin."""
    bus.write_byte(DEVICE_ADDR, pin)  # set PCF8591 control byte to select the specified pin
    value = bus.read_byte(DEVICE_ADDR) # read the analog input value
    return value

# PCF8591에서 측정된 값을 읽어와 미세먼지 농도 계산
def dust_density():
    """Calculate and return the dust density."""
    """
    V_LED = 5  # LED voltage
    V_OC = read_adc(GP2Y1014AU_PIN) / 255 * 3.3  # output voltage of GP2Y1014AU
    dust_density = 0.17 * V_OC * V_LED / (V_OC + 0.1)  # dust density calculation (unit: pcs/0.01cf)

        return dust_density
    """
    # GP2Y1014AU에서 측정한 아날로그 값을 PCF8591의 A0 채널에서 읽어옴
    value = bus.read_byte_data(DEVICE_ADDR, GP2Y1014AU_PIN)
    
    # 미세먼지 농도 계산
    voltage = value * 3.3 / 255 # PCF8591의 입력 전압 범위는 0~3.3V
    dust_density = 0.17 * voltage - 0.1 # GP2Y1014AU의 선형 방정식을 이용하여 미세먼지 농도 계산
    return dust_density*100

# Define GP2Y1014AU dust sensor parameters
VCC = 5.0  # Supply voltage

# Define MQ-5 gas sensor parameters
RL_VALUE = 10.0  # Load resistance on the board, in kilo ohms
RO_CLEAN_AIR = 9.83  # Clean air resistance, in kilo ohms
GAS_HYDROGEN = 0  # Hydrogen gas
GAS_LPG = 1  # LPG gas
GAS_METHANE = 2  # Methane gas
GAS_CARBON_MONOXIDE = 3  # Carbon Monoxide gas
GAS_ALCOHOL = 4  # Alcohol gas
GAS_SMOKE = 5  # Smoke gas

# Define MQ-5 gas sensor read function
def read_gas(gas_type):
    raw = read_adc(MQ5_PIN)
    voltage = raw / 255.0 * VCC
    RS = RL_VALUE * (VCC - voltage) / voltage
    if gas_type == GAS_HYDROGEN:
        print("Hydrogen gas")
        GAS_R0 = 4.4
        GAS_SLOPE = -1.03
    elif gas_type == GAS_LPG:
        #print("LPG gas")
        GAS_R0 = 3.5
        GAS_SLOPE = -0.76
    elif gas_type == GAS_METHANE:
        #print("Methane gas")
        GAS_R0 = 4.4
        GAS_SLOPE = -1.03
    elif gas_type == GAS_CARBON_MONOXIDE:
        print("Carbon Monoxide gas")
        GAS_R0 = 4.4
        GAS_SLOPE = -1.03
    elif gas_type == GAS_ALCOHOL:
        print("Alcohol gas")
        GAS_R0 = 3.5
        GAS_SLOPE = -0.86
    elif gas_type == GAS_SMOKE:
        #print("Smoke gas")
        GAS_R0 = 3.5
        GAS_SLOPE = -0.86
    else:
        return -1
    ratio = RS / RO_CLEAN_AIR
    gas = GAS_R0 * (ratio ** GAS_SLOPE)
    return gas


def gas_concentration():
    """Calculate and return the gas concentration."""
    V_OC = read_adc(MQ5_PIN) / 255 * 3.3  # output voltage of MQ-5 gas sensor
    R_load = 10  # load resistor value (unit: kohm)
    R_s = (3.3 - V_OC) / V_OC * R_load  # sensor resistance (unit: kohm)
    gas_concentration = 0.4 * R_s  # gas concentration calculation (unit: ppm)
    return gas_concentration

# firebase
cred = credentials.Certificate("airflow-b4245-firebase-adminsdk-ctoqi-9241bc952a.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
GPIO.setup(LED, GPIO.OUT)

while (1) :
    if humidity is not None and temperature is not None :
        print('Temp={0:0.1f}*C Humidity={1:0.1f}'.format(temperature, humidity))
        
        GPIO.output(LED, GPIO.HIGH)
        time.sleep(0.5)

        GPIO.output(LED, GPIO.LOW)
        time.sleep(0.5)
        
        # gas, dust
        try:
            dust = float(dust_density())
            print(dust_density())
            print(float(dust_density()))
            print("finedust: %.2f ug/m^3 finedust2: %.2f ug/m3" % (dust_density(), dust))
            gas = float(gas_concentration())
            gas_methane = float(read_gas(GAS_METHANE))
            print("here: %.2f " % gas_methane)
            gas_lpg = float(read_gas(GAS_LPG))
            print("here: %.2f " % read_gas(GAS_LPG))
            gas_smoke = float(read_gas(GAS_SMOKE))
            print("here: %.2f " % read_gas(GAS_SMOKE))
            
            
            print("finedust2: %.2f ug/m3" % dust)
            print("Dust density: {:.2f} pcs/0.01cf, Gas concentration: {:.2f} ppm".format(dust, gas))
            print("")
            time.sleep(1)
            while True:
                port="/dev/ttyAMA0"
                ser=serial.Serial(port, baudrate=9600, timeout=0.5)
                dataout = pynmea2.NMEAStreamReader()
                newdata=ser.readline()
                
                if newdata[0:6] == b'$GPRMC':
                    newmsg=pynmea2.parse(newdata.decode())
                    lat=newmsg.latitude
                    lng=newmsg.longitude
                    gps = "Latitude=" + str(lat) + "and Longitude=" + str(lng)
                    print(gps)
                    
                    doc_air = db.collection(u'airflow').document()
        
                    doc_air.set({
                        u'Humidity' : humidity,
                        u'Temperature' : temperature,
                        u'Dust' : round(dust, 6),
                        u'Gas' : round(gas, 6),
                        u'Gas_methane' : round(gas_methane, 6),
                        u'Gas_lpg' : round(gas_lpg,6),
                        u'Gas_smoke' : round(gas_smoke,6),
                        u'Latitude' : round(float(lat), 6),
                        u'Logitude' : round(float(lng), 6),
                        u'Time': datetime.now().strftime('%Y.%m.%d - %H:%M:%S'),
                        u'Check' : True,      
                    })
                    break
                
                
                
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            
        
        time.sleep(60)
    

            
    else:
        print('fail')


