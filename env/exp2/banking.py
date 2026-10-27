"""
Banking domain (Experiment 2). A set of service requests on a net-banking
app, queued and submitted together with one OTP. Nothing here is a payment:
the constraints are about picking the right record among near-identical
ones and carrying ids and values between requests.

Stages (long format order):
  dispute       raise a dispute on the duplicate (later) of two identical
                charges, with the right reason
  card_block    block the lost debit card, not the credit card with the
                same last four digits, with the right reason
  card_replace  replacement for the blocked card, to the stated address
  card_limit    international online limit on the other debit card
  fd_open       FD in the highest-rate scheme inside a tenure window that
                allows premature withdrawal, from savings, with a payout
  rd_open       RD from salary that matures in the same month as the FD
                (coupled: its tenure is the chosen FD scheme's tenure)
  nominee       Mummy as nominee on the new FD (carried: the FD id is the
                one open_fd returned, not an older deposit)
  cheque_stop   stop the cheque issued to a named payee for a stated amount
  submit        anchors: confirmation channel and home branch, committed
                only in confirm_requests
"""

import random

from env.exp2.core import I, N, S, Exp2Tools, assert_never_first, check, enum, fn, step_of, summarize, term
from env.long.base import neighbour_id

DOMAIN = "banking"
SESSION_DATE = "2026-10-30"
SAVINGS, SALARY = "ACC-301", "ACC-302"
REASONS_DISPUTE = ["duplicate", "not_received", "fraud", "wrong_amount"]
REASONS_BLOCK = ["lost", "stolen", "damaged", "suspected_fraud"]
REASONS_CHEQUE = ["lost", "payment_cancelled", "other"]
CHANNELS = ["sms", "email", "both"]
PAYOUTS = ["cumulative", "monthly", "quarterly"]
MERCHANTS = {"swiggy": ("Swiggy", "Swiggy Instamart"), "zomato": ("Zomato", "Zomato Blinkit"),
             "amazon": ("Amazon", "Amazon Pay Later"), "uber": ("Uber", "Uber Eats"),
             "bigbasket": ("BigBasket", "BigBasket Daily")}
BRANCHES = {"andheri_west": ("Andheri West", "Andheri East"), "bandra_west": ("Bandra West", "Bandra East"),
            "malad_west": ("Malad West", "Malad East")}
ADDRESSES = [{"address_id": "ADR-31", "label": "Office", "line": "Tower B, Mindspace, Malad West, Mumbai"},
             {"address_id": "ADR-13", "label": "Home", "line": "Flat 1203, Lokhandwala, Andheri West, Mumbai"},
             {"address_id": "ADR-33", "label": "Old office", "line": "Unit 4, Kanakia, Andheri East, Mumbai"}]
ADDRESS_OF = {"office": "ADR-31", "home": "ADR-13"}
FAMILY = [{"member_id": "FM-12", "name": "Sunil Sharma", "relation": "uncle"},
          {"member_id": "FM-21", "name": "Sunita Sharma", "relation": "mother"},
          {"member_id": "FM-27", "name": "Kavya Sharma", "relation": "sister"},
          {"member_id": "FM-72", "name": "Ramesh Sharma", "relation": "father"}]
NOMINEE = {"mummy": "FM-21", "papa": "FM-72"}
NOMINEE_DECOY = {"mummy": "FM-12", "papa": "FM-27"}

SCENARIOS = [
    {"id": 1, "seed": 11, "merchant": "swiggy", "block_reason": "lost", "window": (12, 24), "payout": "cumulative",
     "replace_to": "office", "nominee": "mummy", "channel": "email", "branch": "andheri_west"},
    {"id": 2, "seed": 22, "merchant": "amazon", "block_reason": "stolen", "window": (6, 18), "payout": "quarterly",
     "replace_to": "home", "nominee": "papa", "channel": "sms", "branch": "bandra_west"},
    {"id": 3, "seed": 33, "merchant": "uber", "block_reason": "lost", "window": (18, 36), "payout": "cumulative",
     "replace_to": "office", "nominee": "papa", "channel": "email", "branch": "malad_west"},
    {"id": 4, "seed": 44, "merchant": "zomato", "block_reason": "stolen", "window": (12, 30), "payout": "monthly",
     "replace_to": "home", "nominee": "mummy", "channel": "sms", "branch": "andheri_west"},
    {"id": 5, "seed": 55, "merchant": "bigbasket", "block_reason": "lost", "window": (24, 48), "payout": "quarterly",
     "replace_to": "office", "nominee": "mummy", "channel": "email", "branch": "bandra_west"},
]
FORMATS = {
    "short": ["dispute", "submit"],
    "medium": ["dispute", "card_block", "fd_open", "submit"],
    "long": ["dispute", "card_block", "card_replace", "card_limit", "fd_open", "rd_open", "nominee", "cheque_stop",
             "submit"],
}
ANCHOR_STAGE = "submit"


