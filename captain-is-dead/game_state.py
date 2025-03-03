from typing import List, Dict, Tuple, Optional
from models import SystemStatus, Location, SkillType, CharacterRole, AlertLevel, Threat, Character, CrisisCard
import time
import random

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class GameState:
    def __init__(self):
        # Ship systems
        self.systems = {
            "Jump Core": SystemStatus.OFFLINE,
            "Shields": SystemStatus.ONLINE,
            "Sensors": SystemStatus.ONLINE,
            "Teleporter": SystemStatus.ONLINE,
            "Life Support": SystemStatus.ONLINE,
            "Targeting Computer": SystemStatus.ONLINE,
            "Holodeck": SystemStatus.ONLINE,
        }
        
        self.alert_level = AlertLevel.YELLOW
        self.jump_core_progress = 0  # 0-5 levels of progress
        self.active_threats: List[Threat] = []
        self.characters: List[Character] = []
        self.current_character_index = 0
        self.crisis_deck: List[CrisisCard] = []
        self.crisis_discard: List[CrisisCard] = []
        self.last_crisis: Optional[CrisisCard] = None
        
    def get_current_character(self) -> Character:
        return self.characters[self.current_character_index]
    
    def next_character_turn(self):
        self.characters[self.current_character_index].action_points = 4  # Reset action points to 4 (board game standard)
        self.current_character_index = (self.current_character_index + 1) % len(self.characters)
    
    def game_state_description(self) -> str:
        """Generate a text description of the current game state for LLM consumption"""
        description = []
        
        # Alert level
        description.append(f"Alert Level: {self.alert_level.value}")
        
        # Jump core progress
        description.append(f"Jump Core Progress: {self.jump_core_progress}/5")
        
        # Systems status
        description.append("Ship Systems:")
        for system, status in self.systems.items():
            description.append(f"  - {system}: {status.value}")
        
        # Active threats
        if self.active_threats:
            description.append("Active Threats:")
            for threat in self.active_threats:
                description.append(f"  - {threat}")
        else:
            description.append("No active threats.")
        
        # Characters
        description.append("Characters:")
        for i, character in enumerate(self.characters):
            if i == self.current_character_index:
                description.append(f"  -> {character} (CURRENT TURN - {character.action_points} action points)")
            else:
                description.append(f"  - {character}")
        
        return "\n".join(description)
    
    def is_game_over(self) -> Tuple[bool, str]:
        """Check if the game is over, returns (is_over, result_message)"""
        # Win condition
        if self.jump_core_progress >= 5:
            return True, "Victory! The jump core has been fully repaired and the ship has escaped."
        
        # Lose conditions
        critical_systems = ["Life Support", "Shields"]
        for system in critical_systems:
            if self.systems[system] == SystemStatus.OFFLINE:
                return True, f"Defeat! {system} has gone offline."
        
        if self.alert_level == AlertLevel.RED and len(self.active_threats) > 3:
            return True, "Defeat! The ship has been overwhelmed by threats during Red Alert."
        
        return False, ""


