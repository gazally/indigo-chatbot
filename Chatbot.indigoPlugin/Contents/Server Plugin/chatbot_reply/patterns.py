# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
""" Pattern Parsing for chatbot_reply. Translates simplified regular
    expressions, called "patterns" herein, into real regular
    expressions. The strings that the real regular expressions will
    be matched against will be called "targets".

    Components of a pattern:

    Wildcards:
        *       match one or more words containing alphanumerics and
                the underscore
        @       match one or more words containing only alphabetic 
                characters, not including underscore
        $       match one or more numbers containing only digits
 
             All three wildcard characters by themselves will match one or more 
        words/numbers. They may all be modified by numbers representing a 
        minimum and/or maximum number of words to match:

        *2~     two or more
        *~10    one to ten
        *3~5    three to five

        If you want to match zero to two words, do this: [*~2]. See Optionals 
    below.

    Spaces:
        One or more whitespace characters in the pattern match one or more 
        whitespace characters in the target.

    Words:
        Words to be matched may contain alphanumerics and the underscore,
        but may not begin with an underscore.

    Variables:
        %a:varname
        %b:varname
        %u:varname

        During regular expression construction, ParseTree.regex() will
        look up variable values in 
        a dictionary passed into it and substitute them into the regular
        expression it is constructing. Variable names may contain 
        alphanumerics including the underscore but may not begin with 
        a number or an underscore. Case in variable names is ignored.
        Variable values must be unicode strings, and will be parsed
        as even more simplified regular expression patterns, which may only
        contain Spaces, Words, Optionals, Alternates and Pipes.

    Optionals, Alternates and Pipes:
        Any of the above expressions may be grouped together within 
        parentheses or square brackets, or a list of expressions separated
        by "|" characters may be placed within parentheses or square brackets.
        Text within parentheses is required and within square brackets is 
        optional. So:
 
        (this|that)   will match either the string "this" or "that"
        [this|that]   will match either the empty string, "this", or "that"
        (thing [one|two])  will match "thing", "thing one" and "thing two"

    Memorization:
        Any wildcard, variable, or optional or alternate expression preceded
        by an underscore will be made into a named group in the regular 
        expression. They will be given the names "match0" through "matchn"
        in the order they are encountered in the pattern from left to right.
        For example:

        my name is _@ [_@]   will match "My name is Fred" and 
                             "My name is Fred Flintstone". The re.match
                             groupdict will contain "match0" and "match1",
                             and m.groupdict()["match1"] might be None.


"""
from __future__ import print_function
from __future__ import unicode_literals

import inspect
import itertools
import re

from chatbot_reply.six import text_type, next
from chatbot_reply.exceptions import *

# TODO - could pass in a string such as "uba" with variable classes to create
# TODO - make a parsetree class, use that instead of a list and put Token's two
# static methods in it

_WILDCARD_SCORE = -2
_LIMITED_WILDCARD_SCORE = -1
_SPACE_SCORE = 0
_WORD_SCORE = 10
_VARIABLE_SCORE = 10



class StopScanLoop(StopIteration):
    pass

class Token(object):
    """ Parent class of all the types of token that can be found by the parser. 
    The only thing this does is make isinstance(obj, Token) work.
    """
    pass

