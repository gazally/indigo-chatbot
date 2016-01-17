#! /usr/bin/env python
# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import print_function
from __future__ import unicode_literals

import sys, os
import unittest

import mock

from unittest import TestCase
from mock import patch, Mock, MagicMock
from threading import Thread

sys.path.append(os.path.abspath('../Chatbot.indigoPlugin/Contents/Server Plugin'))

class PluginBaseForTest(object):
    def __init__(self, pid, name, version, prefs):
        self.pluginPrefs = prefs

    
def substitute(self, string, validateOnly=True):
    if validateOnly:
        return (True, string)
    else:
        return string

        
class PluginTestCase(TestCase):
    def setUp(self):
        self.indigo_mock = MagicMock()
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
        
        PluginBaseForTest.debugLog = Mock()
        PluginBaseForTest.errorLog = Mock()
        PluginBaseForTest.sleep = Mock()
        PluginBaseForTest.substitute = substitute

        self.plugin = self.new_plugin()

        self.assertFalse(PluginBaseForTest.errorLog.called)

    def tearDown(self):
        self.module_patcher.stop()

    def new_plugin(self, path="./test_scripts"):
        # Before I created this little function,
        # python was giving me a bizillion "NoneType object has no
        # attribute" warnings, I think because tearDown is called,
        # removing the base class, before the plugin objects are deleted.
        # why this fixed it is a mystery to me
        props = {u"showDebugInfo" : False,
                 u"scriptsPath": path}
        plugin = self.plugin_module.Plugin("What's", "here", "doesn't matter",
                                         props)
        plugin.startup()
        return plugin

    def test_Startup_LogsError_OnNonexistantLoadPath(self):
        self.new_plugin(path="./doesnt_exist")
        self.assertTrue(PluginBaseForTest.errorLog.called)

    def test_Startup_LogsError_OnEmptyLoadPath(self):
        self.new_plugin(path="./empty_directory")
        self.assertTrue(PluginBaseForTest.errorLog.called)

    def test_Startup_LogsError_OnBadPyFileInLoadPath(self):
        self.new_plugin(path="./syntax_error")
        self.assertTrue(PluginBaseForTest.errorLog.called)

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
        values = {"showDebugInfo" : True}
        ok, d = self.plugin.validatePrefsConfigUi(values)
        self.assertTrue(ok)
        values = {"showDebugInfo" : False}
        ok, d = self.plugin.validatePrefsConfigUi(values)
        self.assertTrue(ok)

    def test_deviceListGenerator_Succeeds_OnValidInput(self):
        dev = Mock()
        dev.id = 1
        dev.name = "dev"
        dev.protocol = self.indigo_mock.kProtocol.Plugin = "foo"
        self.indigo_mock.devices = [dev]
        results = self.plugin.deviceListGenerator()
        self.assertEqual(len(results), 2)

    def test_ActionUIValidation_Succeeds_OnValidInput(self):
        values = {u"message":u"Hi", "send_method":"send",
                  "message_field":"msg", "fieldvalue1":"",
                  "fieldname1":"", "fieldname2":"",
                  "fieldvalue2":""}
        tup = self.plugin.validateActionConfigUi(values, "", 1)
        self.assertEqual(len(tup), 2)
        ok, val = tup
        self.assertTrue(ok)

    def test_ActionUIValidation_Fails_OnEmptyMessage(self):
        values = {u"message":u"", "send_method":"send",
                  "message_field":"mess", "fieldvalue1":"fv1",
                  "fieldname1":"fn1", "fieldname2":"fn2",
                  "fieldvalue2":"fv2"}
        tup = self.plugin.validateActionConfigUi(values, u"respondToMessage", 1)
        self.asserts_for_UIValidation_Failure("message", tup)

    def test_ActionUIValidation_Fails_OnNoMessage(self):
        values = {u"send_method":"send",
                  "message_field":"mess", "fieldvalue1":"fv1",
                  "fieldname1":"fn1", "fieldname2":"fn2",
                  "fieldvalue2":"fv2"}
        tup = self.plugin.validateActionConfigUi(values, u"respondToMessage", 1)
        self.asserts_for_UIValidation_Failure("message", tup)

    def test_ActionUIValidation_Fails_OnMissingCallbackInfo(self):
        values = {u"message":u"Hi", "send_method":"",
                  "message_field":"", "fieldvalue1":"fv1",
                  "fieldname1":"fn1", "fieldname2":"fn2",
                  "fieldvalue2":"fv2"}
        tup = self.plugin.validateActionConfigUi(values, u"respondToMessage", 1)
        self.asserts_for_UIValidation_Failure("send_method", tup)
        self.asserts_for_UIValidation_Failure("message_field", tup)

    def test_ActionUIValidation_Fails_OnMissingFieldName(self):
        values = {u"message":u"Hi", "send_method":"",
                  "message_field":"", "fieldvalue1":"fv1",
                  "fieldname1":"fn1", "fieldname2":"",
                  "fieldvalue2":"fv2"}
        tup = self.plugin.validateActionConfigUi(values, u"respondToMessage", 1)
        self.asserts_for_UIValidation_Failure("fieldname2", tup)

    def test_ActionUIValidation_Fails_OnFailedSubstitutionCheck(self):
        values = {u"message":u"Hi", "send_method":"send",
                  "message_field":"mess", "fieldvalue1":"fv1",
                  "fieldname1":"fn1", "fieldname2":"fn2",
                  "fieldvalue2":"fv2"}
        fail_on = ""
        def sub(self, string, validateOnly):
            if validateOnly:
                return (string != values[fail_on], string)
        PluginBaseForTest.substitute = sub
        fail_on = "message"
        tup = self.plugin.validateActionConfigUi(values, u"respondToMessage", 1)
        self.asserts_for_UIValidation_Failure("message", tup)

        fail_on = "fieldvalue2"
        tup = self.plugin.validateActionConfigUi(values, u"respondToMessage", 1)
        self.asserts_for_UIValidation_Failure("fieldvalue2", tup)

    def test_respond_LogsError_OnEmptyMessage(self):
        action = Mock()
        action.props = {"message":""}
        self.plugin.respondToMessage(action)
        self.assertTrue(PluginBaseForTest.errorLog.called)

    def test_respond_LogsError_OnUnconfiguredAction(self):
        action = Mock()
        action.props = {"message": "test", "device": 1}
        self.plugin.respondToMessage(action)
        self.assertTrue(PluginBaseForTest.errorLog.called)        

    def test_respond_Succeeds_WithNoReturnAddress(self):
        action = Mock()
        action.props = {"message": "test", "device": 0}
        self.plugin.respondToMessage(action)

    def test_respond_Succeeds_OnValidInput(self):
        action = Mock()
        action.props = {"message": "test", "message_field":"m",
                        "device" : 1, "send_method": "send",
                        "fieldname1": "f1", "fieldvalue1":"v1",
                        "fieldname2": "f2", "fieldvalue2":"v2"}
        m = Mock()
        m.protocol = self.indigo_mock.kProtocol.Plugin = "protocol"
        m.isEnabled.return_value = True
        self.indigo_mock.devices.__contains__.return_value = True
        self.indigo_mock.devices.__getitem__.return_value = m
        self.indigo_mock.server.getPlugin.return_value = m
        self.plugin.respondToMessage(action)

    def asserts_for_UIValidation_Failure(self, tag, tup):
        self.assertEqual(len(tup), 3)
        ok, val, errs = tup
        self.assertFalse(ok)
        if tag:
            self.assertTrue(tag in errs)
            self.assertTrue(errs[tag])


if __name__ == "__main__":
    unittest.main()
