from typing import Dict, List, Tuple, Any, Optional, Union
from src.planner.conversation import format_response
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import sys
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END
from langchain.chat_models import init_chat_model
from langchain.tools import Tool
from langchain.schema import HumanMessage, AIMessage
from ..config import config
from .tools import (
    wine_search, WineColor, WineType, TasteProfile,
    WineFilters, WineSearchResult
)
from langgraph.graph import MessagesState

# Configure detailed logging
logger = logging.getLogger('wine_chatbot')
logger.setLevel(logging.DEBUG)

# Create console handler
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add handler to logger
logger.addHandler(ch)
class AgentState(Enum):
    CLARIFYING = "clarifying"
    RESEARCHING = "researching"
    RECOMMENDING = "recommending"
    SHOPPING = "shopping"
    PRESENTING = "presenting"

@dataclass
class UserPreferences:
    preferred_colors: Optional[List[WineColor]] = field(default_factory=list)
    preferred_types: Optional[List[WineType]] = field(default_factory=list)
    taste_preferences: Optional[TasteProfile] = None
    preferred_regions: Optional[List[str]] = field(default_factory=list)
    preferred_grapes: Optional[List[str]] = field(default_factory=list)

@dataclass
class UserContext:
    occasion: Optional[str] = None
    guests: Optional[int] = None
    budget: Optional[float] = None
    food_pairing: Optional[str] = None
    preferences: UserPreferences = field(default_factory=UserPreferences)
    clarification_prompt: Optional[str] = None # LLM-generated prompt if clarification is needed

@dataclass
class WineResearch:
    occasion: str
    food_pairing: Optional[str]
    preferences: Optional[UserPreferences]
    search_results: List[WineSearchResult] = None
    filters_used: WineFilters = None

@dataclass
class WineRecommendation:
    wines: List[WineSearchResult]
    total_cost: float
    reasoning: str
    taste_analysis: Dict[str, TasteProfile] = None

@dataclass
class ShoppingItem:
    wine: WineSearchResult
    quantity: int
    subtotal: float
    availability: bool = True

@dataclass
class ShoppingList:
    items: List[ShoppingItem]
    total_bottles: int
    total_cost: float
    by_color: Dict[WineColor, int] = None
    by_type: Dict[WineType, int] = None

@dataclass
class WorkflowState:
    user_context: UserContext
    current_state: AgentState
    research_results: Optional[WineResearch] = None
    recommendations: Optional[WineRecommendation] = None
    shopping_list: Optional[ShoppingList] = None
    messages: List[Dict] = None

# Initialize model
api_key = config.get('ai', 'gemini_api_key')
print(api_key)
if not api_key:
    raise ValueError("Gemini API key not found in configuration")

model = init_chat_model(
    model="gemini-2.0-flash-lite",
    model_provider="google_genai",
    api_key=api_key,
    credentials=None
)

