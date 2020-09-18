from flask import Flask, request, render_template, Response, jsonify
from camera import VideoCamera
from nocache import nocache
from relay_pi import Relay
import time
import datetime
import arrow

app = Flask(__name__)
app.debug = False # Torne isso False se voce nao estiver mais depurando

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/temp")
def temp():
	import sys
	import Adafruit_DHT
	humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, 4)
	if humidity is not None and temperature is not None:
		return render_template("temp.html",temp=temperature,hum=humidity)
	else:
		# return render_template("no_sensor.html")
		return render_template("temp.html",temp="*",hum="*")

@app.route("/dataset", methods=['GET']) #Adicionar limites de datas no URL
                                        #Argumentos: de=2015-03-04 & ate=2015-03-05

def dataset():
	temperatures, humidities, acesso, timezone, from_date_str, to_date_str = get_records()
	
	# Crie novas tabelas de registros para que os datetimes sejam ajustados de volta ao fuso horario do navegador do usuario.
	time_adjusted_temperatures = []
	time_adjusted_humidities   = []
	time_adjusted_acesso	   = []
	for record in temperatures:
		#local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm").to(timezone)
		local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm")
		time_adjusted_temperatures.append([local_timedate.format('YYYY-MM-DD HH:mm'), round(record[2],2)])

	for record in humidities:
		#local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm").to(timezone)
		local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm")
		time_adjusted_humidities.append([local_timedate.format('YYYY-MM-DD HH:mm'), round(record[2],2)])

	for record in acesso:
		#local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm").to(timezone)
		local_timedate = arrow.get(record[1], "YYYY-MM-DD HH:mm")
		time_adjusted_acesso.append([local_timedate.format('YYYY-MM-DD HH:mm'), record[2]])

	print "Renderizando dataset.html de %s, de %s ate %s." % (timezone, from_date_str, to_date_str)

	return render_template("dataset.html",	timezone		= timezone,
                               temp 			= time_adjusted_temperatures,
                               hum 			= time_adjusted_humidities,
                               acesso = time_adjusted_acesso,
                               from_date 		= from_date_str,
                               to_date 		= to_date_str,
                               temp_items 		= len(temperatures),
                               query_string	= request.query_string, #Essa query string e usada pelo link Plotly
                               hum_items 		= len(humidities))
    
def get_records():
	import sqlite3
	from_date_str 	= request.args.get('from',time.strftime("%Y-%m-%d 00:00")) #Obtenha o valor da data do URL
	to_date_str 	= request.args.get('to',time.strftime("%Y-%m-%d %H:%M")) #Obtenha o valor da data do URL
	timezone 		= request.args.get('timezone','Etc/UTC');
	range_h_form	= request.args.get('range_h','');  # Retornara uma string, se o campo range_h existir na solicitacao
	range_h_int 	= "nan"   #inicializa esta variavel com um nao numero

	print "REQUEST: "
	print request.args
	
	try: 
		range_h_int	= int(range_h_form)
	except:
		print "range_h_form nao e um numero"

	print "Recebido do navegador: %s \n %s \n %s \n %s" % (from_date_str, to_date_str, timezone, range_h_int)
	
	if not validate_date(from_date_str):			# validando a data antes de envia-la ao DB
		from_date_str 	= time.strftime("%Y-%m-%d 00:00")
	if not validate_date(to_date_str):
		to_date_str 	= time.strftime("%Y-%m-%d %H:%M")
	print 'Mostrando registro de %s ate %s em %s.' % (from_date_str,to_date_str,timezone)
	# Criando o objeto datetime para converter em UTC a partir do horario local do navegador
	from_date_obj       = datetime.datetime.strptime(from_date_str,'%Y-%m-%d %H:%M')
	to_date_obj         = datetime.datetime.strptime(to_date_str,'%Y-%m-%d %H:%M')

	# Se range_h e definido, nao precisamos de from e to times
	if isinstance(range_h_int,int):	
		arrow_time_from = arrow.utcnow().replace(hours=-range_h_int)
		arrow_time_to   = arrow.utcnow()
		from_date_utc   = arrow_time_from.strftime("%Y-%m-%d %H:%M")	
		to_date_utc     = arrow_time_to.strftime("%Y-%m-%d %H:%M")
		from_date_str   = arrow_time_from.to(timezone).strftime("%Y-%m-%d %H:%M")
		to_date_str	    = arrow_time_to.to(timezone).strftime("%Y-%m-%d %H:%M")
	else:
		# Converter os dados em UTC para que possamos recuperar os registros apropriados do banco de dados
		from_date_utc   = arrow.get(from_date_obj, timezone).to('Etc/UTC').strftime("%Y-%m-%d %H:%M")	
		to_date_utc     = arrow.get(to_date_obj, timezone).to('Etc/UTC').strftime("%Y-%m-%d %H:%M")

	print("From date: "+from_date_utc+" - To date: "+to_date_utc)
	conn = sqlite3.connect('/app.db')
	curs = conn.cursor()
	curs.execute("SELECT * FROM temperatures WHERE rDatetime BETWEEN ? AND ?", (from_date_utc.format('YYYY-MM-DD HH:mm'), to_date_utc.format('YYYY-MM-DD HH:mm')))
	temperatures = curs.fetchall()
	curs.execute("SELECT * FROM humidities WHERE rDatetime BETWEEN ? AND ?", (from_date_utc.format('YYYY-MM-DD HH:mm'), to_date_utc.format('YYYY-MM-DD HH:mm')))
	humidities = curs.fetchall()	
	curs.execute("SELECT * FROM acesso WHERE rDatetime BETWEEN ? AND ?", (from_date_utc.format('YYYY-MM-DD HH:mm'), to_date_utc.format('YYYY-MM-DD HH:mm')))
	acesso = curs.fetchall()
	conn.close()

	return [temperatures, humidities, acesso, timezone, from_date_str, to_date_str]

