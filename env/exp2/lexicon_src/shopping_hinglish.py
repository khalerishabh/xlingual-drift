"""Draft hinglish lexicon for the shopping domain (LLM draft). Not loaded by the builder until
Rishabh has reviewed it and moved it to env/exp2/lexicon_src/."""

VERIFICATION = "author: Rishabh, 2026-10-28"

LEX = {
    "intro": "Family ke liye Diwali shopping. Sab kuch {deadline_day} November tak pahunch jaana chahiye, aur jab tak main alag se na bolun, saamaan humare ghar aayega.",
    "clauses": {
        "item_self": "Mere liye ek {cat_self}: size {size_self}, colour {colour_self}, price \u20b9{price_self} se kam, unme jiski rating sabse zyada ho{addr_self}.",
        "item_father": "Papa ke liye ek {cat_father}: size {size_father}, colour {colour_father}, price \u20b9{price_father} se kam, unme jiski rating sabse zyada ho{addr_father}.",
        "item_mother": "Mummy ke liye ek {cat_mother}: size {size_mother}, colour {colour_mother}, price \u20b9{price_mother} se kam, unme jiski rating sabse zyada ho{addr_mother}.",
        "item_sister": "Didi ke liye ek {cat_sister}: size {size_sister}, colour {colour_sister}, price \u20b9{price_sister} se kam, unme jiski rating sabse zyada ho{addr_sister}, bas Mummy aur Didi ka saamaan mila ke \u20b9{pair_budget} ke andar rahe.",
        "gift": "{gift_a} aur {gift_b} ke items gift-wrap karwana.",
        "exchange": "Mere last order wala {ex_cat} size {ex_size} se exchange bhi kar do, colour same rahe.",
        "coupon": "Wo coupon lagao jisse sabse zyada discount mile.",
        "checkout": "Payment mere ICICI credit card se karna jiske last digits {card} hain, aur {slot} wala delivery slot choose karna."
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
            "nani": ", aur ye Pune mein Nani ke ghar deliver ho"
        },
        "relation": {
            "father": "Papa",
            "mother": "Mummy",
            "sister": "Didi"
        },
        "slot": {
            "morning": "morning (9 am - 12 noon)",
            "afternoon": "afternoon (12 noon - 3 pm)",
            "evening": "evening (6 pm - 9 pm)"
        }
    }
}