def extract_user_intent(messages: List[Any]) -> UserContext:
    """Extract user intent and dynamically generate wine preferences using LLM.
    
    Args:
        messages: List of conversation messages (can be HumanMessage, AIMessage, or dict objects)
        
    Returns:
        UserContext with extracted information
    """
    context = UserContext()
    
    # Format the conversation history for the prompt
    conversation_text = ""
    for msg in messages:
        if isinstance(msg, HumanMessage) or (isinstance(msg, dict) and msg.get('role') == 'user'):
            content = msg.content if hasattr(msg, 'content') else msg.get('content')
            conversation_text += f"User: {content}\n"
        elif isinstance(msg, AIMessage) or (isinstance(msg, dict) and msg.get('role') == 'assistant'):
            content = msg.content if hasattr(msg, 'content') else msg.get('content')
            conversation_text += f"Assistant: {content}\n"
    
    # Get the last user message for logging
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) or (isinstance(msg, dict) and msg.get('role') == 'user'):
            content = msg.content if hasattr(msg, 'content') else msg.get('content')
            last_user_message = content
            break

    prompt_template = f"""
You are an expert wine assistant. Here is the conversation history with a user:

{conversation_text}

Analyze this conversation and extract the following information, focusing on the latest user request. 
Respond with a single, valid JSON object containing these fields. 
If a field cannot be determined, use null or an empty list as appropriate.

Fields to extract:
- occasion: string (e.g., "wedding", "casual dinner", "celebration")
- guests: integer (number of guests)
- budget: float (total budget for wines, if mentioned)
- food_pairing: string (e.g., "steak", "seafood", "spicy thai")
- preferred_colors: list of strings (e.g., ["RED", "WHITE", "ROSE"], must be one of WineColor enum: RED, WHITE, ROSE). Infer this based on food or occasion if not explicit.
- preferred_types: list of strings (e.g., ["STILL", "SPARKLING", "DESSERT", "FORTIFIED"], must be one of WineType enum: STILL, SPARKLING, DESSERT, FORTIFIED). Infer this if possible.
- taste_preferences: object with keys "body", "acidity", "sweetness", "tannin" (each an integer from 1-5, where 1 is low/light and 5 is high/full). If not specified, use null for the object or individual keys. Infer this if possible.
- preferred_regions: list of strings (e.g., ["Napa Valley", "Bordeaux"])
- preferred_grapes: list of strings (e.g., ["Cabernet Sauvignon", "Chardonnay"]). Infer these based on food, occasion, or stated preferences.
- clarification_prompt_to_user: string (A polite question to the user if essential information like occasion, guest count, or budget is missing or ambiguous, e.g., "To help you better, could you please tell me about the occasion and number of guests?"). If no clarification is needed, set to null.

Example JSON output:
{{ "occasion": "dinner party", "guests": 6, "budget": 100.0, "food_pairing": "pasta with red sauce", "preferred_colors": ["RED"], "preferred_types": ["STILL"], "taste_preferences": {{ "body": 4, "acidity": 3, "sweetness": 1, "tannin": 4 }}, "preferred_regions": ["Tuscany"], "preferred_grapes": ["Sangiovese"], "clarification_prompt_to_user": null }}
"""

    try:
        response = model.invoke(prompt_template)
        # Assuming response.content is the string containing JSON
        # Sometimes, LLMs wrap JSON in ```json ... ```, so we try to strip that.
        raw_json = response.content
        if raw_json.startswith("```json\n"):
            raw_json = raw_json[len("```json\n"):-len("\n```")]
        elif raw_json.startswith("```"):
             raw_json = raw_json[len("```"):-len("```")]
        
        parsed_data = json.loads(raw_json)

        context.occasion = parsed_data.get('occasion')
        context.guests = parsed_data.get('guests')
        context.budget = parsed_data.get('budget')
        context.food_pairing = parsed_data.get('food_pairing')
        context.clarification_prompt = parsed_data.get('clarification_prompt_to_user')

        # Populate UserPreferences
        if parsed_data.get('preferred_colors'):
            for color_str in parsed_data['preferred_colors']:
                try:
                    context.preferences.preferred_colors.append(WineColor[color_str.upper()])
                except KeyError:
                    print(f"Warning: LLM returned invalid wine color: {color_str}") # Or log
        
        if parsed_data.get('preferred_types'):
            for type_str in parsed_data['preferred_types']:
                try:
                    context.preferences.preferred_types.append(WineType[type_str.upper()])
                except KeyError:
                    print(f"Warning: LLM returned invalid wine type: {type_str}") # Or log

        if parsed_data.get('preferred_regions'):
            context.preferences.preferred_regions = parsed_data['preferred_regions']
        
        if parsed_data.get('preferred_grapes'):
            context.preferences.preferred_grapes = parsed_data['preferred_grapes']

        taste_data = parsed_data.get('taste_preferences')
        if taste_data:
            context.preferences.taste_preferences = TasteProfile(
                body=taste_data.get('body'),
                acidity=taste_data.get('acidity'),
                sweetness=taste_data.get('sweetness'),
                tannin=taste_data.get('tannin')
            )

    except json.JSONDecodeError as e:
        print(f"Error decoding LLM JSON response: {e}")
        print(f"Raw response: {response.content if 'response' in locals() else 'Response not available'}")
        context.clarification_prompt = "I had a little trouble understanding your request. Could you please rephrase or provide more details?"
    except Exception as e:
        print(f"An unexpected error occurred in extract_user_intent: {e}")
        context.clarification_prompt = "I encountered an issue processing your request. Could you try again?"

    return context

def clarify_requirements(context: UserContext) -> str:
    """Return the clarification prompt generated by the LLM, or a fallback."""
    if context.clarification_prompt:
        return context.clarification_prompt
    # This fallback should ideally not be reached if LLM always provides a prompt when needed.
    return "I need a bit more information to proceed. Could you please tell me more about your needs?"

