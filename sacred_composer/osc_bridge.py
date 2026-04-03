"""OSC bridge — real-time communication for multi-sensory installations.

Connects Sacred Composer to external visual tools (TouchDesigner, Processing,
Max/MSP), MIDI output (python-rtmidi), and DMX lighting via Open Sound Control.

All external dependencies (pythonosc, python-rtmidi) are optional.  The module
imports cleanly without them; classes degrade to logged stubs.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Sequence

from sacred_composer.core import Composition

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency imports
# ---------------------------------------------------------------------------

try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import BlockingOSCUDPServer
    from pythonosc.udp_client import SimpleUDPClient
    _HAS_OSC = True
except ImportError:
    _HAS_OSC = False

try:
    import rtmidi
    _HAS_RTMIDI = True
except ImportError:
    _HAS_RTMIDI = False


# ---------------------------------------------------------------------------
# OSCServer — receive parameter updates from external sources
# ---------------------------------------------------------------------------

class OSCServer:
    """Listens for OSC messages and updates a shared state dict.

    Recognised addresses:
        /game/danger    float   (0.0-1.0)
        /game/energy    float   (0.0-1.0)
        /game/environment str
        /game/health    float   (0.0-1.0)
        /game/speed     float   (0.0-1.0)
        /game/time      float   (0-24 hours)

    Parameters
    ----------
    host : Bind address (default "0.0.0.0").
    port : UDP port to listen on (default 8000).
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self.state: dict[str, Any] = {
            "danger": 0.0,
            "energy": 0.5,
            "environment": "forest",
            "health": 1.0,
            "speed": 0.5,
            "time_of_day": 12.0,
        }
        self._server: Any | None = None
        self._thread: threading.Thread | None = None

        if not _HAS_OSC:
            logger.warning(
                "pythonosc not installed — OSCServer will store state "
                "but cannot receive network messages.  Install with: "
                "pip install python-osc"
            )

    # -- OSC handlers ------------------------------------------------------

    def on_game_state(self, address: str, *args: Any) -> None:
        """Handle /game/* messages."""
        if address == "/game/danger" and args:
            self.state["danger"] = float(args[0])
        elif address == "/game/energy" and args:
            self.state["energy"] = float(args[0])
        elif address == "/game/environment" and args:
            self.state["environment"] = str(args[0])
        elif address == "/game/health" and args:
            self.state["health"] = float(args[0])
        elif address == "/game/speed" and args:
            self.state["speed"] = float(args[0])
        elif address == "/game/time" and args:
            self.state["time_of_day"] = float(args[0])
        else:
            logger.debug("Unhandled OSC: %s %s", address, args)

    # -- Lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Start the OSC listener in a background thread."""
        if not _HAS_OSC:
            logger.info("OSCServer.start() skipped — pythonosc not available.")
            return

        dispatcher = Dispatcher()
        dispatcher.map("/game/*", self.on_game_state)

        self._server = BlockingOSCUDPServer(
            (self.host, self.port), dispatcher,
        )
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True,
        )
        self._thread.start()
        logger.info("OSCServer listening on %s:%d", self.host, self.port)

    def stop(self) -> None:
        """Shut down the listener."""
        if self._server is not None:
            self._server.shutdown()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("OSCServer stopped.")


# ---------------------------------------------------------------------------
# OSCSender — broadcast composition events to visualisers
# ---------------------------------------------------------------------------

