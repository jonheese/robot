'''
The MIT License (MIT)

Copyright (c) 2015 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from __future__ import print_function

import requests
import json, time, sys, os, logging, logging.handlers
from flask import Flask, request, jsonify
from datetime import datetime

states = [ "closed", "open", "status" ]

app = Flask(__name__)

LOGGER = None
requests.packages.urllib3.disable_warnings()

with open('%s/robot/config.json' % os.getcwd()) as config_file:
    config = json.load(config_file)

#main Configuration
USERNAME = config['main']['username']
PASSWORD = config['main']['password']
BRAND = config['main']['brand']
TOKENTTL = config['main']['tokenttl']
CULTURE = config['apiglobal']['culture']

#MyQ API Configuration
if (BRAND.lower() == 'chamberlain'):
    SERVICE = config['apiglobal']['chamberservice']
    APPID = config['apiglobal']['chamberappid']
    BRANDID = '2'
elif (BRAND.lower() == 'craftsman'):
    SERVICE = config['apiglobal']['craftservice']
    APPID = config['apiglobal']['craftappid']
    BRANDID = '3'
else:
    print(BRAND, " is not a valid brand name. Check your configuration")


def setup_log(name):
   # Log Location
   PATH = "/var/log/%s" % name
   LOG_FILENAME = PATH + "/%s.log" % name
   LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"

   #### Logging Section ################################################################################
   LOGGER = logging.getLogger('sensors')
   LOGGER.setLevel(LOG_LEVEL)
   # Set the log level to LOG_LEVEL
   # Make a handler that writes to a file, 
   # making a new file at midnight and keeping 3 backups
   HANDLER = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=30)
   # Format each log message like this
   FORMATTER = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
   # Attach the formatter to the handler
   HANDLER.setFormatter(FORMATTER)
   # Attach the handler to the logger
   LOGGER.addHandler(HANDLER)
   return LOGGER


class MyQLogger(object):
    """ Logger Class """
    def __init__(self, logger, level):
        """Needs a logger and a logger level."""
        self.logger = logger
        self.level = level

    def write(self, logmessage):
        """ Only log if there is a message (not just a new line) """
        if logmessage.rstrip() != "":
            self.logger.log(self.level, logmessage.rstrip())

    def read(self, logmessage):
        """" Does nothing, pylist complained """
        pass

        
class Device:
    def __init__(self, id, name, state, uptime):
        self.id = id
        self.name = name
        self.state = state
        self.time = uptime


class MyQ:
    def __init__(self):
        baseurl = SERVICE + "/api/v4"
        self.session = requests.Session()
        self.appid = APPID
        self.username = USERNAME
        self.password = PASSWORD
        self.headers = { "User-Agent": "Chamberlain/3.73",
                         "BrandId": BRANDID,
                         "ApiVersion": "4.1",
                         "Culture": CULTURE,
                         "MyQApplicationId": self.appid }
        self.authurl = baseurl+"/User/Validate"
        self.enumurl = baseurl+"/userdevicedetails/get"
        self.seturl  = baseurl+"/DeviceAttribute/PutDeviceAttribute"
        self.geturl  = baseurl+"/deviceattribute/getdeviceattribute"
        self.tokenfname="/tmp/myqtoken.json"
        self.tokentimeout=TOKENTTL
        self.read_token()


    def save_token(self):
        if (float(self.tokentimeout) > 0):
            ts=time.time()
            token_file={}
            token_file["SecurityToken"]=self.securitytoken
            token_file["TimeStamp"]=datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            json_data=json.dumps(token_file)
            f = open(self.tokenfname,"w")
            f.write(json_data)
            f.close()
            os.chmod(self.tokenfname, 0o600)


    def read_token(self):
        if (os.path.isfile(self.tokenfname)):
            with open(self.tokenfname,"r") as f:
                data = f.read()
            res = json.loads(data) if hasattr(json, "loads") else json.read(data)
            self.securitytoken = res["SecurityToken"]
        else:
            self.login()


    def login(self):
        payload = { "username": self.username, "password": self.password }
        req = self.session.post(self.authurl, headers=self.headers, json=payload)

        if (req.status_code != requests.codes.ok):
            return "Login err code: " + req.status_code
        
        res = req.json()
        if (res["ReturnCode"] == "0"):    
            self.securitytoken = res["SecurityToken"]
            self.save_token()
        else: 
            return "Authentication Failed"


    # State = 0 for closed/off or 1 for open/on
    def set_state(self, device, device_type, desired_state):
        if device.state in ['Open', 'On'] and desired_state == 1:
             return device.name + ' already ' + device.state + '.'
        if device.state in ['Closed', 'Off'] and desired_state == 0:
             return device.name + ' already ' + device.state + '.'
        post_data = {
            "AttributeName"  : "desired" + device_type + "state",
            "MyQDeviceId"    : device.id,
            "ApplicationId"  : self.appid,
            "AttributeValue" : desired_state,
            "SecurityToken"  : self.securitytoken,
            "format"         : "json",
            "nojsoncallback" : "1"
        }

        self.session.headers.update({ "SecurityToken": self.securitytoken })
        payload = { "appId": self.appid, "SecurityToken": self.securitytoken }

        req = self.session.put(self.seturl, headers=self.headers, params=payload, data=post_data)

        if (req.status_code != requests.codes.ok):
            return (False, "Enum err code: " + req.status_code)

        res = req.json()
        
        if (res["ReturnCode"] == "0"):
            return (True, "Status changed")
        else:    
            return (False, "Can't set state, bad token?")

        
    def fetch_device_json(self):
        payload = { 
                "appId": self.appid, 
                "SecurityToken": self.securitytoken, 
                "filterOn": "true", 
                "format": 
                "json", 
                "nojsoncallback": "1" }
        self.session.headers.update({ "SecurityToken": self.securitytoken })

        req = self.session.get(self.enumurl, headers=self.headers, params=payload)
        if (req.status_code != requests.codes.ok):
            return (False, "Enum err code: " + req.status_code)
        return (True, req.json())


    def get_state(self, dev_type, value):
        # States value from API returns an interger, the index corresponds to the below list. Zero is not used. 
        GARAGE_STATES = ['','Open','Closed','Stopped','Opening','Closing']
        # "3" corresponds to a MyQ light
        if dev_type == 3:
            if value == 0:
                return "Off"
            elif value == 1:
                return "On"
        return GARAGE_STATES[value]

        
    def get_devices(self):
        (success, json_data) = self.fetch_device_json()
        # MyQ will tell us if our token is no longer valid. If so, delete the token and login again.
        if (json_data["ReturnCode"] == "-3333"):
            os.remove(self.tokenfname)
            self.read_token()
            (success, json_data) = self.fetch_device_json()
        if not success:
            return (False, json_data)
        instances = []
        if (json_data["ReturnCode"] == "0"):
            devices = [d for d in json_data["Devices"] if d["MyQDeviceTypeId"] in [2,3,7,17]]
            for d in devices:
                dev_type = int(d["MyQDeviceTypeId"])
                dev_id = d["MyQDeviceId"]
                for attr in d["Attributes"]:
                    if (attr["AttributeDisplayName"] == "desc"): 
                        desc = str(attr["Value"])
                    elif (attr["AttributeDisplayName"] in ["doorstate", "lightstate"]):
                        state = self.get_state(dev_type, int(attr["Value"]))
                        updtime = float(attr["UpdatedTime"])
                        timestamp = time.strftime("%a %d %b %Y %H:%M:%S", time.localtime(updtime / 1000.0))
                instances.append(Device(dev_id, desc, state, timestamp))
        return (success, instances)


def do_stuff(device_type, desired_state, LOGGER, name=None):
    message = ""
    devices = {}
    myq = MyQ()
    (success, device_instances) = myq.get_devices()
    if not success:
        return { "message": device_instances }
    if desired_state == 2:
        for inst in device_instances:
            if name is None or name.lower() == inst.name.lower():
                LOGGER.info('%s is %s. Last changed at %s', inst.name, inst.state, inst.time)
                devices[inst.name] = {}
                devices[inst.name]["state"] = inst.state
                devices[inst.name]["last_changed"] = inst.time
    else:
        success = False
        for inst in device_instances:
            if name.lower() == inst.name.lower():
                (success, message) = myq.set_state(inst, device_type, desired_state)
                devices[inst.name] = {}
                devices[inst.name]["requested_state"] = states[desired_state]
                devices[inst.name]["message"] = message
        if not success:
            devices["message"] = name + ' not found in available devices.'
    return devices


LOGGER = setup_log('robot')
LOGGER.info('==================================STARTED==================================')
# Replace stdout with logging to file at INFO level
# sys.stdout = SensorLogger(LOGGER, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyQLogger(LOGGER, logging.ERROR)


@app.route('/open/<name>', methods=['GET'])
def open_door(name):
    device_type = "door"
    desired_state = 1
    devices = do_stuff(device_type, desired_state, LOGGER, name)
    return "<pre>%s</pre>" % json.dumps(devices, indent=2)


@app.route('/close/<name>', methods=['GET'])
def close_door(name):
    device_type = "door"
    desired_state = 0
    devices = do_stuff(device_type, desired_state, LOGGER, name)
    return "<pre>%s</pre>" % json.dumps(devices, indent=2)


@app.route('/status/<name>', methods=['GET'])
def status(name):
    desired_state = 2
    devices = do_stuff(None, desired_state, LOGGER, name)
    return "<pre>%s</pre>" % json.dumps(devices, indent=2)


@app.route('/status', methods=['GET'])
def status_all():
    desired_state = 2
    devices = do_stuff(None, desired_state, LOGGER, None)
    return "<pre>%s</pre>" % json.dumps(devices, indent=2)


@app.route('/', methods=['GET'])
def index():
    return ""


@app.route('/robots.txt', methods=['GET'])
def robots():
    return "User agent: * \n" + \
           "Disallow: /"
