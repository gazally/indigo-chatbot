#! /usr/bin/env python
# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Chatbot plugin for IndigoServer"""

import indigo
import sys

from pycharge import ChatbotEngine

# TODO - menu command to relaunch the bot, be able to do this from within the bot
# TODO - save and restore bot variables
# TODO - define bot administrator
# TODO - have the preferences validation try to load the script files and report
#        errors then
# TODO - PrefsConfigUI(self, whatever, False) means user didn't cancel.
#        Before that scripts directory might not be set up, need to handle that gracefully
#        Also, Prefs is maybe the logical place to put a button to reload the bot files
# TODO - default for scro[ts path can be set up by getPrefsConfigUiValues,
#       indigo.server.getDbFilePath() minus the filename on the end might be a good
#       choice
# TODO - Action configuration UI. Give the user a list of devices to choose from.
#        Tell them what plugin to read the docs of?
# TODO - configuration setting for typing speed delay: Computer/Teenager/Adult (0/1/5)


class Plugin(indigo.PluginBase):
    """Chatbot plugin class for IndigoServer"""

    ##### plugin framework ######
    def __init__(self, plugin_id, display_name, version, prefs):
        indigo.PluginBase.__init__(self, plugin_id, display_name,
                                   version, prefs)
        self.debug = prefs.get(u"showDebugInfo", False)
        self.bot = ChatbotEngine(self.debug, self.debugLog, self.errorLog)

        scripts_directory = prefs.get(u"scriptsPath", "")
        self.bot.load_scripts(scripts_directory)

    def __del__(self):
        indigo.PluginBase.__del__(self)

    def startup(self):
        pass
        
    def shutdown(self):
        pass

    def update(self):
        pass
       
    def runConcurrentThread(self):
        try:
            while True:
                self.update()
                self.sleep(3600) # seconds
        except self.StopThread:
             pass

    ###### Preferences UI ######

    def validatePrefsConfigUi(self, values):
        """ called by the Indigo UI to validate the values dictionary for
        the Plugin Preferences user interface dialog
        """
        self.debugLog(u"Preferences Validation called")
        debug = values.get("showDebugInfo", False)
        if self.debug:
            if not debug:
                self.debugLog("Turning off debug logging")
        self.debug = debug
        self.debugLog("Debug logging is on") #won't print if self.debug is False
            
        return(True, values)
        return(True, values)

    ##### Action Configuration UI ######

    def validateActionConfigUi(self, values, type_id, device_id):
        """ called by the Indigo UI to validate the values dictionary
        for the Action user interface dialog
        """
        self.debugLog(u"Action Validation called for %s" % type_id)
        errors = indigo.Dict()

        if type_id == u"respondToMessage":
            if values.get(u"message", "") == "":
                errors[u"message"] = u"Can't respond to an empty message"
            else:
                tup = self.substitute(values[u"message"], validateOnly=True)
                if not tup[0]:
                    errors["message"] = tup[1]
            if values.get(u"device", 0) != 0:
                if values.get(u"send_method", "") == "":
                    errors[u"send_method"] = (
                        u"See the plugin documentation for the name of the "
                        u"callback method.")
                if values.get(u"message_field", "") == "":
                    errors[u"message_field"] = (
                        u"See the plugin documentation for the field name.")
                    
        if errors:
            return (False, values, errors)
        else:
            return (True, values)

    ###### Menu Items ######
    
    def toggleDebugging(self):
        
        """ Called by the Indigo UI for the Toggle Debugging menu item.
        """
	if self.debug:
            self.debugLog(u"Turning off debug logging")
	else:
            self.debugLog(u"Turning on debug logging")
	self.debug = not self.debug
        self.pluginPrefs[u"showDebugInfo"] = self.debug
 
    ###### Action Callbacks ######

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

        If device_id is 0, the chat script will still be run on the message.
        This is useful if you want to quietly update the state of the chatbot.

        Indigo's device and variable substitution will be used on the 
        message before sending it to the chatbot reply engine.
        """
        message = self.substitute(action.props.get(u"message", ""),
                                  validateOnly=False)
        if not message:
            self.debugLog("RespondToMessage can't respond to empty message")
            return
        
        device_id = int(action.props.get(u"device", 0))
        send_method = action.props.get(u"send_method", "")
        message_field = action.props.get(u"message_field", "")
        if device_id and not (send_method and message_field):
            self.debugLog("RespondToMessage Action is not configured")
            return

        self.debugLog(u"Processing message: %s" % message)
        reply = self.bot.reply(str(device_id), message)
        self.debugLog(u"Chatbot response: %s" % reply)
        
        reply_to = None
        if device_id and device_id in indigo.devices:
            device = indigo.devices[device_id]
            if device.protocol == indigo.kProtocol.Plugin:
                reply_to = indigo.server.getPlugin(device.pluginId)
        
        if reply_to is not None and reply_to.isEnabled():
            reply_to.executeAction(send_method, deviceId=device_id,
                                       props={message_field:reply})

        
