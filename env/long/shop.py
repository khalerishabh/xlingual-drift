"""
Shop domain: festive shopping for four family members plus an exchange
(docs/LONG_SPEC.md). About 36 tool calls. Built to provoke the two drift
kinds the study names:

  entity drift    four people with different sizes, colours, addresses and
                  gift wrap; product and variant ids that differ from the
                  answer by one swapped digit pair sit in the same listings
  semantic drift  add_to_cart and request_exchange take the user's size and
                  colour as confirm_size / confirm_colour next to an opaque
                  variant id, so "label right, value wrong" is observable

A mid-episode stock-out (at the first cart review) forces the agent to
re-apply one person's constraints about 25 steps after they were stated.
"""

import random

from env.long.base import I, LongTools, S, fn, is_neighbour, neighbour_id

MEMBERS = [
    {"member_id": "M-01", "name": "Arjun Sharma", "relation": "self", "gender": "men"},
    {"member_id": "M-02", "name": "Ramesh Sharma", "relation": "father", "gender": "men"},
    {"member_id": "M-03", "name": "Sunita Sharma", "relation": "mother", "gender": "women"},
    {"member_id": "M-04", "name": "Kavya Sharma", "relation": "sister", "gender": "women"},
]
REL_ID = {m["relation"]: m["member_id"] for m in MEMBERS}
ADDRESSES = {"home": "ADR-11", "nani": "ADR-12"}
APPAREL = ["S", "M", "L", "XL", "XXL"]
SHOES = ["UK 6", "UK 7", "UK 8", "UK 9", "UK 10"]
COLOURS = ["blue", "black", "white", "red", "green", "maroon", "yellow", "grey"]
CATEGORIES = ["kurta", "shirt", "kurti", "sneakers", "jeans", "saree"]
BRANDS = ["Fabindia", "Manyavar", "Biba", "W", "Allen Solly", "Peter England", "Puma", "Bata", "Libas", "Raymond"]
PAYMENT_METHODS = [{"payment_id": "PM-CARD-1", "type": "credit_card"}, {"payment_id": "PM-UPI-1", "type": "upi"},
                   {"payment_id": "PM-COD", "type": "cash_on_delivery"}]
SESSION_DATE = "2026-11-01"


def sizes_for(category):
    return SHOES if category == "sneakers" else APPAREL


def _uid(rng, used, prefix, digits=5):
    while True:
        v = f"{prefix}{rng.randrange(10 ** (digits - 1), 10 ** digits)}"
        if v not in used and len(set(v[-digits:])) == digits:
            used.add(v)
            return v


