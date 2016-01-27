# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
""" Exceptions for chatbot_reply
"""
class PatternError(Exception):
    """ Raised when patterns.ParsedPattern can't parse a pattern string"""
    pass
class PatternVariableNotFoundError(Exception):
    """ Raised when a user, bot or alternates variable is not found in a
    pattern string
    """
    pass
class PatternVariableValueError(Exception):
    """ Raised when a user, bot or alternates variable contains something that
    is not a string
    """
    pass
class NoRulesFoundError(Exception):
    """ Raised when ChatbotReply.load_script_directory fails to find any rules
    decorated by @rule in any classes derived from Script in any .py files
    in a directory. """
    pass
class RecursionTooDeepError(Exception):
    """ Raised by reply.reply when recursively expanding replies goes
    over the recursion depth limit."""
    pass


