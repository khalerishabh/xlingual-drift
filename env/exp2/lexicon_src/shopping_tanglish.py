"""Draft tanglish lexicon for the shopping domain (LLM draft). Not loaded by the builder until
Rishabh has reviewed it and moved it to env/exp2/lexicon_src/."""

VERIFICATION = "author: Rishabh, 2026-10-28"

LEX = {
    "intro": "Family-ku Deepavali shopping. Ellam November {deadline_day}-kulla vandhudanum, naan vera edhuvum sollala-na items engha veettukku varanum.",
    "clauses": {
        "item_self": "Enakku oru {cat_self}: size {size_self}, colour {colour_self}, price \u20b9{price_self}-kulla, adhula rating adhigama irukkaradhu{addr_self}.",
        "item_father": "Appa-ku oru {cat_father}: size {size_father}, colour {colour_father}, price \u20b9{price_father}-kulla, adhula rating adhigama irukkaradhu{addr_father}.",
        "item_mother": "Amma-ku oru {cat_mother}: size {size_mother}, colour {colour_mother}, price \u20b9{price_mother}-kulla, adhula rating adhigama irukkaradhu{addr_mother}.",
        "item_sister": "Akka-ku oru {cat_sister}: size {size_sister}, colour {colour_sister}, price \u20b9{price_sister}-kulla, adhula rating adhigama irukkaradhu{addr_sister}, aana Amma, Akka rendu perodha items-um serthu \u20b9{pair_budget}-kulla irukkanum.",
        "gift": "{gift_a}, {gift_b} rendu perodha items-ayum gift-wrap pannunga.",
        "exchange": "En last order-la vandha {ex_cat}-a same colour-la size {ex_size}-ku exchange pannunga.",
        "coupon": "Adhigama discount kudukkara coupon-a apply pannunga.",
        "checkout": "Last digits {card} irukkara en ICICI credit card-la pay panni, {slot} delivery slot-a choose pannunga."
    },
    "terms": {
        "category": {
            "kurta": "kurta",
            "shirt": "shirt",
            "kurti": "kurti",
            "sneakers": "sneakers",
            "jeans": "jeans",
            "saree": "saree"
        },
        "colour": {
            "blue": "blue",
            "black": "black",
            "white": "white",
            "red": "red",
            "green": "green",
            "maroon": "maroon",
            "yellow": "yellow",
            "grey": "grey"
        },
        "deliver_to": {
            "home": "",
            "nani": ", idha Pune-la irukkara paati veettukku deliver pannunga"
        },
        "relation": {
            "father": "Appa",
            "mother": "Amma",
            "sister": "Akka"
        },
        "slot": {
            "morning": "morning (9 am - 12 noon)",
            "afternoon": "afternoon (12 noon - 3 pm)",
            "evening": "evening (6 pm - 9 pm)"
        }
    }
}