class Wild(Token):
    """ Parse and represent wildcards. Instance variables:
    wild - the wildcard character, '@', '#' or '*'
    minimum - the minimum number of repetitions to match. Is a positive integer
        stored in string format.
    maximum - The empty string, if the user did not specify a maximum, or the
        maximum that the user did specify. Is a positive integer stored
        as a string.
    """
    regexc = re.compile(r".(\d*)(~?)(\d*)", re.UNICODE)
    wildcards = {"@" : r"[^_\d\W]+",
                 "#" : r"\d+",
                 "*" : r"\w+"}
    def __init__(self, tokens, text, terminator):
        self.wild = text[0]
        self.minimum = "1"
        self.maximum = ""

        m = re.match(self.__class__.regexc, text)
        groups = m.groups()
        if groups[0]:
            self.minimum = self.maximum = groups[0]
        if groups[1]: #they gave us a ~
            self.maximum = groups[2]
        self.minimum = text_type(max(int(self.minimum), 1))
        if self.maximum:
            self.maximum = text_type(max(int(self.maximum), int(self.minimum)))

    def add_to_parsetree(self, parsetree):
        parsetree.contents.append(self)

    def format(self):
        if self.minimum == self.maximum:
            return self.wild + self.minimum
        if int(self.minimum) == 1:
            if self.maximum == "":
                return self.wild
            else:
                return self.wild + "~" + self.maximum
        else:
            return self.wild + self.minimum + "~" + self.maximum

    def score(self):
        if self.wild == "*":
            return _WILDCARD_SCORE
        else:
            return _LIMITED_WILDCARD_SCORE

    def regex(self, variables, counter):
        wildcard = self.wildcards[self.wild]
        if self.maximum == "1":
            return wildcard + r"\b"
        else:
            # we are going to try to match n-1 repetitions of the pattern
            # followed by a space plus 1 rep of the pattern followed by a
            # \b
            min_str = text_type(int(self.minimum) - 1)
            max_str = self.maximum
            if max_str != "":
                max_str = text_type(int(self.maximum) - 1)
            return (r"(" + wildcard + r"\s)" +
                    r"{" + min_str + r"," + max_str + r"}?"
                    + wildcard + r"\b")

class Word(Token):
    """ Parse and represent words. Instance variables:
    text - one or multiple words separated by spaces. String.

    """
    def __init__(self, tokens, text, terminator):
        self.text = text

    def add_to_parsetree(self, parsetree):
        #if the last two things are a word and a space, merge them
        if (len(parsetree.contents) > 1 and
            isinstance(parsetree.contents[-1], Space) and
            isinstance(parsetree.contents[-2], Word)):
                parsetree.contents[-2].text += (" " + self.text)
                parsetree.contents.pop()
        else:
            parsetree.contents.append(self)

    def format(self):
        return self.text

    def score(self):
        return len(self.text.split(" ")) * _WORD_SCORE

    def regex(self, variables, counter):
        return self.text + r"\b"

class Memo(Token):
    """ Parse and represent memorization. Instance variables:
    item - a Token to be placed in a named group when the regular expression
        is generated
    """
    def __init__(self, tokens, text, terminator):
        self.item = ParsedPattern(tokens, just_one=True).contents[0]

    def add_to_parsetree(self, parsetree):
        parsetree.contents.append(self)

    def format(self):
        return "_" + self.item.format()

    def score(self):
        return self.item.score()

    def regex(self, variables, counter):
        return "(?P<match{0}>{1})".format(next(counter),
                                          self.item.regex(variables, counter))

class Space(Token):
    """ Parse and represent whitespace.
    """
    def __init__(self, tokens, text, terminator):
        pass

    def add_to_parsetree(self, parsetree):
        # leading spaces (for example within a group) are ignored,
        # as are multiple spaces in a row
        if (parsetree.contents
            and isinstance(parsetree.contents[-1], Token)
            and not isinstance(parsetree.contents[-1], Space)):
            parsetree.contents.append(self)

    def format(self):
        return " "

    def score(self):
        return _SPACE_SCORE

    def regex(self, variables, counter):
        return r"\s?"

