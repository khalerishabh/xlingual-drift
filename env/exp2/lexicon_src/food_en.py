R = "\u20b9"
LEX = {
    "intro": "Please order dinner for the family tonight on the food delivery app.",
    "clauses": {
        "restaurant": "Order from the highest-rated pure-veg {cuisine} restaurant that can deliver to {address} within {eta} minutes.",
        "dish_self": "For me: the highest-rated {type_self} under " + R + "{price_self}, spice level {spice_self}.",
        "dish_papa": "For Papa: the highest-rated {type_papa} under " + R + "{price_papa}, spice level {spice_papa}.",
        "dish_mummy": "For Mummy: the highest-rated {type_mummy} under " + R + "{price_mummy} that can be made Jain, and make it Jain.",
        "dish_didi": "For Didi: the highest-rated {type_didi} under " + R + "{price_didi}, spice level {spice_didi}.",
        "sides": "Add {bread_qty} {bread}.",
        "dessert": "Then add the highest-rated dessert that keeps the whole order within " + R + "{total_budget} before any offer.",
        "offer": "Apply the offer that gives the biggest discount.",
        "slot": "Schedule the delivery for the {slot_time} slot.",
        "checkout": "Deliver to {address} and pay with my HDFC credit card ending {card}.",
    },
    "terms": {
        "cuisine": {"north_indian": "North Indian", "south_indian": "South Indian", "indo_chinese": "Indo-Chinese",
                    "italian": "Italian", "gujarati": "Gujarati"},
        "address": {"home": "my home in Andheri West", "office": "my office in Andheri East", "nani": "Nani's house in Thane"},
        "spice": {"mild": "mild", "medium": "medium", "spicy": "spicy"},
        "dish": {"paneer": "paneer curry", "dal": "dal", "biryani": "veg biryani", "kofta": "kofta curry",
                 "dosa": "dosa", "idli": "idli plate", "uttapam": "uttapam", "meals": "South Indian meals plate",
                 "noodles": "noodles", "fried_rice": "fried rice", "manchurian": "veg Manchurian", "soup": "soup",
                 "pizza": "pizza", "pasta": "pasta", "risotto": "risotto", "lasagne": "lasagne",
                 "thali": "Gujarati thali", "khichdi": "khichdi", "dhokla": "dhokla plate", "undhiyu": "undhiyu",
                 "butter_roti": "butter rotis", "parotta": "parottas", "spring_roll": "spring rolls",
                 "garlic_bread": "portions of garlic bread", "phulka": "phulkas"},
    },
}