class OSCSender:
    """Sends OSC messages to a visualiser / lighting controller.

    Parameters
    ----------
    host : Target host (default "127.0.0.1").
    port : Target UDP port (default 9000).
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9000) -> None:
        self.host = host
        self.port = port
        self._client: Any | None = None

        if _HAS_OSC:
            self._client = SimpleUDPClient(host, port)
        else:
            logger.warning(
                "pythonosc not installed — OSCSender will log messages "
                "instead of sending.  Install with: pip install python-osc"
            )

    def _send(self, address: str, *args: Any) -> None:
        if self._client is not None:
            self._client.send_message(address, list(args))
        else:
            logger.debug("OSC (stub) %s %s", address, args)

    def send_note(
        self,
        pitch: int,
        velocity: int,
        duration: float,
        voice_name: str,
    ) -> None:
        """Send a note-on event: ``/note/on pitch velocity duration voice``."""
        self._send("/note/on", pitch, velocity, duration, voice_name)

    def send_note_off(self, pitch: int, voice_name: str) -> None:
        """Send a note-off event: ``/note/off pitch voice``."""
        self._send("/note/off", pitch, voice_name)

    def send_pattern_data(
        self, pattern_name: str, values: Sequence[float],
    ) -> None:
        """Send raw pattern values: ``/pattern/{name} float_list``."""
        self._send(f"/pattern/{pattern_name}", *[float(v) for v in values])

    def send_form_section(self, section_name: str, bar_number: int) -> None:
        """Announce a form boundary: ``/form/section name bar``."""
        self._send("/form/section", section_name, bar_number)

    def send_param(self, name: str, value: float) -> None:
        """Send an arbitrary parameter: ``/param/{name} value``."""
        self._send(f"/param/{name}", value)


# ---------------------------------------------------------------------------
# MIDIOutput — thin wrapper around python-rtmidi
# ---------------------------------------------------------------------------

class MIDIOutput:
    """Send MIDI note messages via python-rtmidi.

    Parameters
    ----------
    port_name : Virtual port name, or *None* to open the first available.
    """

    def __init__(self, port_name: str | None = None) -> None:
        self._port: Any | None = None
        self._port_name = port_name

        if not _HAS_RTMIDI:
            logger.warning(
                "python-rtmidi not installed — MIDIOutput is a no-op.  "
                "Install with: pip install python-rtmidi"
            )
            return

        midiout = rtmidi.MidiOut()
        ports = midiout.get_ports()

        if port_name and port_name in ports:
            midiout.open_port(ports.index(port_name))
        elif ports:
            midiout.open_port(0)
            logger.info("Opened MIDI port: %s", ports[0])
        else:
            midiout.open_virtual_port(port_name or "SacredComposer")
            logger.info("Opened virtual MIDI port: %s", port_name or "SacredComposer")

        self._port = midiout

    def note_on(self, channel: int, pitch: int, velocity: int) -> None:
        """Send a MIDI Note-On message."""
        if self._port is not None:
            status = 0x90 | (channel & 0x0F)
            self._port.send_message([status, pitch & 0x7F, velocity & 0x7F])

    def note_off(self, channel: int, pitch: int) -> None:
        """Send a MIDI Note-Off message."""
        if self._port is not None:
            status = 0x80 | (channel & 0x0F)
            self._port.send_message([status, pitch & 0x7F, 0])

    def program_change(self, channel: int, program: int) -> None:
        """Send a MIDI Program Change message."""
        if self._port is not None:
            status = 0xC0 | (channel & 0x0F)
            self._port.send_message([status, program & 0x7F])

    def close(self) -> None:
        """Release the MIDI port."""
        if self._port is not None:
            self._port.close_port()
            self._port = None
            logger.info("MIDI port closed.")


# ---------------------------------------------------------------------------
# LivePerformer — play a Composition in real-time with OSC + MIDI
# ---------------------------------------------------------------------------

class LivePerformer:
    """Walk through a Composition in real-time, emitting OSC and MIDI events.

    Parameters
    ----------
    composition : A Sacred Composer ``Composition`` instance.
    osc_sender  : Optional ``OSCSender`` for visual/lighting output.
    midi_output : Optional ``MIDIOutput`` for audible MIDI output.
    """

    def __init__(
        self,
        composition: Composition,
        osc_sender: OSCSender | None = None,
        midi_output: MIDIOutput | None = None,
    ) -> None:
        self.composition = composition
        self.osc = osc_sender
        self.midi = midi_output
        self._playing = False
        self._thread: threading.Thread | None = None

    # -- internal ----------------------------------------------------------

    def _collect_events(self) -> list[dict[str, Any]]:
        """Flatten all voices into a time-sorted event list."""
        events: list[dict[str, Any]] = []
        for voice in self.composition.score.voices:
            for note in voice.notes:
                if note.is_rest:
                    continue
                beat_sec = 60.0 / self.composition.tempo
                start_sec = note.time * beat_sec
                dur_sec = note.duration * beat_sec
                events.append({
                    "type": "on",
                    "time": start_sec,
                    "pitch": note.pitch,
                    "velocity": note.velocity,
                    "duration": dur_sec,
                    "voice": voice.name,
                    "channel": voice.channel,
                })
                events.append({
                    "type": "off",
                    "time": start_sec + dur_sec,
                    "pitch": note.pitch,
                    "voice": voice.name,
                    "channel": voice.channel,
                })
        events.sort(key=lambda e: (e["time"], e["type"] == "on"))
        return events

    def _perform(self) -> None:
        """Internal playback loop."""
        events = self._collect_events()
        if not events:
            logger.info("LivePerformer: nothing to play.")
            return

        # Send initial form sections via OSC
        if self.osc:
            for section in self.composition.form:
                self.osc.send_form_section(section.label, section.start_bar)

        # Set up MIDI program changes
        if self.midi:
            for voice in self.composition.score.voices:
                self.midi.program_change(voice.channel, voice.instrument)

        start_wall = time.perf_counter()

        for event in events:
            if not self._playing:
                break

            # Wait until the event's scheduled time
            target = start_wall + event["time"]
            now = time.perf_counter()
            if target > now:
                time.sleep(target - now)

            if not self._playing:
                break

            if event["type"] == "on":
                if self.osc:
                    self.osc.send_note(
                        event["pitch"],
                        event["velocity"],
                        event["duration"],
                        event["voice"],
                    )
                if self.midi:
                    self.midi.note_on(
                        event["channel"], event["pitch"], event["velocity"],
                    )
            else:
                if self.osc:
                    self.osc.send_note_off(event["pitch"], event["voice"])
                if self.midi:
                    self.midi.note_off(event["channel"], event["pitch"])

        self._playing = False
        logger.info("LivePerformer: playback finished.")

    # -- public API --------------------------------------------------------

    def play(self, blocking: bool = True) -> None:
        """Start real-time playback.

        Parameters
        ----------
        blocking : If True, block until playback completes or ``stop()``
                   is called.  If False, run in a background thread.
        """
        self._playing = True
        if blocking:
            self._perform()
        else:
            self._thread = threading.Thread(target=self._perform, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Interrupt playback."""
        self._playing = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
