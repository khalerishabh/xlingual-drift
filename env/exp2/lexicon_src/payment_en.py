R = "\u20b9"
LEX = {
    "intro": ("Please do my month-end payments on the banking app as one batch. For every bill: pay the full amount "
              "due if it is at most " + R + "{full_max}, otherwise pay the minimum due. Pay bills from my savings "
              "account, but if a payment would take savings below " + R + "{floor}, pay that bill and every bill "
              "after it from my salary account. Put a remark on each bill saying which bill it is."),
    "clauses": {
        "bill_1": "First pay the {bill_1}.",
        "bill_2": "Then the {bill_2}.",
        "bill_3": "Then the {bill_3}.",
        "bill_4": "Then the {bill_4}.",
        "bill_5": "Then the {bill_5}.",
        "bill_6": "Then the {bill_6}.",
        "rent": "Send " + R + "{rent} rent to my landlord Vinod Deshpande by NEFT from my salary account.",
        "pocket": "Send " + R + "{pocket} pocket money to my sister Kavya by IMPS from my savings account.",
        "wallet": "Top up my {wallet} wallet from my salary account so that its balance becomes exactly "
                  + R + "{wallet_target}.",
        "merchant": "Pay " + R + "{m_amount} by UPI from my savings account to Sharma Kirana Stores in Andheri West.",
        "submit": "Schedule the whole batch for {sched_day} November 2026 and send the payment summary to {notify}.",
    },
    "terms": {
        "bill": {"elec_home": "electricity bill for our home in Andheri",
                 "elec_nani": "electricity bill for Nani's house in Pune",
                 "gas": "piped gas bill", "broadband": "broadband bill",
                 "mobile_father": "Papa's postpaid mobile bill", "mobile_mother": "Mummy's postpaid mobile bill"},
        "wallet": {"WL-AMZ-1": "Amazon Pay", "WL-PTM-1": "Paytm", "WL-PPE-1": "PhonePe"},
        "relation": {"papa": "Papa", "mummy": "Mummy"},
    },
}
