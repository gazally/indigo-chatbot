# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
""" chatbot_reply.rules, loads rules from python files
"""
from __future__ import print_function
from __future__ import unicode_literals

import bisect
import imp
import inspect
import logging
import os

from chatbot_reply.constants import _PREFIX
from chatbot_reply.exceptions import *
from chatbot_reply.patterns import Pattern
from chatbot_reply.script import Script, ScriptRegistrar

log = logging.getLogger(__name__)

class RulesDB(object):
    """ Rules Database object. Reads directories of python files, and 
    instantiates any subclasses of Script found therein and stores rules,
    patterns and methods in Topic objects. 
   
    Public methods --
    load_script_directory: Load python files from a directory into the
        database
    clear_rules: Empty the rules database

    Public instance variables --
    topics: dictionary of topic names (as found in Script subclasses) and
        Topic objects built from those subclasses
    script_instances: List containing one instance of each Script subclass
        found, except for those with their topic set to None
    """
    def __init__(self):
        """ Create a new empty RulesDB object """
        self.clear_rules()

    def clear_rules(self):
        """ Make a fresh new empty rules database. """
        self.topics = {}
        self.script_instances = []
        self._new_topic("all")

    def _new_topic(self, topic):
        """ Add a new topic to the rules database. """
        self.topics[topic] = Topic()
 
    def load_script_directory(self, directory, botvars):
        """Iterate through the .py files in a directory, and import all of
        them. Then look for subclasses of Script and search them for
        rules, and load those into self.topics.
        botvars is a dictionary that loaded scripts can use to initialize
        chatbot state

        """
        self.rules_sorted = False
        ScriptRegistrar.clear()
        
        for item in os.listdir(directory):
            if item.lower().endswith(".py"):
                log.debug("Importing " + item)
                filename = os.path.join(directory, item)
                self._import(filename)

        for cls in ScriptRegistrar.registry:
            log.debug("Loading scripts from " + cls.__name__)
            self._add_to_rulesdb(cls, botvars)

        if sum([len(t.rules) for k, t in self.topics.items()]) == 0:
            raise NoRulesFoundError(
                "No rules were found in {0}/*.py".format(directory))
                
    def _import(self, filename):
        """Import a python module, given the filename, but to avoid creating
        namespace conflicts give the module a name consisting of
        _PREFIX + filename (minus any extension). 
        """
        global _PREFIX
        path, name = os.path.split(filename)
        name, ext = os.path.splitext(name)

        log.debug("Reading " + filename)
        modname = _PREFIX + name
        file, filename, data = imp.find_module(name, [path])
        module = imp.load_module(modname, file, filename, data)
        return module

    def _add_to_rulesdb(self, script_class, botvars):
        """Given a subclass of Script, create an instance of it.  If it's
        topic is set to None, ignore it, otherwise search its
        attributes for methods that begin with "rule" or "substitute"
        and add those to the topic database.

        """
        instance = script_class()
        topic = instance.topic
        if topic == None: #this is the way to define a script superclass
            return
        if topic not in self.topics:
            self._new_topic(topic)

        instance.botvars = botvars
        instance.setup()
        self.script_instances.append(instance)
        
        rules, substitutions = self._load_script_methods(instance)
        self.topics[topic].add_rules(rules)
        self.topics[topic].add_substitutions(substitutions)

    def _load_script_methods(self, instance):
        """Given an instance of a subclass of Script, find all of its methods
        which begin with one of our keywords and add them to the rules
        database for the topic of the script instance.

        If the instance defines an alternates dictionary, substitute
        those into the patterns of the rules.

        """
        script_class_name = (instance.__module__[len(_PREFIX):] + "." +
                             instance.__class__.__name__)
        alternates = {}
        if hasattr(instance, "alternates"):
            alternates = self._parse_alternates(instance.alternates,
                                                script_class_name)
        rules = []
        substitutes = []
        for attribute in dir(instance):
            if attribute.startswith('rule'):
                rule = self._load_rule(script_class_name, instance,
                                       attribute, alternates)
                rules.append(rule)
            elif attribute.startswith('substitute'):
                sub = self._load_substitution(script_class_name,
                                              instance, attribute)
                substitutes.append(sub)
        return rules, substitutes
   
    def _parse_alternates(self, alternates, script_class_name):
        """Construct Pattern objects for all the values in the alternates
        instance variable (hopefully a dictionary) of a Script
        subclass, and construct a dictionary of the keys from
        alternates and the pattern object. Wrap that in another
        dictionary keyed by 'a' so it can be used by %a:varname in
        other patterns.

        """
        valid = {}
        k = ""
        try:
            for k, v in alternates.items():
                valid[k] = Pattern(v, simple=True).formatted_pattern
        except Exception as e:
            msg = " in alternates"
            if k:
                msg += '["{0}"]'.format(k)
            msg += " of {0}".format(script_class_name)
            e.args = (e.args[0] + msg,) + e.args[1:]
            raise
        return {"a":valid}

    def _load_rule(self, script_class_name, instance, attribute,
                      alternates):
        """ Given an instance of a class derived from Script and
        a callable attribute, check that it is declared correctly, 
        and then construct and return a Rule object.
        """
        method = getattr(instance, attribute)
        rulename = script_class_name + "." + attribute

        argspec = get_rule_method_spec(rulename, method)

        raw_pattern, raw_previous, weight = argspec.defaults
        return Rule(raw_pattern, raw_previous, weight, alternates,
                    method, rulename)

    def _load_substitution(self, script_class_name, instance, attribute):
        """ Given an instance of a class derived from Script and
        a callable attribute, check that it is declared correctly, 
        and then return it as a tuple with its full name 
        """
        name = script_class_name + "." + attribute
        method = getattr(instance, attribute)
        check_substitution_method_spec(name, method)
        return (name, method)

    def sort_rules(self):
        """ Sort the rules for each topic """
        updated = False
        for topic in self.topics.values():
            if not topic.rules_are_sorted:
                updated = True
            topic.sort_rules()
        if updated:
            self._log_all_rules()

    def _log_all_rules(self):
        """ Print the rules lists to debug ouput """
        log.debug("-"*20 + "Sorted rules" + "-"*20)
        for n, t in self.topics.items():
            log.debug("Topic: {0}".format(n))
            t.log_sorted_rules()
        log.debug("-"*52)
    

