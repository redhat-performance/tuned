from inspect import ismethod
from dbus.service import method, signal
from dbus import PROPERTIES_IFACE
from dbus.exceptions import DBusException
from tuned.exports.dbus_exporter import DBusExporter


class DBusExporterWithProperties(DBusExporter):
    def __init__(self, bus_name, interface_name, object_name, namespace):
        super(DBusExporterWithProperties, self).__init__(bus_name, interface_name, object_name, namespace)
        self._property_setters = {}
        self._property_getters = {}

        def Get(_, interface_name, property_name, caller):
            if interface_name != self._interface_name:
                raise DBusException("Unknown interface: %s" % interface_name)
            if property_name not in self._property_getters:
                raise DBusException("No such property: %s" % property_name)
            getter = self._property_getters[property_name]
            return getter(caller)

        def Set(_, interface_name, property_name, value, caller):
            if interface_name != self._interface_name:
                raise DBusException("Unknown interface: %s" % interface_name)
            if property_name not in self._property_setters:
                raise DBusException("No such property: %s" % property_name)
            setter = self._property_setters[property_name]
            setter(value, caller)

        def GetAll(_, interface_name, caller):
            if interface_name != self._interface_name:
                raise DBusException("Unknown interface: %s" % interface_name)
            return {name: getter(caller) for name, getter in self._property_getters.items()}

        def PropertiesChanged(_, interface_name, changed_properties, invalidated_properties):
            if interface_name != self._interface_name:
                raise DBusException("Unknown interface: %s" % interface_name)

        self._dbus_methods["Get"] = method(PROPERTIES_IFACE, in_signature="ss", out_signature="v", sender_keyword="caller")(Get)
        self._dbus_methods["Set"] = method(PROPERTIES_IFACE, in_signature="ssv", sender_keyword="caller")(Set)
        self._dbus_methods["GetAll"] = method(PROPERTIES_IFACE, in_signature="s", out_signature="a{sv}", sender_keyword="caller")(GetAll)
        self._dbus_methods["PropertiesChanged"] = signal(PROPERTIES_IFACE, signature="sa{sv}as")(PropertiesChanged)
        self._signals.add("PropertiesChanged")

    def _auth_wrapper(self, method, action_name):
        def wrapper(*args, **kwargs):
            new_args = self._polkit_auth(action_name, *args)
            if new_args[-1] == "":
                raise DBusException("Unauthorized")
            return method(*new_args, **kwargs)
        return wrapper

    def property_changed(self, property_name, value):
        self.send_signal("PropertiesChanged", self._interface_name, {property_name: value}, {})

    def property_getter(self, method, property_name, action_name=None):
        if not ismethod(method):
            raise Exception("Only bound methods can be exported.")
        if property_name in self._property_getters:
            raise Exception("A getter for this property is already registered.")
        if action_name is not None:
            method = self._auth_wrapper(method, action_name)
        self._property_getters[property_name] = method

    def property_setter(self, method, property_name, action_name=None):
        if not ismethod(method):
            raise Exception("Only bound methods can be exported.")
        if property_name in self._property_setters:
            raise Exception("A setter for this property is already registered.")
        if action_name is not None:
            method = self._auth_wrapper(method, action_name)
        self._property_setters[property_name] = method