def research_wine(
    occasion: str,
    food_pairing: Optional[str] = None,
    preferences: Optional[UserPreferences] = None
) -> WineResearch:
    """Conducts deep research on wines based on occasion and preferences."""
    # Create filters from preferences
    filters = WineFilters(
        wine_colors=preferences.preferred_colors if preferences else None,
        wine_types=preferences.preferred_types if preferences else None,
        grapes=preferences.preferred_grapes if preferences else None,
        regions=preferences.preferred_regions if preferences else None,
        taste_profile=preferences.taste_preferences if preferences else None
    )
    
    # Perform search with structured data
    search_results = wine_search(
        occasion=occasion,
        food_pairing=food_pairing,
        preferences={
            'taste_profile': filters.taste_profile._asdict() if filters.taste_profile else None,
            'regions': filters.regions,
            'grapes': filters.grapes
        } if preferences else None
    )
    
    return WineResearch(
        occasion=occasion,
        food_pairing=food_pairing,
        preferences=preferences,
        search_results=search_results,
        filters_used=filters
    )

def recommend_wine(research: WineResearch, budget: float) -> WineRecommendation:
    """Analyzes research results and provides wine recommendations within budget."""
    recommendations = []
    total_cost = 0.0
    taste_analysis = {}
    
    # Filter and rank wines based on research results
    if research.search_results:
        # Sort by rating first
        sorted_wines = sorted(research.search_results, key=lambda x: x.rating, reverse=True)
        
        for wine in sorted_wines:
            if total_cost + wine.price <= budget:
                recommendations.append(wine)
                total_cost += wine.price
                
                # Analyze taste profile
                taste_analysis[wine.name] = wine.taste_profile
        
        # Build detailed reasoning
        reasoning_parts = [f"Selected {len(recommendations)} wines optimized for {research.occasion}"]
        
        if research.food_pairing:
            reasoning_parts.append(f"paired with {research.food_pairing}")
        
        if research.preferences:
            if research.preferences.preferred_colors:
                colors = [c.value for c in research.preferences.preferred_colors]
                reasoning_parts.append(f"matching preferred colors: {', '.join(colors)}")
            
            if research.preferences.preferred_types:
                types = [t.value for t in research.preferences.preferred_types]
                reasoning_parts.append(f"matching types: {', '.join(types)}")
        
        reasoning = ", ".join(reasoning_parts)
    else:
        reasoning = "No wines found matching the criteria"
    
    return WineRecommendation(
        wines=recommendations,
        total_cost=total_cost,
        reasoning=reasoning,
        taste_analysis=taste_analysis
    )

def create_shopping_list(recommendation: WineRecommendation, guests: int, user_preferences: UserPreferences) -> ShoppingList:
    """Creates a detailed shopping list with quantities based on guest count."""
    # Calculate bottles needed (0.5 bottles per guest is standard)
    bottles_per_person = 0.5
    total_bottles = int(guests * bottles_per_person)
    
    # Distribute bottles across recommended wines
    items = []
    bottles_per_wine = total_bottles // len(recommendation.wines)
    remaining_bottles = total_bottles % len(recommendation.wines)
    
    # Track bottles by color and type based on user preferences
    by_color = {color: 0 for color in user_preferences.preferred_colors} if user_preferences.preferred_colors else {}
    by_type = {ptype: 0 for ptype in user_preferences.preferred_types} if user_preferences.preferred_types else {}
    
    for wine in recommendation.wines:
        quantity = bottles_per_wine + (1 if remaining_bottles > 0 else 0)
        remaining_bottles -= 1
        
        # Create shopping item
        item = ShoppingItem(
            wine=wine,
            quantity=quantity,
            subtotal=(wine.price * quantity) if wine.price is not None else 0.0,
            availability=True  # Mock availability for now
        )
        items.append(item)
        
        # Update color and type counts if the wine's color/type matches user preference
        if wine.color and wine.color in by_color:
            by_color[wine.color] += quantity
        if wine.type and wine.type in by_type:
            by_type[wine.type] += quantity
    
    # Categories with 0 count are intentionally kept to reflect user preferences

    return ShoppingList(
        items=items,
        total_bottles=total_bottles,
        total_cost=sum(item.subtotal for item in items),
        by_color=by_color,
        by_type=by_type
    )

# Create tools
research_tool = Tool(
    name="research_wine",
    func=research_wine,
    description="Research wines based on occasion, food pairing, and preferences"
)

recommend_tool = Tool(
    name="recommend_wine",
    func=recommend_wine,
    description="Analyze research and recommend wines within budget"
)

shopping_tool = Tool(
    name="create_shopping_list",
    func=create_shopping_list,
    description="Create shopping list with quantities based on recommendations"
)