def get_rule_method_spec(name, method):
    """ Check that the passed argument spec matches what we expect the
    @rule decorator in scripts.py to do. Raises TypeError
    if a problem is found. If all is good, return the argspec
    (see inspect.getargspec)
    """
    if not hasattr(method, '__call__'):
        raise TypeError(
            "{0} begins with 'rule' but is not callable.".format(
                name))
    argspec = inspect.getargspec(method)
    if (len(argspec.args) != 4 or
        " ".join(argspec.args) != "self pattern previous_reply weight" or
        argspec.varargs is not None or
        argspec.keywords is not None or
        len(argspec.defaults) != 3):
        raise TypeError("{0} was not decorated by @rule "
                 "or it has the wrong number of arguments.".format(name))
    return argspec


def check_substitution_method_spec(name, method):
    """ Check that the passed argument spec matches what we expect a
    substitute method in a subclass of Script to look like.
    Raises TypeError if a problem is found. If all is good, return the argspec
    (see inspect.getargspec)
    """
    if not hasattr(method, '__call__'):
        raise TypeError(
            "{0} begins with 'substitute' but is not callable.".format(
                name))
    argspec = inspect.getargspec(method)
    if (len(argspec.args) != 3 or
        argspec.varargs is not None or
        argspec.keywords is not None):
        raise TypeError("{0} was not decorated by @rule "
                 "or it has the wrong number of arguments.".format(name))
    return argspec
    

class Topic(object):
    """ Topic object. Stores Rule objects and references to substitution
    methods for each topic. 
    Public instance variables:
        rules : dictionary of Rule objects, indexed by tuples containing
                the two formatted pattern strings of the rule
        sortedrules : List of all the Rule objects from the dictionary,
                in reverse sorted order by score
        substitutions : List of substitution methods, in no particular
                order. RulesDB puts tuples in here, (name, method)
    """
    def __init__(self):
        """ Create a new empty Topic object. """
        self.rules = {}
        self.rules_are_sorted = True
        self.sortedrules = []
        self.substitutions = []

    def add_rules(self, rules):
        """ Add rules from a list to the rule dictionary. If there is already
        a rule in there with the same two patterns, print a warning message
        and ignore it.
        """
        self.rules_are_sorted = False
        for rule in rules:
            tup = (rule.pattern.formatted_pattern,
                   rule.previous.formatted_pattern)
            if tup in self.rules:
                existing_rule = self.rules[tup]
                log.warning("Ignoring rule {0} because its patterns are "
                          "duplicates of the patterns of the rule "
                          "{1} ".format(rule.rulename, existing_rule.rulename))
            else:
                self.rules[tup] = rule
                log.debug('Loaded pattern "{0[0]}", previous="{0[1]}", ' 
                          'weight={1}, method={2}'.format(tup, rule.weight,
                                                           rule.rulename))
    def add_substitutions(self, substitutions):
        """ Add substitution methods to the substitutions list """
        self.substitutions.extend(substitutions)

    def sort_rules(self):
        """ If sorted_rules is out of date, update it. """
        if self.rules_are_sorted:
            return
        self.sortedrules = sorted(self.rules.values(), reverse=True)
        self.rules_are_sorted = True

    def log_sorted_rules(self):
        """ Print sorted rules to logging output """
        for r in self.sortedrules:
            log.debug('({2}) "{0}"/"{1}"'.format(
                r.pattern.formatted_pattern,
                r.previous.formatted_pattern, r.weight))
        
        
