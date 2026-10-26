"""
Pay domain: month-end household payments (docs/LONG_SPEC.md). About 32
tool calls: six bills with an amount rule and a running-balance rule, two
transfers, a standing instruction, budget tags for every bill payment, and
an OTP-confirmed batch.

Drift pressure:
  entity drift    two electricity connections (home and Nani's house) with
                  near-identical consumer numbers plus an inactive old one;
                  two postpaid mobiles one digit-pair apart; two payees
                  called Kavya Sharma; Vinod Deshpande next to Vinod
                  Deshmukh; Sunita next to Sunil Sharma
  semantic drift  every bill payment carries a remark, so "remark names the
                  right bill, money went to the wrong biller" is observable
  carried state   the savings floor rule depends on a running balance and
                  stays switched once triggered; tags at the end refer back
                  to transaction ids from 15-25 steps earlier
  re-grounding    the IMPS transfer to Didi fails with a limit error; the
                  retry must keep amount, account and remark
"""

import random

from env.long.base import I, LongTools, N, S, fn, is_neighbour, neighbour_id

BILLS = ["elec_home", "elec_nani", "gas", "broadband", "mobile_father", "mobile_mother"]
CATEGORY_OF = {"elec_home": "electricity", "elec_nani": "electricity", "gas": "gas", "broadband": "broadband",
               "mobile_father": "mobile_postpaid", "mobile_mother": "mobile_postpaid"}
TAG_OF = {"elec_home": "Utilities", "elec_nani": "Utilities", "gas": "Utilities", "broadband": "Communication",
          "mobile_father": "Communication", "mobile_mother": "Communication"}
TAGS = ["Shopping", "Utilities", "Communication", "Rent", "Family", "Other"]
REMARK_EN = {"elec_home": "Home electricity Oct", "elec_nani": "Nani electricity Pune Oct", "gas": "Piped gas Oct",
             "broadband": "Broadband Oct", "mobile_father": "Papa mobile Oct", "mobile_mother": "Mummy mobile Oct"}
SALARY, SAVINGS = "ACC-201", "ACC-202"
SESSION_DATE = "2026-10-30"


def _digits(rng, n):
    while True:
        s = "".join(rng.choice("0123456789") for _ in range(n))
        if s[0] != "0" and len(set(s)) >= n - 2:
            return s


