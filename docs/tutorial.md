# Tutorial

This tutorial will attempt to help you learn to write your own Chatbot Plugin scripts by going through an example script, `valves.py`.

## What is a Chatbot Plugin script, anyway?
A Chatbot Plugin script is just some python code that lets you relate words and patterns of words to look for in incoming messages to python code that you execute in response to those messages. With Python magic to make it as concise as possible an expression of how you want the conversation to go.
## Ok, let's dive in
There's a little bit of boilerplate that needs to be at the beginning of every script:
```python
from __future__ import unicode_literals
import indigo
from chatbot_reply import Script, rule
```
When Python 2.6 was the latest and greatest, maybe unicode was the future, but in the twenty-teens if you want to respond to text messages from the Wide, Wild World, the future is now, text will be arriving in unicode containing characters you didn't even know existed and you have to deal. 

Importing `indigo` gives you access to the yummy [IOM (Indigo Object Model)](http://wiki.indigodomo.com/doku.php?id=indigo_6_documentation:object_model_reference) which lets you make Indigo Server sing and dance, and the two imports from `chatbot_reply` contain the python magic that turns your python script into an interactive chatbot.

## The Script
```python
class ValveScript(Script):
```
The Chatbot Plugin will import every .py file in the directory you give it, but all it's really looking for is subclasses of `Script`. It will collect all of them, create one instance of each one, and run its `setup` method. This method is optional, but can be used to initialize any data structures you might want to use in your code, plus two structures used by the chatbot engine: `self.alternates` which is a dictionary of alternate names for things, and `self.botvars`, which we will get to later.

```python
    def setup(self):
        self.alternates = {
            "mainvalve" : "((shutoff|shut off|main|main water|city water) valve)",
            "drainvalve": "([water] drain valve)",
            "anyvalve"  : "((shutoff|shut off|main|main water|city water|[water] drain) valve)"
            }
 ```
Woah, what just happened! We just defined some patterns. What is a pattern, anyway? A pattern is a concise description of what user messages we're interested in. These patterns are giving alternate names for things, so for example:
```sh
((shutoff|shut off|main|main water|city water) valve)
```
Is describing all of these: "shutoff valve", "shut off valve", main valve", "main water valve", "city water valve", and:
```sh
([water] drain valve)
```
Means we're interested in the "water drain valve" and the "drain valve". So if you have things between parentheses separated by vertical bars, you can choose any one of them, but you have to choose one. Things between square brackets separated by vertical bars mean you can choose any one of them or nothing if you want.

So what did we just do? We defined a bunch of alternate names for things, specifically for the two automatic water valves on our vacation house. So that you, and especially your spouse, don't have to remember whether you called it the shutoff valve or the main valve. These alternate names are going to come in handy real soon, when we define a Chatbot Rule.

## A Chatbot Rule
```python
   @rule("open [the] _%a:mainvalve")
    def rule_open_the_mainvalve(self):
        if self.drainvalvestatus() == "open":
            return "The drain valve is open. Please close it before opening the {match0}."
        if self.leaksensorstatus() == "wet":
            return "<leak sensor status> Please dry it and reset it before opening the {match0}."
        self.tellmainvalve("open")
        return "I'll tell the {match0} to open" + self.stall_for_time()
```
You can define whatever methods you want in your class that is a subclass of `Script`, but only the ones that are preceded by the `@rule` decorator and begin with the four letters "rule" will be used as Chatbot Rules. The `@rule` decorator is given the pattern to match to the message from the user. In this case the pattern contains four things: the word "open", an optional "the", and `%a:mainvalve` which is shorthand for the `"mainvalve"` entry in the `self.alternates` dictionary. Wait, that's three things, did we miss one? Yes, see the "_" before `%a:mainvalve`? That is shorthand for "memorize" which will make the pattern matching code stash away which valve name the user used in their message, so we can use it later.

So the pattern for this rule will match messages that say things like "Open the main valve." and "open shut off valve" and "OPEN CITY WATER VALVE!!!!" because matching ignores case and punctuation. But it will not match "openmainwatervalve" or "Indigo, please open the main water valve." 

What can a rule do? Run whatever python code you want it to, that's what. And then return a response message to send back to the user. This one calls a couple methods, which go talk to IndigoServer and return things we can combine with a little bit of logic, to make a sensible decision about whether or not it's a good idea to turn on the water. If it turns out to be a good idea, there's a third method call to do the nitty gritty with whichever one of your `indigo.devices` is hooked up to that water valve. And then there are the `return` statements, which hopefully obviously are returning responses to the user. Which responses, also hopefully obviously, get some post-processing by the chatbot. For example this one:

```
The drain valve is open. Please close it before opening the {match0}.
```
What's the `{match0}`? Remember the underscore? Underscores put entries in a dictionary which you can use as `self.match`, and the keys will be `"match0"`, `"match1"`, `"match2"`, and so on for each underscore you put in the pattern.  The values stored with those keys will be the lower-case, punctuation-removed, version of the user's message. There will also be in the dictionary `"raw_match0"` etc., which will contain the original text with original capitalization and punctuation. So if the user called the valve the "shutoff valve" in their message, that would get substituted back in by the chatbot engine, and the user would receive:
```
The drain valve is open. Please close it before opening the shutoff valve.
```
The next return value is also doing some weird thing:

```
<leak sensor status> Please dry it and reset it before opening the {match0}.
```
If a return value from a rule contains some text within `< >`, then the chatbot is going to take that text and treat it like it was a separate message from the user, get an answer to it and substitute it in to this response. So let's say the rule for "leak sensor status" comes back with "The leak sensor is wet." Then the finished response to the user would be:
```
The leak sensor is wet. Please dry it and reset it before opening the shutoff valve.
```
The third possible response for this rule tacks on the return value from something called `self.stall_for_time()`. Let's look at that one:

```python
def stall_for_time(self):
    return self.choose([". Give it a few seconds and text me 'status' and I'll let you know how the valves are doing.",
                        ". Give me just a moment, then text me 'status' to make sure it worked.",
                        ", and in a few seconds please text me 'status' to check on the valves."])            
```
Introducing `self.choose`! This is a method defined in the `Script` parent class, which does a few handy things. If you give it a string, it just returns that string, but if you give it a list of strings, it chooses one at random to return. So if you want to vary your responses like the sophisticated chat robot you are, `self.choose` can help. But you don't need to actually call it, because the first thing that `@rule` does with the return value from a rule method is feed it to `self.choose`. So you could do this:
```python
@rule("hello")
def rule_hello(self):
	return ["Hi!", "Hello!", "Howdy!", "Buongiorno!"]
```
And each time this rule is used, one of the replies from the list will be randomly selected. But `self.choose` can do more, because you could also do this:
```python
@rule("hi")
def rule_hi(self):
    return [("Hi!", 33), ("Hello!",33), ("Howdy!",33), ("Buongiorno!",1)]
```
And then `self.choose` will weight its random selection by the numbers, so that it only has a 1% chance of pretending to be Italian. But after all this, do you want `self.choose` to do more? Then write your own and `@rule` will call it for you. See the script `eliza.py` for an example of an alternative `self.choose` which tries to choose a response that hasn't already been used.

You may be wondering, do the names I give my rule methods matter? And the answer is no, they don't as long as they are unique within your `Script` subclass. I personally like using long descriptive ones because then the autocomplete in my editor will tell me that I'm writing a rule I already wrote somewhere else. But you could call them `rule001`, `rule002` if you want, or if you're writing an AIML translator.

```py
@rule("_%a:mainvalve status")
def rule_mainvalve_status(self):
    return "The {{match0}} is {0}.".format(self.mainvalvestatus())
```
By now you should have an idea what this rule does, but what's with the double curly braces? The return value from `"The {{match0}} is {0}.".format("closed")` is going to be `"The {match0} is closed."`. So the double curly braces make the `match0` survive the first call to `format` so it can be used by the second call to `format` which is behind the scenes in `@rule`. The behind the scenes method which `@rule` uses, which has that call to `format` is called `self.process_reply` so if you would like to do any extra work on the responses of all your rules you can define that method in your subclass as well. Once again see `eliza.py` for an example.

So let's say that last rule just sent the user the message "The city water valve is closed." and the user sends back "Open it." Can we do that? Yes, we can:

```py
@rule("_(open|close) it", previous_reply="[*] _%a:anyvalve [*]")
def rule_open_close_it_previous_any_valve(self):
    return "<{match0} the {reply_match0}>"
```
The keyword argument `previous_reply` is a pattern to match against the chatbot's last response. And in this case it contains wildcards wrapped in square brackets to make them optional. The `*` wildcard will match one or more words or numbers. So `[*]
` makes the wildcard match optional, meaning zero or more words will match. So if the user says "open it" or "close it" and the chatbot's last response was talking about a valve, this rule will match. And we know that we want to use the logic from the very first rule we talked about. But we can't call it directly, because if we try we'll get an error because `@rule` changes the number of arguments to the methods you decorate it with, and if you get around that, `self.match['match0']` is "open" and `rule_open_the_mainvalve` is expecting it to be a valve name and somewhere around this point you realize calling it directly is more trouble than it's worth. Which is why the chatbot engine gives you another way to call it: construct a message to trigger that rule and put it inside `< >`.

If you have a `previous_reply` with underscores, then `self.match` will also have entries for `reply_match0`, `reply_match1` and so on as well as `reply_raw_match0` etc.

There is a problem with this rule. What if the chatbot's last response mentioned both valves? The `%a:anyvalve` will match the first one in the response, but is that always going to be the one the user is talking about? You could either carefully review all the responses in your script to make sure it's always going to work, or write a catchall rule to ask for clarification and a followup rule to redirect to the rule that does the actual work, once we have all the information.

```py
@rule("_(open|close) it", previous_reply=
      "([*] %a:mainvalve * %a:drainvalve [*]|[*] %a:drainvalve * %a:mainvalve [*])")
def rule_open_close_it_previous_both_valves(self):
    return ["What do you want me to {match0}?",
            "Which valve would you like to {match0}?"]
               
@rule("[the] _%a:anyvalve", previous_reply=
      "(what do you want me|which valve would you like) to _(open|close)")
def rule_the_anyvalve_with_previous_whaddayawant(self):
    return "OK, <{reply_match0} the {match0}>"
```
There's still a problem. Don't both rules actually match the message and the last response? Yes, they do. How does the chatbot engine pick the rule to execute and is it going to pick the one we want it to? The chatbot engine has an algorithm for giving patterns scores that tries to rank more complex patterns with more actual words in them higher than patterns with fewer words or wildcards. If you turn on the debug logging for the chatbot engine, when it receives its first message after loading rules, it will print a sorted list of them and you can see if they are in the order you want. If they aren't, there is an optional `weight=` parameter to `@rule` which you can use to move a rule up in the list. The default weight for rules is 1. Once again, see `eliza.py` for examples.

By now you should know enough to write some rules to make Indigo play along with all your knock-knock jokes and tell you they are funny. But there's actually a bunch more stuff the chatbot engine can do. There are variables your rules can set and use in patterns, both per-user and globally for all users. There is the concept of a current topic, which can limit the rules the chatbot engine searches for a match. It's possible to change how raw user messages are processed before they are compared with the patterns. And you can create a hierarchy of `Script` classes that inherit rules and methods. 
