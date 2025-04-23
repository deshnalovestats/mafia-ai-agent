from config import GameConfig
from player import Player
from constants import PHASES
from modules import random,Counter

class MafiaGame:
    """Main game controller that simulates the Mafia game"""
    def __init__(self, config: GameConfig):
        self.config = config
        self.num_players = config.num_players
        self.players = []
        self.alive_players = []
        self.day = 0
        self.phase = None
        self.game_over = False
        self.winning_team = None
        self.night_kill_target = None
        self.night_kill_succeeded = False
        self.protected_player = None
        self.log = []
        
    def initialize_game(self, genetic_population=None):
        """Initialize game with players and roles"""
        self.players = []
        
        # Create players with genetic traits if provided
        for i in range(self.num_players):
            genetic_traits = None
            if genetic_population and i < len(genetic_population):
                genetic_traits = genetic_population[i]
                
            player = Player(i, self.num_players, genetic_traits)
            self.players.append(player)
            
        self.alive_players = list(range(self.num_players))
        self.day = 0
        self.phase = PHASES['DAY_DISCUSSION']
        self.game_over = False
        self.winning_team = None
        
        # Assign roles
        self._assign_roles()
        
    def _assign_roles(self):
        """Randomly assign roles to players"""
        num_mafia = max(1, int(self.num_players * self.config.mafia_ratio))
        num_detective = int(self.num_players * self.config.detective_prob)
        num_doctor = int(self.num_players * self.config.doctor_prob)
        
        # Ensure at least one special role if probability > 0
        if self.config.detective_prob > 0 and num_detective == 0:
            num_detective = 1
        if self.config.doctor_prob > 0 and num_doctor == 0:
            num_doctor = 1
            
        # Limit number of special roles
        total_special = num_mafia + num_detective + num_doctor
        if total_special > self.num_players:
            # Reduce detective and doctor count if needed
            while total_special > self.num_players and (num_detective > 0 or num_doctor > 0):
                if num_detective > 0:
                    num_detective -= 1
                    total_special -= 1
                if total_special > self.num_players and num_doctor > 0:
                    num_doctor -= 1
                    total_special -= 1
            
            # As a last resort, reduce mafia count
            while total_special > self.num_players:
                num_mafia -= 1
                total_special -= 1
                
            # Ensure at least one mafia
            num_mafia = max(1, num_mafia)
        
        # Create role assignments
        roles = ['MAFIA'] * num_mafia + ['DETECTIVE'] * num_detective + ['DOCTOR'] * num_doctor
        remaining = self.num_players - len(roles)
        roles += ['VILLAGER'] * remaining
        
        # Shuffle and assign
        random.shuffle(roles)
        for i, player in enumerate(self.players):
            player.assign_role(roles[i])
            
        # Log assignment
        self.log.append(f"Roles assigned: {num_mafia} Mafia, {num_detective} Detective, {num_doctor} Doctor, {remaining} Villagers")
    
    def run_game(self, max_days=20):
        """Run the complete game simulation"""
        self.day = 1
        
        while not self.game_over and self.day <= max_days:
            self.log.append(f"-- Day {self.day} --")
            
            # Day Discussion Phase
            self.phase = PHASES['DAY_DISCUSSION']
            self._run_day_discussion()
            
            if self.game_over:
                break
                
            # Day Voting Phase
            self.phase = PHASES['DAY_VOTING']
            self._run_day_voting()
            
            if self.game_over:
                break
                
            # Night Phases
            self.log.append(f"-- Night {self.day} --")
            
            # Reset night action results
            self.night_kill_target = None
            self.night_kill_succeeded = False
            self.protected_player = None
            
            # Mafia Phase
            self.phase = PHASES['NIGHT_MAFIA']
            self._run_night_mafia()
            
            # Detective Phase
            self.phase = PHASES['NIGHT_DETECTIVE']
            self._run_night_detective()
            
            # Doctor Phase
            self.phase = PHASES['NIGHT_DOCTOR']
            self._run_night_doctor()
            
            # Execute night actions
            self._resolve_night_actions()
            
            # Check game over condition
            self._check_game_over()
            
            # Next day
            self.day += 1
            
        return self.winning_team, self.day
    
    def _run_day_discussion(self):
        """Run the day discussion phase"""
        self.log.append("Day Discussion Phase:")
        
        # Each alive player makes a statement
        for player_id in self.alive_players:
            player = self.players[player_id]
            statement = player.make_statement(self.alive_players, self.day)
            
            # Log the statement
            self.log.append(f"Player {player_id} ({player.role}): {statement['content']}")
            
            # Broadcast statement to all players
            for observer_id in self.alive_players:
                if observer_id != player_id:  # Don't need to broadcast to self
                    observer = self.players[observer_id]
                    observer.observe_statement(statement['speaker'], statement['type'], 
                                           statement.get('subject'), statement['day'])
    
    def _run_day_voting(self):
        """Run the day voting phase"""
        self.log.append("Day Voting Phase:")
        
        # Each alive player votes
        votes = {}
        for player_id in self.alive_players:
            player = self.players[player_id]
            target = player.get_voting_target(self.alive_players)
            votes[player_id] = target
            
            # Log the vote
            if target != -1:
                self.log.append(f"Player {player_id} votes for Player {target}")
            else:
                self.log.append(f"Player {player_id} abstains from voting")
            
            # Broadcast vote to all players
            for observer_id in self.alive_players:
                observer = self.players[observer_id]
                observer.observe_vote(player_id, target, self.day)
                
        # Count votes
        vote_count = Counter([v for v in votes.values() if v != -1])
        
        # Eliminate player with most votes (if any)
        if vote_count:
            # Check for tie
            max_votes = max(vote_count.values())
            players_with_max_votes = [p for p, v in vote_count.items() if v == max_votes]
            
            if players_with_max_votes:
                # In case of tie, randomly choose one
                eliminated_player = random.choice(players_with_max_votes)
                self._eliminate_player(eliminated_player, False)
                self.log.append(f"Player {eliminated_player} ({self.players[eliminated_player].role}) was eliminated by town vote")
                
                # Check game over condition
                self._check_game_over()
        else:
            self.log.append("No one was eliminated in the vote")
    
    def _run_night_mafia(self):
        """Run the night mafia phase"""
        # Find alive mafia members
        alive_mafia = [p for p in self.alive_players if self.players[p].role == 'MAFIA']
        
        if not alive_mafia:
            self.log.append("No mafia members alive to perform night kill")
            return
            
        # Each mafia member selects a target
        targets = {}
        for mafia_id in alive_mafia:
            mafia_player = self.players[mafia_id]
            target = mafia_player.night_action(self.alive_players)
            targets[mafia_id] = target
            
        # Combine mafia decisions - simplistic for now (random selection)
        valid_targets = [t for t in targets.values() if t != -1]
        if valid_targets:
            self.night_kill_target = random.choice(valid_targets)
            self.log.append(f"Mafia chose to target Player {self.night_kill_target} for elimination")
    
    def _run_night_detective(self):
        """Run the night detective phase"""
        # Find alive detectives
        alive_detectives = [p for p in self.alive_players if self.players[p].role == 'DETECTIVE']
        
        if not alive_detectives:
            return
            
        # Each detective investigates a player
        for detective_id in alive_detectives:
            detective = self.players[detective_id]
            target = detective.night_action(self.alive_players)
            
            if target != -1:
                # Perform investigation
                is_mafia = self.players[target].role == 'MAFIA'
                
                # Detective learns the result
                detective.update_from_detective_result(target, is_mafia)
                
                self.log.append(f"Detective {detective_id} investigated Player {target} and found they are {'mafia' if is_mafia else 'not mafia'}")
    
    def _run_night_doctor(self):
        """Run the night doctor phase"""
        # Find alive doctors
        alive_doctors = [p for p in self.alive_players if self.players[p].role == 'DOCTOR']
        
        if not alive_doctors:
            return
            
        # Each doctor protects a player
        for doctor_id in alive_doctors:
            doctor = self.players[doctor_id]
            target = doctor.night_action(self.alive_players)
            
            if target != -1:
                # Record protection
                # If multiple doctors, last one's choice is used (could be improved)
                self.protected_player = target
                self.log.append(f"Doctor {doctor_id} chose to protect Player {target}")
    
    def _resolve_night_actions(self):
        """Resolve all night actions"""
        # Check if mafia kill succeeds
        if self.night_kill_target is not None:
            if self.night_kill_target == self.protected_player:
                # Kill prevented by doctor
                self.log.append(f"The doctor's protection saved Player {self.night_kill_target} from elimination")
                self.night_kill_succeeded = False
            else:
                # Kill succeeds
                self._eliminate_player(self.night_kill_target, True)
                self.log.append(f"Player {self.night_kill_target} ({self.players[self.night_kill_target].role}) was eliminated during the night")
                self.night_kill_succeeded = True
    
    def _eliminate_player(self, player_id: int, killed_at_night: bool):
        """Eliminate a player from the game"""
        if player_id in self.alive_players:
            self.players[player_id].alive = False
            self.alive_players.remove(player_id)
            
            # Inform all players about death
            eliminated_role = self.players[player_id].role
            for observer_id in self.alive_players:
                observer = self.players[observer_id]
                observer.observe_death(player_id, killed_at_night, eliminated_role)
    
    def _check_game_over(self):
        """Check if the game is over and determine winner"""
        # Count alive players by role
        alive_mafia = sum(1 for p in self.alive_players if self.players[p].role == 'MAFIA')
        alive_town = len(self.alive_players) - alive_mafia
        
        # Check win conditions
        if alive_mafia == 0:
            # Town wins
            self.game_over = True
            self.winning_team = 'TOWN'
            self.log.append("Game over - Town wins! All mafia eliminated.")
            return True
            
        if alive_mafia >= alive_town:
            # Mafia wins - equal or greater numbers
            self.game_over = True
            self.winning_team = 'MAFIA'
            self.log.append("Game over - Mafia wins! They equal or outnumber the town.")
            return True
            
        return False
    
    def get_player_fitness(self):
        """Calculate fitness values for all players"""
        fitness_scores = {}
        
        for player_id, player in enumerate(self.players):
            # Calculate how long the player survived
            if player_id in self.alive_players:
                survival_time = self.day
            else:
                # Find when they died by checking the log
                survival_time = 0
                for day_num in range(1, self.day + 1):
                    death_log = [entry for entry in self.log if f"Player {player_id}" in entry and "eliminated" in entry]
                    if not death_log:
                        survival_time = day_num
                    else:
                        survival_time = day_num - 1
                        break
                        
            # Did their team win?
            team_win = False
            if player.role == 'MAFIA':
                team_win = (self.winning_team == 'MAFIA')
            else:
                team_win = (self.winning_team == 'TOWN')
                
            # Calculate fitness
            fitness = player.calculate_fitness(survival_time, self.winning_team, team_win)
            fitness_scores[player_id] = fitness
            
        return fitness_scores

