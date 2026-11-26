#pragma once

#include <hyprland/src/managers/SeatManager.hpp>
#include <hyprland/src/managers/SessionLockManager.hpp>
#include <hyprland/src/managers/input/InputManager.hpp>
#include <hyprland/src/protocols/core/Seat.hpp>
#include <hyprland/src/protocols/core/Compositor.hpp>
#include <hyprland/src/protocols/LayerShell.hpp>
#include <hyprland/src/protocols/InputMethodV2.hpp>
#include <hyprland/src/protocols/InputCapture.hpp>
#include <hyprland/src/protocols/PointerConstraints.hpp>
#include <hyprland/src/desktop/state/LayerState.hpp>
#include <hyprland/src/event/EventBus.hpp>
#include <hyprland/src/ipc/s2/S2.hpp>
#include <sstream>

namespace PrivateInput {
enum class State { Closed, Draining, WaitingLuma, Luma, WaitingNative, Native };
State state = State::Closed;
uint64_t generation = 0;
uint64_t revision = 0;
uint64_t closedThrough = 0;
std::string lastReason;
PHLLSREF layer;
WP<CWLSurfaceResource> target;
SP<IKeyboard> eventKeyboard;
CFunctionHook *keyHook = nullptr, *modsHook = nullptr, *focusHook = nullptr;
std::vector<std::function<void()>> disconnect;

struct Key {
    WP<IKeyboard> keyboard;
    uint32_t code;
};
bool same(const Key& key, const SP<IKeyboard>& keyboard, uint32_t code) { return key.keyboard == keyboard && key.code == code; }

const char* destination() {
    switch (state) {
        case State::Closed: case State::Draining: return "closed";
        case State::WaitingLuma: return "waiting-luma";
        case State::Luma: return "luma";
        case State::WaitingNative: return "waiting-native";
        case State::Native: return "native";
    }
    return "closed";
}

std::string status() {
    return std::format("{{\"protocol\":1,\"generation\":{},\"revision\":{},\"destination\":\"{}\",\"reason\":\"{}\"}}",
                       generation, revision, destination(), lastReason);
}

void publish(const std::string& reason = "") {
    ++revision;
    lastReason = reason;
    IPC::Socket2::sock()->postEvent({"luma_private", status()});
}

bool safe() {
    const auto ime = g_pInputManager->m_relay.m_inputMethod.lock();
    const auto pointer = g_pSeatManager->m_state.pointerFocus.lock();
    const auto surface = pointer ? pointer->m_hlSurface.lock() : nullptr;
    const auto constraint = surface ? surface->constraint() : nullptr;
    return !g_pSessionLockManager->isSessionLocked() && !g_pSeatManager->m_seatGrab &&
        !(constraint && constraint->isActive()) && !(ime && (ime->hasGrab() || ime->m_active)) &&
        !(PROTO::inputCapture && PROTO::inputCapture->isCaptured());
}

bool live() {
    const bool mapped = !layer.expired() && layer->mapped() && !target.expired() && target->m_mapped &&
        !layer->m_layerSurface.expired() && layer->m_layerSurface->m_surface == target &&
        layer->m_keyboardInteractivity == 0;
    if (!mapped) return false;
    const auto seat = g_pSeatManager->seatResourceForClient(target->client());
    return seat && std::ranges::any_of(seat->m_keyboards, [](const auto& keyboard) { return !keyboard.expired(); });
}

template <typename F> bool keyboards(const WP<CWLSurfaceResource>& surface, F fn) {
    if (surface.expired()) return false;
    const auto seat = g_pSeatManager->seatResourceForClient(surface->client());
    bool sent = false;
    if (seat) for (const auto& keyboard : seat->m_keyboards) if (keyboard) { fn(keyboard); sent = true; }
    return sent;
}

void end(const std::string& reason);

struct Epoch : IKeyboardEventHandler {
    const WP<CWLSurfaceResource> surface;
    std::vector<WP<CWLKeyboardResource>> entered;
    std::vector<Key> held;
    bool delivering = true;
    explicit Epoch(WP<CWLSurfaceResource> surface_) : surface(surface_) {}

    template <typename F> bool send(F fn) {
        bool sent = false;
        for (const auto& keyboard : entered) if (!keyboard.expired()) { fn(keyboard); sent = true; }
        return sent;
    }

    bool resourcesCurrent() {
        size_t count = 0;
        bool matches = true;
        keyboards(surface, [&](const auto& keyboard) {
            ++count;
            if (!std::ranges::any_of(entered, [&](const auto& item) { return item == keyboard; })) matches = false;
        });
        return matches && count == entered.size() && std::ranges::none_of(entered, [](const auto& item) { return item.expired(); });
    }

