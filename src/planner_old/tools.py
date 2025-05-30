from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import json # Ensure json is imported if used by Filters or SearchParams internally for string parsing, though we pass dicts

# Import necessary components from memory_agent.tools
from memory_agent.tools import query_ai_service, SearchParams
from memory_agent.tools import Filters as VinovossFilters # Alias to avoid name collision

class WineColor(Enum):
    RED = 'Red'
    WHITE = 'White'
    ROSE = 'Rose'
    OTHER = 'Other'

class WineType(Enum):
    STILL = 'Still'
    SPARKLING = 'Sparkling'
    FORTIFIED = 'Fortified'
    DESSERT = 'Dessert'
    NOT_WINE = 'Not Wine'

class WineStyle(Enum):
    DRY = 'Dry'
    FULL_BODIED = 'Full-bodied'
    MEDIUM_BODIED = 'Medium-bodied'
    LIGHT_BODIED = 'Light-bodied'
    TANNIC = 'Tannic'
    OAKED = 'Oaked'
    EARTHY = 'Earthy'
    MINERAL = 'Mineral'
    SPARKLING = 'Sparkling'
    SPICY = 'Spicy'
    HERBAL = 'Herbal'
    CRISP = 'Crisp'
    SWEET = 'Sweet'

@dataclass
class TasteProfile:
    sweetness: int  # 1-5 scale
    body: int      # 1-5 scale
    acidity: int   # 1-5 scale
    tannin: int    # 1-5 scale

@dataclass
class WineFilters:
    wine_colors: Optional[List[WineColor]] = None
    wine_types: Optional[List[WineType]] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    grapes: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    foods: Optional[List[str]] = None
    taste_profile: Optional[TasteProfile] = None
    vintage_year_min: Optional[int] = None
    vintage_year_max: Optional[int] = None
    expert_rating: Optional[int] = None
    is_natural: Optional[bool] = None
    is_blended: Optional[bool] = None
    flavors: Optional[List[str]] = None

@dataclass
class WineShoppingPrice:
    variant_id: Optional[str] = None
    price_amount: Optional[float] = None
    vintage_id: Optional[str] = None
    wine_id: Optional[int] = None
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None

@dataclass
class WineImages:
    bottle: Optional[str] = None
    bottle_mobile: Optional[str] = None

@dataclass
class WineSearchResult:
    id: str
    title: str
    slug: Optional[str] = None
    wine_slug: Optional[str] = None
    vintage_year: Optional[int] = None
    image_url: Optional[str] = None
    images: Optional[WineImages] = None
    user_rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    labels: List[str] = field(default_factory=list)
    region: Optional[str] = None
    country: Optional[str] = None
    shopping_prices: List[WineShoppingPrice] = field(default_factory=list)
    is_natural: Optional[bool] = None
    bottle_volume: Optional[str] = None
    link_to_shop: Optional[str] = None

    # Fields from old WineSearchResult, now optional, to be populated if possible
    price: Optional[float] = None # Should be derived from shopping_prices
    color: Optional[WineColor] = None
    type: Optional[WineType] = None
    grapes: List[str] = field(default_factory=list)
    taste_profile: Optional[TasteProfile] = None
    food_pairings: List[str] = field(default_factory=list)
    is_blended: Optional[bool] = None


def create_occasion_filters(occasion: str) -> WineFilters:
    """Create wine filters based on the occasion using Vinovoss patterns."""
    filters = WineFilters()
    
    if occasion.lower() == 'wedding':
        filters.wine_types = [WineType.SPARKLING, WineType.STILL]
        filters.price_min = 30  # Higher quality for weddings
        filters.expert_rating = 4  # Higher rated wines for special occasions
    elif occasion.lower() == 'dinner':
        filters.wine_types = [WineType.STILL]
        filters.expert_rating = 3
    elif occasion.lower() == 'celebration':
        filters.wine_types = [WineType.SPARKLING]
        filters.expert_rating = 4
    
    return filters

