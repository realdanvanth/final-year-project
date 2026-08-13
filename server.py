#!/usr/bin/env python3
import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

import csv
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PORT = 8080
OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY",
    "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"
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DUNGEON_BIN = os.path.join(BASE_DIR, "dungeon_map")
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
ANALYTICS_DIR = os.path.join(BASE_DIR, "research_analytics")
PLOTS_DIR = os.path.join(ANALYTICS_DIR, "plots")

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(ANALYTICS_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)

def append_to_csv_logs(session_id, level_num, telemetry, prev_config, next_config, llm_eval):
    telemetry_csv = os.path.join(ANALYTICS_DIR, "session_telemetry.csv")
    llm_csv = os.path.join(ANALYTICS_DIR, "llm_parameters_history.csv")

    write_tel_header = not os.path.exists(telemetry_csv)
    with open(telemetry_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_tel_header:
            writer.writerow([
                "Session_ID", "Level_Number", "Timestamp", "Clear_Time_Sec",
                "Damage_Taken", "Health_Remaining", "Deaths_Retries",
                "Enemies_Killed", "Total_Enemies", "Chests_Opened", "Total_Chests",
                "Traps_Triggered", "Exploration_Percent", "Playstyle_Assessment"
            ])
        writer.writerow([
            session_id, level_num, time.strftime("%Y-%m-%d %H:%M:%S"),
            f"{telemetry.get('time_taken_sec', 0):.2f}",
            telemetry.get('damage_taken', 0),
            telemetry.get('health_remaining', 100),
            telemetry.get('deaths_retries', 0),
            telemetry.get('enemies_killed', 0),
            telemetry.get('total_enemies', 0),
            telemetry.get('chests_opened', 0),
            telemetry.get('total_chests', 0),
            telemetry.get('traps_triggered', 0),
            f"{telemetry.get('exploration_percent', 0):.1f}",
            llm_eval.get("playstyle_assessment", "N/A")
        ])

    write_llm_header = not os.path.exists(llm_csv)
    with open(llm_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_llm_header:
            writer.writerow([
                "Session_ID", "Level_Number", "Timestamp", "User_Preference",
                "Theme_Name", "Layout_Style", "Corridor_Width", "Room_Density",
                "Enemy_Density", "Enemy_Type", "Difficulty", "Trap_Probability",
                "Visibility", "Reward_Density", "LLM_Model", "Adaptation_Rationale"
            ])
        writer.writerow([
            session_id, level_num, time.strftime("%Y-%m-%d %H:%M:%S"),
            llm_eval.get("user_prompt_given", "N/A"),
            next_config.get("theme_name", "Dark Obsidian"),
            next_config.get("layout_style", "balanced"),
            next_config.get("corridor_width", 2),
            f"{next_config.get('room_density', 0.5):.2f}",
            f"{next_config.get('enemy_density', 0.2):.2f}",
            next_config.get("enemy_type", "patrol"),
            f"{next_config.get('difficulty', 0.5):.2f}",
            f"{next_config.get('trap_probability', 0.15):.2f}",
            next_config.get("visibility", "normal"),
            f"{next_config.get('reward_density', 0.15):.2f}",
            llm_eval.get("llm_model_used", "Rule Engine"),
            str(llm_eval.get("adaptation_rationale", "N/A")).replace("\n", " ")
        ])

def generate_session_matplotlib_plots(session_id=""):
    saved_plots = []
    if session_id:
        session_file = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if os.path.exists(session_file):
            try:
                with open(session_file, "r") as f:
                    history = json.load(f)
                if history:
                    levels = [entry.get("level_number", idx + 1) for idx, entry in enumerate(history)]
                    difficulty = [entry.get("next_config", {}).get("difficulty", 0.5) for entry in history]
                    room_density = [entry.get("next_config", {}).get("room_density", 0.5) for entry in history]
                    enemy_density = [entry.get("next_config", {}).get("enemy_density", 0.2) for entry in history]
                    trap_prob = [entry.get("next_config", {}).get("trap_probability", 0.15) for entry in history]

                    clear_time = [entry.get("telemetry", {}).get("time_taken_sec", 0) for entry in history]
                    damage_taken = [entry.get("telemetry", {}).get("damage_taken", 0) for entry in history]

                    # 1. Parameter Evolution Line Chart
                    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
                    fig.patch.set_facecolor('#090a0f')
                    ax.set_facecolor('#121624')
                    ax.plot(levels, difficulty, marker='o', color='#8b5cf6', label='Difficulty', linewidth=2.5)
                    ax.plot(levels, room_density, marker='s', color='#06b6d4', label='Room Density', linewidth=2)
                    ax.plot(levels, enemy_density, marker='^', color='#f43f5e', label='Enemy Density', linewidth=2)
                    ax.plot(levels, trap_prob, marker='d', color='#f59e0b', label='Trap Probability', linewidth=2)

                    ax.set_title(f'PCG Parameter Evolution — Session {session_id}', color='#f1f5f9', fontsize=11, fontweight='bold')
                    ax.set_xlabel('Level Generation', color='#94a3b8')
                    ax.set_ylabel('Parameter Value (0.0 - 1.0)', color='#94a3b8')
                    ax.tick_params(colors='#94a3b8')
                    ax.grid(True, color='#334155', linestyle='--')
                    ax.legend(facecolor='#090a0f', edgecolor='#94a3b8', labelcolor='#f1f5f9')

                    plt.tight_layout()
                    plot_file1 = f"plot_parameter_evolution_{session_id}.png"
                    plt.savefig(os.path.join(PLOTS_DIR, plot_file1), facecolor=fig.get_facecolor())
                    plt.close()
                    saved_plots.append(plot_file1)

                    # 2. Player Performance Bar Chart
                    fig, ax1 = plt.subplots(figsize=(8, 4.5), dpi=150)
                    fig.patch.set_facecolor('#090a0f')
                    ax1.set_facecolor('#121624')

                    x_indices = list(range(len(levels)))
                    width = 0.35
                    ax1.bar([i - width/2 for i in x_indices], clear_time, width, label='Clear Time (s)', color='#06b6d4')
                    ax1.bar([i + width/2 for i in x_indices], damage_taken, width, label='Damage Taken (HP)', color='#ef4444')

                    ax1.set_title(f'Player Performance Metrics — Session {session_id}', color='#f1f5f9', fontsize=11, fontweight='bold')
                    ax1.set_xlabel('Level Generation', color='#94a3b8')
                    ax1.set_ylabel('Time (s) / Damage (HP)', color='#94a3b8')
                    ax1.set_xticks(x_indices)
                    ax1.set_xticklabels([f"Lvl {l}" for l in levels], color='#94a3b8')
                    ax1.tick_params(colors='#94a3b8')
                    ax1.grid(True, color='#334155', linestyle='--')
                    ax1.legend(facecolor='#090a0f', edgecolor='#94a3b8', labelcolor='#f1f5f9')

                    plt.tight_layout()
                    plot_file2 = f"plot_player_performance_{session_id}.png"
                    plt.savefig(os.path.join(PLOTS_DIR, plot_file2), facecolor=fig.get_facecolor())
                    plt.close()
                    saved_plots.append(plot_file2)
            except Exception as e:
                print("Error reading session history for plots:", e)

    # Always scan PLOTS_DIR for all available plot PNG files
    if os.path.exists(PLOTS_DIR):
        for fname in sorted(os.listdir(PLOTS_DIR)):
            if fname.endswith(".png") and fname not in saved_plots:
                saved_plots.append(fname)

    return saved_plots



DEFAULT_CONFIG = {
    "theme": "dark",
    "layout_style": "balanced",
    "corridor_width": 2,
    "room_density": 0.5,
    "enemy_density": 0.2,
    "enemy_type": "patrol",
    "difficulty": 0.5,
    "trap_probability": 0.15,
    "visibility": "normal",
    "reward_density": 0.15
}

def ensure_binary():
    if not os.path.exists(DUNGEON_BIN):
        print("Compiling C++ dungeon generator...")
        cmd = ["g++", "-O2", "-std=c++17", os.path.join(BASE_DIR, "program.cpp"), "-o", DUNGEON_BIN]
        subprocess.run(cmd, check=True)

def run_pcg_generator(config):
    ensure_binary()
    if "seed" not in config or not config["seed"]:
        config["seed"] = int(time.time() * 1000) % 1000000
    tmp_input = os.path.join(BASE_DIR, "tmp_input.json")
    tmp_output = os.path.join(BASE_DIR, "tmp_map.json")
    tmp_png = os.path.join(BASE_DIR, "tmp_map.png")

    with open(tmp_input, "w") as f:
        json.dump(config, f, indent=2)

    # Generate JSON
    subprocess.run([DUNGEON_BIN, tmp_input, tmp_output, "--export-json"], check=True)
    # Generate PNG
    subprocess.run([DUNGEON_BIN, tmp_input, tmp_png], check=True)

    with open(tmp_output, "r") as f:
        map_json = json.load(f)

    # Inject dynamic full config (palette, theme_name, dimensions)
    map_json["config"] = config
    return map_json


def create_dynamic_palette(user_prompt):
    p = user_prompt.lower()
    if any(k in p for k in ["cyberpunk", "matrix", "neon", "sci-fi", "futuristic", "grid"]):
        return {
            "theme_name": "Cyberpunk Neon Grid",
            "theme": "dark",
            "palette": {
                "background": "#030712",
                "wall": "#0f172a",
                "floor": "#0f2b46",
                "corridor": "#091e36",
                "door": "#38bdf8",
                "trap": "#f43f5e",
                "enemy": "#e11d48",
                "chest": "#f59e0b",
                "start": "#00ffcc",
                "exit": "#00ff66",
                "fog": "#020617"
            }
        }
    elif any(k in p for k in ["volcano", "magma", "fire", "lava", "hell", "inferno", "flame"]):
        return {
            "theme_name": "Volcanic Magma Citadel",
            "theme": "dark",
            "palette": {
                "background": "#1a0505",
                "wall": "#3b0707",
                "floor": "#5c1313",
                "corridor": "#450a0a",
                "door": "#ff4500",
                "trap": "#ef4444",
                "enemy": "#dc2626",
                "chest": "#ffd700",
                "start": "#10b981",
                "exit": "#06b6d4",
                "fog": "#0a0202"
            }
        }
    elif any(k in p for k in ["ice", "glacier", "frost", "crystal", "snow", "frozen"]):
        return {
            "theme_name": "Glacial Crystal Vault",
            "theme": "dark",
            "palette": {
                "background": "#0f172a",
                "wall": "#1e293b",
                "floor": "#e0f2fe",
                "corridor": "#bae6fd",
                "door": "#38bdf8",
                "trap": "#dc2626",
                "enemy": "#e11d48",
                "chest": "#f59e0b",
                "start": "#059669",
                "exit": "#0284c7",
                "fog": "#334155"
            }
        }
    elif any(k in p for k in ["forest", "nature", "jungle", "moss", "green", "swamp"]):
        return {
            "theme_name": "Emerald Forest Sanctuary",
            "theme": "dark",
            "palette": {
                "background": "#022c22",
                "wall": "#064e3b",
                "floor": "#047857",
                "corridor": "#065f46",
                "door": "#10b981",
                "trap": "#ef4444",
                "enemy": "#f43f5e",
                "chest": "#f59e0b",
                "start": "#0ea5e9",
                "exit": "#06b6d4",
                "fog": "#011c15"
            }
        }

    elif any(k in p for k in ["castle", "fortress", "citadel", "palace", "gothic", "keep", "throne"]):
        return {
            "theme_name": "Ancient Royal Citadel",
            "theme": "dark",
            "palette": {
                "background": "#1e1b4b",
                "wall": "#312e81",
                "floor": "#4338ca",
                "corridor": "#3730a3",
                "door": "#fbbf24",
                "trap": "#ef4444",
                "enemy": "#e11d48",
                "chest": "#f59e0b",
                "start": "#10b981",
                "exit": "#06b6d4",
                "fog": "#0f172a"
            }
        }
    elif any(k in p for k in ["dragon", "cave", "lair", "wyrm", "beast", "cavern"]):
        return {
            "theme_name": "Ancient Dragon Cave",
            "theme": "dark",
            "palette": {
                "background": "#1c1917",
                "wall": "#44403c",
                "floor": "#78350f",
                "corridor": "#57534e",
                "door": "#ea580c",
                "trap": "#dc2626",
                "enemy": "#b91c1c",
                "chest": "#fbbf24",
                "start": "#10b981",
                "exit": "#06b6d4",
                "fog": "#0c0a09"
            }
        }
    elif any(k in p for k in ["light", "white", "bright", "marble", "sun", "day", "ivory"]):

        return {
            "theme_name": "Light Marble Sanctuary",
            "theme": "light",
            "palette": {
                "background": "#f8fafc",
                "wall": "#cbd5e1",
                "floor": "#ffffff",
                "corridor": "#f1f5f9",
                "door": "#7c3aed",
                "trap": "#dc2626",
                "enemy": "#e11d48",
                "chest": "#d97706",
                "start": "#059669",
                "exit": "#0891b2",
                "fog": "#94a3b8"
            }
        }
    else:
        return {
            "theme_name": "Dark Obsidian Abyss",
            "theme": "dark",
            "palette": {
                "background": "#050609",
                "wall": "#111422",
                "floor": "#1e2436",
                "corridor": "#181d2e",
                "door": "#8b5cf6",
                "trap": "#ef4444",
                "enemy": "#f43f5e",
                "chest": "#f59e0b",
                "start": "#10b981",
                "exit": "#06b6d4",
                "fog": "#050609"
            }
        }

def parse_initial_prompt_to_config(user_prompt):
    models = [
        "deepseek/deepseek-chat",
        "meta-llama/llama-3.1-70b-instruct",
        "qwen/qwen-2.5-72b-instruct",
        "mistralai/mistral-small-24b-instruct-2501"
    ]


    sys_content = f"""You are a dynamic dungeon configuration generator for an unconstrained closed-loop PCG game engine.
Rules:
- Output ONLY raw JSON
- No markdown
- No explanation
- No duplicate keys

Schema:
{{
  "theme_name": "<Descriptive theme name>",
  "theme": "dark" | "light",
  "palette": {{
    "background": "#HEX",
    "wall": "#HEX",
    "floor": "#HEX",
    "corridor": "#HEX",
    "door": "#HEX",
    "trap": "#HEX",
    "enemy": "#HEX",
    "chest": "#HEX",
    "start": "#HEX",
    "exit": "#HEX",
    "fog": "#HEX"
  }},
  "map_width": 40-100,
  "map_height": 40-100,
  "layout_style": "corridor-heavy" | "room-heavy" | "balanced" | "arena" | "labyrinth",
  "corridor_width": 1-4,
  "room_density": 0.1-0.95,
  "enemy_density": 0.05-0.6,
  "enemy_type": "ambush" | "patrol" | "roaming" | "horde",
  "difficulty": 0.0-1.0,
  "trap_probability": 0.0-0.6,
  "visibility": "low" | "normal" | "high",
  "reward_density": 0.05-0.5
}}

Generate dynamic dungeon parameters matching this player description:
"{user_prompt}"
"""

    for m in models:
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps({"model": m, "messages": [{"role": "user", "content": sys_content}]}).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_API_KEY}"}
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content = res_data["choices"][0]["message"]["content"]
                cleaned = content.replace("```json", "").replace("```", "").strip()
                start_idx = cleaned.find("{")
                end_idx = cleaned.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    cleaned = cleaned[start_idx:end_idx+1]
                cfg = json.loads(cleaned)
                if "difficulty" in cfg:
                    print(f"✅ Initial prompt parsed by LLM ({m})! Theme: {cfg.get('theme_name')}")
                    return cfg
        except Exception as e:
            print(f"Initial prompt parsing with model {m} failed: {e}")

    p = user_prompt.lower()
    cfg = dict(DEFAULT_CONFIG)
    dynamic_palette = create_dynamic_palette(user_prompt)
    cfg["theme_name"] = dynamic_palette["theme_name"]
    cfg["theme"] = dynamic_palette["theme"]
    cfg["palette"] = dynamic_palette["palette"]


    if any(k in p for k in ["huge", "mega", "large", "giant", "massive"]):
        cfg["map_width"] = 80
        cfg["map_height"] = 80
    elif any(k in p for k in ["tiny", "small", "micro", "compact"]):
        cfg["map_width"] = 35
        cfg["map_height"] = 35

    if "hard" in p or "deadly" in p or "abyss" in p or "boss" in p:
        cfg["difficulty"] = 0.75
        cfg["enemy_density"] = 0.3
        cfg["enemy_type"] = "ambush"
        cfg["trap_probability"] = 0.25
    elif "easy" in p or "relax" in p or "treasure" in p:
        cfg["difficulty"] = 0.35
        cfg["enemy_density"] = 0.12
        cfg["reward_density"] = 0.25
        cfg["visibility"] = "normal"

    if "dark" in p or "fog" in p or "shadow" in p:
        cfg["visibility"] = "low"
    if "room" in p or "vault" in p:
        cfg["layout_style"] = "room-heavy"
        cfg["room_density"] = 0.75
    elif "corridor" in p or "maze" in p:
        cfg["layout_style"] = "corridor-heavy"
        cfg["corridor_width"] = 1

    return cfg


def compute_emergent_archetype(telemetry):
    time_taken = telemetry.get('time_taken_sec', 30)
    damage = telemetry.get('damage_taken', 0)
    chests = telemetry.get('chests_opened', 0)
    total_chests = max(1, telemetry.get('total_chests', 1))
    kills = telemetry.get('enemies_killed', 0)
    total_enemies = max(1, telemetry.get('total_enemies', 1))
    traps = telemetry.get('traps_triggered', 0)

    chest_ratio = chests / total_chests
    kill_ratio = kills / total_enemies

    if time_taken < 25 and damage < 20 and kill_ratio > 0.8:
        return "Cluster Alpha: Blitz Krieger (Ultra-Fast Clear, High Combat Efficiency)"
    elif chest_ratio >= 0.8 and damage < 25 and time_taken >= 40:
        return "Cluster Beta: Cautious Hoarder (100% Exploration & Resource Collection)"
    elif traps > 1 or damage > 50:
        return "Cluster Gamma: Panic Striker (High Hesitation, Hazard Volatility)"
    else:
        return "Cluster Delta: Methodical Sentry (Balanced Tactical Navigation)"

def generate_narrative_isomorphism(level_num):
    narratives = [
        {"title": "Act I: The Forgotten Sanctum", "lore": "An ancient stone vault intact with sacred protective wards.", "degrade_factor": 0.0, "theme": "dark"},
        {"title": "Act II: The Corrupted Abyss", "lore": "Dark void magic erodes the sanctuary pillars, spawning dimensional rifts.", "degrade_factor": 0.25, "theme": "dark"},
        {"title": "Act III: The Blood Magma Core", "lore": "Molten lava breaches the lower chambers as architectural stability collapses.", "degrade_factor": 0.5, "theme": "dark"},
        {"title": "Act IV: The Void Citadel", "lore": "Total reality collapse. Corridors morph into spatial anomaly traps.", "degrade_factor": 0.75, "theme": "dark"}
    ]
    idx = min(len(narratives) - 1, level_num - 1)
    return narratives[idx]

def apply_living_dungeon_reaction(telemetry, cfg):
    time_taken = telemetry.get('time_taken_sec', 30)
    damage = telemetry.get('damage_taken', 0)
    kills = telemetry.get('enemies_killed', 0)

    reaction_log = ""
    if kills >= 5 and time_taken < 35:
        cfg["enemy_type"] = "ambush"
        cfg["corridor_width"] = 1
        reaction_log = "Dungeon reacted defensively to aggressive melee rush by reinforcing corridor chokepoints and ambush traps."
    elif time_taken > 50:
        cfg["enemy_type"] = "roaming"
        cfg["room_density"] = min(0.85, cfg.get("room_density", 0.5) + 0.1)
        reaction_log = "Dungeon expanded room networks to challenge cautious exploration."
    else:
        reaction_log = "Dungeon dynamically recalibrated enemy patrol routes."

    return cfg, reaction_log

def query_llm_feedback(telemetry, user_pref, current_config, level_num, research_toggles=None):


    models = [
        "deepseek/deepseek-chat",
        "meta-llama/llama-3.1-70b-instruct",
        "qwen/qwen-2.5-72b-instruct",
        "mistralai/mistral-small-24b-instruct-2501"
    ]



    user_prompt = f"""You are an expert AI Dungeon Master & Closed-Loop PCG Research Director.

Player Performance Telemetry for Level {level_num}:
- Clear Time: {telemetry.get('time_taken_sec', 0):.1f} seconds
- Segment Times: {telemetry.get('segment_times', [])}
- Damage Taken: {telemetry.get('damage_taken', 0)} HP
- Health Remaining: {telemetry.get('health_remaining', 100)} HP
- Deaths / Retries: {telemetry.get('deaths_retries', 0)}
- Enemies Killed: {telemetry.get('enemies_killed', 0)} / {telemetry.get('total_enemies', 0)}
- Chests Opened: {telemetry.get('chests_opened', 0)} / {telemetry.get('total_chests', 0)}
- Traps Triggered: {telemetry.get('traps_triggered', 0)}
- Exploration %: {telemetry.get('exploration_percent', 0):.1f}%

User Target Preference: "{user_pref}"

Current Level PCG Config:
{json.dumps(current_config, indent=2)}

Task:
Analyze the player's playstyle and skill rating based on the telemetry and user request.
If the player cleared the level quickly with minimal damage, but wants a harder game (or balanced), make the next level SUBSTANTIALLY harder (higher difficulty, ambush enemies, higher enemy_density, narrower corridors, low visibility, more traps).
If the player died repeatedly or struggled, balance difficulty to avoid frustration while keeping the challenge engaging.

Return ONLY raw JSON in this EXACT structure (no markdown, no code blocks):
{{
  "playstyle_assessment": "<Brief assessment of player, e.g., 'Aggressive Speedrunner' or 'Cautious Explorer' or 'Struggling Fighter'>",
  "adaptation_rationale": "<2-3 sentence AI Director explanation of why parameters were changed based on metrics and user request>",
  "next_config": {{
    "theme": "dark",
    "layout_style": "room-heavy" | "corridor-heavy" | "balanced",
    "corridor_width": 1-3,
    "room_density": 0.1-0.9,
    "enemy_density": 0.05-0.5,
    "enemy_type": "ambush" | "patrol" | "roaming",
    "difficulty": 0.0-1.0,
    "trap_probability": 0.0-0.5,
    "visibility": "low" | "normal",
    "reward_density": 0.05-0.4
  }}
}}
"""

    for m in models:
        prompt_payload = {
            "model": m,
            "messages": [{"role": "user", "content": user_prompt}]
        }
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(prompt_payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}"
                }
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content = res_data["choices"][0]["message"]["content"]
                cleaned = content.replace("```json", "").replace("```", "").strip()
                start_idx = cleaned.find("{")
                end_idx = cleaned.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    cleaned = cleaned[start_idx:end_idx+1]
                parsed = json.loads(cleaned)
                if "next_config" in parsed:
                    print(f"✅ OpenRouter model ({m}) successfully evaluated feedback!")
                    parsed["llm_model_used"] = m
                    parsed["user_prompt_given"] = user_prompt
                    parsed["llm_raw_response"] = content
                    return parsed
        except Exception as e:
            print(f"Model {m} call failed: {e}")

    print("Falling back to Heuristic Feedback Rule Engine...")
    res = fallback_heuristic_feedback(telemetry, user_pref, current_config)
    res["user_prompt_given"] = user_prompt
    return res


