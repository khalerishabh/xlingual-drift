"""
Shopping domain (Experiment 2). Festive shopping for the family, built on
the long-run shop world (env/long/shop.py) without its mid-episode
stock-out (recovery is tested separately, RQ4).

Stages (long format order):
  item_self, item_father, item_mother, item_sister
              one item each: category, size, colour, budget, highest-rated,
              delivered by the deadline to the right address (Nani's house
              for two of them)
  item_sister is coupled in the long format: the highest-rated option that
              keeps Mummy's and Didi's items together within a joint budget
  gift        gift-wrap two named people's items
  exchange    exchange a line of a past order for the next size up
  coupon      the coupon with the biggest discount for the final cart
  checkout    anchors: payment card and delivery slot, committed only in
              checkout

Traps (from the shop world): a higher-rated product over budget, one whose
requested size and colour is out of stock, one that arrives after the
deadline; product and variant ids one digit-pair apart next to the answer;
confirm labels next to opaque variant ids; two cards of the same bank whose
last four digits differ by one swap.
"""

from env.exp2.core import I, S, Exp2Tools, check, enum, fn, step_of, summarize, term
from env.long import shop as base
from env.long.base import is_neighbour

DOMAIN = "shopping"
RELS = ("self", "father", "mother", "sister")
CARDS = {"4417": "PM-CC-4417", "4471": "PM-CC-4471"}
SLOTS = {"morning": "DS-0912", "afternoon": "DS-1215", "evening": "DS-1821"}
SLOT_LABEL = {"DS-0912": "9 am - 12 noon", "DS-1215": "12 noon - 3 pm", "DS-1821": "6 pm - 9 pm"}

# Seeds are the first five (in seed order) whose worlds pass every design rule in all three formats.
SCENARIOS = [
    {"id": 1, "seed": 5, "card": "4417", "slot": "evening"},
    {"id": 2, "seed": 13, "card": "4471", "slot": "morning"},
    {"id": 3, "seed": 14, "card": "4417", "slot": "afternoon"},
    {"id": 4, "seed": 16, "card": "4471", "slot": "evening"},
    {"id": 5, "seed": 19, "card": "4417", "slot": "morning"},
]
FORMATS = {
    "short": ["item_self", "checkout"],
    "medium": ["item_self", "item_mother", "coupon", "checkout"],
    "long": ["item_self", "item_father", "item_mother", "item_sister", "gift", "exchange", "coupon", "checkout"],
}
ANCHOR_STAGE = "checkout"


def generate(scenario):
    w = base.generate(scenario["seed"])
    w["scenario"] = scenario["id"]
    w["card"] = scenario["card"]
    w["slot"] = scenario["slot"]
    w["pair_budget"] = _pair_budget(w)
    return w


def _valid(world, rel):
    p = world["prefs"][rel]
    out = []
    for pid in world["listings"][f"{p['category']}|{p['gender']}"]:
        prod = world["products"][pid]
        if prod["price"] > p["max_price"]:
            continue
        v = next((v for v in world["variants"].values() if v["product_id"] == pid and v["size"] == p["size"]
                  and v["colour"] == p["colour"] and v["stock"] > 0), None)
        if v is None or v["eta"][p["address"]] > world["deadline"]:
            continue
        out.append((prod["rating"], prod["price"], v["variant_id"]))
    return sorted(out, reverse=True)


