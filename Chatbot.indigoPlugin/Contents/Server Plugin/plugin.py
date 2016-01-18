#! /usr/bin/env python
# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Chatbot plugin for IndigoServer"""
from __future__ import unicode_literals

from UserDict import UserDict
import traceback

import indigo

from chatbot_reply import ChatbotEngine, NoRulesFoundError

# TODO - menu command to relaunch the bot, be able to do this from within the
#        bot
# TODO - save and restore bot variables
# TODO - define bot administrator
# TODO - pass enough user info into the bot that it could asynchronously reply,
#        basically the entire props dict in respondToMessage packed into a
#        hashable tuple, and some way to make it easy for scripters to do that
#        Or have them queue it up and put it in runConcurrentThread???
# TODO - have the preferences validation try to load the script files and report
#        errors then
# TODO - Prefs Config UI is maybe the logical place to put a button to reload
#        the bot files. Or maybe a menu item.
# TODO - default for scripts path can be set up by getPrefsConfigUiValues,
#       indigo.server.getDbFilePath() minus the filename on the end might be a
#       good choice
# TODO   Action Config dialog could get plugin name from device to show the user
# TODO - configuration setting for typing speed delay: Computer/Teenager/Adult
#        (0/1/5)


class Plugin(indigo.PluginBase):
    """Chatbot plugin class for IndigoServer"""

    # ----- plugin framework ----- #

    def __init__(self, plugin_id, display_name, version, prefs):
        indigo.PluginBase.__init__(self, plugin_id, display_name,
                                   version, prefs)
        self.debug = prefs.get("showDebugInfo", False)

    def startup(self):
        self.bot = ChatbotEngine(debug=True,
                                 debuglogger=self.debugLog,
                                 errorlogger=self.errorLog)

        scripts_directory = self.pluginPrefs.get("scriptsPath", "")
        self.load_scripts(scripts_directory)

    def shutdown(self):
        pass

    def update(self):
        pass

    def runConcurrentThread(self):
        try:
            while True:
                self.update()
                self.sleep(3600)  # seconds
        except self.StopThread:
            pass

    # ----- Preferences UI ----- #

    def validatePrefsConfigUi(self, values):
        """ called by the Indigo UI to validate the values dictionary for
        the Plugin Preferences user interface dialog
        """
        self.debugLog("Preferences Validation called")
        debug = values.get("showDebugInfo", False)
        if self.debug:
            if not debug:
                self.debugLog("Turning off debug logging")
        self.debug = debug
        self.debugLog("Debug logging is on")  # won't print if not self.debug

        scripts_directory = values.get("scriptsPath", "")
        self.load_scripts(scripts_directory)
        return(True, values)

    def load_scripts(self, scripts_directory):
        """ Call the chatbot engine to load scripts, catch all exceptions
        and send them to the error log.
        """
        if scripts_directory:
            try:
                self.bot.clear_rules()
                self.bot.load_script_directory(scripts_directory)
            except OSError as e:
                self.debugLog(unicode(e))
                self.errorLog("Unable to read script files from "
                              "directory '{0}'".format(
                                  scripts_directory))
            except NoRulesFoundError as e:
                self.errorLog(unicode(e))
            except Exception:
                self.errorLog(traceback.format_exc())

    # ----- Action Configuration UI ----- #

    def deviceListGenerator(self, filter="", values=None, type_id="",
                            target_id=0):
        """ Called by the Indigo UI for the Action Config dialog, to
        fill the list of devices. Filters for plugin-created devices,
        since Indigo doesn't supply that functionality.
        """
        results = []
        for dev in indigo.devices:
            if dev.protocol == indigo.kProtocol.Plugin:
                results.insert(0, (unicode(dev.id), dev.name))
        results = sorted(results, key=lambda tup: tup[1])
        results.insert(0, (0, "Just ask chatbot for response, don't send it"))
        return results

    def validateActionConfigUi(self, values, type_id, device_id):
        """ called by the Indigo UI to validate the values dictionary
        for the Action user interface dialog
        """
        self.debugLog("Action Validation called for %s" % type_id)
        errors = indigo.Dict()

        if "message" not in values or not values["message"]:
            errors["message"] = "Can't reply to an empty message."
        else:
            self.validate_substitution(values, errors, "message")

        if device_id:
            if not values["send_method"]:
                errors["send_method"] = ("See the plugin documentation for the "
                                         "name of the callback method.")
            if not values["message_field"]:
                errors["message_field"] = ("See the plugin documentation for "
                                           "the name of the message field.")
            self.validate_field(values, errors, "1")
            self.validate_field(values, errors, "2")

        if errors:
            return (False, values, errors)
        else:
            return (True, values)

    def validate_substitution(self, values, errors, field):
        """ Run the variable and device substitution syntax check on
        values[field]. If an error is returned, put that in errors[field].
        """
        tup = self.substitute(values[field], validateOnly=True)
        valid = tup[0]
        if not valid:
            errors[field] = tup[1]

    def validate_field(self, values, errors, num):
        """ Eventually we are going to build a dictionary using field names and
        values that the user is supplying to the Action Config dialog. If the
        user enters a field value, but not a name to go with it, lodge a
        complaint.
        """
        if values["fieldvalue" + num]:
            self.validate_substitution(values, errors, "fieldvalue" + num)
            if not values["fieldname" + num]:
                errors["fieldname" + num] = ("See the plugin documentation for "
                                             "the names of the fields it needs "
                                             "to address a message.")

    # ----- Menu Items ----- #

    def toggleDebugging(self):
        """ Called by the Indigo UI for the Toggle Debugging menu item. """
        if self.debug:
            self.debugLog("Turning off debug logging")
        else:
            self.debugLog("Turning on debug logging")
        self.debug = not self.debug
        self.pluginPrefs["showDebugInfo"] = self.debug

    # ----- Action Callbacks ----- #

    def respondToMessage(self, action):
        """ Called by the Indigo Server to implement the respondToMessage
        action defined in Actions.xml.

        Run the chat script and find a response to a message.

        The following should be defined in action.props:
        message: the message to respond to
        device_id: an indigo device id of a plugin-defined device
        send_method: a plugin action defined by the other plugin
        message_field: what the other plugin would like the outgoing message
                       to be called in its action properties dictionary

        The following may be defined in action.props:
        fieldname1: a fieldname the other plugin needs in its action props dict
        fieldvalue1: a value for that field name
        fieldname2: another fieldname the other plugin needs
        fieldvalue2: a value for the second field

        If device_id is 0, the chat script will still be run on the message.
        This is useful if you want to quietly update the state of the chatbot.

        If the chatbot returns an empty reply, nothing will be sent.

        Indigo's device and variable substitution will be used on the
        message before sending it to the chatbot reply engine, and on the
        field values before sending the response to the other plugin.
        """
        message = self.substitute(action.props.get("message", ""),
                                  validateOnly=False)
        if not message:
            self.errorLog("Can't respond to an empty message")
            return

        ra = ReturnAddress(action.props, ["device", "send_method",
                                          "message_field", "fieldname1",
                                          "fieldvalue1", "fieldname2",
                                          "fieldvalue2"])
        if "fieldvalue1" in ra:
            ra["fieldvalue1"] = self.substitute(ra["fieldvalue1"])
        if "fieldvalue2" in ra:
            ra["fieldvalue2"] = self.substitute(ra["fieldvalue2"])

        self.debugLog("Processing message: %s" % message)
        reply = self.bot.reply(ra.freeze(), message)
        self.debugLog("Chatbot response: %s" % reply)

        if reply:
            self.send_response(reply, ra)

    def send_response(self, reply, ra):
        """ Given a return address object that describes an action in another
        plugin and its parameters, construct an action.props dictionary for
        that plugin and ask Indigo to execute the action. Returns silently
        if the device_id in the return address is 0, and returns after logging
        errors if the device doesn't exist, isn't a plugin, or isn't enabled.
        Other errors that come out of Indigo's executeAction method will not
        be caught. """
        device_id = int(ra.get("device", 0))
        if not device_id:
            return
        if (device_id not in indigo.devices or
                indigo.devices[device_id].protocol != indigo.kProtocol.Plugin):
            self.errorLog("Device {0} no longer exists or is not "
                          "plugin-defined, reply cannot be "
                          " sent".format(device_id))
            return
        device = indigo.devices[device_id]
        reply_to = indigo.server.getPlugin(device.pluginId)
        if not reply_to.isEnabled():
            self.errorLog("Plugin {0} not available or enabled, "
                          "reply cannot be sent.".format(device.pluginId))
            return

        send_method = ra["send_method"]
        props = indigo.Dict()
        if "message_field" in ra:
            props[ra["message_field"]] = reply
        if "fieldname1" in ra:
            props[ra["fieldname1"]] = ra["fieldvalue1"]
        if "fieldname2" in ra:
            props[ra["fieldname2"]] = ra["fieldvalue2"]

        reply_to.executeAction(send_method, deviceId=device_id,
                               props=props)


class ReturnAddress(UserDict):
    """ A dictionary object with a few extra methods to make it useful as a
    return address for chatbot replies. Behaves as a defaultdict with the
    default value ""

    Public instance methods:
        freeze() - Returns itself as a frozenset, so it can be used as a key
                   in other dictionaries, as long as you didn't put anything
                   other than hashable values in it.
        indigo_dict() - Returns itself as an indigo.Dict object.
    """
    def __init__(self, props, fields=None):
        """ Construct a ReturnAddress object.
        parameters:
            props - may be either a frozenset containing tuples or some kind
                    of dictionary object.
            fields - optional list of key names. If provided, only items from
                    props with the key or tuple[0] in fields will be placed
                    in the new object.
        """
        UserDict.__init__(self)
        if isinstance(props, frozenset):
            items = [tup for tup in props]
        else:
            items = [tup for tup in props.items()]

        if fields is not None:
            self.data.update(((k, v) for k, v in items
                              if k in fields))
        else:
            self.data.update(items)

    def freeze(self):
        return frozenset(self.data.items())

    def indigo_dict(self):
        return indigo.Dict(self.data)

    def __missing__(self, key):
        return ""
