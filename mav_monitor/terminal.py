"""Optional interactive shell over Socket.IO.

Only registered when MONITOR_TERMINAL_TOKEN is set. Every session must present
that token. The shell runs as the same OS user as the monitor process, so this
feature is a deliberate remote-shell capability, not a convenience toggle.
"""

import fcntl
import os
import pty
import select
import struct
import subprocess
import termios


class TerminalManager:
    def __init__(self, socketio, token: str):
        self._socketio = socketio
        self._token = token
        self._sessions = {}

    def register(self):
        self._socketio.on_event("terminal_start", self._start)
        self._socketio.on_event("terminal_input", self._input)
        self._socketio.on_event("terminal_resize", self._resize)
        self._socketio.on_event("disconnect", self._disconnect)

    def _reader(self, sid, fd):
        while True:
            try:
                readable, _, _ = select.select([fd], [], [], 0.1)
                if not readable:
                    continue
                data = os.read(fd, 4096)
                if not data:
                    break
                self._socketio.emit(
                    "terminal_output",
                    {"data": data.decode("utf-8", errors="replace")},
                    room=sid,
                )
            except (OSError, IOError):
                break
        self._socketio.emit("terminal_exit", {}, room=sid)
        self._sessions.pop(sid, None)

    def _kill(self, sid):
        session = self._sessions.pop(sid, None)
        if not session:
            return
        try:
            os.kill(session["pid"], 9)
            os.close(session["fd"])
        except OSError:
            pass

    def _start(self, data=None):
        from flask import request

        sid = request.sid
        supplied = (data or {}).get("token", "")
        if supplied != self._token:
            self._socketio.emit("terminal_denied", {"reason": "invalid token"}, room=sid)
            return

        self._kill(sid)
        pid, fd = pty.fork()
        if pid == 0:
            shell = os.environ.get("SHELL", "/bin/bash")
            os.execvpe(shell, [shell, "-l"], os.environ)
            os._exit(1)

        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        self._sessions[sid] = {"pid": pid, "fd": fd}
        self._socketio.start_background_task(self._reader, sid, fd)
        self._socketio.emit("terminal_ready", {}, room=sid)

    def _input(self, data):
        from flask import request

        session = self._sessions.get(request.sid)
        if session:
            try:
                os.write(session["fd"], (data or {}).get("data", "").encode())
            except OSError:
                pass

    def _resize(self, data):
        from flask import request

        session = self._sessions.get(request.sid)
        if not session:
            return
        rows = int((data or {}).get("rows", 24))
        cols = int((data or {}).get("cols", 80))
        try:
            fcntl.ioctl(session["fd"], termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        except OSError:
            pass

    def _disconnect(self):
        from flask import request

        self._kill(request.sid)
