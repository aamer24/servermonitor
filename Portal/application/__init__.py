from flask import Flask, render_template, jsonify, request,redirect, url_for, session,abort
import pymongo
from pymongo import MongoClient
from bson import json_util
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask_socketio import SocketIO, emit
import paramiko 
import json,bson

import os
from requests import HTTPError
sched = BackgroundScheduler()
sched.start()
from flask_mailman import Mail, EmailMessage

app = Flask(__name__)

socketio = SocketIO(app)
client = MongoClient('mongodb://localhost:27017/')
db = client['server_monitoring']
collection = db["server_stats"]
hist_collection = db["server_stats_hist"]
app.config['SECRET_KEY'] = '' 

mail = Mail()

app.config["MAIL_SERVER"] = "smtp.fastmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = ""
app.config["MAIL_PASSWORD"] = ""
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True

mail.init_app(app)
   

from application import routes