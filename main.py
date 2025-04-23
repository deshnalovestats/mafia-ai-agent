"""
Mafia AI Agent with Genetic Algorithms and Propositional Logic
------------------------------------------------------------------
This project implements AI agents for the social deduction game Mafia,
using genetic algorithms to evolve strategies and propositional logic
to model player beliefs and reasoning.
"""

from simulation import run_simulation

if __name__ == "__main__":
    print("Mafia AI Agent with Genetic Algorithms and Propositional Logic")
    print("------------------------------------------------------------")
    
    best_population, best_fitness, avg_fitness, game_log = run_simulation(
        generations=10,     
        population_size=32,  
        num_players=8,      
        games_per_individual=4 
    )
    
    print("\nEvolution complete. The AI agents have evolved strategies for")
    print("deception, trust building, and probabilistic reasoning in social deduction games.")
