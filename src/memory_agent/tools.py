from langchain_core.tools import tool
from pydantic import BaseModel, Field
import httpx
import logging
from pprint import pprint
import json
from memory_agent.utils import format_data_to_string
from typing import Self
from enum import Enum
from memory_agent.settings import get_settings
from memory_agent.enums import VintageSource, FilterType, SortBy
from memory_agent.taste import TasteProfile
from memory_agent.enums import WineColorEnum, WineTypeEnum
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator, field_validator
from typing import Annotated
import json
import pycountry
import us
from pydantic import AfterValidator, Field



logger = logging.getLogger(__name__)

s = get_settings()

from typing import Annotated

import pycountry
import us
from pydantic import AfterValidator, Field


def get_us_state(country: str | None, region: str | None) -> str | None:
    """Return a valid US state name from a country and state name."""
    if country != "US":
        return
    if region is None:
        return
    state = us.states.lookup(region)
    if state is None:
        return
    return state.abbr


ALL_COUNTRIES: dict[str, str] = {item.alpha_2: item.name for item in pycountry.countries}  # type: ignore
"""Map of two letter country code to display name. The two letter code used in the API and stored in the DB."""
ALL_COUNTRIES_CODES = {v: k for k, v in ALL_COUNTRIES.items()}


def validate_country_code(v: str | None) -> str | None:
    if v == "USA":
        # Handle special case
        v = "US"
    if v and (country := ALL_COUNTRIES_CODES.get(v)):
        v = country
    if v is None:
        return
    if v not in ALL_COUNTRIES.keys():
        raise ValueError("Invalid country code")
    return v


CountryCode = Annotated[
    str | None,
    AfterValidator(validate_country_code),
    Field(default=None, description="ISO 3166-1 alpha-2 two-letter country code"),
]


def generate_alias_without_market_prefix(field_name: str) -> str:
    return field_name.replace("market_", "")

class MarketLocation(BaseModel):
    """
    Model used to determine availability of wine in user's market
    """

    # Outputs `country` and `region` over the wire for compatibility with existing (native) client code.
    model_config = ConfigDict(alias_generator=generate_alias_without_market_prefix, populate_by_name=True)

    market_country: CountryCode = None
    market_region: str | None = Field(default=None, description="Supports two letter US state code only")

    @computed_field
    @property
    def medusa_us_state(self) -> str | None:
        """Returns any US state in Medusa "province" format, e.g. `us-ca`"""
        if self.market_region is None:
            return None
        return "us-" + self.market_region.lower()

    @model_validator(mode="after")
    def validate_market_region(self) -> Self:
        # Runs after `CountryCode` field validator
        self.market_region = get_us_state(country=self.market_country, region=self.market_region)
        return self


class Filters(MarketLocation):
    wine_types: list[WineTypeEnum] | None = None
    wine_colors: list[WineColorEnum] | None = None
    merchants: list[str] | None = None
    is_natural: bool | None = None
    price_min: Annotated[float, Field(ge=0)] | None = None
    price_max: Annotated[float, Field(ge=0)] | None = None
    bottle_volumes: list[Annotated[int, Field(gt=0)]] | None = None
    vintage_year_min: int | None = None
    vintage_year_max: int | None = None
    user_rating: int | None = None
    expert_rating: int | None = None
    is_blended: bool | None = None
    grapes: list[str] | None = None
    countries: list[str] | None = None
    regions: list[str] | None = None
    foods: list[str] | None = None
    dishes: list[str] | None = None
    flavors: list[str] | None = None
    taste_profiles: list[TasteProfile] | None = None

    def __bool__(self):
        return any(getattr(self, k) for k in self.model_fields.keys())

    @model_validator(mode="before")
    @classmethod
    def check_unknown_keys(cls, values):
        if prices := values.get("prices"):
            if not isinstance(prices, list) or len(prices) != 2:
                logger.warning(f"Invalid prices: {prices}. Expected a list of two values")
            else:
                values["price_min"], values["price_max"] = prices

        if vintage_years := values.get("vintage_years"):
            if not isinstance(vintage_years, list) or len(vintage_years) != 2:
                logger.warning(f"Invalid vintage_years: {vintage_years}. Expected a list of two values")
            else:
                values["vintage_year_min"], values["vintage_year_max"] = vintage_years

        model_keys = sorted(list(cls.model_fields.keys()) + ["prices", "vintage_years"])
        if unknown_keys := set(values.keys()) - set(model_keys):
            logger.warning(f"Unknown keys: {unknown_keys}. Valid keys are: {model_keys}")

        return values

    @field_validator("foods", "flavors", "dishes")
    @classmethod
    def normalize_name(cls, v: list[str]) -> list[str]:
        return [i.lower() for i in v] if v else v



