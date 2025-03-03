import os
import random
from enum import Enum
from typing import List, Dict, Tuple, Optional

class SystemStatus(Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    DAMAGED = "Damaged"

class Location(Enum):
    BRIDGE = "Bridge"
    ENGINEERING = "Engineering"
    WEAPONS_BAY = "Weapons Bay"
    SCIENCE_LAB = "Science Lab"
    TELEPORTER = "Teleporter"
    SICK_BAY = "Sick Bay"
    COMM_CENTER = "Communications Center"
    HOLODECK = "Holodeck"

class SkillType(Enum):
    TACTICAL = "Tactical"
    ENGINEERING = "Engineering"
    SCIENCE = "Science"
    MEDICAL = "Medical"
    LEADERSHIP = "Leadership"

class CharacterRole(Enum):
    CAPTAIN = "Captain"
    ENGINEER = "Engineer"
    SCIENCE_OFFICER = "Science Officer"
    TACTICAL_OFFICER = "Tactical Officer"
    MEDICAL_OFFICER = "Medical Officer"
    COMMUNICATIONS_OFFICER = "Communications Officer"

class AlertLevel(Enum):
    YELLOW = "Yellow Alert"
    ORANGE = "Orange Alert"
    RED = "Red Alert"

class Threat:
    def __init__(self, name: str, description: str, difficulty: int):
        self.name = name
        self.description = description
        self.difficulty = difficulty
        self.active = True
    
    def __str__(self):
        return f"{self.name} ({self.difficulty}): {self.description}"

class Character:
    def __init__(self, 
                 name: str, 
                 role: CharacterRole, 
                 skills: Dict[SkillType, int],
                 special_ability: str,
                 location: Location):
        self.name = name
        self.role = role
        self.skills = skills
        self.special_ability = special_ability
        self.location = location
        self.action_points = 4  # Standard action points per turn (board game standard)
        
    def __str__(self):
        return f"{self.name} ({self.role.value}) at {self.location.value}"

class CrisisCard:
    def __init__(self, name: str, description: str, effect_type: str, severity: int):
        self.name = name
        self.description = description
        self.effect_type = effect_type  # system_damage, new_threat, action_restriction, etc.
        self.severity = severity  # 1-3, with 3 being most severe
    
    def __str__(self):
        return f"{self.name}: {self.description} (Severity: {self.severity})" 