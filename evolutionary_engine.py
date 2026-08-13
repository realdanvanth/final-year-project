import random
import math

# Default genome constraints
GENOME_SCHEMA = {
    "difficulty": {"type": "float", "min": 0.0, "max": 1.0},
    "enemy_density": {"type": "float", "min": 0.05, "max": 0.5},
    "trap_probability": {"type": "float", "min": 0.0, "max": 0.5},
    "room_density": {"type": "float", "min": 0.1, "max": 0.9},
    "reward_density": {"type": "float", "min": 0.05, "max": 0.4},
    "corridor_width": {"type": "choice", "options": [1, 2, 3]},
    "enemy_type": {"type": "choice", "options": ["patrol", "ambush"]},
    "visibility": {"type": "choice", "options": ["low", "normal"]},
    "layout_style": {"type": "choice", "options": ["corridor-heavy", "room-heavy", "balanced"]}
}

DEFAULT_GENOME = {
    "theme": "dark",
    "layout_style": "balanced",
    "corridor_width": 2,
    "room_density": 0.5,
    "enemy_density": 0.15,
    "enemy_type": "ambush",
    "difficulty": 0.5,
    "trap_probability": 0.12,
    "visibility": "normal",
    "reward_density": 0.08
}

# --- Configurable Fitness Functions ---

def default_flow_fitness(telemetry, config):
    """
    Multi-objective flow state target:
    - HP remaining ~ 50%
    - Time ~ 45-90s
    - Exploration ~ 50-85%
    - High engagement (kills + chests)
    - Low deaths
    """
    hp_ratio = telemetry.get("health_remaining", 100) / 100.0
    survival_score = max(0.0, 1.0 - abs(hp_ratio - 0.5) * 2.0)

    time_sec = telemetry.get("time_taken_sec", 30)
    if time_sec < 20:
        time_score = time_sec / 20.0
    elif time_sec <= 90:
        time_score = 1.0
    else:
        time_score = max(0.0, 1.0 - (time_sec - 90) / 120.0)

    expl = telemetry.get("exploration_percent", 50) / 100.0
    if expl < 0.3:
        exploration_score = expl / 0.3
    elif expl <= 0.85:
        exploration_score = 1.0
    else:
        exploration_score = max(0.0, 1.0 - (expl - 0.85) / 0.15)

    total_chests = max(1, telemetry.get("total_chests", 1))
    total_enemies = max(1, telemetry.get("total_enemies", 1))
    chest_ratio = telemetry.get("chests_opened", 0) / total_chests
    kill_ratio = telemetry.get("enemies_killed", 0) / total_enemies
    engagement_score = 0.4 * chest_ratio + 0.6 * kill_ratio

    deaths = telemetry.get("deaths_retries", 0)
    death_penalty = max(0.0, 1.0 - deaths * 0.3)

    fitness = (
        0.25 * survival_score +
        0.20 * time_score +
        0.20 * exploration_score +
        0.20 * engagement_score +
        0.15 * death_penalty
    )
    return round(float(fitness), 4)

def challenge_seeking_fitness(telemetry, config):
    """Alternative fitness favoring high enemy kills and high difficulty completion."""
    kills = telemetry.get("enemies_killed", 0)
    total_e = max(1, telemetry.get("total_enemies", 1))
    diff = config.get("difficulty", 0.5)
    deaths = telemetry.get("deaths_retries", 0)
    
    score = (kills / total_e) * 0.5 + diff * 0.5 - (deaths * 0.2)
    return round(max(0.0, min(1.0, float(score))), 4)

FITNESS_FUNCTIONS = {
    "default_flow": default_flow_fitness,
    "challenge_seeking": challenge_seeking_fitness
}

# --- Configurable Behavioral Descriptors ---

def default_behavior_descriptor(telemetry, config):
    """
    Returns 2D behavior coordinates (0.0 to 1.0):
    1. Exploration Tendency
    2. Aggression Level
    """
    expl = min(1.0, max(0.0, telemetry.get("exploration_percent", 50) / 100.0))
    
    total_enemies = max(1, telemetry.get("total_enemies", 1))
    kill_ratio = telemetry.get("enemies_killed", 0) / total_enemies
    damage_taken = telemetry.get("damage_taken", 0)
    damage_efficiency = max(0.0, 1.0 - (damage_taken / 100.0))
    aggression = 0.6 * kill_ratio + 0.4 * damage_efficiency
    aggression = min(1.0, max(0.0, aggression))
    
    return {
        "dim1_name": "Exploration Tendency",
        "dim1_val": round(expl, 4),
        "dim2_name": "Aggression Level",
        "dim2_val": round(aggression, 4)
    }

BEHAVIOR_DESCRIPTORS = {
    "default_expl_agg": default_behavior_descriptor
}