# Create a function to handle user input and ensure state is properly updated
def user_interaction_node(state):
    """Entry point node that ensures state is properly updated."""
    logger.debug(f"user_interaction_node called with state keys: {state.keys()}")
    
    # Initialize workflow if not present
    if 'workflow' not in state or not state['workflow']:
        workflow = WorkflowState(
            user_context=UserContext(),
            current_state=AgentState.CLARIFYING,
            messages=[]
        )
    else:
        workflow = state['workflow']
    
    # Get the latest user message
    user_message = None
    if 'messages' in state and state['messages']:
        for msg in reversed(state['messages']):
            if isinstance(msg, HumanMessage):
                user_message = msg.content
                logger.debug(f"Found user message: {user_message}")
                break
    
    if not user_message:
        logger.warning("No user message found in state")
        # Return a default greeting if no message
        return {
            "workflow": workflow,
            "messages": AIMessage(content="Hello! How can I help you plan your wine selection today?")
        }
    
    # Use the model to process the user message
    try:
        logger.info(f"Processing user message: {user_message}")
        # Call the model with the user message
        response = model.invoke([HumanMessage(content=user_message)])
        logger.debug(f"Model response: {response.content}")
        
        # Update the state with the response
        return {
            "workflow": workflow,
            "messages": AIMessage(content=response.content)
        }
    except Exception as e:
        logger.error(f"Error in user_interaction_node: {str(e)}", exc_info=True)
        return {
            "workflow": workflow,
            "messages": AIMessage(content=f"I'm sorry, I encountered an error: {str(e)}")
        }

# Create agents with tools
user_interaction_agent = user_interaction_node

research_agent = create_react_agent(
    model=model,
    tools=[research_tool],
    name="research_agent"
)

recommendation_agent = create_react_agent(
    model=model,
    tools=[recommend_tool],
    name="recommendation_agent"
)

shopping_agent = create_react_agent(
    model=model,
    tools=[shopping_tool],
    name="shopping_agent"
)

def format_wine_details(wine: WineSearchResult) -> str:
    """Format wine details for user presentation."""
    details = [f"🍷 {wine.title or 'Unknown Wine'}"]
    if wine.vintage_year:
        details.append(f"Vintage: {wine.vintage_year}")
    
    details.append(f"Type: {wine.type.value if wine.type else 'N/A'}")
    details.append(f"Region: {wine.region or 'N/A'}{f', {wine.country}' if wine.country else ''}")
    details.append(f"Price: ${wine.price:.2f}" if wine.price is not None else "Price: N/A")
    
    rating_str = "Rating: N/A"
    if wine.user_rating is not None:
        rating_str = f"Rating: {wine.user_rating}/5"
        if wine.user_rating_count is not None:
            rating_str += f" ({wine.user_rating_count} ratings)"
    details.append(rating_str)

    if wine.taste_profile:
        details.extend([
            "Taste Profile:",
            f"  - Body: {wine.taste_profile.body}/5" if wine.taste_profile.body is not None else "  - Body: N/A",
            f"  - Sweetness: {wine.taste_profile.sweetness}/5" if wine.taste_profile.sweetness is not None else "  - Sweetness: N/A",
            f"  - Acidity: {wine.taste_profile.acidity}/5" if wine.taste_profile.acidity is not None else "  - Acidity: N/A",
            f"  - Tannin: {wine.taste_profile.tannin}/5" if wine.taste_profile.tannin is not None else "  - Tannin: N/A"
        ])
    else:
        details.append("Taste Profile: N/A")
    
    if wine.image_url:
        details.append(f"Image: {wine.image_url}")
    if wine.labels:
        details.append(f"Labels: {', '.join(wine.labels)}")

    return "\n".join(details)

def format_shopping_list(shopping_list: ShoppingList) -> str:
    """Format shopping list for user presentation."""
    sections = [
        "🛒 Shopping List:",
        "-" * 40,
        "Wines:"
    ]
    
    for item in shopping_list.items:
        item_details = f"- {item.wine.title or 'Unknown Wine'}: {item.quantity} bottle(s) at ${item.subtotal:.2f}"
        if not item.availability:
            item_details += " (Note: May have limited availability)"
        sections.append(item_details)
    
    sections.extend([
        "-" * 40,
        f"Total Bottles: {shopping_list.total_bottles}",
        f"Total Cost: ${shopping_list.total_cost:.2f}",
        "",
        "Distribution:",
        "By Color: " + ", ".join(f"{color.value}: {count}" for color, count in shopping_list.by_color.items()),
        "By Type: " + ", ".join(f"{type.value}: {count}" for type, count in shopping_list.by_type.items())
    ])
    
    return "\n".join(sections)

