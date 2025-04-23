from traits import GeneticTraits
from config import GameConfig
from mafia import MafiaGame
from modules import random,copy


class GeneticAlgorithm:
    """Handles the evolution of player strategies using genetic algorithms"""
    def __init__(self, population_size=40, num_players=8, elitism_rate=0.2,
                 mutation_rate=0.1, mutation_strength=0.2, tournament_size=3):
        self.population_size = population_size
        self.num_players = num_players
        self.elitism_rate = elitism_rate
        self.mutation_rate = mutation_rate
        self.mutation_strength = mutation_strength
        self.tournament_size = tournament_size
        
        # Initialize population
        self.population = [GeneticTraits() for _ in range(population_size)]
        
        # Track generations and fitness
        self.generation = 0
        self.best_fitness_history = []
        self.avg_fitness_history = []
        
    def evolve(self, num_generations=50, games_per_individual=5, game_config=None):
        """Run the genetic algorithm for a specified number of generations"""
        if not game_config:
            game_config = GameConfig(num_players=self.num_players)
            
        for gen in range(num_generations):
            self.generation = gen + 1
            print(f"Generation {self.generation}...")
            
            # Evaluate population
            fitness_scores = self._evaluate_population(game_config, games_per_individual)
            
            # Record stats
            best_fitness = max(fitness_scores.values())
            avg_fitness = sum(fitness_scores.values()) / len(fitness_scores)
            self.best_fitness_history.append(best_fitness)
            self.avg_fitness_history.append(avg_fitness)
            
            print(f"  Best fitness: {best_fitness:.2f}")
            print(f"  Average fitness: {avg_fitness:.2f}")
            
            # Generate new population
            self._generate_new_population(fitness_scores)
            
        return self.population, self.best_fitness_history, self.avg_fitness_history
    
    def _evaluate_population(self, game_config, games_per_individual):
        """Evaluate the fitness of all individuals in the population"""
        fitness_scores = {}
        
        # Group population into self.num_players sized groups for games
        for i in range(0, self.population_size, self.num_players):
            group = self.population[i:i+self.num_players]
            
            # If not enough players, pad with random individuals
            while len(group) < self.num_players:
                group.append(GeneticTraits())
                
            # Play multiple games with this group
            group_scores = {j: 0 for j in range(len(group))}
            
            for _ in range(games_per_individual):
                # Initialize game
                game = MafiaGame(game_config)
                game.initialize_game(group)
                
                # Run game
                winning_team, days_played = game.run_game()
                
                # Get fitness scores
                game_scores = game.get_player_fitness()
                
                # Add to group scores
                for player_id, score in game_scores.items():
                    if player_id < len(group):
                        group_scores[player_id] += score
            
            # Average scores across games
            for player_id in group_scores:
                group_scores[player_id] /= games_per_individual
                
            # Add to overall fitness scores
            for j, player_id in enumerate(range(i, min(i+self.num_players, self.population_size))):
                fitness_scores[player_id] = group_scores[j]
                
        return fitness_scores
    
    def _tournament_selection(self, fitness_scores):
        """Select an individual using tournament selection"""
        # Randomly select tournament_size individuals
        tournament = random.sample(range(self.population_size), min(self.tournament_size, self.population_size))
        
        # Find the one with highest fitness
        winner = tournament[0]
        for candidate in tournament:
            if fitness_scores[candidate] > fitness_scores[winner]:
                winner = candidate
                
        return winner
    
    def _generate_new_population(self, fitness_scores):
        """Generate a new population using selection, crossover, and mutation"""
        new_population = []
        
        # Elitism - keep best individuals
        elite_count = int(self.population_size * self.elitism_rate)
        elite_indices = sorted(range(self.population_size), key=lambda i: fitness_scores[i], reverse=True)[:elite_count]
        
        for idx in elite_indices:
            new_population.append(copy.deepcopy(self.population[idx]))
            
        # Fill rest with crossover and mutation
        while len(new_population) < self.population_size:
            # Select parents
            parent1_idx = self._tournament_selection(fitness_scores)
            parent2_idx = self._tournament_selection(fitness_scores)
            
            # Crossover
            child = GeneticTraits.crossover(self.population[parent1_idx], self.population[parent2_idx])
            
            # Mutation
            child.mutate(self.mutation_rate, self.mutation_strength)
            
            # Add to new population
            new_population.append(child)
            
        # Replace old population
        self.population = new_population

