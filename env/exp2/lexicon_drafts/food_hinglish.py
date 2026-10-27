"""Draft hinglish lexicon for the food domain (LLM draft). Not loaded by the builder until
Rishabh has reviewed it and moved it to env/exp2/lexicon_src/."""

VERIFICATION = "draft: LLM, pending Rishabh"

LEX = {
    "intro": "Aaj raat family ke liye food delivery app se dinner order kar do.",
    "clauses": {
        "restaurant": "Us pure-veg {cuisine} restaurant se order karo jo {address} pe {eta} minute ke andar deliver kar sake, aur unme jiski rating sabse zyada ho.",
        "dish_self": "Mere liye ek {type_self}: price \u20b9{price_self} se kam, unme sabse high-rated wali dish, spice level {spice_self}.",
        "dish_papa": "Papa ke liye ek {type_papa}: price \u20b9{price_papa} se kam, unme sabse high-rated wali dish, spice level {spice_papa}.",
        "dish_mummy": "Mummy ke liye ek {type_mummy}: price \u20b9{price_mummy} se kam, jo Jain ban sake unme sabse high-rated wali dish, aur use Jain banwana.",
        "dish_didi": "Didi ke liye ek {type_didi}: price \u20b9{price_didi} se kam, unme sabse high-rated wali dish, spice level {spice_didi}.",
        "sides": "Saath mein {bread_qty} {bread} bhi add kar do.",
        "dessert": "Phir ek dessert add karo: sabse high-rated wala, jiske baad bhi poora order kisi bhi offer se pehle \u20b9{total_budget} ke andar rahe.",
        "offer": "Wo offer lagao jisse sabse zyada discount mile.",
        "slot": "Delivery {slot_time} wale slot ke liye schedule karo.",
        "checkout": "Delivery {address} pe karwana aur payment mere HDFC credit card se karna jiske last digits {card} hain."
    },
    "terms": {
        "cuisine": {
            "north_indian": "North Indian",
            "south_indian": "South Indian",
            "indo_chinese": "Indo-Chinese",
            "italian": "Italian",
            "gujarati": "Gujarati"
        },
        "address": {
            "home": "Andheri West wale mere ghar",
            "office": "Andheri East wale mere office",
            "nani": "Thane mein Nani ke ghar"
        },
        "spice": {
            "mild": "mild",
            "medium": "medium",
            "spicy": "spicy"
        },
        "dish": {
            "paneer": "paneer curry",
            "dal": "dal",
            "biryani": "veg biryani",
            "kofta": "kofta curry",
            "dosa": "dosa",
            "idli": "idli plate",
            "uttapam": "uttapam",
            "meals": "South Indian meals plate",
            "noodles": "noodles",
            "fried_rice": "fried rice",
            "manchurian": "veg Manchurian",
            "soup": "soup",
            "pizza": "pizza",
            "pasta": "pasta",
            "risotto": "risotto",
            "lasagne": "lasagne",
            "thali": "Gujarati thali",
            "khichdi": "khichdi",
            "dhokla": "dhokla plate",
            "undhiyu": "undhiyu",
            "butter_roti": "butter roti",
            "parotta": "parotta",
            "spring_roll": "spring rolls",
            "garlic_bread": "garlic bread ke portion",
            "phulka": "phulke"
        }
    }
}