def generate(seed: int) -> dict:
    rng = random.Random(seed)
    order = rng.sample(BILLS, 6)
    full_max = rng.choice([1500, 2000, 2500])
    amounts = {}
    for b in BILLS:
        due = rng.choice([700, 900, 1200, 1400, 1800, 2400, 2900, 3400, 3800, 4600])
        amounts[b] = {"amount_due": due, "minimum_due": max(200, int(due * rng.choice([0.25, 0.3, 0.4]) // 10 * 10))}
    late = rng.choice(order)
    fee = rng.choice([150, 250, 350])
    amounts[late]["late_fee"] = fee
    amounts[late]["amount_due"] += fee
    paid = {b: (a["amount_due"] if a["amount_due"] <= full_max else a["minimum_due"]) for b, a in amounts.items()}
    switch_at = rng.choice([2, 3, 4])
    floor = rng.choice([5000, 8000, 10000])
    before = sum(paid[b] for b in order[:switch_at])
    pocket = rng.choice([1500, 2000, 2500, 3000])
    slack = rng.randrange(10, max(11, paid[order[switch_at]] - 10))
    savings = floor + before + slack
    if savings - before < pocket:
        savings += pocket
        floor += pocket
    rent = rng.choice([18000, 22000, 25000, 28000])
    si = rng.choice([3000, 5000, 7500])
    day = rng.choice([3, 5, 7, 10])

    used = set()

    def bid():
        while True:
            v = f"B-{rng.randrange(1000, 9999)}"
            if v not in used:
                used.add(v)
                return v

    home_no = _digits(rng, 10)
    nani_no = home_no[:4] + home_no[5] + home_no[4] + home_no[6:]
    if nani_no == home_no:
        nani_no = home_no[:6] + home_no[7] + home_no[6] + home_no[8:]
    old_no = neighbour_id(home_no, rng)
    while old_no in (nani_no, home_no):
        old_no = neighbour_id(home_no, rng)
    mob_f = "98201" + _digits(rng, 5)
    mob_m = neighbour_id(mob_f, rng)
    billers = [
        {"biller_id": bid(), "bill": "elec_home", "category": "electricity", "provider": "Adani Electricity",
         "consumer_number": home_no, "registered_to": "home", "status": "active"},
        {"biller_id": bid(), "bill": "elec_nani", "category": "electricity", "provider": "MSEDCL",
         "consumer_number": nani_no, "registered_to": "nani", "status": "active"},
        {"biller_id": bid(), "bill": "elec_old", "category": "electricity", "provider": "Adani Electricity",
         "consumer_number": old_no, "registered_to": "old", "status": "inactive"},
        {"biller_id": bid(), "bill": "gas", "category": "gas", "provider": "Mahanagar Gas",
         "consumer_number": _digits(rng, 12), "registered_to": "home", "status": "active"},
        {"biller_id": bid(), "bill": "broadband", "category": "broadband", "provider": "ACT Fibernet",
         "consumer_number": _digits(rng, 9), "registered_to": "home", "status": "active"},
        {"biller_id": bid(), "bill": "broadband_old", "category": "broadband", "provider": "Hathway",
         "consumer_number": _digits(rng, 9), "registered_to": "old", "status": "inactive"},
        {"biller_id": bid(), "bill": "mobile_father", "category": "mobile_postpaid", "provider": "Airtel Postpaid",
         "consumer_number": mob_f, "registered_to": "Ramesh Sharma", "status": "active"},
        {"biller_id": bid(), "bill": "mobile_mother", "category": "mobile_postpaid", "provider": "Airtel Postpaid",
         "consumer_number": mob_m, "registered_to": "Sunita Sharma", "status": "active"},
    ]
    rng.shuffle(billers)
    bill_ids = {b["bill"]: f"BL-{rng.randrange(100000, 999999)}" for b in billers}

    def acct():
        return "XXXX" + _digits(rng, 4)

    sis = acct()
    pay_ids = rng.sample(range(3300, 3400), 6)
    payees = [
        {"payee_id": f"PY-{pay_ids[0]}", "name": "Kavya Sharma", "bank": "SBI", "account": sis, "relation": "sister", "role": "sister"},
        {"payee_id": f"PY-{pay_ids[1]}", "name": "Kavya Sharma", "bank": "HDFC Bank", "account": sis[:4] + sis[5] + sis[4] + sis[6:]
         if sis[4] != sis[5] else "XXXX" + _digits(rng, 4), "relation": "colleague", "role": "namesake"},
        {"payee_id": f"PY-{pay_ids[2]}", "name": "Vinod Deshpande", "bank": "ICICI Bank", "account": acct(), "relation": "landlord", "role": "landlord"},
        {"payee_id": f"PY-{pay_ids[3]}", "name": "Vinod Deshmukh", "bank": "Axis Bank", "account": acct(), "relation": "society", "role": "lookalike"},
        {"payee_id": f"PY-{pay_ids[4]}", "name": "Sunita Sharma", "bank": "SBI", "account": acct(), "relation": "mother", "role": "mother"},
        {"payee_id": f"PY-{pay_ids[5]}", "name": "Sunil Sharma", "bank": "PNB", "account": acct(), "relation": "uncle", "role": "uncle"},
    ]
    rng.shuffle(payees)
    base = rng.randrange(400000, 900000)
    txn_ids = []
    while len(txn_ids) < 14:
        t = f"TXN-{base + rng.randrange(0, 999):06d}"
        if t not in txn_ids:
            txn_ids.append(t)
    for i in range(0, 12, 3):
        txn_ids[i + 1] = neighbour_id(txn_ids[i], rng) if neighbour_id(txn_ids[i], rng) not in txn_ids else txn_ids[i + 1]
    return {"seed": seed, "session_date": SESSION_DATE, "order": order, "full_max": full_max, "floor": floor,
            "balances": {SALARY: 95000, SAVINGS: savings}, "amounts": amounts, "late": late, "fee": fee,
            "billers": billers, "bill_ids": bill_ids, "payees": payees, "txn_ids": txn_ids,
            "rent": rent, "pocket": pocket, "si": si, "day": day, "switch_at": switch_at}


def biller_of(world, bill):
    return next(b for b in world["billers"] if b["bill"] == bill)


def payee_of(world, role):
    return next(p for p in world["payees"] if p["role"] == role)


def expected_accounts(world: dict, sequence: list) -> dict:
    """Account each bill should come from under the floor rule, replayed
    over the actual sequence of debits. `sequence` holds (kind, bill,
    amount, account) in call order; kind is "bill" or "debit" (any other
    payment). Balances follow what was actually debited, and once the rule
    switches to salary it stays switched."""
    bal = world["balances"][SAVINGS]
    switched, out = False, {}
    for kind, bill, amount, account in sequence:
        if kind == "bill":
            if not switched and bal - amount < world["floor"]:
                switched = True
            out[bill] = SALARY if switched else SAVINGS
        if account == SAVINGS:
            bal -= amount
    return out


class PayTools(LongTools):
    TERMINAL_TOOL = "confirm_batch"
    DOMAIN = "pay"

    def __init__(self, instance, language="en", seam="S1"):
        super().__init__(instance, language, seam)
        self.batch = []
        self._txn = iter(self.world["txn_ids"])
        self.tags = {}
        self.otp = None
        self.imps_failed = False

    def tool_schemas(self):
        return [
            fn("get_accounts", "The user's bank accounts and available balances.", {}),
            fn("get_balance", "Available balance of an account, after payments already queued in the batch.", {"account_id": S}),
            fn("list_billers", "Saved billers.", {}),
            fn("fetch_bill", "Fetch the current bill of a saved biller.", {"biller_id": S}),
            fn("pay_bill", "Queue a bill payment in the batch.",
               {"bill_id": S, "account_id": S, "amount": N,
                "remark": {"type": "string", "description": "Free-text remark shown on the statement."}}),
            fn("list_payees", "Saved payees for transfers.", {}),
            fn("get_payee_details", "Details of a saved payee.", {"payee_id": S}),
            fn("transfer", "Queue a transfer to a saved payee in the batch.",
               {"payee_id": S, "account_id": S, "amount": N, "mode": {"type": "string", "enum": ["IMPS", "NEFT", "RTGS"]},
                "remark": S}),
            fn("create_standing_instruction", "Set up a monthly recurring transfer to a saved payee.",
               {"payee_id": S, "account_id": S, "amount": N,
                "day_of_month": {"type": "integer", "description": "1-28"},
                "start_month": {"type": "string", "description": "YYYY-MM"}, "remark": S}, None),
            fn("tag_transaction", "Tag a queued transaction in the budget tracker.",
               {"transaction_id": S, "category": {"type": "string", "enum": TAGS}}),
            fn("review_batch", "Everything queued in the batch.", {}),
            fn("request_otp", "Send an OTP to authorise the batch.", {}),
            fn("confirm_batch", "Authorise and execute the whole batch.", {"otp_ref": S}),
        ]

    def _account(self, acc):
        if acc not in self.world["balances"]:
            self.fail("validation", "unknown", what="account_id", value=acc)

    def _available(self, acc):
        return self.world["balances"][acc] - sum(x["amount"] for x in self.batch if x["account_id"] == acc and x["kind"] != "si")

    def get_accounts(self):
        return {"accounts": [{"account_id": SALARY, "label": self.label("account", "salary"), "bank": "HDFC Bank",
                              "number": "XX2207", "available_balance": self._available(SALARY)},
                             {"account_id": SAVINGS, "label": self.label("account", "savings"), "bank": "SBI",
                              "number": "XX5531", "available_balance": self._available(SAVINGS)}]}

    def get_balance(self, account_id):
        self._account(account_id)
        return {"account_id": account_id, "available_balance": self._available(account_id)}

    def list_billers(self):
        rows = []
        for b in self.world["billers"]:
            reg = b["registered_to"]
            rows.append({"biller_id": b["biller_id"], "category": b["category"], "provider": b["provider"],
                         "consumer_number": b["consumer_number"],
                         "registered_to": self.label("address", reg) if reg in ("home", "nani", "old") else reg,
                         "status": b["status"]})
        return {"billers": rows}

    def _biller(self, biller_id):
        b = next((b for b in self.world["billers"] if b["biller_id"] == biller_id), None)
        if b is None:
            self.fail("validation", "unknown", what="biller_id", value=biller_id)
        return b

    def fetch_bill(self, biller_id):
        b = self._biller(biller_id)
        bill_id = self.world["bill_ids"][b["bill"]]
        if b["status"] != "active":
            return {"biller_id": biller_id, "bill_id": bill_id, "amount_due": 0, "minimum_due": 0, "due_date": None,
                    "status": "no bill due"}
        a = self.world["amounts"][b["bill"]]
        out = {"biller_id": biller_id, "bill_id": bill_id, "amount_due": a["amount_due"], "minimum_due": a["minimum_due"],
               "due_date": "2026-11-05"}
        if "late_fee" in a:
            out["notice"] = self.text("late_fee", fee=a["late_fee"])
        return out

    def _bill_by_id(self, bill_id):
        name = next((k for k, v in self.world["bill_ids"].items() if v == bill_id), None)
        if name is None:
            self.fail("validation", "unknown", what="bill_id", value=bill_id)
        return name

    def pay_bill(self, bill_id, account_id, amount, remark):
        name = self._bill_by_id(bill_id)
        self._account(account_id)
        a = self.world["amounts"].get(name)
        if a is None or a["amount_due"] == 0:
            self.bad(f"bill {bill_id} has nothing due")
        if not a["minimum_due"] <= amount <= a["amount_due"]:
            self.fail("validation", "amount_range", min=a["minimum_due"], due=a["amount_due"])
        if amount > self._available(account_id):
            self.fail("validation", "funds", account=account_id)
        txn = next(self._txn)
        self.batch.append({"kind": "bill", "transaction_id": txn, "bill_id": bill_id, "bill": name,
                           "biller_id": biller_of(self.world, name)["biller_id"], "account_id": account_id,
                           "amount": amount, "remark": remark})
        return {"transaction_id": txn, "status": "queued", "message": self.text("queued")}

    def list_payees(self):
        return {"payees": [{k: p[k] for k in ("payee_id", "name", "bank", "account")} for p in self.world["payees"]]}

    def _payee(self, payee_id):
        p = next((p for p in self.world["payees"] if p["payee_id"] == payee_id), None)
        if p is None:
            self.fail("validation", "unknown", what="payee_id", value=payee_id)
        return p

    def get_payee_details(self, payee_id):
        p = self._payee(payee_id)
        return {"payee_id": payee_id, "name": p["name"], "bank": p["bank"], "account": p["account"],
                "relation": self.label("relation", p["relation"]), "imps_enabled": True, "neft_enabled": True}

    def transfer(self, payee_id, account_id, amount, mode, remark):
        p = self._payee(payee_id)
        self._account(account_id)
        if p["role"] == "sister" and mode == "IMPS":
            self.imps_failed = True
            self.fail("business", "imps_limit")
        if amount > self._available(account_id):
            self.fail("validation", "funds", account=account_id)
        txn = next(self._txn)
        self.batch.append({"kind": "transfer", "transaction_id": txn, "payee_id": payee_id, "account_id": account_id,
                           "amount": amount, "mode": mode, "remark": remark})
        return {"transaction_id": txn, "status": "queued", "message": self.text("queued")}

    def create_standing_instruction(self, payee_id, account_id, amount, day_of_month, start_month, remark=None):
        self._payee(payee_id)
        self._account(account_id)
        if not 1 <= int(day_of_month) <= 28:
            self.bad("day_of_month must be 1-28")
        txn = next(self._txn)
        self.batch.append({"kind": "si", "transaction_id": txn, "payee_id": payee_id, "account_id": account_id,
                           "amount": amount, "day_of_month": int(day_of_month), "start_month": start_month, "remark": remark})
        return {"standing_instruction_id": txn, "status": "queued", "message": self.text("queued")}

    def tag_transaction(self, transaction_id, category):
        if transaction_id not in {x["transaction_id"] for x in self.batch}:
            self.fail("validation", "unknown", what="transaction_id", value=transaction_id)
        self.tags[transaction_id] = category
        return {"transaction_id": transaction_id, "category": category}

    def review_batch(self):
        return {"items": [{k: v for k, v in x.items() if k not in ("bill",)} for x in self.batch]}

    def request_otp(self):
        self.otp = f"OTP-{len(self.batch):02d}{self.world['seed'] % 97:02d}"
        return {"otp_ref": self.otp, "sent_to": "XXXXXX4517"}

    def snapshot(self) -> dict:
        """State at the end of an episode, for scoring when the agent stopped
        to hand the OTP to the user instead of confirming the batch."""
        return {"status": "queued", "otp_requested": self.otp is not None,
                "items": [dict(x, tag=self.tags.get(x["transaction_id"])) for x in self.batch]}

    def confirm_batch(self, otp_ref):
        if self.otp is None or otp_ref != self.otp:
            self.fail("validation", "bad_otp", ref=otp_ref)
        return {"status": "executed", "items": [dict(x, tag=self.tags.get(x["transaction_id"])) for x in self.batch]}


def plan_from_answer(world: dict) -> dict:
    accounts, seq, bal, switched = {}, [], world["balances"][SAVINGS], False
    for b in world["order"]:
        a = world["amounts"][b]
        amt = a["amount_due"] if a["amount_due"] <= world["full_max"] else a["minimum_due"]
        if not switched and bal - amt < world["floor"]:
            switched = True
        accounts[b] = SALARY if switched else SAVINGS
        bal -= amt if accounts[b] == SAVINGS else 0
        seq.append((b, amt))
    return {"bills": [{"bill": b, "amount": amt, "account": accounts[b], "remark": REMARK_EN[b],
                       "biller": biller_of(world, b)["biller_id"]} for b, amt in seq],
            "rent_payee": payee_of(world, "landlord")["payee_id"], "pocket_payee": payee_of(world, "sister")["payee_id"],
            "si_payee": payee_of(world, "mother")["payee_id"], "tags": dict(TAG_OF), "pocket_account": SAVINGS,
            "pocket_amount": world["pocket"]}


def chain(world: dict, plan: dict) -> list[dict]:
    steps = []

    def add(tool, **args):
        steps.append({"tool": tool, "args": args})

    add("get_accounts")
    add("list_billers")
    txn_of, n = {}, 0
    for b in plan["bills"]:
        add("fetch_bill", biller_id=b["biller"])
        paid_bill = next(x["bill"] for x in world["billers"] if x["biller_id"] == b["biller"])
        add("pay_bill", bill_id=world["bill_ids"][paid_bill], account_id=b["account"], amount=b["amount"], remark=b["remark"])
        txn_of[b["bill"]] = world["txn_ids"][n]
        n += 1
    add("get_balance", account_id=SAVINGS)
    add("list_payees")
    add("get_payee_details", payee_id=plan["rent_payee"])
    add("transfer", payee_id=plan["rent_payee"], account_id=SALARY, amount=world["rent"], mode="NEFT", remark="Rent October")
    n += 1
    add("get_payee_details", payee_id=plan["pocket_payee"])
    add("transfer", payee_id=plan["pocket_payee"], account_id=plan["pocket_account"], amount=plan["pocket_amount"],
        mode="IMPS", remark="Pocket money")
    add("transfer", payee_id=plan["pocket_payee"], account_id=plan["pocket_account"], amount=plan["pocket_amount"],
        mode="NEFT", remark="Pocket money")
    n += 1
    add("get_payee_details", payee_id=plan["si_payee"])
    add("create_standing_instruction", payee_id=plan["si_payee"], account_id=SALARY, amount=world["si"],
        day_of_month=world["day"], start_month="2026-11", remark="Monthly to Mummy")
    for b in world["order"]:
        add("tag_transaction", transaction_id=txn_of[b], category=plan["tags"][b])
    add("review_batch")
    add("request_otp")
    add("confirm_batch", otp_ref=f"OTP-{n + 1:02d}{world['seed'] % 97:02d}")
    return steps


def render_request(world: dict, lex: dict, lang: str) -> str:
    r = lex["request"][lang]
    names = lex["bills"][lang]
    bills = r["join"].join(names[b] for b in world["order"])
    fmt = lambda x: f"{x:,}"
    text = [r["intro"]]
    vals = {"bills": bills, "full_max": fmt(world["full_max"]), "floor": fmt(world["floor"]), "rent": fmt(world["rent"]),
            "landlord": r["landlord"], "pocket": fmt(world["pocket"]), "si": fmt(world["si"]), "day": world["day"]}
    text += [line.format(**vals) for line in r["lines"]]
    return "\n".join(text)


def check_rules(world: dict) -> None:
    plan = plan_from_answer(world)
    accounts = [b["account"] for b in plan["bills"]]
    k = accounts.index(SALARY) if SALARY in accounts else None
    assert k is not None and 1 <= k <= 4, (world["seed"], "floor rule does not switch mid-way", accounts)
    assert accounts[k:] == [SALARY] * (6 - k), (world["seed"], accounts)
    amounts = [b["amount"] for b in plan["bills"]]
    fulls = [world["amounts"][b["bill"]]["amount_due"] <= world["full_max"] for b in plan["bills"]]
    assert 1 <= sum(fulls) <= 5, (world["seed"], "amount rule does not bind both ways")
    late = world["late"]
    a = world["amounts"][late]
    assert sum(1 for b in world["billers"] if b["category"] == "electricity") == 3
    nos = {b["bill"]: b["consumer_number"] for b in world["billers"]}
    assert is_neighbour(nos["mobile_father"], nos["mobile_mother"]), world["seed"]
    assert world["billers"][0]["bill"] not in (world["order"][0],), (world["seed"], "first bill listed first")
    after_bills = world["balances"][SAVINGS] - sum(b["amount"] for b in plan["bills"] if b["account"] == SAVINGS)
    assert after_bills >= world["pocket"], (world["seed"], "no room for pocket money")


# --- verification -----------------------------------------------------------

def _remark_matches(lex, bill, remark):
    text = (remark or "").lower()
    return any(k.lower() in text for k in lex["remark_keywords"][bill])


def verify(traj, instance: dict, sold_out: set, final_state: dict | None = None, lex: dict | None = None) -> dict:
    from env.long.base import load_lexicon
    from env.long.shop import summarize
    lex = lex or load_lexicon("pay")
    world = instance["world"]
    steps = traj.steps
    term = traj.terminal_state or final_state or {}
    done = term.get("status") == "executed"
    items = term.get("items", [])
    checks, cls, commit, drift, reground, prior = {}, {}, {}, {}, {}, {}

    def put(name, klass, ok, step, kind=None, rg=False, evidence=None):
        checks[name], cls[name], commit[name] = bool(ok), klass, step
        if not ok:
            drift[name] = kind or "other"
            prior[name] = bool(evidence)
        reground[name] = rg

    def acted_before(step, tool, key, value):
        return any(s["tool"] == tool and s["args"].get(key) == value and "result" in s
                   for s in steps[:max(0, (step or len(steps) + 1) - 1)])

    step_of = {}
    for i, s in enumerate(steps, 1):
        if s["tool"] in ("pay_bill", "transfer", "create_standing_instruction") and "result" in s:
            t = s["result"].get("transaction_id") or s["result"].get("standing_instruction_id")
            step_of.setdefault(t, i)
    tag_step = {s["args"].get("transaction_id"): i for i, s in enumerate(steps, 1) if s["tool"] == "tag_transaction" and "result" in s}

    bills = [x for x in items if x["kind"] == "bill"]
    seq = [("bill" if x["kind"] == "bill" else "debit", x.get("bill"), x["amount"], x["account_id"])
           for x in sorted(items, key=lambda x: step_of.get(x["transaction_id"], 0)) if x["kind"] != "si"]
    expected_acc = expected_accounts(world, seq)
    active = {b["biller_id"]: b for b in world["billers"]}
    for bill in BILLS:
        mine = [x for x in bills if x["bill"] == bill]
        a = world["amounts"][bill]
        if len(mine) != 1:
            wrong = next((x for x in bills if x["bill"] != bill and _remark_matches(lex, bill, x["remark"])), None)
            kind = "semantic" if wrong else "other"
            if wrong:
                right_no = biller_of(world, bill)["consumer_number"]
                if is_neighbour(active[wrong["biller_id"]]["consumer_number"], right_no):
                    kind = "neighbour_id"
            wstep = step_of.get(wrong["transaction_id"]) if wrong else None
            put(f"bill.{bill}.paid", "selection", False, wstep, kind,
                evidence=acted_before(wstep, "fetch_bill", "biller_id", biller_of(world, bill)["biller_id"]))
            continue
        x = mine[0]
        st = step_of.get(x["transaction_id"])
        put(f"bill.{bill}.paid", "selection", True, st)
        want_amt = a["amount_due"] if a["amount_due"] <= world["full_max"] else a["minimum_due"]
        put(f"bill.{bill}.amount", "attribute", x["amount"] == want_amt, st,
            "semantic" if bill == world["late"] and x["amount"] == a["amount_due"] - a.get("late_fee", 0) else "other")
        put(f"bill.{bill}.account", "binding", x["account_id"] == expected_acc.get(bill), st, "other")
        tag = items_tag(x)
        put(f"bill.{bill}.tag", "binding", tag == TAG_OF[bill], tag_step.get(x["transaction_id"]),
            "entity_swap" if tag in TAGS and tag != TAG_OF[bill] else "other")
        others = [b for b in BILLS if b != bill]
        if not _remark_matches(lex, bill, x["remark"]) and any(_remark_matches(lex, o, x["remark"]) for o in others):
            drift[f"bill.{bill}.remark_label"] = "semantic"
    put("bills.no_extra", "global", len(bills) == 6 and all(active[x["biller_id"]]["status"] == "active" for x in bills),
        len(steps), "neighbour_id" if any(active[x["biller_id"]]["status"] != "active" for x in bills) else "other")

    transfers = [x for x in items if x["kind"] == "transfer"]
    for role, label, amount, mode, account, word in (("landlord", "rent", world["rent"], "NEFT", SALARY, "rent"),
                                                      ("sister", "pocket", world["pocket"], "NEFT", SAVINGS, "pocket")):
        want = payee_of(world, role)
        rg = role == "sister"
        cands = [x for x in transfers if word in (x["remark"] or "").lower()] or \
                [x for x in transfers if abs(x["amount"] - amount) < 1]
        if not cands:
            put(f"transfer.{label}.present", "selection", False, None, "other", rg)
            continue
        x = cands[0]
        st = step_of.get(x["transaction_id"])
        got = next(p for p in world["payees"] if p["payee_id"] == x["payee_id"])
        put(f"transfer.{label}.payee", "selection", got["payee_id"] == want["payee_id"], st,
            "neighbour_id" if got["role"] in ("namesake", "lookalike", "uncle") else "entity_swap", rg,
            acted_before(st, "get_payee_details", "payee_id", want["payee_id"]))
        put(f"transfer.{label}.amount", "attribute", abs(x["amount"] - amount) < 1, st, "other", rg)
        put(f"transfer.{label}.mode", "attribute", x["mode"] == mode, st, "other", rg)
        put(f"transfer.{label}.account", "binding", x["account_id"] == account, st,
            "entity_swap" if x["account_id"] in (SALARY, SAVINGS) else "other", rg)
    put("transfers.count", "global", len(transfers) == 2, len(steps))

    sis = [x for x in items if x["kind"] == "si"]
    if len(sis) != 1:
        put("si.present", "selection", False, None)
    else:
        x = sis[0]
        st = step_of.get(x["transaction_id"])
        got = next(p for p in world["payees"] if p["payee_id"] == x["payee_id"])
        put("si.payee", "selection", got["role"] == "mother", st, "neighbour_id" if got["role"] == "uncle" else "entity_swap",
            evidence=acted_before(st, "get_payee_details", "payee_id", payee_of(world, "mother")["payee_id"]))
        put("si.amount", "attribute", abs(x["amount"] - world["si"]) < 1, st)
        put("si.day", "attribute", x["day_of_month"] == world["day"], st)
        put("si.start", "attribute", x["start_month"] == "2026-11", st)
        put("si.account", "binding", x["account_id"] == SALARY, st, "entity_swap")
    put("batch.confirmed", "global", done, len(steps))
    return summarize(traj, instance, checks, cls, commit, drift, reground, done, prior)


def items_tag(x):
    return x.get("tag")


# --- scripted faults --------------------------------------------------------

FAULTS = ("wrong_electricity", "swap_tags", "floor_rule_forgotten", "retry_wrong_account")


def faulty_plan(world: dict, mode: str):
    plan = plan_from_answer(world)
    if mode == "wrong_electricity":
        b = next(x for x in plan["bills"] if x["bill"] == "elec_nani")
        home = next(x for x in plan["bills"] if x["bill"] == "elec_home")
        b["biller"], b["amount"] = biller_of(world, "elec_home")["biller_id"], home["amount"]
        return plan, "pay_home_twice"
    if mode == "swap_tags":
        plan["tags"] = dict(plan["tags"], elec_home="Communication", broadband="Utilities")
        return plan, None
    if mode == "floor_rule_forgotten":
        for b in plan["bills"]:
            b["account"] = SAVINGS
        return plan, None
    if mode == "retry_wrong_account":
        plan["pocket_account"] = SALARY
        return plan, None
    raise ValueError(mode)
