from modules import np,defaultdict,List,Tuple
from constants import ROLES

class BeliefSystem:
    """
    Represents a player's beliefs about other players using propositional logic
    """
    def __init__(self, player_id: int, num_players: int):
        self.player_id = player_id
        self.num_players = num_players
        
        # Initialize belief matrices for each role
        # For each player, we track probability that they have each role
        self.role_beliefs = {
            role: np.ones(num_players) / num_players for role in ROLES
        }
        
        # Known facts - definite knowledge
        self.known_facts = {
            'is_mafia': set(),
            'is_not_mafia': set(),
            'is_detective': set(),
            'is_doctor': set(),
            'is_villager': set(),
            'is_not_detective': set(),
            'is_not_doctor': set(),
            'is_not_villager':set()
        }
        
        # Set own role certainty (will be updated when role is assigned)
        for role in ROLES.keys():
            self.role_beliefs[role][player_id] = 0.0
        
        # History of observations
        self.observations = []
        
        # Voting history - who voted for whom and when
        self.voting_history = []
        
        # Statements made by other players
        self.player_statements = defaultdict(list)
        
        # Trust levels toward other players (0-1)
        self.trust_levels = np.ones(num_players) * 0.5
        self.trust_levels[player_id] = 1.0  # Trust ourselves completely
        
    def update_known_role(self, player_id: int, role: str):
        """Update beliefs when a player's role is definitively known"""
        if player_id == self.player_id:
            # Update self knowledge
            for r in ROLES.keys():
                if r == role:
                    self.role_beliefs[r][player_id] = 1.0
                else:
                    self.role_beliefs[r][player_id] = 0.0
                    
            # Add to known facts
            self.known_facts[f'is_{role.lower()}'].add(player_id)
            return
            
        # Update role certainty
        for r in ROLES.keys():
            if r == role:
                self.role_beliefs[r][player_id] = 1.0
                self.known_facts[f'is_{role.lower()}'].add(player_id)
            else:
                self.role_beliefs[r][player_id] = 0.0
                self.known_facts[f'is_not_{role.lower()}'].add(player_id)
                
        # If they're mafia, they're not villager/detective/doctor and vice versa
        if role == 'MAFIA':
            self.known_facts['is_not_villager'].add(player_id)
            self.known_facts['is_not_detective'].add(player_id)
            self.known_facts['is_not_doctor'].add(player_id)
        else:
            self.known_facts['is_not_mafia'].add(player_id)
            
    def update_beliefs_from_vote(self, voter_id: int, target_id: int, day: int):
        """Update beliefs based on voting behavior"""
        self.voting_history.append((day, voter_id, target_id))
        
        # Analyze voting patterns
        # If someone keeps voting for non-mafia, they might be mafia
        # If someone consistently votes for mafia, they're more likely innocent
        
        if voter_id != self.player_id and voter_id not in self.known_facts['is_mafia']:
            # Check if target is known to be mafia or non-mafia
            if target_id in self.known_facts['is_mafia']:
                # Voter voted for a known mafia - increase trust
                self.trust_levels[voter_id] = min(1.0, self.trust_levels[voter_id] + 0.1)
                # More likely to be non-mafia
                self._shift_belief_toward(voter_id, 'MAFIA', decrease=True)
                
            elif target_id in self.known_facts['is_not_mafia']:
                # Voter voted for known innocent - decrease trust
                self.trust_levels[voter_id] = max(0.0, self.trust_levels[voter_id] - 0.1)
                # More likely to be mafia
                self._shift_belief_toward(voter_id, 'MAFIA', decrease=False)
    
    def record_statement(self, speaker_id: int, statement_type: str, subject_id: int, day: int):
        """Record a statement made by a player"""
        self.player_statements[speaker_id].append({
            'day': day,
            'type': statement_type, 
            'subject': subject_id
        })
        
        # Update beliefs based on statement
        if statement_type == 'accuse':
            # If speaker accuses someone of being mafia
            if speaker_id != self.player_id:
                # Is the accusation correct based on what we know?
                if subject_id in self.known_facts['is_mafia']:
                    # Correct accusation - increase trust in speaker
                    self.trust_levels[speaker_id] = min(1.0, self.trust_levels[speaker_id] + 0.15)
                    self._shift_belief_toward(speaker_id, 'MAFIA', decrease=True)
                elif subject_id in self.known_facts['is_not_mafia']:
                    # False accusation - decrease trust in speaker
                    self.trust_levels[speaker_id] = max(0.0, self.trust_levels[speaker_id] - 0.1)
                    self._shift_belief_toward(speaker_id, 'MAFIA', decrease=False)
                else:
                    # Unknown validity - slightly update beliefs on subject
                    trust_weight = self.trust_levels[speaker_id] * 0.05
                    current = self.role_beliefs['MAFIA'][subject_id]
                    self.role_beliefs['MAFIA'][subject_id] = min(0.95, current + trust_weight)
                    # Normalize other beliefs
                    self._normalize_beliefs()
        
        elif statement_type == 'defend':
            # If speaker defends someone against mafia accusations
            if speaker_id != self.player_id:
                # Is the defense correct based on what we know?
                if subject_id in self.known_facts['is_not_mafia']:
                    # Correct defense - increase trust in speaker
                    self.trust_levels[speaker_id] = min(1.0, self.trust_levels[speaker_id] + 0.1)
                    self._shift_belief_toward(speaker_id, 'MAFIA', decrease=True)
                elif subject_id in self.known_facts['is_mafia']:
                    # Defending a known mafia - speaker might be mafia
                    self.trust_levels[speaker_id] = max(0.0, self.trust_levels[speaker_id] - 0.15)
                    self._shift_belief_toward(speaker_id, 'MAFIA', decrease=False)
                else:
                    # Unknown validity - slightly update beliefs
                    trust_weight = self.trust_levels[speaker_id] * 0.05
                    current = self.role_beliefs['MAFIA'][subject_id]
                    self.role_beliefs['MAFIA'][subject_id] = max(0.05, current - trust_weight)
                    # Normalize other beliefs
                    self._normalize_beliefs()
    
    def record_detective_investigation(self, target_id: int, is_mafia: bool):
        """Record the result of a detective investigation"""
        if is_mafia:
            self.update_known_role(target_id, 'MAFIA')
        else:
            self.role_beliefs['MAFIA'][target_id] = 0.0
            self.known_facts['is_not_mafia'].add(target_id)
        
        # Add to observations
        self.observations.append({
            'type': 'detective_check',
            'target': target_id,
            'is_mafia': is_mafia
        })
        
    def update_from_death(self, player_id: int, was_killed_at_night: bool, revealed_role: str):
        """Update beliefs when a player dies"""
        self.update_known_role(player_id, revealed_role)
        
        # Add to observations
        self.observations.append({
            'type': 'death',
            'player': player_id,
            'night_kill': was_killed_at_night,
            'role': revealed_role
        })
        
        # If killed at night and not mafia, mafia made that choice
        if was_killed_at_night and revealed_role != 'MAFIA':
            # Analyze voting patterns to see who might have wanted them dead
            self._analyze_night_kill_patterns(player_id)
    
    def _shift_belief_toward(self, player_id: int, role: str, decrease: bool):
        """Shift belief about a player's role"""
        shift_amount = 0.1
        current = self.role_beliefs[role][player_id]
        
        if decrease:
            # Decrease probability of this role
            new_value = max(0.05, current - shift_amount)
        else:
            # Increase probability of this role
            new_value = min(0.95, current + shift_amount)
            
        self.role_beliefs[role][player_id] = new_value
        self._normalize_beliefs()
    
    def _normalize_beliefs(self):
        """Ensure belief probabilities remain consistent"""
        # Ensure probabilities for each player sum to 1 across roles
        for p in range(self.num_players):
            total = sum(self.role_beliefs[role][p] for role in ROLES.keys())
            if total > 0:  # Avoid division by zero
                for role in ROLES.keys():
                    self.role_beliefs[role][p] /= total
    
    def _analyze_night_kill_patterns(self, killed_player_id: int):
        """Analyze voting patterns to infer who might have wanted a player dead"""
        # Check for players who were accused by the killed player
        accused_by_victim = []
        for day_info in self.player_statements.get(killed_player_id, []):
            if day_info['type'] == 'accuse':
                accused_by_victim.append(day_info['subject'])
        
        # Those accused by the victim might be mafia who wanted revenge
        for player_id in accused_by_victim:
            if player_id not in self.known_facts['is_not_mafia']:
                self._shift_belief_toward(player_id, 'MAFIA', decrease=False)
    
    def get_most_likely_mafia(self, alive_players: List[int]) -> List[Tuple[int, float]]:
        """Return a list of alive players sorted by decreasing probability of being mafia"""
        mafia_probs = [(p, self.role_beliefs['MAFIA'][p]) for p in alive_players if p != self.player_id]
        return sorted(mafia_probs, key=lambda x: x[1], reverse=True)
    
    def get_most_likely_detective(self, alive_players: List[int]) -> List[Tuple[int, float]]:
        """Return a list of alive players sorted by decreasing probability of being detective"""
        detective_probs = [(p, self.role_beliefs['DETECTIVE'][p]) for p in alive_players if p != self.player_id]
        return sorted(detective_probs, key=lambda x: x[1], reverse=True)
    
    def get_most_likely_doctor(self, alive_players: List[int]) -> List[Tuple[int, float]]:
        """Return a list of alive players sorted by decreasing probability of being doctor"""
        doctor_probs = [(p, self.role_beliefs['DOCTOR'][p]) for p in alive_players if p != self.player_id]
        return sorted(doctor_probs, key=lambda x: x[1], reverse=True)
    
    def get_most_trusted(self, alive_players: List[int]) -> List[Tuple[int, float]]:
        """Return a list of alive players sorted by decreasing trust level"""
        trust_levels = [(p, self.trust_levels[p]) for p in alive_players if p != self.player_id]
        return sorted(trust_levels, key=lambda x: x[1], reverse=True)