#=============================================================================================================================================#
#	GRAFICOS PLOTLY
#=============================================================================================================================================#

@app.route("/to_plotly", methods=['GET'])  #Este metodo enviara os dados para Ploty.

def to_plotly():
	import plotly
	import plotly.plotly as py
	from plotly.graph_objs import *
	plotly.tools.set_credentials_file(username='YOUR USERNAME', api_key='YOUR API KEY')

	temperatures, humidities, acesso, timezone, from_date_str, to_date_str = get_records()
	
	# Crie novas tabelas de registros para que os datetimes sejam ajustados de volta ao fuso horario do navegador do usuario.
	time_series_adjusted_tempreratures  = []
	time_series_adjusted_humidities 	= []
	time_series_temprerature_values 	= []
	time_series_humidity_values 		= []

	for record in temperatures:
		local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm").to(timezone)
		time_series_adjusted_tempreratures.append(local_timedate.format('YYYY-MM-DD HH:mm'))
		time_series_temprerature_values.append(round(record[2],2))

	for record in humidities:
		local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm").to(timezone)
		time_series_adjusted_humidities.append(local_timedate.format('YYYY-MM-DD HH:mm')) # Melhor para passar datetime no texto
		time_series_humidity_values.append(round(record[2],2)) # Para usar Plotly respeite isso

	temp = Scatter(
        		x=time_series_adjusted_tempreratures,
        		y=time_series_temprerature_values,
        		name='Temperatura'
                )
	hum = Scatter(
        		x=time_series_adjusted_humidities,
        		y=time_series_humidity_values,
        		name='Umidade',
        		yaxis='y2'
                )

	data = Data([temp, hum])

	layout = Layout(
            title="Temperatura e Umidade",
            xaxis=XAxis(
                type='date',
                autorange=True
                ),
            yaxis=YAxis(
                #title='&#176; C',
                title='%sC C',
                type='linear',
                autorange=True
                ),
            yaxis2=YAxis(
                title='%',
                type='linear',
                autorange=True,
                overlaying='y',
                side='right'
                )
            )
	fig = Figure(data=data, layout=layout)
	plot_url = py.plot(fig)
	#plot_url = py.plot(fig, filename='temp_hum')

	return plot_url

def validate_date(d):
    try:
        datetime.datetime.strptime(d, '%Y-%d-%m %H:%M')
        return True
    except ValueError:
        return False

#=============================================================================================================================================#
#	STREAMING DE VIDEO
#=============================================================================================================================================#

video_camera = None
global_frame = None

@app.route('/record_status', methods=['POST'])
def record_status():
    global video_camera
    if video_camera == None:
        video_camera = VideoCamera()

    json = request.get_json()

    status = json['status']

    if status == "true":
        video_camera.start_record()
        return jsonify(result="started")
    else:
        video_camera.stop_record()
        return jsonify(result="stopped")

def video_stream():
    global video_camera 
    global global_frame

    if video_camera == None:
        video_camera = VideoCamera()
        
    while True:
        frame = video_camera.get_frame()

        if frame != None:
            global_frame = frame

            yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + global_frame + b'\r\n')

@app.route('/video_viewer')
def video_viewer():
    return Response(video_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

#=============================================================================================================================================#
#	CONTROLE DOS RELES
#=============================================================================================================================================#

relays = []
ports = []
names = []
checkeds = []

@app.route('/static/css/')
@nocache
def static_css(path):
	return app.send_static_file(path)

@app.route('/static/js/')
@nocache
def static_js(path):
	return app.send_static_file(path)

@app.route('/con<string:relay_id>/<string:state>')
@nocache
def relay_routing(relay_id,state):
	global relays
	global checkeds
	checkeds[int(relay_id)-1] = str(state)
	relays[int(relay_id)-1].go(state)
	return 'ok'

@app.route("/rele")
@nocache
def rele():
	global ports
	global names
	global checkeds
	return render_template('rele.html',ports=ports,names=names,checkeds=checkeds)

def init():
	global ports
	global names
	global relays
	global checkeds

	inverse = True

	ports = ['13','11','12']
	names = ['Telefone','Internet','Lampada']
	checkeds = ['off' for _ in names]
	relays = [Relay(int(port),inverse) for port in ports]

#=============================================================================================================================================#
#	INICIAR O SISTEMA
#=============================================================================================================================================#

if __name__ == "__main__":
	init()
	app.run(
		host = "0.0.0.0",
		port = 8080,
		#debug = True,
		threaded=True
		)