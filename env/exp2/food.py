"""
Food Order domain (Experiment 2). Dinner for the family from one restaurant
on a delivery app.

Stages (long format order):
  restaurant  highest-rated pure-veg restaurant of a cuisine that delivers to
              the chosen address within a time limit
  dish_self, dish_papa, dish_mummy, dish_didi
              one dish each: a dish type, a price cap, highest-rated, and one
              customisation (spice level, or Jain)
  sides       a bread item in a stated quantity
  dessert     coupled: the highest-rated dessert that keeps the whole cart
              within a total budget
  offer       the offer with the biggest discount for the final cart
  slot        scheduled delivery slot (an id copied from the slot listing)
  checkout    anchors: delivery address and payment card, committed only in
              place_order

Traps: a top-rated restaurant that is not pure-veg and another that is too
slow; per dish a higher-rated one over budget and (for Jain) a higher-rated
one that cannot be made Jain; restaurant and dish ids one digit-pair apart
next to the answer; home and office addresses with near-identical ids; two
cards of the same bank whose last four digits differ by one swap.
"""

import random

from env.exp2.core import (B, I, S, Exp2Tools, arr, assert_never_first, check, enum, fn, step_of, summarize,
                           term)
from env.long.base import is_neighbour, neighbour_id

DOMAIN = "food"
SESSION_DATE = "2026-11-03"
PEOPLE = ("self", "papa", "mummy", "didi")
SPICE = ("mild", "medium", "spicy")

CUISINES = {
    "north_indian": {"types": ["paneer", "dal", "biryani", "kofta"], "bread": "butter_roti",
                     "breads": ["butter_roti", "tandoori_roti", "garlic_naan"],
                     "desserts": ["gulab_jamun", "rasmalai", "kulfi", "phirni"],
                     "names": ["Punjab Grill House", "Shree Annapurna", "Rajdhani Rasoi", "Haldiram Express",
                               "Bikaner Bhoj", "Delhi Darbar Veg", "Amritsari Haveli", "Sukh Sagar"]},
    "south_indian": {"types": ["dosa", "idli", "uttapam", "meals"], "bread": "parotta",
                     "breads": ["parotta", "appam", "poori"],
                     "desserts": ["payasam", "kesari", "mysore_pak", "rava_laddu"],
                     "names": ["Udupi Krishna Bhavan", "Saravana Bhavan", "Madras Cafe", "Ramanayaka Udupi",
                               "Mysore Mylari", "Annapoorna Tiffins", "Sri Sagar", "Ananda Bhavan"]},
    "indo_chinese": {"types": ["noodles", "fried_rice", "manchurian", "soup"], "bread": "spring_roll",
                     "breads": ["spring_roll", "momos", "wontons"],
                     "desserts": ["date_pancake", "honey_noodles", "fried_ice_cream", "mango_pudding"],
                     "names": ["Wok Express Veg", "Chinese Wok House", "Mainland Bowl", "Golden Dragon Veg",
                               "Hakka Street", "Bamboo Garden", "Szechuan Spice", "Red Lantern"]},
    "italian": {"types": ["pizza", "pasta", "risotto", "lasagne"], "bread": "garlic_bread",
                "breads": ["garlic_bread", "focaccia", "bruschetta"],
                "desserts": ["tiramisu", "brownie", "panna_cotta", "cheesecake"],
                "names": ["Little Italy", "Pizza Bella", "Trattoria Roma", "Olive Garden Veg",
                          "Pasta Street", "La Pinoz Kitchen", "Napoli Oven", "Casa Verde"]},
    "gujarati": {"types": ["thali", "khichdi", "dhokla", "undhiyu"], "bread": "phulka",
                 "breads": ["phulka", "thepla", "puri"],
                 "desserts": ["shrikhand", "mohanthal", "basundi", "jalebi"],
                 "names": ["Swati Snacks", "Rajwadu Thali", "Gopi Dining Hall", "Agashiye Kitchen",
                           "Shree Thaker Bhojanalay", "Soam", "Kathiyawadi Rasoi", "Panchvati Gaurav"]},
}

