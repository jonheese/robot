import os
import json
import pymyq
import re
from aiohttp import ClientSession


class RobotUtil:
    def __init__(self, options):
        self.options = options


    async def login(self, websession):
        return await pymyq.login(self.options.username, self.options.password, websession)


    async def get_devices(self, name=None):
        async with ClientSession() as websession:
            myq = await self.login(websession)
        if not name:
            return myq.devices.values()
        else:
            for device in myq.devices.values():
                if device.name.lower() == name.lower():
                    return [device]
        return [] 


    async def change_device_state(self, name=None, close=True):
        if not name:
            return False
        async with ClientSession() as websession:
            myq = await self.login(websession)
            for device in myq.devices.values():
                if device.name.lower() == name.lower():
                    if close:
                        await device.close()
                    else:
                        await device.open()
                    return True
        return False


    def check_key(self, name):
        if not name:
            return name
        split_name = name.split(":")
        if len(split_name) < 2 or split_name[1] != self.options.passcode:
            return None
        return split_name[0]


    def is_locked(self, name):
        if os.path.isfile(self.options.lockfile):
            with open(self.options.lockfile, "r") as f:
                data = f.read()
            data = json.loads(data)
            for device in data.keys():
                if device.lower() == name.lower() and "locked" in data[device].keys():
                    return data[device]["locked"]
        return False


    def lock(self, name):
        self.change_lock(name, True)
        return self.is_locked(name)


    def unlock(self, name):
        self.change_lock(name, False)
        return not self.is_locked(name)


    def change_lock(self, name, lock):
        if os.path.isfile(self.options.lockfile):
            with open(self.options.lockfile, "r") as f:
                data = f.read()
            data = json.loads(data)
            if name in data.keys() and "locked" in data[name].keys():
                data[name]["locked"] = lock
            else:
                data[name] = { "locked": lock }
        else:
            data = { name: { "locked": lock } }
        json_data = json.dumps(data)

        with open(self.options.lockfile, "w") as f:
            f.write(json_data)


    def format_duration(self, duration):
        days = duration.days
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        output = ""
        if days > 0:
            output = "%s days, " % days
        if hours > 0:
            output = "%s%s hours, " % (output, hours)
        if minutes > 0:
            output = "%s%s minutes, " % (output, minutes)
        if len(output) == 0 and seconds > 0:
            output = "%s seconds" % seconds
        else:
            output = output[:-2]
        return output
