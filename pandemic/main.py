from game_state import Game
import argparse

if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Run Pandemic game simulation with LLM agents')
    parser.add_argument('--players', type=int, default=2, help='Number of players (2-4)')
    parser.add_argument('--difficulty', type=str, default='normal', choices=['easy', 'normal', 'hard'], 
                        help='Game difficulty (easy, normal, hard)')
    parser.add_argument('--turns', type=int, default=2, help='Maximum number of turns')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for deterministic behavior (default: random)')
    parser.add_argument('--deterministic', action='store_true', help='Use deterministic mode with default seed 42')
    
    args = parser.parse_args()
    
    # If deterministic flag is set and no seed is provided, use default seed 42
    if args.deterministic and args.seed is None:
        args.seed = 42
    
    # Create the game with the specified settings
    game = Game(
        num_players=args.players,
        difficulty=args.difficulty,
        seed=args.seed
    )
    
    # Run the game with the specified number of turns
    game.run_game(max_turns=args.turns) 