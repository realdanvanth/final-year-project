#!/bin/bash

export OPENROUTER_API_KEY="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"

# If no argument or --serve provided, launch the Closed-Loop Research Server
if [ -z "$1" ] || [ "$1" == "--serve" ]; then
  echo "🚀 Launching Closed-Loop LLM PCG Research Server & Game Engine..."
  echo "🌐 Server URL: http://localhost:8080"
  
  # Ensure binary is compiled
  g++ -O2 -std=c++17 program.cpp -o dungeon_map

  # Launch browser if available
  if command -v chromium &> /dev/null; then
    (sleep 1 && chromium http://localhost:8080) &
  elif command -v google-chrome &> /dev/null; then
    (sleep 1 && google-chrome http://localhost:8080) &
  elif command -v xdg-open &> /dev/null; then
    (sleep 1 && xdg-open http://localhost:8080) &
  fi

  python3 server.py
  exit 0
fi

# Mode 2: Single-prompt generation
USER_INPUT="$1"

echo "🔮 Generating config from LLM..."
echo "📝 Prompt: $USER_INPUT"

RESPONSE=$(curl -s https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d "{
    \"model\": \"google/gemma-3-4b-it:free\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"You are a dungeon configuration generator.\n\nRules:\n- Output ONLY raw JSON\n- No markdown\n- No explanation\n- No duplicate keys\n\nSchema:\n{\n  \\\"theme\\\": \\\"dark\\\" | \\\"light\\\",\n  \\\"layout_style\\\": \\\"corridor-heavy\\\" | \\\"room-heavy\\\",\n  \\\"corridor_width\\\": integer (1-3),\n  \\\"room_density\\\": float (0.0-1.0),\n  \\\"enemy_density\\\": float (0.0-1.0),\n  \\\"enemy_type\\\": \\\"ambush\\\" | \\\"patrol\\\",\n  \\\"difficulty\\\": float (0.0-1.0),\n  \\\"trap_probability\\\": float (0.0-1.0),\n  \\\"visibility\\\": \\\"low\\\" | \\\"normal\\\",\n  \\\"reward_density\\\": float (0.0-1.0)\n}\n\nGenerate a dungeon based on this description:\n$USER_INPUT\"
      }
    ]
  }")

echo "$RESPONSE" > raw_output.json

echo "🧹 Extracting JSON..."
cat raw_output.json | jq -r '.choices[0].message.content' \
  | sed 's/```json//g' \
  | sed 's/```//g' > input.txt

echo "🗺️ Running generator..."
g++ -O2 -std=c++17 program.cpp -o dungeon_map
./dungeon_map input.txt dungeon_map.png
if command -v chromium &> /dev/null; then
  chromium dungeon_map.png
fi
echo "✅ Done!"