def handle_user_interaction(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user interaction, call LLM to extract intent and preferences, and determine next state.
    
    This function works with the MessagesState which already has a 'messages' field.
    """
    logger.debug(f"handle_user_interaction called with state keys: {state.keys()}")
    
    # Initialize workflow if it doesn't exist
    if 'workflow' not in state or not state['workflow']:
        logger.info("Initializing new workflow state")
        state['workflow'] = WorkflowState(
            user_context=UserContext(),
            current_state=AgentState.CLARIFYING,
            messages=[]
        )
    
    workflow = state['workflow']
    user_message = None

    # Log the messages in the state
    if 'messages' in state:
        logger.debug(f"Messages in state: {len(state['messages'])}")
        for i, msg in enumerate(state['messages']):
            if isinstance(msg, HumanMessage):
                logger.debug(f"Message {i}: HumanMessage with content: {msg.content}")
            elif isinstance(msg, AIMessage):
                logger.debug(f"Message {i}: AIMessage with content: {msg.content}")
            elif isinstance(msg, dict):
                logger.debug(f"Message {i}: Dict with role: {msg.get('role')}, content: {msg.get('content')}")
            else:
                logger.debug(f"Message {i}: Unknown type {type(msg)}: {msg}")
    else:
        logger.warning("No messages key in state")

    # Check if we have messages in the state
    has_user_message = False
    if 'messages' in state and state['messages']:
        # Check if there's at least one user message
        for msg in state['messages']:
            if isinstance(msg, HumanMessage) or (isinstance(msg, dict) and msg.get('role') == 'user'):
                has_user_message = True
                break
        
        if has_user_message:
            # Pass the entire conversation history to extract user intent
            logger.info(f"Extracting user intent from conversation history with {len(state['messages'])} messages")
            workflow.user_context = extract_user_intent(state['messages'])
        else:
            logger.warning("No user message found in messages list")
            # Initialize with default greeting
            if not workflow.user_context or not workflow.user_context.occasion:
                if not workflow.user_context:
                    workflow.user_context = UserContext()
                workflow.user_context.clarification_prompt = "Hello! How can I help you plan your wine selection today?"
                logger.info("Set default greeting prompt")
    else:
        logger.warning("No messages found in state")
        # Initialize with default greeting
        if not workflow.user_context:
            workflow.user_context = UserContext()
        workflow.user_context.clarification_prompt = "Hello! How can I help you plan your wine selection today?"
        logger.info("Set default greeting prompt")

    # Decide the next step based on the user_context
    if workflow.user_context and workflow.user_context.clarification_prompt:
        clarification_message = clarify_requirements(workflow.user_context)
        logger.info(f"Generated clarification message: {clarification_message}")
        
        # Add the assistant's clarification message to the state
        # MessagesState will handle the message list properly
        response = {
            "workflow": workflow,
            "messages": AIMessage(content=clarification_message)
        }
        logger.debug(f"Returning response with AIMessage: {clarification_message}")
        return response
    elif workflow.user_context and workflow.user_context.occasion:
        # No clarification needed, and we have an occasion, proceed to research
        workflow.current_state = AgentState.RESEARCHING
        logger.info(f"Proceeding to research with occasion: {workflow.user_context.occasion}")
        return {"workflow": workflow}
    else:
        # Not enough information to proceed
        if not workflow.user_context:
            workflow.user_context = UserContext()
        workflow.user_context.clarification_prompt = "I need a bit more information to help you. What is the occasion?"
        clarification_message = clarify_requirements(workflow.user_context)
        logger.info(f"Generated default clarification message: {clarification_message}")
        
        # Add the assistant's clarification message to the state
        workflow.current_state = AgentState.CLARIFYING
        response = {
            "workflow": workflow,
            "messages": AIMessage(content=clarification_message)
        }
        logger.debug(f"Returning response with AIMessage: {clarification_message}")
        return response

def handle_research(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle wine research phase.
    
    Works with MessagesState to properly handle messages.
    """
    workflow = state['workflow']
    
    # Ensure we have a user context
    if not workflow.user_context:
        # This is an error state - we shouldn't reach research without user context
        print("Error: Reached research phase without user context")
        workflow.current_state = AgentState.CLARIFYING
        workflow.user_context = UserContext()
        workflow.user_context.clarification_prompt = "I need to know what occasion you're planning for."
        return {
            "workflow": workflow,
            "messages": AIMessage(content="I need to know what occasion you're planning for.")
        }
    
    # Create a research object
    research = WineResearch(
        occasion=workflow.user_context.occasion,
        food_pairing=workflow.user_context.food_pairing,
        preferences=workflow.user_context.preferences
    )
    
    # Call the research tool
    try:
        research_results = research_agent.invoke({
            "input": f"Research wines for {research.occasion}" + 
                     (f" paired with {research.food_pairing}" if research.food_pairing else "")
        })
        
        # Store the research results
        workflow.research_results = research_results
        
        # Add research summary to conversation using MessagesState
        research_message = f"I've researched wines for {research.occasion}. Found {len(research_results)} options."
        
    except Exception as e:
        print(f"Error during research: {e}")
        research_message = "I'm having trouble researching wines right now. Let's try a different approach."
    
    # Update workflow state
    workflow.current_state = AgentState.RECOMMENDING
    return {
        "workflow": workflow,
        "messages": AIMessage(content=research_message)
    }

def handle_recommendations(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle wine recommendations phase.
    
    Works with MessagesState to properly handle messages.
    """
    workflow = state['workflow']
    
    # Generate recommendations
    try:
        # Call the recommendation agent
        recommendation_result = recommendation_agent.invoke({
            "input": f"Recommend wines for {workflow.user_context.occasion} with budget ${workflow.user_context.budget}"
        })
        
        # Store the recommendations
        workflow.recommendations = recommendation_result
        
        # Format recommendation message
        if workflow.recommendations and workflow.recommendations.wines:
            message = [
                "🎯 Wine Recommendations:",
                workflow.recommendations.reasoning,
                "",
                "Selected Wines:"
            ]
            
            for wine in workflow.recommendations.wines:
                message.append("\n" + format_wine_details(wine))
                
            if workflow.recommendations.taste_analysis:
                message.extend([
                    "",
                    "Taste Profile Analysis:",
                    *[f"{name}: Body {profile.body}/5, Acidity {profile.acidity}/5"
                      for name, profile in workflow.recommendations.taste_analysis.items()]
                ])
            
            recommendation_message = "\n".join(message)
        else:
            recommendation_message = "I couldn't find suitable wine recommendations based on your criteria. Let's try a different approach."
    except Exception as e:
        print(f"Error during recommendations: {e}")
        recommendation_message = "I'm having trouble generating wine recommendations right now. Let's try a different approach."
    
    # Update workflow state
    workflow.current_state = AgentState.SHOPPING
    
    # Return the updated state with the message using MessagesState
    return {
        "workflow": workflow,
        "messages": AIMessage(content=recommendation_message)
    }

def handle_shopping(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle shopping list creation phase.
    
    Works with MessagesState to properly handle messages.
    """
    workflow = state['workflow']
    
    try:
        # Call the shopping agent
        shopping_result = shopping_agent.invoke({
            "input": f"Create shopping list for {workflow.user_context.guests} guests with recommendations"
        })
        
        # Store the shopping list
        workflow.shopping_list = shopping_result
        
        # Format and add shopping list to messages
        if workflow.shopping_list:
            # Format the shopping list
            shopping_list_text = format_shopping_list(workflow.shopping_list)
            
            # Add summary and tips
            tips = [
                "",
                "🔍 Shopping Tips:",
                f"- Plan to buy {workflow.shopping_list.total_bottles} bottles total",
                f"- Budget per bottle: ${workflow.user_context.budget / workflow.shopping_list.total_bottles:.2f}",
                "- Consider buying a few extra bottles as backup",
                "- Store white wines chilled (45-50°F)",
                "- Let red wines breathe before serving"
            ]
            
            # Combine the shopping list and tips
            shopping_message = shopping_list_text + "\n" + "\n".join(tips)
        else:
            shopping_message = "I couldn't create a shopping list based on your preferences. Please provide more details about your event."
    except Exception as e:
        print(f"Error during shopping list creation: {e}")
        shopping_message = "I'm having trouble creating a shopping list right now. Let's try a different approach."
    
    # Update workflow state
    workflow.current_state = AgentState.PRESENTING
    
    # Return the updated state with the message using MessagesState
    return {
        "workflow": workflow,
        "messages": AIMessage(content=shopping_message)
    }

def route_after_interaction(state: Dict[str, Any]) -> str:
    """Determines the next step after user interaction handling based on the current agent state.
    
    This function routes the workflow based on the current state in the WorkflowState object.
    """
    # Get the workflow state from the graph state
    workflow = state.get('workflow')
    logger.debug(f"Routing after interaction with workflow: {workflow}")
    
    # Safety check to ensure we have a valid workflow state
    if not workflow or not hasattr(workflow, 'current_state'):
        logger.error("WorkflowState or current_state not found in graph state for routing.")
        return END  # Safety end if we can't determine the state

    # Get the current agent state
    current_agent_state = workflow.current_state
    logger.debug(f"Current agent state for routing: {current_agent_state}")
    
    # Check if we have a messages field in the state that was just returned from handle_user_interaction
    # If we do, it means we need to return this response to the user before continuing
    if 'messages' in state and isinstance(state['messages'], AIMessage):
        logger.info("Found AIMessage in state, ending graph to return response to user")
        return END
    
    # Route based on the current state
    if current_agent_state == AgentState.CLARIFYING:
        # We've already sent a clarification message, so end the graph
        # The next user input will start a new graph execution
        logger.info("In CLARIFYING state, ending graph to await user response")
        return END
    elif current_agent_state == AgentState.RESEARCHING:
        # Proceed to research
        logger.info("Proceeding to research")
        return "research"
    elif current_agent_state == AgentState.RECOMMENDING:
        # Proceed to recommendations
        logger.info("Proceeding to recommendations")
        return "recommend"
    elif current_agent_state == AgentState.SHOPPING:
        # Proceed to shopping
        logger.info("Proceeding to shopping")
        return "shopping"
    elif current_agent_state == AgentState.PRESENTING:
        # End the graph when we're done presenting
        logger.info("In PRESENTING state, ending graph")
        return END
    else:
        logger.error(f"Unexpected agent state {current_agent_state} in route_after_interaction. Ending graph.")
        return END

def create_wine_planner() -> StateGraph:
    """Create a wine planner graph with proper message handling.
    
    Uses MessagesState to handle conversation history and additional fields for workflow state.
    """
    logger.info("Creating wine planner graph")
    
    # Define the graph state class that extends MessagesState
    class GraphState(MessagesState):
        """State for the wine planner graph with conversation memory.
        
        Extends MessagesState which already has a 'messages' field that is a list of messages.
        Additional fields store the workflow state and results.
        """
        workflow: WorkflowState = None
        user_context: UserContext = None
        research_results: List[WineSearchResult] = field(default_factory=list)
        recommendation: Optional[WineRecommendation] = None
        shopping_list: Optional[ShoppingList] = None
    
    # Create the graph with the GraphState schema
    workflow = StateGraph(GraphState)
    logger.debug("Created StateGraph with GraphState schema")
    
    # Add user_interaction_node directly as a node
    # This ensures proper state updates at the entry point
    workflow.add_node("user_interaction", user_interaction_node)
    logger.debug("Added user_interaction_node")
    
    # Add other agent nodes
    workflow.add_node("research", research_agent)
    workflow.add_node("recommend", recommendation_agent)
    workflow.add_node("shopping", shopping_agent)
    
    # Add nodes for state handlers
    workflow.add_node("handle_user_interaction", handle_user_interaction)
    workflow.add_node("handle_research", handle_research)
    workflow.add_node("handle_recommendations", handle_recommendations)
    workflow.add_node("handle_shopping", handle_shopping)
    logger.debug("Added all handler nodes")
    
    # Define the main flow edges
    workflow.add_edge("user_interaction", "handle_user_interaction")
    
    # Conditional edge after handling user interaction
    workflow.add_conditional_edges(
        "handle_user_interaction",
        route_after_interaction,
        {
            "user_interaction": "user_interaction",  # Loop back for clarification
            "research": "research",                # Proceed to research
            "recommend": "recommend",              # Proceed to recommendations
            "shopping": "shopping",                # Proceed to shopping
            END: END                              # End if presenting or error
        }
    )
    logger.debug("Added conditional edges for routing")
    
    # Define remaining edges
    workflow.add_edge("research", "handle_research")
    workflow.add_edge("handle_research", "recommend")
    workflow.add_edge("recommend", "handle_recommendations")
    workflow.add_edge("handle_recommendations", "shopping")
    workflow.add_edge("shopping", "handle_shopping")
    workflow.add_edge("handle_shopping", END)
    logger.debug("Added all remaining edges")
    
    # Set entry point
    workflow.set_entry_point("user_interaction")
    logger.info("Set entry point to user_interaction")
    
    # Add memory to persist conversation between runs
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    logger.debug("Created MemorySaver for conversation persistence")
    
    # Compile and return the workflow
    logger.info("Compiling workflow")
    return workflow.compile(checkpointer=memory)

# Create the planner
_wine_planner = create_wine_planner()

# Wrap the planner to include conversation history in the response
def wine_planner(inputs, config=None):
    """Wine planner with conversation history.
    
    Args:
        inputs: Input to the planner, including messages
        config: Optional configuration dictionary with thread_id
        
    Returns:
        Dictionary with response and conversation history
    """
    logger.info("=== wine_planner called ===")
    logger.debug(f"Input keys: {inputs.keys() if isinstance(inputs, dict) else 'inputs is not a dict'}")
    
    # Initialize messages list
    messages = []
    
    # Process the input messages to ensure we have a clean conversation history
    if isinstance(inputs, dict) and 'messages' in inputs:
        # Use the full conversation history
        messages = inputs['messages']
        
        # Find the last user message for logging
        last_user_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) or (isinstance(msg, dict) and msg.get('role') == 'user'):
                content = msg.content if hasattr(msg, 'content') else msg.get('content')
                last_user_message = content
                break
        
        if last_user_message:
            logger.info(f"Processing user message: {last_user_message}")
        else:
            logger.warning("No user message found in inputs")
            return {
                "response": "I'm sorry, I couldn't find a user message to process.",
                "conversation_history": inputs.get('messages', [])
            }
    else:
        logger.warning("No 'messages' key in inputs")
        return {
            "response": "I'm sorry, I couldn't find any messages to process.",
            "conversation_history": []
        }
    
    # Ensure we have a valid config with thread_id
    if config is None:
        config = {"configurable": {"thread_id": "default"}}
    logger.debug(f"Using config: {config}")
    
    try:
        # Pass the full conversation history to the workflow
        input_with_history = {"messages": messages}
        
        # Invoke the planner with the full conversation history and config
        logger.info(f"Invoking LangGraph workflow with {len(messages)} messages in history")
        result = _wine_planner.invoke(input_with_history, config)
        logger.debug(f"Result keys: {result.keys() if isinstance(result, dict) else 'result is not a dict'}")
        
        # Extract the AI response
        ai_response = None
        logger.debug(f"Extracting AI response from result with keys: {result.keys()}")
        
        # PRIORITY 1: Check if there's a clarification prompt in the workflow state
        # This is the most specific and relevant response
        if 'workflow' in result:
            workflow = result['workflow']
            if hasattr(workflow, 'user_context') and workflow.user_context and workflow.user_context.clarification_prompt:
                logger.debug(f"Found clarification prompt in workflow: {workflow.user_context.clarification_prompt}")
                ai_response = workflow.user_context.clarification_prompt
        
        # PRIORITY 2: Check if there's a direct AIMessage in the result
        if not ai_response and 'messages' in result:
            if isinstance(result['messages'], AIMessage):
                logger.debug(f"Found AIMessage directly in result['messages']: {result['messages'].content}")
                ai_response = result['messages'].content
        
        # PRIORITY 3: If we have a list of messages, find the LAST AI message (most recent)
        if not ai_response and 'messages' in result and isinstance(result['messages'], list) and result['messages']:
            logger.debug(f"Searching for most recent AI message in list of {len(result['messages'])} messages")
            # Look through the messages in REVERSE order to find the most recent AI message
            for msg in reversed(result['messages']):
                if isinstance(msg, AIMessage):
                    logger.debug(f"Found most recent AIMessage: {msg.content}")
                    ai_response = msg.content
                    break
        
        # If we still don't have a response, create a fallback
        if not ai_response:
            logger.warning("Could not find AI response in result, using fallback")
            ai_response = "I'm a wine assistant ready to help you find the perfect wine. Could you tell me more about what you're looking for?"
        
        # Update the conversation history with the new exchange
        updated_history = inputs.get('messages', []).copy()
        updated_history.append(AIMessage(content=ai_response))
        
        # Return the formatted response
        return {
            "response": ai_response,
            "conversation_history": updated_history
        }
    except Exception as e:
        logger.error(f"Error in wine_planner: {str(e)}", exc_info=True)
        # Return a fallback response
        return {
            "response": f"I'm sorry, I encountered an error: {str(e)}",
            "conversation_history": inputs.get('messages', []) if isinstance(inputs, dict) else []
        }
