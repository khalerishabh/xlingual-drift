"""
Payment domain (Experiment 2). Month-end household payments, built on the
long-run pay world (env/long/pay.py) without its designed IMPS failure
(recovery is tested separately, RQ4), plus a wallet top-up and a UPI
merchant payment. The batch is authorised in one final call.

Stages (long format order):
  bill_1..bill_6  one bill each, in the world's order: the right biller,
              the amount rule (full if at most a limit, else minimum due),
              the account rule (savings until a payment would take it below
              a floor, then salary for that bill and every later one), and a
              remark naming the bill
  rent        NEFT to the landlord from salary
  pocket      IMPS to Didi from savings
  wallet      top up a wallet so its balance becomes a target amount (the
              amount depends on a balance read from a tool)
  merchant    UPI payment to a named shop in a named area
  submit      anchors: processing date and the contact who gets the payment
              summary, committed only in confirm_batch

Traps: two electricity connections and two postpaid mobiles with
near-identical numbers, inactive old billers, two payees called Kavya
Sharma, Vinod Deshpande next to Vinod Deshmukh, two merchants with
near-identical UPI ids, two contacts called Ramesh Sharma.
"""

from env.exp2.core import N, S, Exp2Tools, check, enum, fn, step_of, summarize, term
from env.long import pay as base

DOMAIN = "payment"
SALARY, SAVINGS = base.SALARY, base.SAVINGS
REMARK_KEYS = {
    "elec_home": ["home", "andheri", "ghar", "veedu", "veetu", "veettu", "\u0905\u0902\u0927\u0947\u0930\u0940",
                  "\u0b85\u0ba8\u0bcd\u0ba4\u0bc7\u0bb0\u0bbf", "\u0918\u0930", "\u0bb5\u0bc0\u0b9f\u0bcd\u0b9f\u0bc1"],
    "elec_nani": ["nani", "pune", "paati", "patti", "\u0928\u093e\u0928\u0940", "\u092a\u0941\u0923\u0947",
                  "\u0baa\u0bbe\u0b9f\u0bcd\u0b9f\u0bbf", "\u0baa\u0bc1\u0ba9\u0bc7"],
    "gas": ["gas", "\u0917\u0948\u0938", "\u0b8e\u0bb0\u0bbf\u0bb5\u0bbe\u0baf\u0bc1", "\u0b95\u0bc7\u0bb8\u0bcd"],
    "broadband": ["broadband", "internet", "wifi", "\u092c\u094d\u0930\u0949\u0921\u092c\u0948\u0902\u0921",
                  "\u0baa\u0bbf\u0bb0\u0bbe\u0b9f\u0bcd\u0baa\u0bc7\u0ba3\u0bcd\u0b9f\u0bcd"],
    "mobile_father": ["papa", "father", "dad", "appa", "ramesh", "\u092a\u093e\u092a\u093e", "\u0b85\u0baa\u0bcd\u0baa\u0bbe"],
    "mobile_mother": ["mummy", "mother", "mom", "amma", "sunita", "\u092e\u092e\u094d\u092e\u0940", "\u0b85\u0bae\u0bcd\u0bae\u0bbe"],
}
CONTACTS = [{"contact_id": "C-2161", "name": "Ramesh Sharma", "group": "Work", "phone": "+91 98190 22417"},
            {"contact_id": "C-3105", "name": "Sunita Sharma", "group": "Family", "phone": "+91 98201 77340"},
            {"contact_id": "C-2116", "name": "Ramesh Sharma", "group": "Family", "phone": "+91 98201 77304"},
            {"contact_id": "C-4410", "name": "Kavya Sharma", "group": "Family", "phone": "+91 99300 18822"}]
NOTIFY = {"papa": "C-2116", "mummy": "C-3105"}
NOTIFY_DECOY = {"papa": "C-2161", "mummy": "C-2116"}
DECOY_BILL = {"elec_home": "elec_old", "elec_nani": "elec_home", "mobile_father": "mobile_mother",
              "mobile_mother": "mobile_father", "broadband": "broadband_old"}
WALLETS = [{"wallet_id": "WL-AMZ-1", "provider": "Amazon Pay"}, {"wallet_id": "WL-PTM-1", "provider": "Paytm"},
           {"wallet_id": "WL-PPE-1", "provider": "PhonePe"}]