class Variable(Token):
    """ Parse and represent variables. Instance variables:
    var_id - the one character variable type between % and : in the pattern
    var_name - variable name following : in the pattern

    """
    def __init__(self, tokens, text, terminator):
        self.var_id = text[1]
        self.var_name = ParsedPattern(tokens, just_one=True).contents[0].text

    def add_to_parsetree(self, parsetree):
        parsetree.contents.append(self)

    def format(self):
        return "%" + self.var_id + ":" + self.var_name

    def score(self):
        return _VARIABLE_SCORE

    def regex(self, variables, counter):
        if (self.var_id not in variables or
            self.var_name not in variables[self.var_id]):
            raise PatternVariableNotFoundError(
                "Chatbot variable %{0}:{1} is undefined".format(self.var_id,
                                                             self.var_name))
        value = variables[self.var_id][self.var_name]
        if not isinstance(value, text_type):
            raise PatternVariableValueError(
                "Value in pattern variable %{0}:{1} could not be used "
                "because it is not a unicode string.".format(
                    self.var_id, self.var_name))
        value = value.lower()
        try:
            parse_tree = ParsedPattern(value, simple=True)
            regex = parse_tree.regex(None)
        except PatternError as e:
            msg = " in variable %{0}:{1}".format(self.var_id, self.var_name)
            e.args = (e.args[0] + msg,) + e.args[1:]
            raise

        return regex + r"\b"

class Optional(Token):
    """ Parse and represent optional parts of a pattern. Instance variables:
    choices - a ParseTree containing ParseTrees, one for each sub-pattern
    separated by |'s within the square brackets.
    """
    def __init__(self, tokens, text, terminator):
        self.choices = ParsedPattern(tokens, terminator="]")

    def add_to_parsetree(self, parsetree):
        parsetree.contents.append(self)

    def format(self):
        output = [chunk.format() for chunk in self.choices.contents]
        return "[" + "|".join(output) + "]"

    def score(self):
        return max([chunk.score() for chunk in self.choices.contents])

    def regex(self, variables, counter):
        output = [chunk.regex(variables, counter)
                  for chunk in self.choices.contents]
        return "(" + "|".join(output) + ")?"

class Group(Token):
    """ Parse and represent alternative parts of a pattern. Instance variables:
    choices - a ParseTree containing ParseTrees, one for each sub-pattern
    separated by |'s within the parentheses.
    """
    def __init__(self, tokens, text, terminator):
        self.choices = ParsedPattern(tokens, terminator=")")

    def add_to_parsetree(self, parsetree):
        parsetree.contents.append(self)

    def format(self):
        output = [chunk.format() for chunk in self.choices.contents]
        return "(" + "|".join(output) + ")"

    def score(self):
        return max([chunk.score() for chunk in self.choices.contents])

    def regex(self, variables, counter):
        output = [chunk.regex(variables, counter)
                  for chunk in self.choices.contents]
        return "(" + "|".join(output) + ")"

class Terminator(Token):
    """ Parse the terminator characters ) and ]
    """
    def __init__(self, tokens, text, terminator):
        if terminator != text:
            raise PatternError("Found an unexpected {0}".format(text))

    def add_to_parsetree(self, parsetree):
        parsetree.remove_trailing_space()
        parsetree.group_tokens()
        raise StopScanLoop

class Pipe(Token):
    """ Parse the separator character |
    """
    def __init__(self, tokens, text, terminator):
        if terminator != ")" and terminator != "]":
            raise PatternError("Alternatives operator | must be "
                               "used within parentheses or square "
                               "brackets")

    def add_to_parsetree(self, parsetree):
        parsetree.remove_trailing_space()
        parsetree.group_tokens()

class Invalid(Token):
    """ Throw a PatternError, used when the tokenizer finds an unknown 
    character.
    """
    def __init__(self, tokens, text, terminator):
        raise PatternError("Found an unexpected character {0}".format(text))
        
