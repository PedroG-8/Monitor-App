from typing import cast
from channels.generic.websocket import WebsocketConsumer

import qrcode
from PIL import Image

import json
from time import sleep

import pathlib
import os

import time
import urllib.request
import requests
import subprocess

consequtive_errors = 0
cloud_content = {}

# Function to generate the QR Code and save it under images folder
def make_qr_code(url):
	qr = qrcode.QRCode(
		version=1,
		error_correction=qrcode.constants.ERROR_CORRECT_H,
		box_size=3,
		border=1,
	)

	qr.add_data(url)
	qr.make(fit=True)
	img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

	img.save("integers/static/images/qr.png")

def manipulate_files():
	# CHECKS NEW FILES. DELETES THE ONES THAT ARE NOT LISTED, DOWNLOADS THE ONES THAT ARE NEW

	global consequtive_errors
	global cloud_content

	try:

		url_10 = 'http://peig2.westeurope.cloudapp.azure.com/api/documents/'

		r = requests.get(url_10, auth=('genix', 'genix'))
		ls = r.json()['results']

		# Get cloud content
		cloud_content = {} # ( "file" , "http://.../file" )
		for item in ls:
			cloud_content[item['downloadlink'].split('/')[-1]] = item['downloadlink']
		print("Cloud content", cloud_content.keys())

		# Removing old files
		#for file in os.listdir(pathlib.Path(__file__).parent.absolute().joinpath('static/images/')):
		#
		#	if file not in cloud_content.keys():
		#		print("Removing", file)
		#		os.remove(pathlib.Path(__file__).parent.absolute().joinpath('static/images/'+file))

		# Downloading new files
		#for filename in cloud_content.keys():

		#	if filename not in os.listdir(pathlib.Path(__file__).parent.absolute().joinpath('static/images/')):

		#		link = cloud_content[filename]
		#		print('Downloading', filename)
				# Download the object
		#		urllib.request.urlretrieve(
		#			link, 'integers/static/images/'+filename)

		consequtive_errors = 0

	except:

		consequtive_errors += 1
		print(consequtive_errors)
		manipulate_files()


# No futuro a maneira de checkar os conteudos podera mudar :D
class WSConsumer(WebsocketConsumer):

	def connect(self):

		# URL will be dynamic later on and called more often
		make_qr_code('http://peig2.westeurope.cloudapp.azure.com/control/3/')

		global cloud_content

		self.accept()

		#contentdir = os.listdir(pathlib.Path(
		#	__file__).parent.absolute().joinpath('static/images/'))

		currentindex = 0

		start = time.time()  # PARA O DELAY DE APRESENTACAO

		start2 = time.time()  # PARA OS DOCS

		while True:

			if time.time() - start2 > 10:
				manipulate_files()
				start2 = time.time()

			elif time.time() - start > 5:

				if len(cloud_content.keys()) > 0:

					#contentdir = os.listdir(pathlib.Path(
					#	__file__).parent.absolute().joinpath('static/images/'))

					# se o diretorio tiver 3 elementos e o meu index for 3 ou maior, passa a zero
					# pq index=3 precisa de 4 elementos
					if currentindex >= len(cloud_content.keys()):
						currentindex = 0

					filename = list(cloud_content.keys())[currentindex]
					currentindex += 1

					extension = filename.split('.')[-1]

					#print(filename, extension)

					print("SWITCHED TO", filename)

					type = 'none'

					if extension in ['png', 'jpg']:
						type = 'img'
					elif extension in ['mp4', 'MOV']:
						type = 'video'

					# print(type)

					self.send(json.dumps({
						'message': filename,
						'type': type
					}))

					myfile = pathlib.Path(
						__file__).parent.absolute().joinpath('log.txt')

					#print("a", myfile)

					with open(myfile, "w") as f:
						f.seek(0)
						f.write(filename)
						f.truncate()

				start = time.time()
			else:

				try:

					global consequtive_errors

					# verificar update e fazer send

					url_1 = 'http://peig2.westeurope.cloudapp.azure.com/api/agentupdates/3/'

					r2 = requests.get(url_1, auth=('genix', 'genix'))
					content_name = r2.json()['contentname']
					content_confirm = r2.json()['content_confirm']
					# TODO
					# Buscar o link dinamico do qr code
					# content_qr = r2.json()['qr_code']
					# Transformar o link em imagem e guardar na pasta static/images


					#print('content_name', content_name)
					#print('content_confirm', content_confirm)


					if (content_confirm == False) and (content_name in cloud_content.keys()):
						extension = content_name.split('.')[-1]

						#print(content_name, extension)

						print("UPDATED TO", content_name)

						type = 'none'

						if extension in ['png', 'jpg']:
							type = 'img'
						elif extension in ['mp4', 'MOV']:
							type = 'video'

						# print(type)

						self.send(json.dumps({
							'message': content_name,
							'type': type
						}))

						myfile = pathlib.Path(
						__file__).parent.absolute().joinpath('log.txt')

						with open(myfile, "w") as f:
							f.seek(0)
							f.write(content_name)
							f.truncate()

						# index do conteudo que deu override
						idx = list(cloud_content.keys()).index(content_name)
						# se idx é o ultimo da lista, passamos para o primeiro
						if (idx + 1) >= len(cloud_content.keys()):
							currentindex = 0
						else:
							currentindex = idx + 1  # passar para o proximo

						start = time.time()

						subprocess.call("./postupdate.sh")

					consequtive_errors = 0

					# sleep para n se engasgar. tirar qnd tiver tudo feito.
					# ver se os videos nao tao lentos ou algo do genero
					sleep(1)

				except:

					consequtive_errors += 1
					print(consequtive_errors)
