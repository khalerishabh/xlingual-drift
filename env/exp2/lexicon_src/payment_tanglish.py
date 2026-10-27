"""Draft tanglish lexicon for the payment domain (LLM draft). Not loaded by the builder until
Rishabh has reviewed it and moved it to env/exp2/lexicon_src/."""

VERIFICATION = "author: Rishabh, 2026-10-28"

LEX = {
    "intro": "Banking app-la en month-end payments ellathayum oru batch-a pannunga. Ovvoru bill-kum: amount due \u20b9{full_max} illa adhukku kammiya irundha full amount pay pannunga, illana minimum due mattum pay pannunga. Bills-a en savings account-la irundhu pay pannunga, aana edhavadhu oru payment-naala savings \u20b9{floor}-ku keezha pogum-na, andha bill-ayum adhukku apromulla ella bills-ayum en salary account-la irundhu pay pannunga. Ovvoru bill-layum adhu endha bill-nu oru remark podunga.",
    "clauses": {
        "bill_1": "Modhalla {bill_1} pay pannunga.",
        "bill_2": "Aprom {bill_2}.",
        "bill_3": "Aprom {bill_3}.",
        "bill_4": "Aprom {bill_4}.",
        "bill_5": "Aprom {bill_5}.",
        "bill_6": "Aprom {bill_6}.",
        "rent": "En landlord Vinod Deshpande-ku \u20b9{rent} rent-a en salary account-la irundhu NEFT-la anuppunga.",
        "pocket": "En thangachi Kavya-ku \u20b9{pocket} pocket money-a en savings account-la irundhu IMPS-la anuppunga.",
        "wallet": "En {wallet} wallet balance correct-a \u20b9{wallet_target} aagura maadhiri en salary account-la irundhu top up pannunga.",
        "merchant": "Andheri West-la irukkara Sharma Kirana Stores-ku en savings account-la irundhu UPI-la \u20b9{m_amount} pay pannunga.",
        "submit": "Full batch-a November {sched_day} 2026-ku schedule panni, payment summary-a {notify}-ku anuppunga."
    },
    "terms": {
        "bill": {
            "elec_home": "Andheri-la irukkara engha veettu electricity bill",
            "elec_nani": "Pune-la irukkara paati veettu electricity bill",
            "gas": "piped gas bill",
            "broadband": "broadband bill",
            "mobile_father": "Appa-voda postpaid mobile bill",
            "mobile_mother": "Amma-voda postpaid mobile bill"
        },
        "wallet": {
            "WL-AMZ-1": "Amazon Pay",
            "WL-PTM-1": "Paytm",
            "WL-PPE-1": "PhonePe"
        },
        "relation": {
            "papa": "Appa",
            "mummy": "Amma"
        }
    }
}
