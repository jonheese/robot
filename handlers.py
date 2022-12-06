import json
import pymyq
import tornado.web
from datetime import datetime


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("")


class RobotsHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("User agent: * \n" + \
                   "Disallow: /")


class AuthorizedRequestHandler(tornado.web.RequestHandler):
    def initialize(self, util):
        self.util = util

    async def get(self, name=None):
        name = self.util.check_key(name)
        if name is None:
            self.write({ "error": "Invalid passcode" })
            return None
        return name


class StatusHandler(AuthorizedRequestHandler):
    def initialize(self, util):
        self.util = util

    async def get(self, name=None):
        if name:
            name = await super().get(name)
            if name is None:
                return
        devices = {}
        try:
            device_instances = await self.util.get_devices(name)
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
                    devices[inst.name]["duration"] = self.util.format_duration(datetime.utcnow() - datetime.strptime(devices[inst.name]["last_changed"][:26], "%Y-%m-%dT%H:%M:%S.%fZ"))
                devices[inst.name]["locked"] = self.util.is_locked(inst.name)
            self.write(devices)
        except pymyq.errors.InvalidCredentialsError as e:
            self.write({ "error": str(e)})


class LockHandler(AuthorizedRequestHandler):
    def initialize(self, util):
        self.util = util

    async def get(self, orig_name=None):
        name = await super().get(orig_name)
        if name is None:
            return
        self.util.lock(name)
        self.redirect(f"/status/{orig_name}")


class OpenCloseHandler(AuthorizedRequestHandler):
    def initialize(self, util):
        self.util = util

    async def get(self, orig_name=None):
        name = await super().get(orig_name)
        if name is None:
            return
        try:
            device_instances = await self.util.get_devices(name)
            if len(device_instances) == 0:
                self.redirect(f"/status/")
                return
            url_path = self.request.uri.split("/")
            if self.util.is_locked(name):
                self.util.unlock(name)
            else:
                if url_path[1] == "open":
                    success = await self.util.change_device_state(name=name, close=False)
                elif url_path[1] == "close":
                    success = await self.util.change_device_state(name=name, close=True)
            self.redirect(f"/status/{orig_name}")
        except pymyq.errors.InvalidCredentialsError as e:
            self.write({ "error": str(e)})
