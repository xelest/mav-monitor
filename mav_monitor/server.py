"""Flask application factory for MAV Monitor."""

import hmac
import os
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO

from . import metrics
from .config import Config

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def _token_ok(supplied: str, expected: str) -> bool:
    return hmac.compare_digest(supplied or "", expected or "")


def create_app(config: Config):
    app = Flask(__name__, static_folder=None)
    app.config["MONITOR"] = config

    if config.cors_origins:
        CORS(app, origins=config.socketio_cors)

    socketio = SocketIO(
        app,
        cors_allowed_origins=config.socketio_cors or None,
        async_mode="eventlet",
        logger=False,
        engineio_logger=False,
    )

    def require_token(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if config.auth_enabled:
                header = request.headers.get("Authorization", "")
                supplied = header[7:] if header.startswith("Bearer ") else request.args.get("token", "")
                if not _token_ok(supplied, config.token):
                    return jsonify({"error": "unauthorized"}), 401
            return view(*args, **kwargs)

        return wrapper

    @app.route("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.route("/vendor/<path:filename>")
    def vendor(filename):
        return send_from_directory(os.path.join(STATIC_DIR, "vendor"), filename)

    @app.route("/api/config")
    def api_config():
        return jsonify({
            "auth_required": config.auth_enabled,
            "terminal_enabled": config.terminal_enabled,
            "processes_hidden": config.hide_processes,
            "history_points": config.history_points,
        })

    @app.route("/api/overview")
    @require_token
    def api_overview():
        return jsonify(metrics.overview())

    @app.route("/api/cpu")
    @require_token
    def api_cpu():
        return jsonify(metrics.cpu_detail())

    @app.route("/api/memory")
    @require_token
    def api_memory():
        return jsonify(metrics.memory_detail())

    @app.route("/api/disk")
    @require_token
    def api_disk():
        return jsonify(metrics.disk_detail())

    @app.route("/api/network")
    @require_token
    def api_network():
        return jsonify(metrics.network_detail())

    @app.route("/api/services")
    @require_token
    def api_services():
        return jsonify(metrics.services(config.services))

    @app.route("/api/processes")
    @require_token
    def api_processes():
        return jsonify(metrics.processes(config.process_limit, config.hide_processes))

    @app.route("/api/metrics")
    @require_token
    def api_metrics():
        return jsonify(metrics.tick())

    if config.terminal_enabled:
        from .terminal import TerminalManager

        TerminalManager(socketio, config.terminal_token).register()

    return app, socketio