    void neutralize() {
        if (!delivering) return;
        delivering = false;
        std::vector<uint32_t> released;
        for (const auto& key : held) if (!std::ranges::contains(released, key.code)) {
            released.push_back(key.code);
            send([&](const auto& kb) { kb->sendKey(0, key.code, WL_KEYBOARD_KEY_STATE_RELEASED); });
        }
        send([](const auto& kb) { kb->sendMods(0, 0, 0, 0); kb->sendLeave(); });
    }

    void onKeyboardKey(const IKeyboard::SKeyEvent& event, SP<IKeyboard> keyboard) override {
        const bool pressed = event.state == WL_KEYBOARD_KEY_STATE_PRESSED;
        const bool already = std::ranges::any_of(held, [&](const auto& key) { return key.code == event.keycode; });
        if (delivering && (!safe() || !live() || !resourcesCurrent() ||
            std::ranges::any_of(held, [](const auto& key) { return key.keyboard.expired(); }))) { end("protection-loss"); return; }
        if (pressed) held.push_back({keyboard, event.keycode});
        else std::erase_if(held, [&](const auto& key) { return same(key, keyboard, event.keycode); });
        if (!delivering) return;
        g_pSeatManager->setKeyboard(keyboard);
        const bool remains = std::ranges::any_of(held, [&](const auto& key) { return key.code == event.keycode; });
        if ((pressed && !already) || (!pressed && !remains)) {
            if (!send([&](const auto& kb) { kb->sendKey(event.timeMs, event.keycode, event.state); })) end("target-gone");
        }
    }
};
SP<Epoch> active;
std::vector<SP<Epoch>> epochs;

void nativeMods() {
    const auto keyboard = g_pSeatManager->m_keyboard.lock();
    if (!keyboard) return;
    const auto mods = keyboard->m_modifiersState;
    using Fn = void (*)(CSeatManager*, uint32_t, uint32_t, uint32_t, uint32_t);
    reinterpret_cast<Fn>(modsHook->m_original)(g_pSeatManager.get(), mods.depressed, mods.latched, mods.locked, mods.group);
}

void retire(bool restoreModifiers = true) {
    if (!active) return;
    g_pSeatManager->m_keyboardEventHandlers.remove(active);
    active->neutralize();
    active.reset();
    if (restoreModifiers) nativeMods();
}

void end(const std::string& reason) {
    const bool wasOpen = state != State::Closed && state != State::Draining;
    state = State::Closed;
    if (active && std::ranges::any_of(active->held, [](const auto& key) { return !key.keyboard.expired(); }) && safe() && reason != "shutdown") {
        active->neutralize();
        state = State::Draining;
    } else retire(reason != "protection-loss");
    target.reset();
    layer.reset();
    if (wasOpen) { closedThrough = std::max(closedThrough, generation); publish(reason); }
}

bool neutral() {
    for (const auto& keyboard : g_pInputManager->m_keyboards)
        if (keyboard->m_enabled && (!keyboard->m_pressed.empty() || keyboard->m_modifiersState.depressed || keyboard->m_modifiersState.latched)) return false;
    return true;
}

void advance() {
    auto& stack = g_pSeatManager->m_keyboardEventHandlers;
    std::erase_if(epochs, [&](const auto& epoch) {
        if (epoch == active) return false;
        return !std::ranges::any_of(stack.m_ownedKeys, [&](const auto& key) { return key.handler.get() == epoch.get(); });
    });
    if (state == State::Closed) return;
    if (state == State::Draining) {
        if (!safe() || neutral()) { retire(); state = State::Closed; }
        return;
    }
    if (!safe() || !live()) { end("protection-loss"); return; }
    if (active && std::ranges::any_of(active->held, [](const auto& key) { return key.keyboard.expired(); })) { end("keyboard-gone"); return; }
    if (active && active->delivering && !active->resourcesCurrent()) { end("protection-loss"); return; }
    if (!neutral()) return;
    if (state == State::WaitingNative) {
        retire();
        state = State::Native;
        publish();
    } else if (state == State::WaitingLuma) {
        retire();
        active = makeShared<Epoch>(target);
        epochs.push_back(active);
        wl_array keys;
        wl_array_init(&keys);
        const bool entered = keyboards(target, [&](const auto& kb) {
            active->entered.push_back(kb);
            const auto source = g_pSeatManager->m_keyboard.lock();
            if (source) { kb->sendKeymap(source); kb->repeatInfo(source->m_repeatRate, source->m_repeatDelay); }
            kb->sendEnter(target.lock(), &keys);
            kb->sendMods(0, 0, source ? source->m_modifiersState.locked : 0, source ? source->m_modifiersState.group : 0);
        });
        wl_array_release(&keys);
        if (!entered) { end("target-gone"); return; }
        state = State::Luma;
        stack.push(active);
        publish();
    }
}

void reserve() {
    active = makeShared<Epoch>(target);
    active->delivering = false;
    epochs.push_back(active);
    g_pSeatManager->m_keyboardEventHandlers.push(active);
}

void select(bool luma) {
    if (state == State::Closed || state == State::Draining) return;
    if (luma) {
        if (state == State::Luma || state == State::WaitingLuma) return;
        if (!g_pSeatManager->m_state.keyboardFocus.expired() && !target.expired() &&
            g_pSeatManager->m_state.keyboardFocus->client() == target->client()) { end("same-client-focus"); return; }
        retire();
        state = State::WaitingLuma;
        reserve();
    } else {
        if (state == State::Native || state == State::WaitingNative) return;
        if (active) {
            active->neutralize();
            // Keep this epoch on the stack until physical keys are neutral. New
            // presses during the handoff cannot inherit Luma's held modifiers.
            state = State::WaitingNative;
        } else state = State::Native;
    }
    publish();
    advance();
}

struct EscapeOwner : IKeyboardEventHandler {
    void onKeyboardKey(const IKeyboard::SKeyEvent&, SP<IKeyboard>) override {}
};

bool consume(const IKeyboard::SKeyEvent& event, const SP<IKeyboard>& keyboard) {
    auto owner = makeShared<EscapeOwner>();
    auto& stack = g_pSeatManager->m_keyboardEventHandlers;
    stack.push(owner);
    const bool consumed = stack.dispatch(event, keyboard, true);
    stack.remove(owner);
    return consumed;
}

using KeyFn = void (*)(CInputManager*, const IKeyboard::SKeyEvent&, SP<IKeyboard>);
void key(CInputManager* manager, const IKeyboard::SKeyEvent& event, SP<IKeyboard> keyboard) {
    eventKeyboard = keyboard;
    if (state == State::Draining && !safe()) { retire(); state = State::Closed; }
    if ((state == State::Luma || state == State::WaitingLuma || state == State::WaitingNative) && (!safe() || !live())) {
        const bool consumed = consume(event, keyboard);
        end("protection-loss");
        if (consumed) { eventKeyboard.reset(); return; }
    }
    if (state != State::Closed && state != State::Draining && state != State::Luma && !live()) end("protection-loss");
    reinterpret_cast<KeyFn>(keyHook->m_original)(manager, event, keyboard);
    eventKeyboard.reset();
    advance();
}

using ModsFn = void (*)(CSeatManager*, uint32_t, uint32_t, uint32_t, uint32_t);
void mods(CSeatManager* manager, uint32_t depressed, uint32_t latched, uint32_t locked, uint32_t group) {
    if (state == State::Draining && !safe()) { retire(); state = State::Closed; }
    if (state != State::Closed && state != State::Draining && (!safe() || !live())) {
        const bool routed = state != State::Native;
        end("protection-loss");
        if (routed) return;
    }
    if (state == State::Luma) {
        if (!active->resourcesCurrent()) { end("protection-loss"); return; }
        active->send([&](const auto& kb) { kb->sendMods(depressed, latched, locked, group); });
    } else if (state != State::WaitingLuma && state != State::WaitingNative && state != State::Draining) reinterpret_cast<ModsFn>(modsHook->m_original)(manager, depressed, latched, locked, group);
    advance();
}

using FocusFn = void (*)(CSeatManager*, SP<CWLSurfaceResource>);
void focus(CSeatManager* manager, SP<CWLSurfaceResource> surface) {
    if (manager->m_state.keyboardFocus != surface && state != State::Closed && state != State::Draining) select(false);
    reinterpret_cast<FocusFn>(focusHook->m_original)(manager, surface);
}

template <typename Signal, typename F> void listen(Signal& signal, F fn) {
    auto listener = signal.listen(fn);
    // Signal hosts retain expired weak control blocks too. Remove ours while
    // the plugin's allocation/destruction code is still mapped.
    disconnect.push_back([&signal, listener] { std::erase_if(signal.m_vListeners, [&](const auto& weak) { return weak == listener; }); });
}

std::string command(const std::string& request) {
    std::istringstream input(request);
    std::string name, action;
    uint64_t requested = 0;
    pid_t pid = 0;
    std::string monitor;
    input >> name >> action;
    const auto error = [](const char* message) { return std::format("{{\"error\":\"{}\"}}", message); };
    if (action == "open") {
        if (!(input >> requested >> pid >> monitor) || !requested || pid <= 0) return error("Invalid private canvas identity");
        if (requested <= closedThrough) return error("Private canvas generation already closed");
        if (state != State::Closed && state != State::Draining && requested == generation) { select(true); advance(); }
        else {
            end("replaced");
            retire();
            if (!safe()) return error("Private input unavailable during lock, seat grab, input capture or active IME");
            PHLLS found;
            for (const auto& candidate : Desktop::layerState()->layers()) {
                if (!candidate->mapped() || candidate->m_namespace != "modesty-command-canvas" || candidate->getPID() != pid ||
                    candidate->m_monitor.expired() || candidate->m_monitor->m_name != monitor) continue;
                if (found) return error("Private input requires exactly one mapped Luma canvas");
                found = candidate;
            }
            if (!found || found->m_layerSurface.expired()) return error("No mapped Luma canvas");
            layer = found;
            target = found->m_layerSurface->m_surface;
            if (!live() || g_pSeatManager->m_state.keyboardFocus.expired() ||
                g_pSeatManager->m_state.keyboardFocus->client() == target->client()) {
                target.reset(); layer.reset();
                return error("Private input requires a focusless canvas with keyboards and another focused client");
            }
            generation = requested;
            state = State::WaitingLuma;
            reserve();
            publish();
            advance();
        }
    } else if (action == "quiesce") {
        end("closed");
        advance();
        return std::format("{{\"protocol\":1,\"neutral\":{}}}", neutral() && state == State::Closed);
    } else if (action == "close") {
        if (!(input >> requested)) return error("Invalid private generation");
        if (requested == generation) end("closed");
    } else if (action != "status") return error("Unknown private input command");
    advance();
    return status();
}

template <typename Install> void init(HANDLE handle, Install install) {
    keyHook = install("CInputManager::onKeyboardKey", reinterpret_cast<const void*>(&key));
    modsHook = install("CSeatManager::sendKeyboardMods", reinterpret_cast<const void*>(&mods));
    focusHook = install("CSeatManager::setKeyboardFocus", reinterpret_cast<const void*>(&focus));
    listen(Event::bus()->m_events.input.keyboard.key, std::function<void(IKeyboard::SKeyEvent, Event::SCallbackInfo&)>(
        [](const auto& event, auto& info) {
            if (!eventKeyboard) return;
            if (state != State::Closed && state != State::Draining && safe() && event.keycode == 1 && event.state == WL_KEYBOARD_KEY_STATE_PRESSED) {
                consume(event, eventKeyboard);
                info.cancelled = true;
                end("escape");
            }
        }));
    listen(Event::bus()->m_events.input.mouse.button, std::function<void(IPointer::SButtonEvent, Event::SCallbackInfo&)>(
        [](const auto& event, auto&) {
            if (state == State::Closed || state == State::Draining || event.state != WL_POINTER_BUTTON_STATE_PRESSED) return;
            if (!safe() || !live()) { end("protection-loss"); return; }
            // Button callbacks precede normal focus processing. Hit-test the
            // actual surface input region at the current pointer coordinates.
            const auto box = layer->surfaceLogicalBox();
            const auto pointer = g_pSeatManager->m_state.pointerFocus.lock();
            const bool inTree = pointer && (pointer == target || target->findFirstPreorder([&](auto child) { return child == pointer; }));
            select(box && inTree && bool(target->at(g_pInputManager->getMouseCoordsInternal() - box->pos(), true).first));
        }));
    listen(Event::bus()->m_events.tick, std::function<void()>([] { advance(); }));
    listen(g_pSessionLockManager->m_events.lock, std::function<void()>([] { end("lock"); }));
    listen(Event::bus()->m_events.layer.closed, std::function<void(PHLLS)>([](auto closed) { if (closed == layer) end("target-gone"); }));
    listen(Event::bus()->m_events.monitor.removed, std::function<void(PHLMONITOR)>([](auto monitor) {
        if (!layer.expired() && layer->m_monitor == monitor) end("monitor-gone");
    }));
    if (!HyprlandAPI::registerHyprCtlCommand(handle, {.name="luma-private", .match=IPC::Socket1::COMMAND_MATCH_PREFIX,
        .handler=[](const IPC::Socket1::SRequest& request) -> IPC::Socket1::SResponse { return command(request.command); }}))
        throw std::runtime_error("Cannot register private input API");
}

void shutdown() {
    end("shutdown");
    retire();
    state = State::Closed;
    for (auto& remove : disconnect) remove();
    disconnect.clear();
    // Native ownership keeps expired weak handlers so physical releases remain
    // consumed after dlclose. Only live plugin objects must disappear here.
    epochs.clear();
    eventKeyboard.reset();
}
}
