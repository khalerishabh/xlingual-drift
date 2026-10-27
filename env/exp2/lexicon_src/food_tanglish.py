"""Draft tanglish lexicon for the food domain (LLM draft). Not loaded by the builder until
Rishabh has reviewed it and moved it to env/exp2/lexicon_src/."""

VERIFICATION = "draft: LLM, pending Rishabh"

LEX = {
    "intro": "Inniki night family-ku food delivery app-la dinner order pannunga.",
    "clauses": {
        "restaurant": "{address}-ku {eta} minutes-kulla deliver panna mudiyara pure-veg {cuisine} restaurants-la, rating adhigama irukkara restaurant-la irundhu order pannunga.",
        "dish_self": "Enakku oru {type_self}: price \u20b9{price_self}-kulla, adhula rating adhigama irukkara dish, spice level {spice_self}.",
        "dish_papa": "Appa-ku oru {type_papa}: price \u20b9{price_papa}-kulla, adhula rating adhigama irukkara dish, spice level {spice_papa}.",
        "dish_mummy": "Amma-ku oru {type_mummy}: price \u20b9{price_mummy}-kulla, Jain-a panna mudiyaradhula rating adhigama irukkara dish, adha Jain-a pannunga.",
        "dish_didi": "Akka-ku oru {type_didi}: price \u20b9{price_didi}-kulla, adhula rating adhigama irukkara dish, spice level {spice_didi}.",
        "sides": "Koodave {bread_qty} {bread} add pannunga.",
        "dessert": "Aprom oru dessert add pannunga: endha offer-ku munnadiyum full order \u20b9{total_budget}-kulla irukkura maadhiri, adhula rating adhigama irukkaradhu.",
        "offer": "Adhigama discount kudukkara offer-a apply pannunga.",
        "slot": "Delivery-a {slot_time} slot-ku schedule pannunga.",
        "checkout": "{address}-ku deliver pannunga, last digits {card} irukkara en HDFC credit card-la pay pannunga."
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
            "home": "Andheri West-la irukkara en veedu",
            "office": "Andheri East-la irukkara en office",
            "nani": "Thane-la irukkara paati veedu"
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
            "garlic_bread": "garlic bread portions",
            "phulka": "phulka"
        }
    }
}