def generate(seed: int) -> dict:
    rng = random.Random(seed)
    used = set()
    father_cat = rng.choice(["kurta", "shirt"])
    self_cat = rng.choice([c for c in ["kurta", "shirt", "sneakers"] if c != father_cat])
    mother_cat = rng.choice(["kurti", "sneakers"])
    sister_cat = "sneakers" if mother_cat == "kurti" else "kurti"
    cats = {"self": self_cat, "father": father_cat, "mother": mother_cat, "sister": sister_cat}
    colours = rng.sample(COLOURS, 4)
    apparel_sizes = iter(rng.sample(APPAREL[:4], 4))
    shoe_sizes = iter(rng.sample(SHOES, 4))
    deadline_day = rng.choice([6, 7, 8])
    deadline = f"2026-11-{deadline_day:02d}"
    nani_pair = rng.sample(["father", "mother", "sister"], 2)
    gift_pair = rng.sample(["father", "mother", "sister"], 2)
    order = rng.sample(["self", "father", "mother", "sister"], 4)
    perturbed = rng.choice(order)

    products, variants, listings, prefs = {}, {}, {}, {}
    for rel in ["self", "father", "mother", "sister"]:
        cat = cats[rel]
        gender = next(m["gender"] for m in MEMBERS if m["relation"] == rel)
        size = next(shoe_sizes) if cat == "sneakers" else next(apparel_sizes)
        colour = colours[["self", "father", "mother", "sister"].index(rel)]
        max_price = rng.choice([1500, 1800, 2000, 2200, 2500, 3000]) if cat != "sneakers" else rng.choice([2500, 3000, 3500])
        address = "nani" if rel in nani_pair else "home"
        prefs[rel] = {"category": cat, "gender": gender, "size": size, "colour": colour, "max_price": max_price,
                      "address": address}

        roles = ["top", "nocolour", "late", "gold", "alt", "neighbour", "filler1", "filler2"]
        base_rating = {"top": 4.8, "nocolour": 4.6, "late": 4.5, "gold": 4.4, "alt": 4.2, "neighbour": 4.1,
                       "filler1": 3.9, "filler2": 3.7}
        ids = {}
        ids["gold"] = _uid(rng, used, "P-")
        ids["neighbour"] = neighbour_id(ids["gold"], rng)
        used.add(ids["neighbour"])
        for r in roles:
            if r not in ids:
                ids[r] = _uid(rng, used, "P-")
        brands = rng.sample(BRANDS, len(roles))
        rows = []
        for i, r in enumerate(roles):
            price = max_price + rng.choice([300, 500, 800]) if r == "top" else max_price - rng.choice([100, 200, 300, 400, 600])
            if r == "filler2":
                price = max_price + rng.choice([200, 400])
            pid = ids[r]
            products[pid] = {"product_id": pid, "name": f"{brands[i]} {cat}", "brand": brands[i], "category": cat,
                             "gender": gender, "price": price,
                             "rating": round(base_rating[r] + rng.choice([0.0, 0.04, -0.04]), 2), "role": r, "rel": rel}
            sizes = sizes_for(cat)
            vcolours = [colour] + rng.sample([c for c in COLOURS if c != colour], 2)
            if r in ("filler1",):
                vcolours = rng.sample([c for c in COLOURS if c != colour], 3)
            for c in vcolours:
                for s in sizes:
                    vid = _uid(rng, used, "V-")
                    stock = rng.choice([3, 5, 8, 12])
                    if r == "nocolour" and c == colour and s == size:
                        stock = 0
                    if r == "neighbour" and c == colour and s == size:
                        stock = 0
                    eta = {"home": f"2026-11-{deadline_day - rng.choice([1, 2]):02d}",
                           "nani": f"2026-11-{deadline_day - rng.choice([0, 1]):02d}"}
                    if r == "late":
                        eta = {"home": f"2026-11-{deadline_day + 1:02d}", "nani": f"2026-11-{deadline_day + 2:02d}"}
                    variants[vid] = {"variant_id": vid, "product_id": pid, "size": s, "colour": c, "stock": stock, "eta": eta}
            rows.append(pid)
        gold_v = next(v for v in variants.values() if v["product_id"] == ids["gold"] and v["size"] == size and v["colour"] == colour)
        bait = next(v for v in variants.values() if v["product_id"] == ids["gold"] and v["colour"] == colour and v["size"] != size)
        new_bait_id = neighbour_id(gold_v["variant_id"], rng)
        while new_bait_id in variants or new_bait_id in used:
            new_bait_id = neighbour_id(gold_v["variant_id"], rng)
        del variants[bait["variant_id"]]
        bait["variant_id"] = new_bait_id
        variants[new_bait_id] = bait
        used.add(new_bait_id)
        others = [x for x in rows if x not in (ids["gold"], ids["neighbour"])]
        rng.shuffle(others)
        pair = [ids["gold"], ids["neighbour"]]
        rng.shuffle(pair)
        at = rng.randrange(1, len(others) + 1)
        listings[f"{cat}|{gender}"] = others[:at] + pair + others[at:]

    exch_cat = rng.choice([c for c in ["shirt", "kurta"] if c not in (cats["self"],)] + ["shirt"])
    ex_colour = rng.choice([c for c in COLOURS if c not in colours])
    old_size = rng.choice(APPAREL[:3])
    new_size = APPAREL[APPAREL.index(old_size) + 1]
    ex_pid = _uid(rng, used, "P-")
    products[ex_pid] = {"product_id": ex_pid, "name": f"{rng.choice(BRANDS)} {exch_cat}", "brand": "", "category": exch_cat,
                        "gender": "men", "price": 1499, "rating": 4.0, "role": "exchange", "rel": "self"}
    other_colour = rng.choice([c for c in COLOURS if c != ex_colour])
    for c in (ex_colour, other_colour):
        for s in APPAREL:
            vid = _uid(rng, used, "V-")
            variants[vid] = {"variant_id": vid, "product_id": ex_pid, "size": s, "colour": c, "stock": 6,
                             "eta": {"home": "2026-11-05", "nani": "2026-11-06"}}
    ex_new = next(v for v in variants.values() if v["product_id"] == ex_pid and v["size"] == new_size and v["colour"] == ex_colour)
    ex_old = next(v for v in variants.values() if v["product_id"] == ex_pid and v["size"] == old_size and v["colour"] == ex_colour)
    ex_bait = next(v for v in variants.values() if v["product_id"] == ex_pid and v["size"] == new_size and v["colour"] == other_colour)
    bait_id = neighbour_id(ex_new["variant_id"], rng)
    while bait_id in variants:
        bait_id = neighbour_id(ex_new["variant_id"], rng)
    del variants[ex_bait["variant_id"]]
    ex_bait["variant_id"] = bait_id
    variants[bait_id] = ex_bait
    distract_pid = _uid(rng, used, "P-")
    products[distract_pid] = {"product_id": distract_pid, "name": f"{rng.choice(BRANDS)} {exch_cat}", "brand": "",
                              "category": exch_cat, "gender": "men", "price": 1299, "rating": 3.8, "role": "old", "rel": "self"}
    dv = _uid(rng, used, "V-")
    variants[dv] = {"variant_id": dv, "product_id": distract_pid, "size": old_size, "colour": ex_colour, "stock": 2,
                    "eta": {"home": "2026-11-05", "nani": "2026-11-06"}}
    orders = [
        {"order_id": _uid(rng, used, "O-", 6), "date": "2026-10-24", "lines": [
            {"order_line_id": "OL-1", "product_id": ex_pid, "variant_id": ex_old["variant_id"], "category": exch_cat,
             "size": old_size, "colour": ex_colour, "for_member_id": "M-01"},
            {"order_line_id": "OL-2", "product_id": "P-00000", "variant_id": "V-00000", "category": "jeans", "size": "32",
             "colour": "blue", "for_member_id": "M-01"}]},
        {"order_id": _uid(rng, used, "O-", 6), "date": "2026-09-12", "lines": [
            {"order_line_id": "OL-1", "product_id": distract_pid, "variant_id": dv, "category": exch_cat,
             "size": old_size, "colour": ex_colour, "for_member_id": "M-01"}]},
    ]
    return finalise({"seed": seed, "session_date": SESSION_DATE, "deadline": deadline, "order": order, "perturbed": perturbed,
            "nani_pair": nani_pair, "gift_pair": gift_pair, "prefs": prefs, "products": products, "variants": variants,
            "listings": listings, "orders": orders,
            "exchange": {"order_id": orders[0]["order_id"], "order_line_id": "OL-1", "category": exch_cat,
                         "new_size": new_size, "colour": ex_colour, "product_id": ex_pid},
            "coupon_seed": rng.randrange(10 ** 6), "perturbed_variant": None})


