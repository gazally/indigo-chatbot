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

_VERSION = "0.2"

sys.path.append(os.path.abspath('../Chatbot.indigoPlugin/Contents/Server Plugin'))

class PluginBaseForTest(object):
    def __init__(self, pid, name, version, prefs):
        self.pluginPrefs = prefs

def substitute(self, string, validateOnly=False):
    if validateOnly:
        return (True, string)
    else:
        return string

class DeviceForTest(object):
    """ Mockup of indigo.device, for testing """
    def __init__(self, dev_id, name, props):
        self.id = dev_id
        self.name = name
        self.pluginProps = props
        self.states = {}
        self.configured = True
    def updateStateOnServer(self, key=None, value=None, clearErrorState=True):
        assert key is not None
        assert value is not None
        self.states[key] = value
    def replacePluginPropsOnServer(self, props):
        self.pluginProps = props
    def refreshFromServer(self):
        pass

        
class IndigoMockTestCase(TestCase):
    """ Mock indigo so the plugin can be imported """
    def setUp(self):
        self.indigo_mock = MagicMock()
        self.indigo_mock.Dict = dict
        self.indigo_mock.PluginBase = PluginBaseForTest
        self.indigo_mock.devices = {}

        modules = sys.modules.copy()
        modules["indigo"] = self.indigo_mock
        self.module_patcher = patch.dict("sys.modules", modules)
        self.module_patcher.start()
        import plugin
        self.plugin_module = plugin
        self.plugin_module.indigo.PluginBase = PluginBaseForTest

    def tearDown(self):
        self.module_patcher.stop()
        
