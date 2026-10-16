#!/usr/bin/env python3
"""Test-only MPRIS service, restricted to the explicitly supplied private bus."""
import os
from gi.repository import Gio, GLib

address = os.environ["REZERO_TEST_BUS"]
bus = Gio.DBusConnection.new_for_address_sync(address, Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION, None, None)

XML = """<node>
<interface name="org.mpris.MediaPlayer2">
  <property name="CanQuit" type="b" access="read"/>
  <property name="CanRaise" type="b" access="read"/>
  <property name="HasTrackList" type="b" access="read"/>
  <property name="Identity" type="s" access="read"/>
  <property name="DesktopEntry" type="s" access="read"/>
  <property name="SupportedUriSchemes" type="as" access="read"/>
  <property name="SupportedMimeTypes" type="as" access="read"/>
</interface>
<interface name="org.mpris.MediaPlayer2.Player">
  <method name="PlayPause"/><method name="Play"/><method name="Pause"/><method name="Next"/><method name="Previous"/>
  <property name="PlaybackStatus" type="s" access="read"/>
  <property name="Metadata" type="a{sv}" access="read"/>
  <property name="Position" type="x" access="read"/>
  <property name="CanControl" type="b" access="read"/>
  <property name="CanPlay" type="b" access="read"/>
  <property name="CanPause" type="b" access="read"/>
  <property name="CanGoNext" type="b" access="read"/>
  <property name="CanGoPrevious" type="b" access="read"/>
  <property name="CanSeek" type="b" access="read"/>
  <property name="Rate" type="d" access="read"/>
  <property name="MinimumRate" type="d" access="read"/>
  <property name="MaximumRate" type="d" access="read"/>
  <signal name="Seeked"><arg type="x"/></signal>
</interface>
<interface name="org.example.RezeroTest">
  <method name="SetCapabilities"><arg type="b" direction="in"/></method>
</interface>
</node>"""
playing, controls = True, True
path = "/org/mpris/MediaPlayer2"


def changed(values):
    bus.emit_signal(None, path, "org.freedesktop.DBus.Properties", "PropertiesChanged",
                    GLib.Variant("(sa{sv}as)", ("org.mpris.MediaPlayer2.Player", values, [])))


def called(connection, sender, object_path, interface, method, parameters, invocation):
    global playing, controls
    print(method, flush=True)
    if method == "SetCapabilities":
        controls = parameters.unpack()[0]
        changed({name: GLib.Variant("b", controls) for name in ["CanPlay", "CanPause", "CanGoNext", "CanGoPrevious"]})
    elif method in ["PlayPause", "Play", "Pause"]:
        playing = not playing if method == "PlayPause" else method == "Play"
        changed({"PlaybackStatus": GLib.Variant("s", "Playing" if playing else "Paused")})
    invocation.return_value(None)


def get_property(connection, sender, object_path, interface, name):
    if name in ["Identity", "DesktopEntry"]:
        return GLib.Variant("s", "Spotify" if name == "Identity" else "spotify")
    if name in ["SupportedUriSchemes", "SupportedMimeTypes"]:
        return GLib.Variant("as", [])
    if name == "PlaybackStatus":
        return GLib.Variant("s", "Playing" if playing else "Paused")
    if name == "Metadata":
        return GLib.Variant("a{sv}", {"mpris:trackid": GLib.Variant("o", "/test/track1"),
            "xesam:title": GLib.Variant("s", "Another Beginning"), "xesam:artist": GLib.Variant("as", ["Re:Zero test fixture"]),
            "xesam:album": GLib.Variant("s", "From Zero"), "mpris:length": GLib.Variant("x", 180000000)})
    if name == "Position":
        return GLib.Variant("x", 0)
    if name in ["Rate", "MinimumRate", "MaximumRate"]:
        return GLib.Variant("d", 1.0)
    return GLib.Variant("b", name == "CanControl" or (controls and name in ["CanPlay", "CanPause", "CanGoNext", "CanGoPrevious"]))


for interface in Gio.DBusNodeInfo.new_for_xml(XML).interfaces:
    bus.register_object(path, interface, called, get_property, None)
bus.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "RequestName",
              GLib.Variant("(su)", (os.environ.get("REZERO_MPRIS_NAME", "org.mpris.MediaPlayer2.spotify"), 0)), None, Gio.DBusCallFlags.NONE, -1, None)
print("mock Spotify ready", flush=True)
GLib.MainLoop().run()
