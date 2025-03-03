import os
from openai import OpenAI
from game_state import GameState
from models import Location, SkillType, SystemStatus
import json
import time
import random

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

class LLMAgent:
    def __init__(self, character, model: str = "gemini-2.0-flash-lite"):
        self.character = character
        self.model = model
        self.conversation_history = []
        self.retry_count = 0
        self.max_retries = 3
        
    def get_action(self, game_state: GameState) -> dict:
        """Use LLM to determine the next action for this character using tools API"""
        if self.character != game_state.get_current_character():
            return {"action_type": "skip", "reason": "Not my turn"}
            
        # Reset retry count for each new action request
        self.retry_count = 0
        
        # Create system prompt
        system_prompt = f"""
        You are playing as {self.character.name}, the {self.character.role.value} in the cooperative board game 'The Captain Is Dead'.
        Your special ability is: {self.character.special_ability}
        
        You are currently at the {self.character.location.value}.
        
        You have the following skills:
        {', '.join([f"{skill.value}: {level}" for skill, level in self.character.skills.items()])}
        
        Your goal is to help repair the Jump Core to level 5 so the ship can escape.
        You have {self.character.action_points} action points to spend on your turn.
        
        IMPORTANT: You MUST use one of the following tools to take your action:
        
        1. move - Move to a different location on the ship
           Example: Use this tool to move to Engineering if you need to repair the Jump Core
        
        2. repair - Repair a damaged system (requires Engineering skill)
           Example: Use this tool to repair the Jump Core or other damaged systems
        
        3. use_system - Use a ship system that is online or damaged
           Example: Use this tool to activate the Shields or Sensors
        
        4. battle - Attempt to defeat a threat using tactical skills
           Example: Use this tool to battle an "Alien Boarding Party" threat
        
        5. end_turn - End your turn without taking any more actions
           Example: Use this tool when you've completed all desired actions
        
        Choose the most strategically valuable action based on your skills and the current game state.
        """
        
        # Current game state
        user_prompt = f"Current Game State:\n{game_state.game_state_description()}\n\nWhat action will you take?"
        
        # Define tools based on character skills and location
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "move",
                    "description": "Move to a different location on the ship",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {
                                "type": "string",
                                "enum": [loc.value for loc in Location],
                                "description": "The location to move to"
                            }
                        },
                        "required": ["destination"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "repair",
                    "description": "Attempt to repair a damaged system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "system": {
                                "type": "string",
                                "enum": list(game_state.systems.keys()),
                                "description": "The system to repair"
                            }
                        },
                        "required": ["system"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "use_system",
                    "description": "Use a ship system that is online or damaged",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "system": {
                                "type": "string",
                                "enum": [sys for sys, status in game_state.systems.items() 
                                        if status != SystemStatus.OFFLINE],
                                "description": "The system to use"
                            }
                        },
                        "required": ["system"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "end_turn",
                    "description": "End your turn without taking any more actions",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
        
        # Add battle option if there are active threats
        if game_state.active_threats:
            tools.append({
                "type": "function",
                "function": {
                    "name": "battle",
                    "description": "Attempt to defeat a threat using tactical skills",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "threat": {
                                "type": "string",
                                "enum": [threat.name for threat in game_state.active_threats],
                                "description": "The threat to battle"
                            }
                        },
                        "required": ["threat"]
                    }
                }
            })
        
        # Update conversation history
        self.conversation_history = []  # Reset conversation history for each new action
        self.conversation_history.append({"role": "system", "content": system_prompt})
        self.conversation_history.append({"role": "user", "content": user_prompt})
        
        # Try the tool-based approach first
        action = self._try_tool_based_approach(tools, game_state)
        if action:
            return action
            
        # If tool-based approach fails, try structured prompting
        action = self._try_structured_prompting(game_state)
        if action:
            return action
            
        # If structured prompting fails, try basic parsing
        action = self._try_basic_parsing(game_state)
        if action:
            return action
            
        # Last resort: return a default action based on character skills
        return self._get_default_action(game_state)
        
    def _try_tool_based_approach(self, tools, game_state):
        """Try to get an action using the tools API"""
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Add a small delay to avoid rate limiting
                time.sleep(0.5 + retry_count * 0.5)  # Increase delay with each retry
                
                # Add explicit instructions about tool usage
                tool_instructions = """
                IMPORTANT: You must select one of the available tools to take your action.
                Do not respond with text - you must use a tool.
                
                Available tools:
                - move: Use this to move to a different location
                - repair: Use this to repair a damaged system
                - use_system: Use this to activate a ship system
                - battle: Use this to fight a threat
                - end_turn: Use this to end your turn
                
                Select the most appropriate tool based on your character's skills and the current situation.
                """
                
                # Add tool instructions to the conversation
                self.conversation_history.append({"role": "system", "content": tool_instructions})
                
                # Get response from OpenAI with tools
                response = client.chat.completions.create(
                    model=self.model,
                    messages=self.conversation_history,
                    tools=tools,
                    tool_choice="required",  # Force the model to use a tool
                    max_tokens=250
                )
                
                # Extract the action from the response
                message = response.choices[0].message
                
                # Process the response
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # Get the first tool call (there should only be one)
                    tool_call = message.tool_calls[0]
                    
                    # Extract function name and arguments
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Add the assistant's response to conversation history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                        ]
                    })
                    
                    # Format the action for return
                    action = {
                        "action_type": function_name,
                        "parameters": function_args,
                        "reason": message.content or "Strategic decision based on current game state."
                    }
                    
                    return action
                else:
                    # If no tool was called, try again or fall back to structured prompting
                    print(f"No tool call in response for {self.character.name} (attempt {retry_count+1}/{max_retries+1}). Retrying...")
                    retry_count += 1
                    if retry_count > max_retries:
                        print(f"All tool call attempts failed for {self.character.name}. Falling back to structured prompting.")
                        return None
                    
            except Exception as e:
                # Fall back to structured prompting if tool calling fails
                print(f"Tool calling failed for {self.character.name} (attempt {retry_count+1}/{max_retries+1}): {e}")
                retry_count += 1
                if retry_count > max_retries:
                    print(f"All tool call attempts failed for {self.character.name}. Falling back to structured prompting.")
                    return None
        
        return None
            
    def _try_structured_prompting(self, game_state):
        """Try to get an action using structured prompting"""
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Add a small delay to avoid rate limiting
                time.sleep(0.5 + retry_count * 0.5)  # Increase delay with each retry
                
                # Create a structured prompt as fallback
                fallback_prompt = f"""
                You are playing as {self.character.name}, the {self.character.role.value} in 'The Captain Is Dead'.
                Your special ability is: {self.character.special_ability}
                
                You are currently at the {self.character.location.value}.
                
                You have the following skills:
                {', '.join([f"{skill.value}: {level}" for skill, level in self.character.skills.items()])}
                
                Your goal is to help repair the Jump Core to level 5 so the ship can escape.
                You have {self.character.action_points} action points to spend on your turn.
                
                Current Game State:
                {game_state.game_state_description()}
                
                AVAILABLE ACTIONS - YOU MUST CHOOSE EXACTLY ONE:
                
                1. MOVE - Move to a different location on the ship
                   Available locations: {", ".join([loc.value for loc in Location])}
                   Example: Move to Engineering to repair the Jump Core
                   
                2. REPAIR - Repair a damaged system (requires Engineering skill)
                   Available systems: {", ".join(game_state.systems.keys())}
                   Example: Repair the Jump Core or Shields
                   
                3. USE - Use a ship system that is online or damaged
                   Available systems: {", ".join([sys for sys, status in game_state.systems.items() if status != SystemStatus.OFFLINE])}
                   Example: Use Sensors to scan for threats
                """
                
                if game_state.active_threats:
                    fallback_prompt += f"""
                4. BATTLE - Attempt to defeat a threat (requires Tactical skill)
                   Active threats: {", ".join([threat.name for threat in game_state.active_threats])}
                   Example: Battle the "Alien Boarding Party" threat
                    """
                    
                fallback_prompt += """
                5. END TURN - End your turn without taking any more actions
                   Example: End your turn when you've completed all desired actions
                
                YOU MUST RESPOND WITH EXACTLY ONE ACTION IN THIS FORMAT:
                {
                    "action_type": "move",  // Choose one of: move, repair, use_system, battle, end_turn
                    "parameters": {
                        // For move: "destination": "Location Name"
                        // For repair: "system": "System Name"
                        // For use_system: "system": "System Name"
                        // For battle: "threat": "Threat Name"
                        // For end_turn: no parameters needed
                    },
                    "reason": "Brief explanation of strategic reasoning"
                }
                
                DO NOT INCLUDE ANY OTHER TEXT IN YOUR RESPONSE.
                ONLY RESPOND WITH THE JSON OBJECT.
                """
                
                # Try with structured prompting
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": fallback_prompt}],
                    max_tokens=250
                )
                
                message_content = response.choices[0].message.content
                
                # Try to parse JSON from the response
                json_start = message_content.find('{')
                json_end = message_content.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = message_content[json_start:json_end]
                    try:
                        action_data = json.loads(json_str)
                        
                        # Validate required fields
                        if "action_type" in action_data:
                            return action_data
                    except json.JSONDecodeError:
                        print(f"Failed to parse JSON response for {self.character.name} (attempt {retry_count+1}/{max_retries+1})")
                
                # If we get here, parsing failed, try again
                retry_count += 1
                if retry_count > max_retries:
                    print(f"All structured prompting attempts failed for {self.character.name}. Falling back to basic parsing.")
                    return None
                
            except Exception as e:
                print(f"Structured prompting failed for {self.character.name} (attempt {retry_count+1}/{max_retries+1}): {e}")
                retry_count += 1
                if retry_count > max_retries:
                    print(f"All structured prompting attempts failed for {self.character.name}. Falling back to basic parsing.")
                    return None
        
        return None
            
    def _try_basic_parsing(self, game_state):
        """Try to get an action using basic text parsing"""
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Add a small delay to avoid rate limiting
                time.sleep(0.5 + retry_count * 0.5)  # Increase delay with each retry
                
                final_prompt = f"""
                You are {self.character.name}. You MUST choose ONE action from the following options:
                
                1. MOVE to a specific location (e.g., "I MOVE to Engineering")
                2. REPAIR a specific system (e.g., "I REPAIR Jump Core")
                3. USE a specific system (e.g., "I USE Sensors")
                4. BATTLE a specific threat (e.g., "I BATTLE Alien Boarding Party")
                5. END TURN (e.g., "I END my TURN")
                
                Your response must start with "I MOVE", "I REPAIR", "I USE", "I BATTLE", or "I END TURN".
                Be very specific about what location, system, or threat.
                
                Current Game State:
                {game_state.game_state_description()}
                """
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": final_prompt}],
                    max_tokens=150
                )
                
                message_content = response.choices[0].message.content
                
                # Very basic fallback parsing
                action_type = None
                parameters = {}
                
                if "MOVE" in message_content.upper():
                    action_type = "move"
                    # Try to extract destination
                    for loc in Location:
                        if loc.value in message_content:
                            parameters["destination"] = loc.value
                            break
                elif "REPAIR" in message_content.upper():
                    action_type = "repair"
                    # Try to extract system
                    for system in game_state.systems:
                        if system in message_content:
                            parameters["system"] = system
                            break
                elif "USE" in message_content.upper():
                    action_type = "use_system"
                    # Try to extract system
                    for system in game_state.systems:
                        if system in message_content:
                            parameters["system"] = system
                            break
                elif "BATTLE" in message_content.upper():
                    action_type = "battle"
                    # Try to extract threat
                    for threat in game_state.active_threats:
                        if threat.name in message_content:
                            parameters["threat"] = threat.name
                            break
                elif "END" in message_content.upper() and "TURN" in message_content.upper():
                    action_type = "end_turn"
                
                if action_type:
                    return {
                        "action_type": action_type,
                        "parameters": parameters,
                        "content": message_content,
                        "reason": "Parsed from text response"
                    }
                
                # If we get here, parsing failed, try again
                retry_count += 1
                if retry_count > max_retries:
                    print(f"All basic parsing attempts failed for {self.character.name}. Using default action.")
                    return None
                    
            except Exception as e:
                print(f"Basic parsing failed for {self.character.name} (attempt {retry_count+1}/{max_retries+1}): {e}")
                retry_count += 1
                if retry_count > max_retries:
                    print(f"All basic parsing attempts failed for {self.character.name}. Using default action.")
                    return None
        
        return None
            
    def _get_default_action(self, game_state):
        """Get a default action based on character skills and location"""
        print(f"All LLM approaches failed for {self.character.name}. Using default action.")
        
        # Check if character has engineering skill and there are systems to repair
        engineering_skill = self.character.skills.get(SkillType.ENGINEERING, 0)
        if engineering_skill > 0:
            # Try to repair Jump Core if possible
            if self.character.location.value == "Engineering" and engineering_skill >= 2:
                return {
                    "action_type": "repair",
                    "parameters": {"system": "Jump Core"},
                    "reason": "Default action: Repairing Jump Core"
                }
            
            # Try to repair any damaged system
            damaged_systems = [system for system, status in game_state.systems.items() 
                              if status == SystemStatus.DAMAGED]
            # Sort systems to ensure deterministic selection
            damaged_systems.sort()
            if damaged_systems:
                return {
                    "action_type": "repair",
                    "parameters": {"system": damaged_systems[0]},
                    "reason": f"Default action: Repairing damaged {damaged_systems[0]}"
                }
        
        # Check if character has tactical skill and there are threats
        tactical_skill = self.character.skills.get(SkillType.TACTICAL, 0)
        if tactical_skill > 0 and game_state.active_threats:
            # Find the easiest threat to battle
            sorted_threats = sorted(game_state.active_threats, key=lambda t: (t.difficulty, t.name))
            easiest_threat = sorted_threats[0]
            if tactical_skill >= (easiest_threat.difficulty - 1):
                return {
                    "action_type": "battle",
                    "parameters": {"threat": easiest_threat.name},
                    "reason": f"Default action: Battling {easiest_threat.name}"
                }
        
        # If no better option, move to Engineering to help with Jump Core
        if self.character.location.value != "Engineering":
            return {
                "action_type": "move",
                "parameters": {"destination": "Engineering"},
                "reason": "Default action: Moving to Engineering to help with Jump Core"
            }
        
        # If already at Engineering, use a system
        online_systems = [sys for sys, status in game_state.systems.items() 
                         if status != SystemStatus.OFFLINE]
        # Sort systems to ensure deterministic selection
        online_systems.sort()
        if online_systems:
            return {
                "action_type": "use_system",
                "parameters": {"system": online_systems[0]},
                "reason": f"Default action: Using {online_systems[0]}"
            }
        
        # Last resort: end turn
        return {
            "action_type": "end_turn",
            "parameters": {},
            "reason": "Default action: No viable actions available"
        } 