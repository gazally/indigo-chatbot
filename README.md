## indigo-chatbot
An Indigo Domotics plugin to enable natural language communication, in coordination with other plugins that connect to chat services.

The chatbot engine in this plugin can be scripted using Python. User messages are matched against simplified regular expressions, which direct execution to rule methods in the scripts which can execute arbitrary Python code, communicate just like other Indigo Python scripts with IndigoServer, and then return text responses to send to the user. A rule method decorator is provided to keep rule declarations as concise as possible.

### Installation instructions

[Download the (zip archive of the) plugin here](https://github.com/gazally/indigo-chatbot/archive/master.zip)

[Follow the plugin installation instructions](http://wiki.indigodomo.com/doku.php?id=indigo_6_documentation:getting_started#installing_plugins_and_configuring_plugin_settings_pro_only_feature)

### Configuration Instructions

The configuration dialog for this plugin asks for a path to a directory of scripts files. If you don't have any scripts yet you can point it to the example_scripts directory that was in the zip archive. One of the scripts, valves.py, will create three variables in Indigo, and the others will not talk to Indigo at all.

### Setting up a Chat Trigger

To get a chat going, you'll need another plugin that can send and receive messages. I'll use my Messages Plugin as an example, but the Google SMS plugin should also work. Set up a device in the other plugin, and then create a trigger that reacts when the device gets a new message. For Messages, set it up to react on Device State Changed, when Status becomes equal to New. Copy the numeric device id, because you will need it shortly.

For the first action item in the trigger, choose the Chatbot action Respond to a Message, and Edit Action Settings. In the configuration dialog, enter %%d:00000000:message%%, except instead of 00000000 use the numeric id of the device. This if you haven't seen it is Indigo's device substitution syntax. When the action is executed, Indigo will look up the state named "message" on your device and substitute that in instead.

Continuing with the Action configuration, next you need to tell the plugin how to send a message back. First select the device you created. Then you need the internal name of the plugin action to send a message. In Messages this is "sendMessage". Then you need the plugin's internal name for the outgoing message, in this case "message". There are four more fields to allow flexibility for the needs of different plugins, but if you set up the Messages device to be specific to one person (the "all senders" box not checked) those can be left blank.

Different plugins will have different names for these fields. The Google SMS plugin uses "receivedText" for the state name, "sendSMS" for the internal name of the action and "smsMessage" for the outgoing message. Unfortunately, while these items have much better names in the user interface, Indigo doesn't currently provide an API giving plugins access to each other's names for things. If you don't know, you'll have to look in the plugin's documentation, ask its developer, or read its Devices.xml and Action.xml files looking for them.

To complete your chatbot trigger, add a second action that marks the message as read. If your device is already sitting there with a new message, the trigger won't go off, so you'll have to select "Execute Actions Now" in the bottom right corner of the home window to get it started.

## Say Something

If you're using my example scripts, try sending it "hello". Saying "I'd like to talk to Eliza" is another option.

## Talking to Everyone

The method just described requires you to set up one trigger per person that you want the chatbot to talk to. If you would like your chatbot to be able to respond to messages from anyone, and you can write your own logic to decide if you trust them to communicate with your Indigo Server, you can use a Messages plugin device set to accept messages from all senders. To send the return message, in the action settings you will need to set the four fields at the bottom as follows, replacing the 00000000s with your device's numeric id:

                  |                   |
------------------|------------------
Property Name 1:  | service
Property Value 1: | %%d:00000000:service%%
Property Name 2:  | handle
Property Value 2: | %%d:00000000:handle%%

## Indigo can talk to the Chatbot too

One of the things you can do in the Chatbot Action Settings dialog is set the device to "Just ask Chatbot for response, don't send it" which you may find is the easiest way for you to communicate to your chatbot scripts about events that happen in Indigo, such as triggers firing.

## Making Plugins that work with the Chatbot Plugin

The Chatbot plugin can talk to any other plugin that defines an action which can deliver a message, given a device id and an action properties dictionary containing three entries, one of which is the message.

## Scripting the Chatbot Plugin

Let's say for example that 12345678 is the device id of a Messages Plugin device set to All Senders, and that serviceName and handleName are variables containing the service and handle of the person on Messages who you would like the response to be sent to. Then you can do this:

```py
chatbotId = "me.gazally.indigoplugin.chatbot"
chatbotPlugin = indigo.server.getPlugin(chatbotId)
if chatbotPlugin.isEnabled():
    props = {"device" : 12345678,
             "message" : "This is the message my script would like a response to.",
             "message_field" : "message",
             "send_method" : "sendMessage",
             "fieldname1" : "service",
             "fieldvalue1" : serviceName,
             "fieldname2" : "handle",
             "fieldvalue2" : handleName}
	chatbotPlugin.executeAction("respondToMessage", props=props)
```
