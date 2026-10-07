#!/usr/bin/env python3
"""Check voice scheduling, transcript revisions, cancellation and stream cleanup."""
import importlib.util
from pathlib import Path
import queue
import json
import sys
import tempfile
import threading
from enum import IntEnum
from types import SimpleNamespace as NS
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "voice", Path(__file__).resolve().parents[1] / "scripts/luma-voice.py")
voice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice)


def capture(released=False, cancelled=False):
    result = NS(id="hold", blocks=queue.Queue(), cancelled=threading.Event(),
                released=threading.Event(), failures=[])
    if released:
        result.released.set()
    if cancelled:
        result.cancelled.set()
    def fail(message):
        result.failures.append(message)
        result.cancelled.set()
    result.fail = fail
    result.blocks.put(NS(tolist=lambda: [0.1, 0.2]))
    result.blocks.put(None)
    return result


class Stream:
    def __init__(self, owner, mode="normal"):
        self.owner, self.mode = owner, mode
        self.audio, self.updates, self.stops, self.closed = [], 0, 0, False

    def add_listener(self, listener):
        self.listener = listener

    def start(self):
        if self.mode == "raise":
            raise RuntimeError("native failure")
        self.listener(NS(line=NS(line_id=2, start_time=2, text="second")))
        self.listener(NS(line=NS(line_id=1, start_time=0, text="first draft")))
        self.listener(NS(line=NS(line_id=1, start_time=0, text="first")))

    def add_audio(self, values, sample_rate):
        assert sample_rate == 16000
        self.audio.extend(values)
        if self.mode == "cancel":
            self.owner.cancelled.set()

    def update_transcription(self):
        self.updates += 1

    def stop(self):
        self.stops += 1
        if self.mode == "error":
            self.listener(type("Error", (), {"error": RuntimeError("decode")})())
        return NS(lines=[NS(text="first"), NS(text="second")])

    def close(self):
        self.closed = True


for mode in ("normal", "cancel", "error", "raise"):
    hold = capture(released=True)
    stream = Stream(hold, mode)
    speech = NS(create_stream=lambda update_interval: stream)
    with patch.object(voice, "emit") as emit:
        try:
            voice.transcribe_capture(speech, hold)
        except RuntimeError:
            assert mode == "raise"
        finals = [call for call in emit.call_args_list if call.args[0] == "final"]
        assert len(finals) == (1 if mode == "normal" else 0)
        if finals:
            assert finals[0].kwargs["text"] == "first second"
            partials = [call.kwargs["text"] for call in emit.call_args_list
                        if call.args[0] == "partial"]
            assert partials == ["second", "first draft second", "first second"]
    assert stream.closed
    assert stream.updates == 0  # Released backlog must not trigger obsolete previews.
    assert stream.stops == (0 if mode in ("cancel", "raise") else 1)
    assert bool(hold.failures) == (mode == "error")

hold = capture(cancelled=True)
stream = Stream(hold)
voice.feed_session(stream, hold)
assert not stream.audio and not stream.updates

# A caught-up hold gets a preview, then respects the wall-clock cooldown.
hold = capture()
hold.blocks = NS(get=iter([NS(tolist=lambda: [0.1]), NS(tolist=lambda: [0.2]), None]).__next__,
                 empty=lambda: True)
stream = Stream(hold)
with patch.object(voice.time, "monotonic", return_value=1):
    voice.feed_session(stream, hold)
assert stream.audio == [0.1, 0.2] and stream.updates == 1
print("PASS voice drain, preview cooldown, revisions, cancellation, errors and cleanup")

# Reinstallation must verify cached bytes and preserve the selected model on failure.
class ModelArch(IntEnum):
    SMALL_STREAMING = 4

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    previous, downloaded = root / "previous", root / "downloaded"
    previous.mkdir(); downloaded.mkdir()
    asset = downloaded / "asset.ort"
    asset.write_bytes(b"abc")
    alias = root / "selected"
    alias.symlink_to(previous)
    manifest = {"groups": [{"files": [{"name": "asset.ort", "size": 3,
                 "checksum_type": "crc32c", "checksum": "verified"}]}]}
    modules = {
        "moonshine_voice": NS(ModelArch=ModelArch),
        "moonshine_voice.download": NS(
            find_model_info=lambda language, arch: {},
            download_model_from_info=lambda *args, **kwargs: (downloaded, ModelArch.SMALL_STREAMING)),
        "moonshine_voice.download_file": NS(
            crc32c_file=lambda file: "verified" if file.read_bytes() == b"abc" else "wrong"),
        "moonshine_voice.moonshine_api": NS(
            moonshine_get_stt_dependencies_string=lambda *args: json.dumps(manifest)),
    }
    with patch.dict(sys.modules, modules), patch.object(voice, "MODEL", alias):
        voice.download_model()
        assert alias.resolve() == downloaded
        for invalid in (b"xyz", b"wrong size"):
            alias.unlink(); alias.symlink_to(previous)
            asset.write_bytes(invalid)
            try:
                voice.download_model()
            except RuntimeError as exc:
                assert "integrity check failed" in str(exc)
            else:
                raise AssertionError("Corrupt cached asset accepted")
            assert alias.resolve() == previous
            assert not alias.with_name(".small-streaming-en.tmp").exists()
print("PASS cached model integrity and preservation of the selected model on failure")
