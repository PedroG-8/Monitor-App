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


class WSConsumer(WebsocketConsumer):



	def init(self):
		print("Initializating WSConsumer")
		self.cloud_content = {}
		self.currentindex = 0
		self.ids = []
		self.timers = []
		self.getFilesFromCloud()

	def make_qr_code(self, url):
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



	# verifica os ficheiros da cloud
	def getFilesFromCloud(self):
		url_10 = 'http://peig2.westeurope.cloudapp.azure.com/api/agent/3/'
		erros = 0
		try:
			r = requests.get(url_10, auth=('genix', 'genix'))
			ls = r.json()['group']['contentprogram_set'][0]['programentry_set']


			# Get cloud content
			self.cloud_content = {}
			self.timers = []
			self.ids = []
			for item in ls:
				if str(item['doc']['youtubelink']) != '':
					self.cloud_content[str(item['doc']['id']) + '.youtube'] = item['doc']['youtubelink']
					self.timers.append(item['duration'])
				else:
					self.cloud_content[item['doc']['docname']] = item['doc']['downloadlink']
					self.timers.append(item['duration'])
				self.ids.append(item['doc']['id'])


			print("Cloud content", self.cloud_content.keys())
			print("Timers: ", self.timers)

		except:
			erros += 1
			print("{}- Trying to resolve URL '{}'".format(erros, url_10))
			self.getFilesFromCloud()

	# verifica o input do utilozador
	def verifyUserInput(self):
		url_1 = 'http://peig2.westeurope.cloudapp.azure.com/api/agentupdates/3/'
		try:
			r2 = requests.get(url_1, auth=('genix', 'genix'))
			erros = 0
			return r2.json()['contentname'], r2.json()['content_confirm']
		except:
			errors += 1
			print("{}- Trying to resolve URL '{}'".format(erros, url_1))
			self.verifyUserInput()

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
			'type': type
		}))

		print("SWITCHED TO", filename)


		myfile = pathlib.Path(__file__).parent.absolute().joinpath('log.txt')
		with open(myfile, "w") as f:
			f.seek(0)
			f.write(str(self.ids[self.currentindex]))
			f.truncate()


	def connect(self):
		self.accept()
		self.init()

		self.make_qr_code('http://peig2.westeurope.cloudapp.azure.com/control/3/')

		cloud_timer = time.time()
		user_timer = time.time()

		filename = list(self.cloud_content.keys())[self.currentindex]

		while True:
			if(self.currentindex > len(self.cloud_content.keys()) - 1):
				self.currentindex = 0

			if time.time() - user_timer > 4:
				content_name, content_confirm = self.verifyUserInput()
				print("Content confirm: {}\t Content name in cloud: {}".format(content_confirm == False, content_name in self.cloud_content.keys()))
				if (content_confirm == False) and (content_name in self.cloud_content.keys()):
					cloud_timer = time.time()

					ext = content_name.split('.')[-1]

					type = self.extension(ext)
					print(type)

					if type == 'pdf':
						print("Sending pdf")
						self.send_msg("https://drive.google.com/viewerng/viewer?embedded=true&url=" + self.cloud_content[content_name], type)

					elif type == 'youtube':
						print("Sending youtube")
						link = self.cloud_content[content_name].split("watch?v=")
						src = link[0] + 'embed/' + link[1] + '?autoplay=1&mute=1'
						print(src)
						self.send_msg(src, type)

					else:
						print("Sending a image ")
						self.send_msg(self.cloud_content[content_name], type)

					cloud_timer = time.time()
					self.currentindex = list(self.cloud_content.keys()).index(content_name) + 1

					subprocess.call("./postupdate.sh")
				user_timer = time.time()


			elif time.time() - cloud_timer > self.timers[self.currentindex]:
				self.getFilesFromCloud()
				contentdir = os.listdir(pathlib.Path(__file__).parent.absolute().joinpath('static/images/'))

				filename = list(self.cloud_content.keys())[self.currentindex]


				ext = filename.split('.')[-1]
				type = self.extension(ext)


				if type == 'pdf':
					self.send_msg("https://drive.google.com/viewerng/viewer?embedded=true&url="+ self.cloud_content[filename], type)

				elif type == 'youtube':
					link = self.cloud_content[filename].split("watch?v=")
					src = link[0] + 'embed/' + link[1] + '?autoplay=1&mute=1'

					self.send_msg(src, type)

				else:
					self.send_msg(self.cloud_content[filename], type)
				self.currentindex += 1
				cloud_timer = time.time()
