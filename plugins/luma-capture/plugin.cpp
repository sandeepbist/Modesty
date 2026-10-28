#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/render/Renderer.hpp>
#include <hyprland/src/render/ElementRenderer.hpp>
#include <hyprland/src/output/MonitorResources.hpp>
#include <hyprland/src/managers/screenshare/ScreenshareManager.hpp>
#include <hyprland/src/desktop/view/LayerSurface.hpp>
#include <hyprland/src/desktop/view/window/Window.hpp>
#include <hyprland/src/protocols/ColorManagement.hpp>
#include <hyprutils/utils/ScopeGuard.hpp>

#include <algorithm>
#include <memory>
#include <stdexcept>
#include <vector>

namespace {
using namespace Render;
using namespace Screenshare;
using Hyprutils::Utils::CScopeGuard;

constexpr auto SUPPORTED_BUILD = "c26dbf9337998ba9afcfe84050e36969bb787598";
HANDLE handle = nullptr;
bool capturing = false;
std::vector<CFunctionHook*> hooks;

struct CaptureCallback {
    WP<CScreenshareFrame> frame;
    FScreenshareCallback original;
    bool failed = false;
};
std::vector<std::weak_ptr<CaptureCallback>> callbacks;

void failCapture(CScreenshareFrame* frame) {
    for (const auto& weak : callbacks) {
        if (const auto callback = weak.lock(); callback && !callback->frame.expired() && callback->frame.get() == frame)
            callback->failed = true;
    }
}

struct Scene {
    PHLMONITORREF monitor;
    Vector2D size;
    NColorManagement::PImageDescription description;
    SP<IFramebuffer> framebuffer;
    UP<Monitor::CMonitorResources> resources;
};
std::vector<Scene> scenes;

bool privateLayer(const PHLLS& layer) {
    return layer && (layer->m_namespace == "modesty-command-canvas" || layer->m_namespace == "modesty-island" ||
                     layer->m_ruleApplicator->noScreenShare().valueOrDefault());
}

bool supportedOutput(const PHLMONITOR& monitor) {
    if (!monitor || monitor->isMirror() || monitor->m_scale != 1 || monitor->m_transform != WL_OUTPUT_TRANSFORM_NORMAL ||
        g_pHyprRenderer->type() != IHyprRenderer::RT_GL || !monitor->m_imageDescription)
        return false;
    const auto& description = monitor->m_imageDescription->value();
    return !description.icc.present && description.getPrimaries() == NColorManagement::getPrimaries(NColorManagement::CM_PRIMARIES_SRGB) &&
           (description.transferFunction == NColorManagement::CM_TRANSFER_FUNCTION_SRGB ||
            description.transferFunction == NColorManagement::CM_TRANSFER_FUNCTION_GAMMA22);
}

Scene& sceneFor(const PHLMONITOR& monitor) {
    std::erase_if(scenes, [](const auto& scene) { return scene.monitor.expired(); });
    auto found = std::ranges::find_if(scenes, [&](const auto& scene) { return scene.monitor == monitor; });
    if (found == scenes.end()) {
        scenes.emplace_back();
        found = std::prev(scenes.end());
        found->monitor = monitor;
    }
    const auto size = monitor->m_transformedSize;
    const auto description = monitor->workBufferImageDescription();
    if (!found->framebuffer || found->size != size || found->description != description) {
        auto resources = makeUnique<Monitor::CMonitorResources>(monitor, DRM_FORMAT_ABGR8888, size, description);
        auto framebuffer = g_pHyprRenderer->createFB("Luma clean capture");
        framebuffer->addStencil(resources->m_stencilTex);
        if (!framebuffer->alloc(size.x, size.y, DRM_FORMAT_ABGR8888))
            throw std::runtime_error("Cannot allocate private capture framebuffer");
        framebuffer->setImageDescription(description);
        found->resources = std::move(resources);
        found->framebuffer = framebuffer;
        found->description = description;
        found->size = size;
    }
    return *found;
}

SP<ITexture> cleanScene(const PHLMONITOR& monitor) {
    auto& renderer = *g_pHyprRenderer;
    const bool previousBlurDirty = monitor->m_blurFBDirty;
    const bool previousBlurRender = monitor->m_blurFBShouldRender;
    CScopeGuard restoreBlur([&] {
        monitor->m_blurFBDirty = previousBlurDirty;
        monitor->m_blurFBShouldRender = previousBlurRender;
    });
    auto& scene = sceneFor(monitor);
    const auto previousData = renderer.m_renderData;
    auto previousPass = std::move(renderer.m_renderPass);
    auto* previousCurrentPass = renderer.m_currentPass;
    auto previousResources = std::move(monitor->m_resources);
    const bool previousFeedback = renderer.m_bBlockSurfaceFeedback;
    monitor->m_resources = std::move(scene.resources);
    CScopeGuard restore([&] {
        capturing = false;
        scene.resources = std::move(monitor->m_resources);
        monitor->m_resources = std::move(previousResources);
        renderer.m_renderPass = std::move(previousPass);
        renderer.m_currentPass = previousCurrentPass;
        renderer.m_bBlockSurfaceFeedback = previousFeedback;
        renderer.m_renderData = previousData;
        renderer.bindFB(previousData.currentFB);
        renderer.setViewport(0, 0, previousData.fbSize.x, previousData.fbSize.y);
    });
    capturing = true;
    renderer.m_renderPass = {};
    renderer.m_currentPass = nullptr;
    renderer.m_bBlockSurfaceFeedback = true;
    monitor->m_blurFBDirty = true;
    monitor->m_blurFBShouldRender = true;
    renderer.bindFB(scene.framebuffer);
    renderer.m_renderData.fbSize = scene.size;
    renderer.m_renderData.mainFB = scene.framebuffer;
    renderer.m_renderData.renderModif = {};
    renderer.m_renderData.clipBox = {};
    renderer.m_renderData.currentWindow.reset();
    renderer.m_renderData.surface.reset();
    renderer.m_renderData.noSimplify = true;
    renderer.m_renderData.transformDamage = false;
    renderer.m_renderData.damage = CRegion{0, 0, scene.size.x, scene.size.y};
    renderer.m_renderData.finalDamage = renderer.m_renderData.damage;
    renderer.setProjectionType(RPT_EXPORT);
    renderer.setViewport(0, 0, scene.size.x, scene.size.y);
    renderer.draw(CClearPassElement::SClearData{CHyprColor(0, 0, 0, 1)});
    const auto now = Time::steadyNow();
    const CBox box{{}, scene.size};
    renderer.renderAllClientsForWorkspace(monitor, monitor->m_activeWorkspace, now);
    renderer.renderLockscreen(monitor, now, box);
    renderer.m_renderPass.render(renderer.m_renderData.damage);
    renderer.m_renderPass.clear();
    return scene.framebuffer->getTexture();
}

void renderCapture(CScreenshareFrame* frame) {
    auto& renderer = *g_pHyprRenderer;
    const auto monitor = frame->m_session->monitor();
    renderer.m_renderData.fbSize = frame->m_bufferSize;
    renderer.setProjectionType(RPT_EXPORT);
    renderer.setViewport(0, 0, frame->m_bufferSize.x, frame->m_bufferSize.y);
    renderer.m_renderData.transformDamage = false;
    renderer.m_renderData.noSimplify = true;
    renderer.draw(CClearPassElement::SClearData{CHyprColor(0, 0, 0, 1)});
    if (!supportedOutput(monitor) || capturing) {
        failCapture(frame);
        return;
    }
    try {
        const auto texture = cleanScene(monitor);
        const CBox box = CBox{{}, monitor->m_transformedSize}.translate(-frame->m_session->m_captureBox.pos());
        const bool aware = PROTO::colorManagement && PROTO::colorManagement->isClientCMAware(frame->m_session->m_client);
        const bool previousModif = renderer.m_renderData.renderModif.enabled;
        CScopeGuard restore([&] { renderer.m_renderData.renderModif.enabled = previousModif; });
        renderer.m_renderData.renderModif.enabled = false;
        renderer.draw(CTexPassElement::SRenderData{.tex = texture, .box = box, .cmBackToSRGB = !aware}, {0, 0, frame->m_bufferSize.x, frame->m_bufferSize.y});
    } catch (const std::exception& error) {
        failCapture(frame);
        LOG(Log::ERR, "Luma private capture failed; export remains black: {}", error.what());
    }
}

using LayerRender = void (*)(IHyprRenderer*, PHLLS, PHLMONITOR, const Time::steady_tp&, bool, bool);
using WindowRender = void (*)(IHyprRenderer*, PHLWINDOW, PHLMONITOR, const Time::steady_tp&, bool, eRenderPassMode, bool, bool);
using FadeoutRender = void (*)(IHyprRenderer*, PHLMONITOR, Desktop::eFadeoutPlane, PHLWORKSPACE);
using DragRender = void (*)(IHyprRenderer*, PHLMONITOR, const Time::steady_tp&);
CFunctionHook *layerHook = nullptr, *windowHook = nullptr, *fadeoutHook = nullptr, *dragHook = nullptr;
using FrameShare = eScreenshareError (*)(CScreenshareFrame*, SP<IHLBuffer>, const CRegion&, FScreenshareCallback);
CFunctionHook* shareHook = nullptr;

eScreenshareError shareFrame(CScreenshareFrame* frame, SP<IHLBuffer> buffer, const CRegion& damage, FScreenshareCallback callback) {
    if (frame->done())
        return ERROR_STOPPED;
    if (frame->m_session->m_type != SHARE_WINDOW && !supportedOutput(frame->m_session->monitor()))
        return ERROR_UNKNOWN;
    std::erase_if(callbacks, [](const auto& weak) { return weak.expired(); });
    auto relay = std::make_shared<CaptureCallback>(CaptureCallback{frame->m_self, std::move(callback)});
    callbacks.emplace_back(relay);
    return reinterpret_cast<FrameShare>(shareHook->m_original)(frame, buffer, damage, [relay](eScreenshareResult result) {
        relay->original(relay->failed && result == RESULT_COPIED ? RESULT_NOT_COPIED : result);
    });
}

void renderLayer(IHyprRenderer* renderer, PHLLS layer, PHLMONITOR monitor, const Time::steady_tp& now, bool popups, bool lockscreen) {
    if (!capturing || !privateLayer(layer))
        reinterpret_cast<LayerRender>(layerHook->m_original)(renderer, layer, monitor, now, popups, lockscreen);
}

void renderWindow(IHyprRenderer* renderer, PHLWINDOW window, PHLMONITOR monitor, const Time::steady_tp& now, bool decorate,
                  eRenderPassMode mode, bool ignorePosition, bool standalone) {
    if (!capturing || !window->m_ruleApplicator->noScreenShare().valueOrDefault())
        reinterpret_cast<WindowRender>(windowHook->m_original)(renderer, window, monitor, now, decorate, mode, ignorePosition, standalone);
}

void renderFadeouts(IHyprRenderer* renderer, PHLMONITOR monitor, Desktop::eFadeoutPlane plane, PHLWORKSPACE workspace) {
    // ponytail: omit capture fadeouts until upstream snapshots carry source privacy.
    if (!capturing)
        reinterpret_cast<FadeoutRender>(fadeoutHook->m_original)(renderer, monitor, plane, workspace);
}

void renderDrag(IHyprRenderer* renderer, PHLMONITOR monitor, const Time::steady_tp& now) {
    if (!capturing)
        reinterpret_cast<DragRender>(dragHook->m_original)(renderer, monitor, now);
}

void renderCursor(CCursorshareSession*) {
    g_pHyprRenderer->draw(CClearPassElement::SClearData{CHyprColor(0, 0, 0, 0)});
}

CFunctionHook* install(const std::string& name, const void* replacement) {
    auto matches = HyprlandAPI::findFunctionsByName(handle, name.substr(name.rfind("::") + 2));
    std::erase_if(matches, [&](const auto& match) { return !match.demangled.contains(name + "("); });
    if (matches.size() != 1)
        throw std::runtime_error("Private capture requires exactly one symbol: " + name);
    auto* hook = HyprlandAPI::createFunctionHook(handle, matches[0].address, replacement);
    if (!hook || !hook->hook())
        throw std::runtime_error("Cannot hook private capture symbol: " + name);
    hooks.push_back(hook);
    return hook;
}
}

