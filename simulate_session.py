#!/usr/bin/env python3
import sys
import json
import random
from evolutionary_engine import MAPElitesArchive, DEFAULT_GENOME

def run_simulation(levels=10):
    print("=" * 70)
    print("🧬 MAP-ELITES EVOLUTIONARY PCG SIMULATION (10 LEVELS)")
    print("=" * 70)

    session_id = f"sim_session_{random.randint(1000, 9999)}"
    archive = MAPElitesArchive(grid_size=10, fitness_fn_name="default_flow", behavior_fn_name="default_expl_agg")

    current_config = dict(DEFAULT_GENOME)

    for lvl in range(1, levels + 1):
        # Simulate realistic telemetry adapting over time
        # Early levels: player is fast and takes low damage
        # Mid levels: difficulty increases, time increases
        time_taken = round(random.uniform(25.0, 75.0), 1)
        damage_taken = random.randint(10, 50)
        health_remaining = 100 - damage_taken
        enemies_killed = random.randint(5, 12)
        total_enemies = 12
        chests_opened = random.randint(2, 4)
        total_chests = 4
        traps_triggered = random.randint(0, 2)
        exploration_pct = round(random.uniform(45.0, 85.0), 1)

        telemetry = {
            "time_taken_sec": time_taken,
            "damage_taken": damage_taken,
            "health_remaining": health_remaining,
            "deaths_retries": 0,
            "enemies_killed": enemies_killed,
            "total_enemies": total_enemies,
            "chests_opened": chests_opened,
            "total_chests": total_chests,
            "traps_triggered": traps_triggered,
            "exploration_percent": exploration_pct
        }

        # 1. Evaluate fitness and add to archive
        eval_record = archive.evaluate_and_add(telemetry, current_config)
        stats = archive.get_archive_stats()

        # 2. Breed next genome via MAP-Elites
        next_config = archive.breed_next_genome(player_behavior=eval_record["behavior"])

        # Display results
        b = eval_record["behavior"]
        print(f"\n🎮 LEVEL {lvl}")
        print(f"   Telemetry: Time={time_taken}s | HP={health_remaining}% | Kills={enemies_killed}/{total_enemies} | Expl={exploration_pct}%")
        print(f"   Behavior Niche: {b['dim1_name']}={(b['dim1_val']*100):.0f}% | {b['dim2_name']}={(b['dim2_val']*100):.0f}%")
        print(f"   Grid Cell: ({eval_record['grid_pos']['x']}, {eval_record['grid_pos']['y']})")
        print(f"   Fitness Score: {eval_record['fitness']:.4f} {'(NEW ELITE RECORD! 🏆)' if eval_record['archive_updated'] else ''}")
        print(f"   Archive Stats: Coverage = {stats['coverage_percent']}% ({stats['filled_cells']}/100 cells) | Avg Fitness = {stats['avg_fitness']:.4f} | Max Fitness = {stats['max_fitness']:.4f}")
        print(f"   Next Evolved DNA: diff={next_config['difficulty']:.2f}, enemy_density={next_config['enemy_density']:.2f}, room_density={next_config['room_density']:.2f}, trap_prob={next_config['trap_probability']:.2f}, layout={next_config['enemy_type']}")

        current_config = next_config

    print("\n" + "=" * 70)
    print("🏆 FINAL MAP-ELITES ARCHIVE SNAPSHOT")
    print("=" * 70)
    final_stats = archive.get_archive_stats()
    print(f"Total Evaluations: {final_stats['total_evaluations']}")
    print(f"Archive Coverage:  {final_stats['coverage_percent']}% ({final_stats['filled_cells']}/100 cells)")
    print(f"Average Fitness:   {final_stats['avg_fitness']:.4f}")
    print(f"Maximum Fitness:   {final_stats['max_fitness']:.4f}")

    # Render ASCII Heatmap of Archive
    print("\n10x10 ARCHIVE HEATMAP (X=Exploration, Y=Aggression):")
    print("   " + "".join([f" {x} " for x in range(10)]))
    grid = final_stats['grid']
    for y in range(9, -1, -1):
        row_str = f"{y} |"
        for x in range(10):
            cell = grid[x][y]
            if cell is not None:
                fit = cell['fitness']
                if fit >= 0.75:
                    row_str += " 🟩"
                elif fit >= 0.50:
                    row_str += " 🟨"
                else:
                    row_str += " 🟥"
            else:
                row_str += " ⬛"
        print(row_str)
    print("Legend: 🟩 High Fit (>=0.75) | 🟨 Mid Fit (>=0.50) | 🟥 Low Fit | ⬛ Unexplored Cell")

if __name__ == "__main__":
    run_simulation(10)
