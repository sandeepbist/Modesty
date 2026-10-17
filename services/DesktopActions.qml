pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Networking
import Quickshell.Services.Mpris
import Quickshell.Services.Pipewire
import qs.theme

Singleton {
    id: root
    property var pending: ({})
    property int sequence: 0
    PwObjectTracker { objects: Audio.outputs.concat(Audio.inputs) }
    readonly property var preferenceKeys: ["remindersEnabled","deviceIndicator","contextDevices","contextBattery","compactMissingLyrics","launcherCalculator","launcherDescriptions","matugenAutomatic","themeGtk","themeFolders","themeQt","themeFoot","themeSpotify","footerTray","footerVisible","footerSettings","recordCursor","crispText","liveMedia","mediaAutoHide","focusQuiet","footerPerformance","mediaVisualizer","mediaLyrics","fuzzyApps","rememberApps","terminalGreeting","terminalArtFavoritesOnly","terminalArtMinimal","companionEnabled","companionZen","companionTerminal","agentFeedback","contextWorkspace","contextVolume","contextBrightness","welcomeAtLogin","contextEvents","wallpaperColors","use24Hour","showSeconds","showAlbum","showStatus","shadows","focusMinutes","breakMinutes","recordCountdown","matugenContrast","matugenSource","wallpaperDuration","windowGap","trayIconSize","traySpacing","controlGap","controlRadius","controlIconSize","sliderThickness","terminalArtSize","launcherVisibleRows","companionSize","companionInset","contextDuration","tooltipDelay","hoverLift","motionSpeed","notificationDuration","uiScale","topMargin","barHeight","collapsedWidth","clusterGap","expandedRadius","innerPadding","mediaWidth","controlsWidth","launcherWidth","calendarWidth","motion","wallpaperTransition","fontFamily","clockFontFamily","companionSide","terminal","terminalArtMode","terminalArtFormat","terminalArtCollection","matugenScheme","recordFps"]
    function refused(error:string):var { return {ok:false,status:"refused",error}; }
    function level(value:var):bool { return typeof value==="number"&&Number.isFinite(value)&&value>=0&&value<=100; }
    function deviceId(node:var):string { return node?String(node.id):""; }
    function networkId(network:var):string { return Wireless.device?.name+":"+network.name; }
    function ticket(action:var,service:string,result:var):var {
        if(!result.ok)return result;
        const id="desktop-"+Date.now().toString(36)+"-"+(++sequence);
        const next=Object.assign({},pending);next[id]={action,service,source:result.ticket||"",id:result.id||"",started:Date.now()};
        const keys=Object.keys(next);for(const key of keys.slice(0,Math.max(0,keys.length-128)))delete next[key];pending=next;
        return Object.assign({},result,{ticket:id,status:result.status==="persisted"?"persisted":"requested"});
    }
    function receipt(id:string):var {
        const entry=pending[id];if(!entry)return refused("Unknown action receipt");
        if(entry.service==="notes")return Notes.receipt(entry.source);
        if(entry.service==="reminders")return Reminders.receipt(entry.source);
        const observed=observe(entry.action);
        if(observed.error)return {ok:false,status:"failed",error:observed.error};
        if(observed.verified)return {ok:true,status:"verified",id:entry.id};
        return {ok:true,status:"requested",id:entry.id};
    }
    function observe(action:var):var {
        const a=action.args,name=action.name;
        const player=a.id?Media.players.find(p=>p.dbusName===a.id):Media.active;
        const node=(name.startsWith("microphone")?Audio.inputs:Audio.outputs).find(n=>deviceId(n)===a.id)||(a.id?null:name.startsWith("microphone")?Audio.source:Audio.sink);
        let verified=false,error="";
        switch(name){
        case "volume":verified=Math.abs(Audio.volume*100-a.level)<1;break;
        case "brightness":verified=!SystemInfo.brightnessDirty&&!SystemInfo.brightnessInFlight&&SystemInfo.brightnessAcknowledgedSequence===SystemInfo.brightnessSequence&&Math.abs(SystemInfo.brightness*100-a.level)<1;error=SystemInfo.error;break;
        case "audio_mute":case "microphone_mute":verified=!!node?.audio&&node.audio.muted===a.muted;if(!node?.audio)error="Audio device no longer available";break;
        case "microphone_volume":verified=!!node?.audio&&Math.abs(node.audio.volume*100-a.level)<1;if(!node?.audio)error="Audio device no longer available";break;
        case "audio_device":verified=deviceId(a.direction==="output"?Audio.sink:Audio.source)===a.id;break;
        case "appearance":verified=Theme.mode===a.mode;error=Theme.syncError;break;
        case "palette":verified=Theme.paletteName===a.name;error=Theme.syncError;break;
        case "wallpaper":verified=SystemInfo.wallpaper===a.path&&!SystemInfo.busy;error=SystemInfo.error;break;
        case "focus":verified=FocusTimer.phase==="running"&&FocusTimer.duration===a.minutes*60;break;
        case "focus_pause":verified=FocusTimer.phase===(a.paused===false?"running":"paused");break;
        case "focus_cancel":verified=FocusTimer.phase==="idle";break;
        case "awake":verified=KeepAwake.active===a.enabled;error=KeepAwake.error;break;
        case "peace":verified=Notifications.dnd===a.enabled;break;
        case "nightlight":verified=Display.nightLight===a.enabled&&!Display.nightDirty&&!Display.nightInFlight&&Display.nightAcknowledged;error=Display.error;break;
        case "wifi":verified=Wireless.enabled===a.enabled;error=SystemInfo.error;break;
        case "bluetooth":verified=Radio.enabled===a.enabled;error=Radio.error;break;
        case "wifi_connect":case "wifi_disconnect":case "wifi_forget":{
            const network=Wireless.networks.find(n=>networkId(n)===a.id);error=Wireless.error;
            verified=name==="wifi_forget"?!network?.known:name==="wifi_connect"?network?.connected===true:!network?.connected;
            break;
        }
        case "bluetooth_connect":case "bluetooth_disconnect":case "bluetooth_pair":case "bluetooth_forget":{
            const device=Radio.devices.find(d=>d.dbusPath===a.id);error=Radio.error;
            verified=name==="bluetooth_forget"?!device?.paired:name==="bluetooth_pair"?device?.paired===true:name==="bluetooth_connect"?device?.connected===true:!device?.connected;
            break;
        }
        case "media_play":verified=player?.isPlaying===true;break;
        case "media_pause":verified=!!player&&!player.isPlaying;break;
        case "media_stop":verified=!!player&&player.playbackState===MprisPlaybackState.Stopped;break;
        case "media_seek":verified=!!player&&Math.abs(player.position-a.seconds)<2;break;
        case "media_repeat":verified=!!player&&player.loopState===({none:MprisLoopState.None,track:MprisLoopState.Track,playlist:MprisLoopState.Playlist})[a.mode];break;
        case "media_shuffle":verified=!!player&&player.shuffle===a.enabled;break;
        case "recording_start":verified=Recorder.phase==="recording";error=Recorder.status.error||"";break;
        case "recording_pause":verified=Recorder.phase===(a.paused?"paused":"recording");error=Recorder.status.error||"";break;
        case "recording_stop":verified=Recorder.phase==="saved";error=Recorder.status.error||"";break;
        case "notification_dismiss":verified=!Notifications.list.some(n=>String(n.serial)===a.id&&!n.closing);break;
        case "notification_clear":verified=!Notifications.list.some(n=>!n.closing);break;
        case "preference":verified=Preferences[a.key]===a.value&&!Preferences.saveError;error=Preferences.saveError;break;
        case "open_panel":verified=IslandState.menu===a.panel;break;
        case "note_open":verified=IslandState.menu==="notes"&&Notes.activeId===a.id;break;
        case "lock":verified=Session.isLocked();break;
        case "display":error=Display.error;break;
        case "update":error=Updates.state.phase==="failed"?Updates.state.error||Updates.state.message:"";verified=a.operation==="check"&&Updates.state.phase==="ready"||a.operation==="download"&&Updates.state.phase==="staged";break;
        }
        return {verified,error};
    }
    function execute(action:var,operationId:string):var {
        if(Preferences.preview||Session.isLocked()||!Preferences.lumaDesktop||!action||!action.args||typeof action.args!=="object")return refused("Native controls unavailable");
        const a=Object.assign({},action.args),name=action.name;
        action=Object.assign({},action,{args:a});
        const player=a.id?Media.players.find(p=>p.dbusName===a.id):Media.active;
        if(name.startsWith("media_")&&player)a.id=player.dbusName;
        let node=null,result={ok:true,status:"requested"};
        switch(name){
        case "note_create":case "note_update":case "note_append":case "note_pin":case "note_archive":case "note_trash":case "note_restore":case "note_delete":case "note_export":{
            const kind={note_create:"create",note_update:"update",note_append:"append",note_pin:"pin",note_archive:"status",note_trash:"status",note_restore:"status",note_delete:"delete",note_export:"export"}[name];
            const command=Object.assign({},a,{kind});
            if(name==="note_archive")command.status="archived";else if(name==="note_trash")command.status="trash";else if(name==="note_restore")command.status="active";
            return ticket(action,"notes",Notes.request(command,operationId));
        }
        case "note_open":
            if(typeof a.id!=="string"||!Notes.select(a.id))return refused("Note could not be selected");
            CanvasState.close();IslandState.openMenu("notes");break;
        case "reminder":case "reminder_update":case "reminder_remove":case "reminder_complete":{
            if(!Preferences.remindersEnabled)return refused("Reminders disabled in Settings");
            const kind={reminder:"create",reminder_update:"update",reminder_remove:"remove",reminder_complete:"complete"}[name];
            return ticket(action,"reminders",Reminders.request(Object.assign({},a,{kind}),operationId));
        }
        case "volume":if(!level(a.level)||!Audio.sink?.audio)return refused("Audio output unavailable");Audio.setVolume(a.level/100);break;
        case "brightness":if(!level(a.level)||!SystemInfo.brightnessAvailable)return refused("Brightness unavailable");SystemInfo.setBrightness(a.level/100);break;
        case "audio_mute":case "microphone_mute":case "microphone_volume":
            node=(name.startsWith("microphone")?Audio.inputs:Audio.outputs).find(n=>deviceId(n)===a.id)||(a.id?null:name.startsWith("microphone")?Audio.source:Audio.sink);
            if(!node?.audio)return refused("Audio device no longer available");
            a.id=deviceId(node);
            if(name==="microphone_volume"){if(!level(a.level))return refused("Invalid microphone volume");Audio.setNodeVolume(node,a.level/100);}
            else {if(typeof a.muted!=="boolean")return refused("Invalid mute state");node.audio.muted=a.muted;}
            break;
        case "audio_device":
            if(!["output","input"].includes(a.direction))return refused("Invalid audio direction");
            node=(a.direction==="output"?Audio.outputs:Audio.inputs).find(n=>deviceId(n)===a.id);if(!node)return refused("Audio device no longer available");Audio.setDefault(node,a.direction==="output");break;
        case "focus":if(!FocusTimer.loaded||!Number.isInteger(a.minutes)||a.minutes<1||a.minutes>120)return refused("Invalid focus duration");FocusTimer.start(a.minutes,false);break;
        case "focus_pause":
            if(!["running","paused"].includes(FocusTimer.phase))return refused("No active focus timer");
            if(a.paused===undefined)a.paused=FocusTimer.phase==="running";
            if(typeof a.paused!=="boolean")return refused("Invalid focus state");
            if((FocusTimer.phase==="paused")!==a.paused)FocusTimer.pause();break;
        case "focus_cancel":if(!FocusTimer.loaded)return refused("Focus unavailable");FocusTimer.cancel();break;
        case "appearance":if(!["light","dark"].includes(a.mode))return refused("Invalid appearance");Theme.setMode(a.mode);break;
        case "awake":if(typeof a.enabled!=="boolean")return refused("Invalid awake state");if(a.enabled&&a.seconds){if(!KeepAwake.setFor(a.seconds))return refused(KeepAwake.error||"Invalid awake duration");}else KeepAwake.setActive(a.enabled);break;
        case "peace":if(typeof a.enabled!=="boolean")return refused("Invalid peace state");Notifications.dnd=a.enabled;break;
        case "nightlight":if(typeof a.enabled!=="boolean")return refused("Invalid night light state");Display.setNightLight(a.enabled);break;
        case "wifi":if(typeof a.enabled!=="boolean"||!Wireless.available||!Wireless.hardwareEnabled)return refused("Wi-Fi unavailable or hardware blocked");SystemInfo.action("wifi",String(a.enabled));break;
        case "bluetooth":if(typeof a.enabled!=="boolean"||!Radio.available||Radio.blocked)return refused("Bluetooth unavailable or blocked");Radio.adapter.enabled=a.enabled;break;
        case "wifi_connect":case "wifi_disconnect":case "wifi_forget":{
            const network=Wireless.networks.find(n=>networkId(n)===a.id);if(!network||Wireless.busy)return refused("Network unavailable or busy");
            CanvasState.close();IslandState.openMenu("wifi");
            if(name==="wifi_connect")Wireless.join(network,"");else if(name==="wifi_disconnect")Wireless.disconnect(network);else Wireless.forget(network);
            break;
        }
        case "bluetooth_connect":case "bluetooth_disconnect":case "bluetooth_pair":case "bluetooth_forget":{
            const device=Radio.devices.find(d=>d.dbusPath===a.id);if(!device||Radio.busy)return refused("Bluetooth device unavailable or busy");
            CanvasState.close();IslandState.openMenu("bluetooth");Radio.act(device,name.replace("bluetooth_",""));break;
        }
        case "media_play":if(!player||!Media.play(player))return refused("Playback unavailable");break;
        case "media_pause":if(!player||!Media.pause(player))return refused("Pause unavailable");break;
        case "media_next":case "media_previous":if(!player||(name==="media_next"?!player.canGoNext:!player.canGoPrevious))return refused("Track control unavailable");if(name==="media_next")player.next();else player.previous();break;
        case "media_stop":if(!player?.canControl)return refused("Media stop unavailable");player.stop();break;
        case "media_seek":if(!player?.canSeek||!Number.isFinite(a.seconds)||a.seconds<0||!player.length||a.seconds>player.length)return refused("Seek outside this track");player.position=a.seconds;Media.sync();break;
        case "media_repeat":if(!player?.canControl||!player.loopSupported||!["none","track","playlist"].includes(a.mode))return refused("Repeat unavailable");player.loopState=({none:MprisLoopState.None,track:MprisLoopState.Track,playlist:MprisLoopState.Playlist})[a.mode];break;
        case "media_shuffle":if(!player?.canControl||!player.shuffleSupported||typeof a.enabled!=="boolean")return refused("Shuffle unavailable");player.shuffle=a.enabled;break;
        case "recording_start":if(Recorder.active)return refused("Recording already active");Recorder.start(a.region===true,a.sound===true);break;
        case "recording_pause":if(!Recorder.recording||typeof a.paused!=="boolean")return refused("No recording to pause");if((Recorder.phase==="paused")!==a.paused)Recorder.pause();break;
        case "recording_stop":if(!Recorder.active)return refused("No active recording");Recorder.stop();break;
        case "notification_dismiss":{
            const notification=Notifications.list.find(n=>String(n.serial)===a.id);if(!notification)return refused("Notification no longer available");Notifications.close(notification);break;
        }
        case "notification_clear":Notifications.clearAll();break;
        case "palette":if(typeof a.name!=="string"||!Theme.palettes[a.name])return refused("Palette unavailable");Theme.setPalette(a.name);break;
        case "wallpaper":if(typeof a.path!=="string"||!SystemInfo.wallpapers.some(w=>w.path===a.path))return refused("Wallpaper unavailable");SystemInfo.applyWallpaper(a.path);break;
        case "display":{
            const monitor=Display.monitors.find(m=>m.name===a.id);if(!monitor||typeof a.mode!=="string"||!monitor.availableModes.includes(a.mode)||!Number.isFinite(a.scale)||a.scale<.5||a.scale>3||Display.busy)return refused("Display mode unavailable");
            CanvasState.close();IslandState.openMenu("display");Display.change(a.id,a.mode,a.scale);break;
        }
        case "preference":
            if(!preferenceKeys.includes(a.key))return refused("Use Settings to change access or privacy permissions");
            if(typeof a.value!==typeof Preferences.defaults[a.key]||typeof a.value==="number"&&(!Number.isFinite(a.value)||!["uiScale","matugenContrast","wallpaperDuration","motionSpeed"].includes(a.key)&&!Number.isInteger(a.value)))return refused("Invalid preference value");
            Preferences.set(a.key,a.value);break;
        case "lock":Session.lock(false);break;
        case "sleep":if(!["suspend","hibernate","hybrid-sleep","suspend-then-hibernate"].includes(a.mode))return refused("Unsupported sleep mode");Session.requestSleep(a.mode);break;
        case "system":if(!["logout","reboot","poweroff"].includes(a.operation))return refused("Unsupported system operation");SystemInfo.action(a.operation,"");break;
        case "update":if(!["check","download","apply","rollback","reload"].includes(a.operation)||Updates.busy)return refused("Update unavailable or busy");Updates.run(a.operation);break;
        case "open_app":{
            const app=Apps.apps.find(app=>app.id===a.id);if(!app||Apps.launching)return refused("Application unavailable or launching");CanvasState.close();Apps.launch(app);break;
        }
        case "close_app":{
            const app=Apps.apps.find(app=>app.id===a.id);if(!app||!Apps.close(app))return refused("Application could not close");break;
        }
        case "file_action":if(!["compress","merge","export"].includes(a.operation)||!Array.isArray(a.paths)||!IslandDrop.perform(a.paths,a.operation,a))return refused("File operation unavailable");break;
        case "open_panel":if(!["settings","quicksettings","calendar","themes","wallpapers","wifi","bluetooth","display","sound","media","notifhistory","focus","performance","notes","recorder","privacy","power","launcher"].includes(a.panel))return refused("Panel unavailable");CanvasState.close();IslandState.openMenu(a.panel);break;
        default:return refused("Unsupported native operation");
        }
        result=ticket(action,"",result);
        return Object.assign({},result,receipt(result.ticket));
    }
}
