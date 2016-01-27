# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Chatbot Reply Generator

"""
from __future__ import print_function
from __future__ import unicode_literals

import logging
import re

from chatbot_reply.six import get_method_self, text_type

from chatbot_reply.rules import RulesDB
from chatbot_reply.script import Script, UserInfo
from chatbot_reply.script import kill_non_alphanumerics, split_on_whitespace
from chatbot_reply.exceptions import *

#todo use imp thread locking, though this thing is totally not thread-safe
#should case sensitivity be an option?
#If we decide to rerun setup methods, need to reparse alternates

log = logging.getLogger(__name__)

class ChatbotEngine(object):
    """ Python Chatbot Reply Generator

    Loads pattern/reply rules, using a simplified regular expression grammar
    for the patterns, and decorated Python methods for the rules. Maintains
    rules, a variable dictionary for the chatbot's internal state plus one
    for each user conversing with the chatbot. Matches user input to its 
    database of patterns to select a reply rule, which may recursively reference
    other reply patterns and rules.

    Public instance methods:
      load_script_directory: loads rules from a directory of python files
      clear_rules: empties the rule database
      reply: given a message, find the best matching rule, run it, and return
              the reply
    """

    def __init__(self, depth=50):
        """Initialize a new ChatbotEngine.

        Keyword argument: 
        depth -- Recursion depth limit for replies that reference other replies 
        """
        self._depth_limit = depth

        self._botvars = {}
        self._variables = {"b" : self._botvars,
                           "u" : None}
        
        self._users = {} # will contain UserInfo objects
        log.debug("Chatbot instance created.")
        self.clear_rules()

    def clear_rules(self):
        """ Empty the rules database """
        log.debug("Rules database cleared")
        self.rules_db = RulesDB()

    def load_script_directory(self, directory):
        """ Load rules from *.py in a directory """
        self.rules_db.load_script_directory(directory, self._botvars)

    ##### Reading scripts and building the database of rules #####
    
    def reply(self, user, user_dict, message):
        """ For the current topic, find the best matching rule for the message.
        Recurse as necessary if the first rule returns references to other 
        rules. This method does setup and cleanup and passes the actual work
        to self._reply()

        Arguments:
        user -- any hashable value, used to identify to whom we are speaking
        user_dict -- dictionary of information about the user, to be passed
                        to rule methods
        message -- string (not bytestring!) to reply to

        Return value: string returned by rule(s)

        Exceptions:
        RecursionTooDeepError -- if recursion goes over depth limit passed
            to __init__
        """
        if not isinstance(message, text_type):
            raise TypeError("message argument must be string, not bytestring")

        self.rules_db.sort_rules()
        
        log.debug('Asked to reply to: "{0}" from {1}'.format(message, user))
        self._setup_user(user, user_dict)

        try:
            reply = self._reply(user, message, 0)
        except RecursionTooDeepError as e:
            e.args = ('Could not find reply to "{0}", due to rules '
                      "referencing other rules too many "
                      "times".format(message),)
            raise
        self._remember(user, message, reply)
        return reply

    def _reply(self, user, message, depth):
        """ Recursively construct replies """
        if depth > self._depth_limit:
            raise RecursionTooDeepError
        
        log.debug('Searching for rule matching "{0}", depth == {1}'.format(
            message, depth))
        userinfo = self._users[user]
        topic = userinfo.topic_name
        target = Target(message, self.rules_db.topics[topic].substitutions)
        reply = ""
        
        for rule in self.rules_db.topics[topic].sortedrules:
            m = rule.match(target, userinfo.repl_history,
                           self._variables)
            if m is not None:
                reply = self._reply_from_rule(rule, m, userinfo)
                self._check_for_topic_change(user, rule, topic,
                                             userinfo.topic_name)
                break

        reply = self._recursively_expand_reply(user, reply, depth)
        if not reply:
            log.debug("Empty reply generated")
        else:
            log.debug("Generated reply: " + reply)
        return reply

    def _reply_from_rule(self, rule, rule_match, userinfo):
        """ Given a rule and the results from a successful match of the rule's
        pattern, call the rule method and return the results. 
        """
        log.debug("Found match, rule {0}".format(rule.rulename))

        inst = get_method_self(rule.method)
        inst.userinfo = userinfo
        inst.match = rule_match.dict
        reply = rule.method()
        if not isinstance(reply, text_type):
            raise TypeError("Rule {0} returned something other than a "
                            "string.".format(rule.rulename))
        log.debug('Rule {0} returned "{1}"'.format(rule.rulename, reply))
        return reply

    def _recursively_expand_reply(self, user, reply, depth):
        """ Given a reply string from a rule, look for references to other
        rules enclosed within < > and recursively call _reply to get responses,
        and substitute those into the original string. Evaluates from left
        to right. Doesn't care if you match the <>'s or not.
        """
        matches = [m for m in re.finditer("<(.*?)>", reply, flags=re.UNICODE)]
        if matches:
            log.debug("Rule returned: " + reply)
        sub_replies = [self._reply(user, m.groups()[0], depth + 1)
                       for m in matches]
        zipper = list(zip(matches, sub_replies))
        zipper.reverse()
        for m, sub_reply in zipper:
            reply = reply[:m.start()] + sub_reply + reply[m.end():]
        return reply    

    def _check_for_topic_change(self, user, rule, old_topic, new_topic):
        """ Given a rule, and the topic set before and after its execution,
        make sure the change is legit and do appropriate debug logging. 
        """
        if old_topic != new_topic:
            if new_topic not in self.rules_db.topics:
                log.warning("Rule {0} changed to empty topic {1}, "
                          "returning to 'all'".format(rule.rulename, new_topic))
                new_topic = "all"
            log.debug("User {0} now in topic {1}".format(user, new_topic))

        self._users[user].topic_name = new_topic

    def _setup_user(self, user, user_dict):
        """ Set up the Script class to process a message from a user. If the
        user is new to us, create the UserInfo object for them, and call
        the setup_user method of all the script instances so they can
        initialize user variables.
        """
        new = (user not in self._users)
        if new:
            self._users[user] = UserInfo(user_dict)

        self._variables["u"] = self._users[user].vars
        topic = self._users[user].topic_name
        if topic not in self.rules_db.topics:
            log.warning("User {0} is in empty topic {1}, "
                      "returning to 'all'".format(user, topic))
            topic = self._users[user].topic_name = "all"

        if new:
            log.debug("New user, running all scripts' setup_user methods")
            for inst in self.rules_db.script_instances:
                inst.userinfo = self._users[user]
                inst.setup_user(user)
            
    def _remember(self, user, message, reply):
        """ Save recent messages and replies, per user """
        user_info = self._users[user]
        topic_name = user_info.topic_name
        user_info.msg_history.appendleft(message)
        user_info.repl_history.appendleft(
            Target(reply, self.rules_db.topics[topic_name].substitutions))
        
    
class Target(object):
    """ A message prepared to be a match target.

    Public instance variables:
    raw_text: the string passed to the constructor
    raw_words: a list of words of the same string, split on whitespace
    tokenized_words: a list of lists, one for each word in orig_words
        after doing substitutions (see below), making them lower case, 
        and removing all remaining non-alphanumeric characters.
    normalized: tokenized_words, joined back together by single spaces

    """
    def __init__(self, text, substitutions=[]):
        """ Create a match target from a string.
            - Break it into a list of words on whitespace and save the originals
            - Run substitutions
            - lowercase everything
            - Kill remaining non-alphanumeric characters

        Parameters:
            text - the string to process
            substitutions - a list of (name, func) tuples. Each function will
                be passed the original input string and a list containing lists
                of words derived from the original input string. Each function
                must return a list of lists of words and the outer list must be
                the same length as the input. The functions in the substitutions
                list will all be called, using the output of one as the input of
                the next.

        Examples, showing text and the results placed in raw_words,
        tokenized_words and normalized.

        I'm tired today! ==>  ["I'm", "tired", "today!"],
                              [["im"], ["tired"], ["today"]]
                              "im tired today"
        Wazzup! :) ==> ["Wazzup!", ":)"]
                       [["wazzup"], [[""]])
                       "wazzup"

        Substitutor methods may change the number of words in the sublists of 
        tokenized_words, but they should not change the number of sublists in
        tokenized_words, or a TypeError will be raised.

        For example, a substitutor that expands contractions might do this:

        I'm tired today! ==>  ["I'm", "tired", "today!"],
                              [["i am"], ["tired"], ["today"]]
                              "i am tired today"

        The reason for the nested lists in tokenized_words is so that the code
        which generates matches can map text matched  in the normalized 
        string back to the original string, so for example if you match
        "I'm tired today!" to the pattern "i am tired _*", the match dict
        entry for "raw_match0" will contain "today!"
        """
        self.raw_text = text
        self.raw_words = split_on_whitespace(text)
        sub_words = self._do_substitutions(substitutions)

        self.tokenized_words = [[kill_non_alphanumerics(word.lower())
                        for word in wl] for wl in sub_words]
        self.normalized = " ".join(
                                [" ".join(wl) for wl in self.tokenized_words])
        log.debug('Normalized message to "{0}"'.format(self.normalized))

    def _do_substitutions(self, substitutions):
        """Check a word against the substitutions dictionary. If the word is
        not found, return it wrapped in a list. Otherwise return the
        value from the dictionary as a list of words.
        """
        results = [[word] for word in self.raw_words]
        length = len(results)
        for name, func in substitutions:
            try:
                clearer_error_message = ""
                results = func(self.raw_text, results)
                clearer_error_message = " return value of"
                log.debug("{0} returned {1}".format(name, results))
                if len(results) != length:
                    raise TypeError("Returned list must be same length as "
                                    "passed list")
            except Exception as e:
                msg = (" in{0} {1}".format(clearer_error_message, name))
                e.args = (e.args[0] + msg,) + e.args[1:]
                raise
                
        return results