MERCHANTS = [{"vpa": "sharmakirana.andheri@okaxis", "name": "Sharma Kirana Stores", "area": "Andheri West"},
             {"vpa": "sharmakirana.andhei@okaxis", "name": "Sharma Kirana & General", "area": "Thane"},
             {"vpa": "sharmakirana.borivali@okaxis", "name": "Sharma Kirana Stores", "area": "Borivali"}]

# Seeds are the first five (in seed order) whose worlds pass every design rule in all three formats.
SCENARIOS = [
    {"id": 1, "seed": 2, "sched_day": 1, "notify": "papa", "wallet": "WL-PTM-1", "wallet_target": 2000},
    {"id": 2, "seed": 4, "sched_day": 2, "notify": "mummy", "wallet": "WL-AMZ-1", "wallet_target": 1500},
    {"id": 3, "seed": 5, "sched_day": 3, "notify": "papa", "wallet": "WL-PPE-1", "wallet_target": 2500},
    {"id": 4, "seed": 6, "sched_day": 1, "notify": "mummy", "wallet": "WL-PTM-1", "wallet_target": 3000},
    {"id": 5, "seed": 7, "sched_day": 2, "notify": "papa", "wallet": "WL-AMZ-1", "wallet_target": 2000},
]
FORMATS = {
    "short": ["bill_1", "submit"],
    "medium": ["bill_1", "bill_2", "bill_3", "rent", "submit"],
    "long": ["bill_1", "bill_2", "bill_3", "bill_4", "bill_5", "bill_6", "rent", "pocket", "wallet", "merchant",
             "submit"],
}
ANCHOR_STAGE = "submit"


def generate(scenario):
    w = base.generate(scenario["seed"])
    w.update({"scenario": scenario["id"], "sched_date": f"2026-11-{scenario['sched_day']:02d}",
              "notify": scenario["notify"], "wallet": scenario["wallet"], "wallet_target": scenario["wallet_target"]})
    rng_vals = {"WL-AMZ-1": 410 + 7 * scenario["seed"], "WL-PTM-1": 230 + 11 * scenario["seed"],
                "WL-PPE-1": 655 + 5 * scenario["seed"]}
    w["wallet_balances"] = rng_vals
    w["merchant_amount"] = 980 + 37 * scenario["seed"]
    return w


def bills_in(world, stages):
    return [world["order"][int(s.split("_")[1]) - 1] for s in stages if s.startswith("bill_")]


def solve(world, stages):
    bal, switched, bills = world["balances"][SAVINGS], False, []
    for b in bills_in(world, stages):
        a = world["amounts"][b]
        amt = a["amount_due"] if a["amount_due"] <= world["full_max"] else a["minimum_due"]
        if not switched and bal - amt < world["floor"]:
            switched = True
        acc = SALARY if switched else SAVINGS
        if acc == SAVINGS:
            bal -= amt
        bills.append({"bill": b, "amount": amt, "account": acc, "remark": base.REMARK_EN[b],
                      "biller": base.biller_of(world, b)["biller_id"]})
    plan = {"bills": bills, "rent": None, "pocket": None, "wallet": None, "merchant": None,
            "sched_date": world["sched_date"], "notify": NOTIFY[world["notify"]]}
    if "rent" in stages:
        plan["rent"] = {"payee_id": base.payee_of(world, "landlord")["payee_id"], "account_id": SALARY,
                        "amount": world["rent"], "mode": "NEFT", "remark": "Rent October"}
    if "pocket" in stages:
        plan["pocket"] = {"payee_id": base.payee_of(world, "sister")["payee_id"], "account_id": SAVINGS,
                          "amount": world["pocket"], "mode": "IMPS", "remark": "Pocket money"}
    if "wallet" in stages:
        plan["wallet"] = {"wallet_id": world["wallet"], "account_id": SALARY,
                          "amount": world["wallet_target"] - world["wallet_balances"][world["wallet"]]}
    if "merchant" in stages:
        plan["merchant"] = {"vpa": MERCHANTS[0]["vpa"], "account_id": SAVINGS, "amount": world["merchant_amount"]}
    return plan


