class GameConfig:
    def __init__(self, num_players=8, mafia_ratio=0.25, detective_prob=0.125, doctor_prob=0.125):
        self.num_players = num_players
        self.mafia_ratio = mafia_ratio
        self.detective_prob = detective_prob
        self.doctor_prob = doctor_prob
