from typing import cast
from channels.generic.websocket import WebsocketConsumer

import qrcode
from PIL import Image
from moviepy.editor import VideoFileClip		# pip install moviepy

import json
from time import sleep

import pathlib
import os

import time
import urllib.request
import requests
import subprocess

from datetime import datetime
from datetime import timedelta
from django.utils.timezone import now
from django.utils import dateformat
from django.utils.timezone import make_aware
import hashlib
import pytz

class WSConsumer(WebsocketConsumer):



	def init(self):
		print("Initializating WSConsumer")
		self.cloud_content = {}
		self.currentindex = 0
		self.ids = []
		self.timers = []
		self.getFilesFromCloud()
		self.change_qr = True
		self.first_hash()
		self.first_time = True


	def first_hash(self):
		newhash = str(hashlib.md5(("3"+str(now())).encode()).hexdigest())
		self.qr_url = 'http://peig2.westeurope.cloudapp.azure.com/qr/' + str(newhash) + '.png'
		daqui_a_20min = now() + timedelta(minutes=80) # pode-se usar seconds=1200 tmb
		expires_max = dateformat.format(daqui_a_20min, 'Y-m-d H:i:s') # é isto que tem de ser espetado no endpoint
		aux = expires_max.split(' ')
		expires_max = aux[0] + 'T' + aux[1] + '+01:00'
		subprocess.call(['./authpost2.sh', newhash, str(expires_max)])
		sleep(2)


	# verifica os ficheiros da cloud
	def getFilesFromCloud(self):
		url_10 = 'http://peig2.westeurope.cloudapp.azure.com/api/agent/3/'
		#erros = 0
		try:
			r = requests.get(url_10, auth=('genix', 'genix'))
			ls = r.json()['group']['contentprogram_set'][0]['programentry_set']


			# Get cloud content
			self.cloud_content = {}
			self.timers = []
			self.ids = []
			for item in ls:
				if str(item['doc']['youtubelink']) != '':
					type = str(item['doc']['id']) + '.youtube'
					self.cloud_content[item['doc']['id']] = [type, item['doc']['youtubelink']]
					self.timers.append(item['duration'])
				else:

					self.cloud_content[item['doc']['id']] = [item['doc']['docname'], item['doc']['downloadlink']]
					self.timers.append(item['duration'])


			print("Cloud content", self.cloud_content.keys())
			print("Timers: ", self.timers)

		except:
			#erros += 1
			#print("{}- Trying to resolve URL '{}'".format(erros, url_10))
			self.getFilesFromCloud()

	# verifica o input do utilozador
	def verifyUserInput(self):
		url_1 = 'http://peig2.westeurope.cloudapp.azure.com/api/agentupdates/3/'
		try:
			r2 = requests.get(url_1, auth=('genix', 'genix'))
			#erros = 0
			a = int(r2.json()['contentid'])
			b = r2.json()['content_confirm']
			print(a, b)
			return a, b
		except:
			#erros += 1
			#print("{}- Trying to resolve URL '{}'".format(erros, url_1))
			print("Exception no Verify User Input")
			return None, None

	def get_expires_time(self):
		url = 'http://peig2.westeurope.cloudapp.azure.com/api/agentupdates/3/'
		try:
			r2 = requests.get(url, auth=('genix', 'genix'))
			#erros = 0
			return r2.json()['expires_max'], r2.json()['expires']
		except:
			#erros += 1
			#print("{}- Trying to resolve URL '{}'".format(erros, url))
			self.get_expires_time()

	def get_newhash(self):
		url = 'http://peig2.westeurope.cloudapp.azure.com/api/agentupdates/3/'
		try:
			r2 = requests.get(url, auth=('genix', 'genix'))
			#erros = 0
			return r2.json()['url_hash']
		except:
			#erros += 1
			#print("{}- Trying to resolve URL '{}'".format(erros, url))
			self.get_expires_time()

	def extension(self, extension):
		if extension in ['png', 'jpg']:
			return 'img'
		elif extension in ['mp4', 'MOV']:
			return 'video'
		elif extension == 'pdf':
			return 'pdf'
		elif extension == 'youtube':
			return 'youtube'
		else:
			return 'Unsuported'


	def send_msg(self, filename, type):
		self.send(json.dumps({
			'message': filename,
			'type': type,
			'change_qr': self.change_qr,
			'qr_url': self.qr_url
		}))

		print("SWITCHED TO", filename)

	def writeFile(self, id):
		myfile = pathlib.Path(__file__).parent.absolute().joinpath('log.txt')
		with open(myfile, "w") as f:
			f.seek(0)
			f.write(str(id))
			f.truncate()

	def check_expires(self):

		# verificar se uma data qq (pode ser o 'expires') ja passou
		expires_max, expires = self.get_expires_time()

		# Expires max
		ymd, hms = expires_max.split('T')
		year, month, day = ymd.split('-')
		hour, mins, secs = hms.split(':')[0:3]
		secs = secs.split('+')[0]
		secs = secs.split('.')[0]

		naive = datetime(int(year), int(month), int(day), int(hour), int(mins), int(secs))
		make_aware(naive)
		expires_max = make_aware(naive, timezone=pytz.timezone("Europe/Lisbon"))

		# Expires
		ymd, hms = expires.split('T')
		year, month, day = ymd.split('-')
		hour, mins, secs = hms.split(':')[0:3]
		secs = secs.split('+')[0]
		secs = secs.split('.')[0]

		naive = datetime(int(year), int(month), int(day), int(hour), int(mins), int(secs))
		make_aware(naive)
		expires = make_aware(naive, timezone=pytz.timezone("Europe/Lisbon"))


		if expires_max < now():
			print("Expira max e gera nova hash")
			# ir buscar o id
			newhash = str(hashlib.md5(("3"+str(now())).encode()).hexdigest())
			print("Que é " + newhash)
			#novo qr
			daqui_a_20min = now() + timedelta(minutes=80) # pode-se usar seconds=1200 tmb
			expires_max = dateformat.format(daqui_a_20min, 'Y-m-d H:i:s') # é isto que tem de ser espetado no endpoint
			aux = expires_max.split(' ')
			expires_max = aux[0] + 'T' + aux[1] + '+01:00'

			print(expires_max)
			print("Script")

			subprocess.call(['./authpost2.sh', newhash, str(expires_max)])
			# self.make_qr_code('http://peig2.westeurope.cloudapp.azure.com/control/' + newhash)
			self.change_qr = True
			self.qr_url = 'http://peig2.westeurope.cloudapp.azure.com/qr/' + str(newhash) + '.png'

		elif expires < now():
			print("Expira e gera nova hash")
			newhash2 = str(hashlib.md5(("3"+str(now())).encode()).hexdigest())
			print("Que é " + newhash2)
			daqui_a_20min = now() + timedelta(minutes=80) # pode-se usar seconds=1200 tmb
			expires_max = dateformat.format(daqui_a_20min, 'Y-m-d H:i:s') # é isto que tem de ser espetado no endpoint

			aux = expires_max.split(' ')
			expires_max = aux[0] + 'T' + aux[1] + '+01:00'

			subprocess.call(['./authpost2.sh', newhash2, str(expires_max)])
			# self.make_qr_code('http://peig2.westeurope.cloudapp.azure.com/control/' + newhash2)
			self.change_qr = True
			self.qr_url = 'http://peig2.westeurope.cloudapp.azure.com/qr/' + str(newhash2) + '.png'


	def connect(self):
		self.accept()
		self.init()

		# self.make_qr_code('http://peig2.westeurope.cloudapp.azure.com/control/' + self.get_newhash())

		cloud_timer = time.time()
		user_timer = time.time()

		id = -1

		# filename = list(self.cloud_content.keys())[self.currentindex]

		while True:
			if(self.currentindex > len(self.cloud_content.keys()) - 1):
				self.currentindex = 0

			if time.time() - user_timer > 2:
				id = None
				content_confirm = None
				id, content_confirm = self.verifyUserInput()

				print("Content confirm: {}\t Content name in cloud: {}".format(content_confirm == False, id in self.cloud_content.keys()))
				if (content_confirm == False) and (id in self.cloud_content.keys()):
					cloud_timer = time.time()

					filename = self.cloud_content.get(id)[0]
					ext = filename.split('.')[-1]
					type = self.extension(ext)

					self.check_expires()

					if type == 'pdf':
						self.send_msg("https://drive.google.com/viewerng/viewer?embedded=true&url="+ str(self.cloud_content.get(id)[1]), type)

					elif type == 'youtube':
						link = str(self.cloud_content.get(id)[1]).split("watch?v=")
						src = link[0] + 'embed/' + link[1] + '?autoplay=1&mute=1'

						self.send_msg(src, type)

					else:
						self.send_msg(self.cloud_content[id][1], type)

					self.change_qr = False
					self.writeFile(id)
					cloud_timer = time.time()
					self.currentindex = list(self.cloud_content.keys()).index(id) + 1

					subprocess.call("./postupdate.sh")

				user_timer = time.time()


			elif (time.time() - cloud_timer > self.timers[self.currentindex-1]) or self.first_time:
				self.first_time = False
				self.getFilesFromCloud()
				contentdir = os.listdir(pathlib.Path(__file__).parent.absolute().joinpath('static/images/'))

				keys_list = list(self.cloud_content.keys())
				id = keys_list[self.currentindex]


				filename = self.cloud_content.get(id)[0]
				ext = filename.split('.')[-1]
				type = self.extension(ext)

				self.check_expires()

				if type == 'pdf':
					self.send_msg("https://drive.google.com/viewerng/viewer?embedded=true&url="+ self.cloud_content.get(id)[1], type)

				elif type == 'youtube':
					link = str(self.cloud_content.get(id)[1]).split("watch?v=")
					src = link[0] + 'embed/' + link[1] + '?autoplay=1&mute=1'

					self.send_msg(src, type)

				else:
					self.send_msg(self.cloud_content.get(id)[1], type)

				self.change_qr = False
				self.writeFile(id)
				self.currentindex += 1
				cloud_timer = time.time()
