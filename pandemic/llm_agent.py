import os
from openai import OpenAI
from game_state import GameState
from models import DiseaseColor, DiseaseStatus, PlayerRole, City, Player, EventCard
import json
import time
import random

# Initialize OpenAI client using Gemini API (adapter mode)
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

class LLMAgent:
    def __init__(self, player, model: str = "gemini-2.0-flash-lite"):
        self.player = player
        self.model = model
        self.conversation_history = []
        self.retry_count = 0
        self.max_retries = 3
    
    def get_action(self, game_state: GameState) -> dict:
        """Use LLM to determine the next action for this player using tools API"""
        if self.player != game_state.get_current_player():
            return {"action_type": "skip", "reason": "Not my turn"}
        
        # Reset retry count for each new action request
        self.retry_count = 0
        
        # Check for unread messages
        unread_messages = self.player.messages
        message_summary = ""
        if unread_messages:
            message_summary = "\n\n📬 You have received the following messages:\n"
            for i, msg in enumerate(unread_messages):
                message_summary += f"{i+1}. From {msg['sender']}: \"{msg['content']}\"\n"
            
            # Clear messages after reading
            self.player.messages = []
        
        # Try using the tool-based approach (more structured)
        tools = self._get_pandemic_tools()
        return self._try_tool_based_approach(tools, game_state, message_summary)
    
    def _get_pandemic_tools(self):
        """Define the tools available to the LLM for Pandemic game actions"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "move",
                    "description": "Move your pawn to an adjacent city or use special movement",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {
                                "type": "string",
                                "description": "Name of the city to move to"
                            },
                            "movement_type": {
                                "type": "string",
                                "enum": ["regular", "direct_flight", "charter_flight", "shuttle_flight", "operations_expert"],
                                "description": "Type of movement to use"
                            }
                        },
                        "required": ["destination", "movement_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "treat_disease",
                    "description": "Remove disease cubes from your current city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "disease_color": {
                                "type": "string",
                                "enum": ["Blue", "Yellow", "Black", "Red"],
                                "description": "Color of the disease to treat"
                            }
                        },
                        "required": ["disease_color"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "build_research_station",
                    "description": "Build a research station in your current city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "use_operations_expert": {
                                "type": "boolean",
                                "description": "Whether to use the Operations Expert ability (no card needed)"
                            }
                        },
                        "required": ["use_operations_expert"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "share_knowledge",
                    "description": "Give or take a city card to/from another player in the same city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "card_name": {
                                "type": "string",
                                "description": "Name of the city card to share"
                            },
                            "player_name": {
                                "type": "string",
                                "description": "Name of the player to share with"
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["give", "take"],
                                "description": "Whether to give or take the card"
                            }
                        },
                        "required": ["card_name", "player_name", "direction"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "discover_cure",
                    "description": "Discover a cure for a disease at a research station",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "disease_color": {
                                "type": "string",
                                "enum": ["Blue", "Yellow", "Black", "Red"],
                                "description": "Color of the disease to cure"
                            },
                            "card_names": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "List of city card names to use (5 cards, or 4 if Scientist)"
                            }
                        },
                        "required": ["disease_color", "card_names"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "play_event",
                    "description": "Play an event card from your hand",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_name": {
                                "type": "string",
                                "enum": ["Airlift", "Government Grant", "Forecast", "Resilient Population", "One Quiet Night"],
                                "description": "Name of the event card to play"
                            },
                            "target_city": {
                                "type": "string",
                                "description": "City name for events that require a target city"
                            },
                            "target_player": {
                                "type": "string",
                                "description": "Player name for events that require a target player"
                            },
                            "additional_args": {
                                "type": "object",
                                "description": "Additional arguments specific to the event card"
                            }
                        },
                        "required": ["event_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "pass_turn",
                    "description": "Pass your turn without taking any action",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Reason for passing"
                            }
                        },
                        "required": ["reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "communicate",
                    "description": "Send a message to other players in your city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Message to send"
                            },
                            "target_player": {
                                "type": "string",
                                "description": "Name of the player to send the message to, or 'all' for all players in the same city"
                            }
                        },
                        "required": ["message", "target_player"]
                    }
                }
            }
        ]
    
    def _try_tool_based_approach(self, tools, game_state, message_summary=""):
        """Use the LLM with defined tools to generate an action"""
        # Create prompt with game state
        system_prompt = f"""You are an AI agent playing the Pandemic board game as {self.player.name} with the role {self.player.role.value}.

YOU MUST analyze the game state carefully and make the best strategic decision. Focus on:
1. Treating diseases in highly infected areas
2. Building research stations strategically
3. Collecting city cards of the same color for discovering cures
4. Coordinating with other players to share cards efficiently
5. Managing the infection and outbreak rate
6. Using your role's special abilities effectively

Only take actions that are legal in the Pandemic board game.
Do not fabricate actions or invent new mechanics.
Use an action that costs 1 action point (out of your 4 per turn).
"""

        # Create detailed game state description
        game_state_description = game_state.game_state_description()
        
        # Get current player's role and special abilities
        role_abilities = self._get_role_abilities(self.player.role)
        
        # Get description of cities connected to the player's location
        current_city = game_state.cities[self.player.location]
        connected_cities = []
        for city_name in current_city.connections:
            city = game_state.cities[city_name]
            disease_counts = [f"{color.value}: {count}" for color, count in city.disease_cubes.items() if count > 0]
            disease_info = ", ".join(disease_counts) if disease_counts else "No diseases"
            station_info = "Has research station" if city.has_research_station else "No research station"
            connected_cities.append(f"{city_name} ({city.color.value}) - {disease_info} - {station_info}")
        
        connected_cities_desc = "\n".join(connected_cities)
        
        # Create a list of players in the same city
        players_in_same_city = [p for p in game_state.players if p.location == self.player.location and p != self.player]
        players_desc = ""
        if players_in_same_city:
            players_desc = "Players in your city:\n"
            for p in players_in_same_city:
                players_desc += f"- {p.name} ({p.role.value})\n"
        
        # Create color-coded disease status
        disease_statuses = []
        for color, status in game_state.disease_status.items():
            cubes_remaining = game_state.disease_cubes[color]
            disease_statuses.append(f"{color.value}: {status.value} (Cubes in supply: {cubes_remaining}/24)")
        
        disease_status_desc = "\n".join(disease_statuses)
        
        # Describe cities with research stations
        research_stations = [city for city in game_state.cities.values() if city.has_research_station]
        stations_desc = "Research Stations:\n"
        for city in research_stations:
            stations_desc += f"- {city.name}\n"
        
        # Create message with all this information
        user_message = f"""Current Game State:
{game_state_description}