SCENARIOS = [
    {"id": 1, "seed": 101, "cuisine": "north_indian", "address": "home", "card": "4417", "slot": "21:00"},
    {"id": 2, "seed": 202, "cuisine": "south_indian", "address": "office", "card": "4471", "slot": "20:30"},
    {"id": 3, "seed": 303, "cuisine": "indo_chinese", "address": "home", "card": "4471", "slot": "21:30"},
    {"id": 4, "seed": 404, "cuisine": "italian", "address": "office", "card": "4417", "slot": "20:00"},
    {"id": 5, "seed": 505, "cuisine": "gujarati", "address": "home", "card": "4417", "slot": "20:30"},
]

FORMATS = {
    "short": ["restaurant", "dish_self", "checkout"],
    "medium": ["restaurant", "dish_self", "dish_papa", "dish_mummy", "offer", "checkout"],
    "long": ["restaurant", "dish_self", "dish_papa", "dish_mummy", "dish_didi", "sides", "dessert", "offer", "slot",
             "checkout"],
}
ANCHOR_STAGE = "checkout"
CUSTOM = {"self": ("spice", "spicy"), "papa": ("spice", "mild"), "mummy": ("jain", True), "didi": ("spice", "medium")}
ADDRESSES = {"home": ("ADR-31", "Home - Andheri West"), "office": ("ADR-13", "Office - Andheri East"),
             "nani": ("ADR-42", "Nani - Thane")}
CARDS = {"4417": "PM-CC-4417", "4471": "PM-CC-4471"}
SLOT_TIMES = ("19:30", "20:00", "20:30", "21:00", "21:30", "22:00")


def _uid(rng, used, prefix, digits=4):
    while True:
        v = prefix + "".join(rng.choice("123456789") for _ in range(digits))
        if v not in used and len(set(v[len(prefix):])) == digits:
            used.add(v)
            return v


def generate(scenario: dict) -> dict:
    rng = random.Random(scenario["seed"])
    used = set()
    cz = CUISINES[scenario["cuisine"]]
    addr_key = scenario["address"]
    eta_limit = rng.choice([35, 40, 45])
    names = list(cz["names"])
    rng.shuffle(names)

    roles = ["top_nonveg", "slow", "gold", "lookalike", "alt", "filler1", "filler2", "filler3"]
    base = {"top_nonveg": 4.8, "slow": 4.7, "gold": 4.5, "lookalike": 4.2, "alt": 4.3, "filler1": 4.0,
            "filler2": 3.9, "filler3": 3.7}
    ids = {"gold": _uid(rng, used, "R-")}
    ids["lookalike"] = neighbour_id(ids["gold"], rng)
    used.add(ids["lookalike"])
    restaurants = {}
    for i, role in enumerate(roles):
        rid = ids.get(role) or _uid(rng, used, "R-")
        eta = {a: rng.choice(range(20, eta_limit - 2)) for a in ADDRESSES}
        if role == "slow":
            eta[addr_key] = eta_limit + rng.choice([10, 15, 20])
        pure_veg = role != "top_nonveg" and role != "filler3"
        restaurants[rid] = {"restaurant_id": rid, "name": names[i], "cuisine": scenario["cuisine"],
                            "pure_veg": pure_veg, "rating": round(base[role] + rng.choice([0.0, 0.04, -0.04]), 2),
                            "eta_min": eta, "role": role}
    order = list(restaurants)
    rng.shuffle(order)
    while order[0] == ids["gold"] or order.index(ids["lookalike"]) != order.index(ids["gold"]) + 1:
        rng.shuffle(order)
        gi = order.index(ids["gold"])
        if gi < len(order) - 1:
            order.remove(ids["lookalike"])
            order.insert(gi + 1, ids["lookalike"])

    types = cz["types"][scenario["id"] % 4:] + cz["types"][:scenario["id"] % 4]
    person_type = dict(zip(PEOPLE, types))
    budgets = {p: rng.choice([250, 300, 350, 400]) for p in PEOPLE}
    menus = {}
    for rid in restaurants:
        menus[rid] = _menu(rng, used, cz, person_type, budgets, rid == ids["gold"])

    gold_menu = menus[ids["gold"]]
    world = {"seed": scenario["seed"], "scenario": scenario["id"], "session_date": SESSION_DATE,
             "cuisine": scenario["cuisine"], "address_key": addr_key, "card": scenario["card"],
             "eta_limit": eta_limit, "restaurants": restaurants, "listing": order, "menus": menus,
             "person_type": person_type, "budgets": budgets, "bread": cz["bread"],
             "bread_qty": rng.choice([4, 6, 8]), "slot_time": scenario["slot"],
             "slots": [{"slot_id": f"SL-{t.replace(':', '')}", "start_time": t} for t in SLOT_TIMES],
             "offers": _offers(rng)}
    world["slots"] = world["slots"][3:] + world["slots"][:3]
    world["total_budget"] = _coupled_budget(world)
    return world


