#include <QGuiApplication>
#include <QQuickView>
#include <QQuickItem>
#include <QTest>
#include <QJSValue>
#include <iostream>
#include "context.h"

int main(int argc, char **argv) {
    QGuiApplication app(argc, argv);
    QQuickView view;
    const QString theme = QString::fromLocal8Bit(argv[1]);
    auto backend = setupContext(view.engine(), theme);
    // Use a deterministic session fixture so tests also run on a clean checkout.
    auto sessions=view.engine()->rootContext()->contextProperty("sessionModel").value<QObject *>();
    QMetaObject::invokeMethod(sessions,"clear");
    QMetaObject::invokeMethod(sessions,"addSession",Q_ARG(QVariant,QString("Hyprland")),Q_ARG(QVariant,QString("hyprland.desktop")));
    // Tests do not play audio or require the optional telemetry bridge.
    auto config = view.engine()->rootContext()->contextProperty("config").value<QObject *>();
    auto values = config->property("values").toMap(); values["Animations"]="false"; values["TelemetryUrl"]=""; config->setProperty("values", values);
    view.setResizeMode(QQuickView::SizeRootObjectToView);
    view.setSource(QUrl::fromLocalFile(theme));
    if (view.status()!=QQuickView::Ready) return 1;
    view.resize(1920,1080); view.show(); QTest::qWait(100);
    auto root = view.rootObject();
    std::function<QObject *(QQuickItem *,const QString &)> visualFind = [&](QQuickItem *item,const QString &name)->QObject * {
        if(item->objectName()==name) return item;
        for(auto next:item->childItems()) if(auto found=visualFind(next,name)) return found;
        return nullptr;
    };
    auto child = [&](const char* name) { auto item=root->findChild<QObject *>(name); if(!item) item=visualFind(root,name); if (!item) qFatal("Missing object %s",name); return item; };
    auto user=child("username"), pass=child("password");
    int failures=0;
    auto check = [&](bool condition, const char* label) { std::cout << (condition?"PASS ":"FAIL ") << label << std::endl; if(!condition) failures++; };
    auto click = [&](const char* name) { auto item=qobject_cast<QQuickItem *>(child(name)); QTest::mouseClick(&view,Qt::LeftButton,Qt::NoModifier,item->mapToScene(QPointF(item->width()/2,item->height()/2)).toPoint()); QTest::qWait(25); };
    auto submit = [&]() { QMetaObject::invokeMethod(root,"submit"); };
    check(root->property("host").toString()==QSysInfo::machineHostName(),"greeting resolves hostname");
    check(user->property("text").toString()==qEnvironmentVariable("USER"),"input resolves login username");
    check(!root->property("animations").toBool(),"reduced motion configuration");
    check(user->property("readOnly").toBool(),"lock screen keeps current account read-only");
    check(root->property("sessionName").toString()=="Hyprland","preferred installed session");
    user->setProperty("text",""); pass->setProperty("text","test"); submit();
    check(backend->property("calls").toInt()==0 && root->property("failed").toBool(),"empty username blocks authentication");
    user->setProperty("text","demo"); pass->setProperty("text",""); submit();
    check(backend->property("calls").toInt()==0,"empty password blocks authentication");
    pass->setProperty("text","incorrect"); click("reveal");
    check(root->property("revealPassword").toBool(),"eye reveals password");
    submit(); submit(); QTest::qWait(900);
    check(backend->property("calls").toInt()==1,"duplicate submissions suppressed");
    check(!root->property("revealPassword").toBool(),"authentication conceals password");
    check(root->property("failed").toBool() && !root->property("busy").toBool() && pass->property("text").toString().isEmpty(),"failed sign-in clears password and restores input");
    pass->setProperty("text","temporary"); qobject_cast<QQuickItem *>(pass)->forceActiveFocus(); QTest::keyClick(&view,Qt::Key_Escape);
    check(pass->property("text").toString().isEmpty(),"Escape clears password");
    click("session-0");
    check(root->property("sessionIndex").toInt()==0,"current session is retained");
    user->setProperty("text","  demo  "); pass->setProperty("text","test");
    qobject_cast<QQuickItem *>(pass)->forceActiveFocus(); QTest::keyClick(&view,Qt::Key_Return); QTest::qWait(900);
    check(root->property("signedIn").toBool() && pass->property("text").toString().isEmpty(),"Enter submits; successful preview unlock clears password");
    check(backend->property("submittedUser").toString()=="demo" && backend->property("submittedSession").toInt()==0,"submitted username and selected session match");
    QTest::qWait(2700);
    check(!root->property("busy").toBool(),"demo success returns to locked preview");
    for(const auto &entry : {QPair<const char*,const char*>("powerOff","powerOffCalls"),{"restart","rebootCalls"},{"sleep","suspendCalls"}}) {
        click(entry.first); check(child("powerDialog")->property("visible").toBool(),"power action opens confirmation");
        click("cancelPower"); check(backend->property(entry.second).toInt()==0,"cancel causes no power action");
        click(entry.first); click("confirmPower"); check(backend->property(entry.second).toInt()==1,"confirmation invokes only mock power backend");
    }
    click("mute"); check(root->property("audioMuted").toBool(),"mute toggles ambience output");
    click("mute"); check(!root->property("audioMuted").toBool(),"unmute restores ambience output");
    auto volume=qobject_cast<QQuickItem *>(child("volume")); volume->forceActiveFocus(); QTest::keyClick(&view,Qt::Key_Right);
    check(root->property("volumeValue").toDouble()==73,"volume supports keyboard adjustment");
    backend->setProperty("canPowerOff",false); QTest::qWait(20);
    check(!child("powerOff")->property("enabled").toBool(),"unavailable power capability is disabled");
    QMetaObject::invokeMethod(sessions,"clear"); QTest::qWait(30);
    pass->setProperty("text","test"); int before=backend->property("calls").toInt(); submit();
    check(root->property("sessionIndex").toInt()==-1 && backend->property("calls").toInt()==before,"missing session blocks authentication");
    std::cout << "Failures: " << failures << std::endl;
    return failures ? 1 : 0;
}