{role_abilities}

Your current city: {current_city.name} ({current_city.color.value})
Disease cubes here: {', '.join([f"{color.value}: {count}" for color, count in current_city.disease_cubes.items() if count > 0]) or "None"}
Research station here: {"Yes" if current_city.has_research_station else "No"}

Connected cities:
{connected_cities_desc}

{players_desc}

Disease Status:
{disease_status_desc}

{stations_desc}

Cards in your hand:
{', '.join(self.player.hand) or "No cards"}

You have {self.player.action_points} action points remaining.
{message_summary}

What action would you like to take now? Choose the single best action.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Add conversation history for context (limited to last few exchanges)
        if len(self.conversation_history) > 0:
            # Insert conversation history before the current query
            for i, history_item in enumerate(self.conversation_history[-6:]):  # Last 3 exchanges (6 messages)
                messages.insert(i + 1, history_item)
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                temperature=0.2,
                max_tokens=800,
                tool_choice="auto"
            )
            
            # Save the interaction in history
            self.conversation_history.append({"role": "user", "content": user_message})
            response_message = response.choices[0].message
            self.conversation_history.append({"role": "assistant", "content": response_message.content or ""})
            
            # Check for tool calls
            if response_message.tool_calls:
                tool_call = response_message.tool_calls[0]
                action_info = json.loads(tool_call.function.arguments)
                action_info["action_type"] = tool_call.function.name
                action_info["explanation"] = response_message.content
                return action_info
            else:
                # No tool was called, manually extract action from text
                return self._get_default_action(response_message.content)
                
        except Exception as e:
            self.retry_count += 1
            if self.retry_count < self.max_retries:
                print(f"Error: {e}. Retrying... ({self.retry_count}/{self.max_retries})")
                time.sleep(1)
                return self._try_tool_based_approach(tools, game_state, message_summary)
            else:
                print(f"Failed after {self.max_retries} attempts. Error: {e}")
                return {"action_type": "pass_turn", "reason": f"Error: {str(e)}"}
    
    def _get_default_action(self, content):
        """Extract a default action from the LLM's text response"""
        action_mapping = {
            "move": ["move", "travel", "go to", "drive", "direct flight", "charter flight", "shuttle flight"],
            "treat_disease": ["treat", "cure", "remove cube", "treat disease"],
            "build_research_station": ["build", "research station", "construct"],
            "share_knowledge": ["share", "give card", "take card", "exchange"],
            "discover_cure": ["discover cure", "find cure", "develop cure", "cure disease"],
            "play_event": ["play event", "use event", "event card"],
            "communicate": ["communicate", "tell", "inform", "message", "chat"],
            "pass_turn": ["pass", "skip", "end turn"]
        }
        
        # Default to pass action if we can't determine anything
        action_type = "pass_turn"
        reason = "Unable to determine action from response"
        
        # Try to identify the action from the content
        content_lower = content.lower()
        for action, keywords in action_mapping.items():
            if any(keyword in content_lower for keyword in keywords):
                action_type = action
                reason = content
                break
        
        return {"action_type": action_type, "reason": reason}
    
    def _get_role_abilities(self, role: PlayerRole) -> str:
        """Get a description of the player's role abilities"""
        abilities = {
            PlayerRole.MEDIC: "Medic Special Abilities:\n- Remove ALL cubes of a single color when treating a disease (not just 1)\n- If a disease is cured, automatically remove cubes of that color from your city (free action)\n- These automatic removals also happen when you enter a city or when the cure is discovered",
            
            PlayerRole.SCIENTIST: "Scientist Special Abilities:\n- You only need 4 city cards of the matching color to discover a cure (instead of 5)",
            
            PlayerRole.RESEARCHER: "Researcher Special Abilities:\n- You can give ANY city card from your hand to another player in the same city as a single action\n- Normal rules apply when receiving cards from other players",
            
            PlayerRole.OPERATIONS_EXPERT: "Operations Expert Special Abilities:\n- You can build a research station in your current city without discarding a city card\n- Once per turn, you can move from a research station to any city by discarding any city card",
            
            PlayerRole.DISPATCHER: "Dispatcher Special Abilities:\n- You can move another player's pawn as if it were your own\n- You can dispatch any pawn to a city containing another pawn\n- When moving another player's pawn, use their cards for Direct and Charter flights",
            
            PlayerRole.QUARANTINE_SPECIALIST: "Quarantine Specialist Special Abilities:\n- Prevent disease cube placement and outbreaks in your current city and all connected cities",
            
            PlayerRole.CONTINGENCY_PLANNER: "Contingency Planner Special Abilities:\n- As an action, take an Event card from the discard pile and store it on your role card\n- When you play the stored Event card, remove it from the game\n- Only 1 Event card can be on your role card at a time"
        }
        
        return abilities.get(role, "No special abilities") 