def _pair_budget(world):
    """Joint budget for Mummy + Didi that excludes Didi's best and admits the
    best of the cheaper ones below it; None if the world cannot support it."""
    m = _valid(world, "mother")[0]
    cands = _valid(world, "sister")
    best = cands[0]
    cheaper = [c for c in cands[1:] if c[1] < best[1]]
    if not cheaper:
        return None
    nxt = cheaper[0]
    return (m[1] + (nxt[1] + best[1]) // 2) // 50 * 50


def item_answer(world, rel, stages):
    cands = _valid(world, rel)
    if rel == "sister" and "item_mother" in stages and world.get("pair_budget"):
        m_price = _valid(world, "mother")[0][1]
        cands = [c for c in cands if m_price + c[1] <= world["pair_budget"]]
    return cands[0][2]


def coupon_best(world, lines):
    best_c, best_d = None, -1
    for c in base.coupons_for(world):
        d = base.coupon_discount(c, lines)
        if d is not None and d > best_d:
            best_c, best_d = c["code"], d
    return best_c


def exchange_variant(world):
    ex = world["exchange"]
    return next(v["variant_id"] for v in world["variants"].values() if v["product_id"] == ex["product_id"]
                and v["size"] == ex["new_size"] and v["colour"] == ex["colour"])


def solve(world, stages):
    items = {rel: item_answer(world, rel, stages) for rel in RELS if f"item_{rel}" in stages}
    lines = [{"price": world["products"][world["variants"][v]["product_id"]]["price"],
              "category": world["prefs"][r]["category"]} for r, v in items.items()]
    return {"items": items, "gift": [r for r in world["gift_pair"] if r in items] if "gift" in stages else [],
            "exchange": exchange_variant(world) if "exchange" in stages else None,
            "coupon": coupon_best(world, lines) if "coupon" in stages else None,
            "payment": CARDS[world["card"]], "slot": SLOTS[world["slot"]],
            "addresses": {r: base.ADDRESSES[world["prefs"][r]["address"]] for r in items}}


def chain(world, stages, plan):
    steps = []

    def add(tool, **args):
        steps.append({"tool": tool, "args": args})

    v = world["variants"]
    add("get_family_profile")
    line_of = {}
    for rel in RELS:
        if rel not in plan["items"]:
            continue
        p = world["prefs"][rel]
        vid = plan["items"][rel]
        add("search_products", category=p["category"], gender=p["gender"], max_price=p["max_price"])
        add("get_product_variants", product_id=v[vid]["product_id"], address_id=plan["addresses"][rel])
        add("add_to_cart", variant_id=vid, quantity=1, recipient_member_id=base.REL_ID[rel],
            address_id=plan["addresses"][rel], confirm_size=p["size"], confirm_colour=p["colour"])
        line_of[rel] = f"CL-{len(line_of) + 1}"
    for rel in plan["gift"]:
        add("set_gift_wrap", line_id=line_of[rel], recipient_member_id=base.REL_ID[rel])
    if plan["exchange"]:
        ex = world["exchange"]
        add("list_orders")
        add("get_order", order_id=ex["order_id"])
        add("get_product_variants", product_id=ex["product_id"], address_id=base.ADDRESSES["home"])
        add("request_exchange", order_line_id=ex["order_line_id"], order_id=ex["order_id"],
            new_variant_id=plan["exchange"], confirm_size=ex["new_size"])
    if plan["coupon"]:
        add("list_coupons")
        add("apply_coupon", code=plan["coupon"])
    add("get_delivery_slots")
    add("get_payment_methods")
    add("checkout", payment_id=plan["payment"], delivery_slot_id=plan["slot"])
    return steps


def _day(date):
    return int(date[-2:])


def slots(world, stages):
    v = {"deadline_day": _day(world["deadline"]), "card": world["card"], "slot": term("slot", world["slot"]),
         "pair_budget": f"{world['pair_budget']:,}" if world.get("pair_budget") else ""}
    for rel in RELS:
        p = world["prefs"][rel]
        v[f"cat_{rel}"] = term("category", p["category"])
        v[f"size_{rel}"] = p["size"]
        v[f"colour_{rel}"] = term("colour", p["colour"])
        v[f"price_{rel}"] = f"{p['max_price']:,}"
        v[f"addr_{rel}"] = term("deliver_to", p["address"])
    gp = world["gift_pair"]
    v["gift_a"], v["gift_b"] = term("relation", gp[0]), term("relation", gp[1])
    ex = world["exchange"]
    v["ex_cat"], v["ex_size"] = term("category", ex["category"]), ex["new_size"]
    return v


def check_rules(world, stages):
    if "item_sister" in stages and "item_mother" in stages:
        assert world.get("pair_budget"), "world cannot support the coupled budget"
        free = _valid(world, "sister")[0][2]
        assert item_answer(world, "sister", stages) != free, "coupled budget must change Didi's answer"
    for rel in RELS:
        if f"item_{rel}" in stages:
            vid = item_answer(world, rel, stages)
            p = world["prefs"][rel]
            listing = world["listings"][f"{p['category']}|{p['gender']}"]
            assert listing[0] != world["variants"][vid]["product_id"], "never-first"
    if "coupon" in stages:
        plan = solve(world, stages)
        lines = [{"price": world["products"][world["variants"][v]["product_id"]]["price"],
                  "category": world["prefs"][r]["category"]} for r, v in plan["items"].items()]
        ds = sorted((base.coupon_discount(c, lines) or 0) for c in base.coupons_for(world))
        assert ds[-1] > ds[-2], "coupon must have a unique best"


class Tools(Exp2Tools):
    TERMINAL_TOOL = "checkout"
    DOMAIN = DOMAIN

    def __init__(self, instance, language="en"):
        super().__init__(instance, language)
        self.coupons = base.coupons_for(self.world)
        self.cart, self.exchanges, self.coupon, self.order = [], [], None, None
        self._n = 0

    def tool_schemas(self):
        conf_size = {"type": "string", "description": "The size you selected, as the user asked for it (e.g. M, UK 8)."}
        conf_colour = {"type": "string", "description": "The colour you selected, as the user asked for it (e.g. blue)."}
        return [
            fn("get_family_profile", "Family members and saved delivery addresses on the account.", {}),
            fn("search_products", "Search products by category and gender, optionally under a maximum price (INR).",
               {"category": enum(base.CATEGORIES), "gender": enum(["men", "women"]), "max_price": {"type": "number"}},
               ["category", "gender"]),
            fn("get_product_variants", "Sizes, colours, stock and estimated delivery date to an address for a product.",
               {"product_id": S, "address_id": S}),
            fn("add_to_cart", "Add a variant to the cart for one family member, delivered to an address.",
               {"variant_id": S, "quantity": I, "recipient_member_id": S, "address_id": S,
                "confirm_size": conf_size, "confirm_colour": conf_colour}),
            fn("remove_from_cart", "Remove a cart line.", {"line_id": S}),
            fn("view_cart", "Show the cart.", {}),
            fn("set_gift_wrap", "Gift-wrap a cart line for a family member.", {"line_id": S, "recipient_member_id": S}),
            fn("list_orders", "The user's past orders, newest first.", {}),
            fn("get_order", "Lines of a past order.", {"order_id": S}),
            fn("request_exchange", "Exchange a delivered order line for another variant of the same product.",
               {"order_line_id": S, "order_id": S, "new_variant_id": S, "confirm_size": conf_size}),
            fn("list_coupons", "Coupons available to the user, with their terms.", {}),
            fn("apply_coupon", "Apply a coupon to the cart (replaces any coupon already applied).", {"code": S}),
            fn("get_delivery_slots", "Delivery time slots for this order.", {}),
            fn("get_payment_methods", "Saved payment methods.", {}),
            fn("checkout", "Place the order for everything in the cart.", {"payment_id": S, "delivery_slot_id": S}),
        ]

    def _variant(self, vid):
        v = self.world["variants"].get(vid)
        if v is None:
            self.bad(f"unknown variant_id '{vid}'")
        return v

    def _addr_key(self, aid):
        key = next((k for k, a in base.ADDRESSES.items() if a == aid), None)
        if key is None:
            self.bad(f"unknown address_id '{aid}'")
        return key

    def get_family_profile(self):
        return {"members": [{"member_id": m["member_id"], "name": m["name"], "relation": m["relation"]}
                            for m in base.MEMBERS],
                "addresses": [{"address_id": base.ADDRESSES["home"], "label": "Home - Mumbai"},
                              {"address_id": base.ADDRESSES["nani"], "label": "Nani's house - Pune"}]}

    def search_products(self, category, gender, max_price=None):
        rows = []
        for pid in self.world["listings"].get(f"{category}|{gender}", []):
            p = self.world["products"][pid]
            if max_price is None or p["price"] <= max_price:
                rows.append({k: p[k] for k in ("product_id", "name", "brand", "category", "price", "rating")})
        return {"products": rows}

    def get_product_variants(self, product_id, address_id):
        if product_id not in self.world["products"]:
            self.bad(f"unknown product_id '{product_id}'")
        key = self._addr_key(address_id)
        return {"product_id": product_id, "variants": [
            {"variant_id": v["variant_id"], "size": v["size"], "colour": v["colour"], "stock": v["stock"],
             "estimated_delivery": v["eta"][key]}
            for v in self.world["variants"].values() if v["product_id"] == product_id]}

    def add_to_cart(self, variant_id, quantity, recipient_member_id, address_id, confirm_size, confirm_colour):
        v = self._variant(variant_id)
        if recipient_member_id not in base.REL_ID.values():
            self.bad(f"unknown recipient_member_id '{recipient_member_id}'")
        self._addr_key(address_id)
        if v["stock"] <= 0:
            self.not_found(f"variant {variant_id} is out of stock")
        self._n += 1
        p = self.world["products"][v["product_id"]]
        line = {"line_id": f"CL-{self._n}", "variant_id": variant_id, "product_id": v["product_id"], "name": p["name"],
                "category": p["category"], "size": v["size"], "colour": v["colour"], "price": p["price"] * int(quantity),
                "quantity": int(quantity), "recipient_member_id": recipient_member_id, "address_id": address_id,
                "confirm_size": confirm_size, "confirm_colour": confirm_colour, "gift_wrap_for": None}
        self.cart.append(line)
        return {"line_id": line["line_id"], "product": p["name"], "price": line["price"]}

    def _line(self, line_id):
        line = next((l for l in self.cart if l["line_id"] == line_id), None)
        if line is None:
            self.bad(f"unknown line_id '{line_id}'")
        return line

    def remove_from_cart(self, line_id):
        self.cart.remove(self._line(line_id))
        return {"removed": line_id}

    def view_cart(self):
        return {"lines": [{k: l[k] for k in ("line_id", "product_id", "variant_id", "name", "size", "colour", "price",
                                             "recipient_member_id", "address_id", "gift_wrap_for")} for l in self.cart],
                "subtotal": sum(l["price"] for l in self.cart), "coupon": self.coupon}

    def set_gift_wrap(self, line_id, recipient_member_id):
        line = self._line(line_id)
        if recipient_member_id not in base.REL_ID.values():
            self.bad(f"unknown recipient_member_id '{recipient_member_id}'")
        line["gift_wrap_for"] = recipient_member_id
        return {"line_id": line_id, "gift_wrap_for": recipient_member_id}

    def list_orders(self):
        return {"orders": [{"order_id": o["order_id"], "date": o["date"], "items": len(o["lines"])}
                           for o in self.world["orders"]]}

    def get_order(self, order_id):
        o = next((o for o in self.world["orders"] if o["order_id"] == order_id), None)
        if o is None:
            self.bad(f"unknown order_id '{order_id}'")
        return {"order_id": order_id, "date": o["date"], "lines": [dict(l) for l in o["lines"]]}

    def request_exchange(self, order_line_id, order_id, new_variant_id, confirm_size):
        o = next((o for o in self.world["orders"] if o["order_id"] == order_id), None)
        if o is None:
            self.bad(f"unknown order_id '{order_id}'")
        line = next((l for l in o["lines"] if l["order_line_id"] == order_line_id), None)
        if line is None:
            self.bad(f"unknown order_line_id '{order_line_id}'")
        v = self._variant(new_variant_id)
        if v["product_id"] != line["product_id"]:
            self.bad(f"variant {new_variant_id} is not a variant of {line['product_id']}")
        ex = {"exchange_id": f"EX-{len(self.exchanges) + 1}", "order_id": order_id, "order_line_id": order_line_id,
              "new_variant_id": new_variant_id, "size": v["size"], "colour": v["colour"], "confirm_size": confirm_size}
        self.exchanges.append(ex)
        return {"exchange_id": ex["exchange_id"], "status": "exchange requested"}

    def list_coupons(self):
        return {"coupons": [{k: v for k, v in c.items() if v is not None or k == "max_discount"} for c in self.coupons]}

    def apply_coupon(self, code):
        c = next((c for c in self.coupons if c["code"] == code), None)
        if c is None:
            self.bad(f"unknown coupon '{code}'")
        d = base.coupon_discount(c, self.cart)
        if d is None:
            self.bad(f"coupon {code} is not applicable to this cart")
        self.coupon = code
        return {"code": code, "discount": d}

    def get_delivery_slots(self):
        return {"slots": [{"slot_id": "DS-1215", "window": SLOT_LABEL["DS-1215"]},
                          {"slot_id": "DS-1821", "window": SLOT_LABEL["DS-1821"]},
                          {"slot_id": "DS-0912", "window": SLOT_LABEL["DS-0912"]}]}

    def get_payment_methods(self):
        return {"payment_methods": [
            {"payment_id": "PM-UPI-1", "type": "upi", "label": "UPI (arjun@okicici)"},
            {"payment_id": "PM-CC-4471", "type": "credit_card", "label": "ICICI Bank credit card ending 4471"},
            {"payment_id": "PM-COD", "type": "cash_on_delivery", "label": "Cash on delivery"},
            {"payment_id": "PM-CC-4417", "type": "credit_card", "label": "ICICI Bank credit card ending 4417"}]}

    def checkout(self, payment_id, delivery_slot_id):
        if payment_id not in {"PM-UPI-1", "PM-CC-4471", "PM-COD", "PM-CC-4417"}:
            self.bad(f"unknown payment_id '{payment_id}'")
        if delivery_slot_id not in SLOT_LABEL:
            self.bad(f"unknown delivery_slot_id '{delivery_slot_id}'")
        if not self.cart:
            self.bad("the cart is empty")
        self.order = {"payment_id": payment_id, "slot_id": delivery_slot_id}
        return {"status": "placed", "order_id": "O-NEW-1"}

    def snapshot(self):
        return {"lines": [dict(l) for l in self.cart], "exchanges": [dict(e) for e in self.exchanges],
                "coupon": self.coupon, "order": self.order}


def verify(traj, instance, final_state):
    world, stages = instance["world"], instance["stages"]
    plan = solve(world, stages)
    steps, st = traj.steps, final_state or {}
    lines, order = st.get("lines", []), st.get("order")
    prods, vars_ = world["products"], world["variants"]
    checks = []
    add_step = {}
    for i, s in enumerate(steps, 1):
        if s["tool"] == "add_to_cart" and "result" in s:
            add_step[s["result"]["line_id"]] = i
    for rel, want in plan["items"].items():
        stage = f"item_{rel}"
        p = world["prefs"][rel]
        mine = [l for l in lines if l["recipient_member_id"] == base.REL_ID[rel]]
        l = mine[0] if len(mine) == 1 else None
        stp = add_step.get(l["line_id"]) if l else None
        got = l["variant_id"] if l else None
        roles = {prods[pid]["role"]: pid for pid in world["listings"][f"{p['category']}|{p['gender']}"]}
        want_pid = vars_[want]["product_id"]
        got_pid = l["product_id"] if l else None
        checks.append(check(f"{stage}.present", stage, "selection", l is not None, stp, want, got))
        checks.append(check(f"{stage}.price", stage, "selection", bool(l and prods[got_pid]["price"] <= p["max_price"]),
                            stp, want_pid, got_pid, roles.get("top")))
        cls = "coupled" if rel == "sister" and "item_mother" in stages and world.get("pair_budget") else "selection"
        checks.append(check(f"{stage}.best", stage, cls, got_pid == want_pid, stp, want_pid, got_pid, roles.get("neighbour")))
        checks.append(check(f"{stage}.size", stage, "attribute", bool(l and l["size"] == p["size"]), stp, p["size"],
                            l and l["size"]))
        checks.append(check(f"{stage}.colour", stage, "attribute", bool(l and l["colour"] == p["colour"]), stp,
                            p["colour"], l and l["colour"]))
        want_addr = base.ADDRESSES[p["address"]]
        checks.append(check(f"{stage}.address", stage, "binding", bool(l and l["address_id"] == want_addr), stp,
                            want_addr, l and l["address_id"]))
        key = next((k for k, a in base.ADDRESSES.items() if l and a == l["address_id"]), "home")
        checks.append(check(f"{stage}.delivery", stage, "selection",
                            bool(l and vars_[got]["eta"][key] <= world["deadline"]), stp, want_pid, got_pid,
                            roles.get("late")))
        if cls == "coupled":
            m = [x for x in lines if x["recipient_member_id"] == base.REL_ID["mother"]]
            tot = (m[0]["price"] if len(m) == 1 else 0) + (l["price"] if l else 0)
            checks.append(check(f"{stage}.pair_budget", stage, "coupled", bool(l and len(m) == 1 and tot <= world["pair_budget"]),
                                stp, world["pair_budget"], tot))
    if "gift" in stages:
        for rel in plan["items"]:
            want = rel in plan["gift"]
            mine = [l for l in lines if l["recipient_member_id"] == base.REL_ID[rel]]
            has = bool(mine and mine[0]["gift_wrap_for"] == base.REL_ID[rel])
            g_step = step_of(steps, "set_gift_wrap", lambda a, r=rel: a.get("recipient_member_id") == base.REL_ID[r])
            checks.append(check(f"gift.{rel}", "gift", "binding", has == want, g_step, want, has))
    if "exchange" in stages:
        ex = world["exchange"]
        exs = st.get("exchanges", [])
        e = next((x for x in exs if x["order_id"] == ex["order_id"] and x["order_line_id"] == ex["order_line_id"]), None)
        e_step = step_of(steps, "request_exchange")
        checks.append(check("exchange.line", "exchange", "selection", e is not None and len(exs) == 1, e_step,
                            f"{ex['order_id']}/{ex['order_line_id']}", e and f"{e['order_id']}/{e['order_line_id']}"))
        checks.append(check("exchange.size", "exchange", "attribute", bool(e and e["size"] == ex["new_size"]), e_step,
                            ex["new_size"], e and e["size"]))
        checks.append(check("exchange.colour", "exchange", "attribute", bool(e and e["colour"] == ex["colour"]), e_step,
                            plan["exchange"], e and e["new_variant_id"]))
    if "coupon" in stages:
        best = coupon_best(world, lines)
        checks.append(check("coupon.best", "coupon", "global", st.get("coupon") == best and best is not None,
                            step_of(steps, "apply_coupon"), best, st.get("coupon")))
    final = step_of(steps, "checkout")
    checks.append(check("cart.no_extra_lines", "checkout", "global", len(lines) == len(plan["items"]), final,
                        len(plan["items"]), len(lines)))
    other = CARDS["4471" if world["card"] == "4417" else "4417"]
    checks.append(check("checkout.payment", "checkout", "anchor", bool(order and order["payment_id"] == plan["payment"]),
                        final, plan["payment"], order and order["payment_id"], other, anchor=True))
    checks.append(check("checkout.slot", "checkout", "anchor", bool(order and order["slot_id"] == plan["slot"]), final,
                        plan["slot"], order and order["slot_id"], anchor=True))
    return summarize(traj, instance, checks, completed=order is not None)


FAULTS = ("neighbour_variant", "swap_address", "anchor_card", "anchor_slot")


def faulty_plan(world, stages, mode):
    plan = solve(world, stages)
    if mode == "neighbour_variant":
        vid = plan["items"]["self"]
        plan["items"]["self"] = next(o for o in world["variants"] if is_neighbour(vid, o))
        return plan, {"item_self.size"}
    if mode == "swap_address":
        rel = "self"
        plan["addresses"][rel] = base.ADDRESSES["nani" if world["prefs"][rel]["address"] == "home" else "home"]
        return plan, {"item_self.address"}
    if mode == "anchor_card":
        plan["payment"] = CARDS["4471" if world["card"] == "4417" else "4417"]
        return plan, {"checkout.payment"}
    if mode == "anchor_slot":
        plan["slot"] = next(s for k, s in SLOTS.items() if k != world["slot"])
        return plan, {"checkout.slot"}
    raise ValueError(mode)
