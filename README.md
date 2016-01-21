## indigo-chatbot
An Indigo Domotics plugin to enable natural language communication, in coordination with other plugins that connect to chat services.  This plugin is, optimistically, beta software. Please only use it if you don't mind using beta software.

The chatbot engine in this plugin can be scripted using Python. User messages are matched against simplified regular expressions, which direct execution to rule methods in the scripts which can execute arbitrary Python code, communicate just like other Indigo Python scripts with IndigoServer, and then return text responses to send to the user. A rule method decorator is provided to keep rule declarations as concise as possible.

### Installation instructions

[Download the (zip archive of the) plugin here](https://github.com/gazally/indigo-chatbot/archive/master.zip)

[Follow the plugin installation instructions](http://wiki.indigodomo.com/doku.php?id=indigo_6_documentation:getting_started#installing_plugins_and_configuring_plugin_settings_pro_only_feature)

### Configuration Instructions

The configuration dialog for this plugin asks for a path to a directory of scripts files. If you don't have any scripts yet you can point it to the example_scripts directory in the zip archive. One of the scripts in example_scripts, valves.py, will create three variables in Indigo, and the others will not talk to Indigo at all.

There are also options for debug logging. If don't turn on "Enable plugin debug logging" you won't see any debug output, but if you turn on that plus "Enable chatbot engine debug logging" you will get A LOT of logging. Unless you're trying to track down bugs in your chat scripts, you probably want to leave it off.

### Menu Commands

In addition to the usual plugin menu commands for toggling debug logging, there is one that will reload the scripts directory. This is handy if you've edited your scripts and want to try out your changes.

### Setting up a Chatbot Device

In order to use the chatbot, you'll need to set up a device called a Chatbot Responder. No configuration is necessary.

### Getting a Response from the Chatbot

To get a chat going, you'll need another plugin that can send and receive messages. I'll use my Messages Plugin as an example, but the Google SMS plugin or the Twitter direct messaging plugin should also work. Set up the other plugin, and then create a trigger that reacts when the other plugin gets a new message. For Messages, you'll need to create a Messages App Device and set it up to react on Device State Changed, when Status becomes equal to New. Copy the numeric device id, because you will need it shortly.

For the first action item in the trigger, choose the Chatbot action Get Chatbot Response, choose the Chatbot Responder Device you made earlier, and Edit Action Settings. In the Message field of the configuration dialog, enter %%d:00000000:message%%, except instead of 00000000 use the numeric id of the Messages App device. This if you haven't seen it is Indigo's device substitution syntax. When the action is executed, Indigo will look up the state named "message" on your device and substitute that in instead.

The Action configuration has three boxes for "Sender Info". For a Messages App device which is not set to "All Senders" you don't need to put anything here.

To complete your trigger, add a second action that marks the message as read. It's a good idea to add a small delay here, because Indigo Server doesn't always execute your trigger actions in the order you think it's going to, and you don't want the Messages plugin to clear the message on its device before the Chatbot fetches it.

If your Messages App device is already sitting there with a new message, the trigger won't go off, so you'll have to select "Execute Actions Now" in the bottom right corner of the home window to get it started. If all went well, the state of the Chatbot Responder device will change from "Idle" to "Ready". If all didn't go well, have a look at the log and maybe turn on debug logging and try it again. The most likely cause for a Chatbot Responder device staying on Idle when you tell it to Get Chatbot Response is that the chatbot engine ran its scripts and came up with an empty response.

### Delivering the Response

First, go look at your Chatbot Responder device and copy its numeric id, because you are going to need it.

In order to do something with the response from the chatbot, another trigger is necessary. This one should use the Chatbot Responder device and react when Status: becomes equal to Ready. No conditions are necessary.

For the first action item in this trigger, choose the Messages App action Send Message, and choose the Messages App device you made earlier. In the Message to Send field, enter %%d:11111111:response%%, except replace the 11111111 with the numeric id of your Chatbot Responder device. Save this action configuration. Then add a second action, and choose "Clear Chatbot Response" and select the Chatbot Responder. No configuration of this action is necessary but again, it is a good idea to add a small delay. 

If your Chatbot Responder already has it's status set to Ready, this second trigger won't go off, but you can start it using "Execute Actions Now" in the bottom right corner of the home window.

### Say Something

If you're using my example scripts, try sending it "hello". Saying "I'd like to talk to Eliza" is another option.

### Talking to Everyone

The method just described requires you to set up two triggers and two devices per person that you would like the chatbot to talk to, which might be fine if you only want Indigo to talk to yourself and your spouse. But if you would like your chatbot to be able to respond to messages from anyone, and you can write your own logic to decide if you trust them to communicate with your Indigo Server, you can use a Messages App plugin device set to accept messages from all senders. Set the Chatbot Responder device and the two triggers up as before, with a couple changes.

First, in the configuration for Get Chatbot Response, you will need to put %%d:00000000:service%% in the first Sender Info field and %%d:00000000:handle%% in the second, in both cases replacing the 00000000 with the id of your Messages App Device.

Second, in the configuration for the Send Message Action, you should put %%d:11111111:info1%% in the Service: field and %%d:11111111:info2%% in the handle field, except instead of 11111111 use the id of your Chatbot Responder device.

### What is going on here?

The Get Chatbot Response action has three generic fields for stashing away information about who to reply to. Using device state substitution, you can get this information from the states of the Chatbot Responder device and use it to configure the action of whichever plugin you use to deliver the reply.

### Getting started writing Chat Scripts

Have a look at the scripts in example_scripts. There is also some incomplete but possibly helpful documentation in the docs directory.

### Scripting the Chatbot Plugin

Let's say for example that 12345678 is the device id of a Chatbot Responder device, and that serviceName and handleName are variables containing the service and handle of the person on Messages who you would like the response to be sent to. Then you can do this:

```py
chatbotId = "me.gazally.indigoplugin.chatbot"
chatbotPlugin = indigo.server.getPlugin(chatbotId)
if chatbotPlugin.isEnabled():
    props = {"message" : "This is the message my script would like a response to.",
             "info1" : serviceName,
             "info2" : handleName,
             "info3" : ""}
    chatbotPlugin.executeAction("getChatbotResponse", deviceId=12345678, props=props)
```
The Chatbot Plugin is running in a different process than your script, so this will not immediately set the device state to Ready. But you can run another script from a trigger set to the device state becoming Ready that does this:

```py
device = indigo.devices[12345678]
reply = device.states["response"]
service = device.states["info1"]
handle = device.states["info2"]

chatbotId = "me.gazally.indigoplugin.chatbot"
chatbotPlugin = indigo.server.getPlugin(chatbotId)
if chatbotPlugin.isEnabled():
    chatbotPlugin.executeAction("clearResponse", deviceId=12345678, props={})
    
# Now go do something with reply, service and handle...
```

### What does the future hold?

A chatbot rule method that takes a long time to execute will block the plugin from responding to anyone else. Maybe rules need to be run in separate threads and maybe separate processes.

It would be nice to have a mechanism for asynchronous replies, so that based on things that happen in Indigo, the chatbot engine could be triggered to send unprompted messages.

There are internal state variables for the chatbot scripts. These could be saved to a file and reloaded.

It's kind of disconcerting how fast replies arrive. Perhaps a typing delay simulator would help.

By the time a message gets to the chatbot, all the chatbot knows about who it is from is the device number plus the three Sender Info fields. Adding a field for the sender's name would be useful for logging and script logic. 