def _add_months(ym, n):
    y, m = ym
    m += n
    return y + (m - 1) // 12, (m - 1) % 12 + 1


def generate(scenario):
    rng = random.Random(scenario["seed"])
    used = set()

    def uid(prefix, lo=100000, hi=999999):
        while True:
            v = f"{prefix}{rng.randrange(lo, hi)}"
            if v not in used:
                used.add(v)
                return v

    name, look = MERCHANTS[scenario["merchant"]]
    amt = rng.choice([349, 486, 612, 799, 1149, 1385])
    day = rng.randrange(18, 25)
    date = f"2026-10-{day:02d}"
    hh, mm = rng.randrange(12, 21), rng.randrange(5, 50)
    t1, t2 = f"{hh:02d}:{mm:02d}", f"{hh:02d}:{mm + rng.randrange(1, 6):02d}"
    others = [("Reliance Digital", 2499), ("Indian Oil", 1500), ("Apollo Pharmacy", 642), ("BookMyShow", 560),
              ("DMart", 2187)]
    rng.shuffle(others)
    txns = [
        {"merchant": others[0][0], "amount": others[0][1], "date": f"2026-10-{day + 4:02d}", "time": "10:12", "role": "filler"},
        {"merchant": name, "amount": amt, "date": date, "time": t2, "role": "duplicate"},
        {"merchant": look, "amount": amt, "date": date, "time": f"{hh + 1:02d}:{mm:02d}", "role": "lookalike"},
        {"merchant": name, "amount": amt, "date": date, "time": t1, "role": "original"},
        {"merchant": name, "amount": amt, "date": f"2026-10-{day - 6:02d}", "time": t1, "role": "earlier"},
        {"merchant": name, "amount": amt + 120, "date": date, "time": f"{hh - 3:02d}:{mm:02d}", "role": "other_amount"},
        {"merchant": others[1][0], "amount": others[1][1], "date": f"2026-10-{day - 2:02d}", "time": "19:40", "role": "filler"},
        {"merchant": others[2][0], "amount": others[2][1], "date": f"2026-10-{day - 9:02d}", "time": "08:55", "role": "filler"},
    ]
    txns.sort(key=lambda t: (t["date"], t["time"]), reverse=True)
    for t in txns:
        t["txn_id"] = uid("TX-")
    dup = next(t for t in txns if t["role"] == "duplicate")
    orig = next(t for t in txns if t["role"] == "original")
    orig["txn_id"] = neighbour_id(dup["txn_id"], rng)

    last4 = rng.choice(["4417", "5283", "6091", "7364", "8125"])
    other4 = last4[:2] + last4[3] + last4[2]
    cards = [{"card_id": f"CC-{last4}", "type": "credit", "network": "Visa", "last4": last4, "linked_account": None,
              "role": "lookalike"},
             {"card_id": f"DC-{other4}", "type": "debit", "network": "RuPay", "last4": other4, "linked_account": SALARY,
              "role": "salary_debit"},
             {"card_id": f"DC-{last4}", "type": "debit", "network": "Visa", "last4": last4, "linked_account": SAVINGS,
              "role": "lost"}]

    lo, hi = scenario["window"]
    inside = sorted({lo, (lo + hi) // 2 // 3 * 3, hi})
    schemes = []
    best_t = rng.choice(inside)
    base_rate = rng.choice([6.8, 7.0, 7.1])
    for t in sorted({3, 6, 9, 12, 18, 24, 30, 36, 48, 60} | set(inside)):
        if lo <= t <= hi:
            r = base_rate + (0.45 if t == best_t else rng.choice([0.0, 0.1, 0.2]))
        else:
            r = base_rate + rng.choice([-0.6, -0.3, 0.1])
        schemes.append({"tenure_months": t, "rate": round(r, 2), "premature_withdrawal": True, "role": "filler"})
    best = next(s for s in schemes if s["tenure_months"] == best_t)
    best["role"] = "answer"
    out_t = next(t for t in (60, 48, 36, 3) if not lo <= t <= hi)
    outside = next(s for s in schemes if s["tenure_months"] == out_t)
    outside.update(rate=round(best["rate"] + 0.35, 2), role="outside_window")
    in_other = [s for s in schemes if lo <= s["tenure_months"] <= hi and s["role"] == "filler"]
    lock_t = rng.choice(in_other)["tenure_months"]
    schemes.append({"tenure_months": lock_t, "rate": round(best["rate"] + 0.25, 2), "premature_withdrawal": False,
                    "role": "no_withdrawal"})
    rng.shuffle(schemes)
    while schemes[0]["role"] == "answer":
        rng.shuffle(schemes)
    for s in schemes:
        s["scheme_id"] = uid("FDS-", 100, 999)
        s["name"] = ("Non-Callable FD " if not s["premature_withdrawal"] else "Regular FD ") + f"{s['tenure_months']}M"
    fd_amount = rng.choice([50000, 75000, 100000, 150000])
    fd_id = uid("FD-", 10000, 99999)
    old_fd = neighbour_id(fd_id, rng)
    deposits = [{"deposit_id": old_fd, "type": "FD", "amount": 40000, "opened": "2025-03-14", "nominee": None},
                {"deposit_id": uid("RD-", 10000, 99999), "type": "RD", "amount": 2000, "opened": "2025-08-01",
                 "nominee": "FM-21"}]

    cq_payee = rng.choice(["Vinod Deshpande", "Meera Iyer", "Arjun Nair"])
    cq_look = {"Vinod Deshpande": "Vinod Deshmukh", "Meera Iyer": "Meena Iyer", "Arjun Nair": "Arjun Nayak"}[cq_payee]
    cq_amt = rng.choice([18000, 22000, 25000])
    n0 = rng.randrange(400, 900)
    cheques = [{"cheque_number": f"000{n0 + 1}", "payee": cq_payee, "amount": cq_amt - 5000, "role": "same_payee"},
               {"cheque_number": f"000{n0 + 3}", "payee": cq_look, "amount": cq_amt, "role": "lookalike"},
               {"cheque_number": f"000{n0 + 2}", "payee": cq_payee, "amount": cq_amt, "role": "answer"},
               {"cheque_number": f"000{n0 + 4}", "payee": "Society Maintenance", "amount": 3500, "role": "filler"}]
    fd_ym = _add_months((2026, 10), best_t)
    return {"seed": scenario["seed"], "scenario": scenario["id"], "session_date": SESSION_DATE,
            "merchant": scenario["merchant"], "txns": txns, "dup_amount": amt, "dup_date": date,
            "cards": cards, "last4": last4, "other4": other4, "block_reason": scenario["block_reason"],
            "replace_to": scenario["replace_to"], "limit": rng.choice([25000, 40000, 50000]),
            "window": [lo, hi], "schemes": schemes, "fd_amount": fd_amount, "payout": scenario["payout"],
            "fd_id": fd_id, "deposits": deposits, "fd_maturity": f"{fd_ym[0]}-{fd_ym[1]:02d}-30",
            "rd_amount": rng.choice([3000, 5000, 7500]), "nominee": scenario["nominee"],
            "cheques": cheques, "cq_payee": cq_payee, "cq_amount": cq_amt,
            "channel": scenario["channel"], "branch": scenario["branch"],
            "branches": _branches(scenario["branch"], rng)}


def _branches(key, rng):
    right, wrong = BRANCHES[key]
    a, b = rng.sample(range(10, 99), 2)
    out = [{"branch_id": f"BR-{b}{a}", "name": wrong, "ifsc": f"HDFC00{b}{a}"},
           {"branch_id": f"BR-{a}{b}", "name": right, "ifsc": f"HDFC00{a}{b}"},
           {"branch_id": f"BR-{a}{a}", "name": right.split()[0] + " Station Road", "ifsc": f"HDFC00{a}{a}"}]
    return out


def _role(items, role):
    return next(x for x in items if x["role"] == role)


def solve(world, stages):
    best = _role(world["schemes"], "answer")
    lost = _role(world["cards"], "lost")
    plan = {"dispute": {"txn_id": _role(world["txns"], "duplicate")["txn_id"], "reason": "duplicate"},
            "channel": world["channel"], "branch_id": world["branches"][1]["branch_id"]}
    if "card_block" in stages:
        plan["card_block"] = {"card_id": lost["card_id"], "reason": world["block_reason"]}
    if "card_replace" in stages:
        plan["card_replace"] = {"card_id": lost["card_id"], "address_id": ADDRESS_OF[world["replace_to"]]}
    if "card_limit" in stages:
        plan["card_limit"] = {"card_id": _role(world["cards"], "salary_debit")["card_id"],
                              "channel": "international_online", "amount": world["limit"]}
    if "fd_open" in stages:
        plan["fd_open"] = {"scheme_id": best["scheme_id"], "account_id": SAVINGS, "amount": world["fd_amount"],
                           "payout": world["payout"]}
    if "rd_open" in stages:
        plan["rd_open"] = {"account_id": SALARY, "monthly_amount": world["rd_amount"],
                           "tenure_months": best["tenure_months"]}
    if "nominee" in stages:
        plan["nominee"] = {"deposit_id": world["fd_id"], "member_id": NOMINEE[world["nominee"]], "share_percent": 100}
    if "cheque_stop" in stages:
        plan["cheque_stop"] = {"account_id": SAVINGS, "cheque_number": _role(world["cheques"], "answer")["cheque_number"],
                               "reason": "payment_cancelled"}
    return plan


def chain(world, stages, plan):
    steps = []

    def add(tool, **args):
        steps.append({"tool": tool, "args": args})

    add("get_accounts")
    add("list_transactions", account_id=SAVINGS)
    add("raise_dispute", **plan["dispute"])
    if "card_block" in plan:
        add("list_cards")
        add("block_card", **plan["card_block"])
    if "card_replace" in plan:
        add("get_saved_addresses")
        add("request_replacement", **plan["card_replace"])
    if "card_limit" in plan:
        add("set_card_limit", **plan["card_limit"])
    if "fd_open" in plan:
        add("list_fd_schemes")
        add("open_fd", **plan["fd_open"])
    if "rd_open" in plan:
        add("open_rd", **plan["rd_open"])
    if "nominee" in plan:
        add("list_family_members")
        add("add_nominee", **plan["nominee"])
    if "cheque_stop" in plan:
        add("list_issued_cheques", account_id=SAVINGS)
        add("stop_cheque", **plan["cheque_stop"])
    add("get_branches", city="Mumbai")
    add("request_otp")
    n = sum(1 for k in plan if k not in ("channel", "branch_id"))
    add("confirm_requests", otp_ref=_otp(world, n), notify_channel=plan["channel"], branch_id=plan["branch_id"])
    return steps


def _otp(world, n):
    return f"OTP-{n:02d}{world['seed'] % 89:02d}"


def slots(world, stages):
    return {"merchant": MERCHANTS[world["merchant"]][0], "amt": f"{world['dup_amount']:,}",
            "day": int(world["dup_date"][-2:]), "last4": world["last4"],
            "block_reason": term("block_reason", world["block_reason"]),
            "replace_to": term("address", world["replace_to"]), "limit": f"{world['limit']:,}",
            "fd_amount": f"{world['fd_amount']:,}", "lo": world["window"][0], "hi": world["window"][1],
            "payout": term("payout", world["payout"]), "rd_amount": f"{world['rd_amount']:,}",
            "nominee": term("relation", world["nominee"]), "cq_payee": world["cq_payee"],
            "cq_amount": f"{world['cq_amount']:,}", "channel": term("channel", world["channel"]),
            "branch": BRANCHES[world["branch"]][0]}


def check_rules(world, stages):
    assert world["txns"][0]["role"] != "duplicate", "never-first: transactions"
    assert_never_first(world["cards"], _role(world["cards"], "lost")["card_id"], "card_id", "cards")
    assert_never_first(world["schemes"], _role(world["schemes"], "answer")["scheme_id"], "scheme_id", "schemes")
    assert_never_first(world["branches"], world["branches"][1]["branch_id"], "branch_id", "branches")
    lo, hi = world["window"]
    ok = [s for s in world["schemes"] if lo <= s["tenure_months"] <= hi and s["premature_withdrawal"]]
    best = max(ok, key=lambda s: s["rate"])
    assert best["role"] == "answer" and sum(1 for s in ok if s["rate"] == best["rate"]) == 1, "unique FD answer"
    top = max(world["schemes"], key=lambda s: s["rate"])
    assert top["role"] != "answer", "a decoy scheme must out-rate the answer"
    lock = _role(world["schemes"], "no_withdrawal")
    assert lo <= lock["tenure_months"] <= hi and lock["rate"] > best["rate"]
    dup, orig = _role(world["txns"], "duplicate"), _role(world["txns"], "original")
    assert dup["time"] > orig["time"] and dup["txn_id"] != orig["txn_id"]
    assert len({t["txn_id"] for t in world["txns"]}) == len(world["txns"])
    assert world["fd_id"] != world["deposits"][0]["deposit_id"]


class Tools(Exp2Tools):
    TERMINAL_TOOL = "confirm_requests"
    DOMAIN = DOMAIN

    def __init__(self, instance, language="en"):
        super().__init__(instance, language)
        self.requests, self.otp, self.done, self.fd_opened = [], None, None, None
        self._n = 0

    def tool_schemas(self):
        return [
            fn("get_accounts", "The user's accounts.", {}),
            fn("list_transactions", "Card and UPI transactions on an account in the last 30 days, newest first.",
               {"account_id": S}),
            fn("raise_dispute", "Queue a dispute on a transaction.",
               {"txn_id": S, "reason": enum(REASONS_DISPUTE)}),
            fn("list_cards", "The user's cards.", {}),
            fn("block_card", "Queue a permanent block on a card.", {"card_id": S, "reason": enum(REASONS_BLOCK)}),
            fn("get_saved_addresses", "Saved addresses for card delivery.", {}),
            fn("request_replacement", "Queue a replacement for a card that is being blocked.",
               {"card_id": S, "address_id": S}),
            fn("set_card_limit", "Queue a change to a card's daily limit for one channel.",
               {"card_id": S, "channel": enum(["domestic_online", "international_online", "atm", "pos"]),
                "amount": N}),
            fn("list_fd_schemes", "Fixed deposit schemes on offer.", {}),
            fn("list_deposits", "The user's existing deposits.", {}),
            fn("open_fd", "Queue a new fixed deposit. Returns the new deposit's id.",
               {"scheme_id": S, "account_id": S, "amount": N, "payout": enum(PAYOUTS)}),
            fn("open_rd", "Queue a new recurring deposit. Returns its maturity month.",
               {"account_id": S, "monthly_amount": N, "tenure_months": I}),
            fn("list_family_members", "Family members saved for nominations.", {}),
            fn("add_nominee", "Queue a nominee on a deposit.", {"deposit_id": S, "member_id": S, "share_percent": I}),
            fn("list_issued_cheques", "Cheques issued from an account that have not been cleared.", {"account_id": S}),
            fn("stop_cheque", "Queue a stop-payment on a cheque.",
               {"account_id": S, "cheque_number": S, "reason": enum(REASONS_CHEQUE)}),
            fn("get_branches", "Branches in a city.", {"city": S}),
            fn("review_requests", "Everything queued so far.", {}),
            fn("request_otp", "Generate the OTP reference that authorises the queued requests.", {}),
            fn("confirm_requests", "Submit all queued requests together. Confirmations go out on the chosen channel "
               "and the requests are attached to the chosen home branch.",
               {"otp_ref": S, "notify_channel": enum(CHANNELS), "branch_id": S}),
        ]

    def _queue(self, kind, **fields):
        self._n += 1
        rid = f"SR-{self.world['seed']:02d}{self._n:03d}"
        self.requests.append({"kind": kind, "request_id": rid, **fields})
        return rid

    def _acc(self, a):
        if a not in (SAVINGS, SALARY):
            self.bad(f"unknown account_id '{a}'")

    def _card(self, cid):
        c = next((c for c in self.world["cards"] if c["card_id"] == cid), None)
        if c is None:
            self.bad(f"unknown card_id '{cid}'")
        return c

    def get_accounts(self):
        return {"accounts": [{"account_id": SAVINGS, "label": "Savings account", "number": "XX5531", "balance": 284500},
                             {"account_id": SALARY, "label": "Salary account", "number": "XX2207", "balance": 96200}]}

    def list_transactions(self, account_id):
        self._acc(account_id)
        if account_id == SALARY:
            return {"transactions": []}
        return {"transactions": [{k: t[k] for k in ("txn_id", "date", "time", "merchant", "amount")}
                                 for t in self.world["txns"]]}

    def raise_dispute(self, txn_id, reason):
        if txn_id not in {t["txn_id"] for t in self.world["txns"]}:
            self.bad(f"unknown txn_id '{txn_id}'")
        return {"request_id": self._queue("dispute", txn_id=txn_id, reason=reason), "status": "queued"}

    def list_cards(self):
        return {"cards": [{k: c[k] for k in ("card_id", "type", "network", "last4", "linked_account")}
                          for c in self.world["cards"]]}

    def block_card(self, card_id, reason):
        self._card(card_id)
        return {"request_id": self._queue("block", card_id=card_id, reason=reason), "status": "queued"}

    def get_saved_addresses(self):
        return {"addresses": [dict(a) for a in ADDRESSES]}

    def request_replacement(self, card_id, address_id):
        self._card(card_id)
        if address_id not in {a["address_id"] for a in ADDRESSES}:
            self.bad(f"unknown address_id '{address_id}'")
        if not any(r["kind"] == "block" and r["card_id"] == card_id for r in self.requests):
            self.bad("a replacement needs a queued block on the same card")
        return {"request_id": self._queue("replace", card_id=card_id, address_id=address_id), "status": "queued"}

    def set_card_limit(self, card_id, channel, amount):
        c = self._card(card_id)
        if c["type"] != "debit":
            self.bad("limits can only be changed on debit cards")
        if not 0 < amount <= 200000:
            self.bad("amount must be between 1 and 200000")
        return {"request_id": self._queue("limit", card_id=card_id, channel=channel, amount=amount), "status": "queued"}

    def list_fd_schemes(self):
        return {"schemes": [{k: s[k] for k in ("scheme_id", "name", "tenure_months", "rate", "premature_withdrawal")}
                            for s in self.world["schemes"]]}

    def list_deposits(self):
        out = [dict(d) for d in self.world["deposits"]]
        if self.fd_opened:
            out.append({"deposit_id": self.world["fd_id"], "type": "FD", "amount": self.fd_opened["amount"],
                        "opened": "pending", "nominee": None})
        return {"deposits": out}

    def open_fd(self, scheme_id, account_id, amount, payout):
        s = next((s for s in self.world["schemes"] if s["scheme_id"] == scheme_id), None)
        if s is None:
            self.bad(f"unknown scheme_id '{scheme_id}'")
        self._acc(account_id)
        if not 10000 <= amount <= 500000:
            self.bad("amount must be between 10000 and 500000")
        if self.fd_opened:
            self.bad("only one new fixed deposit can be queued per session")
        self.fd_opened = {"scheme_id": scheme_id, "account_id": account_id, "amount": amount, "payout": payout}
        y, m = _add_months((2026, 10), s["tenure_months"])
        rid = self._queue("fd", deposit_id=self.world["fd_id"], **self.fd_opened)
        return {"request_id": rid, "deposit_id": self.world["fd_id"], "tenure_months": s["tenure_months"],
                "maturity_month": f"{y}-{m:02d}", "status": "queued"}

    def open_rd(self, account_id, monthly_amount, tenure_months):
        self._acc(account_id)
        if not 6 <= tenure_months <= 120:
            self.bad("tenure_months must be between 6 and 120")
        y, m = _add_months((2026, 10), tenure_months)
        rid = self._queue("rd", account_id=account_id, monthly_amount=monthly_amount, tenure_months=tenure_months)
        return {"request_id": rid, "maturity_month": f"{y}-{m:02d}", "status": "queued"}

    def list_family_members(self):
        return {"members": [dict(f) for f in FAMILY]}

    def add_nominee(self, deposit_id, member_id, share_percent):
        ids = {d["deposit_id"] for d in self.world["deposits"]} | ({self.world["fd_id"]} if self.fd_opened else set())
        if deposit_id not in ids:
            self.bad(f"unknown deposit_id '{deposit_id}'")
        if member_id not in {f["member_id"] for f in FAMILY}:
            self.bad(f"unknown member_id '{member_id}'")
        if not 1 <= share_percent <= 100:
            self.bad("share_percent must be between 1 and 100")
        rid = self._queue("nominee", deposit_id=deposit_id, member_id=member_id, share_percent=share_percent)
        return {"request_id": rid, "status": "queued"}

    def list_issued_cheques(self, account_id):
        self._acc(account_id)
        if account_id == SALARY:
            return {"cheques": []}
        return {"cheques": [{k: c[k] for k in ("cheque_number", "payee", "amount")} for c in self.world["cheques"]]}

    def stop_cheque(self, account_id, cheque_number, reason):
        self._acc(account_id)
        if account_id == SAVINGS and cheque_number not in {c["cheque_number"] for c in self.world["cheques"]}:
            self.bad(f"no uncleared cheque '{cheque_number}' on {account_id}")
        if account_id == SALARY:
            self.bad(f"no uncleared cheque '{cheque_number}' on {account_id}")
        rid = self._queue("cheque", account_id=account_id, cheque_number=cheque_number, reason=reason)
        return {"request_id": rid, "status": "queued"}

    def get_branches(self, city):
        if city.strip().lower() not in ("mumbai", "bombay"):
            return {"branches": []}
        return {"branches": [dict(b) for b in self.world["branches"]]}

    def review_requests(self):
        return {"requests": [dict(r) for r in self.requests]}

    def request_otp(self):
        self.otp = _otp(self.world, len(self.requests))
        return {"otp_ref": self.otp, "note": "Pass this reference to confirm_requests."}

    def confirm_requests(self, otp_ref, notify_channel, branch_id):
        if self.otp is None or otp_ref != self.otp:
            self.bad("otp_ref does not match the latest OTP for these requests")
        if branch_id not in {b["branch_id"] for b in self.world["branches"]}:
            self.bad(f"unknown branch_id '{branch_id}'")
        if not self.requests:
            self.bad("nothing is queued")
        self.done = {"notify_channel": notify_channel, "branch_id": branch_id}
        return {"status": "submitted", "requests": len(self.requests)}

    def snapshot(self):
        return {"requests": [dict(r) for r in self.requests], "confirmed": self.done}


def verify(traj, instance, final_state):
    world, stages = instance["world"], instance["stages"]
    plan = solve(world, stages)
    steps, st = traj.steps, final_state or {}
    reqs, done = st.get("requests", []), st.get("confirmed")
    step_of_req = {}
    for i, s in enumerate(steps, 1):
        r = s.get("result")
        if isinstance(r, dict) and r.get("request_id"):
            step_of_req[r["request_id"]] = i
    checks = []

    def one(kind, pick=None):
        mine = [r for r in reqs if r["kind"] == kind and (pick is None or pick(r))]
        mine = mine or [r for r in reqs if r["kind"] == kind]
        r = mine[0] if len(mine) == 1 else None
        return r, (step_of_req.get(r["request_id"]) if r else None)

    def add(name, stage, cls, r, field, want, decoy=None, stp=None):
        got = r.get(field) if r else None
        checks.append(check(name, stage, cls, got == want, stp, want, got, decoy))

    r, s = one("dispute")
    add("dispute.txn", "dispute", "selection", r, "txn_id", plan["dispute"]["txn_id"],
        _role(world["txns"], "original")["txn_id"], s)
    add("dispute.reason", "dispute", "attribute", r, "reason", "duplicate", None, s)
    if "card_block" in plan:
        r, s = one("block")
        add("card_block.card", "card_block", "selection", r, "card_id", plan["card_block"]["card_id"],
            _role(world["cards"], "lookalike")["card_id"], s)
        add("card_block.reason", "card_block", "attribute", r, "reason", plan["card_block"]["reason"], None, s)
    if "card_replace" in plan:
        r, s = one("replace")
        add("card_replace.card", "card_replace", "carried", r, "card_id", plan["card_replace"]["card_id"],
            _role(world["cards"], "lookalike")["card_id"], s)
        other = ADDRESS_OF["home" if world["replace_to"] == "office" else "office"]
        add("card_replace.address", "card_replace", "attribute", r, "address_id", plan["card_replace"]["address_id"],
            other, s)
    if "card_limit" in plan:
        r, s = one("limit")
        add("card_limit.card", "card_limit", "selection", r, "card_id", plan["card_limit"]["card_id"],
            _role(world["cards"], "lost")["card_id"], s)
        add("card_limit.channel", "card_limit", "attribute", r, "channel", "international_online", None, s)
        add("card_limit.amount", "card_limit", "attribute", r, "amount", plan["card_limit"]["amount"], None, s)
    if "fd_open" in plan:
        r, s = one("fd")
        add("fd_open.scheme", "fd_open", "selection", r, "scheme_id", plan["fd_open"]["scheme_id"],
            _role(world["schemes"], "no_withdrawal")["scheme_id"], s)
        add("fd_open.amount", "fd_open", "attribute", r, "amount", plan["fd_open"]["amount"], None, s)
        add("fd_open.account", "fd_open", "attribute", r, "account_id", SAVINGS, SALARY, s)
        add("fd_open.payout", "fd_open", "attribute", r, "payout", plan["fd_open"]["payout"], None, s)
    if "rd_open" in plan:
        r, s = one("rd")
        add("rd_open.tenure", "rd_open", "coupled", r, "tenure_months", plan["rd_open"]["tenure_months"],
            _role(world["schemes"], "no_withdrawal")["tenure_months"], s)
        add("rd_open.amount", "rd_open", "attribute", r, "monthly_amount", plan["rd_open"]["monthly_amount"], None, s)
        add("rd_open.account", "rd_open", "attribute", r, "account_id", SALARY, SAVINGS, s)
    if "nominee" in plan:
        r, s = one("nominee", lambda x: x["deposit_id"] in (world["fd_id"], world["deposits"][0]["deposit_id"]))
        add("nominee.deposit", "nominee", "carried", r, "deposit_id", world["fd_id"],
            world["deposits"][0]["deposit_id"], s)
        add("nominee.member", "nominee", "binding", r, "member_id", plan["nominee"]["member_id"],
            NOMINEE_DECOY[world["nominee"]], s)
        add("nominee.share", "nominee", "attribute", r, "share_percent", 100, None, s)
    if "cheque_stop" in plan:
        r, s = one("cheque")
        add("cheque_stop.number", "cheque_stop", "selection", r, "cheque_number", plan["cheque_stop"]["cheque_number"],
            _role(world["cheques"], "lookalike")["cheque_number"], s)
        add("cheque_stop.reason", "cheque_stop", "attribute", r, "reason", "payment_cancelled", None, s)
    n_expected = sum(1 for k in plan if k not in ("channel", "branch_id"))
    final = step_of(steps, "confirm_requests")
    checks.append(check("requests.no_extra", "submit", "global", len(reqs) == n_expected, final, n_expected, len(reqs)))
    checks.append(check("submit.channel", "submit", "anchor", bool(done and done["notify_channel"] == plan["channel"]),
                        final, plan["channel"], done and done["notify_channel"], "both", anchor=True))
    checks.append(check("submit.branch", "submit", "anchor", bool(done and done["branch_id"] == plan["branch_id"]),
                        final, plan["branch_id"], done and done["branch_id"], world["branches"][0]["branch_id"],
                        anchor=True))
    return summarize(traj, instance, checks, completed=done is not None)


FAULTS = ("dispute_original", "dispute_reason", "anchor_channel", "anchor_branch")


def faulty_plan(world, stages, mode):
    plan = solve(world, stages)
    if mode == "dispute_original":
        plan["dispute"]["txn_id"] = _role(world["txns"], "original")["txn_id"]
        return plan, {"dispute.txn"}
    if mode == "dispute_reason":
        plan["dispute"]["reason"] = "fraud"
        return plan, {"dispute.reason"}
    if mode == "anchor_channel":
        plan["channel"] = "both"
        return plan, {"submit.channel"}
    if mode == "anchor_branch":
        plan["branch_id"] = world["branches"][0]["branch_id"]
        return plan, {"submit.branch"}
    raise ValueError(mode)