def fallback_heuristic_feedback(telemetry, user_pref, current_config):
    cfg = dict(current_config) if current_config else dict(DEFAULT_CONFIG)
    time_taken = telemetry.get('time_taken_sec', 30)

    damage = telemetry.get('damage_taken', 0)
    deaths = telemetry.get('deaths_retries', 0)
    user_p = user_pref.lower()

    diff_delta = 0.0
    rationale_parts = []

    if "hard" in user_p:
        if deaths == 0 and damage < 30 and time_taken < 40:
            diff_delta += 0.25
            cfg["enemy_type"] = "ambush"
            cfg["visibility"] = "low"
            cfg["corridor_width"] = max(1, cfg.get("corridor_width", 2) - 1)
            rationale_parts.append("Player completed previous level effortlessly with minimal damage. Elevating difficulty significantly and enabling ambush AI with reduced visibility.")
        else:
            diff_delta += 0.15
            rationale_parts.append("Increasing difficulty per user request while balancing enemy pressure.")
    elif "easy" in user_p or "casual" in user_p:
        diff_delta -= 0.15
        cfg["visibility"] = "normal"
        cfg["reward_density"] = min(0.4, cfg.get("reward_density", 0.15) + 0.1)
        rationale_parts.append("Easing difficulty and increasing reward chests per user request.")
    else: # Balanced / Default
        if deaths > 0 or damage > 60:
            diff_delta -= 0.1
            rationale_parts.append("Slightly easing combat pressure to prevent player exhaustion.")
        elif time_taken < 35 and damage < 15:
            diff_delta += 0.15
            rationale_parts.append("Player demonstrated high skill speed. Scaling up difficulty and enemy density.")

    cfg["difficulty"] = max(0.1, min(1.0, cfg.get("difficulty", 0.5) + diff_delta))
    cfg["enemy_density"] = max(0.05, min(0.45, cfg["difficulty"] * 0.4))
    cfg["trap_probability"] = max(0.05, min(0.4, cfg["difficulty"] * 0.35))
    cfg["room_density"] = max(0.3, min(0.8, cfg.get("room_density", 0.5) + (0.05 if diff_delta > 0 else -0.05)))

    assessment = "High Skill Speedrunner" if time_taken < 30 and damage < 20 else ("Cautious Explorer" if time_taken > 60 else "Balanced Combatant")

    return {
        "playstyle_assessment": assessment,
        "adaptation_rationale": " ".join(rationale_parts) or "Adapted PCG parameters based on clear speed and damage metrics.",
        "next_config": cfg,
        "llm_model_used": "Deterministic Rule Engine (Offline Fallback)",
        "llm_raw_response": json.dumps({
            "playstyle_assessment": assessment,
            "adaptation_rationale": " ".join(rationale_parts) or "Adapted PCG parameters based on clear speed and damage metrics.",
            "next_config": cfg
        }, indent=2)
    }


class DungeonServerHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        url_path = self.path.split("?")[0]
        if url_path == "/" or url_path == "/index.html":
            file_path = os.path.join(BASE_DIR, "static", "index.html")
            content_type = "text/html"
        elif url_path.startswith("/static/"):
            rel = url_path.replace("/static/", "")
            file_path = os.path.join(BASE_DIR, "static", rel)
            if file_path.endswith(".css"):
                content_type = "text/css"
            elif file_path.endswith(".js"):
                content_type = "application/javascript"
            elif file_path.endswith(".png"):
                content_type = "image/png"
            else:
                content_type = "text/plain"
        elif url_path.startswith("/research_analytics/"):
            rel = url_path.replace("/research_analytics/", "")
            file_path = os.path.join(ANALYTICS_DIR, rel)
            if file_path.endswith(".png"):
                content_type = "image/png"
            elif file_path.endswith(".csv"):
                content_type = "text/csv"
            else:
                content_type = "text/plain"
        elif url_path == "/tmp_map.png":
            file_path = os.path.join(BASE_DIR, "tmp_map.png")
            content_type = "image/png"
        else:
            self.send_error(404, "File Not Found")
            return

        if os.path.exists(file_path):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        print(f"DEBUG: POST {self.path}")
        try:
            length_hdr = self.headers.get("content-length") or self.headers.get("Content-Length") or "0"
            content_length = int(length_hdr)
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            req_json = json.loads(post_data) if post_data.strip() else {}
        except Exception as err:
            print("Error parsing POST body:", err)
            req_json = {}


        if self.path == "/api/prompt_initial_level":
            prompt = req_json.get("prompt", "Balanced dungeon crawler map")
            parsed_config = parse_initial_prompt_to_config(prompt)
            map_data = run_pcg_generator(parsed_config)
            self.send_json_response({
                "status": "success",
                "config": parsed_config,
                "map": map_data
            })

        elif self.path == "/api/initial_level":
            config = req_json.get("config") or DEFAULT_CONFIG
            map_data = run_pcg_generator(config)
            self.send_json_response({"status": "success", "map": map_data})

        elif self.path == "/api/feedback_next_level":
            telemetry = req_json.get("telemetry", {})
            user_pref = req_json.get("user_preference", "Balanced challenge")
            current_config = req_json.get("current_config", DEFAULT_CONFIG)
            level_num = req_json.get("level_number", 1)
            session_id = req_json.get("session_id", f"session_{int(time.time())}")
            toggles = req_json.get("research_toggles", {})

            # 1. Base LLM / Rule evaluation
            llm_result = query_llm_feedback(telemetry, user_pref, current_config, level_num)
            next_config = dict(llm_result.get("next_config", current_config))

            # Feature 6: Emergent Playstyle Archetype Discovery
            if toggles.get("f6_clustering", False):
                archetype = compute_emergent_archetype(telemetry)
                llm_result["playstyle_assessment"] = f"{archetype} [Unsupervised Clustering]"

            # Feature 7: Narrative-Architectural Isomorphism
            narrative_info = None
            if toggles.get("f7_isomorphism", False):
                narrative_info = generate_narrative_isomorphism(level_num + 1)
                llm_result["narrative_isomorphism"] = narrative_info
                llm_result["adaptation_rationale"] += f" Narrative Degrade: '{narrative_info['title']}' - {narrative_info['lore']}"

            # Feature 8: Asymmetric Dual-Path PCG
            if toggles.get("f8_dual_path", False):
                next_config["layout_style"] = "room-heavy"
                next_config["corridor_width"] = 2
                llm_result["adaptation_rationale"] += " [Asymmetric Dual-Path Route Activated]"

            # Feature 9: Dynamic Environmental Reaction ("The Living Dungeon")
            if toggles.get("f9_living_dungeon", False):
                next_config, reaction_log = apply_living_dungeon_reaction(telemetry, next_config)
                if reaction_log:
                    llm_result["adaptation_rationale"] += f" [{reaction_log}]"

            # Generate next map
            next_map = run_pcg_generator(next_config)

            # Save research session data
            session_file = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            session_history = []
            if os.path.exists(session_file):
                try:
                    with open(session_file, "r") as f:
                        session_history = json.load(f)
                except Exception:
                    session_history = []

            session_entry = {
                "level_number": level_num,
                "telemetry": telemetry,
                "user_preference": user_pref,
                "previous_config": current_config,
                "llm_eval": llm_result,
                "next_config": next_config,
                "research_toggles": toggles,
                "timestamp": time.time()
            }
            session_history.append(session_entry)
            with open(session_file, "w") as f:
                json.dump(session_history, f, indent=2)

            # 1. Live Excel/CSV Logging
            append_to_csv_logs(session_id, level_num, telemetry, current_config, next_config, llm_result)

            # 2. Matplotlib Folder Plot Generation
            saved_plots = generate_session_matplotlib_plots(session_id)

            self.send_json_response({
                "status": "success",
                "session_id": session_id,
                "llm_eval": llm_result,
                "next_map": next_map,
                "next_config": next_config,
                "narrative": narrative_info,
                "saved_plots": saved_plots
            })

        elif self.path == "/api/get_analytics":
            session_id = req_json.get("session_id", "")
            session_file = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            history = []
            if os.path.exists(session_file):
                try:
                    with open(session_file, "r") as f:
                        history = json.load(f)
                except Exception:
                    history = []
            saved_plots = generate_session_matplotlib_plots(session_id)
            self.send_json_response({
                "status": "success",
                "session_id": session_id,
                "history": history,
                "saved_plots": saved_plots,
                "telemetry_csv": "/research_analytics/session_telemetry.csv",
                "llm_csv": "/research_analytics/llm_parameters_history.csv"
            })

        elif self.path == "/api/export_session":
            session_id = req_json.get("session_id", "")
            session_file = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            if os.path.exists(session_file):
                with open(session_file, "r") as f:
                    history = json.load(f)
                self.send_json_response({"status": "success", "history": history})
            else:
                self.send_json_response({"status": "error", "message": "Session not found"}, status=404)
        else:
            self.send_error(404, "Endpoint not found")


def main():
    ensure_binary()
    print(f"=====================================================")
    print(f"🚀 Closed-Loop LLM PCG Research Server running on http://localhost:{PORT}")
    print(f"=====================================================")
    httpd = HTTPServer(("0.0.0.0", PORT), DungeonServerHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")

if __name__ == "__main__":
    main()
