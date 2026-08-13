#!/usr/bin/env python3
import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from evolutionary_engine import MAPElitesArchive, DEFAULT_GENOME

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

# In-memory sessions archives
ACTIVE_ARCHIVES = {}

def get_or_create_archive(session_id, fitness_fn="default_flow", behavior_fn="default_expl_agg"):
    if session_id not in ACTIVE_ARCHIVES:
        ACTIVE_ARCHIVES[session_id] = MAPElitesArchive(
            grid_size=10,
            fitness_fn_name=fitness_fn,
            behavior_fn_name=behavior_fn
        )
    return ACTIVE_ARCHIVES[session_id]

def append_to_csv_logs(session_id, level_num, telemetry, prev_config, next_config, llm_eval, eval_record=None, archive_stats=None):
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
                "Traps_Triggered", "Exploration_Percent", "MAP_Elites_Fitness", "Archive_Coverage_Pct"
            ])
        fit_val = f"{eval_record['fitness']:.4f}" if eval_record else "N/A"
        cov_val = f"{archive_stats['coverage_percent']:.1f}" if archive_stats else "N/A"
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
            fit_val,
            cov_val
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
            "MAP-Elites EA + OpenRouter (Lore Only)",
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

                    fitness_scores = [entry.get("eval_record", {}).get("fitness", 0.5) for entry in history]

                    # Plot 1: Genome Evolution & Fitness Plot
                    fig, ax1 = plt.subplots(figsize=(8, 4.5), dpi=100)
                    ax1.set_facecolor('#0f172a')
                    fig.patch.set_facecolor('#0b0f19')

                    ax1.plot(levels, difficulty, label="Difficulty", color="#38bdf8", marker="o", linewidth=2)
                    ax1.plot(levels, room_density, label="Room Density", color="#a855f7", marker="s", linewidth=2)
                    ax1.plot(levels, enemy_density, label="Enemy Density", color="#f43f5e", marker="^", linewidth=2)
                    ax1.plot(levels, trap_prob, label="Trap Prob", color="#eab308", marker="d", linewidth=2)
                    ax1.plot(levels, fitness_scores, label="MAP-Elites Fitness", color="#10b981", marker="*", linewidth=3, linestyle="--")

                    ax1.set_title(f"MAP-Elites Genome & Fitness Evolution (Session: {session_id[:12]})", color="#f8fafc", fontsize=11, fontweight="bold")
                    ax1.set_xlabel("Level Number", color="#94a3b8", fontsize=9)
                    ax1.set_ylabel("Parameter Scale / Fitness [0-1]", color="#94a3b8", fontsize=9)
                    ax1.tick_params(colors="#94a3b8")
                    ax1.grid(True, linestyle=":", alpha=0.3, color="#334155")
                    ax1.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#f8fafc", fontsize=8)

                    plt.tight_layout()
                    plot_filename1 = f"plot_parameter_evolution_{session_id}.png"
                    plot_path1 = os.path.join(PLOTS_DIR, plot_filename1)
                    plt.savefig(plot_path1)
                    plt.close()
                    saved_plots.append(plot_filename1)

            except Exception as e:
                print(f"Error generating matplotlib plot for {session_id}: {e}")
    return saved_plots

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

    subprocess.run([DUNGEON_BIN, tmp_input, tmp_output, "--export-json"], check=True)
    subprocess.run([DUNGEON_BIN, tmp_input, tmp_png], check=True)

    with open(tmp_output, "r") as f:
        map_json = json.load(f)

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
        "qwen/qwen-2.5-72b-instruct"
    ]

    sys_content = f"""You are a dynamic dungeon configuration generator for an unconstrained closed-loop PCG game engine.
Output ONLY raw JSON matching schema:
{{
  "theme_name": "<Descriptive theme name>",
  "theme": "dark" | "light",
  "palette": {{ "background": "#HEX", "wall": "#HEX", "floor": "#HEX", "corridor": "#HEX", "door": "#HEX", "trap": "#HEX", "enemy": "#HEX", "chest": "#HEX", "start": "#HEX", "exit": "#HEX", "fog": "#HEX" }},
  "map_width": 40-100,
  "map_height": 40-100,
  "layout_style": "corridor-heavy" | "room-heavy" | "balanced",
  "corridor_width": 1-3,
  "room_density": 0.1-0.9,
  "enemy_density": 0.05-0.5,
  "enemy_type": "ambush" | "patrol",
  "difficulty": 0.0-1.0,
  "trap_probability": 0.0-0.5,
  "visibility": "low" | "normal",
  "reward_density": 0.05-0.4
}}
Prompt: "{user_prompt}"
"""

    for m in models:
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps({"model": m, "messages": [{"role": "user", "content": sys_content}]}).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_API_KEY}"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
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
    cfg = dict(DEFAULT_GENOME)
    dynamic_palette = create_dynamic_palette(user_prompt)
    cfg["theme_name"] = dynamic_palette["theme_name"]
    cfg["theme"] = dynamic_palette["theme"]
    cfg["palette"] = dynamic_palette["palette"]
    return cfg

