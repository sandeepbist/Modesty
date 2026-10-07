pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Services.Notifications
import qs.theme
Singleton {
    id: root
    property var list: []
    readonly property ListModel historyModel: ListModel {}
    property int nextSerial:0
    property real popupHeight:116
    property bool dnd: false
    readonly property var popups: list.filter(n => n.popup)
    function dismiss(n, expired = false): void {
        if (!n || n.popupClosing) return;
        n.expired = expired;
        n.popupClosing = true;
        n.popupExit.start();
    }
    function close(n, delay = 0): void {
        if (!n || n.closing) return;
        n.removalDelay = delay;
        n.closing = true;
        dismiss(n);
        n.removal.start();
    }
    function removeRecord(n): void {
        for (let i=0;i<historyModel.count;i++) if(historyModel.get(i).record===n) {historyModel.remove(i);break;}
        list = list.filter(x => x !== n);
        if (n.notification) n.notification.dismiss();
        n.destroy(Tokens.animMedium+50);
    }
    function clearAll(): void { list.slice().forEach((n,i)=>close(n,Tokens.reducedMotion?0:Math.min(i*24,144))); }
    function add(record): void {
        historyModel.insert(0,{record}); list=[record,...list];
        // Closing records remain until their exit animation finishes. Count
        // retained records so a burst does not keep closing the same oldest one.
        const retained = list.filter(n => !n.closing);
        if (retained.length > 50) close(retained[retained.length - 1]);
    }
    onDndChanged: if (dnd) for (const n of list) dismiss(n)
    function previewNotify(timeout: int): void {
        if (Quickshell.env("MODESTY_PREVIEW") !== "1") return;
        const record = recordComponent.createObject(root, { serial:++root.nextSerial, appName: "Modesty", summary: "Screenshot saved", body: "Your capture is ready in Pictures", popup: !dnd, timeout });
        add(record);
    }
    function remind(id:string,title:string,body:string,open,complete):void {
        for(const old of list.filter(n=>n.reminderId===id))close(old);
        const n=recordComponent.createObject(root,{serial:++root.nextSerial,reminderId:id,appName:"Reminder",summary:title,body,popup:!dnd,timeout:Preferences.notificationDuration});
        n.localActions=[{identifier:"default",text:"Open",invoke:()=>{open();root.dismiss(n);}},{identifier:"complete",text:"Done",invoke:()=>complete()}];
        add(n);
    }
    // The installed 0.3.1 service exposes expireTimeout in milliseconds (verified via D-Bus).
    function track(notification): void {
        notification.tracked = true;
        const record = recordComponent.createObject(root, { serial:++root.nextSerial, notification, appName: notification.appName, appIcon:notification.appIcon, summary: notification.summary, body: notification.body, popup: !dnd, timeout: notification.expireTimeout === 0 ? 0 : notification.expireTimeout > 0 ? Math.round(notification.expireTimeout) : Preferences.notificationDuration });
        add(record);
    }
    Loader {
        active: Quickshell.env("MODESTY_PREVIEW") !== "1"
        sourceComponent: Component {
            NotificationServer {
                actionsSupported: true
                bodySupported: true
                bodyMarkupSupported: false
                persistenceSupported: false
                onNotification: notification => root.track(notification)
            }
        }
    }
    Component {
        id: recordComponent
        QtObject {
            id: record
            property int serial:0
            property var notification: null
            property string reminderId:""
            property var localActions:[]
            property string appName: ""
            property string appIcon: ""
            property date receivedAt: new Date()
            property string summary: ""
            property string body: ""
            property bool popup: false
            property bool popupClosing: false
            property bool popupHovered: false
            property bool closing: false
            property bool expired: false
            property int removalDelay: 0
            property int timeout: 6000
            readonly property var actions: notification?.actions ?? localActions
            function invokeAction(identifier: string): void { const a = actions.find(a => a.identifier === identifier); if (a) a.invoke(); }
            readonly property Timer expiry: Timer { interval: record.timeout; running: record.popup && !record.popupClosing && !record.popupHovered && record.timeout > 0; onTriggered: root.dismiss(record,true) }
            readonly property Timer popupExit: Timer {interval:Tokens.animMedium;onTriggered:{record.popup=false;if(record.notification){if(record.expired)record.notification.expire();else record.notification.dismiss();}}}
            readonly property Timer removal: Timer {interval:Tokens.animMedium+record.removalDelay+16;onTriggered:root.removeRecord(record)}
            readonly property Connections connection: Connections {
                target: record.notification
                function onClosed() { root.dismiss(record); record.notification = null; }
            }
        }
    }
}