def get_us_state(country: str | None, region: str | None) -> str | None:
    """Return a valid US state name from a country and state name."""
    if country != "US":
        return
    if region is None:
        return
    state = us.states.lookup(region)
    if state is None:
        return
    return state.abbr


ALL_COUNTRIES: dict[str, str] = {item.alpha_2: item.name for item in pycountry.countries}  # type: ignore
"""Map of two letter country code to display name. The two letter code used in the API and stored in the DB."""
ALL_COUNTRIES_CODES = {v: k for k, v in ALL_COUNTRIES.items()}


def validate_country_code(v: str | None) -> str | None:
    if v == "USA":
        # Handle special case
        v = "US"
    if v and (country := ALL_COUNTRIES_CODES.get(v)):
        v = country
    if v is None:
        return
    if v not in ALL_COUNTRIES.keys():
        raise ValueError("Invalid country code")
    return v


CountryCode = Annotated[
    str | None,
    AfterValidator(validate_country_code),
    Field(default=None, description="ISO 3166-1 alpha-2 two-letter country code"),
]



class SearchParams(MarketLocation):
    query: str = Field(description="The query to search for wines.")
    skip_spell_check: bool | None = Field(default=False, description="Skip spell check")
    vintage_source: VintageSource | None = Field(
        default=None, description="The source of the vintages"
    )
    sort_by: SortBy = SortBy.recommended
    filters: Filters = Field(default_factory=Filters)
    removed_filters: Filters | None = None

    histogram_steps: int = s.histogram_steps

    def __hash__(self):
        return hash(self.model_dump_json(exclude_defaults=True))


    @property
    def bottle_volumes(self) -> list[int] | None:
        if filters := self.filters:
            return filters.bottle_volumes

def prettyprint_top_items(items, top=3):
    items = items[:top]
    # for item in items:
    #     pprint(item["data"])
    return json.dumps(items, indent=4)


def query_ai_service(
    data: SearchParams,
    timeout: int = 10,
    method: str = "POST",
):
    try:
        url = "https://api.dev.vinovoss.com/api/v2/vintages/search"
        #https://api.dev.vinovoss.com/_/ai/80/search
    
        response = httpx.request(method=method, url=url, json=data.model_dump(), timeout=timeout)

        if response.is_success:
            logger.debug(   
                f"query_ai_service(url={url}, payload={data})\n"
                f" -> Took {response.elapsed.total_seconds()}s\n"
                f" -> {response.status_code} {response.json()}"
            )
            return response.json()["items"]

        logger.error(
            f"query_ai_service(url={url}, data={data})\n" f" -> [{response.status_code}] {response.text}"
        )
        response.raise_for_status()
    except httpx.RequestError as e:
        logger.warning(f"Failed to query AI service: {e}")
        raise
from typing import List, TypedDict
from typing_extensions import Annotated
from langgraph.managed import IsLastStep, RemainingSteps
from typing import List, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.prebuilt import InjectedState

class AgentStateWithWines(TypedDict):
    messages: List[BaseMessage]
    wines: list[dict] | None
    is_last_step: IsLastStep
    remaining_steps: RemainingSteps


