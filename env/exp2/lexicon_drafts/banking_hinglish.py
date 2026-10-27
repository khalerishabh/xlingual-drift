"""Draft hinglish lexicon for the banking domain (LLM draft). Not loaded by the builder until
Rishabh has reviewed it and moved it to env/exp2/lexicon_src/."""

VERIFICATION = "draft: LLM, pending Rishabh"

LEX = {
    "intro": "Meri net banking pe kuch kaam kar do, sab queue mein daalo aur end mein ek saath submit karo.",
    "clauses": {
        "dispute": "{day} October ko {merchant} ne mere savings account se \u20b9{amt} do baar kaat liye. Doosre, duplicate charge pe dispute raise karo.",
        "card_block": "Mera savings account wala debit card jiske last digits {last4} hain, {block_reason}. Use block kar do.",
        "card_replace": "Us card ka replacement mangwao, mere {replace_to} wale address pe.",
        "card_limit": "Mere salary account wale debit card pe international online limit \u20b9{limit} per day kar do.",
        "fd_open": "Mere savings account se \u20b9{fd_amount} ka fixed deposit kholo, us scheme mein jiska tenure {lo} se {hi} months ke beech ho, premature withdrawal allowed ho, aur unme jiska interest rate sabse zyada ho; interest payout {payout} ho.",
        "rd_open": "Mere salary account se \u20b9{rd_amount} mahine ka ek recurring deposit start karo jo usi mahine mature ho jis mahine wo fixed deposit.",
        "nominee": "Naye fixed deposit pe {nominee} ko 100% share ke saath nominee banao.",
        "cheque_stop": "Maine {cq_payee} ko \u20b9{cq_amount} ka jo cheque diya tha, use stop kar do; wo payment cancel ho gaya hai.",
        "submit": "Confirmations sirf {channel} pe bhejna aur saari requests meri home branch {branch} se attach karna."
    },
    "terms": {
        "block_reason": {
            "lost": "kho gaya hai",
            "stolen": "chori ho gaya hai"
        },
        "address": {
            "office": "office",
            "home": "ghar"
        },
        "payout": {
            "cumulative": "cumulative",
            "monthly": "monthly",
            "quarterly": "quarterly"
        },
        "relation": {
            "mummy": "Mummy",
            "papa": "Papa"
        },
        "channel": {
            "sms": "SMS",
            "email": "email"
        }
    }
}
