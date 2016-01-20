#! /usr/bin/env python
# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import print_function
from __future__ import unicode_literals

import sys

from mock import Mock, MagicMock, patch
from test_plugin import PluginBaseForTest, substitute

class InteractivePlugin(object):
    def __init__(self, path):
        self.indigo_mock = MagicMock()
        self.indigo_mock.PluginBase = PluginBaseForTest
        self.indigo_mock.PluginBase.pluginPrefs = {u"showDebugInfo" : True}
        self.indigo_mock.PluginBase.debugLog = print
        self.indigo_mock.PluginBase.errorLog = print
        self.indigo_mock.PluginBase.sleep = Mock()
        self.indigo_mock.PluginBase.substitute = substitute
        self.indigo_mock.Dict = dict
        self.indigo_mock.variables = MagicMock()
        
        modules = sys.modules.copy()
        modules["indigo"] = self.indigo_mock
        self.module_patcher = patch.dict("sys.modules", modules)
        self.module_patcher.start()
        import plugin

        self.plugin_module = plugin
        if path == "":
            path = "../example_scripts"
        self.path = path
            
        self.plugin = self.plugin_module.Plugin("What's", "here", "doesn't matter",
                                           {u"showDebugInfo" : True,
                                            u"scriptsPath": path})
        self.plugin.startup()

    def __del(self):
        self.module_patcher.stop()
                
    def messageLoop(self):
        action = Mock()
        action.deviceId = None
        action.props = {"send_method":None, "message_field":None}

        while True:
            msg = raw_input("You> ")
            if msg == "/quit":
                break
            elif msg == "/botvars":
                print(unicode(self.plugin.bot._botvars))
            elif msg == "/uservars":
                if "local" in self.plugin.bot._users:
                    print(unicode(self.plugin.bot._users["local"].vars))
                else:
                    print("No user variables have been defined.")
            elif msg == "/reload":
                self.plugin.bot.clear_rules()
                self.plugin.bot.load_script_directory(self.path)
            elif msg == "/debug":
                if self.plugin.bot._botvars["debug"] == "True":
                    self.plugin.bot._botvars["debug"] = "False"
                else:
                    self.plugin.bot._botvars["debug"] = "True"
            else:
                action.props[u"message"] = unicode(msg)
                self.plugin.respondToMessage(action)


def interact(path=""):
    ip = InteractivePlugin(path)
    ip.messageLoop()
    

