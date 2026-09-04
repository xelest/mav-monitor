"""Console entrypoint: ``python -m mav_monitor`` / ``mavmon``."""

import eventlet

eventlet.monkey_patch()

from . import __version__
from .config import Config
from .server import create_app


def main():
    config = Config()
    app, socketio = create_app(config)

    print(f"MAV Monitor {__version__}")
    print(config.summary())
    if not config.auth_enabled and config.host not in ("127.0.0.1", "localhost", "::1"):
        print("\n  WARNING: bound to a non-loopback address with no MONITOR_TOKEN set.")
        print("  Anyone who can reach this port sees full host metrics.\n")
    print(f"\n  http://{config.host}:{config.port}\n")

    socketio.run(app, host=config.host, port=config.port, debug=False)


if __name__ == "__main__":
    main()
