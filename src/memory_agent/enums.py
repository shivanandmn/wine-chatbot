from enum import Enum


class StringEnum(str, Enum):
    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

    @classmethod
    def values(cls) -> list[str]:
        return list(map(str, cls))


class VintageSearchDataType(str, Enum):
    vintage = "vintage"
    message = "message"
    meta = "meta"


class VintageSource(StringEnum):
    favorites = "Favorites"
    wine_cellar = "Wine Cellar"
    drinking_history = "Drinking History"
    shared_list = "Shared List"
    wishlist = "Wishlist"
    celebrity = "Celebrity"
    award_winning = "Award Winning"
    organic_biodynamic = "Organic Biodynamic"
    orange_wines = "Orange Wines"
    rare_collectable = "Rare Collectable"
    sommelier_selections = "Sommelier Selections"
    must_try = "Must Try"
    xmas = "Xmas"  # curated list of Christmas wines by the wine experts
    explore = "Explore"


class WineTypeEnum(StringEnum):
    STILL = "Still"
    SPARKLING = "Sparkling"
    FORTIFIED = "Fortified"
    DESSERT = "Dessert"
    NOT_WINE = "Not Wine"


class WineColorEnum(StringEnum):
    RED = "Red"
    WHITE = "White"
    ROSE = "Rose"
    OTHER = "Other"


class LegacyWineType(StringEnum):
    # deprecated
    RED = "Red"
    WHITE = "White"
    SPARKLING = "Sparkling"
    ROSE = "Rose"
    DESSERT = "Dessert"
    FORTIFIED = "Fortified"
    OTHER = "Other"


class TopVintagesFieldName(StringEnum):
    grape = "grape"
    winery = "winery"
    region = "region"
    dish = "dish"


class TasteProfile(StringEnum):
    DRY = "Dry"
    SWEET = "Sweet"
    LOW_ALCOHOL = "Low Alcohol"
    AROMATIC = "Aromatic"
    DELICATE = "Delicate"
    BOLD = "Bold"
    REFRESHING = "Refreshing"
    SMOOTH = "Smooth"


class PromoType(StringEnum):
    most_popular = "Most Popular"
    highest_rating = "Highest Rating"
    premium = "Premium"
    best_value = "Best Value"


class FilterType(StringEnum):
    wine_types = "wine_types"
    wine_colors = "wine_colors"
    merchants = "merchants"
    is_natural = "is_natural"
    prices = "prices"
    bottle_volumes = "bottle_volumes"
    vintage_years = "vintage_years"
    user_ratings = "user_ratings"
    expert_ratings = "expert_ratings"
    grapes = "grapes"
    is_blended = "is_blended"
    countries = "countries"
    regions = "regions"
    foods = "foods"
    dishes = "dishes"
    flavors = "flavors"
    taste_profiles = "taste_profiles"


class Gender(str, Enum):
    male = "Male"
    female = "Female"
    other = "Others"
    not_specified = "Not Specified"


class SharedSource(StringEnum):
    TASTE_LOG = "Taste Log"  # aka Drinking History
    WISHLIST = "Wishlist"
    WINE_CELLAR = "Wine Cellar"


DEFAULT_GENDER = Gender.not_specified


class GrapeColor(StringEnum):
    red = "Red"
    white = "White"


class Pronoun(StringEnum):
    HE = "He/Him"
    SHE = "She/Her"
    THEY = "They/Them"
    OTHER = "Other"


class RatingSort(StringEnum):
    RECENT = "recent"
    OLDEST = "oldest"
    HIGHEST_RATING = "highest_rating"
    LOWEST_RATING = "lowest_rating"
    MOST_LIKED = "most_liked"


class UserEmailSubscriptionOption(StringEnum):
    PROMOTIONS = "promotions"
    NEWSLETTER = "newsletter"


class SignupPlatform(StringEnum):
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"


class OAuthProvider(StringEnum):
    APPLE = "apple"
    GOOGLE = "google"


class CopilotStatus(StringEnum):
    INACTIVE = "inactive"
    """Not yet joined waitlist"""
    WAITLIST = "waitlist"
    ACTIVE = "active"


class WSStatus(StringEnum):
    connected = "connected"
    disconnected = "disconnected"


class SortBy(StringEnum):
    recommended = "recommended"
    price = "price"
    price_desc = "price-desc"
    rating = "rating"
    rating_desc = "rating-desc"
    rating_count = "rating_count"
    rating_count_desc = "rating_count-desc"
    title = "title"  # pyright: ignore [reportAssignmentType]. Overlap with the title() method but we need to keep it
    title_desc = "title-desc"


class SortUserRatingBy(StringEnum):
    recent = "recent"
    oldest = "oldest"
    highest_rating = "highest_rating"
    lowest_rating = "lowest_rating"


class Platform(StringEnum):
    ios = "ios"
    android = "android"


class SmartSommPlatform(StringEnum):
    web = "web"
    native = "native"