def chain(world, stages, plan):
    steps = []

    def add(tool, **args):
        steps.append({"tool": tool, "args": args})

    add("get_accounts")
    add("list_billers")
    for b in plan["bills"]:
        add("fetch_bill", biller_id=b["biller"])
        add("pay_bill", bill_id=world["bill_ids"][b["bill"]], account_id=b["account"], amount=b["amount"],
            remark=b["remark"])
    if plan["rent"] or plan["pocket"]:
        add("list_payees")
    if plan["rent"]:
        add("transfer", **plan["rent"])
    if plan["pocket"]:
        add("get_payee_details", payee_id=plan["pocket"]["payee_id"])
        add("transfer", **plan["pocket"])
    if plan["wallet"]:
        add("get_wallets")
        add("topup_wallet", **plan["wallet"])
    if plan["merchant"]:
        add("search_merchants", query="Sharma Kirana")
        add("pay_merchant", **plan["merchant"])
    add("get_contacts")
    add("request_otp")
    n = len(plan["bills"]) + sum(1 for k in ("rent", "pocket", "wallet", "merchant") if plan[k])
    add("confirm_batch", otp_ref=_otp(world, n), process_date=plan["sched_date"], notify_contact_id=plan["notify"])
    return steps


def _otp(world, n):
    return f"OTP-{n:02d}{world['seed'] % 97:02d}"


def slots(world, stages):
    v = {"full_max": f"{world['full_max']:,}", "floor": f"{world['floor']:,}", "rent": f"{world['rent']:,}",
         "pocket": f"{world['pocket']:,}", "wallet": term("wallet", world["wallet"]),
         "wallet_target": f"{world['wallet_target']:,}", "m_amount": f"{world['merchant_amount']:,}",
         "sched_day": int(world["sched_date"][-2:]), "notify": term("relation", world["notify"])}
    for i, b in enumerate(world["order"], 1):
        v[f"bill_{i}"] = term("bill", b)
    return v


def check_rules(world, stages):
    plan = solve(world, stages)
    if len(plan["bills"]) == 6:
        accs = [b["account"] for b in plan["bills"]]
        assert SALARY in accs and accs.index(SALARY) >= 1, "floor rule must switch mid-way in the long format"
    after = world["balances"][SAVINGS] - sum(b["amount"] for b in plan["bills"] if b["account"] == SAVINGS)
    need = (plan["pocket"]["amount"] if plan["pocket"] else 0) + (plan["merchant"]["amount"] if plan["merchant"] else 0)
    assert after >= need, "no room in savings for the later debits"
    assert world["billers"][0]["bill"] != world["order"][0], "never-first"
    if plan["wallet"]:
        assert plan["wallet"]["amount"] > 0


