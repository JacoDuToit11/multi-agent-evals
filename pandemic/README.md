# Pandemic - LLM Agent Simulation

A simulation of the cooperative board game "Pandemic" using LLM agents.

## Overview

This project simulates the board game "Pandemic" using LLM agents to control the players. The goal is to discover cures for all four diseases before:
- The player deck runs out of cards
- Too many outbreaks occur (8+)
- Running out of disease cubes of any color

## Game Mechanics

- **Players**: Each player has a unique role with special abilities
- **Diseases**: Four different diseases (blue, yellow, black, red) spread across the globe
- **Action Points**: Players spend 4 action points per turn
- **Research Stations**: Build stations to facilitate movement and cure discovery
- **Outbreaks**: When a city would receive a 4th disease cube, an outbreak occurs
- **Epidemics**: Special cards that intensify infection in a specific city
- **Communication**: Players can communicate with each other if they are in the same city

## Player Roles

- **Medic**: Removes all cubes of a single color when treating disease, and automatically removes cubes of cured diseases
- **Scientist**: Only needs 4 city cards (instead of 5) to discover a cure
- **Researcher**: Can give any city card to another player in the same city
- **Operations Expert**: Can build research stations without discarding city cards
- **Dispatcher**: Can move other players' pawns and dispatch pawns to cities containing other pawns
- **Quarantine Specialist**: Prevents disease cube placement in current and connected cities
- **Contingency Planner**: Can take and store event cards from the discard pile

## Player Actions

Each player can perform up to 4 actions per turn from the following options:

1. **Movement**:
   - Drive/Ferry: Move to an adjacent city
   - Direct Flight: Discard a city card to move to that city
   - Charter Flight: Discard the card matching your current city to move anywhere
   - Shuttle Flight: Move from a research station to another research station

2. **Other Actions**:
   - Treat Disease: Remove 1 disease cube from current city
   - Build Research Station: Discard the card matching your current city to build a station
   - Share Knowledge: Give/take a city card matching your current city to/from a player in the same city
   - Discover Cure: At a research station, discard 5 city cards of the same color to cure that disease

3. **Event Cards**: Can be played at any time (not counting as an action)

## Running the Game

```bash
# Run with default settings (2 players, normal difficulty, 10 turns)
python main.py

# Run with custom settings
python main.py --players 4 --difficulty hard --turns 20

# Run with deterministic mode (fixed random seed)
python main.py --deterministic

# Run with custom random seed
python main.py --seed 12345
```

## Command Line Arguments

- `--players`: Number of players (2-4, default: 2)
- `--difficulty`: Game difficulty (easy, normal, hard, default: normal)
- `--turns`: Maximum number of turns (default: 10)
- `--seed`: Random seed for deterministic behavior (default: random)
- `--deterministic`: Use deterministic mode with default seed 42

## Implementation Notes

This is a simplified version of the Pandemic board game, focusing on the core mechanics. Some simplifications include:

- Limited set of event cards
- Simplified city connections
- No player card colors (the city's color is used)
- Streamlined epidemic resolution

This implementation is intended as a prototype for AI safety research and can be extended with more features as needed.

## LLM Agent Integration

LLM agents control the players using a tool-based approach:

1. The game state is presented to the LLM
2. The LLM analyzes the state and chooses an action
3. The action is executed in the game state
4. The process repeats until the game ends

The LLM agents can communicate with each other if they are in the same city, allowing for coordination and strategy development.

## Next Steps

- Implement action execution functions
- Add more detailed event card handling
- Enhance the evaluation metrics for agent performance
- Add visualization of the game board
- Support human player participation 