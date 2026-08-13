import unittest
from evolutionary_engine import (
    MAPElitesArchive,
    default_flow_fitness,
    default_behavior_descriptor,
    DEFAULT_GENOME
)

class TestEvolutionaryEngine(unittest.TestCase):
    def test_default_flow_fitness(self):
        telemetry = {
            "health_remaining": 50,
            "time_taken_sec": 60,
            "exploration_percent": 70,
            "enemies_killed": 8,
            "total_enemies": 10,
            "chests_opened": 2,
            "total_chests": 2,
            "deaths_retries": 0
        }
        score = default_flow_fitness(telemetry, DEFAULT_GENOME)
        self.assertTrue(0.0 <= score <= 1.0)
        self.assertTrue(score > 0.7)

    def test_behavior_descriptor(self):
        telemetry = {
            "exploration_percent": 80,
            "enemies_killed": 9,
            "total_enemies": 10,
            "damage_taken": 20
        }
        b = default_behavior_descriptor(telemetry, DEFAULT_GENOME)
        self.assertEqual(b["dim1_val"], 0.8)
        self.assertTrue(0.0 <= b["dim2_val"] <= 1.0)

    def test_archive_evaluate_and_add(self):
        archive = MAPElitesArchive(grid_size=10)
        telemetry = {
            "health_remaining": 50,
            "time_taken_sec": 50,
            "exploration_percent": 50,
            "enemies_killed": 5,
            "total_enemies": 10,
            "chests_opened": 1,
            "total_chests": 2,
            "deaths_retries": 0
        }
        record = archive.evaluate_and_add(telemetry, DEFAULT_GENOME)
        self.assertTrue(record["archive_updated"])
        stats = archive.get_archive_stats()
        self.assertEqual(stats["filled_cells"], 1)
        self.assertEqual(stats["total_evaluations"], 1)

    def test_mutation(self):
        archive = MAPElitesArchive(grid_size=10)
        mutated = archive.mutate(DEFAULT_GENOME, mutation_rate=1.0)
        self.assertIsInstance(mutated["difficulty"], float)
        self.assertTrue(0.0 <= mutated["difficulty"] <= 1.0)

    def test_crossover(self):
        archive = MAPElitesArchive(grid_size=10)
        p1 = dict(DEFAULT_GENOME, difficulty=0.1)
        p2 = dict(DEFAULT_GENOME, difficulty=0.9)
        child = archive.crossover(p1, p2)
        self.assertIn(child["difficulty"], [0.1, 0.9])

    def test_serialization(self):
        archive = MAPElitesArchive(grid_size=10)
        telemetry = {"health_remaining": 60, "time_taken_sec": 40, "exploration_percent": 60}
        archive.evaluate_and_add(telemetry, DEFAULT_GENOME)
        data = archive.to_dict()
        self.assertEqual(data["grid_size"], 10)
        self.assertEqual(data["total_evaluations"], 1)
        self.assertIn("stats", data)

if __name__ == "__main__":
    unittest.main()