def create_food_filters(food: str) -> WineFilters:
    """Create basic wine filters based on food pairing.
    The LLM agent calling this tool is expected to provide more nuanced
    wine style, color, or grape preferences based on its knowledge.
    """
    filters = WineFilters()
    filters.foods = [food.lower()]

    # Basic heuristic for wine color - LLM should refine this.
    if any(meat in food.lower() for meat in ['beef', 'steak', 'lamb', 'pork', 'game']):
        filters.wine_colors = [WineColor.RED]
    elif any(item in food.lower() for item in ['fish', 'seafood', 'shellfish', 'chicken', 'turkey']):
        filters.wine_colors = [WineColor.WHITE]
    
    return filters

def construct_search_query(occasion: str, food_pairing: Optional[str] = None, style: Optional[WineStyle] = None) -> str:
    """Construct a search query following Vinovoss patterns."""
    query_parts = []
    
    # Add style if provided
    if style:
        query_parts.append(style.value)
    
    # Add occasion-specific terms
    if occasion.lower() == 'wedding':
        if not style:
            query_parts.append('Sparkling')
    elif occasion.lower() == 'dinner':
        if not style:
            query_parts.append('Full-bodied')
    
    # Add basic term
    query_parts.append('wine')
    
    # Add food pairing if provided
    if food_pairing:
        query_parts.append(f"with {food_pairing}")
    
    return " ".join(query_parts)

