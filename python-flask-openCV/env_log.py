import sqlite3
import sys
import time
import Adafruit_DHT

def log_values(sensor_id, sensor_id2, temp, hum):
	conn=sqlite3.connect('/home/pi/projetos/rf/tcc_app.db')

	curs=conn.cursor()
	curs.execute("""INSERT INTO temperatures values(datetime(CURRENT_TIMESTAMP, 'localtime'),
         (?), (?))""", (sensor_id,temp))
	curs.execute("""INSERT INTO humidities values(datetime(CURRENT_TIMESTAMP, 'localtime'),
         (?), (?))""", (sensor_id2,hum))
	conn.commit()
	conn.close()

while True:
	humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, 4)
	if humidity is not None and temperature is not None:					
		log_values("1", "2", temperature, humidity)							
	time.sleep(300)                                              			                                     

# aleatoriamente numeros para as variaveis de temperatura e umidade):
# import random
# humidity = random.randint (1,100)
# temperature = random.randint (10,30)