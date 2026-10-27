"""Draft hinglish lexicon for the payment domain (LLM draft). Not loaded by the builder until
Rishabh has reviewed it and moved it to env/exp2/lexicon_src/."""

VERIFICATION = "author: Rishabh, 2026-10-28"

LEX = {
    "intro": "Banking app pe mere month-end ke saare payments ek batch mein kar do. Har bill ke liye: agar amount due \u20b9{full_max} ya usse kam hai toh poora amount bharo, warna minimum due bharo. Bills mere savings account se bharo, lekin agar kisi payment se savings \u20b9{floor} se neeche chala jaaye, toh wo bill aur uske baad ke saare bills mere salary account se bharo. Har bill pe ek remark daalo ki wo kaunsa bill hai.",
    "clauses": {
        "bill_1": "Pehle {bill_1} bharo.",
        "bill_2": "Phir {bill_2}.",
        "bill_3": "Phir {bill_3}.",
        "bill_4": "Phir {bill_4}.",
        "bill_5": "Phir {bill_5}.",
        "bill_6": "Phir {bill_6}.",
        "rent": "Mere landlord Vinod Deshpande ko \u20b9{rent} rent NEFT se mere salary account se bhejo.",
        "pocket": "Meri behen Kavya ko \u20b9{pocket} pocket money IMPS se mere savings account se bhejo.",
        "wallet": "Mera {wallet} wallet mere salary account se itna top up karo ki uska balance exactly \u20b9{wallet_target} ho jaaye.",
        "merchant": "Andheri West ke Sharma Kirana Stores ko mere savings account se UPI se \u20b9{m_amount} pay karo.",
        "submit": "Poora batch {sched_day} November 2026 ke liye schedule karo aur payment summary {notify} ko bhejo."
    },
    "terms": {
        "bill": {
            "elec_home": "Andheri wale humare ghar ka electricity bill",
            "elec_nani": "Pune mein Nani ke ghar ka electricity bill",
            "gas": "piped gas ka bill",
            "broadband": "broadband ka bill",
            "mobile_father": "Papa ka postpaid mobile bill",
            "mobile_mother": "Mummy ka postpaid mobile bill"
        },
        "wallet": {
            "WL-AMZ-1": "Amazon Pay",
            "WL-PTM-1": "Paytm",
            "WL-PPE-1": "PhonePe"
        },
        "relation": {
            "papa": "Papa",
            "mummy": "Mummy"
        }
    }
}