APICALL EXPORT std::string PLUGIN_API_VERSION() { return HYPRLAND_API_VERSION; }

APICALL EXPORT PLUGIN_DESCRIPTION_INFO PLUGIN_INIT(HANDLE pluginHandle) {
    handle = pluginHandle;
    if (HyprlandAPI::getHyprlandVersion(handle).hash != SUPPORTED_BUILD || std::string(GIT_COMMIT_HASH) != SUPPORTED_BUILD ||
        std::string(__hyprland_api_get_hash()) != __hyprland_api_get_client_hash())
        throw std::runtime_error("Luma private capture needs matching supported Hyprland headers and binary");
    const auto& manager = Screenshare::mgr();
    for (const auto& weak : manager->m_sessions) {
        const auto* session = weak.expired() ? nullptr : weak.get();
        if (session && (session->m_sharing || (session->m_tempFB && session->m_tempFB->isAllocated())))
            throw std::runtime_error("Stop screen capture before loading Luma private capture");
    }
    for (const auto& weak : manager->m_pendingFrames) {
        const auto* frame = weak.expired() ? nullptr : weak.get();
        if (frame && !frame->done())
            throw std::runtime_error("Stop screen capture before loading Luma private capture");
    }
    try {
        layerHook = install("IHyprRenderer::renderLayer", reinterpret_cast<const void*>(&renderLayer));
        windowHook = install("IHyprRenderer::renderWindow", reinterpret_cast<const void*>(&renderWindow));
        fadeoutHook = install("IHyprRenderer::renderFadeouts", reinterpret_cast<const void*>(&renderFadeouts));
        dragHook = install("IHyprRenderer::renderDragIcon", reinterpret_cast<const void*>(&renderDrag));
        install("CCursorshareSession::render", reinterpret_cast<const void*>(&renderCursor));
        install("CScreenshareFrame::renderMonitor", reinterpret_cast<const void*>(&renderCapture));
        shareHook = install("CScreenshareFrame::share", reinterpret_cast<const void*>(&shareFrame));
    } catch (...) {
        for (auto* hook : hooks)
            HyprlandAPI::removeFunctionHook(handle, hook);
        hooks.clear();
        throw;
    }
    return {"luma-capture", "Capture a fresh desktop scene without Luma overlays", "Modesty", "0.1.0"};
}

APICALL EXPORT void PLUGIN_EXIT() {
    for (const auto& weak : callbacks) {
        if (const auto callback = weak.lock()) {
            if (!callback->frame.expired()) {
                auto* frame = callback->frame.get();
                frame->m_callback = std::move(callback->original);
                if (callback->failed && !frame->m_copied && !frame->m_failed) {
                    frame->m_failed = true;
                    frame->m_copied = true;
                    const auto notify = frame->m_callback;
                    notify(RESULT_NOT_COPIED);
                }
            }
        }
    }
    callbacks.clear();
    scenes.clear();
}
