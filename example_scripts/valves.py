# coding=utf-8
#Any copyright is dedicated to the Public Domain.
#http://creativecommons.org/publicdomain/zero/1.0/
from __future__ import unicode_literals
import indigo
from chatbot_reply import Script, rule

class ValveScript(Script):

    def setup(self):
        self.alternates = {
            "mainvalve" : "((shutoff|shut off|main [water]|city water) valve)",
            "drainvalve": "([water] drain valve)",
            "anyvalve"  : "((shutoff|shut off|main|main water|city water|[water] drain) valve)"
            }

        indigo.variable.updateValue(
            self.get_or_create_indigo_var("leaksensorstatus"), "dry")
        indigo.variable.updateValue(
            self.get_or_create_indigo_var("mainvalvestatus"), "closed")
        indigo.variable.updateValue(
            self.get_or_create_indigo_var("drainvalvestatus"), "open")


    @rule("help [on] (valve|valves|water valves|%a:anyvalve)")
    def rule_help_valves(self):
        return ['I can turn the water on and off and drain the house by '
                'controlling the shutoff valve and the drain valve. Ask me '
                '"What is the valve status?" to get started.',
                
                'Try telling me to turn the water on or off or to drain the '
                'house.',
                
                'If you tell me "sensor wet" I\'ll pretend the leak sensor '
                'in the bathroom is wet. Then try telling me "Turn the water '
                'on" and see what I do.']
 
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

    @rule("_(open|close) it", previous_reply=
          "([*] %a:mainvalve [*] %a:drainvalve [*]|[*] %a:drainvalve [*] %a:mainvalve [*])")
    def rule_open_close_it_previous_both_valves(self):
        return ["What do you want me to {match0}?",
                "Which valve would you like to {match0}?"]

    @rule("_(open|close) it", previous_reply="* _%a:anyvalve [*]")
    def rule_open_close_it_previous_any_valve(self):
        return "<{match0} the {reply_match0}>"

    @rule("_(open|close) [it]")
    def rule_open_close_it(self):
        return "What do you want me to {match0}?"

    @rule("[the] _%a:anyvalve", previous_reply=
          "(what do you want me|which valve would you like) to _(open|close)")
    def rule_the_anyvalve_with_previous_whaddayawant(self):
        return "OK, <{reply_match0} the {match0}>"

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

    @rule("[what is [the]] (water|leak) sensor status")
    def rule_water_sensor_status(self):
        return "The water leak sensor is {0}.".format(self.leaksensorstatus())

    @rule("_%a:mainvalve status")
    def rule_mainvalve_status(self):
        return "The {{match0}} is {0}.".format(self.mainvalvestatus())

    @rule("_%a:drainvalve status")
    def rule_what_is_the_drainvalve_status(self):
        return "The {{match0}} is {0}.".format(self.drainvalvestatus())

    @rule("[tell me about|how is|what is] [the] valve status")
    def rule_valve_status(self):
        return "<shutoff valve status> <drain valve status>"

    @rule("status")
    def rule_status(self):
        return "<valve status> <water sensor status>"        

    @rule("(tell me about the|how is the|what is [the]) _%a:anyvalve [status]")
    def rule_what_is_the_anyvalve_status(self):
        return "<{match0} status>"

    @rule("is the _%a:anyvalve (open|closed)")
    def rule_is_the_anyvalve_open_or_closed(self):
        return "<{match0} status>"

    @rule("sensor wet")
    def rule_sensor_wet(self):
        indigo.variable.updateValue(
            self.get_or_create_indigo_var("leaksensorstatus"), "wet")
        return "Now the leak sensor is wet."
        
    @rule("sensor dry")
    def rule_sensor_dry(self):
        indigo.variable.updateValue(
            self.get_or_create_indigo_var("leaksensorstatus"), "dry")
        return "Now the leak sensor is dry."

    def stall_for_time(self):
        return self.choose([". Give it a few seconds and text me 'status' and I'll let you know how the valves are doing.",
                            ". Give me just a moment, then text me 'status' to make sure it worked.",
                            ", and in a few seconds please text me 'status' to check on the valves."])
            
    def get_or_create_indigo_var(self, name):
        if name in indigo.variables:
           ivar = indigo.variables[name]
        else:
            ivar = indigo.variable.create(name, "")
        return ivar

    def get_indigo_var_value_if_it_exists(self, name):
        if name in indigo.variables:
            return indigo.variables[name].value
        else:
            return "unknown"

    def mainvalvestatus(self):
        return self.get_indigo_var_value_if_it_exists("mainvalvestatus")

    def drainvalvestatus(self):
        return self.get_indigo_var_value_if_it_exists("drainvalvestatus")

    def tellmainvalve(self, todo):
        if todo == "close":
            newstate = "closed"
        else:
            newstate = "open"
        ivar = self.get_or_create_indigo_var("mainvalvestatus")
        indigo.variable.updateValue(ivar, newstate)

    def telldrainvalve(self, todo):
        if todo == "close":
            newstate = "closed"
        else:
            newstate = "open"
        ivar = self.get_or_create_indigo_var("drainvalvestatus")
        indigo.variable.updateValue(ivar, newstate)
        
    def leaksensorstatus(self):
        return self.get_indigo_var_value_if_it_exists("leaksensorstatus")

