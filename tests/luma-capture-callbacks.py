#!/usr/bin/env python3
"""Exercise the actual unload body with native unique/weak ownership and completion ordering."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1]/'plugins/luma-capture/plugin.cpp').read_text()
body = source.split('APICALL EXPORT void PLUGIN_EXIT()', 1)[1]
harness = r'''
#include <hyprutils/memory/UniquePtr.hpp>
#include <hyprutils/memory/WeakPtr.hpp>
#include <cassert>
#include <functional>
#include <iostream>
#include <memory>
#include <vector>
using namespace Hyprutils::Memory;
enum Result { RESULT_COPIED, RESULT_NOT_COPIED, RESULT_TIMESTAMP };
struct Frame {
    bool m_copied = false, m_failed = false;
    std::function<void(Result)> m_callback;
};
struct CaptureCallback {
    CWeakPointer<Frame> frame;
    std::function<void(Result)> original;
    bool failed = false;
};
std::vector<std::weak_ptr<CaptureCallback>> callbacks;
std::vector<int> scenes;
void PLUGIN_EXIT() UNLOAD_BODY

void check(const char* name, bool copied, bool nativeFailed, bool renderFailed, bool destroy, bool expire) {
    auto frame = makeUnique<Frame>();
    unsigned failures = 0, successes = 0;
    auto relay = std::make_shared<CaptureCallback>();
    relay->frame = frame;
    relay->failed = renderFailed;
    relay->original = [&](Result result) {
        failures += result == RESULT_NOT_COPIED;
        successes += result == RESULT_COPIED;
        if (destroy) frame.reset();
    };
    frame->m_callback = [relay](Result result) {
        relay->original(relay->failed && result == RESULT_COPIED ? RESULT_NOT_COPIED : result);
    };
    callbacks.emplace_back(relay);
    frame->m_failed = nativeFailed;
    if (copied) {
        frame->m_callback(RESULT_COPIED);
        frame->m_copied = true;
    } else if (nativeFailed) {
        frame->m_callback(RESULT_NOT_COPIED);
    }
    if (expire) frame.reset();
    PLUGIN_EXIT();
    if (frame && !frame->m_copied && !frame->m_failed) {
        frame->m_callback(RESULT_COPIED);
        frame->m_copied = true;
    }
    assert(callbacks.empty());
    const unsigned expectedFailures = !expire && (renderFailed || nativeFailed);
    const unsigned expectedSuccesses = !expire && !renderFailed && !nativeFailed;
    if (failures != expectedFailures || successes != expectedSuccesses) {
        std::cerr << name << ": failure=" << failures << " success=" << successes << '\n';
        std::exit(1);
    }
    std::cout << name << ": failure=" << failures << " success=" << successes << '\n';
}
int main() {
    check("pending render failure", false, false, true, false, false);
    check("completed render failure", true, false, true, false, false);
    check("completed native failure", false, true, true, false, false);
    check("pending ordinary success", false, false, false, false, false);
    check("callback destroys frame", false, false, true, true, false);
    check("expired frame", false, false, true, false, true);
}
'''.replace('UNLOAD_BODY', body)

with tempfile.TemporaryDirectory(prefix='luma-callback-check-') as temporary:
    path = Path(temporary)
    (path/'check.cpp').write_text(harness)
    flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'hyprutils'], text=True))
    subprocess.run(['c++', '-std=c++23', '-g', '-fsanitize=address,undefined', str(path/'check.cpp'), *flags, '-o', str(path/'check')], check=True)
    subprocess.run([str(path/'check')], env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'), check=True)
