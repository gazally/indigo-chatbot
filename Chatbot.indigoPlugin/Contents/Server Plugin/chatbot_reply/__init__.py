# Copyright (c) 2016 Gemini Lasswell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from .exceptions import PatternError, NoRulesFoundError, RecursionTooDeepError
from .exceptions import PatternVariableNotFoundError
from .script import rule, Script, split_on_whitespace, kill_non_alphanumerics
from .script import UserInfo
from .reply import ChatbotEngine

# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())

__all__ = ["ChatbotEngine", "Script", "rule", "UserInfo", "PatternError",
           "PatternVariableNotFoundError", "NoRulesFoundError",
           "RecursionTooDeepError", "split_on_whitespace",
           "kill_non_alphanumerics"]

__version__ = "0.1.0"