@tool("wine_search")
def wine_search(
    query: str,
    filters: Filters | dict | None = None,
    removed_filters: Filters | dict | None = None,
    histogram_steps: int | None = None,
    market_country: CountryCode | None = None,
    market_region: str | None = None
):
    """Search for wines using the Vinovoss API based on user preferences and filters.
    
    This tool queries the Vinovoss wine database to find wines matching specific criteria
    such as type, price range, taste profile, region, or occasion.

    region_varietals:
    - region: Bordeaux
        red_varietals: [ Cabernet Sauvignon, Merlot, Cabernet Franc, Petit Verdot, Malbec ]
        white_varietals: [ Sauvignon Blanc, Semillon ]
        common_styles: [ Dry, Full-bodied, Medium-bodied, Tannic, Oaked ]

    - region: Burgundy
        red_varietals: [ Pinot Noir ]
        white_varietals: [ Chardonnay ]
        common_styles: [ Light-bodied, Medium-bodied, Earthy, Mineral ]

    - region: Champagne
        red_varietals: [ Pinot Noir, Pinot Meunier ]
        white_varietals: [ Chardonnay ]
        common_styles: [ Sparkling, Traditional Method, Dry, Off-dry ]

    - region: Rhone Valley
        red_varietals: [ Syrah, Grenache, Mourvedre ]
        white_varietals: [ Viognier, Marsanne, Roussanne ]
        common_styles: [ Full-bodied, Spicy, Herbal ]

    varietal_styles:
    - varietal: Cabernet Sauvignon
        common_styles: [ Full-bodied, Tannic, Oaked, Red ]
        typical_regions: [ Bordeaux, Napa Valley, Margaret River ]

    - varietal: Merlot
        common_styles: [ Medium-bodied, Red, Fruity ]
        typical_regions: [ Bordeaux, Napa Valley ]

    - varietal: Pinot Noir
        common_styles: [ Light-bodied, Medium-bodied, Red, Earthy ]
        typical_regions: [ Burgundy, Willamette Valley, Marlborough ]

    - varietal: Chardonnay
        common_styles: [ Medium-bodied, Full-bodied, White, Oaked, Unoaked ]
        typical_regions: [ Burgundy, Napa Valley, Margaret River ]

    food_pairings:  
    - food_category: Meat
        foods: [ beef, steak, lamb, pork, chicken, duck, game ]
        wine_styles: [ Red, Full-bodied, Medium-bodied, Tannic ]

    - food_category: Seafood
        foods: [ fish, salmon, tuna, halibut, shellfish, shrimp, lobster, crab, oysters ]
        wine_styles: [ White, Light-bodied, Crisp, Dry ]

    - food_category: Cheese
        foods: [ soft cheese, hard cheese, blue cheese, goat cheese, cheddar, brie, gouda ]
        wine_styles: [ Varied, depending on cheese type ]

    - food_category: Dessert
        foods: [ chocolate, fruit tart, crème brûlée, cake, ice cream ]
        wine_styles: [ Sweet, Fortified, Late Harvest ]
    
    Search query pattern format:
        - pattern: "{Region} {Varietal}"
            examples: [ "Bordeaux Cabernet Sauvignon", "Napa Valley Chardonnay" ]

        - pattern: "{Style} {Varietal}"
            examples: [ "Dry Riesling", "Full-bodied Syrah" ]

        - pattern: "{Style} {Region} wine"
            examples: [ "Full-bodied Napa Valley wine", "Dry German wine" ]

        - pattern: "{Varietal} from {Region}"
            examples: [ "Sauvignon Blanc from Marlborough", "Pinot Noir from Burgundy" ]

        - pattern: "{Style} wine with {Food}"
            examples: [ "Full-bodied wine with steak", "Dry white wine with fish" ]

        - pattern: "{Production} {Varietal}"
            examples: [ "Organic Chardonnay", "Biodynamic Pinot Noir" ]
    
    Args:
        query (str): Search text completely.
        filters (Filters | dict): Wine criteria with exact values:
                - wine_colors (list[str]): Must be ['Red'], ['White'], ['Rose'], or ['Other']
                - wine_types (list[str]): Must be ['Still'], ['Sparkling'], ['Fortified'], ['Dessert'], or ['Not Wine']
                - merchants (list[str], optional): List of merchant names
                - is_natural (bool, optional): Filter for natural wines
                - price_min (float, optional): Minimum price (must be >= 0)
                - price_max (float, optional): Maximum price (must be >= 0)
                - bottle_volumes (list[int], optional): List of bottle volumes
                - vintage_year_min (int, optional): Minimum vintage year
                - vintage_year_max (int, optional): Maximum vintage year
                - user_rating (int, optional): Filter by user rating
                - expert_rating (int, optional): Filter by expert rating
                - is_blended (bool, optional): Filter for blended wines
                - grapes (list[str], optional): List of grape varieties
                - countries (list[str], optional): List of country names
                - regions (list[str], optional): List of region names
                - foods (list[str], optional): List of food pairings
                - dishes (list[str], optional): List of dish pairings
                - flavors (list[str], optional): List of flavor profiles
                - taste_profiles (list[TasteProfile], optional): List of taste profiles
        removed_filters (Filters | dict, optional): Filters to exclude
        histogram_steps (int, optional): Number of histogram steps
        market_country (CountryCode, optional): ISO 3166-1 alpha-2 two-letter country code
        market_region (str | None, optional): Two letter US state code
    
    Returns:
        list[dict]: List of wine vintages with details like name,
            price, region, ratings, and tasting notes.
    """
    data = SearchParams(
        query=query,
        market_country=market_country,
        market_region=market_region
    )
    if histogram_steps is not None:
        data.histogram_steps = histogram_steps
    if isinstance(filters, dict):
        data.filters = Filters(**filters)
    elif isinstance(filters, Filters):
        data.filters = filters
    elif filters is None:
        data.filters = Filters()
    elif isinstance(filters, str):
        data.filters = Filters(**json.loads(filters))
    else:
        raise ValueError("Invalid filters")
    if isinstance(removed_filters, dict):
        data.removed_filters = Filters(**removed_filters)
    elif isinstance(removed_filters, Filters):
        data.removed_filters = removed_filters
    elif removed_filters is None:
        data.removed_filters = Filters()
    print("Get wine data from Vinovoss search API.")
    response = query_ai_service(data=data)
    return response