class Tools(Exp2Tools):
    TERMINAL_TOOL = "confirm_batch"
    DOMAIN = DOMAIN

    def __init__(self, instance, language="en"):
        super().__init__(instance, language)
        self.batch, self.otp, self.done = [], None, None
        self._t = iter(self.world["txn_ids"] + [f"TXN-9{i:05d}" for i in range(20)])

    def tool_schemas(self):
        return [
            fn("get_accounts", "The user's bank accounts and available balances (after queued payments).", {}),
            fn("list_billers", "Saved billers.", {}),
            fn("fetch_bill", "Fetch the current bill of a saved biller.", {"biller_id": S}),
            fn("pay_bill", "Queue a bill payment in the batch.",
               {"bill_id": S, "account_id": S, "amount": N, "remark": {"type": "string",
                                                                       "description": "Free-text remark shown on the statement."}}),
            fn("list_payees", "Saved payees for transfers.", {}),
            fn("get_payee_details", "Details of a saved payee, including the relation.", {"payee_id": S}),
            fn("transfer", "Queue a bank transfer to a saved payee in the batch.",
               {"payee_id": S, "account_id": S, "amount": N, "mode": enum(["IMPS", "NEFT", "RTGS"]), "remark": S}),
            fn("get_wallets", "Linked wallets and their balances.", {}),
            fn("topup_wallet", "Queue a wallet top-up from a bank account.", {"wallet_id": S, "account_id": S, "amount": N}),
            fn("search_merchants", "Search UPI merchants by name.", {"query": S}),
            fn("pay_merchant", "Queue a UPI payment to a merchant.", {"vpa": S, "account_id": S, "amount": N}),
            fn("get_contacts", "The user's contacts, for sending payment summaries.", {}),
            fn("review_batch", "Everything queued in the batch.", {}),
            fn("request_otp", "Generate the OTP reference that authorises the batch.", {}),
            fn("confirm_batch", "Authorise the whole batch: it is processed on process_date and a summary is sent "
               "to the contact.", {"otp_ref": S, "process_date": {"type": "string", "description": "YYYY-MM-DD"},
                                   "notify_contact_id": S}),
        ]

    def _acc(self, a):
        if a not in self.world["balances"]:
            self.bad(f"unknown account_id '{a}'")

    def _available(self, a):
        return self.world["balances"][a] - sum(x["amount"] for x in self.batch if x["account_id"] == a)

    def _queue(self, item):
        if item["amount"] <= 0:
            self.bad("amount must be positive")
        if item["amount"] > self._available(item["account_id"]):
            self.bad(f"insufficient available balance in {item['account_id']}")
        item["transaction_id"] = next(self._t)
        self.batch.append(item)
        return {"transaction_id": item["transaction_id"], "status": "queued"}

    def get_accounts(self):
        return {"accounts": [
            {"account_id": SALARY, "label": "Salary account", "bank": "HDFC Bank", "number": "XX2207",
             "available_balance": self._available(SALARY)},
            {"account_id": SAVINGS, "label": "Savings account", "bank": "SBI", "number": "XX5531",
             "available_balance": self._available(SAVINGS)}]}

    def list_billers(self):
        lbl = {"home": "Home - Andheri, Mumbai", "nani": "Nani's house - Pune", "old": "Old flat - Borivali"}
        return {"billers": [{"biller_id": b["biller_id"], "category": b["category"], "provider": b["provider"],
                             "consumer_number": b["consumer_number"],
                             "registered_to": lbl.get(b["registered_to"], b["registered_to"]), "status": b["status"]}
                            for b in self.world["billers"]]}

    def fetch_bill(self, biller_id):
        b = next((b for b in self.world["billers"] if b["biller_id"] == biller_id), None)
        if b is None:
            self.bad(f"unknown biller_id '{biller_id}'")
        bill_id = self.world["bill_ids"][b["bill"]]
        if b["status"] != "active":
            return {"biller_id": biller_id, "bill_id": bill_id, "amount_due": 0, "minimum_due": 0, "status": "no bill due"}
        a = self.world["amounts"][b["bill"]]
        out = {"biller_id": biller_id, "bill_id": bill_id, "amount_due": a["amount_due"],
               "minimum_due": a["minimum_due"], "due_date": "2026-11-05"}
        if "late_fee" in a:
            out["note"] = f"Amount due includes a late fee of Rs {a['late_fee']}."
        return out

    def pay_bill(self, bill_id, account_id, amount, remark):
        name = next((k for k, v in self.world["bill_ids"].items() if v == bill_id), None)
        if name is None:
            self.bad(f"unknown bill_id '{bill_id}'")
        self._acc(account_id)
        a = self.world["amounts"].get(name)
        if a is None:
            self.bad(f"bill {bill_id} has nothing due")
        if not a["minimum_due"] <= amount <= a["amount_due"]:
            self.bad(f"amount must be between the minimum due ({a['minimum_due']}) and the amount due ({a['amount_due']})")
        return self._queue({"kind": "bill", "bill": name, "bill_id": bill_id, "account_id": account_id,
                            "amount": amount, "remark": remark})

    def list_payees(self):
        return {"payees": [{k: p[k] for k in ("payee_id", "name", "bank", "account")} for p in self.world["payees"]]}

    def _payee(self, pid):
        p = next((p for p in self.world["payees"] if p["payee_id"] == pid), None)
        if p is None:
            self.bad(f"unknown payee_id '{pid}'")
        return p

    def get_payee_details(self, payee_id):
        p = self._payee(payee_id)
        return {"payee_id": payee_id, "name": p["name"], "bank": p["bank"], "account": p["account"],
                "relation": p["relation"]}

    def transfer(self, payee_id, account_id, amount, mode, remark):
        self._payee(payee_id)
        self._acc(account_id)
        return self._queue({"kind": "transfer", "payee_id": payee_id, "account_id": account_id, "amount": amount,
                            "mode": mode, "remark": remark})

    def get_wallets(self):
        return {"wallets": [dict(w, balance=self.world["wallet_balances"][w["wallet_id"]]) for w in WALLETS]}

    def topup_wallet(self, wallet_id, account_id, amount):
        if wallet_id not in self.world["wallet_balances"]:
            self.bad(f"unknown wallet_id '{wallet_id}'")
        self._acc(account_id)
        return self._queue({"kind": "wallet", "wallet_id": wallet_id, "account_id": account_id, "amount": amount})

    def search_merchants(self, query):
        q = query.lower()
        return {"merchants": [dict(m) for m in MERCHANTS[1:] + MERCHANTS[:1]
                              if any(w in m["name"].lower() for w in q.split())]}

    def pay_merchant(self, vpa, account_id, amount):
        if vpa not in {m["vpa"] for m in MERCHANTS}:
            self.bad(f"unknown vpa '{vpa}'")
        self._acc(account_id)
        return self._queue({"kind": "merchant", "vpa": vpa, "account_id": account_id, "amount": amount})

    def get_contacts(self):
        return {"contacts": [dict(c) for c in CONTACTS]}

    def review_batch(self):
        return {"items": [dict(x) for x in self.batch]}

    def request_otp(self):
        self.otp = _otp(self.world, len(self.batch))
        return {"otp_ref": self.otp, "note": "Pass this reference to confirm_batch to authorise the batch."}

    def confirm_batch(self, otp_ref, process_date, notify_contact_id):
        if self.otp is None or otp_ref != self.otp:
            self.bad("otp_ref does not match the latest OTP for this batch")
        if notify_contact_id not in {c["contact_id"] for c in CONTACTS}:
            self.bad(f"unknown notify_contact_id '{notify_contact_id}'")
        if not self.batch:
            self.bad("the batch is empty")
        self.done = {"process_date": process_date, "notify_contact_id": notify_contact_id}
        return {"status": "submitted", "items": len(self.batch)}

    def snapshot(self):
        return {"items": [dict(x) for x in self.batch], "confirmed": self.done}


