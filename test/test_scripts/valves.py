#Any copyright is dedicated to the Public Domain.
#http://creativecommons.org/publicdomain/zero/1.0/
from __future__ import unicode_literals
from chatbot_reply import Script, rule

class ValveScript(Script):

    def setup(self):
        self.alternates = {}
        self.alternates["mainvalve"] = \
            "((shutoff|shut off|main|main water|city water) valve)"
        self.alternates["drainvalve"] = "([water] drain valve)"
        self.alternates["anyvalve"] = \
            "({0}|{1})".format(self.alternates["mainvalve"],
                               self.alternates["drainvalve"])

    def setup_user(self, user):
        self.uservars["mainvalvestatus"] = "open"
        self.uservars["drainvalvestatus"] = "closed"
        self.uservars["leaksensorstatus"] = "dry"


    @rule("status")
    def rule_status(self):
        return ("Here is where I would tell you everything I know about "
                "the shutoff valve and the drain valve, as well as the water "
                "sensors.")

    @rule("valve status")
    def rule_valve_status(self):
        return "<shutoff valve status> <drain valve status> <water sensor status>"

    @rule("_%a:mainvalve status")
    def rule_what_is_the_mainvalve_status(self):
        return "The {{match0}} is {0}.".format(self.mainvalvestatus())

    @rule("_%a:drainvalve status")
    def rule_what_is_the_drainvalve_status(self):
        return "The {{match0}} is {0}.".format(self.drainvalvestatus())

    @rule("(tell me about the|how is the|what is [the]) _%a:anyvalve [status]")
    def rule_what_is_the_anyvalve_status(self):
        return "<{match0} status>"

    @rule("is the _%a:anyvalve (open|closed)")
    def rule_is_the_anyvalve_open_or_closed(self):
        return "<{match0} status>"

    @rule("open [the] _%a:mainvalve")
    def rule_open_the_mainvalve(self):
        if self.drainvalvestatus() == "open":
            return "The drain valve is open. Please close it before opening the {match0}."
        if self.leaksensorstatus() == "wet":
            return "<leak sensor status> Please dry it and reset it before opening the {match0}."
        self.tellmainvalve("open")
        return "I'll tell the {match0} to open" + self.stall_for_time()

    @rule("open [the] _%a:drainvalve")
    def rule_open_the_drainvalve(self):
        if self.mainvalvestatus() == "open":
            return "The shutoff valve is open. Please close it first."
        else:
            self.telldrainvalve("open")
            return "I'll tell the {match0} to open" + self.stall_for_time()

    @rule("close [the] _%a:mainvalve")
    def rule_close_the_mainvalve(self):
        self.tellmainvalve("close")
        return "I'll tell the {match0} to close" + self.stall_for_time()

    @rule("close [the] _%a:drainvalve")
    def rule_close_the_drainvalve(self):
        self.telldrainvalve("close")
        return "I will tell the {match0} to close" + self.stall_for_time()

    def stall_for_time(self):
        return self.choose([" and get back to you shortly.",
                            ". Give me just a moment.",
                            ". I'll check back with you shortly.",
                            ". I'll check back with you in a moment.",
                            " and get back to you in a moment.",
                            " and get back to you in just a moment."])

    @rule("_(open|close) it", previous_reply="* shutoff valve * drain valve *")
    def rule_open_close_it_previous_both_valves(self):
        return "What do you want me to {match0}?"

    @rule("_(open|close) it", previous_reply="* _%a:anyvalve [*]")
    def rule_open_close_it_previous_any_valve(self):
        return "<{match0} the {botmatch0}>"

    @rule("_(open|close) [it]")
    def rule_open_close_it(self):
        return "What do you want me to {match0}?"

    @rule("[the] _%a:anyvalve", previous_reply="what do you want me to _(open|close)")
    def rule_the_anyvalve_with_previous_whaddayawant(self):
        return "OK, <{botmatch0} the {match0}>"

    @rule("[turn [the]] water on")
    def rule_turn_the_water_on(self):
        if self.mainvalvestatus() == "open":
            return "It's already on."
        if self.leaksensorstatus() == "wet":
            return "<leak sensor status> Please dry it and reset it before turning the water on."
        if self.drainvalvestatus() == "open":
            self.telldrainvalve("close")
            return "I closed the drain valve and <open shutoff valve>"
        else:
            return "<open shutoff valve>"

    @rule("[turn [the]] water off")
    def rule_turn_the_water_off(self):
        return "<close shutoff valve>"

    @rule("drain [the] (water|house)")
    def rule_drain_the_house(self):
        if self.drainvalvestatus() == "open":
            return "It's already drained."
        if self.mainvalvestatus() == "open":
            self.tellmainvalve("close")
            return "I closed the main valve and <open drain valve>"
        else:
            return "<open drain valve>"

    @rule("(water|leak) sensor status")
    def rule_water_sensor_status(self):
        return "The water leak sensor is {0}.".format(self.leaksensorstatus())


    @rule("sensor wet")
    def rule_sensor_wet(self):
        self.uservars["leaksensorstatus"] = "wet"
        return "Now the leak sensor is wet."

    @rule("sensor dry")
    def rule_sensor_dry(self):
        self.uservars["leaksensorstatus"] = "dry"
        return "Now the leak sensor is dry."

    def mainvalvestatus(self):
        return self.uservars["mainvalvestatus"]

    def drainvalvestatus(self):
        return self.uservars["drainvalvestatus"]        

    def tellmainvalve(self, todo):
        if todo == "close":
            newstate = "closed"
        else:
            newstate = "open"
        self.uservars["mainvalvestatus"] = newstate

    def telldrainvalve(self, todo):
        if todo == "close":
            newstate = "closed"
        else:
            newstate = "open"
        self.uservars["drainvalvestatus"] = newstate
        
    def leaksensorstatus(self):
        return self.uservars["leaksensorstatus"]