class MAPElitesArchive:
    def __init__(self, grid_size=10, fitness_fn_name="default_flow", behavior_fn_name="default_expl_agg"):
        self.grid_size = grid_size
        self.fitness_fn_name = fitness_fn_name
        self.behavior_fn_name = behavior_fn_name
        self.archive = [[None for _ in range(grid_size)] for _ in range(grid_size)]
        self.total_evaluations = 0
        self.history = []

    def get_fitness_fn(self):
        return FITNESS_FUNCTIONS.get(self.fitness_fn_name, default_flow_fitness)

    def get_behavior_fn(self):
        return BEHAVIOR_DESCRIPTORS.get(self.behavior_fn_name, default_behavior_descriptor)

    def evaluate_and_add(self, telemetry, genome):
        self.total_evaluations += 1
        fitness_fn = self.get_fitness_fn()
        behavior_fn = self.get_behavior_fn()

        fitness = fitness_fn(telemetry, genome)
        behavior = behavior_fn(telemetry, genome)

        b1 = behavior["dim1_val"]
        b2 = behavior["dim2_val"]

        x = min(self.grid_size - 1, max(0, int(b1 * self.grid_size)))
        y = min(self.grid_size - 1, max(0, int(b2 * self.grid_size)))

        updated = False
        current_cell = self.archive[x][y]

        if current_cell is None or fitness > current_cell["fitness"]:
            entry = {
                "genome": dict(genome),
                "fitness": fitness,
                "behavior": behavior,
                "grid_pos": {"x": x, "y": y},
                "eval_id": self.total_evaluations
            }
            self.archive[x][y] = entry
            updated = True

        eval_record = {
            "eval_id": self.total_evaluations,
            "telemetry": telemetry,
            "genome": genome,
            "fitness": fitness,
            "behavior": behavior,
            "grid_pos": {"x": x, "y": y},
            "archive_updated": updated
        }
        self.history.append(eval_record)

        return eval_record

    def select_parent(self, player_behavior=None):
        filled_cells = []
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                if self.archive[x][y] is not None:
                    filled_cells.append(self.archive[x][y])

        if not filled_cells:
            return dict(DEFAULT_GENOME)

        if player_behavior is not None:
            b1 = player_behavior.get("dim1_val", 0.5)
            b2 = player_behavior.get("dim2_val", 0.5)
            px = min(self.grid_size - 1, max(0, int(b1 * self.grid_size)))
            py = min(self.grid_size - 1, max(0, int(b2 * self.grid_size)))

            neighbors = []
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                        if self.archive[nx][ny] is not None:
                            neighbors.append(self.archive[nx][ny])
            if neighbors:
                if len(neighbors) >= 2:
                    c1, c2 = random.sample(neighbors, 2)
                    return dict(c1["genome"] if c1["fitness"] >= c2["fitness"] else c2["genome"])
                return dict(neighbors[0]["genome"])

        # Default tournament selection across entire archive
        if len(filled_cells) >= 2:
            c1, c2 = random.sample(filled_cells, 2)
            return dict(c1["genome"] if c1["fitness"] >= c2["fitness"] else c2["genome"])
        return dict(filled_cells[0]["genome"])

    def mutate(self, genome, mutation_rate=0.4, mutation_strength=0.25):
        child = dict(genome)
        for key, schema in GENOME_SCHEMA.items():
            if random.random() < mutation_rate:
                if schema["type"] == "float":
                    val = child.get(key, (schema["min"] + schema["max"]) / 2)
                    delta = random.gauss(0, mutation_strength * (schema["max"] - schema["min"]))
                    child[key] = round(max(schema["min"], min(schema["max"], val + delta)), 4)
                elif schema["type"] == "choice":
                    child[key] = random.choice(schema["options"])
        return child

    def crossover(self, parent_a, parent_b):
        child = dict(parent_a)
        for key in GENOME_SCHEMA:
            if random.random() < 0.5 and key in parent_b:
                child[key] = parent_b[key]
        return child

    def breed_next_genome(self, player_behavior=None):
        parent_a = self.select_parent(player_behavior)
        if random.random() < 0.5:
            parent_b = self.select_parent(player_behavior)
            child = self.crossover(parent_a, parent_b)
        else:
            child = parent_a
        child = self.mutate(child)
        return child

    def get_archive_stats(self):
        filled = 0
        total_fit = 0.0
        max_fit = 0.0
        grid_data = []

        for x in range(self.grid_size):
            col = []
            for y in range(self.grid_size):
                cell = self.archive[x][y]
                if cell is not None:
                    filled += 1
                    total_fit += cell["fitness"]
                    max_fit = max(max_fit, cell["fitness"])
                    col.append({
                        "fitness": cell["fitness"],
                        "behavior": cell["behavior"],
                        "eval_id": cell["eval_id"],
                        "genome": cell["genome"]
                    })
                else:
                    col.append(None)
            grid_data.append(col)

        total_cells = self.grid_size * self.grid_size
        return {
            "grid_size": self.grid_size,
            "coverage_percent": round((filled / total_cells) * 100.0, 2),
            "filled_cells": filled,
            "total_cells": total_cells,
            "avg_fitness": round(total_fit / filled, 4) if filled > 0 else 0.0,
            "max_fitness": round(max_fit, 4),
            "total_evaluations": self.total_evaluations,
            "grid": grid_data
        }

    def to_dict(self):
        return {
            "grid_size": self.grid_size,
            "fitness_fn_name": self.fitness_fn_name,
            "behavior_fn_name": self.behavior_fn_name,
            "total_evaluations": self.total_evaluations,
            "stats": self.get_archive_stats(),
            "history": self.history
        }
