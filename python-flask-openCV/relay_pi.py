try:
	import RPi.GPIO as GPIO
except ImportError:
	raise ImportError("A biblioteca RPi.GPIO  nao pode ser importada!")

class Relay:

	def __init__(self, port, inverse):
		self.inverse = inverse
		GPIO.setwarnings(False)
		GPIO.setmode(GPIO.BOARD)
		GPIO.setup(port, GPIO.OUT)
		GPIO.output(port, inverse)

		self.port = port
	   
	def go(self, value):
		if (value == "on"):
			GPIO.output(self.port, not self.inverse)
		else:
			GPIO.output(self.port, self.inverse)
		
