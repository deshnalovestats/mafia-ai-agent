from modules import random,List,Tuple,Dict,Counter
from traits import GeneticTraits    
from belief import BeliefSystem

class Player:
    """Base class for all players in the game"""
    def __init__(self, player_id: int, num_players: int, genetic_traits: GeneticTraits = None):
        self.player_id = player_id
        self.num_players = num_players
        self.role = None
        self.alive = True
        self.beliefs = BeliefSystem(player_id, num_players)
        
        # Genetic traits - initialize random if not provided
        self.genetic_traits = genetic_traits if genetic_traits else GeneticTraits()
        
        # Game state tracking
        self.day = 0
        self.last_statement = None
        self.game_history = []
        self.statements_made = []
        self.protected_by_doctor = False
        
    def assign_role(self, role: str):
        """Assign a role to the player"""
        self.role = role
        # Update belief system with knowledge of own role
        self.beliefs.update_known_role(self.player_id, role)
        
    def observe_death(self, player_id: int, was_killed_at_night: bool, revealed_role: str):
        """Observe another player's death and update beliefs"""
        self.beliefs.update_from_death(player_id, was_killed_at_night, revealed_role)
        
    def observe_vote(self, voter_id: int, target_id: int, day: int):
        """Observe a vote and update beliefs"""
        self.beliefs.update_beliefs_from_vote(voter_id, target_id, day)
        
    def observe_statement(self, speaker_id: int, statement_type: str, subject_id: int, day: int):
        """Observe a statement made by another player"""
        self.beliefs.record_statement(speaker_id, statement_type, subject_id, day)
        
    def get_voting_target(self, alive_players: List[int]) -> int:
        """Decide who to vote for during the day"""
        if not alive_players or len(alive_players) <= 1:
            return -1
            
        # Check if we should vote randomly based on genetic traits
        if random.random() < self.genetic_traits.vote_randomness:
            valid_targets = [p for p in alive_players if p != self.player_id]
            if valid_targets:
                return random.choice(valid_targets)
            return -1
            
        # Get mafia probability rankings
        mafia_probs = self.beliefs.get_most_likely_mafia(alive_players)
        
        # Different voting strategies based on role
        if self.role == 'MAFIA':
            # As mafia, avoid voting for other mafia and try to eliminate threats
            # Get known mafia
            known_mafia = list(self.beliefs.known_facts['is_mafia'])
            
            # Identify most threatening non-mafia players
            threats = []
            for player_id, probability in self.beliefs.get_most_likely_detective(alive_players):
                if player_id not in known_mafia and player_id != self.player_id:
                    threats.append((player_id, 2 * probability))  # Detectives are high-priority targets
                
            # Add untrusted players who might suspect us
            for player_id, trust in self.beliefs.get_most_trusted(alive_players):
                if player_id not in known_mafia and player_id != self.player_id:
                    inverse_trust = 1.0 - trust
                    threats.append((player_id, inverse_trust))
                    
            # Sort threats by priority
            threats.sort(key=lambda x: x[1], reverse=True)
            
            if threats:
                return threats[0][0]
            
            # Fall back to random non-mafia
            valid_targets = [p for p in alive_players if p not in known_mafia and p != self.player_id]
            if valid_targets:
                return random.choice(valid_targets)
            return -1
        
        else:
            # As villager/detective/doctor, vote for most likely mafia
            if mafia_probs:
                return mafia_probs[0][0]  # Vote for player with highest mafia probability
            
            # If no clear target, vote for least trusted player
            trusted_players = self.beliefs.get_most_trusted(alive_players)
            if trusted_players:
                return trusted_players[-1][0]  # Vote for least trusted
            
            # Fall back to random vote
            valid_targets = [p for p in alive_players if p != self.player_id]
            if valid_targets:
                return random.choice(valid_targets)
            return -1
            
    def make_statement(self, alive_players: List[int], day: int) -> Dict:
        """Generate a statement during day discussion phase"""
        statement = {'day': day, 'speaker': self.player_id, 'type': None, 'subject': None, 'content': None}
        
        # Base probability of making an accusation on genetic traits
        if random.random() < self.genetic_traits.accusation_threshold:
            # Make an accusation
            if self.role == 'MAFIA':
                # As mafia, strategically accuse non-mafia players
                # Try to avoid accusing other mafia
                known_mafia = list(self.beliefs.known_facts['is_mafia'])
                valid_targets = [p for p in alive_players if p != self.player_id and p not in known_mafia]
                
                if valid_targets:
                    # Prioritize suspicion on detectives or those who might suspect us
                    detective_probs = self.beliefs.get_most_likely_detective(valid_targets)
                    
                    if detective_probs and random.random() < 0.7:
                        target = detective_probs[0][0]
                    else:
                        # Accuse someone who seems trusted
                        trusted_players = self.beliefs.get_most_trusted(valid_targets)
                        if trusted_players:
                            # Target the most trusted non-mafia player
                            target = trusted_players[0][0]
                        else:
                            target = random.choice(valid_targets)
                            
                    statement['type'] = 'accuse'
                    statement['subject'] = target
                    statement['content'] = f"Player {target} is acting suspiciously and might be mafia."
            else:
                # As non-mafia, accuse based on beliefs
                mafia_probs = self.beliefs.get_most_likely_mafia(alive_players)
                
                if mafia_probs:
                    # Only accuse if we have a reasonable suspicion
                    target, prob = mafia_probs[0]
                    
                    if prob > 0.5 or random.random() < self.genetic_traits.false_accusation_rate:
                        statement['type'] = 'accuse'
                        statement['subject'] = target
                        statement['content'] = f"I suspect Player {target} is mafia based on their behavior."
        
        # If we didn't make an accusation, consider defending someone
        if not statement['type'] and random.random() < 0.4:
            if self.role == 'MAFIA':
                # As mafia, occasionally defend fellow mafia
                known_mafia = list(self.beliefs.known_facts['is_mafia'])
                fellow_mafia = [p for p in alive_players if p != self.player_id and p in known_mafia]
                
                if fellow_mafia and random.random() < self.genetic_traits.deception_skill:
                    target = random.choice(fellow_mafia)
                    statement['type'] = 'defend'
                    statement['subject'] = target
                    statement['content'] = f"I think Player {target} is innocent and being unfairly accused."
            else:
                # As non-mafia, defend those we believe are innocent
                trusted_players = self.beliefs.get_most_trusted(alive_players)
                
                if trusted_players:
                    # Find a trusted player with low mafia probability
                    for player_id, trust in trusted_players:
                        if player_id != self.player_id and self.beliefs.role_beliefs['MAFIA'][player_id] < 0.3:
                            statement['type'] = 'defend'
                            statement['subject'] = player_id
                            statement['content'] = f"I believe Player {player_id} is innocent."
                            break
        
        # If still no statement type, make a generic comment
        if not statement['type']:
            statement['type'] = 'comment'
            statement['content'] = "I'm observing everyone's behavior closely."
            
        # Record the statement we made
        self.statements_made.append(statement)
        self.last_statement = statement
        
        return statement

    def night_action(self, alive_players: List[int]) -> int:
        """Perform a night action based on role"""
        if not alive_players or len(alive_players) <= 1:
            return -1
            
        if self.role == 'MAFIA':
            return self.mafia_kill_target(alive_players)
        elif self.role == 'DETECTIVE':
            return self.detective_investigate_target(alive_players)
        elif self.role == 'DOCTOR':
            return self.doctor_protect_target(alive_players)
        else:
            return -1  # Villagers have no night action
            
    def mafia_kill_target(self, alive_players: List[int]) -> int:
        """Select a player to kill during the night (mafia only)"""
        # Don't target other mafia members
        known_mafia = list(self.beliefs.known_facts['is_mafia'])
        valid_targets = [p for p in alive_players if p not in known_mafia and p != self.player_id]
        
        if not valid_targets:
            return -1
            
        # Prioritize threats - detectives, doctors, or vocal accusers
        detective_probs = [(p, prob) for p, prob in self.beliefs.get_most_likely_detective(valid_targets) if prob > 0.5]
        doctor_probs = [(p, prob) for p, prob in self.beliefs.get_most_likely_doctor(valid_targets) if prob > 0.5]
        
        # Create a threat score for each valid target
        threat_scores = {}
        for p in valid_targets:
            threat_scores[p] = 0
            
            # Higher score for suspected detectives
            for pid, prob in detective_probs:
                if p == pid:
                    threat_scores[p] += 3 * prob
                    
            # Higher score for suspected doctors
            for pid, prob in doctor_probs:
                if p == pid:
                    threat_scores[p] += 2 * prob
                    
            # Higher score for players who accused us
            for statement in self.beliefs.player_statements.get(p, []):
                if statement['type'] == 'accuse' and statement['subject'] == self.player_id:
                    threat_scores[p] += 2
                    
            # Lower trust means higher threat
            trust = self.beliefs.trust_levels[p]
            threat_scores[p] += (1 - trust)
        
        # Select target with highest threat score
        if threat_scores:
            target = max(threat_scores.items(), key=lambda x: x[1])[0]
            return target
            
        # Fall back to random selection
        return random.choice(valid_targets)
    
    def detective_investigate_target(self, alive_players: List[int]) -> int:
        """Select a player to investigate (detective only)"""
        # Don't investigate players we already know about
        known_mafia = list(self.beliefs.known_facts['is_mafia'])
        known_not_mafia = list(self.beliefs.known_facts['is_not_mafia'])
        valid_targets = [p for p in alive_players if p != self.player_id 
                      and p not in known_mafia and p not in known_not_mafia]
        
        if not valid_targets:
            return -1
            
        # Use genetic trait to determine investigation strategy
        if self.genetic_traits.detective_investigation_strategy < 0.5:
            # Strategy: Focus on most suspicious first
            mafia_probs = self.beliefs.get_most_likely_mafia(valid_targets)
            if mafia_probs:
                return mafia_probs[0][0]
        else:
            # Strategy: Random investigation (information gathering)
            return random.choice(valid_targets)
            
        # Fall back to random selection
        return random.choice(valid_targets)
    
    def doctor_protect_target(self, alive_players: List[int]) -> int:
        """Select a player to protect (doctor only)"""
        valid_targets = [p for p in alive_players]
        
        if not valid_targets:
            return -1
            
        # Determine protection strategy based on genetic traits
        if self.genetic_traits.doctor_protection_strategy < 0.3:
            # Strategy: Protect self
            return self.player_id
        elif self.genetic_traits.doctor_protection_strategy < 0.7:
            # Strategy: Protect most valuable players (detectives or trusted)
            detective_probs = self.beliefs.get_most_likely_detective(alive_players)
            if detective_probs and detective_probs[0][1] > 0.6:
                return detective_probs[0][0]
                
            # Protect most trusted player
            trusted_players = self.beliefs.get_most_trusted(alive_players)
            if trusted_players:
                return trusted_players[0][0]
        else:
            # Strategy: Protect who seems most at risk
            # This could be improved with more sophisticated threat assessment
            mafia_targets = []
            
            # Look at recent accusations to predict who might be targeted
            for player_id, statements in self.beliefs.player_statements.items():
                if player_id in self.beliefs.known_facts['is_mafia'] or self.beliefs.role_beliefs['MAFIA'][player_id] > 0.6:
                    # This is likely a mafia member, check who they defended
                    for statement in statements:
                        if statement['type'] == 'defend' and statement['subject'] in alive_players:
                            # Mafia rarely defend non-mafia, so this could be a fellow mafia
                            mafia_targets.append(statement['subject'])
                            
                    # Also check who they accused - mafia often target who they accused
                    for statement in statements:
                        if statement['type'] == 'accuse' and statement['subject'] in alive_players:
                            mafia_targets.append(statement['subject'])
            
            # Count frequencies of potential targets
            if mafia_targets:
                target_counts = Counter(mafia_targets)
                most_likely_target = target_counts.most_common(1)[0][0]
                return most_likely_target
                
        # Fall back to random protection
        return random.choice(valid_targets)
    
    def update_from_detective_result(self, player_id: int, is_mafia: bool):
        """Update beliefs based on detective investigation results"""
        self.beliefs.record_detective_investigation(player_id, is_mafia)
    
    def calculate_fitness(self, survival_time, game_outcome, team_win):
        """Calculate fitness for genetic algorithm based on performance"""
        fitness = 0
        
        # Base fitness from survival
        fitness += survival_time * 10
        
        # Bonus for winning
        if team_win:
            fitness += 100
            
        # Role-specific bonuses
        if self.role == 'MAFIA':
            # Mafia gets bonus for deception
            successful_deception = 0
            for statement in self.statements_made:
                if statement['type'] in ['defend', 'accuse']:
                    # Defending fellow mafia or accusing non-mafia is good deception
                    if (statement['type'] == 'defend' and 
                        statement['subject'] in self.beliefs.known_facts['is_mafia']):
                        successful_deception += 1
                    elif (statement['type'] == 'accuse' and 
                          statement['subject'] not in self.beliefs.known_facts['is_mafia']):
                        successful_deception += 1
            
            fitness += successful_deception * 5
            
        elif self.role == 'DETECTIVE':
            # Detective gets bonus for correct investigations
            successful_investigations = len(self.beliefs.observations)
            fitness += successful_investigations * 10
            
        elif self.role == 'DOCTOR':
            # Doctor gets bonus for successful protection
            # This would require tracking successful protections
            pass
            
        return fitness