class PatternTokenizer(object):
    """ Pattern Tokenizer class for simplified regular expression patterns.
    The class instance has no public instance variables, but builds and contains
    compiled regular expressions to use in the tokenizing process along with a
    dispatch table listing which subclass of Token to call.

    Public instance method:
    tokens - return a generator which will yield (token_subclass, match_text)
             for each token substring found 
    """
    
    def __init__(self, simple=False):
        """ Build and re.compile the machinery that makes PatternParser work.
        if simple is True, limit the tokens that will be matched to Word,
        Space, Optional, Group, Pipe and Terminator and send everything else
        to Invalid.
        """
        regexes = []
        self._token_classes = []

        token_definitions = [
            (False, r"([*#@]\d*~?\d*)([])|\s]|$)", Wild,       True),
            (False, r"(_)([*#@%([])",              Memo,       True),
            (True,  r"([^_\W][\w-]*)([])|\s]|$)",  Word,       True),
            (True,  r"([\s]+)",                    Space,      False),
            (False, r"(%u:)([^_\d\W][\w]*)",       Variable,   True),
            (False, r"(%b:)([^_\d\W][\w]*)",       Variable,   True),
            (False, r"(%a:)([^_\d\W][\w]*)",       Variable,   True),
            (True,  r"(\[)",                       Optional,   False),
            (True,  r"(\])([])|\s]|$)",            Terminator, True),
            (True,  r"(\()",                       Group,      False),
            (True,  r"(\))([])|\s]|$)",            Terminator, True),
            (True,  r"(\|)",                       Pipe,       False),
            (True,  r"(.)",                        Invalid,    False)
            ]

        # In the list of regular expressions above, several have two
        # groups. The first group is the token to match, and the second
        # does lookahead. If the lookahead match fails, then the match
        # will fall through to the last regular expression which will
        # always match and then call Invalid.

        # If both a token and its lookahead match, the tokens() generator
        # will get the index for the lookahead group and find None in
        # the token_classes list. But the one we want in that case is
        # always the one before so it just subtracts 1 from the index.

        for simple_token, regex, token_class, lookahead in token_definitions:
            if simple_token or not simple:
                regexes.append(regex)
                self._token_classes.append(token_class)
                if lookahead:
                    self._token_classes.append(None)
                
        self._regexc = re.compile("|".join(regexes), re.UNICODE)
            
    def tokens(self, string):
        """ Returns a generator expression which will yield (token_class, text)
        for each matching regular expression that it finds in the string.
        Raises TypeError if not given a unicode argument.
        """
        if not isinstance(string, text_type):
            raise TypeError("Argument must be unicode string")
        while True:
            m = self._regexc.match(string)
            if m is None:
                return
            index = m.lastindex
            token_class = self._token_classes[index - 1]
            if token_class is None:
                index = index - 1
            yield self._token_classes[index - 1], m.group(index)
            string = string[m.end(index):]