def _menu(rng, used, cz, person_type, budgets, is_gold):
    dishes = []

    def add(name, course, dtype, price, rating, jain, role):
        did = _uid(rng, used, "D-")
        dishes.append({"dish_id": did, "name": name, "course": course, "type": dtype, "price": price,
                       "rating": rating, "jain_available": jain, "spice_levels": list(SPICE), "role": role})
        return did

    for p, dtype in person_type.items():
        cap = budgets[p]
        needs_jain = CUSTOM[p][0] == "jain"
        label = dtype.replace("_", " ").title()
        add(f"Royal {label}", "main", dtype, cap + rng.choice([40, 60, 90]), 4.8, True, f"{p}:over")
        if needs_jain:
            add(f"Chef's Special {label}", "main", dtype, cap - rng.choice([20, 40]), 4.7, False, f"{p}:nojain")
        gid = add(f"Classic {label}", "main", dtype, cap - rng.choice([30, 50, 70]), 4.5, True, f"{p}:gold")
        nid = neighbour_id(gid, rng)
        while nid in used:
            nid = neighbour_id(gid, rng)
        used.add(nid)
        dishes.append({"dish_id": nid, "name": f"House {label}", "course": "main", "type": dtype,
                       "price": cap - rng.choice([60, 80]), "rating": 4.1, "jain_available": True,
                       "spice_levels": list(SPICE), "role": f"{p}:lookalike"})
        add(f"Home-style {label}", "main", dtype, cap - rng.choice([90, 110]), 3.9, True, f"{p}:filler")
    for b in cz["breads"]:
        add(b.replace("_", " ").title(), "bread", b, rng.choice([30, 40, 50, 60]), round(rng.uniform(3.9, 4.6), 1),
            True, "bread:gold" if b == cz["bread"] else "bread:other")
    for j, d in enumerate(cz["desserts"]):
        add(d.replace("_", " ").title(), "dessert", d, [260, 180, 140, 120][j], [4.8, 4.6, 4.4, 4.0][j], True,
            f"dessert:{j}")
    while True:
        rng.shuffle(dishes)
        ok = True
        for p, dtype in person_type.items():
            same = [d for d in dishes if d["course"] == "main" and d["type"] == dtype]
            if same[0]["role"] == f"{p}:gold":
                ok = False
        if ok:
            return dishes


def _offers(rng):
    return [{"code": "FLAT120", "description": "Flat Rs 120 off on orders of Rs 1,200 or more", "kind": "flat",
             "value": 120, "min_order": 1200, "cap": 120},
            {"code": "VEG20", "description": "20% off up to Rs 150 on orders of Rs 600 or more", "kind": "pct",
             "value": 20, "min_order": 600, "cap": 150},
            {"code": "FEAST15", "description": "15% off up to Rs 300 on orders of Rs 1,500 or more", "kind": "pct",
             "value": 15, "min_order": 1500, "cap": 300},
            {"code": "NEWUSER50", "description": "50% off up to Rs 100, first order only", "kind": "pct",
             "value": 50, "min_order": 0, "cap": 100, "first_order_only": True}]


