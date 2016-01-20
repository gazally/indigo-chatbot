#Any copyright is dedicated to the Public Domain.
#http://creativecommons.org/publicdomain/zero/1.0/
from __future__ import unicode_literals
from chatbot_reply import Script, rule

class HokeyPokeyScript(Script):
    def setup(self):
        self.botvars["mood"] = "good"
        self.botvars["bodypart"] = "right foot"
        self.botvars["danced"] = False
        self.bodyparts = ['right foot', 'left foot', 'right arm',
                                       'left arm', 'whole self']

    @rule("help (hokey pokey|fun stuff|knock knock|jokes)")
    def rule_help_fun_stuff(self):
        return ["Tell me a knock knock joke please!",
                "Do you know any knock knock jokes? Tell me one.",
                "Ask me if I can do the hokey pokey."]

    @rule("how are you doing")
    def rule_how_are_you_doing(self):
        mood = self.botvars["mood"]
        return "I'm in a {0} mood.".format(mood)

    @rule("get grumpy")
    def rule_get_grumpy(self):
        self.botvars["mood"] = "bad"
        return "Now I'm grouchy."

    @rule("get happy")
    def rule_get_happy(self):
        self.botvars["mood"] = "good"
        return "I feel much better."

    @rule("hey [there]")
    def rule_hey_opt(self):
        if self.botvars["mood"] == "good":
            return "<hello>"
        else:
            return "Hay is for horses."

    @rule("knock knock")
    def rule_knock_knock(self):
        return "Who's there?"

    @rule("_*", previous_reply="whos there")
    def rule_star_prev_who_is_there(self):
        return "{raw_match0} who?"

    @rule("_*", previous_reply="* who")
    def rule_star_prev_star_who(self):
        return "Lol {raw_match0}! That's a good one!"

    @rule("put your _* in")
    def rule_put_your_star_in(self):
        return ("I put my {match0} in, I put my {match0} out, "
                "I shake it all about!")

    @rule("where are you in the dance")
    def rule_where_are_you_in_the_dance(self):
        return "I'm about to use my {0}.".format(self.botvars["bodypart"])

    @rule("back to the right foot")
    def rule_back_to_the_right_foot(self):
        self.botvars["bodypart"] = "right foot"
        return "OK, I'm back on the right foot."

    @rule("what would the next one be")
    def rule_what_would_the_next_one_be(self):
        next_part = self.next_body_part(self.botvars["bodypart"])
        return "After {0} comes {1}.".format(self.botvars["bodypart"],
                                            next_part)

    @rule("skip to the next one")
    def rule_skip_to_the_next_one(self):
        self.botvars["bodypart"] = self.next_body_part(self.botvars["bodypart"])
        return "OK, when I dance I'll use my {0}.".format(self.botvars["bodypart"])

    @rule("[*] do the hokey pokey")
    def rule_do_the_hokey_pokey(self):
        self.botvars["danced"] = True
        bodypart = self.botvars["bodypart"]
        self.botvars["bodypart"] = self.next_body_part(bodypart)
        return "<put your {0} in>".format(bodypart)
    
    @rule("(have you done|did you do) the hokey pokey")
    def rule_have_you_done_the_hokey_pokey(self):
        if self.botvars["danced"]:
            return "Yes!"
        else:
            return "No, but I'd like to!"

    @rule("do you know [how to do] the hokey pokey")
    def rule_can_you_do_the_hokey_pokey(self):
        if self.botvars["danced"]:
            return "Yes!"
        else:
            return "I think so! I'd like to try!"

    def next_body_part(self, bodypart):
        return self.bodyparts[(self.bodyparts.index(bodypart) + 1)
                              % len(self.bodyparts)]
    
