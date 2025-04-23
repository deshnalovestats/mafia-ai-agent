from GeneticAlgorithm import GeneticAlgorithm
from config import GameConfig
from mafia import MafiaGame
from modules import time

def run_simulation(generations=20, population_size=40, num_players=8, games_per_individual=3):
    """Run a complete simulation with visualization"""
    print("Initializing Genetic Algorithm for Mafia AI Agent...")
    
    # Initialize genetic algorithm
    ga = GeneticAlgorithm(population_size=population_size, num_players=num_players)
    
    # Set up game configuration
    game_config = GameConfig(num_players=num_players)
    
    # Evolve population
    start_time = time.time()
    best_population, best_fitness, avg_fitness = ga.evolve(
        num_generations=generations, 
        games_per_individual=games_per_individual,
        game_config=game_config
    )
    end_time = time.time()
    
    print(f"Evolution completed in {end_time - start_time:.2f} seconds")
    
    # Display resulting traits of best individual
    best_idx = best_fitness.index(max(best_fitness))
    best_individual = best_population[0]  # First individual due to elitism
    
    print("\nBest Individual Traits:")
    for trait, value in vars(best_individual).items():
        print(f"  {trait}: {value:.4f}")
    
    # Run a showcase game with some of the best evolved agents
    print("\nRunning showcase game with evolved agents...")
    showcase_game = MafiaGame(game_config)
    showcase_game.initialize_game(best_population[:num_players])
    winning_team, days_played = showcase_game.run_game()
    
    print(f"\nGame Results:")
    print(f"  Winning Team: {winning_team}")
    print(f"  Days Played: {days_played}")
    
    # Print game log
    print("\nGame Log:")
    for entry in showcase_game.log:
        print(f"  {entry}")
    
    return best_population, best_fitness, avg_fitness, showcase_game.log
