#! /usr/bin/env python
# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
""" chatbot_reply.script, defines decorators and superclass for chatbot scripts 
"""
from __future__ import unicode_literals
import collections
from functools import wraps
import random
import re

from chatbot_reply.six import with_metaclass
from chatbot_reply.constants import _HISTORY, _PREFIX

def rule(pattern_text, previous_reply="", weight=1):
    """ decorator for rules in subclasses of Script """
    def rule_decorator(func):
        @wraps(func)
        def func_wrapper(self, pattern=pattern_text,
                         previous_reply=previous_reply, weight=weight):
            result = func(self)
            try:
                return self.process_reply(self.choose(result))
            except Exception as e:
                name = (func.__module__[len(_PREFIX):] + "." +
                        self.__class__.__name__ + "." + func.__name__)
                msg = (" in @rule while processing return value "
                       "from {0}".format(name))
                e.args = (e.args[0] + msg,) + e.args[1:]
                raise
        return func_wrapper
    return rule_decorator

class ScriptRegistrar(type):
    """ Metaclass of Script which keeps track of newly imported Script
    subclasses in a list.
    Public class attribute:
        registry - a list of classes
    Public class method:
        clear - empty the registry list
    """
    registry = []
    def __new__(cls, name, bases, attributes):
        new_cls = type.__new__(cls, name, bases, attributes)
        if new_cls.__module__ != cls.__module__:
            cls.registry.append(new_cls)
        return new_cls

    @classmethod
    def clear(cls):
        cls.registry = []


class Script(with_metaclass(ScriptRegistrar, object)):
    """Base class for Chatbot Engine Scripts

    Classes derived from this one can be loaded by the ChatbotEngine.

    Subclasses may define: 

    topic - This must be a class attribute, not an instance variable.
        Contains a string that is inspected when the class is
        imported. All rules and substitution functions in a class are
        associated with a topic, and will only be used to process a user's
        message when the user's topic is equal to the class
        topic. Changing this value for a class after import will have no
        effect.  If topic is set to None, the class will not be instantiated,
        so __init__, setup and setup_user will not be run. If you 
        want to share a lot of rules between two Script subclasses with
        different topics, have them inherit them from a base class with
        its topic set to None.
    setup(self) - a method that may be used to define alternates (see below)
        and to initialize bot variables. It will be called after the class is
        loaded, and may be called again if resetting bot variables is implemented.
    setup_user(self, user) - a method that is called the first time the engine
        is processing a message from a given user. This is a good place to initialize
        user variables used by a script.
    alternates - a dictionary of patterns. Key names must be alphanumeric and
        may not begin with an underscore or number. The patterns must be simple
        in that they can't contain references to variables or wildcards or
        the memorization character _. When the patterns for the rules are 
        imported the alternates will be substituted in at import time, as 
        opposed to user and bot variables, which are substituted in every time
        a rule is matched with a new message. If you have 20,000 rules, this
        might make a performance difference, but if you have 20, it won't. 
        Changing self.alternates after import will have no effect on pattern matching.
    substitute(self, text, list_of_lists) - Any method name defined by a subclass
        that begins with substitute will be called with the raw text of every
        message (within its topic) and a list of list of words that have been
        split on whitespace. It must return a list of lists of words where the 
        outer list is the same length. Use this to do things like expand
        contractions, interpret ascii smileys such as >:| and otherwise mess
        with the tokenizations. If there is more than one substitute method 
        for a topic, they will all be called in an unpredictable order, each
        passed the output of the one before.
    @rule(pattern, previous="", weight=1)
    rule(self) - methods decorated by @rule and beginning with "rule" are
        the gears of the script engine. The engine will select one rule method 
        that matches a message and call it. The @rule decorator will run the 
        method's return value through first self.choose then self.process_reply.

    Child classes may overload self.choose and self.process_reply if they would
    like different behavior.

    Public instance variables that are meant to be used by child classes,
    but not modified (with the exception that it's ok to change, add and
    delete things in the variable dictionaries, just not the dictionary
    objects themselves):
    botvars - dictionary of variable names and values that are global for
        all users of the chatbot engine
    uservars - dictionary of variable names and values for the current user
    userinfo - UserInfo object containing info about the sender
    match - a Match object (see rules.py) representing the relationship between
        the matched user input (and previous reply, if applicable) and the 
        rule's patterns
    current_topic - string giving current conversation topic, which
        will limit the rule search for the next message

    All of the above are set by the ChatbotEngine.

    """
    topic = "all"

    def __init__(self):
        self.botvars = None
        self.userinfo = None
        self.match = None

    @property
    def uservars(self):
        return self.userinfo.vars

    def ct_get(self):
        return self.userinfo.topic_name

    def ct_set(self, newtopic):
        self.userinfo.topic_name = newtopic

    current_topic = property(ct_get, ct_set)
    
    def setup(self):
        """ placeholder """
        pass

    def setup_user(self, user):
        """ placeholder """
        pass

    def choose(self, args):
        """ Select a response from a list of possible responses. For increased
        flexibility, since this is used to process all return values from all
        rules, this can also be passed None or an empty string or list, in which
        case it will return the empty string, or it may be passed a string, which
        it will simply return.
        If the argument is a list of strings, select one randomly and return it.
        If the argument is a list of tuples containing a string and an integer 
        weight, select a string randomly with the probability of its selection 
        being proportional to the weight.

        """
        if args is None or not args:
            reply = ""
        else:
            reply = args
        if isinstance(args, list) and args:
            reply = random.choice(args)
            if isinstance(args[0], tuple):
                args = [(string, max(1, weight)) for string, weight in args]
                total = sum([weight for string, weight in args])
                choice = random.randrange(total)
                for string, weight in args:
                    if choice < abs(weight):
                        reply = string
                        break
                    else:
                        choice -= abs(weight)
        return reply

    def process_reply(self, string):
        """ Process a reply before returning it to the chatbot engine. The only
        thing this does is use built-in string formatting to substitute in the 
        match results.
        """
        return string.format(*[], **self.match)

    
class UserInfo(object):
    """ A class for stashing per-user information. Public instance variables:
    vars: a dictionary of variable names and values
    info: a dictionary of information about the user
    topic_name: the name of the topic the user is currently in
    msg_history: a deque containing Targets for a few recent messages
    repl_history: a deque containing Targets for a few recent replies
    """
    def __init__(self, info):
        self.vars = {}
        self.info = info
        self.topic_name = "all"
        self.msg_history = collections.deque(maxlen=_HISTORY)
        self.repl_history = collections.deque(maxlen=_HISTORY)

    
    
#### a couple of useful utility functions for writers of substitute methods


def split_on_whitespace(text):
    """ Because this has to work in Py 2.6, and re.split doesn't do UNICODE
    in 2.6.  Return text broken into words by whitespace. """
    matches = [m for m in re.finditer("[\S]+", text, flags=re.UNICODE)]
    results = [text[m.span()[0]:m.span()[1]] for m in matches]
    return results

def kill_non_alphanumerics(text):
    """remove any non-alphanumeric characters from a string and return the
    result. re.sub doesn't do UNICODE in python 2.6.

    """
    matches = [m for m in re.finditer("[\w]+", text, flags=re.UNICODE)]
    result = "".join([text[m.span()[0]:m.span()[1]] for m in matches])
    return result        
            


