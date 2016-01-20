# coding=utf-8
#Any copyright is dedicated to the Public Domain.
#http://creativecommons.org/publicdomain/zero/1.0/
from __future__ import unicode_literals
import random
import string
from chatbot_reply import rule, Script

class ElizaIntroScript(Script):
    @rule("[id like to|can i|may i] talk to Eliza")
    def rule_eliza_intro(self):
        Script.set_topic("eliza")
        return ["Hi, I'm Eliza. If you have a problem tell me about it.",
                "Hello, my name is Eliza. Please tell me what's been troubling you.",
                "Hi, I'm Eliza. Is something bothering you?"]

    @rule("help [*] eliza")
    def rule_eliza_help(self):
        return ["If you'd like to meet the in-house psychoanalyst, just ask to "
                "talk to Eliza. When you're done talking to her, say goodbye.",

                'We have a therapist on staff. Say "May I talk to Eliza?" to '
                'begin your therapy session and "done" or "bye" when you are '
                'finished.']


class ElizaScript(Script):
    topic = "eliza"

    def setup(self):
        self.alternates = {
            "be"       : "(am|is|are|was|be)",
            "belief"   : "(feel|think|believe|wish|belief)",
            "cannot"   : "(can not|cannot)",
            "desire"   : "(want|need|desire)",
            "everyone" : "(everybody|nobody|everyone)",
            "family"   : "(mother|mom|father|dad|sister|brother|wife|husband|"
                         "son|daughter|kids|children|child|family)",
            "happy"    : "(elated|glad|better|happy)",
            "sad"      : "(unhappy|depressed|sick|sad)"}

    def setup_user(self, user):
        self.uservars["Eliza replies"] = {}
        self.uservars["Eliza remembers"] = []

    def reflect(self, text):
        swaps = {"am":"are", "your":"my", "me":"you", "myself":"yourself",
                 "yourself":"myself", "i":"you", "you":"I", "my":"your",
                 "was":"were", "you're": "I'm", "i'm": "you're",
                 "i've": "you've", "you've" : "I've"}
        text = text.rstrip(string.punctuation)
        words = text.split()
        words = [swaps.get(w.lower(), w) for w in words]
        return " ".join(words)

    def choose(self, args):
        """This version of choose maintains a dictionary of responses that 
        have already been used, in self.uservars, and will select from the
        least-used responses available. 
        """
        if isinstance(args, list) and args and isinstance(args[0], unicode):
            counted_args = [(string,
                             self.uservars["Eliza replies"].get(string, 0))
                            for string in args]
            least_uses = min([c for s, c in counted_args])
            reply = random.choice([s for s, c in counted_args
                                   if c == least_uses])
            self.uservars["Eliza replies"][reply] = least_uses + 1
            return reply
        else:
            return super(ElizaScript, self).choose(args)

    def substitute(self, text, wordlists):
        contractions = {"don't":"do not", "can't":"can not", "won't":"will not",
                        "you're":"you are", "i'm" : "i am",
                        "i've" : "i have", "you've" : "you have"}
        results = []
        for wl in wordlists:
            new = []
            for word in wl:
                stripped = word.lower().rstrip(string.punctuation)
                new_word = contractions.get(stripped, word)
                new.extend(new_word.split())
            results.append(new)
        return results

    def process_reply(self, string):
        """This version of process_reply does Eliza style swapping of first and
        second person, and creates a match dictionary containing swapped versions
        of all the match variables that it then passes to str.format
        """
        reflected_matches = {}
        for k, v in self.match.items():
            reflected_matches[k] = v
            reflected_matches["refl_" + k] = self.reflect(v)
        return string.format(*[], **reflected_matches)

    @rule("(bye|goodbye|done|exit|quit)")
    def rule_leave_eliza(self):
        Script.set_topic("all")
        return ["Goodbye. It was nice talking to you.",
                "Goodbye. I'm looking forward to the next time we talk."
                "It was nice talking to you. Goodbye.",
                "Maybe we could talk about this more next time? Goodbye."]

    @rule("*")
    def rule_star(self):
        if self.uservars["Eliza remembers"]:
            memory = self.reflect(self.uservars["Eliza remembers"].pop())
            return self.choose([
                "Does that have anything to do with the fact that your {0}?",
                "Let's talk more why your {0}.",
                "Before you said your {0}.",
                "But your {0}."]).format(memory)
        else:
            return ["I'm not sure I understand you fully.",
                    "Please go on.",
                    "What does that suggest to you?",
                    "Do you feel strongly about discussing such things?",
                    "That is interesting. Please continue.",
                    "Tell me more about that.",
                    "Does talking about this bother you?"]

    @rule("[*] (sorry|apologize) [*]", weight=2)
    def rule_sorry(self):
        return ["Please don't apologize.",
                "Apologies are not necessary.",
                "I've told you that apologies are not required.",
                "It did not bother me. Please continue."]

    @rule("[*] i remember _*", weight=6)
    def rule_i_remember(self):
        return ["Do you often think of {refl_raw_match0}?",
                "Does thinking of {refl_raw_match0} bring anything else to mind?",
                "What else do you recall?",
                "Why do you remember {refl_raw_match0} just now?",
                "What in the present situation reminds you of {refl_raw_match0}?",
                "What is the connection between me and {refl_raw_match0}?",
                "What else does {refl_raw_match0} remind you of?"]

    @rule("[*] do you remember _*", weight=6)
    def rule_do_you_remember(self):
        return ["Did you think I would forget {refl_raw_match0}?",
                "Why do you think I should recall {refl_raw_match0} now?",
                "What about {refl_raw_match0}?",
                "<what>",
                "You mentioned {refl_raw_match0}?"]

    @rule("[*] you remember _*", weight=6)
    def rule_you_remember(self):
        return ["How could I forget {refl_raw_match0}?",
                "What about {refl_raw_match0} should I remember?",
                "<you recall {raw_match0}>"]

    @rule("[*] i forget _*", weight=6)
    def rule_i_forget(self):
        return ["Can you think of why you might forget {refl_raw_match0}?",
                "Why can't you remember {refl_raw_match0}?",
                "How often do you think of {refl_raw_match0}?",
                "Does it bother you to forget that?",
                "Could it be a mental block?",
                "Are you generally forgetful?",
                "Do you think you are suppressing {refl_raw_match0}?"]

    @rule("[*] did you forget _*", weight=6)
    def rule_did_you_forget(self):
        return ["Why do you ask?",
                "Are you sure you told me?",
                "Would it bother you if I forgot {refl_raw_match0}?",
                "Why should I recall {refl_raw_match0} just now?",
                "<what>",
                "Tell me more about {refl_raw_match0}."]

    @rule("[*] if _*", weight=4)
    def rule_if(self):
        return ["Do you think it's likely that {refl_raw_match0}?",
                "Do you wish that {refl_raw_match0}?",
                "What do you know about {refl_raw_match0}?",
                "Really, if {refl_raw_match0}?",
                "What would you do if {refl_raw_match0}?",
                "But what are the chances that {refl_raw_match0}?",
                "What does this speculation lead to?"]
    
    @rule("[*] i dreamed _*", weight=5)
    def rule_i_dreamed(self):
        return ["Really, {refl_raw_match0}?",
                "Have you ever fantasized {refl_raw_match0} while you were awake?",
                "Have you ever dreamed {refl_raw_match0} before?",
                "<dream>"]

    @rule("[*] (dream|dreams) [*]", weight=3)
    def rule_dream(self):
        return ["What does that dream suggest to you?",
                "Do you dream often?",
                "What people appear in your dreams?",
                "Do you believe that dreams have something to do with your problem?"]

    @rule("[*] maybe *", weight=2)
    def rule_maybe(self):
        return ["You don't seem quite certain.",
                "Why the uncertain tone?",
                "Can't you be more positive?",
                "You aren't sure?",
                "Don't you know?",
                "How likely, would you estimate?"]

    @rule("* name *", weight=26)
    def rule_name(self):
        return ["I am not interested in names.",
                "I've told you before, I don't care about names--please continue."]

    @rule("[*] _(deutsch|francais|français|italiano|espanol|español) [*]")
    def rule_foreign(self):
        languages = {"deutsch" : "German", "francais": "French",
                     "français" : "French", "italiano" : "Italian",
                     "espanol" : "Spanish", "español" : "Spanish"}
        return ["I only speak English.",
                "I told you before, I don't understand {0}.".format(
                    languages[self.match["match0"]])]
        
    @rule("[*] hello [*]", weight=2)
    def rule_hello(self):
        return ["Hello. Please tell me about your problem.",
                "Hi. What seems to be your problem?"]

    @rule("[*] (computer|computers|machine|machines) [*]", weight=50)
    def rule_computer(self):
        return ["Do computers worry you?",
                "Why do you mention computers?",
                "What do you think machines have to do with your problem?",
                "Don't you think computers can help people?",
                "What about machines worries you?",
                "What do you think about machines?",
                "You don't think I am a computer program, do you?"]

    @rule("[*] am i _*")
    def rule_am_i(self):
        return ["Do you believe you are {refl_raw_match0}?",
                "Would you want to be {refl_raw_match0}?",
                "Do you wish I would tell you you are {refl_raw_match0}?",
                "What would it mean if you were {refl_raw_match0}?",
                "<what>"]

    @rule("* am *")
    def rule_am(self):
        return ["Why do you say 'am'?",
                "I don't understand that."]

    @rule("[*] are you _*")
    def rule_are_you(self):
        return ["Why are you interested in whether I am {refl_raw_match0} or not?",
                "Would you prefer if I weren't {refl_raw_match0}?",
                "Maybe I am {refl_raw_match0} in your fantasies.",
                "Do you sometimes think I am {refl_raw_match0}?",
                "<what>",
                "Would it matter to you?",
                "What if I were {refl_raw_match0}?"]

    @rule("* are _*")
    def rule_are(self):
        return ["Did you think they might not be {refl_raw_match0}?",
                "Would you like it if they were not {refl_raw_match0}?",
                "What if they were not {refl_raw_match0}?",
                "Are they always {refl_raw_match0}?",
                "Possibly they are {refl_raw_match0}.",
                "Are you positive they are {refl_raw_match0}?"]

    @rule("[*] your _*")
    def rule_your(self):
        return ["Why are you concerned over my {refl_raw_match0}?",
                "What about your own {refl_raw_match0}?",
                "Are you worried about someone else's {refl_raw_match0}?",
                "Really, my {refl_raw_match0}?",
                "What makes you think of my {refl_raw_match0}?",
                "Do you want my {refl_raw_match0}?"]

    @rule("[*] (was i|i was) _*", weight=3)
    def rule_was_i(self):
        return ["What if you were {refl_raw_match0}?",
                "Do you think you were {refl_raw_match0}?",
                "Were you {refl_raw_match0}?",
                "What would it mean if you were {refl_raw_match0}?",
                'What does "{refl_raw_match0}" suggest to you?',
                "<what>"]

    @rule("[*] were you _*", weight=3)
    def rule_were_you(self):
        return ["Would you like to believe I was {refl_raw_match0}?",
                "What suggests that I was {refl_raw_match0}?",
                "What do you think?",
                "Maybe I was {refl_raw_match0}.",
                "What if I had been {refl_raw_match0}?"]

    @rule("[*] i %a:desire _*")
    def rule_i_desire(self):
        return ["What would it mean to you if you got {refl_raw_match0}?",
                "Why do you want {refl_raw_match0}?",
                "Suppose you got {refl_raw_match0} soon.",
                "What if you never got {refl_raw_match0}?",
                "What would getting {refl_raw_match0} mean to you?",
                "What does wanting {refl_raw_match0} have to do with this "
                    "discussion?"]

    @rule("[*] i am _%a:sad [*]")
    def rule_im_sad(self):
        return ["I am sorry to hear that you are {match0}.",
                "Do you think coming here will help you not to be {match0}?",
                "I'm sure it's not pleasant to be {match0}.",
                "Can you explain what made you {match0}?"]

    @rule("[*] i am _%a:happy [*]")
    def rule_im_happy(self):
        return ["How have I helped you to be {match0}?",
                "Has your treatment made you {match0}?",
                "What makes you {match0} just now?",
                "Can you explain why you are suddenly {match0}?"]

    @rule("[*] i %a:belief i _*")
    def rule_i_belief(self):
        return ["Do you really think so?",
                "But you are not sure you {refl_raw_match0}.",
                "Do you really doubt you {refl_raw_match0}?"]

    @rule("[*] i [*] %a:belief [*] you _[*]")
    def rule_belief_you(self):
        return "<you {raw_match0}>"

    @rule("[*] i am _*")
    def rule_i_am(self):
        return ["Is it because you are {refl_raw_match0} that you came to me?",
                "How long have you been {refl_raw_match0}?",
                "Do you believe it is normal to be {refl_raw_match0}?",
                "Do you enjoy being {refl_raw_match0}?",
                "Do you know anyone else who is {refl_raw_match0}?"]

    @rule("[*] i %a:cannot _*")
    def rule_i_cannot(self):
        return ["How do you know that you can't {refl_raw_match0}?",
                "Have you tried?",
                "Maybe you could {refl_raw_match0} now.",
                "Do you really want to be able to {refl_raw_match0}?",
                "What if you could {refl_raw_match0}?"]
    
    @rule("[*] i do not _*")
    def rule_i_dont(self):
        return ["Don't you really {refl_raw_match0}?",
                "Why don't you {refl_raw_match0}?",
                "Do you wish you could {refl_raw_match0}?",
                "Does that trouble you?"]

    @rule("[*] i feel _*")
    def rule_i_feel(self):
        return ["Tell me more about such feelings.",
                "Do you often feel {refl_raw_match0}?",
                "Do you enjoy feeling {refl_raw_match0}?",
                "Of what does feeling {refl_raw_match0} remind you?"]

    @rule("[*] i _* you [*]")
    def rule_i_you(self):
          return ["Maybe in your fantasies we {refl_raw_match0} each other.",
                  "Do you wish to {refl_raw_match0} me?",
                  "You seem to need to {refl_raw_match0} me.",
                  "Do you {refl_raw_match0} anyone else?"]
          
    @rule("_([*] i [*])")
    def rule_i(self):
        return ["You say {refl_raw_match0}?",
                "Can you tell me more about that?",
                "Do you say {refl_raw_match0} for some special reason?",
                "That's very interesting."]


    @rule("[*] you remind me of _*")
    def rule_you_remind_me_of(self):
        return "<alike> {raw_match0}"

    @rule("[*] you are _*")
    def rule_you_are(self):
        return ["What makes you think I am {refl_raw_match0}?",
                "Do you like to believe I am {refl_raw_match0}?",
                "Do you sometimes wish you were {refl_raw_match0}?",
                "Maybe you would like to be {refl_raw_match0}."]

    @rule("[*] you _* me *")
    def rule_you_me(self):
        return ["Why do you think I {refl_raw_match0} you?",
                "You like to think I {refl_raw_match0} you -- don't you?",
                "What makes you think I {refl_raw_match0} you?",
                "Really, I {refl_raw_match0} you?",
                "Do you wish to believe I {refl_raw_match0} you?",
                "Suppose I did {refl_raw_match0} you -- what would that mean?",
                "Does someone else believe I {refl_raw_match0} you?"]
    
    @rule("[*] you _*")
    def rule_you(self):
        return ["We were discussing you -- not me.",
                "Oh, I {refl_raw_match0}?",
                "You're not really talking about me -- are you?",
                "What are your feelings now?"]

    @rule("[*] yes [*]", weight=2)
    def rule_yes(self):
        return ["You seem to be quite positive.",
                "You are sure.",
                "I see.",
                "I understand."]

    @rule("[*] (no one|noone) _*")
    def rule_no_one(self):
        return ["Are you sure, no one {refl_raw_match0}?",
               "Surely someone {refl_raw_match0} .",
               "Can you think of anyone at all?",
               "Are you thinking of a very special person?",
               "Who, may I ask?",
               "You have a particular person in mind, don't you?",
               "Who do you think you are talking about?"]

    @rule("[*] no [*]")
    def rule_no(self):
        return ["Are you saying no just to be negative?",
                "You are being a bit negative.",
                "Why not?",
                "Why 'no'?"]

    @rule("[*] my _*", weight=3)
    def rule_my(self):
        self.uservars["Eliza remembers"].append(self.match["raw_match0"])
        return ["Your {refl_raw_match0}?",
                "Why do you say your {refl_raw_match0}?",
                "Does that suggest anything else which belongs to you?",
                "Is it important to you that your {refl_raw_match0}?"]

    @rule("[*] my [*] _%a:family _*", weight=3)
    def rule_my_family(self):
        return ["Tell me more about your family.",
                "Who else in your family {refl_raw_match1}?",
                "Your {refl_raw_match0}?",
                "What else comes to your mind when you think of your {refl_raw_match0}?"]

    @rule("[*] can you _*")
    def rule_can_you(self):
        return ["You believe I can {refl_raw_match0} don't you?",
                "<what>",
                "You want me to be able to {refl_raw_match0}.",
                "Perhaps you would like to be able to {refl_raw_match0} yourself."]

    @rule("[*] can i _*")
    def rule_can_i(self):
        return ["Whether or not you can {refl_raw_match0} depends on you more than on me.",
                "Do you want to be able to {refl_raw_match0}?",
                "Perhaps you don't want to {refl_raw_match0}.",
                "<what>"]

    @rule("(what|who|when|where|how) [*]", weight=2)
    def rule_question_words(self):
        return ["Why do you ask?",
                "Does that question interest you?",
                "What is it you really want to know?",
                "Are such questions much on your mind?",
                "What answer would please you most?",
                "What do you think?",
                "What comes to mind when you ask that?",
                "Have you asked such questions before?",
                "Have you asked anyone else?"]


    @rule("[*] why do not you _*")
    def rule_why_dont_you(self):
        return ["Do you believe I don't {refl_raw_match0}?",
                "Perhaps I will {refl_raw_match0} in good time.",
                "Should you {refl_raw_match0} yourself?",
                "You want me to {refl_raw_match0}?",
                "<what>"]

    @rule("[*] why can not i _*")
    def rule_why_cant_i(self):
        return ["Do you think you should be able to {refl_raw_match0}?",
                "Do you want to be able to {refl_raw_match0}?",
                "Do you believe this will help you to {refl_raw_match0}?",
                "Have you any idea why you can't {refl_raw_match0}?",
                "<what>"]

    @rule("[*] why [*]")
    def rule_why(self):
        return "<what>"

    @rule("[*] because *",weight=2)
    def rule_because(self):
        return ["Is that the real reason?",
                "Don't any other reasons come to mind?",
                "Does that reason seem to explain anything else?",
                "What other reasons might there be?"]

    @rule("[*] _%a:everyone [*]", weight=3)
    def rule_everyone(self):
        return ["Really, {refl_raw_match0}?",
                "Surely not {refl_raw_match0}.",
                "Can you think of anyone in particular?",
                "Who, for example?",
                "Are you thinking of a very special person?",
                "Who, may I ask?",
                "Someone special perhaps?",
                "You have a particular person in mind, don't you?",
                "Who do you think you're talking about?"]
    
    @rule("[*] always [*]", weight=2)
    def rule_always(self):
        return ["Can you think of a specific example?",
                "When?",
                "What incident are you thinking of?",
                "Really, always?"]

    @rule("[*] (%a:be [*] like|alike) *", weight=21)
    def rule_like(self):
        return ["In what way?",
                "What resemblence do you see?",
                "What does that similarity suggest to you?",
                "What other connections do you see?",
                "What do you suppose that resemblence means?",
                "What is the connection, do you suppose?",
                "Could there really be some connection?",
                "How?"]

    @rule ("[*] different [*]",weight=2)
    def rule_different(self):
        return ["How is it different?",
                "What differences do you see?",
                "What does that difference suggest to you?",
                "What other distinctions do you see?",
                "What do you suppose that disparity means?",
                "Could there be some connection, do you suppose?",
                "How?"]