class Game:
    def __init__(self, num_characters=2, num_threats=2, difficulty="normal", seed=None):
        """
        Initialize the game with configurable complexity
        
        Parameters:
        - num_characters: int - Number of characters/agents (1-6)
        - num_threats: int - Number of initial threats (0-4)
        - difficulty: str - Game difficulty level ("easy", "normal", "hard")
        - seed: int - Optional random seed for deterministic behavior (None for random)
        """
        self.num_characters = max(1, min(6, num_characters))  # Clamp between 1-6
        self.num_threats = max(0, min(4, num_threats))  # Clamp between 0-4
        self.difficulty = difficulty
        self.seed = seed
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
            print(f"Using deterministic mode with seed: {seed}")
        
        self.game_state = GameState()
        self.setup_game()
        
    def setup_game(self):
        """Initialize the game with characters, threats, etc."""
        # Available character templates
        character_templates = [
            {
                "name": "Alex Chen", 
                "role": CharacterRole.ENGINEER,
                "skills": {
                    SkillType.ENGINEERING: 3,
                    SkillType.TACTICAL: 1,
                    SkillType.SCIENCE: 2,
                    SkillType.MEDICAL: 0,
                    SkillType.LEADERSHIP: 1
                },
                "special_ability": "Can repair systems more efficiently",
                "location": Location.ENGINEERING
            },
            {
                "name": "Dr. Maya Patel", 
                "role": CharacterRole.SCIENCE_OFFICER,
                "skills": {
                    SkillType.ENGINEERING: 1,
                    SkillType.TACTICAL: 0,
                    SkillType.SCIENCE: 3,
                    SkillType.MEDICAL: 2,
                    SkillType.LEADERSHIP: 1
                },
                "special_ability": "Can analyze threats to find weaknesses",
                "location": Location.SCIENCE_LAB
            },
            {
                "name": "Commander Riz Jackson", 
                "role": CharacterRole.TACTICAL_OFFICER,
                "skills": {
                    SkillType.ENGINEERING: 0,
                    SkillType.TACTICAL: 3,
                    SkillType.SCIENCE: 1,
                    SkillType.MEDICAL: 0,
                    SkillType.LEADERSHIP: 2
                },
                "special_ability": "Can deal with threats more effectively",
                "location": Location.WEAPONS_BAY
            },
            {
                "name": "Dr. James Wilson", 
                "role": CharacterRole.MEDICAL_OFFICER,
                "skills": {
                    SkillType.ENGINEERING: 0,
                    SkillType.TACTICAL: 0,
                    SkillType.SCIENCE: 2,
                    SkillType.MEDICAL: 3,
                    SkillType.LEADERSHIP: 1
                },
                "special_ability": "Can heal and boost crew effectiveness",
                "location": Location.SICK_BAY
            },
            {
                "name": "Lt. Olivia Chen", 
                "role": CharacterRole.COMMUNICATIONS_OFFICER,
                "skills": {
                    SkillType.ENGINEERING: 1,
                    SkillType.TACTICAL: 1,
                    SkillType.SCIENCE: 1,
                    SkillType.MEDICAL: 0,
                    SkillType.LEADERSHIP: 3
                },
                "special_ability": "Can coordinate crew actions efficiently",
                "location": Location.COMM_CENTER
            },
            {
                "name": "Acting Captain Mira Novak", 
                "role": CharacterRole.CAPTAIN,
                "skills": {
                    SkillType.ENGINEERING: 1,
                    SkillType.TACTICAL: 2,
                    SkillType.SCIENCE: 1,
                    SkillType.MEDICAL: 0,
                    SkillType.LEADERSHIP: 3
                },
                "special_ability": "Can inspire crew to perform beyond their limits",
                "location": Location.BRIDGE
            },
        ]
        
        # Available threat templates
        threat_templates = [
            Threat("System Cascade Failure", "Ship systems are failing one after another", 3),
            Threat("Alien Boarding Party", "Hostile aliens have teleported aboard", 4),
            Threat("Energy Drain", "Something is draining the ship's power reserves", 2),
            Threat("Computer Malfunction", "Ship's computer is behaving erratically", 3)
        ]
        
        # Initialize characters based on the requested number
        selected_templates = character_templates[:self.num_characters]
        self.game_state.characters = []
        
        for template in selected_templates:
            char = Character(
                name=template["name"],
                role=template["role"],
                skills=template["skills"],
                special_ability=template["special_ability"],
                location=template["location"]
            )
            self.game_state.characters.append(char)
        
        # Initialize threats based on the requested number
        selected_threats = threat_templates[:self.num_threats]
        self.game_state.active_threats = selected_threats.copy()
        
        # Initialize crisis cards
        crisis_templates = [
            CrisisCard("System Failure", "A critical system has malfunctioned.", "system_damage", 2),
            CrisisCard("Alien Boarding", "Hostile aliens have boarded the ship.", "new_threat", 3),
            CrisisCard("Power Surge", "A power surge has affected ship systems.", "system_damage", 1),
            CrisisCard("Communications Interference", "Communications are being jammed.", "action_restriction", 2),
            CrisisCard("Hull Breach", "The ship's hull has been breached.", "system_damage", 3),
            CrisisCard("Navigation Error", "The ship's navigation is malfunctioning.", "system_damage", 2),
            CrisisCard("Alien Attack", "The ship is under attack from alien forces.", "new_threat", 3),
            CrisisCard("Life Support Failure", "Life support systems are failing.", "system_damage", 3),
            CrisisCard("Computer Virus", "Ship's computer has been infected with a virus.", "action_restriction", 2),
            CrisisCard("Sensor Malfunction", "Sensors are providing incorrect readings.", "system_damage", 1),
        ]
        
        self.game_state.crisis_deck = crisis_templates.copy()
        
        # Shuffle the crisis deck (will be deterministic if seed was set)
        random.shuffle(self.game_state.crisis_deck)
        
        # Adjust difficulty
        if self.difficulty == "easy":
            # Make it easier by reducing threat difficulty
            for threat in self.game_state.active_threats:
                threat.difficulty = max(1, threat.difficulty - 1)
            # Give characters more action points
            for char in self.game_state.characters:
                char.action_points = 5  # One extra action point in easy mode
        elif self.difficulty == "hard":
            # Make it harder by increasing threat difficulty
            for threat in self.game_state.active_threats:
                threat.difficulty += 1
            # Reduce the initial status of some systems
            self.game_state.systems["Shields"] = SystemStatus.DAMAGED
            # Set a higher alert level
            self.game_state.alert_level = AlertLevel.ORANGE
            # Reduce action points
            for char in self.game_state.characters:
                char.action_points = 3  # One less action point in hard mode
        
    def create_agents(self, model="gemini-2.0-flash-lite"):
        """Create LLM agents for all characters"""
        from llm_agent import LLMAgent
        self.agents = [LLMAgent(character, model) for character in self.game_state.characters]
        
    def play_turn(self):
        """
        Play a single character's turn following the board game structure:
        1. Player spends their Action Points (AP)
        2. Draw and resolve a Crisis Card
        3. Next player's turn begins
        """
        current_character = self.game_state.get_current_character()
        
        # Find the agent for the current character
        current_agent = next(agent for agent in self.agents if agent.character == current_character)
        
        # Display turn header for this character
        print(f"\n{Colors.BOLD}{Colors.GREEN}🎮 {current_character.name}'s turn:{Colors.ENDC}")
        
        # Step 1: Player spends their Action Points
        action_points_remaining = current_character.action_points
        while action_points_remaining > 0:
            # Get the agent's action
            print(f"{Colors.CYAN}⏳ {current_character.name} is thinking... ({action_points_remaining} AP remaining){Colors.ENDC}")
            action_data = current_agent.get_action(self.game_state)
            
            action_type = action_data.get("action_type", "unknown")
            action_executed = False
            action_result = ""
            action_cost = 1  # Default action cost
            
            # Skip turn if it's not this character's turn or if they choose to end their turn
            if action_type == "skip" or action_type == "end_turn":
                print(f"{Colors.YELLOW}Ending turn: {action_data.get('reason', 'Character chose to end their turn')}{Colors.ENDC}")
                break
                
            # Handle text_response (fallback to old method)
            if action_type == "text_response":
                content = action_data.get("content", "")
                print(content)
                
                # Basic fallback parsing (minimal support for old method)
                if "MOVE" in content.upper():
                    print(f"{Colors.YELLOW}Using fallback parsing for text response.{Colors.ENDC}")
                    action_points_remaining -= 1
                    continue
                    
            # Display the action and reason
            if action_type != "text_response":
                action_display = f"{action_type.upper()}"
                if "parameters" in action_data:
                    params = action_data["parameters"]
                    param_str = ", ".join([f"{k}='{v}'" for k, v in params.items()])
                    action_display += f"({param_str})"
                    
                print(f"{Colors.BOLD}ACTION:{Colors.ENDC} {Colors.YELLOW}{action_display}{Colors.ENDC}")
                
                if "reason" in action_data:
                    print(f"{Colors.BOLD}REASON:{Colors.ENDC} {action_data['reason']}")
            
            # Process each action type
            if action_type == "move":
                # Extract destination from parameters
                if "destination" in action_data.get("parameters", {}):
                    destination_str = action_data["parameters"]["destination"]
                    destination = None
                    
                    # Find the matching Location enum
                    for loc in Location:
                        if loc.value == destination_str:
                            destination = loc
                            break
                    
                    if destination:
                        # Update character location
                        old_location = current_character.location
                        current_character.location = destination
                        action_executed = True
                        action_result = f"{current_character.name} moved from {old_location.value} to {destination.value}."
                    else:
                        action_result = f"Invalid location: {destination_str}"
                else:
                    action_result = "No destination specified for movement."
                    
            elif action_type == "repair":
                # Extract system to repair from parameters
                if "system" in action_data.get("parameters", {}):
                    system_to_repair = action_data["parameters"]["system"]
                    
                    if system_to_repair in self.game_state.systems:
                        system_status = self.game_state.systems[system_to_repair]
                        
                        if system_status == SystemStatus.ONLINE:
                            action_result = f"{system_to_repair} is already online and functioning correctly."
                        else:
                            # Check if character has sufficient engineering skill
                            engineering_skill = current_character.skills.get(SkillType.ENGINEERING, 0)
                            
                            if system_to_repair == "Jump Core":
                                # Jump Core requires special handling
                                if engineering_skill >= 2:
                                    # Progress the jump core by 1 step
                                    self.game_state.jump_core_progress += 1
                                    action_executed = True
                                    action_result = f"{current_character.name} made progress on the Jump Core! Progress: {self.game_state.jump_core_progress}/5"
                                    
                                    # If fully repaired, set system status to online
                                    if self.game_state.jump_core_progress >= 5:
                                        self.game_state.systems["Jump Core"] = SystemStatus.ONLINE
                                        action_result += " Jump Core is now fully repaired and ONLINE!"
                                else:
                                    action_result = f"Insufficient Engineering skill to repair Jump Core. Required: 2, Current: {engineering_skill}"
                            else:
                                # Regular system repair
                                if engineering_skill >= 1:
                                    if system_status == SystemStatus.DAMAGED:
                                        self.game_state.systems[system_to_repair] = SystemStatus.ONLINE
                                        action_executed = True
                                        action_result = f"{current_character.name} repaired {system_to_repair}! It is now ONLINE."
                                    elif system_status == SystemStatus.OFFLINE:
                                        self.game_state.systems[system_to_repair] = SystemStatus.DAMAGED
                                        action_executed = True
                                        action_result = f"{current_character.name} partially repaired {system_to_repair}. It is now DAMAGED but functional."
                                else:
                                    action_result = f"Insufficient Engineering skill to repair {system_to_repair}. Required: 1, Current: {engineering_skill}"
                    else:
                        action_result = f"Unknown system: {system_to_repair}"
                else:
                    action_result = "No system specified for repair."
                    
            elif action_type == "use_system":
                # Extract system to use from parameters
                if "system" in action_data.get("parameters", {}):
                    system_to_use = action_data["parameters"]["system"]
                    
                    if system_to_use in self.game_state.systems:
                        # Check if system is online or damaged
                        system_status = self.game_state.systems[system_to_use]
                        
                        if system_status == SystemStatus.OFFLINE:
                            action_result = f"Cannot use {system_to_use} because it is OFFLINE."
                        else:
                            # System is either ONLINE or DAMAGED
                            action_executed = True
                            
                            # Handle specific system effects
                            if system_to_use == "Shields":
                                # Improve shields - reduce threat level
                                if self.game_state.active_threats:
                                    # Sort threats to ensure deterministic selection when seed is set
                                    sorted_threats = sorted(self.game_state.active_threats, key=lambda t: t.name)
                                    threat = random.choice(sorted_threats)
                                    threat.difficulty = max(1, threat.difficulty - 1)
                                    action_result = f"{current_character.name} reinforced the Shields! Reduced threat level of {threat.name} to {threat.difficulty}."
                                else:
                                    action_result = f"{current_character.name} reinforced the Shields, but there are no active threats."
                            
                            elif system_to_use == "Sensors":
                                # Scan for threats - provide info
                                if self.game_state.active_threats:
                                    threats_info = "\n".join([f"  • {t.name}: {t.description} (Difficulty: {t.difficulty})" for t in self.game_state.active_threats])
                                    action_result = f"{current_character.name} used the Sensors to scan active threats:\n{threats_info}"
                                else:
                                    action_result = f"{current_character.name} used the Sensors but detected no active threats."
                            
                            elif system_to_use == "Teleporter":
                                # Teleport to another location
                                possible_locations = list(Location)
                                # Sort locations to ensure deterministic selection when seed is set
                                possible_locations.sort(key=lambda loc: loc.value)
                                new_location = random.choice(possible_locations)
                                old_location = current_character.location
                                current_character.location = new_location
                                action_result = f"{current_character.name} used the Teleporter to move from {old_location.value} to {new_location.value}."
                            
                            elif system_to_use == "Targeting Computer":
                                # Reduce a threat's difficulty
                                if self.game_state.active_threats:
                                    # Sort threats to ensure deterministic selection when seed is set
                                    sorted_threats = sorted(self.game_state.active_threats, key=lambda t: t.name)
                                    threat = random.choice(sorted_threats)
                                    threat.difficulty = max(1, threat.difficulty - 1)
                                    action_result = f"{current_character.name} used the Targeting Computer to analyze {threat.name}! Reduced its difficulty to {threat.difficulty}."
                                else:
                                    action_result = f"{current_character.name} used the Targeting Computer, but there are no active threats."
                            
                            elif system_to_use == "Holodeck":
                                # Generate a simulation to practice - boost a random skill
                                skill_types = list(SkillType)
                                # Sort skills to ensure deterministic selection when seed is set
                                skill_types.sort(key=lambda skill: skill.value)
                                skill_to_boost = random.choice(skill_types)
                                current_skill = current_character.skills.get(skill_to_boost, 0)
                                current_character.skills[skill_to_boost] = min(5, current_skill + 1)  # Cap at 5
                                action_result = f"{current_character.name} used the Holodeck to practice! {skill_to_boost.value} skill increased to {current_character.skills[skill_to_boost]}."
                            
                            elif system_to_use == "Life Support":
                                # Improve life support - give extra action point
                                current_character.action_points += 1
                                action_points_remaining += 1
                                action_result = f"{current_character.name} optimized Life Support systems! Gained 1 extra action point (total: {action_points_remaining})."
                            
                            else:
                                action_result = f"{current_character.name} used {system_to_use}, but it had no specific effect."
                    else:
                        action_result = f"Unknown system: {system_to_use}"
                else:
                    action_result = "No system specified to use."
                    
            elif action_type == "battle":
                # Extract threat to battle from parameters
                if "threat" in action_data.get("parameters", {}):
                    threat_name = action_data["parameters"]["threat"]
                    
                    # Find the matching threat
                    threat_to_battle = None
                    for threat in self.game_state.active_threats:
                        if threat.name == threat_name:
                            threat_to_battle = threat
                            break
                    
                    if threat_to_battle:
                        # Check if character has sufficient tactical skill
                        tactical_skill = current_character.skills.get(SkillType.TACTICAL, 0)
                        
                        if tactical_skill >= (threat_to_battle.difficulty - 1):  # Allow for some chance of success
                            # Success chance based on skill vs difficulty
                            success_chance = min(0.9, 0.5 + (tactical_skill - threat_to_battle.difficulty) * 0.2)
                            
                            # Use a deterministic approach for battle outcomes when seed is set
                            battle_roll = random.random()  # Will be deterministic if seed was set
                            if battle_roll < success_chance:
                                # Successfully defeated the threat
                                self.game_state.active_threats.remove(threat_to_battle)
                                action_executed = True
                                action_result = f"{current_character.name} successfully defeated the {threat_to_battle.name} threat!"
                            else:
                                # Failed to defeat the threat
                                action_executed = True
                                # The threat gets stronger
                                threat_to_battle.difficulty += 1
                                action_result = f"{current_character.name} failed to defeat {threat_to_battle.name}! The threat has grown stronger (Difficulty: {threat_to_battle.difficulty})."
                        else:
                            action_result = f"Insufficient Tactical skill to battle {threat_to_battle.name}. Required: {threat_to_battle.difficulty - 1}, Current: {tactical_skill}"
                    else:
                        action_result = f"Unknown threat: {threat_name}"
                else:
                    action_result = "No threat specified for battle."
            
            # If no specific action was recognized or executed
            if not action_executed and action_type not in ["skip", "text_response", "end_turn"]:
                print(f"{Colors.YELLOW}Could not execute action: '{action_type}'{Colors.ENDC}")
                action_points_remaining -= 1  # Still consume an action point
                action_result = "Action could not be executed. Lost 1 action point."
            elif action_executed:
                # Consume action points for the executed action
                action_points_remaining -= action_cost
            
            # Display the result of the action
            if action_result:
                print(f"\n{Colors.CYAN}📝 RESULT: {action_result}{Colors.ENDC}")
            
            # Show remaining action points
            print(f"{Colors.CYAN}► {current_character.name} has {action_points_remaining} action points remaining.{Colors.ENDC}")
            
            # Check if game is over after this action
            game_over, message = self.game_state.is_game_over()
            if game_over:
                return True, message
                
            # If no more action points, break the loop
            if action_points_remaining <= 0:
                print(f"{Colors.CYAN}► {current_character.name} has used all action points.{Colors.ENDC}")
                break
        
        # Update the character's action points
        current_character.action_points = action_points_remaining
        
        # Step 2: Draw and resolve a Crisis Card
        print(f"\n{Colors.BOLD}{Colors.RED}🚨 CRISIS PHASE{Colors.ENDC}")
        self.draw_crisis_card()
        
        # Check if game is over after crisis
        game_over, message = self.game_state.is_game_over()
        if game_over:
            return True, message
            
        # Step 3: Next player's turn begins
        self.game_state.next_character_turn()
        print(f"\n{Colors.CYAN}► Next character's turn will begin.{Colors.ENDC}")
        
        return False, ""
        
    def display_ship_status(self):
        """Display the ship's current status in a visually appealing way"""
        gs = self.game_state
        
        # Show alert level with appropriate color
        alert_color = Colors.YELLOW
        if gs.alert_level == AlertLevel.ORANGE:
            alert_color = Colors.YELLOW
        elif gs.alert_level == AlertLevel.RED:
            alert_color = Colors.RED
            
        print(f"\n{Colors.BOLD}🚨 ALERT STATUS:{Colors.ENDC} {alert_color}{gs.alert_level.value}{Colors.ENDC}")
        
        # Jump core progress
        progress_bar = "█" * gs.jump_core_progress + "░" * (5 - gs.jump_core_progress)
        print(f"{Colors.BOLD}🚀 JUMP CORE PROGRESS:{Colors.ENDC} {Colors.CYAN}[{progress_bar}] {gs.jump_core_progress}/5{Colors.ENDC}")
        
        # Last crisis card
        if gs.last_crisis:
            print(f"\n{Colors.BOLD}🚨 LAST CRISIS:{Colors.ENDC} {Colors.RED}{gs.last_crisis.name}{Colors.ENDC}")
            print(f"  {gs.last_crisis.description} (Severity: {gs.last_crisis.severity})")
        
        # Systems status with appropriate colors
        print(f"\n{Colors.BOLD}📊 SHIP SYSTEMS:{Colors.ENDC}")
        for system, status in gs.systems.items():
            if status == SystemStatus.ONLINE:
                status_color = Colors.GREEN
            elif status == SystemStatus.DAMAGED:
                status_color = Colors.YELLOW
            else:  # OFFLINE
                status_color = Colors.RED
                
            print(f"  • {system}: {status_color}{status.value}{Colors.ENDC}")
        
        # Active threats
        if gs.active_threats:
            print(f"\n{Colors.BOLD}⚠️ ACTIVE THREATS:{Colors.ENDC}")
            for threat in gs.active_threats:
                print(f"  • {Colors.RED}{threat.name}{Colors.ENDC} (Difficulty: {threat.difficulty})")
                print(f"    {threat.description}")
        else:
            print(f"\n{Colors.BOLD}⚠️ ACTIVE THREATS:{Colors.ENDC} {Colors.GREEN}None{Colors.ENDC}")
        
        # Characters
        print(f"\n{Colors.BOLD}👥 CREW STATUS:{Colors.ENDC}")
        for i, character in enumerate(gs.characters):
            if i == gs.current_character_index:
                char_color = Colors.GREEN
                active = f" {Colors.BOLD}[ACTIVE - {character.action_points} AP]{Colors.ENDC}"
            else:
                char_color = Colors.BLUE
                active = ""
                
            print(f"  • {char_color}{character.name}{Colors.ENDC} ({character.role.value}) at {character.location.value}{active}")
            skills_str = ", ".join([f"{skill.value}: {level}" for skill, level in character.skills.items() if level > 0])
            print(f"    Skills: {skills_str}")
            print(f"    Special: {character.special_ability}")
            
    def run_game(self, max_turns=10):
        """Run the game for a specified number of turns or until game over"""
        self.create_agents()
        
        # Display welcome message
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'THE CAPTAIN IS DEAD - SIMULATION':^60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
        print("\nThe captain is dead... Can you and your crew repair the Jump Core")
        print("and escape before the alien threats overwhelm your ship?\n")
        print("\nGame follows the board game turn structure:")
        print("1. Player spends their Action Points (AP)")
        print("2. Draw and resolve a Crisis Card")
        print("3. Next player's turn begins\n")
        
        time.sleep(1)  # Dramatic pause
        
        turn_count = 0
        while turn_count < max_turns:
            # Display turn header
            print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.ENDC}")
            print(f"{Colors.BOLD}{Colors.BLUE}{f' TURN {turn_count + 1} ':=^60}{Colors.ENDC}")
            print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.ENDC}")
            
            # Display current ship status
            self.display_ship_status()
            
            # Add a separator before the action
            print(f"\n{Colors.BOLD}{'-' * 60}{Colors.ENDC}")
            
            # Play the turn (returns game_over, message)
            game_over, message = self.play_turn()
            if game_over:
                print(f"\n{Colors.BOLD}{Colors.RED}{'=' * 60}{Colors.ENDC}")
                print(f"{Colors.BOLD}{Colors.RED}{'GAME OVER':^60}{Colors.ENDC}")
                print(f"{Colors.BOLD}{Colors.RED}{'=' * 60}{Colors.ENDC}")
                print(f"\n{message}")
                break
                
            turn_count += 1
            
            # Ask if user wants to continue (optional)
            if turn_count < max_turns and not game_over:
                print(f"\n{Colors.CYAN}Press Enter to continue to next turn...{Colors.ENDC}")
                input()
        
        # End of game summary
        if not game_over:
            print(f"\n{Colors.YELLOW}Simulation completed after {turn_count} turns.{Colors.ENDC}")
            print(f"Jump Core Progress: {self.game_state.jump_core_progress}/5")
            
    def draw_crisis_card(self) -> CrisisCard:
        """Draw a crisis card from the deck and resolve its effects"""
        # If deck is empty, shuffle discard pile back in
        if not self.game_state.crisis_deck and self.game_state.crisis_discard:
            print(f"{Colors.YELLOW}Crisis deck empty. Reshuffling discard pile.{Colors.ENDC}")
            self.game_state.crisis_deck = self.game_state.crisis_discard
            self.game_state.crisis_discard = []
            
            # Shuffle the deck (will be deterministic if seed was set)
            random.shuffle(self.game_state.crisis_deck)
            
        # If still empty (no cards at all), create a default crisis
        if not self.game_state.crisis_deck:
            default_crisis = CrisisCard("Emergency Alert", "Ship systems are failing.", "system_damage", 2)
            self.game_state.crisis_deck.append(default_crisis)
            
        # Draw the top card
        crisis = self.game_state.crisis_deck.pop(0)
        self.game_state.last_crisis = crisis
        self.game_state.crisis_discard.append(crisis)
        
        print(f"\n{Colors.BOLD}{Colors.RED}🚨 CRISIS CARD: {crisis.name}{Colors.ENDC}")
        print(f"{Colors.RED}{crisis.description} (Severity: {crisis.severity}){Colors.ENDC}")
        
        # Resolve crisis effects
        self.resolve_crisis(crisis)
        
        return crisis
        
    def resolve_crisis(self, crisis: CrisisCard):
        """Resolve the effects of a crisis card"""
        if crisis.effect_type == "system_damage":
            # Damage a random system
            available_systems = [sys for sys, status in self.game_state.systems.items() 
                               if status != SystemStatus.OFFLINE and sys != "Jump Core"]
            
            if available_systems:
                # Sort systems to ensure deterministic selection when seed is set
                available_systems.sort()
                
                # Select a system to damage (deterministic if seed was set)
                system_to_damage = random.choice(available_systems)
                current_status = self.game_state.systems[system_to_damage]
                
                if current_status == SystemStatus.ONLINE:
                    self.game_state.systems[system_to_damage] = SystemStatus.DAMAGED
                    print(f"{Colors.YELLOW}System {system_to_damage} has been DAMAGED!{Colors.ENDC}")
                elif current_status == SystemStatus.DAMAGED:
                    self.game_state.systems[system_to_damage] = SystemStatus.OFFLINE
                    print(f"{Colors.RED}System {system_to_damage} is now OFFLINE!{Colors.ENDC}")
                    
                    # If shields go offline, increase alert level
                    if system_to_damage == "Shields" and self.game_state.alert_level != AlertLevel.RED:
                        if self.game_state.alert_level == AlertLevel.YELLOW:
                            self.game_state.alert_level = AlertLevel.ORANGE
                        elif self.game_state.alert_level == AlertLevel.ORANGE:
                            self.game_state.alert_level = AlertLevel.RED
                        print(f"{Colors.RED}Alert level increased to {self.game_state.alert_level.value}!{Colors.ENDC}")
            else:
                print(f"{Colors.YELLOW}No systems available to damage. Crisis effect mitigated.{Colors.ENDC}")
                
        elif crisis.effect_type == "new_threat":
            # Add a new threat
            potential_threats = [
                Threat("Alien Saboteur", "An alien has infiltrated the ship", 3),
                Threat("Power Fluctuation", "Ship's power is unstable", 2),
                Threat("Hull Breach", "The ship's hull has been breached", 4),
                Threat("Navigation Error", "Ship's navigation is malfunctioning", 2)
            ]
            
            # Sort threats by name to ensure deterministic selection when seed is set
            potential_threats.sort(key=lambda t: t.name)
            
            if len(self.game_state.active_threats) < 4:  # Cap the number of threats
                new_threat = random.choice(potential_threats)
                self.game_state.active_threats.append(new_threat)
                print(f"{Colors.RED}New threat: {new_threat.name} - {new_threat.description} (Difficulty: {new_threat.difficulty}){Colors.ENDC}")
            else:
                print(f"{Colors.YELLOW}Too many active threats. Increasing alert level instead.{Colors.ENDC}")
                if self.game_state.alert_level == AlertLevel.YELLOW:
                    self.game_state.alert_level = AlertLevel.ORANGE
                elif self.game_state.alert_level == AlertLevel.ORANGE:
                    self.game_state.alert_level = AlertLevel.RED
                print(f"{Colors.RED}Alert level increased to {self.game_state.alert_level.value}!{Colors.ENDC}")
                
        elif crisis.effect_type == "action_restriction":
            # Reduce action points for all characters
            for character in self.game_state.characters:
                character.action_points = max(1, character.action_points - 1)
            print(f"{Colors.YELLOW}All characters lose 1 action point due to the crisis!{Colors.ENDC}")
            
        # If shields are offline, make crisis effects worse
        if self.game_state.systems["Shields"] == SystemStatus.OFFLINE:
            print(f"{Colors.RED}Shields are OFFLINE! Crisis effects are amplified!{Colors.ENDC}")
            
            # Add an additional effect
            if crisis.effect_type == "system_damage":
                # Damage another system
                available_systems = [sys for sys, status in self.game_state.systems.items() 
                                  if status != SystemStatus.OFFLINE and sys != "Jump Core"]
                
                # Sort systems to ensure deterministic selection when seed is set
                available_systems.sort()
                
                if available_systems:
                    system_to_damage = random.choice(available_systems)
                    current_status = self.game_state.systems[system_to_damage]
                    
                    if current_status == SystemStatus.ONLINE:
                        self.game_state.systems[system_to_damage] = SystemStatus.DAMAGED
                        print(f"{Colors.YELLOW}Additional system {system_to_damage} has been DAMAGED!{Colors.ENDC}")
                    elif current_status == SystemStatus.DAMAGED:
                        self.game_state.systems[system_to_damage] = SystemStatus.OFFLINE
                        print(f"{Colors.RED}Additional system {system_to_damage} is now OFFLINE!{Colors.ENDC}")
            
            elif crisis.effect_type == "new_threat" and len(self.game_state.active_threats) < 4:
                # Add another threat
                potential_threats = [
                    Threat("Alien Saboteur", "An alien has infiltrated the ship", 3),
                    Threat("Power Fluctuation", "Ship's power is unstable", 2),
                    Threat("Hull Breach", "The ship's hull has been breached", 4),
                    Threat("Navigation Error", "Ship's navigation is malfunctioning", 2)
                ]
                
                # Sort threats by name to ensure deterministic selection when seed is set
                potential_threats.sort(key=lambda t: t.name)
                
                new_threat = random.choice(potential_threats)
                self.game_state.active_threats.append(new_threat)
                print(f"{Colors.RED}Additional threat: {new_threat.name} - {new_threat.description} (Difficulty: {new_threat.difficulty}){Colors.ENDC}")
                
            elif crisis.effect_type == "action_restriction":
                # Further reduce action points
                for character in self.game_state.characters:
                    character.action_points = max(1, character.action_points - 1)
                print(f"{Colors.YELLOW}All characters lose an additional action point!{Colors.ENDC}")
                
        # If at red alert, make crisis even worse
        if self.game_state.alert_level == AlertLevel.RED:
            print(f"{Colors.RED}RED ALERT! Crisis effects are catastrophic!{Colors.ENDC}")
            
            # Increase difficulty of all threats
            for threat in self.game_state.active_threats:
                threat.difficulty += 1
                print(f"{Colors.RED}Threat {threat.name} difficulty increased to {threat.difficulty}!{Colors.ENDC}") 