def offer_discount(offer, total):
    if offer.get("first_order_only") or total < offer["min_order"]:
        return None
    if offer["kind"] == "flat":
        return offer["value"]
    return min(offer["cap"], total * offer["value"] // 100)


def gold_restaurant(world):
    return next(r for r in world["restaurants"].values() if r["role"] == "gold")["restaurant_id"]


def best_dish(world, rid, person):
    p_type, cap = world["person_type"][person], world["budgets"][person]
    rows = [d for d in world["menus"][rid] if d["course"] == "main" and d["type"] == p_type and d["price"] <= cap]
    if CUSTOM[person][0] == "jain":
        rows = [d for d in rows if d["jain_available"]]
    return max(rows, key=lambda d: d["rating"])["dish_id"] if rows else None


def bread_dish(world, rid):
    return next(d["dish_id"] for d in world["menus"][rid] if d["course"] == "bread" and d["type"] == world["bread"])


def _dish(world, rid, did):
    return next(d for d in world["menus"][rid] if d["dish_id"] == did)


def _coupled_budget(world):
    """Total budget that rules out the top dessert but admits the second."""
    rid = gold_restaurant(world)
    base = sum(_dish(world, rid, best_dish(world, rid, p))["price"] for p in PEOPLE)
    base += _dish(world, rid, bread_dish(world, rid))["price"] * world["bread_qty"]
    desserts = sorted([d for d in world["menus"][rid] if d["course"] == "dessert"], key=lambda d: -d["rating"])
    lo, hi = base + desserts[1]["price"], base + desserts[0]["price"]
    return (lo + hi) // 2 // 10 * 10


def solve(world, stages):
    rid = gold_restaurant(world)
    plan = {"restaurant": rid, "lines": [], "offer": None, "slot": None,
            "address": ADDRESSES[world["address_key"]][0], "payment": CARDS[world["card"]]}
    total = 0
    for p in PEOPLE:
        if f"dish_{p}" in stages:
            did = best_dish(world, rid, p)
            kind, val = CUSTOM[p]
            plan["lines"].append({"dish_id": did, "quantity": 1,
                                  "spice_level": val if kind == "spice" else "medium", "jain": kind == "jain"})
            total += _dish(world, rid, did)["price"]
    if "sides" in stages:
        bid = bread_dish(world, rid)
        plan["lines"].append({"dish_id": bid, "quantity": world["bread_qty"], "spice_level": "medium", "jain": False})
        total += _dish(world, rid, bid)["price"] * world["bread_qty"]
    if "dessert" in stages:
        rows = [d for d in world["menus"][rid] if d["course"] == "dessert" and total + d["price"] <= world["total_budget"]]
        d = max(rows, key=lambda d: d["rating"])
        plan["lines"].append({"dish_id": d["dish_id"], "quantity": 1, "spice_level": "medium", "jain": False})
        total += d["price"]
    if "offer" in stages:
        best = max(((offer_discount(o, total), o["code"]) for o in world["offers"] if offer_discount(o, total)),
                   default=(None, None))
        plan["offer"] = best[1]
    if "slot" in stages:
        plan["slot"] = next(s["slot_id"] for s in world["slots"] if s["start_time"] == world["slot_time"])
    plan["total"] = total
    return plan


def chain(world, stages, plan):
    steps = []

    def add(tool, **args):
        steps.append({"tool": tool, "args": args})

    rid = plan["restaurant"]
    add("get_saved_addresses")
    add("search_restaurants", cuisine=world["cuisine"], address_id=plan["address"])
    add("get_menu", restaurant_id=rid)
    for ln in plan["lines"]:
        d = _dish(world, rid, ln["dish_id"])
        if d["course"] == "main":
            add("get_dish_details", restaurant_id=rid, dish_id=ln["dish_id"])
        add("add_item", restaurant_id=rid, dish_id=ln["dish_id"], quantity=ln["quantity"],
            spice_level=ln["spice_level"], jain=ln["jain"])
    if plan["offer"]:
        add("list_offers", restaurant_id=rid)
        add("apply_offer", code=plan["offer"])
    if plan["slot"]:
        add("get_delivery_slots", restaurant_id=rid, address_id=plan["address"])
    add("get_payment_methods")
    args = {"address_id": plan["address"], "payment_id": plan["payment"]}
    if plan["slot"]:
        args["slot_id"] = plan["slot"]
    add("place_order", **args)
    return steps


def slots(world, stages):
    rid = gold_restaurant(world)
    v = {"cuisine": term("cuisine", world["cuisine"]), "eta": world["eta_limit"],
         "address": term("address", world["address_key"]), "card": world["card"],
         "bread": term("dish", world["bread"]), "bread_qty": world["bread_qty"],
         "total_budget": f"{world['total_budget']:,}", "slot_time": world["slot_time"]}
    for p in PEOPLE:
        v[f"type_{p}"] = term("dish", world["person_type"][p])
        v[f"price_{p}"] = world["budgets"][p]
        kind, val = CUSTOM[p]
        if kind == "spice":
            v[f"spice_{p}"] = term("spice", val)
    return v


def check_rules(world, stages):
    rid = gold_restaurant(world)
    rows = [world["restaurants"][r] for r in world["listing"]]
    assert_never_first(rows, rid, "restaurant_id", "search_restaurants")
    for p in PEOPLE:
        did = best_dish(world, rid, p)
        assert did, p
        mains = [d for d in world["menus"][rid] if d["course"] == "main" and d["type"] == world["person_type"][p]]
        assert mains[0]["dish_id"] != did, f"never-first: dish for {p}"
        assert any(is_neighbour(did, d["dish_id"]) for d in mains), p
    plan = solve(world, stages)
    if "dessert" in stages:
        top = max((d for d in world["menus"][rid] if d["course"] == "dessert"), key=lambda d: d["rating"])
        assert plan["lines"][-1]["dish_id"] != top["dish_id"], "coupled budget must exclude the top dessert"
    if "offer" in stages:
        ranked = sorted((offer_discount(o, plan["total"]) or 0, o["code"]) for o in world["offers"])
        assert ranked[-1][0] > ranked[-2][0], "offer must have a unique best"


# --- tools -------------------------------------------------------------------

class Tools(Exp2Tools):
    TERMINAL_TOOL = "place_order"
    DOMAIN = DOMAIN

    def __init__(self, instance, language="en"):
        super().__init__(instance, language)
        self.cart = []
        self.offer = None
        self.order = None

    def tool_schemas(self):
        return [
            fn("get_saved_addresses", "List the user's saved delivery addresses.", {}),
            fn("search_restaurants", "Restaurants of a cuisine that deliver to an address, with rating, pure-veg "
               "flag and estimated delivery time in minutes to that address.",
               {"cuisine": enum(CUISINES), "address_id": S}),
            fn("get_menu", "Menu of a restaurant: dish id, name, course, type, price and rating.",
               {"restaurant_id": S}),
            fn("get_dish_details", "Customisation options of a dish: spice levels and whether it can be made Jain.",
               {"restaurant_id": S, "dish_id": S}),
            fn("add_item", "Add a dish to the cart with its customisation. The cart holds dishes from one "
               "restaurant only.",
               {"restaurant_id": S, "dish_id": S, "quantity": I, "spice_level": enum(SPICE), "jain": B}),
            fn("remove_item", "Remove a cart line.", {"line_id": S}),
            fn("view_cart", "Current cart lines and total.", {}),
            fn("list_offers", "Offers available at a restaurant.", {"restaurant_id": S}),
            fn("apply_offer", "Apply one offer code to the cart (replaces any earlier one).", {"code": S}),
            fn("get_delivery_slots", "Scheduled delivery slots for tonight from a restaurant to an address.",
               {"restaurant_id": S, "address_id": S}),
            fn("get_payment_methods", "List the user's saved payment methods.", {}),
            fn("place_order", "Place the order. Leave slot_id out for delivery as soon as possible.",
               {"address_id": S, "payment_id": S, "slot_id": S}, required=["address_id", "payment_id"]),
        ]

    def _rest(self, rid):
        r = self.world["restaurants"].get(rid)
        if r is None:
            self.bad(f"unknown restaurant_id '{rid}'")
        return r

    def _addr(self, aid):
        if aid not in {v[0] for v in ADDRESSES.values()}:
            self.bad(f"unknown address_id '{aid}'")

    def _dish(self, rid, did):
        d = next((x for x in self.world["menus"][rid] if x["dish_id"] == did), None)
        if d is None:
            self.bad(f"dish '{did}' is not on the menu of {rid}")
        return d

    def get_saved_addresses(self):
        return {"addresses": [{"address_id": a, "label": label} for a, label in ADDRESSES.values()]}

    def search_restaurants(self, cuisine, address_id):
        self._addr(address_id)
        key = next(k for k, v in ADDRESSES.items() if v[0] == address_id)
        if cuisine != self.world["cuisine"]:
            return {"restaurants": []}
        rows = [self.world["restaurants"][r] for r in self.world["listing"]]
        return {"restaurants": [{"restaurant_id": r["restaurant_id"], "name": r["name"], "rating": r["rating"],
                                 "pure_veg": r["pure_veg"], "eta_min": r["eta_min"][key]} for r in rows]}

    def get_menu(self, restaurant_id):
        self._rest(restaurant_id)
        return {"restaurant_id": restaurant_id,
                "dishes": [{k: d[k] for k in ("dish_id", "name", "course", "type", "price", "rating")}
                           for d in self.world["menus"][restaurant_id]]}

    def get_dish_details(self, restaurant_id, dish_id):
        self._rest(restaurant_id)
        d = self._dish(restaurant_id, dish_id)
        return {"dish_id": dish_id, "name": d["name"], "spice_levels": d["spice_levels"],
                "jain_available": d["jain_available"]}

    def add_item(self, restaurant_id, dish_id, quantity, spice_level, jain):
        self._rest(restaurant_id)
        d = self._dish(restaurant_id, dish_id)
        if self.cart and self.cart[0]["restaurant_id"] != restaurant_id:
            self.bad("the cart already has dishes from another restaurant; remove them first")
        if not isinstance(quantity, int) or quantity < 1:
            self.bad("quantity must be a positive integer")
        if jain and not d["jain_available"]:
            self.bad(f"dish '{dish_id}' cannot be made Jain")
        line = {"line_id": f"L-{len(self.cart) + 1}", "restaurant_id": restaurant_id, "dish_id": dish_id,
                "quantity": quantity, "spice_level": spice_level, "jain": bool(jain), "price": d["price"]}
        self.cart.append(line)
        return {"line_id": line["line_id"], "dish": d["name"], "cart_total": self._total()}

    def remove_item(self, line_id):
        before = len(self.cart)
        self.cart = [ln for ln in self.cart if ln["line_id"] != line_id]
        if len(self.cart) == before:
            self.bad(f"unknown line_id '{line_id}'")
        return {"removed": line_id, "cart_total": self._total()}

    def _total(self):
        return sum(ln["price"] * ln["quantity"] for ln in self.cart)

    def view_cart(self):
        return {"lines": [dict(ln) for ln in self.cart], "total": self._total(), "offer": self.offer}

    def list_offers(self, restaurant_id):
        self._rest(restaurant_id)
        return {"offers": [{k: o[k] for k in ("code", "description")} for o in self.world["offers"]]}

    def apply_offer(self, code):
        o = next((x for x in self.world["offers"] if x["code"] == code), None)
        if o is None:
            self.bad(f"unknown offer code '{code}'")
        disc = offer_discount(o, self._total())
        if disc is None:
            self.bad(f"offer {code} is not applicable to this cart")
        self.offer = code
        return {"applied": code, "discount": disc, "payable": self._total() - disc}

    def get_delivery_slots(self, restaurant_id, address_id):
        self._rest(restaurant_id)
        self._addr(address_id)
        return {"slots": [dict(s) for s in self.world["slots"]]}

    def get_payment_methods(self):
        return {"payment_methods": [
            {"payment_id": "PM-UPI-1", "type": "upi", "label": "UPI (arjun@okhdfcbank)"},
            {"payment_id": "PM-CC-4471", "type": "credit_card", "label": "HDFC Bank credit card ending 4471"},
            {"payment_id": "PM-WAL-1", "type": "wallet", "label": "App wallet"},
            {"payment_id": "PM-CC-4417", "type": "credit_card", "label": "HDFC Bank credit card ending 4417"}]}

    def place_order(self, address_id, payment_id, slot_id=None):
        self._addr(address_id)
        if payment_id not in {"PM-UPI-1", "PM-CC-4471", "PM-WAL-1", "PM-CC-4417"}:
            self.bad(f"unknown payment_id '{payment_id}'")
        if slot_id is not None and slot_id not in {s["slot_id"] for s in self.world["slots"]}:
            self.bad(f"unknown slot_id '{slot_id}'")
        if not self.cart:
            self.bad("the cart is empty")
        self.order = {"address_id": address_id, "payment_id": payment_id, "slot_id": slot_id}
        return {"status": "placed", "order_id": "ORD-" + str(self.world["seed"]) + str(len(self.cart))}

    def snapshot(self):
        return {"lines": [dict(ln) for ln in self.cart], "offer": self.offer, "order": self.order}


# --- verification ------------------------------------------------------------

def verify(traj, instance, final_state):
    world, stages = instance["world"], instance["stages"]
    plan = solve(world, stages)
    steps = traj.steps
    st = final_state or {}
    lines, order = st.get("lines", []), st.get("order")
    rid = plan["restaurant"]
    rest_used = lines[0]["restaurant_id"] if lines else None
    checks = []
    first_add = next((i for i, s in enumerate(steps, 1) if s["tool"] == "add_item" and "result" in s), None)
    decoy_rest = {r["role"]: r["restaurant_id"] for r in world["restaurants"].values()}
    r = world["restaurants"].get(rest_used)
    checks += [
        check("restaurant.veg", "restaurant", "selection", bool(r and r["pure_veg"]), first_add, rid, rest_used,
              decoy_rest["top_nonveg"]),
        check("restaurant.eta", "restaurant", "selection", bool(r and r["eta_min"][world["address_key"]] <= world["eta_limit"]),
              first_add, rid, rest_used, decoy_rest["slow"]),
        check("restaurant.best", "restaurant", "selection", rest_used == rid, first_add, rid, rest_used,
              decoy_rest["lookalike"]),
    ]

    def line_step(line_id):
        return next((i for i, s in enumerate(steps, 1) if s["tool"] == "add_item" and "result" in s
                     and s["result"].get("line_id") == line_id), None)

    menu = {d["dish_id"]: d for d in world["menus"].get(rest_used or rid, [])}
    for p in PEOPLE:
        if f"dish_{p}" not in stages:
            continue
        stage = f"dish_{p}"
        want = best_dish(world, rid, p)
        roles = {d["role"]: d["dish_id"] for d in world["menus"][rid]}
        mine = [ln for ln in lines if menu.get(ln["dish_id"], {}).get("type") == world["person_type"][p]
                and menu.get(ln["dish_id"], {}).get("course") == "main"]
        ln = mine[0] if len(mine) == 1 else None
        stp = line_step(ln["line_id"]) if ln else None
        got = ln["dish_id"] if ln else None
        d = menu.get(got) if got else None
        checks.append(check(f"{stage}.present", stage, "selection", ln is not None, stp, want, got))
        checks.append(check(f"{stage}.price", stage, "selection", bool(d and d["price"] <= world["budgets"][p]), stp,
                            want, got, roles.get(f"{p}:over")))
        checks.append(check(f"{stage}.best", stage, "selection", got == want, stp, want, got,
                            roles.get(f"{p}:lookalike")))
        kind, val = CUSTOM[p]
        if kind == "spice":
            checks.append(check(f"{stage}.spice", stage, "attribute", bool(ln and ln["spice_level"] == val), stp, val,
                                ln["spice_level"] if ln else None))
        else:
            checks.append(check(f"{stage}.jain", stage, "attribute", bool(ln and ln["jain"]), stp, True,
                                ln["jain"] if ln else None, roles.get(f"{p}:nojain")))
    if "sides" in stages:
        want = bread_dish(world, rid)
        mine = [ln for ln in lines if ln["dish_id"] == want]
        ln = mine[0] if mine else None
        stp = line_step(ln["line_id"]) if ln else None
        checks.append(check("sides.item", "sides", "selection", ln is not None, stp, want, ln and ln["dish_id"]))
        checks.append(check("sides.quantity", "sides", "attribute", bool(ln and ln["quantity"] == world["bread_qty"]),
                            stp, world["bread_qty"], ln["quantity"] if ln else None))
    if "dessert" in stages:
        want = plan["lines"][-1]["dish_id"]
        top = max((d for d in world["menus"][rid] if d["course"] == "dessert"), key=lambda d: d["rating"])["dish_id"]
        mine = [ln for ln in lines if menu.get(ln["dish_id"], {}).get("course") == "dessert"]
        ln = mine[0] if len(mine) == 1 else None
        stp = line_step(ln["line_id"]) if ln else None
        total = sum(x["price"] * x["quantity"] for x in lines)
        checks.append(check("dessert.best", "dessert", "coupled", bool(ln and ln["dish_id"] == want), stp, want,
                            ln["dish_id"] if ln else None, top))
        checks.append(check("dessert.total_budget", "dessert", "coupled", total <= world["total_budget"], stp,
                            world["total_budget"], total))
    if "offer" in stages:
        total = sum(x["price"] * x["quantity"] for x in lines)
        best = max(((offer_discount(o, total), o["code"]) for o in world["offers"] if offer_discount(o, total)),
                   default=(None, None))[1]
        checks.append(check("offer.best", "offer", "global", st.get("offer") == best and best is not None,
                            step_of(steps, "apply_offer"), best, st.get("offer")))
    extra = len(lines) - len(plan["lines"])
    checks.append(check("cart.no_extra_lines", "checkout", "global", extra == 0 and rest_used == rid if lines else False,
                        step_of(steps, "place_order"), len(plan["lines"]), len(lines)))
    final = step_of(steps, "place_order")
    other_addr = ADDRESSES["office" if world["address_key"] == "home" else "home"][0]
    other_card = CARDS["4471" if world["card"] == "4417" else "4417"]
    checks.append(check("checkout.address", "checkout", "anchor", bool(order and order["address_id"] == plan["address"]),
                        final, plan["address"], order and order["address_id"], other_addr, anchor=True))
    checks.append(check("checkout.payment", "checkout", "anchor", bool(order and order["payment_id"] == plan["payment"]),
                        final, plan["payment"], order and order["payment_id"], other_card, anchor=True))
    if "slot" in stages:
        checks.append(check("slot.id", "slot", "carried", bool(order and order.get("slot_id") == plan["slot"]), final,
                            plan["slot"], order and order.get("slot_id")))
    return summarize(traj, instance, checks, completed=order is not None)


# --- scripted faults (harness test) ------------------------------------------

def faulty_plan(world, stages, mode):
    plan = solve(world, stages)
    rid = plan["restaurant"]
    roles = {d["role"]: d["dish_id"] for d in world["menus"][rid]}
    if mode == "lookalike_dish":
        plan["lines"][0]["dish_id"] = roles["self:lookalike"]
        return plan, {"dish_self.best"}
    if mode == "wrong_spice":
        plan["lines"][0]["spice_level"] = "mild"
        return plan, {"dish_self.spice"}
    if mode == "anchor_card":
        plan["payment"] = CARDS["4471" if world["card"] == "4417" else "4417"]
        return plan, {"checkout.payment"}
    if mode == "anchor_address":
        plan["address"] = ADDRESSES["office" if world["address_key"] == "home" else "home"][0]
        return plan, {"checkout.address"}
    raise ValueError(mode)


FAULTS = ("lookalike_dish", "wrong_spice", "anchor_card", "anchor_address")
