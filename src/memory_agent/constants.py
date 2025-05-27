from enum import Enum


class TAGS(str, Enum):
    auth = "Auth"
    users = "Users"


# For formatting message from AI output
SUFFIX_TYPES = ("food",)


alcohol_adj = [
    ("very low", "VL"),
    ("low", "L"),
    ("moderate", "M"),
    ("moderate", "MH"),
    ("high", "H"),
    ("very high", "VH"),
]

sweetness_adj = [
    ("dry", 1.5),
    ("almost dry", 2.5),
    ("semi-sweet", 3.5),
    ("sweet", 4.5),
    ("luscious", 5),
]
intensity_adj = [
    ("neutral", 1.5),
    ("subtle", 2.5),
    ("mildly aromatic", 3.5),
    ("fragrant", 4),
    ("pronounced", 4.5),
    ("intense", 5),
]
body_adj = [
    ("light", 1.5),
    ("delicate", 2),
    ("medium", 3),
    ("generous", 3.5),
    ("bold", 4),
    ("rich", 4.5),
    ("full", 5),
]
acidity_adj = [
    ("soft", 1.5),
    ("supple", 2),
    ("smooth", 3),
    ("refreshing", 3.5),
    ("lean", 4),
    ("vibrant", 4.5),
    ("searing", 5),
]
tannin_adj = [
    ("no tannins", 0.5),
    ("gentle", 1),
    ("smooth", 2),
    ("silky", 2.5),
    ("velvety", 3),
    ("firm", 3.5),
    ("grainy", 4),
    ("grippy", 4.5),
    ("high", 5),
]
# TODO: move images_host and default_images_host to the settings.py
IMAGES_HOST = "https://vinovoss.com/images"
DISH_IMAGES_ROOT = f"{IMAGES_HOST}/dishes"
AROMAS_IMAGE_ROOT = f"{IMAGES_HOST}/flavors"

example_queries = (
    "What riesling to drink",
    "Hungarian Cabernet Franc",
    "Barbera with pork",
    "I'm looking for a demi sec wine",
    "What moscato to drink",
    "Chianti wine",
    "Burgundy goes well with beef",
    "Riesling for asian food",
    "What to drink in Austria",
    "Wine from Japan",
    "Blanc de noir",
    "Wine to drink by the fireplace",
    "Best wine from chile",
    "Fruity Cabernet Sauvignon",
    "I'm looking for a red wine that's good with steak",
    "Recommend a white wine for a summer picnic",
    "I want a sparkling wine for a special occasion",
    "I need a wine for a party of 20 people",
    "I'm craving a bold, full-bodied red wine",
)

price_ranges_3_4 = dict(
    red=(14.33, 44.57),
    white=(11.97, 27.69),
    rose=(9.1, 20.0),
    dessert=(13.87, 37.56),
    fortified=(16.55, 47.89),
    sparkling=(13.03, 31.73),
)

drinking_window_below_3 = dict(
    red=4,
    white=3,
    rose=2,
    dessert=5,
    fortified=10,
    sparkling=4,
)
drinking_window_3_4 = dict(
    red=8,
    white=5,
    rose=4,
    dessert=0,
    fortified=0,
    sparkling=8,
)

drinking_window_above_4 = dict(
    red=40,
    white=25,
    rose=15,
    dessert=60,
    fortified=60,
    sparkling=20,
)