@tool("sort_wines")
def sort_wines(
    wines: list[dict],
    sort_by: SortBy,
    descending: bool = False
) -> list[dict]:
    """Sort wines by price, rating, vintage, etc.
    
    Args:
        wines (list[dict]): List of wines to sort.
        sort_by (SortBy): Sort by recommended, price, price-desc, rating, rating-desc, rating_count, rating_count-desc, title, or title-desc.
        descending (bool, optional): Sort in descending order. Defaults to False.
    Returns:
        list[dict]: List of wines sorted by the specified field.
    """
    key_fn = {
        SortBy.recommended: lambda w: w["recommendation_score"],
        SortBy.price: lambda w: w["price"],
        SortBy.price_desc: lambda w: -w["price"],
        SortBy.rating: lambda w: w["ratings"]["average"],
        SortBy.rating_desc: lambda w: -w["ratings"]["average"],
        SortBy.rating_count: lambda w: w["ratings"]["count"],
        SortBy.rating_count_desc: lambda w: -w["ratings"]["count"],
        SortBy.title: lambda w: w["title"].lower(),  # pyright: ignore [reportAssignmentType]. Overlap with the title() method but we need to keep it
        SortBy.title_desc: lambda w: -w["title"].lower(),
    }[sort_by]
    print("Sorting wines by", sort_by)
    return sorted(wines, key=key_fn, reverse=descending)


if __name__ == "__main__":
    # Create search parameters
    params = SearchParams(query="red wine under 200")
    # Call the underlying function directly to avoid tool wrapper
    result = wine_search.func(data=params)
    print(prettyprint_top_items(result))