#! /usr/bin/env python
# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys, os
import unittest
import mock
from unittest import TestCase
from mock import patch, Mock, MagicMock
from threading import Thread

sys.path.append(os.path.abspath('../Chatbot/Contents/Server Plugin'))

class PluginBaseForTest:
    _verbose = False
    
    def __init__(self, pid, name, version, prefs):
        pass
    def __del__(self):
        pass
    def sleep(self):
        pass
    def substitute(self, string, validateOnly=True):
        if validateOnly:
            return (True, string)
        else:
            return string
    def debugLog(self, string):
        print "debugLog"
        if PluginBaseForTest._verbose:
            print string
    def errorLog(self, string):
        if PluginBaseForTest._verbose:
            print string


class DeviceForTest:
    def __init__(self, dev_id, name, props):
        self.id = dev_id
        self.name = name
        self.pluginProps = props
        self.states = {}
    def updateStateOnServer(self, key=None, value=None, clearErrorState=True):
        assert key != None
        assert value != None
        self.states[key] = value
    def replacePluginPropsOnServer(self, props):
        self.props = props

def printstr(s):
    print s
    
class InteractivePlugin(object):
    def __init__(self, path, python=False):
        PluginBaseForTest._verbose = True
        
        self.indigo_mock = Mock()
        self.indigo_mock.PluginBase = PluginBaseForTest
        self.indigo_mock.PluginBase.pluginPrefs = {u"showDebugInfo" : True}
        self.indigo_mock.Dict = Mock(return_value={}.copy())
        self.indigo_mock.variables = MagicMock()
        
        modules = sys.modules.copy()
        modules["indigo"] = self.indigo_mock
        self.module_patcher = patch.dict("sys.modules", modules)
        self.module_patcher.start()
        import plugin

        self.plugin_module = plugin
        self.plugin_module.indigo.PluginBase = PluginBaseForTest
        if path == "":
            path = "./brain"
            
        self.plugin = self.plugin_module.Plugin("What's", "here", "doesn't matter",
                                           {u"showDebugInfo" : True,
                                            u"brainPath": path})

    def __del(self):
        self.module_patcher.stop()
                
    def messageLoop(self):
        action = Mock()
        action.deviceId = None
        action.props = {"send_method":None, "message_field":None}

        while True:
            msg = raw_input("You> ")
            if msg == '/quit':
                return
            action.props[u"message"] = msg
            self.plugin.respondToMessage(action)

        

class PluginTestCase(TestCase):

    def setUp(self):
        self.indigo_mock = Mock()
        self.indigo_mock.PluginBase = PluginBaseForTest
        self.indigo_mock.PluginBase.pluginPrefs = {u"showDebugInfo" : False}
        self.indigo_mock.Dict = Mock(return_value={}.copy())

        modules = sys.modules.copy()
        modules["indigo"] = self.indigo_mock
        self.module_patcher = patch.dict("sys.modules", modules)
        self.module_patcher.start()
        import plugin

        self.plugin_module = plugin
        self.plugin_module.indigo.PluginBase = PluginBaseForTest

        self.plugin = self.new_plugin()
        

    def tearDown(self):
        self.module_patcher.stop()

    def new_plugin(self):
        # Before I created this little function,
        # python was giving me a bizillion "NoneType object has no
        # attribute" warnings, I think because tearDown is called,
        # removing the base class, before the plugin objects are deleted.
        # why this fixed it is a mystery to me
        return self.plugin_module.Plugin("What's", "here", "doesn't matter",
                                           {u"showDebugInfo" : False,
                                            u"brainPath": "./brain"})

    def test_Startup_Succeeds(self):
        self.plugin.startup()
        pass

    def test_Shutdown_Succeeds(self):
        self.plugin.shutdown()
        pass

    def test_Update_Succeeds(self):
        self.plugin.update()
        pass

    def test_RunConcurrentThread_Exits_OnStopThread(self):
        self.plugin.StopThread = Exception
        self.plugin.sleep = Mock(side_effect = Exception("test"))

        t = Thread(target=self.plugin.runConcurrentThread)
        t.start()
        t.join(0.1)
        self.assertFalse(t.is_alive(), "I'm in an infinite loop!")

    def test_DebugMenuItem_Toggles(self):
        self.assertFalse(self.plugin.debug)
        self.plugin.debugLog = Mock()
        
        self.plugin.toggleDebugging()
        self.assertEqual(self.plugin.debugLog.call_count, 1)
        self.assertTrue(self.plugin.debug)

        self.plugin.toggleDebugging()
        self.assertEqual(self.plugin.debugLog.call_count, 2)
        self.assertFalse(self.plugin.debug)
             
    def test_PreferencesUIValidation_Succeeds(self):
        values = {}
        ok, d = self.plugin.validatePrefsConfigUi(values)
        self.assertTrue(ok)

    def test_ActionUIValidation_Succeeds_OnValidInput(self):
        values = {u"message":u"Hi"}
        tup = self.plugin.validateActionConfigUi(values, 0, 0)
        self.assertEqual(len(tup), 2)
        ok, val = tup
        self.assertTrue(ok)

    def test_ActionUIValidation_Fails_OnEmptyMessage(self):
        values = {u"message":""}
        tup = self.plugin.validateActionConfigUi(values, u"respondToMessage", 0)
        self.asserts_for_UIValidation_Failure("message", tup)

    def test_ActionUIValidation_Fails_OnNoMessage(self):
        values = {"":"whatever"}
        tup = self.plugin.validateActionConfigUi(values, u"respondToMessage", 0)
        self.asserts_for_UIValidation_Failure("message", tup)

    def test_ActionUIValidation_Fails_OnMissingCallbackInfo(self):
        values = {"message":"Hi", "device":1}
        tup = self.plugin.validateActionConfigUi(values, u"respondToMessage", 0)
        self.asserts_for_UIValidation_Failure("send_method", tup)
        self.asserts_for_UIValidation_Failure("message_field", tup)
        
    def asserts_for_UIValidation_Failure(self, tag, tup):
        self.assertEqual(len(tup), 3)
        ok, val, errs = tup
        self.assertFalse(ok)
        if tag:
            self.assertTrue(tag in errs)
            self.assertTrue(errs[tag])


if __name__ == "__main__":
    unittest.main()

def interact(path=""):
    ip = InteractivePlugin(path)
    ip.messageLoop()
    

     
    
