from typing import List, Dict, Tuple, Optional, Set
from models import DiseaseStatus, DiseaseColor, PlayerRole, City, Player, InfectionCard, PlayerCard, EventCard
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
    BLACK = '\033[90m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class GameState:
    def __init__(self):
        # Game board
        self.cities: Dict[str, City] = {}
        
        # Disease status
        self.disease_status = {
            DiseaseColor.BLUE: DiseaseStatus.ACTIVE,
            DiseaseColor.YELLOW: DiseaseStatus.ACTIVE,
            DiseaseColor.BLACK: DiseaseStatus.ACTIVE,
            DiseaseColor.RED: DiseaseStatus.ACTIVE
        }
        
        # Counters
        self.outbreak_counter = 0
        self.infection_rate_index = 0
        self.infection_rates = [2, 2, 2, 3, 3, 4, 4]  # Number of infection cards drawn per turn
        
        # Cubes supply
        self.disease_cubes = {
            DiseaseColor.BLUE: 24,
            DiseaseColor.YELLOW: 24,
            DiseaseColor.BLACK: 24,
            DiseaseColor.RED: 24
        }
        
        # Research stations
        self.total_research_stations = 6
        self.placed_research_stations = 0
        
        # Players
        self.players: List[Player] = []
        self.current_player_index = 0
        
        # Card decks
        self.player_deck: List[PlayerCard] = []
        self.player_discard: List[PlayerCard] = []
        self.infection_deck: List[InfectionCard] = []
        self.infection_discard: List[InfectionCard] = []
        
        # Game state flags
        self.quiet_night_active = False  # One Quiet Night event
        
        # Message history for communication between players
        self.message_history: List[Dict] = []
    
    def get_current_player(self) -> Player:
        """Get the player whose turn it currently is"""
        return self.players[self.current_player_index]
    
    def next_player_turn(self):
        """Advance to the next player's turn"""
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.players[self.current_player_index].action_points = 4  # Reset action points
    
    def game_state_description(self) -> str:
        """Generate a text description of the current game state"""
        description = []
        
        # Disease status
        diseases_desc = []
        for color, status in self.disease_status.items():
            diseases_desc.append(f"{color.value}: {status.value}")
        description.append("Diseases:\n" + "\n".join(f"- {d}" for d in diseases_desc))
        
        # Outbreak counter
        description.append(f"Outbreak Counter: {self.outbreak_counter}/8")
        
        # Infection rate
        description.append(f"Infection Rate: {self.infection_rates[self.infection_rate_index]} (index: {self.infection_rate_index})")
        
        # Research stations
        stations = [city for city in self.cities.values() if city.has_research_station]
        description.append(f"Research Stations ({len(stations)}/{self.total_research_stations}):")
        for city in stations:
            description.append(f"- {city.name}")
        
        # Current player
        current_player = self.get_current_player()
        description.append(f"Current Player: {current_player.name} ({current_player.role.value})")
        description.append(f"Location: {current_player.location}")
        description.append(f"Actions Remaining: {current_player.action_points}")
        description.append(f"Hand: {', '.join(current_player.hand)}")
        
        # Most infected cities (top 5)
        infected_cities = sorted(
            [city for city in self.cities.values() if city.get_total_disease_cubes() > 0],
            key=lambda c: c.get_total_disease_cubes(),
            reverse=True
        )[:5]
        
        if infected_cities:
            description.append("Top Infected Cities:")
            for city in infected_cities:
                cubes_desc = ", ".join([f"{color.value}: {count}" for color, count in city.disease_cubes.items() if count > 0])
                description.append(f"- {city.name}: {cubes_desc}")
        
        return "\n".join(description)
    
    def is_game_over(self) -> Tuple[bool, str]:
        """Check if the game is over. Returns (is_over, reason)"""
        # Win condition: all diseases cured
        if all(status != DiseaseStatus.ACTIVE for status in self.disease_status.values()):
            return True, "Victory! All diseases have been cured."
        
        # Lose condition 1: Too many outbreaks
        if self.outbreak_counter >= 8:
            return True, "Defeat! Too many outbreaks occurred."
        
        # Lose condition 2: Ran out of disease cubes
        for color, count in self.disease_cubes.items():
            if count <= 0:
                return True, f"Defeat! Ran out of {color.value} disease cubes."
        
        # Lose condition 3: Ran out of player cards
        if not self.player_deck:
            return True, "Defeat! The player deck is empty."
        
        return False, ""
    
    def can_players_communicate(self, sender: Player, receiver: Player) -> bool:
        """Check if two players can communicate (they are in the same city)"""
        # In Pandemic, players can communicate freely if they are in the same city
        # The Researcher role can give cards to other players in the same city without needing the specific card
        return sender.location == receiver.location
    
    def send_message(self, sender: Player, receiver: Player, message: str) -> bool:
        """Send a message from one player to another. Returns success status."""
        if not self.can_players_communicate(sender, receiver):
            return False
        
        # Add message to receiver's message queue
        receiver.messages.append({
            "sender": f"{sender.name} ({sender.role.value})",
            "content": message,
            "timestamp": time.time()
        })
        
        # Add to message history
        self.message_history.append({
            "sender": f"{sender.name} ({sender.role.value})",
            "receiver": f"{receiver.name} ({receiver.role.value})",
            "content": message,
            "timestamp": time.time()
        })
        
        return True
    
    def broadcast_message(self, sender: Player, message: str) -> List[Player]:
        """Send a message to all players in the same city. Returns list of players who received the message."""
        recipients = []
        for player in self.players:
            if player != sender and player.location == sender.location:
                success = self.send_message(sender, player, message)
                if success:
                    recipients.append(player)
        return recipients


