"""Draft tanglish lexicon for the banking domain (LLM draft). Not loaded by the builder until
Rishabh has reviewed it and moved it to env/exp2/lexicon_src/."""

VERIFICATION = "author: Rishabh, 2026-10-28"

LEX = {
    "intro": "En net banking-la konjam velai pannunga, ellathayum queue-la vechu kadaisila onna submit pannunga.",
    "clauses": {
        "dispute": "October {day} anniki {merchant} en savings account-la \u20b9{amt} rendu thadava eduthuttanga. Rendavadhu, duplicate charge mela dispute raise pannunga.",
        "card_block": "Last digits {last4} irukkara en savings account debit card {block_reason}. Adha block pannunga.",
        "card_replace": "Andha card-ku replacement order panni, en {replace_to} address-ku deliver panna sollunga.",
        "card_limit": "En salary account debit card-la international online limit-a oru naalukku \u20b9{limit}-a vainga.",
        "fd_open": "En savings account-la irundhu \u20b9{fd_amount}-ku oru fixed deposit open pannunga: tenure {lo} la irundhu {hi} months-kulla, premature withdrawal allow pannra schemes-la interest rate adhigama irukkaradhu; interest payout {payout}-a irukkanum.",
        "rd_open": "En salary account-la irundhu maasam \u20b9{rd_amount} recurring deposit onnu start pannunga, adhu andha fixed deposit mature aagura adhe maasam mature aaganum.",
        "nominee": "Pudhu fixed deposit-la {nominee}-va 100% share-oda nominee-a add pannunga.",
        "cheque_stop": "{cq_payee}-ku naan kudutha \u20b9{cq_amount} cheque-a stop pannunga; andha payment cancel aayiduchu.",
        "submit": "Confirmations-a {channel}-la mattum anuppunga, ella requests-ayum en home branch {branch}-oda attach pannunga."
    },
    "terms": {
        "block_reason": {
            "lost": "tholanjuduchu",
            "stolen": "thirudu poyiduchu"
        },
        "address": {
            "office": "office",
            "home": "veettu"
        },
        "payout": {
            "cumulative": "cumulative",
            "monthly": "monthly",
            "quarterly": "quarterly"
        },
        "relation": {
            "mummy": "Amma",
            "papa": "Appa"
        },
        "channel": {
            "sms": "SMS",
            "email": "email"
        }
    }
}
