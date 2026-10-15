#!/usr/bin/env python3
"""Test-only login1 on an explicitly supplied private bus. Never suspends."""
import os
from gi.repository import Gio, GLib

address = os.environ["REZERO_TEST_BUS"]
bus = Gio.DBusConnection.new_for_address_sync(
    address,
    Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
    None, None,
)
bus.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "RequestName",
              GLib.Variant("(su)", ("org.freedesktop.login1", 0)), None, Gio.DBusCallFlags.NONE, -1, None)

XML = """<node>
  <interface name="org.freedesktop.login1.Manager">
    <method name="GetSession"><arg type="s" direction="in"/><arg type="o" direction="out"/></method>
    <method name="Inhibit">
      <arg type="s" direction="in"/><arg type="s" direction="in"/>
      <arg type="s" direction="in"/><arg type="s" direction="in"/>
      <arg type="h" direction="out"/>
    </method>
    <property name="BlockInhibited" type="s" access="read"/>
    <signal name="PrepareForSleep"><arg type="b"/></signal>
  </interface>
  <interface name="org.freedesktop.login1.Session"><signal name="Lock"/></interface>
  <interface name="org.example.RezeroTest">
    <method name="SimulateSleep"><arg type="b" direction="in"/></method>
    <method name="SimulateLock"/>
  </interface>
</node>"""


def called(connection, sender, path, interface, method, parameters, invocation):
    if method == "GetSession":
        invocation.return_value(GLib.Variant("(o)", ("/org/freedesktop/login1/session/test",)))
    elif method == "Inhibit":
        # This FD is only a test token, never a host sleep inhibitor.
        fd = os.open("/dev/null", os.O_RDONLY)
        fds = Gio.UnixFDList.new()
        index = fds.append(fd)
        os.close(fd)
        invocation.return_value_with_unix_fd_list(GLib.Variant("(h)", (index,)), fds)
    elif method == "SimulateSleep":
        connection.emit_signal(None, path, "org.freedesktop.login1.Manager", "PrepareForSleep", parameters)
        invocation.return_value(None)
    elif method == "SimulateLock":
        connection.emit_signal(None, path, "org.freedesktop.login1.Session", "Lock", None)
        invocation.return_value(None)
    else:
        invocation.return_dbus_error("org.example.RezeroTest.UnknownMethod", method)


node = Gio.DBusNodeInfo.new_for_xml(XML)
for interface in node.interfaces:
    for path in ["/org/freedesktop/login1", "/org/freedesktop/login1/session/test"]:
        bus.register_object(path, interface, called, lambda *args: GLib.Variant("s", ""), None)
print("mock logind ready", flush=True)
GLib.MainLoop().run()
