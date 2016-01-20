#Any copyright is dedicated to the Public Domain.
#http://creativecommons.org/publicdomain/zero/1.0/
from __future__ import unicode_literals
import string
from chatbot_reply import Script, rule

class TutorialScript(Script):
    def setup(self):
        self.alternates = {"colors": "(red|yellow|orange|green|blue|indigo|violet)"}
        self.help_ideas = ["valve", "eliza", "fun stuff"]

    @rule("random help")
    def rule_random_help(self):
        return "<help {0}>".format(self.choose(self.help_ideas))
        
    @rule("*")
    def rule_star(self):
        return ["I don't understand that. <random help>",
                "Let's change the subject. <random help>"]

    @rule("hello robot")
    def rule_hello_robot(self):
        return "Hello, carbon-based life form!"
        
    @rule("how are you", weight=2)
    def rule_how_are_you(self):
        return ["I'm great, how are you?",
                "Doing awesome, you?",
                "Great! You?",
                "I'm fine, thanks for asking!"]

    @rule("say something random")
    def rule_say_something_random(self):
        word = self.choose(["it's fun", "potato"])
        return "I like being random because {0}.".format(word)

    @rule("greetings")
    def rule_greetings(self):
        return [("Hello!", 20),
                ("Buenas dias!", 25),
                ("Buongiorno!", 1)]

    @rule("_* told me to say _*")
    def rule_star2_told_me_to_say_star(self):
        return ['Why would {raw_match0} tell you to say "{match1}"?',
                'Are you just saying "{match1}" because {raw_match0} told you to?']
    
    @rule("i am _#1 years old")
    def rule_i_am_number1_years_old(self):
        return "{match0} isn't old at all!"

    @rule("who is _*")
    def rule_who_is_star(self):
        return "I don't know who {match0} is."

    @rule("i am @~3 years old")
    def rule_i_am_atsign3_years_old(self):
        return "Tell me that again, but with a number this time."

    @rule("i am * years old")
    def rule_i_am_star_years_old(self):
        return "Can you use a number instead?"

    @rule("are you a (bot|robot|computer|machine)")
    def rule_are_you_a_alt(self):
        return "Darn! You got me!"

    @rule("i am _(so|really|very) excited")
    def rule_i_am_alt_excited(self):
        return "What are you {match0} excited about?"

    @rule("i _(like|love) the color _*")
    def rule_i_alt_the_color_star(self):
        return ["What a coincidence! I {match0} that color too!",
                "The color {match1} is one of my favorites",
                "Really? I {match0} the color {match1} too!",
                "Oh I {match0} {match1} too!"]

    @rule("how [are] you")
    def rule_how_opt_you(self):
        return "I'm great, you?"

    @rule("what is your (home|office|cell) [phone] number")
    def rule_what_is_your_alt_opt_number(self):
        return "You can reach me at: 1 (800) 555-1234."

    @rule("i have a [red|green|blue] car")
    def rule_i_have_a_optalt_car(self):
        return "I bet you like your car a lot."

    @rule("[*] the matrix [*]")
    def rule_optstar_the_matrix_optstar(self):
        return "How do you know about the matrix?"

    @rule("what color is my _(red|blue|green|yellow) _*")
    def rule_what_color_is_my_alt_star(self):
        return "According to you, your {match1} is {match0}."

    @rule("my _* is _%a:colors")
    def rule_my_star_is_arrcolors(self):
        return "I've always wanted a {match1} {match0}."

    @rule("google _*", weight=10)
    def rule_google_star(self):
        return "OK, I'll google it. Jk, I'm not Siri."

    @rule("_* or whatever", weight=100)
    def rule_star_or_whatever(self):
        return "Whatever. <{match0}>"

    @rule("hello")
    def rule_hello(self):
        return ["Hi there!", "Hey!", "Howdy!"]

    @rule("hi")
    def rule_hi(self):
        return "<hello>"

    @rule("my name is _@~3")
    def rule_my_name_is_star(self):
        name = self.match["raw_match0"].rstrip(string.punctuation)
        self.uservars["name"] = name
        return "It's nice to meet you, {0}.".format(name)

    @rule("what is my name")
    def rule_what_is_my_name(self):
        if "name" not in self.uservars:
            return "You never told me your name."
        else:
            return ["Your name is {0}.".format(self.uservars["name"]),
                    "You told me your name is {0}.".format(self.uservars["name"])]

    @rule("is my name %u:name")
    def rule_is_my_name(self):
        return "That's what you told me!"
    

    