class PluginTestCase(IndigoMockTestCase):
    def setUp(self):
        IndigoMockTestCase.setUp(self)
        PluginBaseForTest.pluginPrefs = {u"showDebugInfo" : False}
        PluginBaseForTest.debugLog = Mock()
        PluginBaseForTest.errorLog = Mock(side_effect=Exception("test"))
        PluginBaseForTest.sleep = Mock()
        PluginBaseForTest.substitute = substitute

        self.plugin = self.new_plugin()
        self.assertFalse(PluginBaseForTest.errorLog.called)

    def tearDown(self):
        IndigoMockTestCase.tearDown(self)

    def new_plugin(self, path="./test_scripts"):
        # Before I created this little function,
        # python was giving me a bizillion "NoneType object has no
        # attribute" warnings, I think because tearDown is called,
        # removing the base class, before the plugin objects are deleted.
        # why this fixed it is a mystery to me
        props = {"showDebugInfo" : False,
                 "scriptsPath": path}
        plugin = self.plugin_module.Plugin("", "", "0.2", props)
        plugin.startup()
        return plugin

    def test_Startup_LogsError_OnNonexistantLoadPath(self):
        PluginBaseForTest.errorLog.side_effect = None
        self.new_plugin(path="./doesnt_exist")
        self.assertTrue(PluginBaseForTest.errorLog.called)

    def test_Startup_LogsError_OnEmptyLoadPath(self):
        PluginBaseForTest.errorLog.side_effect = None        
        self.new_plugin(path="./empty_directory")
        self.assertTrue(PluginBaseForTest.errorLog.called)

    def test_Startup_LogsError_OnBadPyFileInLoadPath(self):
        PluginBaseForTest.errorLog.side_effect = None        
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
        values = {"showDebugInfo" : True, "scriptsPath":"./test_scripts"}
        ok, d = self.plugin.validatePrefsConfigUi(values)
        self.assertTrue(ok)
        values = {"showDebugInfo" : False, "scriptsPath":"./test_scripts"}
        ok, d = self.plugin.validatePrefsConfigUi(values)
        self.assertTrue(ok)

    def test_PreferencesUIValidation_ReturnsErrorDict_OnBadLoadPath(self):
        values = {"showDebugInfo" : False, "scriptsPath" : "doesnt_exist"}
        PluginBaseForTest.errorLog.side_effect = None
        tup = self.plugin.validatePrefsConfigUi(values)
        self.asserts_for_UIValidation_Failure("scriptsPath", tup)

    def test_ActionUIValidation_Succeeds_OnValidInput(self):
        values = {"message":"Hi", "actionVersion":_VERSION,
                  "info1":"", "info2":"", "info3":""}
        tup = self.plugin.validateActionConfigUi(values, "getChatbotResponse", 1)
        self.assertEqual(len(tup), 2)
        ok, val = tup
        self.assertTrue(ok)

    def test_ActionUIValidation_Corrects_OldVersion(self):
        values = {"message":"Hi", "actionVersion":"0.0",
                  "info1":"", "info2":"", "info3":""}
        tup = self.plugin.validateActionConfigUi(values, "getChatbotResponse", 1)
        self.assertEqual(values["actionVersion"],
                         self.plugin_module._VERSION)
        self.assertEqual(len(tup), 2)
        ok, val = tup
        self.assertTrue(ok)

    def test_ActionUIValidation_Fails_OnEmptyMessage(self):
        values = {"message":"", "actionVersion":_VERSION,
                  "info1":"", "info2":"", "info3":""}
        tup = self.plugin.validateActionConfigUi(values, "getChatbotResponse", 1)
        self.asserts_for_UIValidation_Failure("message", tup)

    def test_ActionUIValidation_Fails_OnFailedSubstitutionCheck(self):
        values = {"message":"Hi", "actionVersion":_VERSION,
                  "info1":"1", "info2":"2", "info3":"3"}
        fail_on = ""
        def sub(self, string, validateOnly):
            if validateOnly:
                return (string != values[fail_on], string)
        PluginBaseForTest.substitute = sub
        fail_on = "message"
        tup = self.plugin.validateActionConfigUi(values, "getChatbotResponse", 1)
        self.asserts_for_UIValidation_Failure("message", tup)

        fail_on = "info3"
        tup = self.plugin.validateActionConfigUi(values, "getChatbotResponse", 1)
        self.asserts_for_UIValidation_Failure("info3", tup)

    def test_DeviceStartComm_Fixes_DeviceVersion(self):
        dev = DeviceForTest(1, "dev", {})
        self.plugin.deviceStartComm(dev)
        self.assertEqual(dev.pluginProps["deviceVersion"], _VERSION)

    def test_DeviceStartComm_Succeeds_OnValidInput(self):
        dev = self.make_and_start_a_test_device(1, "dev1",
                                                {"deviceVersion":_VERSION})
        states = dev.states
        self.assertEqual(len(states),
                         3 + len(self.plugin_module._SENDER_INFO_FIELDS))
        self.assertEqual(states["message"], "")
        self.assertEqual(states["status"], "Idle")
        for k in self.plugin_module._SENDER_INFO_FIELDS:
            self.assertEqual(states[k], "")
                        
    def test_DeviceStopComm_Succeeds(self):
        dev = self.make_and_start_a_test_device(1, "d1",
                                                {"deviceVersion":_VERSION})
        self.plugin.deviceStopComm(dev)
        self.assertFalse(dev.id in self.plugin.device_info)
        
    def test_respond_LogsError_OnEmptyMessage(self):
        action = Mock()
        action.props = {"message":"", "actionVersion":_VERSION} 
        dev = self.make_and_start_a_test_device(1, "d1",
                                                {"deviceVersion":_VERSION})
        action.deviceId = dev.id
        PluginBaseForTest.errorLog.side_effect = None
        self.plugin.getChatbotResponse(action)
        self.assertTrue(PluginBaseForTest.errorLog.called)

    def test_respond_LogsError_OnBadVersion(self):
        action = Mock()
        action.props = {"message":"status", "actionVersion":"0.1"}
        dev = self.make_and_start_a_test_device(1, "d1",
                                                {"deviceVersion":_VERSION})
        action.deviceId = dev.id
        PluginBaseForTest.errorLog.side_effect = None
        self.plugin.getChatbotResponse(action)
        self.assertTrue(PluginBaseForTest.errorLog.called)

    def test_respondToMessageAndClearResponse_Succeed_OnValidInput(self):
        dev = self.make_and_start_a_test_device(1, "d1",
                                                {"deviceVersion":_VERSION})
        self.assertEqual(dev.states["status"], "Idle")

        action = Mock()
        action.deviceId = dev.id

        test_message = "sensor wet"
        action.props = {"message":test_message, "actionVersion":_VERSION}
        for i, k in enumerate(self.plugin_module._SENDER_INFO_FIELDS):
            action.props[k] = "wet" + unicode(i)
        self.plugin.getChatbotResponse(action)
        
        self.assertEqual(dev.states["status"], "Ready")
        self.assertEqual(dev.states["message"], test_message)
        self.assertEqual(dev.states["response"], "Now the leak sensor is wet.")
        for i, k in enumerate(self.plugin_module._SENDER_INFO_FIELDS):
            self.assertEqual(dev.states[k], "wet" + unicode(i))

        # Because the setup is already done, test that getChatbotResponse adds to
        # the backlog when there is already a response waiting

        test_message2 = "sensor dry"
        action.props["message"] = test_message2
        for i, k in enumerate(self.plugin_module._SENDER_INFO_FIELDS):
            action.props[k] = "dry" + unicode(i)
        self.plugin.getChatbotResponse(action)

        self.assertEqual(dev.states["status"], "Ready")
        self.assertEqual(dev.states["message"], test_message)
        self.assertEqual(dev.states["response"], "Now the leak sensor is wet.")
        for i, k in enumerate(self.plugin_module._SENDER_INFO_FIELDS):
            self.assertEqual(dev.states[k], "wet" + unicode(i))
        
        self.assertEqual(len(self.plugin.device_info[dev.id]), 1)

        # Now test that clearResponse fetches the backlog 
        action = Mock()
        action.deviceId = dev.id
        self.plugin.clearResponse(action)
        self.assertEqual(dev.states["status"], "Ready")
        self.assertEqual(dev.states["message"], test_message2)
        self.assertEqual(dev.states["response"], "Now the leak sensor is dry.")
        for i, k in enumerate(self.plugin_module._SENDER_INFO_FIELDS):
            self.assertEqual(dev.states[k], "dry" + unicode(i))
        self.assertEqual(self.plugin.device_info[dev.id], [])

        # And clearResponse again should change state to Idle
        self.plugin.clearResponse(action)
        self.assertEqual(dev.states["status"], "Idle")
        
    def make_and_start_a_test_device(self, dev_id, name, props):
        dev = DeviceForTest(dev_id, name, props)
        self.indigo_mock.devices[dev_id] = dev
        self.plugin.deviceStartComm(dev)
        return dev

    def asserts_for_UIValidation_Failure(self, tag, tup):
        self.assertEqual(len(tup), 3)
        ok, val, errs = tup
        self.assertFalse(ok)
        if tag:
            self.assertTrue(tag in errs)
            self.assertTrue(errs[tag])

class ReturnAddressTestCase(IndigoMockTestCase):
    def setUp(self):
        IndigoMockTestCase.setUp(self)
        self.RA = self.plugin_module.ReturnAddress

    def tearDown(self):
        IndigoMockTestCase.tearDown(self)

    def testReturnAddress_Freezes_and_Thaws(self):
        d = {"key":"value"}
        ra = self.RA(info=d)

        f = ra.freeze()
        ra2 = self.RA(frozen=f)
        self.assertEqual(len(ra2.info), 1)
        self.assertEqual(ra2.info["key"], "value")

    def testReturnAddress_Raises_OnIncorrectKwargs(self):
        self.assertRaises(TypeError, self.RA)
        f = self.RA(info={"key":"value"}).freeze()
        self.assertRaises(TypeError, self.RA, frozen=f, foobar=None)
        self.assertRaises(TypeError, self.RA, info={"key":"value"}, foobar="what")


if __name__ == "__main__":
    unittest.main()
