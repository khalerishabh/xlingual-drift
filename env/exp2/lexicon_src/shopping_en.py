R = "\u20b9"
LEX = {
    "intro": "Diwali shopping for the family. Everything must arrive by {deadline_day} November, and items come to our home unless I say otherwise.",
    "clauses": {
        "item_self": "For me: the highest-rated {cat_self} in size {size_self} and {colour_self} under " + R + "{price_self}{addr_self}.",
        "item_father": "For Papa: the highest-rated {cat_father} in size {size_father} and {colour_father} under " + R + "{price_father}{addr_father}.",
        "item_mother": "For Mummy: the highest-rated {cat_mother} in size {size_mother} and {colour_mother} under " + R + "{price_mother}{addr_mother}.",
        "item_sister": "For Didi: the highest-rated {cat_sister} in size {size_sister} and {colour_sister} under " + R + "{price_sister}{addr_sister}, as long as Mummy's and Didi's items together stay within " + R + "{pair_budget}.",
        "gift": "Gift-wrap the items for {gift_a} and {gift_b}.",
        "exchange": "Also exchange the {ex_cat} from my last order for size {ex_size}, same colour.",
        "coupon": "Use the coupon that gives the biggest discount.",
        "checkout": "Pay with my ICICI credit card ending {card} and choose the {slot} delivery slot.",
    },
    "terms": {
        "category": {"kurta": "kurta", "shirt": "shirt", "kurti": "kurti", "sneakers": "sneakers", "jeans": "jeans",
                     "saree": "saree"},
        "colour": {"blue": "blue", "black": "black", "white": "white", "red": "red", "green": "green",
                   "maroon": "maroon", "yellow": "yellow", "grey": "grey"},
        "deliver_to": {"home": "", "nani": ", delivered to Nani's house in Pune"},
        "relation": {"father": "Papa", "mother": "Mummy", "sister": "Didi"},
        "slot": {"morning": "morning (9 am - 12 noon)", "afternoon": "afternoon (12 noon - 3 pm)",
                 "evening": "evening (6 pm - 9 pm)"},
    },
}
