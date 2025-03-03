import os
import random
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set

class DiseaseStatus(Enum):
    ACTIVE = "Active"
    CURED = "Cured"
    ERADICATED = "Eradicated"

class DiseaseColor(Enum):
    BLUE = "Blue"
    YELLOW = "Yellow"
    BLACK = "Black"
    RED = "Red"

class EventCard(Enum):
    AIRLIFT = "Airlift"
    GOVERNMENT_GRANT = "Government Grant"
    FORECAST = "Forecast"
    RESILIENT_POPULATION = "Resilient Population"
    ONE_QUIET_NIGHT = "One Quiet Night"

class PlayerRole(Enum):
    MEDIC = "Medic"
    SCIENTIST = "Scientist"
    RESEARCHER = "Researcher"
    OPERATIONS_EXPERT = "Operations Expert"
    DISPATCHER = "Dispatcher"
    QUARANTINE_SPECIALIST = "Quarantine Specialist"
    CONTINGENCY_PLANNER = "Contingency Planner"

class City:
    def __init__(self, name: str, color: DiseaseColor, connections: List[str] = None):
        self.name = name
        self.color = color
        self.connections = connections or []
        self.disease_cubes = {
            DiseaseColor.BLUE: 0,
            DiseaseColor.YELLOW: 0,
            DiseaseColor.BLACK: 0,
            DiseaseColor.RED: 0
        }
        self.has_research_station = False
    
    def add_disease_cube(self, color: DiseaseColor) -> bool:
        """Adds a disease cube to the city. Returns False if outbreak occurs (4th cube)"""
        if self.disease_cubes[color] >= 3:
            return False  # Outbreak
        self.disease_cubes[color] += 1
        return True
    
    def remove_disease_cube(self, color: DiseaseColor) -> bool:
        """Removes a disease cube from the city. Returns False if no cubes to remove."""
        if self.disease_cubes[color] <= 0:
            return False
        self.disease_cubes[color] -= 1
        return True
    
    def get_total_disease_cubes(self) -> int:
        """Returns the total number of disease cubes in the city"""
        return sum(self.disease_cubes.values())
    
    def __str__(self):
        return f"{self.name} ({self.color.value})"

class Player:
    def __init__(self, name: str, role: PlayerRole, location: str):
        self.name = name
        self.role = role
        self.location = location  # City name
        self.hand: List[str] = []  # List of city cards and event cards
        self.action_points = 4  # Each player gets 4 actions per turn
        self.messages = []  # Store messages received from other players
    
    def add_card(self, card: str):
        self.hand.append(card)
    
    def remove_card(self, card: str) -> bool:
        if card in self.hand:
            self.hand.remove(card)
            return True
        return False
    
    def has_city_card(self, city_name: str) -> bool:
        return city_name in self.hand
    
    def __str__(self):
        return f"{self.name} ({self.role.value}) at {self.location}"

class InfectionCard:
    def __init__(self, city_name: str):
        self.city_name = city_name
    
    def __str__(self):
        return f"Infection: {self.city_name}"

class PlayerCard:
    def __init__(self, name: str, is_epidemic: bool = False, is_event: bool = False):
        self.name = name
        self.is_epidemic = is_epidemic
        self.is_event = is_event
    
    @property
    def is_city(self):
        return not (self.is_epidemic or self.is_event)
    
    def __str__(self):
        if self.is_epidemic:
            return "EPIDEMIC!"
        elif self.is_event:
            return f"Event: {self.name}"
        else:
            return f"City: {self.name}" 