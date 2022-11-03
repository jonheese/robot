import os
import tornado
from tornado.options import define, options, parse_config_file
from handlers import  MainHandler, RobotsHandler, StatusHandler, LockHandler, OpenCloseHandler
from util import RobotUtil


if __name__ == "__main__":
    define("username", default="<myq-username>", help="Username for MyQ app login")
    define("password", default="<myq-password>", help="Password for MyQ app login")
    define("lockfile", default="/tmp/robot.lock", help="File to store door lock status across invocations")
    define("passcode", default="1234", help="Passcode to authenticate users to the robot API")
    define("port", default=8000, help="Run on the given port", type=int)
    define("debug", default=True, help="Run in debug mode")
    parse_config_file(os.path.join(os.path.dirname(__file__), "config.py"))

    util = RobotUtil(options)
    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/(favicon.ico)", tornado.web.StaticFileHandler, {"path": "static/"}),
            (r"/(robots.txt)", tornado.web.StaticFileHandler, {"path": "static/"}),
            (r"/status/(.*)", StatusHandler, dict(util=util)),
            (r"/status", StatusHandler, dict(util=util)),
            (r"/lockout/(.*)", LockHandler, dict(util=util)),
            (r"/open/(.*)", OpenCloseHandler, dict(util=util)),
            (r"/close/(.*)", OpenCloseHandler, dict(util=util)),
        ],
        debug=options.debug,
    )
    server = tornado.web.HTTPServer(app, xheaders=True)
    server.add_sockets(tornado.netutil.bind_sockets(options.port))
    tornado.ioloop.IOLoop.current().start()
