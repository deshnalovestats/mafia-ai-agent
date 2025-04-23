from modules import random

class GeneticTraits:
    """Represents the genetic traits that define an AI player's strategy"""
    def __init__(self):
        # Aggression traits - how aggressively the player accuses others
        self.accusation_threshold = random.uniform(0.4, 0.8)  # Probability threshold for making accusations
        self.false_accusation_rate = random.uniform(0.0, 0.3)  # Chance of making false accusations
        
        # Deception traits (especially for mafia)
        self.deception_skill = random.uniform(0.3, 0.9)  # How effectively they can lie
        self.self_preservation = random.uniform(0.5, 1.0)  # How much they prioritize own survival
        
        # Trust traits
        self.trust_baseline = random.uniform(0.3, 0.7)  # Base level of trust in others
        self.trust_change_rate = random.uniform(0.05, 0.2)  # How quickly trust changes
        
        # Voting behavior
        self.vote_randomness = random.uniform(0.0, 0.3)  # Chance of voting randomly
        
        # Special role traits
        self.detective_investigation_strategy = random.uniform(0.0, 1.0)  # 0 = suspicious first, 1 = random
        self.doctor_protection_strategy = random.uniform(0.0, 1.0)  # 0 = protect trusted, 1 = protect self
        
        # Bluffing traits
        self.bluff_chance = random.uniform(0.1, 0.5)  # Chance to bluff about role
        self.bluff_confidence = random.uniform(0.5, 1.0)  # How confidently they bluff
        
        # Social traits - for determining speech and interaction strategy
        self.verbosity = random.uniform(0.2, 0.8)  # How much the player talks
        self.defensive_nature = random.uniform(0.2, 0.8)  # How defensive they are when accused
                
    def mutate(self, mutation_rate=0.1, mutation_strength=0.2):
        """Apply random mutations to genetic traits"""
        traits = vars(self)
        for trait in traits:
            if random.random() < mutation_rate:
                current_value = getattr(self, trait)
                # Mutate by adding or subtracting a random value
                change = random.uniform(-mutation_strength, mutation_strength)
                new_value = current_value + change
                # Ensure values stay within 0-1 range
                new_value = max(0.0, min(1.0, new_value))
                setattr(self, trait, new_value)
    
    @staticmethod
    def crossover(parent1, parent2):
        """Create a new trait set by crossing over two parents"""
        child = GeneticTraits()
        traits = vars(child)
        
        for trait in traits:
            # Crossover with 50% chance of inheriting from each parent
            if random.random() < 0.5:
                setattr(child, trait, getattr(parent1, trait))
            else:
                setattr(child, trait, getattr(parent2, trait))
                
        return child