class Game:
    def __init__(self, num_players=2, difficulty="normal", seed=None):
        """
        Initialize a new Pandemic game
        
        Args:
            num_players: Number of players (2-4)
            difficulty: Game difficulty (easy, normal, hard)
            seed: Random seed for deterministic behavior
        """
        if seed is not None:
            random.seed(seed)
        
        self.state = GameState()
        self.num_players = min(max(2, num_players), 4)  # Ensure 2-4 players
        self.difficulty = difficulty
        
        # Number of epidemic cards based on difficulty
        self.num_epidemic_cards = {
            "easy": 4,
            "normal": 5,
            "hard": 6
        }[difficulty]
        
        # Setup the game
        self.setup_game()
        
    def setup_game(self):
        """Setup the game board, players, and initial state"""
        # Initialize cities (simplified version with key cities)
        self._initialize_cities()
        
        # Create card decks
        self._create_infection_deck()
        self._create_player_deck()
        
        # Create players with random roles
        self._create_players()
        
        # Initial infections
        self._perform_initial_infections()
        
        # Add research station to Atlanta and make it the starting location
        self.state.cities["Atlanta"].has_research_station = True
        self.state.placed_research_stations = 1
        
        # Deal initial cards to players
        self._deal_initial_cards()
    
    def _initialize_cities(self):
        """Initialize the cities on the board with their connections"""
        # Blue cities
        self.state.cities["Atlanta"] = City("Atlanta", DiseaseColor.BLUE, ["Chicago", "Washington", "Miami"])
        self.state.cities["Chicago"] = City("Chicago", DiseaseColor.BLUE, ["San Francisco", "Los Angeles", "Mexico City", "Atlanta", "Montreal"])
        self.state.cities["Montreal"] = City("Montreal", DiseaseColor.BLUE, ["Chicago", "New York", "Washington"])
        self.state.cities["New York"] = City("New York", DiseaseColor.BLUE, ["Montreal", "Washington", "London", "Madrid"])
        self.state.cities["Washington"] = City("Washington", DiseaseColor.BLUE, ["Atlanta", "Montreal", "New York", "Miami"])
        self.state.cities["San Francisco"] = City("San Francisco", DiseaseColor.BLUE, ["Chicago", "Los Angeles", "Tokyo", "Manila"])
        self.state.cities["London"] = City("London", DiseaseColor.BLUE, ["New York", "Madrid", "Paris", "Essen"])
        self.state.cities["Madrid"] = City("Madrid", DiseaseColor.BLUE, ["New York", "London", "Paris", "Algiers", "Sao Paulo"])
        self.state.cities["Paris"] = City("Paris", DiseaseColor.BLUE, ["London", "Madrid", "Algiers", "Milan", "Essen"])
        self.state.cities["Essen"] = City("Essen", DiseaseColor.BLUE, ["London", "Paris", "Milan", "St. Petersburg"])
        
        # Yellow cities
        self.state.cities["Los Angeles"] = City("Los Angeles", DiseaseColor.YELLOW, ["San Francisco", "Chicago", "Mexico City", "Sydney"])
        self.state.cities["Mexico City"] = City("Mexico City", DiseaseColor.YELLOW, ["Los Angeles", "Chicago", "Miami", "Lima", "Bogota"])
        self.state.cities["Miami"] = City("Miami", DiseaseColor.YELLOW, ["Atlanta", "Washington", "Mexico City", "Bogota"])
        self.state.cities["Bogota"] = City("Bogota", DiseaseColor.YELLOW, ["Miami", "Mexico City", "Lima", "Sao Paulo", "Buenos Aires"])
        self.state.cities["Lima"] = City("Lima", DiseaseColor.YELLOW, ["Mexico City", "Bogota", "Santiago"])
        self.state.cities["Santiago"] = City("Santiago", DiseaseColor.YELLOW, ["Lima"])
        self.state.cities["Sao Paulo"] = City("Sao Paulo", DiseaseColor.YELLOW, ["Bogota", "Buenos Aires", "Madrid", "Lagos"])
        self.state.cities["Buenos Aires"] = City("Buenos Aires", DiseaseColor.YELLOW, ["Bogota", "Sao Paulo"])
        self.state.cities["Lagos"] = City("Lagos", DiseaseColor.YELLOW, ["Sao Paulo", "Kinshasa", "Khartoum"])
        self.state.cities["Kinshasa"] = City("Kinshasa", DiseaseColor.YELLOW, ["Lagos", "Khartoum", "Johannesburg"])
        
        # Black cities
        self.state.cities["Algiers"] = City("Algiers", DiseaseColor.BLACK, ["Madrid", "Paris", "Istanbul", "Cairo"])
        self.state.cities["Cairo"] = City("Cairo", DiseaseColor.BLACK, ["Algiers", "Istanbul", "Baghdad", "Khartoum"])
        self.state.cities["Istanbul"] = City("Istanbul", DiseaseColor.BLACK, ["Milan", "St. Petersburg", "Moscow", "Baghdad", "Cairo", "Algiers"])
        self.state.cities["Moscow"] = City("Moscow", DiseaseColor.BLACK, ["St. Petersburg", "Istanbul", "Tehran"])
        self.state.cities["Tehran"] = City("Tehran", DiseaseColor.BLACK, ["Moscow", "Baghdad", "Karachi", "Delhi"])
        self.state.cities["Baghdad"] = City("Baghdad", DiseaseColor.BLACK, ["Istanbul", "Cairo", "Tehran", "Karachi", "Riyadh"])
        self.state.cities["Riyadh"] = City("Riyadh", DiseaseColor.BLACK, ["Baghdad", "Karachi", "Cairo"])
        self.state.cities["Karachi"] = City("Karachi", DiseaseColor.BLACK, ["Tehran", "Baghdad", "Riyadh", "Mumbai", "Delhi"])
        self.state.cities["Mumbai"] = City("Mumbai", DiseaseColor.BLACK, ["Karachi", "Delhi", "Chennai"])
        self.state.cities["Delhi"] = City("Delhi", DiseaseColor.BLACK, ["Tehran", "Karachi", "Mumbai", "Chennai", "Kolkata"])
        
        # Red cities
        self.state.cities["Beijing"] = City("Beijing", DiseaseColor.RED, ["Seoul", "Shanghai"])
        self.state.cities["Seoul"] = City("Seoul", DiseaseColor.RED, ["Beijing", "Shanghai", "Tokyo"])
        self.state.cities["Tokyo"] = City("Tokyo", DiseaseColor.RED, ["Seoul", "Shanghai", "Osaka", "San Francisco"])
        self.state.cities["Shanghai"] = City("Shanghai", DiseaseColor.RED, ["Beijing", "Seoul", "Tokyo", "Taipei", "Hong Kong"])
        self.state.cities["Hong Kong"] = City("Hong Kong", DiseaseColor.RED, ["Shanghai", "Taipei", "Manila", "Ho Chi Minh City", "Bangkok", "Kolkata"])
        self.state.cities["Taipei"] = City("Taipei", DiseaseColor.RED, ["Shanghai", "Osaka", "Manila", "Hong Kong"])
        self.state.cities["Osaka"] = City("Osaka", DiseaseColor.RED, ["Tokyo", "Taipei"])
        self.state.cities["Manila"] = City("Manila", DiseaseColor.RED, ["Taipei", "Hong Kong", "Ho Chi Minh City", "Sydney", "San Francisco"])
        self.state.cities["Ho Chi Minh City"] = City("Ho Chi Minh City", DiseaseColor.RED, ["Hong Kong", "Manila", "Jakarta", "Bangkok"])
        self.state.cities["Jakarta"] = City("Jakarta", DiseaseColor.RED, ["Ho Chi Minh City", "Bangkok", "Chennai", "Sydney"])
        
    def _create_infection_deck(self):
        """Create and shuffle the infection deck"""
        self.state.infection_deck = [InfectionCard(city) for city in self.state.cities.keys()]
        random.shuffle(self.state.infection_deck)
        
    def _create_player_deck(self):
        """Create and shuffle the player deck with epidemic cards"""
        # Create city cards
        city_cards = [PlayerCard(city) for city in self.state.cities.keys()]
        
        # Add event cards
        event_cards = [PlayerCard(event.value, is_event=True) for event in EventCard]
        
        # Combine and shuffle
        player_cards = city_cards + event_cards
        random.shuffle(player_cards)
        
        # Add epidemic cards based on difficulty
        # In the official game, the deck is divided into equal piles, and one epidemic
        # card is shuffled into each pile, then the piles are stacked
        cards_per_pile = len(player_cards) // self.num_epidemic_cards
        piles = []
        
        for i in range(self.num_epidemic_cards):
            start_idx = i * cards_per_pile
            end_idx = (i + 1) * cards_per_pile if i < self.num_epidemic_cards - 1 else len(player_cards)
            pile = player_cards[start_idx:end_idx]
            pile.append(PlayerCard("Epidemic", is_epidemic=True))
            random.shuffle(pile)
            piles.append(pile)
        
        # Combine the piles to form the final deck
        self.state.player_deck = []
        for pile in piles:
            self.state.player_deck.extend(pile)
    
    def _create_players(self):
        """Create the players with random roles and place them in Atlanta"""
        # Available roles
        available_roles = list(PlayerRole)
        random.shuffle(available_roles)
        
        # Create players
        for i in range(self.num_players):
            role = available_roles[i]
            player = Player(f"Player {i+1}", role, "Atlanta")
            self.state.players.append(player)
    
    def _deal_initial_cards(self):
        """Deal initial cards to players"""
        # Number of cards per player based on player count
        cards_per_player = {
            2: 4,
            3: 3,
            4: 2
        }[self.num_players]
        
        # Deal cards to each player
        for player in self.state.players:
            for _ in range(cards_per_player):
                if self.state.player_deck:
                    card = self.state.player_deck.pop()
                    player.hand.append(card.name)
    
    def _perform_initial_infections(self):
        """Perform initial infections (3 cities with 3 cubes, 3 with 2, 3 with 1)"""
        for num_cubes in [3, 2, 1]:
            for _ in range(3):
                if self.state.infection_deck:
                    infection_card = self.state.infection_deck.pop()
                    city = self.state.cities[infection_card.city_name]
                    
                    # Add cubes to the city
                    for _ in range(num_cubes):
                        self._add_disease_cube(city, city.color)
                    
                    # Add card to discard pile
                    self.state.infection_discard.append(infection_card)
    
    def _add_disease_cube(self, city: City, color: DiseaseColor) -> bool:
        """Add a disease cube to a city, handling outbreaks if necessary"""
        # Check if disease is eradicated
        if self.state.disease_status[color] == DiseaseStatus.ERADICATED:
            return True
        
        # Check if we have cubes available
        if self.state.disease_cubes[color] <= 0:
            return False
        
        # Try to add cube to city
        success = city.add_disease_cube(color)
        
        if success:
            # Cube was added, decrease available cubes
            self.state.disease_cubes[color] -= 1
            return True
        else:
            # Outbreak occurred (4th cube)
            return self._handle_outbreak(city, color)
    
    def _handle_outbreak(self, city: City, color: DiseaseColor) -> bool:
        """Handle an outbreak in a city"""
        # Increment outbreak counter
        self.state.outbreak_counter += 1
        
        print(f"⚠️ Outbreak in {city.name}! ({self.state.outbreak_counter}/8)")
        
        # Check for game over
        if self.state.outbreak_counter >= 8:
            return False
        
        # To avoid chain reactions to the same city, we'll keep track of cities already affected
        # by this chain of outbreaks
        outbreak_chain = set([city.name])
        
        # Add one cube of matching color to all connected cities
        for connected_city_name in city.connections:
            connected_city = self.state.cities[connected_city_name]
            
            # Skip if already in the outbreak chain
            if connected_city_name in outbreak_chain:
                continue
                
            # Add cube to connected city, potentially triggering more outbreaks
            success = self._add_disease_cube(connected_city, color)
            
            if not success:
                return False
        
        return True
    
    def play_turn(self, actions=None):
        """
        Play a turn for the current player
        
        Args:
            actions: List of action dictionaries if pre-defined, otherwise LLM will be used
        """
        current_player = self.state.get_current_player()
        print(f"\n{Colors.BOLD}🎮 {current_player.name}'s Turn ({current_player.role.value}){Colors.ENDC}")
        
        # Create LLM agent if needed
        if not hasattr(current_player, 'agent'):
            from llm_agent import LLMAgent
            current_player.agent = LLMAgent(current_player)
        
        # 1. Do up to 4 actions
        for _ in range(4):
            if current_player.action_points <= 0:
                break
                
            # Display current game state
            print(f"\n{self.state.game_state_description()}")
            
            # Get action from LLM agent or use predefined actions
            if actions and len(actions) > 0:
                action_result = actions.pop(0)
                print(f"Using predefined action: {action_result['action_type']}")
            else:
                # Get action from LLM agent
                try:
                    print(f"\n{Colors.BOLD}Getting action from {current_player.name}...{Colors.ENDC}")
                    action_result = current_player.agent.get_action(self.state)
                    print(f"Action: {action_result['action_type']}")
                    if 'explanation' in action_result:
                        print(f"Reasoning: {action_result['explanation']}")
                except Exception as e:
                    print(f"{Colors.RED}Error getting action from LLM agent: {str(e)}{Colors.ENDC}")
                    action_result = {"action_type": "pass_turn", "reason": f"Error: {str(e)}"}
            
            # Apply the action and update state
            success, message = self._apply_action(action_result)
            if success:
                current_player.action_points -= 1
                print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")
            else:
                print(f"{Colors.RED}✗ {message}{Colors.ENDC}")
            
            # Check if game is over after action
            game_over, reason = self.state.is_game_over()
            if game_over:
                print(f"\n{reason}")
                return game_over, reason
        
        # 2. Draw 2 player cards
        drawn_cards = []
        epidemics = 0
        
        for _ in range(2):
            # Check if player deck is empty
            if not self.state.player_deck:
                print("\n🚨 Game over: Player deck is empty!")
                return True, "Defeat! The player deck is empty."
            
            # Draw a card
            card = self.state.player_deck.pop()
            
            if card.is_epidemic:
                # Handle epidemic
                epidemics += 1
                print(f"\n⚠️ {Colors.RED}{Colors.BOLD}EPIDEMIC!{Colors.ENDC}")
                drawn_cards.append("Epidemic")
                
                # Resolve epidemic:
                # 1. Increase infection rate
                self.state.infection_rate_index = min(self.state.infection_rate_index + 1, len(self.state.infection_rates) - 1)
                
                # 2. Infect: Draw bottom card from infection deck
                if self.state.infection_deck:
                    epidemic_city_card = self.state.infection_deck[0]  # Bottom card
                    self.state.infection_deck.pop(0)
                    
                    epidemic_city = self.state.cities[epidemic_city_card.city_name]
                    print(f"Epidemic in {epidemic_city.name}!")
                    
                    # Add 3 cubes of the city's color
                    for _ in range(3):
                        self._add_disease_cube(epidemic_city, epidemic_city.color)
                    
                    # Add card to infection discard
                    self.state.infection_discard.append(epidemic_city_card)
                
                # 3. Intensify: Shuffle infection discard and put on top of infection deck
                random.shuffle(self.state.infection_discard)
                self.state.infection_deck = self.state.infection_discard + self.state.infection_deck
                self.state.infection_discard = []
            else:
                # Regular card draw
                drawn_cards.append(card.name)
                current_player.add_card(card.name)
                
                # Check hand limit (7 cards)
                if len(current_player.hand) > 7:
                    # TODO: Ask player which card to discard
                    # For now, just discard the first card
                    discard_card = current_player.hand[0]
                    current_player.remove_card(discard_card)
                    
                    print(f"{current_player.name} discards {discard_card} (hand limit reached)")
                    self.state.player_discard.append(PlayerCard(discard_card, 
                                                               is_event="Event:" in discard_card))
        
        print(f"{current_player.name} drew: {', '.join(drawn_cards)}")
        
        # Check if game is over after drawing cards
        game_over, reason = self.state.is_game_over()
        if game_over:
            print(f"\n{reason}")
            return game_over, reason
        
        # 3. Infect cities
        if not self.state.quiet_night_active:
            self._infect_cities()
            
            # Reset quiet night if it was active
            self.state.quiet_night_active = False
        else:
            print("🌙 One Quiet Night event is active - skipping infection phase!")
            self.state.quiet_night_active = False
        
        # Check if game is over after infections
        game_over, reason = self.state.is_game_over()
        if game_over:
            print(f"\n{reason}")
            return game_over, reason
        
        # Advance to next player
        self.state.next_player_turn()
        
        return False, ""
    
    def _apply_action(self, action):
        """Apply a player action to the game state and return (success, message)"""
        action_type = action.get("action_type", "")
        current_player = self.state.get_current_player()
        
        # Pass turn
        if action_type == "pass_turn":
            reason = action.get("reason", "No reason provided")
            return True, f"{current_player.name} passes their action. Reason: {reason}"
        
        # Movement actions
        elif action_type == "move":
            destination = action.get("destination")
            movement_type = action.get("movement_type", "regular")
            
            if not destination:
                return False, "No destination specified for movement"
            
            # Check if destination exists
            if destination not in self.state.cities:
                return False, f"Invalid destination: {destination}"
            
            # Handle different movement types
            if movement_type == "regular":
                # Check if destination is connected to current location
                if destination not in self.state.cities[current_player.location].connections:
                    return False, f"{destination} is not connected to {current_player.location}"
                
                # Move player
                current_player.location = destination
                
                # If player is Medic, automatically remove cubes of cured diseases
                if current_player.role == PlayerRole.MEDIC:
                    for color, status in self.state.disease_status.items():
                        if status == DiseaseStatus.CURED:
                            city = self.state.cities[destination]
                            cubes_removed = 0
                            while city.disease_cubes[color] > 0:
                                city.remove_disease_cube(color)
                                self.state.disease_cubes[color] += 1  # Return to supply
                                cubes_removed += 1
                            if cubes_removed > 0:
                                print(f"Medic automatically removed {cubes_removed} {color.value} cubes from {destination}")
                
                return True, f"{current_player.name} moved to {destination}"
                
            elif movement_type == "direct_flight":
                # Check if player has the destination card
                if not current_player.has_city_card(destination):
                    return False, f"{current_player.name} doesn't have the {destination} card for direct flight"
                
                # Discard the card and move
                current_player.remove_card(destination)
                self.state.player_discard.append(PlayerCard(destination))
                
                # Update location
                current_player.location = destination
                
                # Medic special ability for cured diseases
                if current_player.role == PlayerRole.MEDIC:
                    for color, status in self.state.disease_status.items():
                        if status == DiseaseStatus.CURED:
                            city = self.state.cities[destination]
                            cubes_removed = 0
                            while city.disease_cubes[color] > 0:
                                city.remove_disease_cube(color)
                                self.state.disease_cubes[color] += 1
                                cubes_removed += 1
                            if cubes_removed > 0:
                                print(f"Medic automatically removed {cubes_removed} {color.value} cubes from {destination}")
                
                return True, f"{current_player.name} took a direct flight to {destination}"
                
            elif movement_type == "charter_flight":
                # Check if player has their current location card
                current_location = current_player.location
                if not current_player.has_city_card(current_location):
                    return False, f"{current_player.name} doesn't have the {current_location} card for charter flight"
                
                # Discard the card and move
                current_player.remove_card(current_location)
                self.state.player_discard.append(PlayerCard(current_location))
                
                # Update location
                current_player.location = destination
                
                # Medic special ability
                if current_player.role == PlayerRole.MEDIC:
                    for color, status in self.state.disease_status.items():
                        if status == DiseaseStatus.CURED:
                            city = self.state.cities[destination]
                            cubes_removed = 0
                            while city.disease_cubes[color] > 0:
                                city.remove_disease_cube(color)
                                self.state.disease_cubes[color] += 1
                                cubes_removed += 1
                            if cubes_removed > 0:
                                print(f"Medic automatically removed {cubes_removed} {color.value} cubes from {destination}")
                
                return True, f"{current_player.name} took a charter flight to {destination}"
                
            elif movement_type == "shuttle_flight":
                # Check if current location has a research station
                current_location = current_player.location
                if not self.state.cities[current_location].has_research_station:
                    return False, f"{current_location} does not have a research station"
                
                # Check if destination has a research station
                if not self.state.cities[destination].has_research_station:
                    return False, f"{destination} does not have a research station"
                
                # Move player
                current_player.location = destination
                
                # Medic special ability
                if current_player.role == PlayerRole.MEDIC:
                    for color, status in self.state.disease_status.items():
                        if status == DiseaseStatus.CURED:
                            city = self.state.cities[destination]
                            cubes_removed = 0
                            while city.disease_cubes[color] > 0:
                                city.remove_disease_cube(color)
                                self.state.disease_cubes[color] += 1
                                cubes_removed += 1
                            if cubes_removed > 0:
                                print(f"Medic automatically removed {cubes_removed} {color.value} cubes from {destination}")
                
                return True, f"{current_player.name} took a shuttle flight to {destination}"
                
            elif movement_type == "operations_expert":
                # Check if player is Operations Expert
                if current_player.role != PlayerRole.OPERATIONS_EXPERT:
                    return False, "Only the Operations Expert can use this movement type"
                
                # Check if current location has a research station
                if not self.state.cities[current_player.location].has_research_station:
                    return False, "Operations Expert must be at a research station to use this ability"
                
                # Check if player has any city card to discard
                if not current_player.hand:
                    return False, "Operations Expert needs a city card to discard for this ability"
                
                # For simplicity, just discard the first card in hand
                card_to_discard = current_player.hand[0]
                current_player.remove_card(card_to_discard)
                self.state.player_discard.append(PlayerCard(card_to_discard))
                
                # Move player
                current_player.location = destination
                
                # Medic special ability
                if current_player.role == PlayerRole.MEDIC:
                    for color, status in self.state.disease_status.items():
                        if status == DiseaseStatus.CURED:
                            city = self.state.cities[destination]
                            cubes_removed = 0
                            while city.disease_cubes[color] > 0:
                                city.remove_disease_cube(color)
                                self.state.disease_cubes[color] += 1
                                cubes_removed += 1
                            if cubes_removed > 0:
                                print(f"Medic automatically removed {cubes_removed} {color.value} cubes from {destination}")
                
                return True, f"Operations Expert {current_player.name} moved to {destination} by discarding {card_to_discard}"
            
            else:
                return False, f"Unknown movement type: {movement_type}"
        
        # Treat disease
        elif action_type == "treat_disease":
            disease_color_str = action.get("disease_color")
            if not disease_color_str:
                return False, "No disease color specified for treatment"
            
            # Convert string to enum value
            try:
                disease_color = getattr(DiseaseColor, disease_color_str.upper())
            except (AttributeError, ValueError):
                return False, f"Invalid disease color: {disease_color_str}"
            
            # Check if there are cubes to remove
            city = self.state.cities[current_player.location]
            if city.disease_cubes[disease_color] <= 0:
                return False, f"No {disease_color.value} disease cubes in {city.name}"
            
            # Check if disease is cured
            is_cured = self.state.disease_status[disease_color] != DiseaseStatus.ACTIVE
            
            # Special handling for Medic (remove all cubes of one color)
            if current_player.role == PlayerRole.MEDIC:
                cubes_removed = city.disease_cubes[disease_color]
                for _ in range(cubes_removed):
                    city.remove_disease_cube(disease_color)
                    self.state.disease_cubes[disease_color] += 1  # Return cubes to supply
                
                return True, f"Medic {current_player.name} removed all {cubes_removed} {disease_color.value} cubes from {city.name}"
            
            # Regular treatment (if cured, remove all cubes)
            if is_cured:
                cubes_removed = city.disease_cubes[disease_color]
                for _ in range(cubes_removed):
                    city.remove_disease_cube(disease_color)
                    self.state.disease_cubes[disease_color] += 1
                
                return True, f"{current_player.name} removed all {cubes_removed} {disease_color.value} cubes from {city.name} (disease is cured)"
            else:
                # Remove just one cube
                city.remove_disease_cube(disease_color)
                self.state.disease_cubes[disease_color] += 1
                
                return True, f"{current_player.name} removed 1 {disease_color.value} cube from {city.name}"
        
        # Build research station
        elif action_type == "build_research_station":
            city = self.state.cities[current_player.location]
            
            # Check if research station already exists
            if city.has_research_station:
                return False, f"{city.name} already has a research station"
            
            # Check if we've reached the maximum number of research stations
            if self.state.placed_research_stations >= self.state.total_research_stations:
                return False, f"Maximum number of research stations ({self.state.total_research_stations}) already built"
            
            use_ops_expert = action.get("use_operations_expert", False)
            
            # Operations Expert can build without a card
            if use_ops_expert and current_player.role == PlayerRole.OPERATIONS_EXPERT:
                city.has_research_station = True
                self.state.placed_research_stations += 1
                return True, f"Operations Expert {current_player.name} built a research station in {city.name}"
            
            # Regular build requires the matching city card
            if not current_player.has_city_card(city.name):
                return False, f"{current_player.name} doesn't have the {city.name} card to build a research station"
            
            # Discard the card and build
            current_player.remove_card(city.name)
            self.state.player_discard.append(PlayerCard(city.name))
            
            city.has_research_station = True
            self.state.placed_research_stations += 1
            
            return True, f"{current_player.name} built a research station in {city.name}"
        
        # Share knowledge
        elif action_type == "share_knowledge":
            card_name = action.get("card_name")
            player_name = action.get("player_name")
            direction = action.get("direction", "give")  # "give" or "take"
            
            if not card_name:
                return False, "No card specified for knowledge sharing"
            
            if not player_name:
                return False, "No target player specified for knowledge sharing"
            
            # Find target player
            target_player = None
            for player in self.state.players:
                if player.name == player_name:
                    target_player = player
                    break
            
            if not target_player:
                return False, f"Player {player_name} not found"
            
            # Check if players are in same location
            if current_player.location != target_player.location:
                return False, f"{current_player.name} and {target_player.name} must be in the same city to share knowledge"
            
            # Handle Researcher's special ability
            is_researcher = (current_player.role == PlayerRole.RESEARCHER and direction == "give") or \
                             (target_player.role == PlayerRole.RESEARCHER and direction == "take")
            
            # Determine giver and receiver based on direction
            if direction == "give":
                giver, receiver = current_player, target_player
            else:  # "take"
                giver, receiver = target_player, current_player
            
            # Normal sharing requires card to match current location
            if not is_researcher and card_name != giver.location:
                return False, f"Can only share {giver.location} cards when not using Researcher ability"
            
            # Check if giver has the card
            if not giver.has_city_card(card_name):
                return False, f"{giver.name} doesn't have the {card_name} card to share"
            
            # Transfer the card
            giver.remove_card(card_name)
            receiver.add_card(card_name)
            
            if is_researcher:
                return True, f"Researcher shared {card_name} card from {giver.name} to {receiver.name}"
            else:
                return True, f"{giver.name} shared {card_name} card with {receiver.name}"
        
        # Discover cure
        elif action_type == "discover_cure":
            disease_color_str = action.get("disease_color")
            card_names = action.get("card_names", [])
            
            if not disease_color_str:
                return False, "No disease color specified for cure discovery"
            
            # Convert string to enum value
            try:
                disease_color = getattr(DiseaseColor, disease_color_str.upper())
            except (AttributeError, ValueError):
                return False, f"Invalid disease color: {disease_color_str}"
            
            # Check if disease is already cured
            if self.state.disease_status[disease_color] != DiseaseStatus.ACTIVE:
                return False, f"The {disease_color.value} disease is already cured"
            
            # Check if at a research station
            if not self.state.cities[current_player.location].has_research_station:
                return False, f"{current_player.name} must be at a research station to discover a cure"
            
            # Determine required number of cards (Scientist needs only 4)
            cards_required = 4 if current_player.role == PlayerRole.SCIENTIST else 5
            
            # Check if enough cards are provided
            if len(card_names) < cards_required:
                return False, f"Need {cards_required} cards of {disease_color.value} color to discover a cure (only {len(card_names)} provided)"
            
            # Check if player has all the specified cards
            for card in card_names:
                if not current_player.has_city_card(card):
                    return False, f"{current_player.name} doesn't have the {card} card"
            
            # Check if all cards are of the correct color (simplified - assuming city name corresponds to color)
            for card in card_names:
                if card in self.state.cities and self.state.cities[card].color != disease_color:
                    return False, f"{card} is not a {disease_color.value} city card"
            
            # Discard the cards and cure the disease
            for card in card_names:
                current_player.remove_card(card)
                self.state.player_discard.append(PlayerCard(card))
            
            self.state.disease_status[disease_color] = DiseaseStatus.CURED
            
            # If Medic is in play, automatically remove cubes of the cured disease
            for player in self.state.players:
                if player.role == PlayerRole.MEDIC:
                    city = self.state.cities[player.location]
                    cubes_removed = 0
                    while city.disease_cubes[disease_color] > 0:
                        city.remove_disease_cube(disease_color)
                        self.state.disease_cubes[disease_color] += 1
                        cubes_removed += 1
                    if cubes_removed > 0:
                        print(f"Medic automatically removed {cubes_removed} {disease_color.value} cubes from {player.location}")
            
            return True, f"{current_player.name} discovered a cure for the {disease_color.value} disease!"
        
        # Play event
        elif action_type == "play_event":
            event_name = action.get("event_name")
            if not event_name:
                return False, "No event card specified"
            
            # Check if player has the event card
            if event_name not in current_player.hand:
                return False, f"{current_player.name} doesn't have the {event_name} event card"
            
            # Handle different event cards
            if event_name == "Airlift":
                target_player_name = action.get("target_player")
                destination = action.get("target_city")
                
                if not target_player_name or not destination:
                    return False, "Airlift requires target player and destination"
                
                # Find target player
                target_player = None
                for player in self.state.players:
                    if player.name == target_player_name:
                        target_player = player
                        break
                
                if not target_player:
                    return False, f"Player {target_player_name} not found"
                
                if destination not in self.state.cities:
                    return False, f"City {destination} not found"
                
                # Move the player directly to the destination
                target_player.location = destination
                
                # Remove the event card
                current_player.remove_card(event_name)
                self.state.player_discard.append(PlayerCard(event_name, is_event=True))
                
                # Medic special ability if applicable
                if target_player.role == PlayerRole.MEDIC:
                    for color, status in self.state.disease_status.items():
                        if status == DiseaseStatus.CURED:
                            city = self.state.cities[destination]
                            cubes_removed = 0
                            while city.disease_cubes[color] > 0:
                                city.remove_disease_cube(color)
                                self.state.disease_cubes[color] += 1
                                cubes_removed += 1
                            if cubes_removed > 0:
                                print(f"Medic automatically removed {cubes_removed} {color.value} cubes from {destination}")
                
                return True, f"{current_player.name} used Airlift to move {target_player.name} to {destination}"
                
            elif event_name == "Government Grant":
                city_name = action.get("target_city")
                
                if not city_name:
                    return False, "Government Grant requires a target city"
                
                if city_name not in self.state.cities:
                    return False, f"City {city_name} not found"
                
                city = self.state.cities[city_name]
                
                # Check if research station already exists
                if city.has_research_station:
                    return False, f"{city_name} already has a research station"
                
                # Check if maximum research stations reached
                if self.state.placed_research_stations >= self.state.total_research_stations:
                    return False, f"Maximum number of research stations ({self.state.total_research_stations}) already built"
                
                # Build a research station
                city.has_research_station = True
                self.state.placed_research_stations += 1
                
                # Remove the event card
                current_player.remove_card(event_name)
                self.state.player_discard.append(PlayerCard(event_name, is_event=True))
                
                return True, f"{current_player.name} used Government Grant to build a research station in {city_name}"
                
            elif event_name == "One Quiet Night":
                # Skip the next infection phase
                self.state.quiet_night_active = True
                
                # Remove the event card
                current_player.remove_card(event_name)
                self.state.player_discard.append(PlayerCard(event_name, is_event=True))
                
                return True, f"{current_player.name} played One Quiet Night - next infection phase will be skipped"
                
            # TODO: Implement other event cards (Forecast, Resilient Population)
                
            return False, f"Event card {event_name} not fully implemented yet"
        
        # Communicate with other players
        elif action_type == "communicate":
            message = action.get("message")
            target_player = action.get("target_player")
            
            if not message:
                return False, "No message provided for communication"
            
            if not target_player:
                return False, "No target player specified for communication"
            
            if target_player == "all":
                # Send to all players in the same location
                recipients = self.state.broadcast_message(current_player, message)
                if not recipients:
                    return False, "No other players in your location to communicate with"
                
                recipient_names = [p.name for p in recipients]
                return True, f"{current_player.name} sent a message to all players in {current_player.location}: {', '.join(recipient_names)}"
            else:
                # Send to a specific player
                target = None
                for player in self.state.players:
                    if player.name == target_player:
                        target = player
                        break
                
                if not target:
                    return False, f"Player {target_player} not found"
                
                success = self.state.send_message(current_player, target, message)
                if not success:
                    return False, f"Cannot communicate with {target.name} - must be in the same location"
                
                return True, f"{current_player.name} sent a message to {target.name}"
        
        else:
            return False, f"Unknown action type: {action_type}"
    
    def _infect_cities(self):
        """Draw infection cards and add disease cubes"""
        infection_rate = self.state.infection_rates[self.state.infection_rate_index]
        print(f"\n🦠 Infecting {infection_rate} cities...")
        
        for _ in range(infection_rate):
            if not self.state.infection_deck:
                # Shuffle discard if needed
                if self.state.infection_discard:
                    print("Reshuffling infection discard pile...")
                    self.state.infection_deck = self.state.infection_discard
                    self.state.infection_discard = []
                    random.shuffle(self.state.infection_deck)
                else:
                    print("No more infection cards!")
                    break
            
            # Draw an infection card
            infection_card = self.state.infection_deck.pop()
            city = self.state.cities[infection_card.city_name]
            
            print(f"Infecting {city.name} with {city.color.value} disease")
            
            # Add a disease cube of the city's color
            self._add_disease_cube(city, city.color)
            
            # Add card to discard pile
            self.state.infection_discard.append(infection_card)
    
    def run_game(self, max_turns=10):
        """Run the game for a maximum number of turns, or until game ends"""
        print(f"{Colors.BOLD}🌍 Starting Pandemic game with {self.num_players} players at {self.difficulty} difficulty{Colors.ENDC}")
        print(f"Epidemic cards: {self.num_epidemic_cards}")
        
        turn_counter = 0
        game_over = False
        reason = ""
        
        while not game_over and turn_counter < max_turns:
            turn_counter += 1
            print(f"\n{Colors.BOLD}===== TURN {turn_counter} ====={Colors.ENDC}")
            
            game_over, reason = self.play_turn()
        
        if game_over:
            print(f"\n{Colors.BOLD}Game over after {turn_counter} turns: {reason}{Colors.ENDC}")
        else:
            print(f"\n{Colors.BOLD}Maximum turn limit ({max_turns}) reached.{Colors.ENDC}")
            
            # Check the current state to see if victory was achieved
            all_cured = all(status != DiseaseStatus.ACTIVE for status in self.state.disease_status.values())
            if all_cured:
                print(f"{Colors.GREEN}Victory! All diseases have been cured.{Colors.ENDC}")
            else:
                print(f"{Colors.YELLOW}The game did not reach a conclusion. Current state:{Colors.ENDC}")
                print(self.state.game_state_description()) 