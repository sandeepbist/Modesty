#!/usr/bin/env python3
"""Local Moonshine Small hold-to-talk worker. Audio stays in memory; stdout is UI events."""
import argparse
import json
import math
import os
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time

DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "modesty"
ENV = DATA / "stt-moonshine-venv"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "modesty/voice-moonshine"
MODEL = CACHE / "small-streaming-en"
RATE, BLOCK, LIMIT = 16000, 800, 60
OUTPUT = threading.Lock()


def emit(event, session="", **data):
    with OUTPUT:
        print(json.dumps({"event": event, "id": session, **data}), flush=True)


def download_model():
    from moonshine_voice import ModelArch
    from moonshine_voice.download import download_model_from_info, find_model_info
    from moonshine_voice.download_file import crc32c_file
    from moonshine_voice.moonshine_api import moonshine_get_stt_dependencies_string
    path, arch = download_model_from_info(
        find_model_info("en", ModelArch.SMALL_STREAMING), cache_root=CACHE,
        include_word_timestamps=False,
    )
    if arch != ModelArch.SMALL_STREAMING:
        raise RuntimeError("Expected Moonshine Small Streaming English")
    target = Path(path).resolve()
    # Upstream skips CRC checks for cached files of the right size. Check every
    # asset before selecting it, including downloads reused by a reinstall.
    manifest = json.loads(moonshine_get_stt_dependencies_string(
        "en", {"model_arch": int(ModelArch.SMALL_STREAMING)}))
    for entry in manifest["groups"][0]["files"]:
        file = target / entry["name"]
        if (file.stat().st_size != entry["size"] or entry["checksum_type"] != "crc32c"
                or crc32c_file(file) != entry["checksum"]):
            raise RuntimeError(f"Voice model integrity check failed: {entry['name']}")
    if MODEL.exists() and not MODEL.is_symlink():
        raise RuntimeError(f"Model alias is occupied: {MODEL}")
    pending = MODEL.with_name(".small-streaming-en.tmp")
    pending.unlink(missing_ok=True)
    pending.symlink_to(target, target_is_directory=True)
    pending.replace(MODEL)


def install():
    uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
    if not Path(uv).is_file():
        raise RuntimeError("Install uv first: sudo pacman -S uv")
    if not (ENV / "bin/python").is_file():
        subprocess.run([uv, "venv", "--python", sys.executable, str(ENV)], check=True)
    python = str(ENV / "bin/python")
    subprocess.run([uv, "pip", "install", "--python", python,
                    "moonshine-voice==0.1.5", "numpy==2.5.3", "soundfile==0.14.0"], check=True)
    subprocess.run([python, str(Path(__file__).resolve()), "--download"], check=True)
    subprocess.run([python, str(Path(__file__).resolve()), "--prepare"], check=True)


