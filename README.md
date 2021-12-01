# Robot

Robot is a simple python webapp designed to run in Docker (specifically with Docker Compose) for providing an easy HTTP/S API layer on top of the clunky Chamberlain MyQ garage door opener system API.

## Authentication

To make sure that random people on the internet can't open and close your garage door, very simple URL-based authentication is done.  In order to execute the authenticated actions (open, close & lockout), passcode must be included on the end of the URL when performing those actions.

eg. To open a door with the name `Door` and the passcode `1234`:
    http://robot.domain/open/door:1234

Note that the colon character (`:`) delineates the primary URL from the passcode.

The passcode is set in the `config.py` file and should be kept secret (and not set to `1234`) to maintain security.

## Opening & Closing

As may be obvious from the Authentication section above, opening and closing is done at endpoints `/open/NAME` and `/close/NAME` where `NAME` is the name of the door in the MyQ app (case-insensitive).  As mentioned above, the correct passcode is required to be appended for these actions to be successful.

Note that running the `open` command on an open door -- and similarly the `close` command on a closed door -- will do nothing.  This is not functionality provided by the Robot code -- the MyQ API simply doesn't do anything when Robot passes a non-sensical request to it.

## Lockout

For some reason (possibly testing purposes) a lockout function was added to Robot.  If a given door is locked, the `open` and `close` commands are ignored and the lock is disabled.  In other words, a locked door will need to be triggered twice for the command to be run.  Note that the command that unlocks the door can be different from the command that is run afterwards (in other words, if you run a `close` command on a locked closed door, that will disable the lock, and then a subsequent `open` command will open it).  PHrased another way, locks are not exclusive to `open` or `close`, they are a property of the door (opener) in general.