def query_llm_narrative_only(level_num, archive_stats, eval_record):
    models = [
        "deepseek/deepseek-chat",
        "meta-llama/llama-3.1-70b-instruct",
        "qwen/qwen-2.5-72b-instruct"
    ]

    prompt = f"""You are a dark fantasy dungeon chronicler.
Generate lore for Level {level_num} based on the dungeon's MAP-Elites evolutionary state:
- Archive Coverage: {archive_stats['coverage_percent']}% ({archive_stats['filled_cells']}/100 niches discovered)
- Level Fitness Score: {eval_record['fitness']} (Target: Flow State)
- Player Niche: {eval_record['behavior']['dim1_name']}={eval_record['behavior']['dim1_val']}, {eval_record['behavior']['dim2_name']}={eval_record['behavior']['dim2_val']}

Return ONLY raw JSON:
{{
  "title": "<Act/Chapter Title>",
  "lore": "<2-3 sentence lore story matching evolutionary progression>"
}}
"""
    for m in models:
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps({"model": m, "messages": [{"role": "user", "content": prompt}]}).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_API_KEY}"}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content = res_data["choices"][0]["message"]["content"]
                cleaned = content.replace("```json", "").replace("```", "").strip()
                start_idx = cleaned.find("{")
                end_idx = cleaned.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    cleaned = cleaned[start_idx:end_idx+1]
                return json.loads(cleaned)
        except Exception as e:
            print(f"Narrative LLM call with model {m} failed: {e}")

    return {
        "title": f"Act {level_num}: Evolutionary Chamber {archive_stats['filled_cells']}",
        "lore": f"The dungeon morphs continuously. MAP-Elites archive coverage has reached {archive_stats['coverage_percent']}%, reshaping layout DNA to adapt to your exploration pattern."
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
        elif url_path.startswith("/research_analytics/plots/"):
            rel = url_path.replace("/research_analytics/plots/", "")
            file_path = os.path.join(PLOTS_DIR, rel)
            content_type = "image/png"
        elif url_path.startswith("/research_analytics/"):
            rel = url_path.replace("/research_analytics/", "")
            file_path = os.path.join(ANALYTICS_DIR, rel)
            content_type = "text/csv"
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
            config = req_json.get("config") or DEFAULT_GENOME
            map_data = run_pcg_generator(config)
            self.send_json_response({"status": "success", "map": map_data})

        elif self.path == "/api/feedback_next_level":
            telemetry = req_json.get("telemetry", {})
            user_pref = req_json.get("user_preference", "Balanced challenge")
            current_config = req_json.get("current_config", DEFAULT_GENOME)
            level_num = req_json.get("level_number", 1)
            session_id = req_json.get("session_id", f"session_{int(time.time())}")
            fitness_fn_name = req_json.get("fitness_fn_name", "default_flow")
            behavior_fn_name = req_json.get("behavior_fn_name", "default_expl_agg")

            # 1. MAP-Elites Archive evaluation
            archive = get_or_create_archive(session_id, fitness_fn=fitness_fn_name, behavior_fn=behavior_fn_name)
            eval_record = archive.evaluate_and_add(telemetry, current_config)
            archive_stats = archive.get_archive_stats()

            # 2. Breed next genome via MAP-Elites
            next_config = archive.breed_next_genome(player_behavior=eval_record["behavior"])
            if "palette" in current_config:
                next_config["palette"] = current_config["palette"]
            if "theme_name" in current_config:
                next_config["theme_name"] = current_config["theme_name"]

            # 3. Generate C++ Map
            next_map = run_pcg_generator(next_config)

            # 4. Lore LLM call
            narrative = query_llm_narrative_only(level_num + 1, archive_stats, eval_record)

            evo_eval = {
                "playstyle_assessment": f"Fitness: {eval_record['fitness']:.4f} | Cell ({eval_record['grid_pos']['x']},{eval_record['grid_pos']['y']})",
                "adaptation_rationale": f"MAP-Elites Archive Coverage: {archive_stats['coverage_percent']}% ({archive_stats['filled_cells']}/100 cells). Next genome bred via tournament selection + Gaussian mutation.",
                "narrative_isomorphism": narrative,
                "next_config": next_config,
                "archive_stats": archive_stats,
                "eval_record": eval_record,
                "user_prompt_given": user_pref,
                "llm_model_used": "MAP-Elites EA Engine"
            }

            # 5. Save session JSON
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
                "eval_record": eval_record,
                "archive_stats": archive_stats,
                "next_config": next_config,
                "narrative": narrative,
                "timestamp": time.time()
            }
            session_history.append(session_entry)
            with open(session_file, "w") as f:
                json.dump(session_history, f, indent=2)

            # 6. CSV logging & Matplotlib plot generation
            append_to_csv_logs(session_id, level_num, telemetry, current_config, next_config, evo_eval, eval_record, archive_stats)
            saved_plots = generate_session_matplotlib_plots(session_id)

            self.send_json_response({
                "status": "success",
                "session_id": session_id,
                "llm_eval": evo_eval,
                "next_map": next_map,
                "next_config": next_config,
                "narrative": narrative,
                "archive_stats": archive_stats,
                "saved_plots": saved_plots
            })

        elif self.path == "/api/archive_state":
            session_id = req_json.get("session_id", "")
            if session_id in ACTIVE_ARCHIVES:
                archive = ACTIVE_ARCHIVES[session_id]
                self.send_json_response({
                    "status": "success",
                    "archive": archive.to_dict()
                })
            else:
                self.send_json_response({"status": "error", "message": "Archive not found for session"}, status=404)

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
            archive_data = ACTIVE_ARCHIVES[session_id].to_dict() if session_id in ACTIVE_ARCHIVES else {}
            if os.path.exists(session_file):
                with open(session_file, "r") as f:
                    history = json.load(f)
                self.send_json_response({"status": "success", "history": history, "archive": archive_data})
            else:
                self.send_json_response({"status": "error", "message": "Session not found"}, status=404)
        else:
            self.send_error(404, "Endpoint not found")

def main():
    ensure_binary()
    print(f"=====================================================")
    print(f"🚀 Integrated MAP-Elites EA & Analytics Server running on http://localhost:{PORT}")
    print(f"=====================================================")
    httpd = HTTPServer(("0.0.0.0", PORT), DungeonServerHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")

if __name__ == "__main__":
    main()