def finalise(world: dict) -> dict:
    world["perturbed_variant"] = best_variant(world, world["perturbed"])["variant_id"]
    return world


def coupons_for(world: dict) -> list[dict]:
    rng = random.Random(world["coupon_seed"])
    return [
        {"code": "NEWUSER25", "percent": 25, "max_discount": None, "min_cart_value": 0, "excluded_categories": [],
         "first_order_only": True},
        {"code": "FEST20", "percent": 20, "max_discount": rng.choice([400, 500, 600, 700]), "min_cart_value": 3000,
         "excluded_categories": [], "first_order_only": False},
        {"code": "DIWALI" + str(rng.choice([500, 600, 750])), "flat": None, "percent": None, "max_discount": None,
         "min_cart_value": 4000, "excluded_categories": [], "first_order_only": False},
        {"code": "STYLE15", "percent": 15, "max_discount": None, "min_cart_value": 0,
         "excluded_categories": [rng.choice(["sneakers", "kurti", "kurta", "shirt"])], "first_order_only": False},
    ]


def coupon_discount(c: dict, lines: list[dict]) -> int | None:
    """Discount on a cart, or None if the coupon cannot apply."""
    total = sum(l["price"] for l in lines)
    if c["first_order_only"] or total < c["min_cart_value"]:
        return None
    if c["code"].startswith("DIWALI"):
        return int(c["code"][6:])
    base = sum(l["price"] for l in lines if l["category"] not in c["excluded_categories"])
    d = int(base * c["percent"] / 100)
    if c["max_discount"] is not None:
        d = min(d, c["max_discount"])
    return d if d > 0 else None


def best_variant(world: dict, rel: str, sold_out=frozenset()) -> dict | None:
    p = world["prefs"][rel]
    best = None
    for pid in world["listings"][f"{p['category']}|{p['gender']}"]:
        prod = world["products"][pid]
        if prod["price"] > p["max_price"]:
            continue
        v = next((v for v in world["variants"].values() if v["product_id"] == pid and v["size"] == p["size"]
                  and v["colour"] == p["colour"] and v["stock"] > 0 and v["variant_id"] not in sold_out), None)
        if v is None or v["eta"][p["address"]] > world["deadline"]:
            continue
        if best is None or prod["rating"] > world["products"][best["product_id"]]["rating"]:
            best = v
    return best