_EXCLUDES = {"elec_home": "elec_nani", "mobile_father": "mobile_mother", "mobile_mother": "mobile_father"}


def _remark_ok(bill, remark):
    text = (remark or "").lower()
    other = _EXCLUDES.get(bill)
    if other and any(k in text for k in REMARK_KEYS[other]):
        return False
    return any(k in text for k in REMARK_KEYS[bill])


def verify(traj, instance, final_state):
    world, stages = instance["world"], instance["stages"]
    plan = solve(world, stages)
    steps, st = traj.steps, final_state or {}
    items, done = st.get("items", []), st.get("confirmed")
    step_of_txn = {}
    for i, s in enumerate(steps, 1):
        if "result" in s and isinstance(s["result"], dict) and s["result"].get("transaction_id"):
            step_of_txn[s["result"]["transaction_id"]] = i
    checks = []
    bills = [x for x in items if x["kind"] == "bill"]
    seq = [("bill" if x["kind"] == "bill" else "debit", x.get("bill"), x["amount"], x["account_id"]) for x in items]
    exp_acc = base.expected_accounts(world, seq)
    for i, b in enumerate(plan["bills"], 1):
        stage, name = f"bill_{i}", b["bill"]
        mine = [x for x in bills if x["bill"] == name]
        x = mine[0] if len(mine) == 1 else None
        stp = step_of_txn.get(x["transaction_id"]) if x else None
        decoy = world["bill_ids"].get(DECOY_BILL.get(name))
        got = x["bill_id"] if x else next((y["bill_id"] for y in bills if y["bill_id"] == decoy), None)
        checks.append(check(f"{stage}.paid", stage, "selection", x is not None, stp, world["bill_ids"][name], got,
                            decoy))
        checks.append(check(f"{stage}.amount", stage, "attribute", bool(x and x["amount"] == b["amount"]), stp,
                            b["amount"], x and x["amount"]))
        want_acc = exp_acc.get(name, b["account"])
        checks.append(check(f"{stage}.account", stage, "carried", bool(x and x["account_id"] == want_acc), stp,
                            want_acc, x and x["account_id"]))
        checks.append(check(f"{stage}.remark", stage, "attribute", bool(x and _remark_ok(name, x["remark"])), stp,
                            name, x and x["remark"]))
    for key, role, decoy_role in (("rent", "landlord", "lookalike"), ("pocket", "sister", "namesake")):
        if not plan[key]:
            continue
        want = plan[key]
        decoy = base.payee_of(world, decoy_role)["payee_id"]
        tr = [x for x in items if x["kind"] == "transfer" and x["payee_id"] in (want["payee_id"], decoy)]
        tr = tr or [x for x in items if x["kind"] == "transfer" and x["amount"] == want["amount"]]
        x = tr[0] if len(tr) == 1 else None
        stp = step_of_txn.get(x["transaction_id"]) if x else None
        checks.append(check(f"{key}.payee", key, "selection", bool(x and x["payee_id"] == want["payee_id"]), stp,
                            want["payee_id"], x and x["payee_id"], decoy))
        checks.append(check(f"{key}.amount", key, "attribute", bool(x and x["amount"] == want["amount"]), stp,
                            want["amount"], x and x["amount"]))
        checks.append(check(f"{key}.mode", key, "attribute", bool(x and x["mode"] == want["mode"]), stp, want["mode"],
                            x and x["mode"]))
        checks.append(check(f"{key}.account", key, "attribute", bool(x and x["account_id"] == want["account_id"]), stp,
                            want["account_id"], x and x["account_id"]))
    if plan["wallet"]:
        want = plan["wallet"]
        ws = [x for x in items if x["kind"] == "wallet"]
        x = ws[0] if len(ws) == 1 else None
        stp = step_of_txn.get(x["transaction_id"]) if x else None
        checks.append(check("wallet.id", "wallet", "selection", bool(x and x["wallet_id"] == want["wallet_id"]), stp,
                            want["wallet_id"], x and x["wallet_id"]))
        checks.append(check("wallet.amount", "wallet", "carried", bool(x and x["amount"] == want["amount"]), stp,
                            want["amount"], x and x["amount"], world["wallet_target"]))
        checks.append(check("wallet.account", "wallet", "attribute", bool(x and x["account_id"] == want["account_id"]),
                            stp, want["account_id"], x and x["account_id"]))
    if plan["merchant"]:
        want = plan["merchant"]
        ms = [x for x in items if x["kind"] == "merchant"]
        x = ms[0] if len(ms) == 1 else None
        stp = step_of_txn.get(x["transaction_id"]) if x else None
        checks.append(check("merchant.vpa", "merchant", "selection", bool(x and x["vpa"] == want["vpa"]), stp,
                            want["vpa"], x and x["vpa"], MERCHANTS[1]["vpa"]))
        checks.append(check("merchant.amount", "merchant", "attribute", bool(x and x["amount"] == want["amount"]), stp,
                            want["amount"], x and x["amount"]))
        checks.append(check("merchant.account", "merchant", "attribute",
                            bool(x and x["account_id"] == want["account_id"]), stp, want["account_id"],
                            x and x["account_id"]))
    n_expected = len(plan["bills"]) + sum(1 for k in ("rent", "pocket", "wallet", "merchant") if plan[k])
    final = step_of(steps, "confirm_batch")
    checks.append(check("batch.no_extra", "submit", "global", len(items) == n_expected, final, n_expected, len(items)))
    checks.append(check("submit.date", "submit", "anchor", bool(done and done["process_date"] == plan["sched_date"]),
                        final, plan["sched_date"], done and done["process_date"], anchor=True))
    checks.append(check("submit.notify", "submit", "anchor", bool(done and done["notify_contact_id"] == plan["notify"]),
                        final, plan["notify"], done and done["notify_contact_id"], NOTIFY_DECOY[world["notify"]],
                        anchor=True))
    return summarize(traj, instance, checks, completed=done is not None)