def load_model():
    # These variables must be set before loading the native ONNX Runtime library.
    os.environ["MOONSHINE_ORT_SINGLE_THREAD"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    from moonshine_voice import ModelArch, Transcriber
    if not MODEL.is_dir():
        raise RuntimeError("Voice model missing. Run python3 scripts/luma-voice.py --install")
    started = time.monotonic()
    speech = Transcriber(model_path=MODEL, model_arch=ModelArch.SMALL_STREAMING,
                         options={"max_tokens_per_second": 6.5,
                                  "decode_incomplete_lines": True,
                                  "use_speculative_decoding": True})
    # Report this process's own peak; ru_maxrss can inherit a launcher's peak on exec.
    peak_kib = next(int(line.split()[1]) for line in Path("/proc/self/status").read_text().splitlines()
                    if line.startswith("VmHWM:"))
    emit("ready", loadSeconds=round(time.monotonic() - started, 3),
         peakMiB=round(peak_kib / 1024), runtime="moonshine-small-cpu")
    return speech


class Capture:
    def __init__(self, identity, audio=None):
        self.id = identity
        self.audio = audio
        self.blocks = queue.Queue(maxsize=RATE * LIMIT // BLOCK + 2)
        self.cancelled = threading.Event()
        self.released = threading.Event()
        self.process = None
        self.samples = 0
        self.thread = threading.Thread(target=self.read, daemon=True)

    def fail(self, message):
        if not self.cancelled.is_set():
            self.cancelled.set()
            emit("error", self.id, text=message)
        self.stop()

    def stop(self):
        self.released.set()
        process = self.process
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)

    def cancel(self):
        self.cancelled.set()
        self.stop()

    def add(self, block):
        import numpy as np
        self.samples += len(block)
        if self.samples > RATE * LIMIT:
            self.fail("Voice reached its 60-second limit. Try a shorter request.")
            return False
        try:
            self.blocks.put_nowait(block)
        except queue.Full:
            self.fail("Voice could not keep up. Try a shorter request.")
            return False
        rms = float(np.sqrt(np.mean(block * block)))
        # Meter is captured audio energy, not a decorative microphone animation.
        # dB range makes quiet speech visible without amplifying digital silence.
        emit("level", self.id, value=max(0, min(1, (20 * math.log10(max(rms, 1e-6)) + 60) / 42)))
        return True

    def read(self):
        try:
            import numpy as np
            if self.audio:
                import soundfile as sf
                wave, rate = sf.read(self.audio, dtype="float32", always_2d=True)
                if rate != RATE:
                    raise RuntimeError("Recorded verification audio must be 16 kHz.")
                wave = wave.mean(axis=1)
                for start in range(0, len(wave), BLOCK):
                    if self.released.is_set() or not self.add(wave[start:start + BLOCK]):
                        break
                    self.released.wait(BLOCK / RATE)
                self.released.wait(LIMIT)
            else:
                # PipeWire performs channel conversion/resampling. No temporary WAV.
                if self.released.is_set():
                    return
                self.process = subprocess.Popen([
                    "pw-record", "--raw", "--rate", str(RATE), "--channels", "1",
                    "--format", "f32", "--latency", "50ms", "--media-role", "Communication",
                    "--properties", "application.name=Luma node.name=modesty-luma-voice", "-"
                ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                # Release can race the process creation; never leave that capture open.
                if self.released.is_set():
                    self.stop()
                emit("listening", self.id)
                remainder = b""
                while not self.cancelled.is_set():
                    raw = self.process.stdout.read(BLOCK * 4)
                    if not raw:
                        break
                    raw = remainder + raw
                    size = len(raw) // 4 * 4
                    remainder = raw[size:]
                    if size and not self.add(np.frombuffer(raw[:size], dtype="<f4").copy()):
                        break
                if not self.released.is_set():
                    self.fail("Microphone unavailable. Check your input device.")
        except Exception:
            self.fail("Could not capture audio. Check your input device.")
        finally:
            self.stop()
            if self.process and self.process.stdout:
                self.process.stdout.close()
            while True:
                try:
                    self.blocks.put_nowait(None)
                    break
                except queue.Full:
                    if not self.cancelled.is_set():
                        time.sleep(.01)
                    else:
                        try:
                            self.blocks.get_nowait()
                        except queue.Empty:
                            pass


def feed_session(stream, capture):
    """Feed every block; compute previews only while caught up and still held."""
    partial_due = 0.0
    while not capture.cancelled.is_set():
        block = capture.blocks.get()
        if block is None:
            break
        stream.add_audio(block.tolist(), sample_rate=RATE)
        if (not capture.cancelled.is_set() and not capture.released.is_set()
                and capture.blocks.empty() and time.monotonic() >= partial_due):
            stream.update_transcription()
            partial_due = time.monotonic() + .5


def transcribe_capture(speech, capture):
    # Disable implicit previews within a bounded hold. Public update_transcription
    # lets release drain audio without paying for obsolete preview decodes.
    stream = speech.create_stream(update_interval=LIMIT + 1)
    lines = {}
    last_text = ""
    errors = []

    def update(event):
        nonlocal last_text
        if capture.cancelled.is_set():
            return
        if event.__class__.__name__ == "Error":
            errors.append(event.error)
            capture.fail("Transcription failed. Your request was not submitted.")
            return
        line = getattr(event, "line", None)
        if line is None:
            return
        lines[line.line_id] = (line.start_time, (line.text or "").strip())
        text = " ".join(value[1] for value in sorted(lines.values(), key=lambda value: value[0]) if value[1])
        if text != last_text:
            last_text = text
            emit("partial", capture.id, text=text)

    stream.add_listener(update)
    try:
        stream.start()
        feed_session(stream, capture)
        if capture.cancelled.is_set():
            return
        result = stream.stop()
        if errors or capture.cancelled.is_set():
            return
        if result is None:
            raise RuntimeError("Moonshine returned no final transcript")
        text = " ".join(line.text.strip() for line in result.lines if line.text.strip())
        if not capture.cancelled.is_set():
            emit("final", capture.id, text=text)
    finally:
        stream.close()


def serve(audio=None):
    jobs = queue.Queue(maxsize=2)
    current = None
    closing = threading.Event()

    def decode():
        try:
            speech = load_model()
        except (Exception, SystemExit) as exc:
            emit("unavailable", text=str(exc)[:300])
            closing.set()
            return
        try:
            while not closing.is_set():
                capture = jobs.get()
                if capture is None:
                    return
                if capture.cancelled.is_set():
                    continue
                try:
                    transcribe_capture(speech, capture)
                except Exception:
                    capture.fail("Transcription failed. Your request was not submitted.")
        finally:
            speech.close()

    threading.Thread(target=decode, daemon=True).start()
    def terminate(*_):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    try:
        for line in sys.stdin:
            try:
                command = json.loads(line)
                if not isinstance(command, dict):
                    continue
                identity = command.get("id", "")
                kind = command.get("command")
                if kind == "start" and isinstance(identity, str) and identity and len(identity) <= 80:
                    if closing.is_set():
                        emit("error", identity, text="Voice engine unavailable. Reopen Luma to retry.")
                        continue
                    if current and current.id == identity:
                        continue
                    if current and not current.cancelled.is_set() and not current.released.is_set():
                        continue
                    if current:
                        current.cancel()
                    current = Capture(identity, audio)
                    try:
                        jobs.put_nowait(current)
                    except queue.Full:
                        current.fail("Voice is still finishing. Try again shortly.")
                        continue
                    current.thread.start()
                elif current and current.id == identity:
                    if kind == "stop":
                        current.stop()
                    elif kind == "cancel":
                        current.cancel()
            except (ValueError, TypeError):
                continue
    finally:
        closing.set()
        if current:
            current.cancel()
        try:
            jobs.put_nowait(None)
        except queue.Full:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="install isolated Moonshine runtime and verified Small model")
    parser.add_argument("--download", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--prepare", action="store_true", help="load/measure the model without opening a microphone")
    parser.add_argument("--audio", type=Path, help="verify hold/release using recorded 16 kHz audio instead of microphone")
    args = parser.parse_args()
    try:
        os.nice(max(0, 10 - os.getpriority(os.PRIO_PROCESS, 0)))
    except OSError:
        pass
    if args.install:
        install()
        return
    if Path(sys.prefix).resolve() != ENV.resolve():
        python = ENV / "bin/python"
        if not python.is_file():
            emit("unavailable", text="Install voice first: python3 scripts/luma-voice.py --install")
            return
        os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
    if args.download:
        download_model()
    elif args.prepare:
        speech = load_model()
        speech.close()
    else:
        serve(args.audio)


if __name__ == "__main__":
    try:
        main()
    except (Exception, SystemExit) as exc:
        if isinstance(exc, SystemExit) and not exc.code:
            pass
        else:
            emit("unavailable", text=str(exc)[:300])
            sys.exit(1)
