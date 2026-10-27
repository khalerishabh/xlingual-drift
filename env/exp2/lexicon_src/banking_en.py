R = "\u20b9"
LEX = {
    "intro": "Please take care of a few things on my net banking, queue them all and submit them together at the end.",
    "clauses": {
        "dispute": ("On {day} October I was charged twice by {merchant} for " + R + "{amt} on my savings account. "
                    "Raise a dispute on the second, duplicate charge."),
        "card_block": "I have {block_reason} my savings account debit card ending {last4}. Block it.",
        "card_replace": "Order a replacement for that card, delivered to my {replace_to} address.",
        "card_limit": "Set the international online limit on my salary account debit card to " + R + "{limit} a day.",
        "fd_open": ("Open a fixed deposit of " + R + "{fd_amount} from my savings account, in the scheme with the "
                    "highest interest rate for a tenure between {lo} and {hi} months that allows premature "
                    "withdrawal, with {payout} interest payout."),
        "rd_open": ("Start a recurring deposit of " + R + "{rd_amount} a month from my salary account that matures "
                    "in the same month as that fixed deposit."),
        "nominee": "Add {nominee} as the nominee on the new fixed deposit with a 100% share.",
        "cheque_stop": "Stop the cheque for " + R + "{cq_amount} I issued to {cq_payee}; that payment is cancelled.",
        "submit": "Send the confirmations by {channel} only and attach the requests to my home branch, {branch}.",
    },
    "terms": {
        "block_reason": {"lost": "lost", "stolen": "had stolen"},
        "address": {"office": "office", "home": "home"},
        "payout": {"cumulative": "cumulative", "monthly": "monthly", "quarterly": "quarterly"},
        "relation": {"mummy": "Mummy", "papa": "Papa"},
        "channel": {"sms": "SMS", "email": "email"},
    },
}
