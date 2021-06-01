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
		self.erros = 0
		self.cloud_content = {}
		self.currentindex = 0
		self.videos = {}


		self.getFilesFromCloud()
		# calcular à priori a length dos videos
		for filename in list(self.cloud_content.keys()):
			print(filename.split('.')[1])
			if self.extension(filename.split('.')[1]) == 'video':
				clip = VideoFileClip(self.cloud_content[filename])
				self.videos[filename] = clip.duration

		print(self.videos)

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
		url_10 = 'http://peig2.westeurope.cloudapp.azure.com/api/documents/'
		try:
			r = requests.get(url_10, auth=('genix', 'genix'))
			ls = r.json()['results']

			# Get cloud content
			self.cloud_content = {}
			for item in ls:
				self.cloud_content[item['downloadlink'].split('/')[-1]] = item['downloadlink']
			print("Cloud content", self.cloud_content.keys())
			erros = 0
		except:
			errors += 1
			print("{}- Trying to resolve URL '{}'".format(erros, url_10))
			self.getFilesFromCloud()

	# verifica o input do utilozador
	def verifyUserInput(self):
		url_1 = 'http://peig2.westeurope.cloudapp.azure.com/api/agentupdates/3/'
		try:
			r2 = requests.get(url_1, auth=('genix', 'genix'))
			erros = 0
		except:
			errors += 1
			print("{}- Trying to resolve URL '{}'".format(erros, url_1))
			self.verifyUserInput()

	def extension(self, extension):
		if extension in ['png', 'jpg']:
			return 'img'
		elif extension in ['mp4', 'MOV']:
			return 'video'
		else:
			return 'Unsuported'


	def send_msg(self, filename, type):
		self.send(json.dumps({
			'message': filename,
			'type': type
		}))

		myfile = pathlib.Path(__file__).parent.absolute().joinpath('log.txt')
		with open(myfile, "w") as f:
			f.seek(0)
			f.write(filename)
			f.truncate()


	def connect(self):
		print("aqui")
		self.accept()
		self.init()

		self.make_qr_code('http://peig2.westeurope.cloudapp.azure.com/control/3/')

		cloud_timer = time.time()
		user_timer = time.time()

		filename = list(self.cloud_content.keys())[self.currentindex]
		timer = self.videos[filename] if self.extension(filename) == 'video' else 5

		while True:
			if(self.currentindex > len(self.cloud_content.keys()) - 1):
				self.currentindex = 0

			if time.time() - user_timer > 1:
				try:
					url_1 = 'http://peig2.westeurope.cloudapp.azure.com/api/agentupdates/3/'
					r2 = requests.get(url_1, auth=('genix', 'genix'))
				except:
					print("Could not resolve URL...")

				content_name = r2.json()['contentname']
				content_confirm = r2.json()['content_confirm']

				if (content_confirm == False) and (content_name in self.cloud_content.keys()):
					ext = content_name.split('.')[-1]
					print("UPDATED TO", content_name)
					type = self.extension(ext)

					# esta operação é pesada logo convem só fazer uma vez ou quando há novos videos
					if type == 'video' and filename not in self.videos.keys():
						clip = VideoFileClip(self.cloud_content[filename])
						timer = clip.duration
						self.videos[filename] = timer
					elif type == 'video' and filename in self.videos.keys():
						timer = self.videos[filename]
					else:
						timer = 5

					self.send_msg(content_name, type)
					cloud_timer = time.time()

					self.currentindex = list(self.cloud_content.keys()).index(content_name) + 1
					subprocess.call("./postupdate.sh")


				user_timer = time.time()


			elif time.time() - cloud_timer > timer:
				self.getFilesFromCloud()
				contentdir = os.listdir(pathlib.Path(__file__).parent.absolute().joinpath('static/images/'))

				filename = list(self.cloud_content.keys())[self.currentindex]
				self.currentindex += 1

				ext = filename.split('.')[-1]
				type = self.extension(ext)

				# esta operação é pesada logo convem só fazer uma vez ou quando há novos videos
				if type == 'video' and filename not in self.videos.keys():
					clip = VideoFileClip(self.cloud_content[filename])
					timer = clip.duration
					self.videos[filename] = timer
				elif type == 'video' and filename in self.videos.keys():
					timer = self.videos[filename]
				else:
					timer = 5

				print("SWITCHED TO", filename)
				self.send_msg(filename, type)

				print("Timer: {}".format(timer))
				cloud_timer = time.time()
