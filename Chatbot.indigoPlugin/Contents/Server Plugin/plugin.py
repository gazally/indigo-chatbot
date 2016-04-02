#! /usr/bin/env python
# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Chatbot plugin for IndigoServer"""
from __future__ import print_function
from __future__ import unicode_literals

from distutils.version import StrictVersion
import logging
import traceback
import indigo

from chatbot_reply import ChatbotEngine, NoRulesFoundError
from termapp_server import start_interaction_thread, start_shell_thread

_VERSION = "0.3.0"
_SENDER_INFO_FIELDS = ["info1", "info2", "info3"]

log = logging.getLogger(__name__)


class Plugin(indigo.PluginBase):
    """Chatbot plugin class for IndigoServer"""

    # ----- plugin framework ----- #

    def __init__(self, plugin_id, display_name, version, prefs):
        indigo.PluginBase.__init__(self, plugin_id, display_name,
                                   version, prefs)
        self.debug = prefs.get("showDebugInfo", False)
        self.debug_engine = prefs.get("showEngineDebugInfo", False)
        self.configure_logging()

        if (StrictVersion(prefs.get("configVersion", "0.0")) <
                StrictVersion(version)):
            log.debug("Updating config version to " + version)
            prefs["configVersion"] = version
        self.device_info = {}

    def startup(self):
        log.debug("Startup called")
        self.bot = ChatbotEngine()

        scripts_directory = self.pluginPrefs.get("scriptsPath", "")
        if scripts_directory:
            self.load_scripts(scripts_directory)
        else:
            log.debug("Chatbot plugin is not configured.")

    def shutdown(self):
        log.debug("Shutdown called")
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

    # ----- Logging Configuration ----- #

    def configure_logging(self):
        """ Set up the logging for this module and chatbot_reply. """
        self.configure_logger(log)
        self.configure_logger(logging.getLogger("chatbot_reply"),
                              prefix="Engine")
        self.configure_logger(logging.getLogger("termapp_server"),
                              prefix="Console")
        self.set_chatbot_logging()

    def configure_logger(self, logger, level=logging.DEBUG, prefix="",
                         propagate=False):
        """ Create a Handler subclass for the logging module that uses the
        logging methods supplied to the plugin by Indigo. Use it for both
        the plugin and the chatbot_reply module, and add a little formatting
        to chatbot_reply's logger to distinguish the two in the log.
        """
        def make_handler(debugLog, errorLog, prefix=""):
            class NewHandler(logging.Handler):
                def emit(self, record):
                    try:
                        msg = self.format(record)
                        if record.levelno < logging.WARNING:
                            debugLog(msg)
                        else:
                            errorLog(msg)
                    except Exception:
                        self.handleError(record)
            handler = NewHandler()
            if prefix:
                prefix = "[" + prefix + "]"
            handler.setFormatter(logging.Formatter(prefix + "%(message)s"))
            return handler

        logger.addHandler(make_handler(self.debugLog, self.errorLog,
                                       prefix))
        logger.setLevel(level)
        if propagate is not None:
            logger.propagate = propagate

    def set_chatbot_logging(self):
        """ Set the logging level for the chatbot_reply module's logger """
        chatbot_logger = logging.getLogger("chatbot_reply")
        if self.debug_engine:
            chatbot_logger.setLevel(logging.DEBUG)
        else:
            chatbot_logger.setLevel(logging.WARNING)

    # ----- Preferences UI ----- #

    def validatePrefsConfigUi(self, values):
        """ called by the Indigo UI to validate the values dictionary for
        the Plugin Preferences user interface dialog
        """
        errors = indigo.Dict()
        log.debug("Preferences Validation called")
        debug = values.get("showDebugInfo", False)
        if self.debug:
            if not debug:
                log.debug("Turning off debug logging")
        self.debug = debug
        log.debug("Debug logging is on")  # won't print if not self.debug

        self.debug_engine = values.get("showEngineDebugInfo", False)
        self.set_chatbot_logging()

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
            log.error("", exc_info=True)
            message = ("Unable to read script files from directory "
                       "'{0}'".format(scripts_directory))
        except NoRulesFoundError as e:
            message = unicode(e)
        except Exception:
            log.error("", exc_info=True)
            message = "Error reading script files"

        if message:
            log.error(message)
        if errors is not None:
            if message:
                errors[key] = message

    # ----- Action Configuration UI ----- #

    def validateActionConfigUi(self, values, type_id, device_id):
        """ called by the Indigo UI to validate the values dictionary
        for the Action user interface dialog
        """
        log.debug("Action Validation called for %s" % type_id)
        errors = indigo.Dict()

        if StrictVersion(values["actionVersion"]) < StrictVersion(_VERSION):
            values["actionVersion"] = _VERSION

        if not values["message"]:
            errors["message"] = "Can't reply to an empty message."

        if not values["name"]:
            errors["name"] = "Name of the message sender is required."

        fields = ["message", "name"]
        fields.extend(_SENDER_INFO_FIELDS)
        self.validate_substitution(values, errors, fields)

        if errors:
            return (False, values, errors)
        else:
            return (True, values)

    def validate_substitution(self, values, errors, keys):
        """ Run the variable and device substitution syntax check on
        values[key]. If an error is returned, put that in errors[key].
        """
        for key in keys:
            tup = self.substitute(values[key], validateOnly=True)
            valid = tup[0]
            if not valid:
                errors[key] = tup[1]

    # ----- Menu Items ----- #

    def toggleDebugging(self):
        """ Called by the Indigo UI for the Toggle Debugging menu item. """
        if self.debug:
            log.debug("Turning off debug logging")
        self.debug = not self.debug
        log.debug("Turning on debug logging")  # won't print if !self.debug
        self.pluginPrefs["showDebugInfo"] = self.debug

    def toggleEngineDebugging(self):
        """ Called by the Indigo UI for the Toggle Chatbot Engine
        Debugging menu item.
        """
        if self.debug_engine:
            log.debug("Turning off chatbot engine debug logging")
        else:
            log.debug("Turning on chatbot engine debug logging")
        self.debug_engine = not self.debug_engine
        self.pluginPrefs["showEngineDebugInfo"] = self.debug_engine
        self.set_chatbot_logging()

    def reloadScripts(self):
        """ Called by the Indigo UI for the Reload Script Files menu item. """
        scripts_directory = self.pluginPrefs.get("scriptsPath", "")
        if scripts_directory:
            self.load_scripts(scripts_directory)
        else:
            log.error("Can't load script files because the scripts "
                      "directory has not been set. See the Chatbot "
                      "Configure dialog.")

    def startInteractiveInterpreter(self):
        """ Called by the Indigo UI for the Start Interactive Interpreter
        menu item.
        """
        log.debug("startInteractiveInterpreter called")
        namespace = globals().copy()
        namespace.update(locals())
        start_shell_thread(namespace, "", "Chatbot Plugin")

    def startInteractiveChat(self):
        """ Called by the Indigo UI for the Start Interactive Chat
        menu item.
        """
        log.debug("startInteractiveChat called")
        start_interaction_thread(Chatter(self.bot).push,
                                 Chatter.helpmessage, "Chat")

    # ----- Device Start and Stop methods  ----- #

    def deviceStartComm(self, device):
        """Called by Indigo Server to tell a device to start working.
        Initialize the device's message backlog to empty.

        """
        props = device.pluginProps
        if "deviceVersion" not in props:
            props["deviceVersion"] = _VERSION
            device.replacePluginPropsOnServer(props)

        log.debug("Starting device {0}".format(device.id))
        self.device_info[device.id] = []
        self.clear_device_state(device)

    def clear_device_state(self, device):
        device.updateStateOnServer("message", "")
        device.updateStateOnServer("response", "")
        device.updateStateOnServer("name", "")
        for k in _SENDER_INFO_FIELDS:
            device.updateStateOnServer(k, "")
        device.updateStateOnServer("status", "Idle")

    def deviceStopComm(self, device):
        """ Called by Indigo Server to tell us it's done with a device.
        """
        log.debug("Stopping device: {0}".format(device.id))
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
        name: name of the sender
        info1, info2, info3: some information about the
            sender that the user wants to save

        Indigo's device and variable substitution will be used on the
        message before sending it to the chatbot reply engine, and on the
        sender_info values before saving them.
        """
        message = self.substitute(action.props.get("message", ""),
                                  validateOnly=False)
        name = self.substitute(action.props.get("name", ""),
                               validateOnly=False)
        if not message:
            log.error("Can't respond to an empty message")
            return
        if ("actionVersion" in action.props and
                StrictVersion(action.props["actionVersion"]) <
                StrictVersion("0.2.0")):
            log.error("Action was configured by a previous version of this "
                      "plugin. Please check and save the Action Settings.")
            return

        sender_info = dict([(k, self.substitute(action.props.get(k, "")))
                            for k in _SENDER_INFO_FIELDS])
        sender_info["device_id"] = action.deviceId
        sender_info["name"] = name

        device = indigo.devices[action.deviceId]
        if device.states["status"] == "Idle":
            self.device_respond(device, message, sender_info)
        else:
            self.device_info[action.deviceId].append((message, sender_info))

    def device_respond(self, device, message, sender_info):
        """ Ask the chatbot for a response to a message. If it returns a
        non-empty reply, set the device to Ready with the response and
        sender info. If it returns an empty reply, clear the device state.
        If it raises an error, also clear the device and clear the device's
        backlog too, and then re-raise.
        """
        device.updateStateOnServer("message", message)
        device.updateStateOnServer("response", "")
        device.updateStateOnServer("name", sender_info["name"])
        for k in _SENDER_INFO_FIELDS:
            device.updateStateOnServer(k, sender_info[k])
        device.updateStateOnServer("status", "Processing")

        try:
            log.debug("Processing message: '{0}' From user {1}".format(
                message, sender_info["name"]))
            reply = self.bot.reply(sender_info["name"], sender_info, message)
            log.debug("Chatbot response: '{0}'".format(reply))
        except Exception:
            # kill any backlog, so as not to add to the confusion
            del self.device_info[device.id][:]
            self.clear_device_state(device)
            raise

        if reply:
            device.updateStateOnServer("response", reply)
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


class Chatter(object):
    helpmessage = ("Use /name to tell me who you are or "
                   "/names to see who I know already")

    def __init__(self, bot):
        self.bot = bot
        self.name = None

    def push(self, message):
        if message.startswith("/"):
            self.do_command(message)
        elif self.name is None:
            print(self.helpmessage)
        else:
            print("Reply:  " + self.bot.reply(self.name, {"name": self.name},
                                              message))
        return False

    def do_command(self, message):
        words = message.split()
        usernames = self.bot._users.keys()
        if words[0] == "/names":
            print("Here are the people I know: " + ", ".join(usernames))
        elif words[0] == "/name" or words[0] == "/new":
            if len(words) == 1:
                print("Please follow {0} with your name or use /names "
                      "and I will tell you who I know already".format(
                          words[0]))
            else:
                name = " ".join(words[1:])
                if name in usernames:
                    self.name = name
                    print("Hello {0}!".format(name))
                    print("Here is what I know about you:")
                    for k, v in self.bot._users[name].info.items():
                        print("    {0}: {1}".format(k, v))
                elif words[0] == "/name":
                    print("I don't know you. Please use /new followed by "
                          "your name to introduce yourself")
                else:
                    self.name = name
                    print("Nice to meet you, {0}!".format(name))
        else:
            print(self.helpmessage)
