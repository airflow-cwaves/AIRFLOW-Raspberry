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

pin = 2

# gas
bus = smbus.SMBus(1)
AINO = 0x40
LED = 25

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
        
        # gas
        try:
            bus.write_byte(0x48, AINO)
            first = bus.read_byte(0x48)
            gas = bus.read_byte(0x48)
            time.sleep(0.5)
            print("input = %d / first = %d" % (gas, first))
            while True:
                port="/dev/ttyAMA0"
                ser=serial.Serial(port, baudrate=9600, timeout=0.5)
                dataout = pynmea2.NMEAStreamReader()
                newdata=ser.readline()
                
                if newdata[0:6] == b'$GPRMC':
                    newmsg=pynmea2.parse(newdata.decode())
                    lat=newmsg.latitude
                    lng=newmsg.longitude
                    gps = "Latitude=" + str(lat) + "and Longitude=" + str(lat)
                    print(gps)
                    
                    doc_air = db.collection(u'airflow').document()
        
                    doc_air.set({
                        u'Humidity' : humidity,
                        u'Temperature' : temperature,
                        u'Gas' : gas,
                        u'Latitude' : str(lat),
                        u'Logitude' : str(lat),
                        u'Time': datetime.now().strftime('%Y.%m.%d - %H:%M:%S'),
                        u'Check' : False,      
                    })
                    break
                
                
                
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            
        
        time.sleep(60)
    

            
    else:
        print('fail')