class ParsedPattern(object):
    pp = PatternTokenizer(simple=False)
    pp_simple = PatternTokenizer(simple=True)
    
    def __init__(self, *args, **kwargs):
        """ Construct a ParsedPattern object. Since ParsedPattern objects can
        contain other ParsedPattern objects, this can be called recursively,
        therefore it needs to do different things depending on how it is called.

        The external entry point, to create a new ParsedPattern from a 
        pattern string:
            pp = ParsedPattern(pattern)

        Or if you want to limit it to the simple tokens:
            pp = ParsedPattern(pattern, simple=True)

        The following variations are used during the recursion process:
            To create an empty ParsedPattern:
                pp = ParsedPattern() 

            To create a new ParsedPattern and fill with a list of tokens:
                pp = ParsedPattern(token_list)

            To create a new ParsedPattern from a token generator expression
                pp = ParsedPattern(token_gen, just_one=False, terminator=None)

                In this last version, setting just_one to True causes it to 
                parse just one token and then return. Setting terminator to ")"
                or "]" causes it to return when it encounters that character.

        """
        self.contents = []

        if len(args) > 1:
            raise TypeError("Expected 1 argument, {0} given".format(len(args)))

        if not args:
            pass
        elif isinstance(args[0], list):
            self.contents.extend(args[0])
        else:
            if isinstance(args[0], text_type): 
                simple = kwargs.pop("simple", False)
                pattern = args[0]
                pattern = pattern.lower()
                if simple:
                    tokens = self.pp_simple.tokens(pattern)
                else:
                    tokens = self.pp.tokens(pattern)
                terminator = None
                just_one = False

            elif inspect.isgenerator(args[0]):
                tokens = args[0]
                terminator = kwargs.pop("terminator", None)
                just_one = kwargs.pop("just_one", False)
            else:
                raise TypeError("Expected unicode string")

            try:
                while True:
                    token_class, text = next(tokens)
                    token = token_class(tokens, text, terminator)
                    token.add_to_parsetree(self)
                    if just_one:
                        break
            except StopScanLoop:
                pass
            except StopIteration:
                if terminator != None:
                    raise PatternError("Missing a closing parenthesis "
                                       "or square bracket")
            self.remove_trailing_space()
            if not self.contents:
                raise PatternError("Pattern string is empty")

        if kwargs:
            raise TypeError("Unexpected **kwargs: {0}".format(repr(kwargs)))

    def format(self):
        """Reconstruct the pattern string. Spacing will 
        be normalized, so you could use this to compare two patterns with
        inconsistent whitespace.
        """
        return "".join([token.format() for token in self.contents])

    def score(self):
        """Return a signed integer score that can be used
        to compare this pattern to others for complexity and
        specificity.
        """
        return sum(token.score() for token in self.contents)

    def regex(self, variables, counter=None):
        """ Generate a regular expression from the parsed pattern, 
        substituting in variable values if given.

        variables - a dictionary of dictionaries. The keys to the outer 
            dictionary are the single characters between % and :
            in the pattern. The keys to the inner dictionaries
            are variable names, and since case is ignored only
            keys in lower case will be used. The values of the inner
            dictionaries must be unicode strings, and will be
            parsed in turn, with the simple flag set to True.
        counter - a generator expression, used to get the number which
            is added onto "match" to create the names for the named
            groups for memorized matches. If None is passed, starts
            counting at zero.

        May raise:
        PatternVariableNotFoundError if a variable is referenced which is 
            not in the dictionary
        PatternVariableValueError if a variable contains something other
            than a unicode string
        PatternError if there is a syntax error in the value of a variable
        """
        if counter is None:
            counter = itertools.count()

        return "".join([token.regex(variables, counter)
                        for token in self.contents])

    def group_tokens(self):
        tokens = [t for t in self.contents if isinstance(t, Token)]
        if not tokens:
            raise PatternError("Alternatives between parentheses or "
                               "square brackets can't be empty")
        del self.contents[-len(tokens):]
        subtree = ParsedPattern(tokens)
        self.contents.append(subtree)

    def remove_trailing_space(self):
        if (self.contents and isinstance(self.contents[-1], Space)):
            self.contents.pop()


 
class Pattern(object):

    def __init__(self, raw, alternates=None, simple=False, say=print):
        self.raw = raw
        self.alternates = alternates
        self._say = say
        if self.raw:
            self._parse_tree = ParsedPattern(raw, simple=simple)
            self.formatted_pattern = self._parse_tree.format()
            self.score = self._parse_tree.score()
            self.regexc = self._cache_regexc(alternates)
        else:
            self._parse_tree = None
            self.formatted_pattern = ""
            self.score = _WILDCARD_SCORE
            self.regexc = None

    def __bool__(self):
        return len(self.raw) != 0

    def __nonzero__(self):
        return self.__bool__()

    def _cache_regexc(self, alternates):
        try:
            regex = self.regex(alternates)
            return re.compile(regex, flags=re.UNICODE)
        except PatternVariableNotFoundError as e:
            self._say("[Pattern] " + e.args[0] +
                      ' in "{0}"'.format(self.formatted_pattern) +
                      ", failed to cache regex")
            return None

    def regex(self, variables):
        return self._parse_tree.regex(variables) + "$"

    def match(self, string, variables):
        allvars = {}
        allvars.update(self.alternates)
        allvars.update(variables)
        if self.regexc:
            m = re.match(self.regexc, string)
        else:
            try:
                regex = self.regex(allvars)
            except PatternVariableNotFoundError as e:
                self._say("[Pattern] " + e.args[0] +
                          ' in "{0}"'.format(self.formatted_pattern) +
                          ", match failed")
                return None
            m = re.match(regex, string, flags=re.UNICODE)
        if m is not None:
            self._say('[Pattern] "' + self.formatted_pattern +
                      '" matched "' + string + '"')
                     
        return m
            
