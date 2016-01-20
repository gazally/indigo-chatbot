#! /usr/bin/env python
# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Chatbot plugin for IndigoServer"""
from __future__ import unicode_literals

from distutils.version import StrictVersion
from UserDict import UserDict
import traceback

import indigo

from chatbot_reply import ChatbotEngine, NoRulesFoundError

_VERSION = "0.2"
_SENDER_INFO_FIELDS = ["info1", "info2", "info3"]


# TODO - menu command to relaunch the bot, be able to do this from within the
#        bot
# TODO - save and restore bot variables
# TODO - define bot administrator
# TODO - pass enough user info into the bot that it could asynchronously reply,
#        basically the entire props dict in getChatbotResponse packed into a
#        hashable tuple, and some way to make it easy for scripters to do that
#        Or have them queue it up and put it in runConcurrentThread???
# TODO - configuration setting for typing speed delay: Computer/Teenager/Adult
#        (0/1/5)


class Plugin(indigo.PluginBase):
    """Chatbot plugin class for IndigoServer"""

    # ----- plugin framework ----- #

    def __init__(self, plugin_id, display_name, version, prefs):
        indigo.PluginBase.__init__(self, plugin_id, display_name,
                                   version, prefs)
        self.debug = prefs.get("showDebugInfo", False)
        self.debug_engine = prefs.get("showEngineDebugInfo", False)

        if (StrictVersion(prefs.get("configVersion", "0.0")) <
                StrictVersion(version)):
            self.debugLog("Updating config version to " + version)
            prefs["configVersion"] = version
        self.device_info = {}

    def startup(self):
        self.debugLog("Startup called")
        self.bot = ChatbotEngine(self.debug_engine,
                                 debuglogger=self.debugLog,
                                 errorlogger=self.errorLog)

        scripts_directory = self.pluginPrefs.get("scriptsPath", "")
        if scripts_directory:
            self.load_scripts(scripts_directory)
        else:
            self.errorLog("Chatbot plugin is not configured.")

    def shutdown(self):
        self.debugLog("Shutdown called")
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
        errors = indigo.Dict()
        self.debugLog("Preferences Validation called")
        debug = values.get("showDebugInfo", False)
        if self.debug:
            if not debug:
                self.debugLog("Turning off debug logging")
        self.debug = debug
        self.debugLog("Debug logging is on")  # won't print if not self.debug

        self.debug_engine = values.get("showEngineDebugInfo", False)
        self.bot._botvars["debug"] = unicode(self.debug_engine)

        scripts_directory = values.get("scriptsPath", "")
        if not scripts_directory:
            errors["scriptsPath"] = "Directory of script files is required."
        elif scripts_directory != self.pluginPrefs.get("scriptsPath", ""):
            self.load_scripts(scripts_directory, errors, "scriptsPath")
        if errors:
            return (False, values, errors)
        else:
            return(True, values)

    def load_scripts(self, scripts_directory, errors=None, key=None):
        """ Call the chatbot engine to load scripts, catch all exceptions
        and send them to the error log or error dictionary if provided.
        """
        message = ""
        try:
            self.bot.clear_rules()
            self.bot.load_script_directory(scripts_directory)
        except OSError as e:
            self.errorLog(unicode(e))
            message = ("Unable to read script files from directory "
                       "'{0}'".format(scripts_directory))
        except NoRulesFoundError as e:
            message = unicode(e)
        except Exception:
            self.errorLog(traceback.format_exc())
            message = "Error reading script files"

        if message:
            self.errorLog(message)
        if errors is not None:
            if message:
                errors[key] = message

    # ----- Action Configuration UI ----- #

    def validateActionConfigUi(self, values, type_id, device_id):
        """ called by the Indigo UI to validate the values dictionary
        for the Action user interface dialog
        """
        self.debugLog("Action Validation called for %s" % type_id)
        errors = indigo.Dict()

        if StrictVersion(values["actionVersion"]) < StrictVersion(_VERSION):
            values["actionVersion"] = _VERSION

        if not values["message"]:
            errors["message"] = "Can't reply to an empty message."
        else:
            self.validate_substitution(values, errors, "message")
            for k in _SENDER_INFO_FIELDS:
                self.validate_substitution(values, errors, k)

        if errors:
            return (False, values, errors)
        else:
            return (True, values)

    def validate_substitution(self, values, errors, key):
        """ Run the variable and device substitution syntax check on
        values[field]. If an error is returned, put that in errors[key].
        """
        tup = self.substitute(values[key], validateOnly=True)
        valid = tup[0]
        if not valid:
            errors[key] = tup[1]


    # ----- Menu Items ----- #

    def toggleDebugging(self):
        """ Called by the Indigo UI for the Toggle Debugging menu item. """
        if self.debug:
            self.debugLog("Turning off debug logging")
        else:
            self.debugLog("Turning on debug logging")
        self.debug = not self.debug
        self.pluginPrefs["showDebugInfo"] = self.debug

    def toggleEngineDebugging(self):
        """ Called by the Indigo UI for the Toggle Chatbot Engine 
        Debugging menu item. 
        """
        if self.debug_engine:
            self.debugLog("Turning off chatbot engine debug logging")
        else:
            self.debugLog("Turning on chatbot engine debug logging")
        self.debug_engine = not self.debug_engine
        self.pluginPrefs["showEngineDebugInfo"] = self.debug_engine
        self.bot._botvars["debug"] = unicode(self.debug_engine)

    def reloadScripts(self):
        """ Called by the Indigo UI for the Reload Script Files menu item. """
        scripts_directory = self.pluginPrefs.get("scriptsPath", "")
        if scripts_directory:
            self.load_scripts(scripts_directory)
        else:
            self.errorLog("Can't load script files because the scripts "
                          "directory has not been set. See the Chatbot "
                          "Configure dialog.")
        

    # ----- Device Start and Stop methods  ----- #

    def deviceStartComm(self, device):
        """Called by Indigo Server to tell a device to start working.
        Initialize the device's message backlog to empty.

        """
        props = device.pluginProps
        if "deviceVersion" not in props:
            props["deviceVersion"] = _VERSION
            device.replacePluginPropsOnServer(props)

        self.debugLog("Starting device {0}".format(device.id))
        self.device_info[device.id] = []
        self.clear_device_state(device)

    def clear_device_state(self, device):
        device.updateStateOnServer("message", "")
        device.updateStateOnServer("response", "")
        for k in _SENDER_INFO_FIELDS:
            device.updateStateOnServer(k, "")
        device.updateStateOnServer("status", "Idle")

    def deviceStopComm(self, device):
        """ Called by Indigo Server to tell us it's done with a device.
        """
        self.debugLog("Stopping device: {0}".format(device.id))
        self.device_info.pop(device.id, None)

    # ----- Action Callbacks ----- #

    def getChatbotResponse(self, action):
        """ Called by the Indigo Server to implement the respondToMessage
        action defined in Actions.xml.

        If the device is busy, which means there is an uncleared response,
        put the message and sender info in the backlog.

        Otherwise, run the chat script and find a response to a message and
        set the device state to Ready with all sender info.

        The following should be defined in action.props:
        message: the message to respond to
        sender_info1, sender_info2, sender_info3: some information about the
            sender that the user wants to save

        Indigo's device and variable substitution will be used on the
        message before sending it to the chatbot reply engine, and on the
        sender_info values before saving them.
        """
        message = self.substitute(action.props.get("message", ""),
                                  validateOnly=False)
        if not message:
            self.errorLog("Can't respond to an empty message")
            return
        if (StrictVersion(action.props.get("actionVersion", "0.0")) <
             StrictVersion(_VERSION)):
            self.errorLog("Action is from a previous version of this plugin. "
                          "Please check and save the Action Settings.")
            return

        device = indigo.devices[action.deviceId]
        sender_info = dict([(k, self.substitute(action.props.get(k, "")))
                            for k in _SENDER_INFO_FIELDS])

        if device.states["status"] == "Idle":
            self.device_respond(device, message, sender_info)
        else:
            self.device_info[action.deviceId].append((message, sender_info))

    def device_respond(self, device, message, sender_info):
        device.updateStateOnServer("status", "Processing")

        info = {"device_id": device.id}
        info.update(sender_info)
        user = ReturnAddress(info=info).freeze()
        try:
            self.debugLog("Processing message: '{0}' From user {1}".format(
                message, user))
            reply = self.bot.reply(user, message)
            self.debugLog("Chatbot response: '{0}'".format(reply))
        except Exception:
            # kill any backlog, so as not to add to the confusion
            device.updateStateOnServer("status", "Idle")
            del self.device_info[device.id][:]
            raise

        if reply:
            device.updateStateOnServer("message", message)
            device.updateStateOnServer("response", reply)
            for k in _SENDER_INFO_FIELDS:
                device.updateStateOnServer(k, sender_info[k])
            device.updateStateOnServer("status", "Ready")
        else:
            self.clear_device_state(device)

    def clearResponse(self, action):
        """Called by Indigo Server to implement clearResponse action in
        Actions.xml. Only uses action.deviceId, not props. If there are
        waiting messages to process, get responses for them from the chatbot.
        Empty replies are ignored.

        """
        device = indigo.devices[action.deviceId]
        status = device.states["status"]
        if status != "Idle":
            device.updateStateOnServer("status", "Idle")

        backlog = self.device_info.get(action.deviceId, None)
        while backlog:
            message, sender_info = backlog.pop(0)
            self.device_respond(device, message, sender_info)
            device.refreshFromServer()
            if device.states["status"] == "Ready":
                return
        self.clear_device_state(device)


class ReturnAddress(object):
    """ A return address for chatbot replies.

    Public instance methods:
        freeze() - Returns itself as a frozenset, so it can be used as a key
                   in dictionaries, as long as you didn't put anything
                   other than hashable values in the info dictionary
                   passed to the constructor

    Public instance variables:
        info - dictionary
    """
    def __init__(self, **kwargs):
        """ Construct a ReturnAddress object.
        named parameters:
            info - a dictionary of information identifying the user
            frozen - a frozen ReturnAddress object to be thawed

        You must supply either frozen or info, but not both, or an error
        will be raised.
        """
        if "frozen" in kwargs:
            items = [x for x in kwargs.pop("frozen")]
            self.info = dict([tup for tup in items])
        elif "info" in kwargs:
            self.info = kwargs.pop("info")
        else:
            raise(TypeError, "One argument is required")
        if kwargs:
            raise(TypeError, "Unexpected keyword argument")

    def freeze(self):
        return frozenset(self.info.items())