class ShopTools(LongTools):
    TERMINAL_TOOL = "checkout"
    DOMAIN = "shop"

    def __init__(self, instance, language="en", seam="S1"):
        super().__init__(instance, language, seam)
        w = self.world
        self.coupons = coupons_for(w)
        self._last_search = None
        self.cart = []
        self._line_no = 0
        self.exchanges = []
        self.coupon = None
        self.perturbation_fired = False
        self.perturbed_variant = None

    def tool_schemas(self):
        conf_size = {"type": "string", "description": "The size you selected, as the user asked for it (e.g. M, UK 8)."}
        conf_colour = {"type": "string", "description": "The colour you selected, as the user asked for it (e.g. blue)."}
        return [
            fn("get_family_profile", "Family members and saved delivery addresses on the account.", {}),
            fn("search_products", "Search products by category and gender.",
               {"category": {"type": "string", "enum": CATEGORIES}, "gender": {"type": "string", "enum": ["men", "women"]}}),
            fn("filter_products", "Filter the most recent search results.",
               {"max_price": {"type": "number", "description": "Maximum price in INR."},
                "min_rating": {"type": "number", "description": "Minimum rating."}}, []),
            fn("get_product_variants", "Sizes, colours and stock of a product.", {"product_id": S}),
            fn("check_delivery", "Estimated delivery date of a variant to a saved address.", {"variant_id": S, "address_id": S}),
            fn("add_to_cart", "Add a variant to the cart for one family member.",
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
            fn("get_payment_methods", "Saved payment methods.", {}),
            fn("checkout", "Place the order for everything in the cart.", {"payment_id": S}),
        ]

    def _variant(self, vid):
        v = self.world["variants"].get(vid)
        if v is None:
            self.fail("validation", "unknown", what="variant_id", value=vid)
        return v

    def _product_row(self, pid):
        p = self.world["products"][pid]
        return {k: p[k] for k in ("product_id", "name", "brand", "category", "price", "rating")}

    def get_family_profile(self):
        return {"members": [{"member_id": m["member_id"], "name": m["name"], "relation": self.label("relation", m["relation"])}
                            for m in MEMBERS],
                "addresses": [{"address_id": ADDRESSES[k], "label": self.label("address", k)} for k in ("home", "nani")]}

    def search_products(self, category, gender):
        rows = [self._product_row(pid) for pid in self.world["listings"].get(f"{category}|{gender}", [])]
        self._last_search = rows
        return {"products": rows}

    def filter_products(self, max_price=None, min_rating=None):
        if self._last_search is None:
            self.bad("call search_products before filter_products")
        rows = [r for r in self._last_search if (max_price is None or r["price"] <= max_price)
                and (min_rating is None or r["rating"] >= min_rating)]
        self._last_search = rows
        return {"products": rows}

    def get_product_variants(self, product_id):
        if product_id not in self.world["products"]:
            self.fail("validation", "unknown", what="product_id", value=product_id)
        vs = [{"variant_id": v["variant_id"], "size": v["size"], "colour": v["colour"],
               "stock": 0 if v["variant_id"] in self._sold_out else v["stock"]}
              for v in self.world["variants"].values() if v["product_id"] == product_id]
        return {"product_id": product_id, "variants": vs}

    def check_delivery(self, variant_id, address_id):
        v = self._variant(variant_id)
        key = next((k for k, a in ADDRESSES.items() if a == address_id), None)
        if key is None:
            self.fail("validation", "unknown", what="address_id", value=address_id)
        return {"variant_id": variant_id, "address_id": address_id, "estimated_delivery": v["eta"][key]}

    def add_to_cart(self, variant_id, quantity, recipient_member_id, address_id, confirm_size, confirm_colour):
        v = self._variant(variant_id)
        if recipient_member_id not in REL_ID.values():
            self.fail("validation", "unknown", what="recipient_member_id", value=recipient_member_id)
        if address_id not in ADDRESSES.values():
            self.fail("validation", "unknown", what="address_id", value=address_id)
        if v["stock"] <= 0 or variant_id in self._sold_out:
            self.fail("not_found", "oos", vid=variant_id)
        self._line_no += 1
        p = self.world["products"][v["product_id"]]
        line = {"line_id": f"CL-{self._line_no}", "variant_id": variant_id, "product_id": v["product_id"],
                "name": p["name"], "category": p["category"], "size": v["size"], "colour": v["colour"],
                "price": p["price"] * int(quantity), "quantity": int(quantity), "recipient_member_id": recipient_member_id,
                "address_id": address_id, "confirm_size": confirm_size, "confirm_colour": confirm_colour,
                "gift_wrap_for": None, "status": "ok"}
        self.cart.append(line)
        return {"line_id": line["line_id"], "product": p["name"], "price": line["price"], "message": self.text("added")}

    def remove_from_cart(self, line_id):
        line = self._line(line_id)
        self.cart.remove(line)
        return {"removed": line_id}

    def _line(self, line_id):
        line = next((l for l in self.cart if l["line_id"] == line_id), None)
        if line is None:
            self.fail("validation", "unknown", what="line_id", value=line_id)
        return line

    def _maybe_perturb(self):
        if self.perturbation_fired:
            return None
        if len(self.cart) < 4:
            return None
        target = REL_ID[self.world["perturbed"]]
        gold_vid = self.world["perturbed_variant"]
        line = next((l for l in self.cart if l["variant_id"] == gold_vid and l["status"] == "ok"), None) or \
            next((l for l in self.cart if l["recipient_member_id"] == target and l["status"] == "ok"), None)
        if line is None:
            return None
        self.perturbation_fired = True
        self.perturbed_variant = line["variant_id"]
        self._sold_out.add(line["variant_id"])
        line["status"] = "unavailable"
        return line

    def _cart_view(self):
        return [{k: l[k] for k in ("line_id", "product_id", "variant_id", "name", "size", "colour", "price",
                                   "recipient_member_id", "address_id", "gift_wrap_for", "status")} for l in self.cart]

    def view_cart(self):
        hit = self._maybe_perturb()
        out = {"lines": self._cart_view(), "subtotal": sum(l["price"] for l in self.cart if l["status"] == "ok"),
               "coupon": self.coupon}
        if hit:
            out["notice"] = self.text("oos_notice", line_id=hit["line_id"])
        return out

    def set_gift_wrap(self, line_id, recipient_member_id):
        line = self._line(line_id)
        if recipient_member_id not in REL_ID.values():
            self.fail("validation", "unknown", what="recipient_member_id", value=recipient_member_id)
        line["gift_wrap_for"] = recipient_member_id
        return {"line_id": line_id, "gift_wrap_for": recipient_member_id}

    def list_orders(self):
        return {"orders": [{"order_id": o["order_id"], "date": o["date"], "items": len(o["lines"])} for o in self.world["orders"]]}

    def get_order(self, order_id):
        o = next((o for o in self.world["orders"] if o["order_id"] == order_id), None)
        if o is None:
            self.fail("validation", "unknown", what="order_id", value=order_id)
        return {"order_id": order_id, "date": o["date"], "lines": [dict(l) for l in o["lines"]]}

    def request_exchange(self, order_line_id, order_id, new_variant_id, confirm_size):
        o = next((o for o in self.world["orders"] if o["order_id"] == order_id), None)
        if o is None:
            self.fail("validation", "unknown", what="order_id", value=order_id)
        line = next((l for l in o["lines"] if l["order_line_id"] == order_line_id), None)
        if line is None:
            self.fail("validation", "unknown", what="order_line_id", value=order_line_id)
        v = self._variant(new_variant_id)
        if v["product_id"] != line["product_id"]:
            self.bad(f"variant {new_variant_id} is not a variant of {line['product_id']}")
        ex = {"exchange_id": f"EX-{len(self.exchanges) + 1}", "order_id": order_id, "order_line_id": order_line_id,
              "new_variant_id": new_variant_id, "size": v["size"], "colour": v["colour"], "confirm_size": confirm_size}
        self.exchanges.append(ex)
        return {"exchange_id": ex["exchange_id"], "message": self.text("exchange_ok")}

    def list_coupons(self):
        return {"coupons": [{k: v for k, v in c.items() if v is not None or k in ("max_discount",)} for c in self.coupons]}

    def apply_coupon(self, code):
        c = next((c for c in self.coupons if c["code"] == code), None)
        if c is None:
            self.fail("validation", "unknown", what="coupon", value=code)
        d = coupon_discount(c, [l for l in self.cart if l["status"] == "ok"])
        if d is None:
            self.fail("validation", "coupon", code=code)
        self.coupon = code
        return {"code": code, "discount": d}

    def get_payment_methods(self):
        return {"payment_methods": [dict(p) for p in PAYMENT_METHODS]}

    def snapshot(self) -> dict:
        """State at the end of an episode, for scoring when the agent stopped
        before checkout (e.g. to ask the user to confirm payment)."""
        lines = [dict(l) for l in self.cart if l["status"] == "ok"]
        c = next((c for c in self.coupons if c["code"] == self.coupon), None)
        return {"status": "not_placed", "lines": lines, "exchanges": [dict(e) for e in self.exchanges],
                "coupon": self.coupon, "discount": (coupon_discount(c, lines) or 0) if c else 0, "payment_id": None}

    def checkout(self, payment_id):
        if payment_id not in {p["payment_id"] for p in PAYMENT_METHODS}:
            self.fail("validation", "unknown", what="payment_id", value=payment_id)
        self._maybe_perturb()
        bad = next((l for l in self.cart if l["status"] != "ok"), None)
        if bad:
            self.fail("validation", "unavailable_line", line=bad["line_id"])
        lines = [dict(l) for l in self.cart]
        c = next((c for c in self.coupons if c["code"] == self.coupon), None)
        disc = coupon_discount(c, lines) if c else None
        return {"status": "placed", "order_id": "O-NEW-1", "lines": lines, "exchanges": [dict(e) for e in self.exchanges],
                "coupon": self.coupon, "discount": disc or 0, "payment_id": payment_id,
                "total": sum(l["price"] for l in lines) - (disc or 0)}


def answer(world: dict) -> dict:
    gold = {rel: best_variant(world, rel)["variant_id"] for rel in world["prefs"]}
    p = world["perturbed"]
    replacement = best_variant(world, p, {gold[p]})["variant_id"]
    final = dict(gold, **{p: replacement})
    lines = [{"price": world["products"][world["variants"][final[r]]["product_id"]]["price"],
              "category": world["prefs"][r]["category"]} for r in final]
    best_c, best_d = None, -1
    for c in coupons_for(world):
        d = coupon_discount(c, lines)
        if d is not None and d > best_d:
            best_c, best_d = c["code"], d
    ex = world["exchange"]
    new_v = next(v["variant_id"] for v in world["variants"].values() if v["product_id"] == ex["product_id"]
                 and v["size"] == ex["new_size"] and v["colour"] == ex["colour"])
    return {"initial": gold, "final": final, "coupon": best_c, "exchange_variant": new_v}


def plan_from_answer(world: dict) -> dict:
    a = answer(world)
    return {"variants": dict(a["initial"]), "replacement": a["final"][world["perturbed"]],
            "recipients": {r: REL_ID[r] for r in world["prefs"]},
            "addresses": {r: ADDRESSES[world["prefs"][r]["address"]] for r in world["prefs"]},
            "labels": {r: (world["prefs"][r]["size"], world["prefs"][r]["colour"]) for r in world["prefs"]},
            "gift": list(world["gift_pair"]), "coupon": a["coupon"], "exchange_variant": a["exchange_variant"],
            "exchange_label": world["exchange"]["new_size"], "payment": "PM-UPI-1"}


def chain(world: dict, plan: dict) -> list[dict]:
    steps = []

    def add(tool, **args):
        steps.append({"tool": tool, "args": args})

    v = world["variants"]
    add("get_family_profile")
    line_of = {}
    for i, rel in enumerate(world["order"], 1):
        p = world["prefs"][rel]
        vid = plan["variants"][rel]
        add("search_products", category=p["category"], gender=p["gender"])
        add("filter_products", max_price=p["max_price"])
        add("get_product_variants", product_id=v[vid]["product_id"])
        add("check_delivery", variant_id=vid, address_id=plan["addresses"][rel])
        size, colour = plan["labels"][rel]
        add("add_to_cart", variant_id=vid, quantity=1, recipient_member_id=plan["recipients"][rel],
            address_id=plan["addresses"][rel], confirm_size=size, confirm_colour=colour)
        line_of[rel] = f"CL-{i}"
    ex = world["exchange"]
    add("list_orders")
    add("get_order", order_id=ex["order_id"])
    add("get_product_variants", product_id=ex["product_id"])
    add("request_exchange", order_line_id=ex["order_line_id"], order_id=ex["order_id"],
        new_variant_id=plan["exchange_variant"], confirm_size=plan["exchange_label"])
    add("view_cart")
    p = world["perturbed"]
    rep = plan["replacement"]
    add("remove_from_cart", line_id=line_of[p])
    add("get_product_variants", product_id=v[rep]["product_id"])
    add("check_delivery", variant_id=rep, address_id=plan["addresses"][p])
    size, colour = plan["labels"][p]
    add("add_to_cart", variant_id=rep, quantity=1, recipient_member_id=plan["recipients"][p],
        address_id=plan["addresses"][p], confirm_size=size, confirm_colour=colour)
    line_of[p] = "CL-5"
    for rel in plan["gift"]:
        add("set_gift_wrap", line_id=line_of[rel], recipient_member_id=REL_ID[rel])
    add("list_coupons")
    add("apply_coupon", code=plan["coupon"])
    add("get_payment_methods")
    add("checkout", payment_id=plan["payment"])
    return steps


def render_request(world: dict, lex: dict, lang: str) -> str:
    r = lex["request"][lang]
    rel, cat, col = lex["rel"][lang], lex["category"][lang], lex["colour"][lang]
    lines = [r["intro"]]
    for who in world["order"]:
        p = world["prefs"][who]
        lines.append(r["line"].format(rel=rel[who], category=cat[p["category"]], size=p["size"], colour=col[p["colour"]],
                                      price=f"{p['max_price']:,}"))
    pair = lambda xs: r["pair"].format(a=rel[xs[0]], b=rel[xs[1]])
    day = int(world["deadline"][-2:])
    lines.append(r["rules"].format(nani_pair=pair(world["nani_pair"]), gift_pair=pair(world["gift_pair"]),
                                   date=r["date"].format(d=day), exch_category=cat[world["exchange"]["category"]],
                                   exch_size=world["exchange"]["new_size"]))
    return "\n".join(lines)


def check_rules(world: dict) -> None:
    a = answer(world)
    for rel, vid in a["initial"].items():
        p = world["prefs"][rel]
        listing = world["listings"][f"{p['category']}|{p['gender']}"]
        pid = world["variants"][vid]["product_id"]
        assert world["products"][pid]["role"] == "gold", (world["seed"], rel, world["products"][pid]["role"])
        assert listing[0] != pid, (world["seed"], rel, "answer listed first")
        nb = next(x for x in listing if world["products"][x]["role"] == "neighbour")
        assert is_neighbour(pid, nb), (world["seed"], rel)
        assert any(is_neighbour(vid, o) for o in world["variants"]), (world["seed"], rel, "no neighbour variant")
    rep = world["variants"][a["final"][world["perturbed"]]]
    assert world["products"][rep["product_id"]]["role"] == "alt", world["seed"]
    lines = [{"price": world["products"][world["variants"][a["final"][r]]["product_id"]]["price"],
              "category": world["prefs"][r]["category"]} for r in a["final"]]
    ds = sorted((coupon_discount(c, lines) or -1, c["code"]) for c in coupons_for(world))
    assert ds[-1][0] > 0 and ds[-1][0] - ds[-2][0] >= 25, (world["seed"], "coupon best not unique", ds)
    assert ds[-1][1] != "NEWUSER25", world["seed"]
    sizes = [world["prefs"][r]["size"] for r in world["prefs"]]
    colours = [world["prefs"][r]["colour"] for r in world["prefs"]]
    assert len(set(colours)) == 4 and len(set(sizes)) == 4, world["seed"]


# --- verification -----------------------------------------------------------

CLASSES = ("selection", "attribute", "binding", "global")
COMPLETION_CHECKS = ("payment.upi", "batch.confirmed")


def verify(traj, instance: dict, sold_out: set, final_state: dict | None = None) -> dict:
    world = instance["world"]
    steps = traj.steps
    term = traj.terminal_state or final_state or {}
    checks, cls, commit, drift, reground, prior = {}, {}, {}, {}, {}, {}

    def put(name, klass, ok, step, kind=None, rg=False, evidence=None):
        checks[name], cls[name], commit[name] = bool(ok), klass, step
        if not ok:
            drift[name] = kind or "other"
            prior[name] = bool(evidence)
        reground[name] = rg

    def acted_before(step, ids):
        ids = {i for i in ids if i}
        return any(set(map(str, s["args"].values())) & ids for s in steps[:max(0, (step or 1) - 1)]
                   if s["tool"] in ("get_product_variants", "check_delivery") and "result" in s)

    add_step = {}
    for i, s in enumerate(steps, 1):
        if s["tool"] == "add_to_cart" and "result" in s:
            add_step[s["result"]["line_id"]] = i
    lines = term.get("lines", [])
    placed = term.get("status") == "placed"
    v_all, prods = world["variants"], world["products"]
    pert = world["perturbed"]
    for rel, p in world["prefs"].items():
        mid = REL_ID[rel]
        mine = [l for l in lines if l["recipient_member_id"] == mid]
        rg = rel == pert
        if len(mine) != 1:
            put(f"item.{rel}.present", "selection", False, None, "other", rg)
            continue
        l = mine[0]
        step = add_step.get(l["line_id"])
        expected = best_variant(world, rel, sold_out)
        exp_vid = expected["variant_id"] if expected else None
        exp_pid = expected["product_id"] if expected else None
        others = {r: q for r, q in world["prefs"].items() if r != rel}

        def kind_for(attr, value, label=None, requested=None):
            if exp_vid and (is_neighbour(l["variant_id"], exp_vid) or is_neighbour(l["product_id"], exp_pid)):
                return "neighbour_id"
            if label is not None and label == requested and value != requested:
                return "semantic"
            if any(q[attr] == value for q in others.values()):
                return "entity_swap"
            return "other"

        ev = acted_before(step, (exp_vid, exp_pid))
        put(f"item.{rel}.category", "selection", l["category"] == p["category"], step,
            kind_for("category", l["category"]), rg, ev)
        put(f"item.{rel}.price", "selection", prods[l["product_id"]]["price"] <= p["max_price"], step,
            kind_for("max_price", None), rg, ev)
        put(f"item.{rel}.best", "selection", l["product_id"] == exp_pid, step, kind_for("category", None), rg, ev)
        put(f"item.{rel}.size", "attribute", l["size"] == p["size"], step,
            kind_for("size", l["size"], l["confirm_size"], p["size"]), rg, ev)
        put(f"item.{rel}.colour", "attribute", l["colour"] == p["colour"], step,
            kind_for("colour", l["colour"], l["confirm_colour"], p["colour"]), rg, ev)
        addr_key = next(k for k, a in ADDRESSES.items() if a == l["address_id"]) if l["address_id"] in ADDRESSES.values() else None
        put(f"item.{rel}.address", "binding", addr_key == p["address"], step,
            "entity_swap" if addr_key and any(q["address"] == addr_key for q in others.values()) else "other", rg)
        eta = v_all[l["variant_id"]]["eta"].get(addr_key or "home", "9999")
        put(f"item.{rel}.delivery", "selection", eta <= world["deadline"], step, "other", rg)
        g_step = next((i for i, s in enumerate(steps, 1) if s["tool"] == "set_gift_wrap" and "result" in s
                       and s["args"].get("line_id") == l["line_id"]), None)
        want_gift = rel in world["gift_pair"]
        has_gift = l.get("gift_wrap_for") == mid
        put(f"gift.{rel}", "binding", has_gift == want_gift, g_step or traj_len(steps),
            "entity_swap" if (not want_gift and has_gift) or (want_gift and any(
                o.get("gift_wrap_for") == mid and o["line_id"] != l["line_id"] for o in lines)) else "other", rg)
    extra = [l for l in lines if l["recipient_member_id"] not in REL_ID.values()]
    put("cart.no_extra_lines", "global", len(lines) == 4 and not extra, traj_len(steps))

    ex = world["exchange"]
    exs = term.get("exchanges", [])
    ex_step = next((i for i, s in enumerate(steps, 1) if s["tool"] == "request_exchange" and "result" in s), None)
    good = [e for e in exs if e["order_id"] == ex["order_id"] and e["order_line_id"] == ex["order_line_id"]]
    put("exchange.line", "global", len(good) == 1 and len(exs) == 1, ex_step)
    e = good[0] if good else (exs[0] if exs else None)
    put("exchange.size", "attribute", bool(e) and e["size"] == ex["new_size"], ex_step,
        "semantic" if e and e["confirm_size"] == ex["new_size"] and e["size"] != ex["new_size"] else "other")
    exp_ex = answer(world)["exchange_variant"]
    put("exchange.colour", "attribute", bool(e) and e["colour"] == ex["colour"], ex_step,
        "neighbour_id" if e and is_neighbour(e["new_variant_id"], exp_ex) else "other")

    final_lines = [{"price": prods[l["product_id"]]["price"], "category": l["category"]} for l in lines]
    best_c, best_d = None, -1
    for c in coupons_for(world):
        d = coupon_discount(c, final_lines)
        if d is not None and d > best_d:
            best_c, best_d = c["code"], d
    c_step = max((i for i, s in enumerate(steps, 1) if s["tool"] == "apply_coupon" and "result" in s), default=None)
    put("coupon.best", "global", term.get("coupon") == best_c, c_step)
    put("payment.upi", "global", term.get("payment_id") == "PM-UPI-1", traj_len(steps))
    return summarize(traj, instance, checks, cls, commit, drift, reground, placed, prior)


def traj_len(steps):
    return len(steps)


def summarize(traj, instance, checks, cls, commit, drift, reground, placed, prior=None) -> dict:
    """`success` (pre-registered) needs the final irreversible step (checkout,
    batch confirmation). `success_state` scores the state the agent built,
    so an agent that stops to hand the OTP or payment confirmation to the
    user is not failed for it; `completed` records which one happened."""
    by = {}
    for k, v in checks.items():
        by.setdefault(cls[k], []).append(v)
    ok = placed and all(checks.values())
    state_ok = all(v for k, v in checks.items() if k not in COMPLETION_CHECKS)
    return {
        "success": ok,
        "success_state": state_ok,
        "completed": placed,
        "booked": placed,
        "booked_flight": "placed" if placed else None,
        "constraint_ok": checks, "constraint_class": cls, "constraint_commit_step": commit,
        "drift_type": drift, "regrounding": reground, "prior_correct_action": prior or {},
        "validation_errors": sum(1 for s in traj.steps if s.get("error", {}).get("error_type") == "validation"),
        **{f"all_{k}_ok": (all(v) if v else None) for k, v in by.items()},
        "drift_counts": {t: sum(1 for x in drift.values() if x == t) for t in ("entity_swap", "neighbour_id", "semantic", "other")},
        "first_error_step": traj.first_error_step,
        "num_steps_taken": len(traj.steps),
        "extra_steps": len(traj.steps) - len(instance["gold_steps"]),
        "injected": traj.injected_error is not None,
        "injected_at_step": traj.injected_at_step,
        "recovered": ok if traj.injected_error is not None else None,
    }


# --- scripted faults for testing the harness -------------------------------

FAULTS = ("swap_recipients", "neighbour_variant", "semantic_label", "reground_wrong_colour")


def faulty_plan(world: dict, mode: str) -> tuple[dict, set]:
    plan = plan_from_answer(world)
    order = world["order"]
    if mode == "swap_recipients":
        a, b = [r for r in order if r != world["perturbed"]][:2]
        plan["recipients"][a], plan["recipients"][b] = REL_ID[b], REL_ID[a]
        return plan, None
    if mode == "neighbour_variant":
        rel = next(r for r in order if r != world["perturbed"])
        vid = plan["variants"][rel]
        plan["variants"][rel] = next(o for o in world["variants"] if is_neighbour(vid, o))
        return plan, {f"item.{rel}.size"}
    if mode == "semantic_label":
        rel = next(r for r in order if r != world["perturbed"])
        vid = plan["variants"][rel]
        v = world["variants"][vid]
        plan["variants"][rel] = next(o["variant_id"] for o in world["variants"].values()
                                     if o["product_id"] == v["product_id"] and o["colour"] == v["colour"]
                                     and o["size"] != v["size"] and not is_neighbour(vid, o["variant_id"]) and o["stock"] > 0)
        return plan, {f"item.{rel}.size"}
    if mode == "reground_wrong_colour":
        rel = world["perturbed"]
        rep = world["variants"][plan["replacement"]]
        plan["replacement"] = next(o["variant_id"] for o in world["variants"].values()
                                   if o["product_id"] == rep["product_id"] and o["size"] == rep["size"]
                                   and o["colour"] != rep["colour"] and o["stock"] > 0)
        return plan, {f"item.{rel}.colour"}
    raise ValueError(mode)