class Rule(object):
    """ Pattern matching and response rule.

    Describes one method decorated by @rule. Parses
    the simplified regular expression strings, raising PatternError
    if there is an error. Can match the pattern and previous_pattern
    against tokenized input (a Target) and return a Match object.

    Public instance variables:
    pattern - the Pattern object to match against the current message
    previous - the Pattern object to match against the previous reply
    weight - the weight, given to @rule
    method - a reference to the decorated method
    rulename - modulename.classname.methodname, for error messages

    Public methods:
    match - given current message and reply history, return a Match
            object if the patterns match or None if they don't
    full set of comparison operators - to enable sorting first by weight then 
            score of the two patterns
    """
    def __init__(self, raw_pattern, raw_previous, weight, alternates,
                 method, rulename):
        """ Create a new Rule object based on information supplied to the
        @rule decorator. Arguments:
        raw_pattern - simplified regular expression string supplied to @rule
        raw_previous - simplified regular expression string supplied to @rule
        weight -  weight supplied to @rule
        alternates - dictionary of variable names and values that can
                   be substituted in the patterns
        method - reference to method decorated by @rule
        rulename - modulename.classname.methodname, used to make better
                 error messages

        Raises PatternError, PatternVariableNotFoundError, 
               PatternVariableValueError
        """
        try:
            previous = ""
            if not raw_pattern:
                raise PatternError("Empty string found")
            self.pattern = Pattern(raw_pattern, alternates)
            previous = "previous "
            self.previous = Pattern(raw_previous, alternates)
        except (TypeError, PatternError, PatternVariableValueError,\
               PatternVariableNotFoundError) as e: 
            msg = " in {0}pattern of {1}".format(previous, rulename)
            e.args = (e.args[0] + msg,) + e.args[1:]
            raise

        self.weight = weight
        self.method = method
        self.rulename = rulename

    def match(self, target, history, variables):
        """ Return a Match object if the targets match the patterns
        for this rule, or None if they don't.
        Arguments:
            target - a Target object for the user's message
            history - a deque object containing Targets for previous
                      replies
            variables - User and Bot variables for the PatternParser
                      to substitute into the patterns
        """
        m = self.pattern.match(target.normalized, variables)
        if m is None:
            return None
        mp = None
        reply_target = None

        if self.previous:
            if not history:
                return None
            reply_target = history[0]
            mp = self.previous.match(reply_target.normalized, variables)
            if mp is None:
                return None
        return Match(m, mp, target, reply_target)

    def __lt__(self, other):
        """ Full set of comparison operators. The weight passed to @rule
        is the most significant, followed by the complexity of the pattern
        and the complexity of the previous pattern.
        """
        return (self.weight < other.weight
                or
                (self.weight == other.weight
                 and self.pattern.score < other.pattern.score)
                or
                (self.weight == other.weight
                 and self.pattern.score == other.pattern.score
                 and self.previous.score < other.previous.score))
                
    def __eq__(self, other):
        return (self.weight == other.weight
                and self.pattern.score == other.pattern.score
                and self.previous.score == other.previous.score)

    def __gt__(self, other):
        return not (self == other or self < other)
    def __le__(self, other):
        return self < other or self == other
    def __ge__(self, other):
        return self > other or self == other
    def __ne__(self, other):
        return not self == other


class Match(object):
    """ For a match between the two patterns of a @rule and a user message
    and previous reply, construct a dictionary of values for the parts of the
    match the @rule wanted to use.

    Public instance variable:
        dict -- dictionary of matched text

    The dictionary keys will be:
    match0..matchN         -- memorized matches in the tokenized text of 
                              the message
    reply_match0...reply_matchN  -- matches in the previous reply's tokenized text
    raw_match0..rawN       -- memorized matches of the untokenized text of the
                              message, all capitals and punctuation included, 
                              but whitespace normalized.
    reply_raw_match0 -- reply_rawmatchN -- memorized matches of the untokenized 
                              text of the previous reply
    """
    def __init__(self, m_pattern, m_previous, target, previous_target):
        """ Construct a Match object given two regular expression match objects,
        which if constructed by ParsedPattern will have populated the groupdict
        with keys match0, match1, ... matchN, as well as the Target objects 
        they were matched to. 
        """
        self.dict = {}
        self._add_matches(m_pattern, target, "")
        if m_previous is not None:
            self._add_matches(m_previous, previous_target, "reply_")

    def _add_matches(self, m, target, prefix):
        """ Prefix all keys from m.groupdict() with the prefix argument, and 
        add them to self.dict. Then use the fact that the tokenized_words and
        raw_words lists in target are the same length to find the chunk of raw
        text that each match corresponds to, and add those to the dictionary
        with "raw_" prefixed to their keys.
        Arguments:
            m - a match object from a re function
            target - a Target object
            prefix - a prefix string to add to key names

        """
        offsets = []
        offset = 0
        for wl in target.tokenized_words:
            offsets.append(offset)
            offset += len(" ".join(wl)) + 1
            
        for k, v in m.groupdict().items():
            self.dict[prefix + k] = v
            start, end = m.span(k)
            i_start = bisect.bisect_left(offsets, start)
            i_end = bisect.bisect(offsets, end)
            self.dict["raw_" + prefix + k] = " ".join(target.raw_words[i_start:
                                                                       i_end])
