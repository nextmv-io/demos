"""Rule set definitions and business-rules variable/action classes."""

from business_rules.actions import BaseActions, rule_action
from business_rules.fields import FIELD_TEXT
from business_rules.variables import BaseVariables, numeric_rule_variable, string_rule_variable


class OrderVariables(BaseVariables):
    def __init__(self, order):
        self.order = order

    @numeric_rule_variable(label="Order Value ($)")
    def order_value(self):
        return self.order["value"]

    @numeric_rule_variable(label="Days Until Deadline")
    def days_until_deadline(self):
        return self.order["days_until_deadline"]

    @string_rule_variable(label="Customer Tier")
    def customer_tier(self):
        return self.order["customer_tier"]

    @numeric_rule_variable(label="Units")
    def units(self):
        return self.order["units"]


class OrderActions(BaseActions):
    def __init__(self, order):
        self.order = order
        self.priority = "defer"  # default if no rule fires

    @rule_action(params={"priority": FIELD_TEXT})
    def set_priority(self, priority):
        self.priority = priority


def get_rules(rule_set: str, options) -> list:
    """Return the rule list for the given rule set name."""
    expedite_days = options.expedite_deadline_days
    standard_days = options.standard_deadline_days

    RULE_SETS = {
        # Prioritize by order value and customer tier.
        "cost-first": [
            {
                "conditions": {
                    "any": [
                        {"name": "order_value", "operator": "greater_than", "value": 10000},
                        {"name": "customer_tier", "operator": "equal_to", "value": "gold"},
                    ]
                },
                "actions": [{"name": "set_priority", "params": {"priority": "expedite"}}],
            },
            {
                "conditions": {
                    "any": [
                        {"name": "order_value", "operator": "greater_than", "value": 3000},
                        {"name": "customer_tier", "operator": "equal_to", "value": "silver"},
                    ]
                },
                "actions": [{"name": "set_priority", "params": {"priority": "standard"}}],
            },
        ],
        # Prioritize by deadline urgency (thresholds configurable via options).
        "deadline-first": [
            {
                "conditions": {
                    "all": [
                        {"name": "days_until_deadline", "operator": "less_than_or_equal_to", "value": expedite_days},
                    ]
                },
                "actions": [{"name": "set_priority", "params": {"priority": "expedite"}}],
            },
            {
                "conditions": {
                    "all": [
                        {"name": "days_until_deadline", "operator": "less_than_or_equal_to", "value": standard_days},
                    ]
                },
                "actions": [{"name": "set_priority", "params": {"priority": "standard"}}],
            },
        ],
        # Prioritize strictly by customer tier.
        "tier-first": [
            {
                "conditions": {
                    "all": [{"name": "customer_tier", "operator": "equal_to", "value": "gold"}]
                },
                "actions": [{"name": "set_priority", "params": {"priority": "expedite"}}],
            },
            {
                "conditions": {
                    "all": [{"name": "customer_tier", "operator": "equal_to", "value": "silver"}]
                },
                "actions": [{"name": "set_priority", "params": {"priority": "standard"}}],
            },
        ],
    }

    if rule_set not in RULE_SETS:
        raise ValueError(f"Unknown rule set '{rule_set}'. Must be one of: {list(RULE_SETS)}")
    return RULE_SETS[rule_set]