def wine_search(
    occasion: str,
    food_pairing: Optional[str] = None,
    budget: Optional[float] = None,
    preferences: Optional[Dict] = None
) -> List[WineSearchResult]:
    """Enhanced wine search using Vinovoss API with structured data and patterns."""
    
    # Create base filters from occasion
    filters = create_occasion_filters(occasion)
    
    # Add food pairing filters
    if food_pairing:
        food_filters = create_food_filters(food_pairing)
        filters.wine_colors = food_filters.wine_colors or filters.wine_colors
        filters.foods = food_filters.foods
        filters.taste_profile = food_filters.taste_profile or filters.taste_profile
    
    # Add budget and preference constraints
    if budget:
        filters.price_max = budget
    
    if preferences:
        if 'taste_profile' in preferences and isinstance(preferences['taste_profile'], dict):
            filters.taste_profile = TasteProfile(**preferences['taste_profile'])
        elif 'taste_profile' in preferences and isinstance(preferences['taste_profile'], TasteProfile):
            filters.taste_profile = preferences['taste_profile']
            
        if 'regions' in preferences and isinstance(preferences['regions'], list):
            filters.regions = preferences['regions']
        
        if 'grapes' in preferences and isinstance(preferences['grapes'], list):
            filters.grapes = (filters.grapes or []) + preferences['grapes']

        if 'wine_colors' in preferences and isinstance(preferences['wine_colors'], list):
            filters.wine_colors = (filters.wine_colors or []) + [WineColor(c) if isinstance(c, str) else c for c in preferences['wine_colors']]
        
        if 'wine_types' in preferences and isinstance(preferences['wine_types'], list):
            filters.wine_types = (filters.wine_types or []) + [WineType(t) if isinstance(t, str) else t for t in preferences['wine_types']]

    # Construct query using Vinovoss patterns
    style = None
    if filters.taste_profile:
        if filters.taste_profile.body >= 4:
            style = WineStyle.FULL_BODIED
        elif filters.taste_profile.body <= 2:
            style = WineStyle.LIGHT_BODIED
    
    query = construct_search_query(occasion, food_pairing, style)
    
    # Convert to Vinovoss API format
    api_filters = {
        'wine_colors': [color.value for color in filters.wine_colors] if filters.wine_colors else None,
        'wine_types': [type.value for type in filters.wine_types] if filters.wine_types else None,
        'price_max': filters.price_max,
        'price_min': filters.price_min,
        'foods': filters.foods,
        'grapes': list(set(filters.grapes)) if filters.grapes else None,  # Remove duplicates
        'regions': filters.regions,
        'expert_rating': filters.expert_rating,
        'is_natural': filters.is_natural,
        'is_blended': filters.is_blended,
        'vintage_year_min': filters.vintage_year_min,
        'vintage_year_max': filters.vintage_year_max,
        'flavors': filters.flavors,
        # 'taste_profiles': [filters.taste_profile.__dict__] if filters.taste_profile else None, # Pass taste_profile as dict
    }

    # Map local planner.tools.TasteProfile numeric values to API string descriptors.
    # These string descriptors will be used as the 'value' in memory_agent.taste.TasteProfile objects.
    # The original numeric score will be used as 'step'.
    api_taste_profile_objects_input = []
    if filters.taste_profile:
        tp = filters.taste_profile # This is our local planner.tools.TasteProfile dataclass instance
        
        # API allowed strings: 'Dry', 'Sweet', 'Low Alcohol', 'Aromatic', 'Delicate', 'Bold', 'Refreshing', 'Smooth'
        # TasteProfileName enum values (for 'name' field): 'acidity', 'intensity', 'sweetness', 'tannin', 'body', 'alcohol'

        if tp.sweetness is not None:
            descriptor = None
            if tp.sweetness == 1: descriptor = "Dry"
            elif tp.sweetness >= 4: descriptor = "Sweet"
            if descriptor:
                api_taste_profile_objects_input.append({
                    "name": "sweetness", 
                    "value": descriptor, 
                    "text": f"Sweetness: {descriptor} (Score: {tp.sweetness})", 
                    "step": float(tp.sweetness) # step is float or None
                })

        if tp.body is not None:
            descriptor = None
            if tp.body <= 2: descriptor = "Delicate"
            elif tp.body >= 4: descriptor = "Bold"
            if descriptor:
                api_taste_profile_objects_input.append({
                    "name": "body", 
                    "value": descriptor, 
                    "text": f"Body: {descriptor} (Score: {tp.body})", 
                    "step": float(tp.body)
                })

        if tp.acidity is not None:
            descriptor = None
            if tp.acidity >= 3: descriptor = "Refreshing" # Based on API error for acidity=3
            if descriptor:
                api_taste_profile_objects_input.append({
                    "name": "acidity", 
                    "value": descriptor, 
                    "text": f"Acidity: {descriptor} (Score: {tp.acidity})", 
                    "step": float(tp.acidity)
                })
        
        if tp.tannin is not None:
            descriptor = None
            if tp.tannin <=2 : descriptor = "Smooth" # Tentative mapping for low tannin
            # High tannin contributes to 'Bold', but 'Bold' is primarily from body. No direct API string for 'Tannic'.
            if descriptor:
                 api_taste_profile_objects_input.append({
                    "name": "tannin", 
                    "value": descriptor, 
                    "text": f"Tannin: {descriptor} (Score: {tp.tannin})", 
                    "step": float(tp.tannin)
                })

    # Remove duplicates that might arise if multiple characteristics map to the same descriptor (e.g. low body and low tannin both map to Smooth)
    # This is tricky because the 'name' field would make them distinct objects for VinovossFilters.
    # The API expects a flat list of strings. If VinovossFilters' serializer extracts 'value' and puts them in a list,
    # then duplicates in that final list of strings might be undesirable by the API.
    # For now, let VinovossFilters handle the list of TasteProfile objects. If the API complains about duplicate string descriptors,
    # we might need to refine this logic or how VinovossFilters serializes.
    api_filters['taste_profiles'] = api_taste_profile_objects_input if api_taste_profile_objects_input else None

    # Create VinovossFilters and SearchParams instances
    try:
        vinovoss_filters_obj = VinovossFilters(**api_filters)
    except Exception as e:
        print(f"Error creating VinovossFilters with api_filters: {api_filters}. Error: {e}")
        raise

    search_params_obj = SearchParams(
        query=query,
        filters=vinovoss_filters_obj,
        market_country=None, # Or map from existing params if available
        market_region=None,  # Or map from existing params if available
        histogram_steps=20   # Default, or map if available
    )

    # Call query_ai_service directly
    print(f"Calling query_ai_service with SearchParams: {search_params_obj}")
    results = query_ai_service(data=search_params_obj)
    
    # Convert API results to structured format
    # The 'results' from query_ai_service might already be structured if it returns dicts.
    # If query_ai_service returns a list of Pydantic models from memory_agent, they might need to be converted to dicts first.
    # Assuming 'results' is a list of dictionaries matching WineSearchResult fields.
    structured_results = []
    if not isinstance(results, list):
        print(f"Warning: query_ai_service did not return a list. Got: {type(results)}.")
        # Assuming results might be a dict with a key like 'vintages' or 'matches'
        # This part might need adjustment based on actual query_ai_service output structure
        if isinstance(results, dict):
            if 'vintages' in results and isinstance(results['vintages'], list):
                results = results['vintages']
            elif 'matches' in results and isinstance(results['matches'], list): # Another common pattern
                results = results['matches']
            # Add other potential keys if necessary
            else:
                print("Warning: query_ai_service returned a dict but no known list key found. Processing as empty.")
                results = [] 
        else:
            results = []

    for item in results: # Each 'item' is expected to be like an entry from vinovoss_sample_output.json
        if not isinstance(item, dict) or 'data' not in item or not isinstance(item['data'], dict):
            print(f"Skipping malformed item in results: {item}")
            continue
        
        data = item['data']
        
        try:
            # Populate WineShoppingPrice objects
            shopping_prices_data = data.get('shopping_prices', [])
            shopping_prices_list = []
            if isinstance(shopping_prices_data, list):
                for price_info in shopping_prices_data:
                    if isinstance(price_info, dict):
                        shopping_prices_list.append(WineShoppingPrice(
                            variant_id=price_info.get('variant_id'),
                            price_amount=price_info.get('price_amount'),
                            vintage_id=price_info.get('vintage_id'),
                            wine_id=price_info.get('wine_id'),
                            vendor_id=price_info.get('vendor_id'),
                            vendor_name=price_info.get('vendor_name')
                        ))
            
            # Populate WineImages object
            images_data = data.get('images')
            wine_images_obj = None
            if isinstance(images_data, dict):
                wine_images_obj = WineImages(
                    bottle=images_data.get('bottle'),
                    bottle_mobile=images_data.get('bottle_mobile')
                )

            # Derive price from the first shopping_prices entry if available
            derived_price = None
            if shopping_prices_list and shopping_prices_list[0].price_amount is not None:
                derived_price = shopping_prices_list[0].price_amount

            # Vintage year: handle 0 as None, otherwise use the value
            vintage_year = data.get('vintage_year')
            if vintage_year == 0:
                vintage_year = None

            structured_results.append(WineSearchResult(
                id=str(data.get('id')), # Ensure ID is a string
                title=data.get('title'),
                slug=data.get('slug'),
                wine_slug=data.get('wine_slug'),
                vintage_year=vintage_year,
                image_url=data.get('image'), # Main image URL
                images=wine_images_obj,
                user_rating=data.get('user_rating'),
                user_rating_count=data.get('user_rating_count'),
                labels=data.get('labels', []),
                region=data.get('region'),
                country=data.get('country'),
                shopping_prices=shopping_prices_list,
                is_natural=data.get('is_natural'),
                bottle_volume=data.get('bottle_volume'),
                link_to_shop=data.get('link_to_shop'),
                
                # Legacy fields - will be None or default as per new API structure
                price=derived_price,
                color=None, # Not available in new API output structure
                type=None,  # Not available
                grapes=[],  # Not available
                taste_profile=None, # Not available, old parsing logic removed
                food_pairings=[], # Not available
                is_blended=None # Not available
            ))
        except Exception as e:
            print(f"Error processing item data: {data}. Error: {e}. Skipping this item.")
            # import traceback; traceback.print_exc() # For debugging
            continue
            
    return structured_results