FAULTS = ("swap_remarks", "wrong_amount", "anchor_notify", "anchor_date")


def faulty_plan(world, stages, mode):
    plan = solve(world, stages)
    if mode == "swap_remarks":
        b = plan["bills"][0]
        other = next(k for k in base.REMARK_EN if k != b["bill"] and not any(w in base.REMARK_EN[k].lower()
                                                                              for w in REMARK_KEYS[b["bill"]]))
        b["remark"] = base.REMARK_EN[other]
        return plan, {"bill_1.remark"}
    if mode == "wrong_amount":
        n = len(plan["bills"])
        b = plan["bills"][-1]
        a = world["amounts"][b["bill"]]
        b["amount"] = a["minimum_due"] if b["amount"] == a["amount_due"] else a["amount_due"]
        bal, switched = world["balances"][SAVINGS], False
        for x in plan["bills"]:
            switched = switched or bal - x["amount"] < world["floor"]
            x["account"] = SALARY if switched else SAVINGS
            bal -= 0 if switched else x["amount"]
        return plan, {f"bill_{n}.amount"}
    if mode == "anchor_notify":
        plan["notify"] = NOTIFY_DECOY[world["notify"]]
        return plan, {"submit.notify"}
    if mode == "anchor_date":
        plan["sched_date"] = "2026-11-09"
        return plan, {"submit.date"}
    raise ValueError(mode)
