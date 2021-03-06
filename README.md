## indigo-chatbot

An Indigo Domotics plugin to enable natural language communication, in
coordination with other plugins that connect to chat services.  This
plugin is, optimistically, beta software. Please only use it if you
don't mind using software that is only partially complete, subject
to change, and undoubtedly buggy.

The chatbot engine in this plugin can be scripted using Python. User
messages are matched against simplified regular expressions, which
direct execution to rule methods in the scripts which can execute
arbitrary Python code, communicate just like other Indigo Python
scripts with IndigoServer, and then return text responses to send to
the user. A rule method decorator is provided to keep rule
declarations as concise as possible.

### Installation instructions

[Download the (zip archive of the) plugin here](https://github.com/gazally/indigo-chatbot/archive/master.zip)

[Follow the plugin installation instructions](http://wiki.indigodomo.com/doku.php?id=indigo_6_documentation:getting_started#installing_plugins_and_configuring_plugin_settings_pro_only_feature)

### Configuration Instructions

The configuration dialog for this plugin asks for a path to a
directory of scripts files. If you don't have any scripts yet you can
point it to the example_scripts directory in the zip archive. One of
the scripts in example_scripts, valves.py, will create three variables
in Indigo, and the others will not talk to Indigo at all.

There are also options for debug logging. If don't turn on "Enable
plugin debug logging" you won't see any debug output, but if you turn
on that plus "Enable chatbot engine debug logging" you will get A LOT
of logging. Unless you're trying to track down bugs in your chat
scripts, you probably want to leave it off.

### Menu Commands

From the menu you can reload the scripts directory, which is useful if
you have edited your scripts and would like to try out your
changes. If you would like to test your scripts without going through
whichever messaging app you are using with Indigo, choose "Start
Interactive Chat in Terminal Window". This will bring up a prompt that
will let you type messages and see the bot's response to them.

Commands at the chat prompt:

-`/names`: see what users are in the chatbot's registry.

-`/name Fred`: tell it the name of the user you want the messages you
 type to appear to come from. It will respond with the information
 last used to communicate with that user.

-`/new Fred`: tell it to process the next message you type as if from
 a new user named Fred.

In addition to the usual plugin menu commands for toggling debug
logging, there is one that will start a Python interpreter in the
plugin's namespace. Typing `self.bot.rules_db.script_instances` at
that prompt will give you a list of the instances of your script
classes that the chatbot is using, in case you would like to examine
instance variables in your scripts.

### Setting up a Chatbot Device

In order to use the chatbot, you'll need to set up a device called a
Chatbot Responder. No configuration is necessary.

### Getting a Response from the Chatbot

To get a chat going, you'll need another plugin that can send and
receive messages. I'll use my Messages Plugin as an example, but the
Google SMS plugin or the Twitter direct messaging plugin should also
work. Set up the other plugin, and then create a trigger that reacts
when the other plugin gets a new message. For Messages, you'll need to
create a Messages App Device and set it up to react on Device State
Changed, when Status becomes equal to New. Copy the numeric device id,
because you will need it shortly.

For the first action item in the trigger, choose the Chatbot action
Get Chatbot Response, choose the Chatbot Responder Device you made
earlier, and Edit Action Settings. In the Message field of the
configuration dialog, enter %%d:00000000:message%%, except instead of
00000000 use the numeric id of the Messages App device. This if you
haven't seen it is Indigo's device substitution syntax. When the
action is executed, Indigo will look up the state named "message" on
your device and substitute that in instead.

In the Name field of the configuration dialog, put
%%d:00000000:name%%, once again substituting the Messages App device's
numeric id. This will give you the Messages App's best guess as to the
real name for your contact. You could also type in whatever you want
here, but you have to have something, because this field is the one
the chatbot uses to identify who it's talking to.

The Action configuration has three boxes for "Sender Info". For a
Messages App device which is not set to "All Senders" you don't need
to put anything here.

To complete your trigger, add a second action that marks the message
as read. It's a good idea to add a small delay here, because Indigo
Server doesn't always execute your trigger actions in the order you
think it's going to, and you don't want the Messages plugin to clear
the message on its device before the Chatbot fetches it.

If your Messages App device is already sitting there with a new
message, the trigger won't go off, so you'll have to select "Execute
Actions Now" in the bottom right corner of the home window to get it
started. If all went well, the state of the Chatbot Responder device
will change from "Idle" to "Ready". If all didn't go well, have a look
at the log and maybe turn on debug logging and try it again. The most
likely cause for a Chatbot Responder device staying on Idle when you
tell it to Get Chatbot Response is that the chatbot engine ran its
scripts and came up with an empty response.

### Delivering the Response

First, go look at your Chatbot Responder device and copy its numeric
id, because you are going to need it.

In order to do something with the response from the chatbot, another
trigger is necessary. This one should use the Chatbot Responder device
and react when Status: becomes equal to Ready. No conditions are
necessary.

For the first action item in this trigger, choose the Messages App
action Send Message, and choose the Messages App device you made
earlier. In the Message to Send field, enter %%d:11111111:response%%,
except replace the 11111111 with the numeric id of your Chatbot
Responder device. Save this action configuration. Then add a second
action, and choose "Clear Chatbot Response" and select the Chatbot
Responder. No configuration of this action is necessary but again, it
is a good idea to add a small delay.

If your Chatbot Responder already has it's status set to Ready, this
second trigger won't go off, but you can start it using "Execute
Actions Now" in the bottom right corner of the home window.

### Say Something

If you're using my example scripts, try sending it "hello". Saying
"I'd like to talk to Eliza" is another option.

### Talking to Everyone

The method just described requires you to set up two triggers and two
devices per person that you would like the chatbot to talk to, which
might be fine if you only want Indigo to talk to yourself and your
spouse. But if you would like your chatbot to be able to respond to
messages from anyone, and you can write your own logic to decide if
you trust them to communicate with your Indigo Server, you can use a
Messages App plugin device set to accept messages from all
senders. Set the Chatbot Responder device and the two triggers up as
before, with a couple changes.

First, in the configuration for Get Chatbot Response, you will need to
put %%d:00000000:service%% in the first Sender Info field and
%%d:00000000:handle%% in the second, in both cases replacing the
00000000 with the id of your Messages App Device.

Second, in the configuration for the Send Message Action, you should
put %%d:11111111:info1%% in the Service field and %%d:11111111:info2%%
in the Handle field, except instead of 11111111 use the id of your
Chatbot Responder device.

### What is going on here?

The Get Chatbot Response action has three generic fields for stashing
away information about who to reply to. Using device state
substitution, you can get this information from the states of the
Chatbot Responder device and use it to configure the action of
whichever plugin you use to deliver the reply.

### That one second delay is a kludge and I don't like it

Well it's a kludge that mostly works, at least on my lightly loaded
Indigo Server. But you could get rid of it with two more triggers, one
to mark the message as read when the Chatbot Responder device state
changes to Processing and another to clear the chatbot response when
the Messages App device "Status of Last Sent Message" changes to
Sending.

### Getting started writing Chat Scripts

Have a look at the scripts in example_scripts. There is also some
incomplete but possibly helpful documentation in the docs directory.

### Scripting the Chatbot Plugin

Let's say for example that 12345678 is the device id of a Chatbot
Responder device, and that userName, serviceName and handleName are
variables containing the name, service and handle of the person on
Messages who you would like the response to be sent to. Then you can
do this:

```py
chatbotId = "me.gazally.indigoplugin.chatbot"
chatbotPlugin = indigo.server.getPlugin(chatbotId)
if chatbotPlugin.isEnabled():
    props = {"message" : "This is the message my script would like a response to.",
             "name"  : userName,
             "info1" : serviceName,
             "info2" : handleName,
             "info3" : ""}
    chatbotPlugin.executeAction("getChatbotResponse", deviceId=12345678, props=props)
```

The Chatbot Plugin is running in a different process than your script,
so this will not immediately set the device state to Ready. But you
can run another script from a trigger set to the device state becoming
Ready that does this:

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

### What does the future hold? Some ideas.

The chatbot engine waits for rule methods to finish. Rules could be
run in separate threads or maybe separate processes. This would
probably mean creating per-user instances of Script objects.

It would be nice to have a mechanism for asynchronous replies, so that
based on things that happen in Indigo, the chatbot engine could be
triggered to send unprompted messages, using address information it
has saved. Currently you could do that by having a trigger ask for a
reply to a message the user didn't actually send. But the logic seems
convoluted. The whole area needs some thought.

There are internal state variables for the chatbot scripts. These
could be saved to a file and reloaded.

It's kind of disconcerting how fast replies arrive. Perhaps a typing
delay simulator would help.

Better tokenizing of numbers and numeric expressions.

Let scripts supply a list of substitutions to be made in the
tokenizer, instead of or in addition to a substitute function.

Parsing of time expressions. "Turn off the basement lights in an hour"
and "Turn off the basement lights at 3:30" should be handled by the
same rule.

Could define an exception that rules could raise if they look at the
match dictionary and decide it doesn't make sense, and then the engine
would search for the next rule that matches.

Add wildcard syntax to match anything except a list of supplied
words. For example: "i *~3!(hate|not) cookies"

Make case-sensitive matching an option?

Maybe look for __init__.py in the scripts directory and import it as
one module if found. This would let script writers control their
import order.

### What are some known issues

If you don't put any rules in the default topic, "all", the chatbot
won't deal with that very well.

Rule methods that take a long time will block the chatbot from
responding to anyone else.

