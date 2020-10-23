import asyncio
import collections
import json
import os
import pymyq
import queue
import re
import tornado.ioloop
import tornado.web
from aiohttp import ClientSession
from datetime import datetime
from tornado.options import define, options, parse_config_file

define("username", default="<myq-username>", help="Username for MyQ app login")
define("password", default="<myq-password>", help="Password for MyQ app login")
define("lockfile", default="/tmp/robot.lock", help="File to store door lock status across invocations")
define("passcode", default="1234", help="Passcode to authenticate users to the robot API")
define("port", default=8000, help="Run on the given port", type=int)
define("debug", default=True, help="Run in debug mode")
parse_config_file(os.path.join(os.path.dirname(__file__), "config.py"))


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("")


class RobotsHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("User agent: * \n" + \
                   "Disallow: /")


class AuthorizedRequestHandler(tornado.web.RequestHandler):
    async def get(self, name=None):
        name = check_key(name)
        if name is None:
            self.write({ "error": "Invalid passcode" })
            return None
        return name


class StatusHandler(AuthorizedRequestHandler):
    async def get(self, name=None):
        if name:
            name = await super().get(name)
            if name is None:
                return
        devices = {}
        try:
            device_instances = await get_devices(name)
            for inst in device_instances:
                if inst.device_type != "virtualgaragedooropener":
                    continue
                devices[inst.name] = {}
                devices[inst.name]["state"] = inst.state
                if "last_update" in inst.device_json["state"]:
                    devices[inst.name]["last_changed"] = inst.device_json["state"]["last_update"]
                elif "updated_date" in inst.device_json["state"]:
                    devices[inst.name]["last_changed"] = inst.device_json["state"]["updated_date"]
                if devices[inst.name]["last_changed"]:
                    devices[inst.name]["duration"] = format_duration(datetime.utcnow() - datetime.strptime(devices[inst.name]["last_changed"][:26], "%Y-%m-%dT%H:%M:%S.%f"))
                devices[inst.name]["locked"] = is_locked(inst.name)
            self.write(devices)
        except pymyq.errors.InvalidCredentialsError as e:
            self.write({ "error": str(e)})


class LockHandler(AuthorizedRequestHandler):
    async def get(self, orig_name=None):
        name = await super().get(orig_name)
        if name is None:
            return
        lock(name)
        self.redirect(f"/status/{orig_name}")


class OpenCloseHandler(AuthorizedRequestHandler):
    async def get(self, orig_name=None):
        name = await super().get(orig_name)
        if name is None:
            return
        try:
            device_instances = await get_devices(name)
            if len(device_instances) == 0:
                self.redirect(f"/status/")
            url_path = self.request.uri.split("/")
            if is_locked(name):
                unlock(name)
            else:
                if url_path[1] == "open":
                    success = await change_device_state(name=name, close=False)
                elif url_path[1] == "close":
                    success = await change_device_state(name=name, close=True)
            self.redirect(f"/status/{orig_name}")
        except pymyq.errors.InvalidCredentialsError as e:
            self.write({ "error": str(e)})


async def login(websession):
    return await pymyq.login(options.username, options.password, websession)


async def get_devices(name=None):
    async with ClientSession() as websession:
        myq = await login(websession)
    if not name:
        return myq.devices.values()
    else:
        for device in myq.devices.values():
            if device.name.lower() == name.lower():
                return [device]
    return [] 


async def change_device_state(name=None, close=True):
    if not name:
        return False
    async with ClientSession() as websession:
        myq = await login(websession)
        for device in myq.devices.values():
            if device.name.lower() == name.lower():
                if close:
                    await device.close()
                else:
                    await device.open()
                return True
    return False


def check_key(name):
    if not name:
        return name
    split_name = name.split(":")
    if len(split_name) < 2 or split_name[1] != options.passcode:
        return None
    return split_name[0]


def is_locked(name):
    if os.path.isfile(options.lockfile):
        with open(options.lockfile, "r") as f:
            data = f.read()
        data = json.loads(data)
        if name in data.keys() and "locked" in data[name].keys():
            return data[name]["locked"]
    return False


def lock(name):
    change_lock(name, True)
    return is_locked(name)


def unlock(name):
    change_lock(name, False)
    return not is_locked(name)


def change_lock(name, lock):
    if os.path.isfile(options.lockfile):
        with open(options.lockfile, "r") as f:
            data = f.read()
        data = json.loads(data)
        if name in data.keys() and "locked" in data[name].keys():
            data[name]["locked"] = lock
        else:
            data[name] = { "locked": lock }
    else:
        data = { name: { "locked": lock } }
    json_data = json.dumps(data)

    with open(options.lockfile, "w") as f:
        f.write(json_data)


def format_duration(duration):
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    output = ""
    if days > 0:
        output = "%s days, " % days
    if hours > 0:
        output = "%s%s hours, " % (output, hours)
    if minutes > 0:
        output = "%s%s minutes" % (output, minutes)
    if len(output) == 0 and seconds > 0:
        output = "%s seconds" % seconds
    if re.search(", $", output):
        output = output[:-2]
    return output


if __name__ == "__main__":
    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/favicon.ico", MainHandler),
            (r"/robots.txt", RobotsHandler),
            (r"/status/(.*)", StatusHandler),
            (r"/status", StatusHandler),
            (r"/lockout", LockHandler),
            (r"/lockout/(.*)", LockHandler),
            (r"/open/(.*)", OpenCloseHandler),
            (r"/close/(.*)", OpenCloseHandler),
        ],
        debug=options.debug,
    )
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()
