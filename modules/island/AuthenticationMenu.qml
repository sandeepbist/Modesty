import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.services
import qs.theme
import qs.components
FocusScope {
    id:root
    readonly property bool preview:SystemInfo.preview
    readonly property var flow:Authorization.flow
    readonly property bool waiting:!!flow&&!flow.isCompleted&&!flow.isResponseRequired
    readonly property bool hasError:!!flow?.supplementaryIsError
    readonly property bool canSubmit:!preview&&response.enabled&&response.text.length>0
    property bool detailsExpanded:false
    readonly property var request:Authorization.requestInfo
    readonly property var application: {
        const program=request.program??"",policy=(request.policy??"").toLowerCase();
        return DesktopEntries.applications.values.find(entry=>{
            if(program){const name=program.split("/").pop();if(/^(?:env|sh|bash|zsh|python[\d.]*|flatpak)$/.test(name))return false;const executable=entry.command?.[0]??"";return executable===program||executable.split("/").pop()===name;}
            return policy&&entry.id.toLowerCase().replace(/\.desktop$/,"")===policy;
        })??null;
    }
    readonly property string applicationName:application?.name||request.name||"Administrator access"
    readonly property string applicationIcon:application?.icon||root.flow?.iconName||request.icon||""
    readonly property string iconPath:applicationIcon&&!/^dialog-|^security-/.test(applicationIcon)?Quickshell.iconPath(applicationIcon,true):""
    implicitHeight:form.implicitHeight+28
    function measure():void {IslandState.measurePanel("authentication",implicitHeight);}
    onImplicitHeightChanged:Qt.callLater(measure)
    property real shake:0
    function focusResponse():void {if(response.enabled)response.forceActiveFocus();}
    function submit():void {if(canSubmit){Authorization.submit(response.text);response.clear();}}
    function dismiss():void {if(!preview)Authorization.cancel();IslandState.closeMenu();}
    onActiveFocusChanged:if(activeFocus)Qt.callLater(focusResponse)
    Component.onCompleted:{Qt.callLater(focusResponse);Qt.callLater(measure);}
    Connections {target:Authorization;function onFlowChanged(){response.clear();root.detailsExpanded=false;Qt.callLater(root.focusResponse);}}
    Connections {
        target:root.flow
        function onAuthenticationFailed(){response.clear();if(!Tokens.reducedMotion)errorMotion.restart();Qt.callLater(root.focusResponse);}
        function onSelectedIdentityChanged(){response.clear();Qt.callLater(root.focusResponse);}
    }
    ColumnLayout {
        id:form;x:14;y:14;width:Math.max(0,parent.width-28);spacing:12
        Item {
            Layout.fillWidth:true;Layout.preferredHeight:52
            Image {id:brand;anchors.centerIn:parent;width:48;height:48;source:root.iconPath;sourceSize:Qt.size(96,96);fillMode:Image.PreserveAspectFit;mipmap:true;visible:status===Image.Ready}
            AuthorizationEmblem {anchors.centerIn:parent;visible:brand.status!==Image.Ready}
            IconButton {
                anchors.right:parent.right;anchors.top:parent.top;size:15;icon:root.detailsExpanded?"expand_less":"info"
                label:root.detailsExpanded?"Hide permission details":"Permission details";color:Theme.subtext
                visible:!!root.flow?.message&&!!root.request.caption
                onClicked:root.detailsExpanded=!root.detailsExpanded
            }
        }
        ColumnLayout {
            Layout.fillWidth:true;spacing:5
            PanelText {
                Layout.fillWidth:true;horizontalAlignment:Text.AlignHCenter
                text:root.applicationName
                font.pixelSize:19;font.weight:Font.DemiBold;font.letterSpacing:-.3
            }
        }
        Flickable {
            Layout.fillWidth:true;Layout.preferredHeight:Math.min(88,message.implicitHeight)
            visible:!!root.flow?.message
            contentHeight:message.implicitHeight;clip:true;boundsBehavior:Flickable.StopAtBounds
            ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
            PanelText {
                id:message;width:parent.width-8;x:4
                text:root.detailsExpanded?root.flow?.message??"":root.request.caption||root.flow?.message||""
                horizontalAlignment:Text.AlignHCenter
                wrapMode:Text.Wrap;elide:Text.ElideNone;font.pixelSize:13;lineHeight:1.25;color:Theme.subtext
            }
        }
        ComboBox {
            id:identity;Layout.fillWidth:true;Layout.preferredHeight:36
            visible:(root.flow?.identities?.length??0)>1
            model:root.flow?.identities??[];textRole:"displayName"
            currentIndex:model.indexOf(root.flow?.selectedIdentity)
            onActivated:index=>{if(root.flow)root.flow.selectedIdentity=model[index];}
            Accessible.name:"Authorize as";font.family:Tokens.font;font.pixelSize:12
            background:Rectangle {radius:10;color:Theme.surfaceSolid;border.width:1;border.color:identity.activeFocus?Theme.accent:Theme.withAlpha(Theme.text,.12)}
            contentItem:PanelText {leftPadding:12;rightPadding:28;text:identity.displayText;verticalAlignment:Text.AlignVCenter;font.pixelSize:12}
        }
        EntryField {
            id:response;Layout.fillWidth:true;implicitHeight:46;leftPadding:14;rightPadding:14;font.pixelSize:16
            horizontalAlignment:TextInput.AlignHCenter
            transform:Translate {x:root.shake}
            property string hint:root.waiting?"":root.flow?.inputPrompt||"Password"
            placeholderText:""
            echoMode:root.flow?.responseVisible?TextInput.Normal:TextInput.Password
            color:echoMode===TextInput.Normal?Theme.text:"transparent"
            selectedTextColor:color
            passwordMaskDelay:0;passwordCharacter:"●"
            enabled:root.preview||(root.flow?.isResponseRequired??false)
            onEnabledChanged:{if(enabled)Qt.callLater(root.focusResponse);else clear();}
            onAccepted:root.submit()
            Accessible.name:root.flow?.inputPrompt||"Password"
            cursorDelegate:Rectangle {width:1;color:Theme.accent;visible:response.echoMode===TextInput.Normal&&response.text.length>0&&response.cursorVisible}
            PasswordDots {
                anchors.centerIn:parent;maximumWidth:parent.width-48
                length:Array.from(response.text).length
                visible:response.echoMode===TextInput.Password
            }
            PanelText {
                anchors.fill:parent;anchors.leftMargin:14;anchors.rightMargin:14
                text:response.hint;visible:!response.text.length&&!response.preeditText.length
                font.family:Tokens.font;font.pixelSize:13;color:Theme.subtext
                horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter
            }
            background:Rectangle {
                radius:Tokens.fieldRadius;color:Theme.withAlpha(Theme.text,response.activeFocus?.045:.025)
                gradient:Gradient {
                    GradientStop {position:0;color:Theme.withAlpha(Theme.text,response.activeFocus?.065:.04)}
                    GradientStop {position:1;color:Theme.withAlpha(Theme.text,response.activeFocus?.03:.02)}
                }
                Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                Rectangle {
                    anchors.fill:parent;radius:parent.radius;color:Theme.withAlpha(Theme.red,.07)
                    opacity:root.hasError?1:0
                    Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
                }
                SurfaceLighting {anchors.fill:parent;radius:parent.radius;focused:response.activeFocus;working:root.waiting}
            }
        }
        PanelText {
            Layout.fillWidth:true;visible:!!root.flow?.supplementaryMessage
            horizontalAlignment:Text.AlignHCenter
            text:root.flow?.supplementaryMessage??"";font.pixelSize:11
            color:root.hasError?Theme.red:Theme.subtext;wrapMode:Text.Wrap;maximumLineCount:3;elide:Text.ElideRight
        }
        RowLayout {
            Layout.alignment:Qt.AlignHCenter;spacing:12
            ActionButton {
                Layout.preferredWidth:112;implicitHeight:36;text:"Cancel";onClicked:root.dismiss()
                background:Rectangle {
                    radius:10;color:parent.hovered?Theme.withAlpha(Theme.text,.07):"transparent"
                    border.width:parent.activeFocus?1:0;border.color:Theme.accent
                    Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                }
            }
            ActionButton {
                id:confirm;Layout.preferredWidth:112;implicitHeight:36;text:root.waiting?"Verifying…":"Allow"
                primary:true;enabled:root.canSubmit;onClicked:root.submit()
                opacity:1
                background:Rectangle {
                    radius:10;color:confirm.enabled?Theme.accent:Theme.withAlpha(Theme.accent,.08)
                    border.width:1;border.color:confirm.activeFocus?Theme.text:Theme.withAlpha(Theme.accent,confirm.enabled?0:.12)
                    Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                    Rectangle {anchors.fill:parent;radius:parent.radius;color:Theme.withAlpha(Theme.bgSolid,confirm.down?.14:confirm.hovered?.06:0)}
                }
                contentItem:PanelText {
                    text:confirm.text;font.pixelSize:12;font.weight:Font.Medium
                    color:confirm.enabled?Theme.accentText:Theme.subtext
                    horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter
                    Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                }
            }
        }
    }
    SequentialAnimation {
        id:errorMotion
        NumberAnimation {target:root;property:"shake";to:-3;duration:55}
        NumberAnimation {target:root;property:"shake";to:3;duration:85}
        NumberAnimation {target:root;property:"shake";to:0;duration:95;easing.type:Easing.OutCubic}
    }
    Component.onDestruction:response.clear()
}
