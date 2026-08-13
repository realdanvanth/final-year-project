/*
 * ╔══════════════════════════════════════════════════════════╗
 * ║          DUNGEON CRAWLER  —  Map Generator v2            ║
 * ║                                                          ║
 * ║  Two ways to use this program:                           ║
 * ║                                                          ║
 * ║  1. CLI mode  (classic)                                  ║
 * ║     ./dungeon input.json dungeon_map.png                 ║
 * ║                                                          ║
 * ║  2. Web UI mode  (new!)                                  ║
 * ║     ./dungeon --serve                                    ║
 * ║     Then open  http://localhost:8080  in your browser.   ║
 * ║     Fill in the JSON form, hit Generate, download PNG.   ║
 * ╚══════════════════════════════════════════════════════════╝
 *
 * Build (Linux / macOS):
 *   g++ -O2 -std=c++17 -o dungeon dungeon_crawler.cpp -lpthread
 *
 * Build (Windows / MSVC):
 *   cl /O2 /std:c++17 dungeon_crawler.cpp /link ws2_32.lib
 *
 * Dependencies:
 *   stb_image_write.h  — single-header PNG writer (drop next to this file)
 *   Everything else is standard C++17 + POSIX sockets (or WinSock).
 *
 * ── Tile legend ────────────────────────────────────────────
 *   WALL      solid stone
 *   FLOOR     walkable room floor
 *   CORRIDOR  connecting passage
 *   DOOR      room entry point
 *   TRAP      hidden danger
 *   ENEMY     monster spawn
 *   CHEST     reward chest
 *   START     player start position
 *   EXIT      dungeon exit
 *   FOG       low-visibility overlay zone
 */

// ─────────────────────────────────────────────────────────────
//  Platform detection for socket code
// ─────────────────────────────────────────────────────────────
#ifdef _WIN32
#define _WIN32_WINNT 0x0601
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
using ssize_t = int;
#define CLOSE_SOCKET(s) closesocket(s)
#define SOCK_ERR SOCKET_ERROR
using socket_t = SOCKET;
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#define CLOSE_SOCKET(s) close(s)
#define SOCK_ERR (-1)
using socket_t = int;
#endif

// ─────────────────────────────────────────────────────────────
//  Standard includes
// ─────────────────────────────────────────────────────────────
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstring>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

// ─────────────────────────────────────────────────────────────
//  stb_image_write  (PNG encoder, header-only)
// ─────────────────────────────────────────────────────────────
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

// ══════════════════════════════════════════════════════════════
//  SECTION 1 — Configuration
//  All dungeon parameters live here.  parse_config() fills this
//  from a JSON string; defaults are safe and balanced.
// ══════════════════════════════════════════════════════════════

struct Config {
  // Visual
  std::string theme = "dark"; // "dark" | "light"

  // Layout
  std::string layout_style =
      "balanced";         // "room-heavy" | "corridor-heavy" | "balanced"
  int corridor_width = 1; // 1–3 tiles wide

  // Density  (0.0 – 1.0)
  float room_density = 0.5f;      // how many rooms to attempt
  float enemy_density = 0.15f;    // fraction of walkable tiles with enemies
  float trap_probability = 0.12f; // per-tile trap chance in corridors
  float reward_density = 0.08f;   // per-tile chest chance in rooms

  // Behaviour
  std::string enemy_type = "ambush"; // "ambush" | "roaming"
  float difficulty = 0.5f;           // 0–1, scales enemy/trap counts
  std::string visibility = "normal"; // "low" | "normal"

  // Map dimensions (overridable from JSON)
  int map_width = 0; // 0 = auto
  int map_height = 0;

  // Seed (overridable from JSON; 0 = auto-generate)
  unsigned seed = 0;
};

// ── Tiny JSON extractor ───────────────────────────────────────
//  Pulls one value out of a flat JSON object by key.
//  No dependencies, handles strings, numbers, and booleans.
static std::string json_get(const std::string &json, const std::string &key) {
  auto pos = json.find('"' + key + '"');
  if (pos == std::string::npos)
    return "";
  pos = json.find(':', pos);
  if (pos == std::string::npos)
    return "";
  ++pos;
  // skip whitespace
  while (pos < json.size() && std::isspace((unsigned char)json[pos]))
    ++pos;
  if (pos >= json.size())
    return "";
  if (json[pos] == '"') {
    ++pos;
    auto end = json.find('"', pos);
    return json.substr(pos, end - pos);
  }
  auto end = json.find_first_of(",}\n", pos);
  auto val = json.substr(pos, end - pos);
  // trim trailing whitespace
  while (!val.empty() && std::isspace((unsigned char)val.back()))
    val.pop_back();
  return val;
}

static Config parse_config(const std::string &json) {
  Config c;
  auto str = [&](const std::string &k, std::string &out) {
    auto v = json_get(json, k);
    if (!v.empty())
      out = v;
  };
  auto flt = [&](const std::string &k, float &out) {
    auto v = json_get(json, k);
    if (!v.empty())
      try {
        out = std::stof(v);
      } catch (...) {
      }
  };
  auto integer = [&](const std::string &k, int &out) {
    auto v = json_get(json, k);
    if (!v.empty())
      try {
        out = std::stoi(v);
      } catch (...) {
      }
  };

  str("theme", c.theme);
  str("layout_style", c.layout_style);
  str("enemy_type", c.enemy_type);
  str("visibility", c.visibility);
  integer("corridor_width", c.corridor_width);
  integer("map_width", c.map_width);
  integer("map_height", c.map_height);
  flt("room_density", c.room_density);
  flt("enemy_density", c.enemy_density);
  flt("trap_probability", c.trap_probability);
  flt("reward_density", c.reward_density);
  flt("difficulty", c.difficulty);

  // Read seed from JSON (0 = auto-generate later)
  {
    auto sv = json_get(json, "seed");
    if (!sv.empty()) {
      try { c.seed = static_cast<unsigned>(std::stoul(sv)); } catch (...) {}
    }
  }

  // Clamp ranges
  c.corridor_width = std::clamp(c.corridor_width, 1, 3);
  c.room_density = std::clamp(c.room_density, 0.0f, 1.0f);
  c.enemy_density = std::clamp(c.enemy_density, 0.0f, 1.0f);
  c.trap_probability = std::clamp(c.trap_probability, 0.0f, 1.0f);
  c.reward_density = std::clamp(c.reward_density, 0.0f, 1.0f);
  c.difficulty = std::clamp(c.difficulty, 0.0f, 1.0f);
  return c;
}

static Config parse_config_file(const std::string &path) {
  std::ifstream f(path);
  if (!f) {
    std::cerr << "Warning: cannot open '" << path << "', using defaults.\n";
    return {};
  }
  std::ostringstream ss;
  ss << f.rdbuf();
  return parse_config(ss.str());
}

// ══════════════════════════════════════════════════════════════
//  SECTION 2 — Map & Tile types
// ══════════════════════════════════════════════════════════════

enum Tile : uint8_t {
  WALL = 0,
  FLOOR,
  CORRIDOR,
  DOOR,
  TRAP,
  ENEMY,
  CHEST,
  START,
  EXIT,
  FOG,
  TILE_COUNT
};

static const char *tile_name(Tile t) {
  static const char *names[] = {"WALL",  "FLOOR", "CORRIDOR", "DOOR", "TRAP",
                                "ENEMY", "CHEST", "START",    "EXIT", "FOG"};
  return (t < TILE_COUNT) ? names[t] : "?";
}

struct Map {
  int W = 0, H = 0;
  std::vector<Tile> cells;

  void init(int w, int h) {
    W = w;
    H = h;
    cells.assign(w * h, WALL);
  }
  Tile &at(int x, int y) { return cells[y * W + x]; }
  const Tile &at(int x, int y) const { return cells[y * W + x]; }
  bool inBounds(int x, int y) const {
    return x >= 0 && y >= 0 && x < W && y < H;
  }
};

// ══════════════════════════════════════════════════════════════
//  SECTION 3 — Dungeon Generator
//  Rooms are placed by rejection sampling, then connected with
//  L-shaped corridors.  Special tiles are sprinkled last.
// ══════════════════════════════════════════════════════════════

struct Room {
  int x, y, w, h;
  int cx() const { return x + w / 2; }
  int cy() const { return y + h / 2; }

  // Returns true if this room overlaps 'o' (with 1-tile padding)
  bool overlaps(const Room &o) const {
    return x < o.x + o.w + 2 && x + w + 2 > o.x && y < o.y + o.h + 2 &&
           y + h + 2 > o.y;
  }
};

class DungeonGenerator {
public:
  Map map;
  std::vector<Room> rooms;

  DungeonGenerator(const Config &cfg, unsigned seed = 42)
      : cfg_(cfg), rng_(seed) {}

  void generate() {
    // ── Decide map dimensions ──────────────────
    bool corridor_heavy =
        cfg_.layout_style.find("corridor") != std::string::npos;
    int W = cfg_.map_width > 0 ? cfg_.map_width : (corridor_heavy ? 140 : 120);
    int H = cfg_.map_height > 0 ? cfg_.map_height : (corridor_heavy ? 90 : 80);
    map.init(W, H);

    place_rooms(W, H, corridor_heavy);
    connect_rooms();
    place_doors();
    place_start_exit();
    place_traps();
    place_enemies();
    place_chests();
  }


private:
  const Config &cfg_;
  std::mt19937 rng_;

  // ── Helper: set a tile only if it is currently a WALL ──
  void carve(int x, int y, Tile t = CORRIDOR) {
    if (map.inBounds(x, y) && map.at(x, y) == WALL)
      map.at(x, y) = t;
  }

  // ── 3a. Room placement ─────────────────────────────────
  void place_rooms(int W, int H, bool corridor_heavy) {
    // corridor-heavy → fewer small rooms; room-heavy → more, bigger
    int max_rooms =
        static_cast<int>(cfg_.room_density * (corridor_heavy ? 14 : 24)) + 5;
    int min_w = corridor_heavy ? 3 : 4, max_w = corridor_heavy ? 7 : 10;
    int min_h = corridor_heavy ? 3 : 4, max_h = corridor_heavy ? 7 : 10;

    std::uniform_int_distribution<int> dw(min_w, max_w), dh(min_h, max_h);
    std::uniform_int_distribution<int> dx(1, W - max_w - 2);
    std::uniform_int_distribution<int> dy(1, H - max_h - 2);

    for (int attempt = 0; attempt < 500 && (int)rooms.size() < max_rooms;
         ++attempt) {
      Room r{dx(rng_), dy(rng_), dw(rng_), dh(rng_)};
      // make sure it fits within the map
      if (r.x + r.w >= W - 1 || r.y + r.h >= H - 1)
        continue;
      // reject if overlapping any existing room
      bool ok = std::none_of(rooms.begin(), rooms.end(),
                             [&](const Room &e) { return r.overlaps(e); });
      if (!ok)
        continue;
      rooms.push_back(r);
      // carve interior
      for (int ry = r.y; ry < r.y + r.h; ++ry)
        for (int rx = r.x; rx < r.x + r.w; ++rx)
          map.at(rx, ry) = FLOOR;
    }
  }

  // ── 3b. Connect rooms with L-shaped corridors ──────────
  void connect_rooms() {
    if (rooms.size() < 2)
      return;

    // Shuffle room order so connections aren't always left-to-right
    std::vector<int> order(rooms.size());
    std::iota(order.begin(), order.end(), 0);
    std::shuffle(order.begin(), order.end(), rng_);

    // Connect each consecutive pair (guarantees full connectivity)
    for (int i = 1; i < (int)order.size(); ++i)
      carve_corridor(rooms[order[i - 1]], rooms[order[i]]);

    // Extra random connections — higher difficulty = more loops = more ambush
    // spots
    int extra = static_cast<int>(cfg_.difficulty * rooms.size() * 0.3f);
    std::uniform_int_distribution<int> ri(0, (int)rooms.size() - 1);
    for (int i = 0; i < extra; ++i)
      carve_corridor(rooms[ri(rng_)], rooms[ri(rng_)]);
  }

  void carve_corridor(const Room &a, const Room &b) {
    int ax = a.cx(), ay = a.cy(), bx = b.cx(), by = b.cy();
    int cw = cfg_.corridor_width;
    std::bernoulli_distribution coin(0.5);

    // L-shape: horizontal then vertical, or vice versa
    if (coin(rng_)) {
      carve_hline(ax, bx, ay, cw);
      carve_vline(bx, ay, by, cw);
    } else {
      carve_vline(ax, ay, by, cw);
      carve_hline(ax, bx, by, cw);
    }
  }

  void carve_hline(int x1, int x2, int y, int w) {
    if (x1 > x2)
      std::swap(x1, x2);
    for (int x = x1; x <= x2; ++x)
      for (int dw = 0; dw < w; ++dw)
        carve(x, y + dw);
  }

  void carve_vline(int x, int y1, int y2, int w) {
    if (y1 > y2)
      std::swap(y1, y2);
    for (int y = y1; y <= y2; ++y)
      for (int dw = 0; dw < w; ++dw)
        carve(x + dw, y);
  }

  // ── 3c. Doors — placed where corridors meet room edges ─
  void place_doors() {
    for (auto &room : rooms) {
      auto try_door = [&](int x, int y) {
        if (map.inBounds(x, y) && map.at(x, y) == CORRIDOR)
          map.at(x, y) = DOOR;
      };
      for (int x = room.x; x < room.x + room.w; ++x) {
        try_door(x, room.y - 1);
        try_door(x, room.y + room.h);
      }
      for (int y = room.y; y < room.y + room.h; ++y) {
        try_door(room.x - 1, y);
        try_door(room.x + room.w, y);
      }
    }
  }

  // Helper: Returns true if (x,y) is inside or near the starting room
  bool in_start_room(int x, int y) const {
    if (rooms.empty()) return false;
    const auto &s = rooms.front();
    // Padding of 3 tiles around start room
    return (x >= s.x - 3 && x < s.x + s.w + 3 && y >= s.y - 3 && y < s.y + s.h + 3);
  }

  // ── 3d. Start & Exit ───────────────────────────────────
  //  Start = first room placed.
  //  Exit  = the room whose center is FARTHEST from Start
  //          (guarantees the player must traverse the dungeon).
  void place_start_exit() {
    if (rooms.empty())
      return;
    auto &s = rooms.front();
    map.at(s.cx(), s.cy()) = START;

    // Find the room farthest from the start room
    int best_idx = (int)rooms.size() - 1;
    double best_dist = 0.0;
    for (int i = 1; i < (int)rooms.size(); ++i) {
      double dx = rooms[i].cx() - s.cx();
      double dy = rooms[i].cy() - s.cy();
      double d = dx * dx + dy * dy;
      if (d > best_dist) {
        best_dist = d;
        best_idx = i;
      }
    }
    map.at(rooms[best_idx].cx(), rooms[best_idx].cy()) = EXIT;
  }

  // ── 3e. Traps (corridors & floors) ────────────────────
  void place_traps() {
    float corridor_prob = cfg_.trap_probability * cfg_.difficulty * 0.4f;
    float floor_prob = cfg_.trap_probability * cfg_.difficulty * 0.15f;
    std::uniform_real_distribution<float> roll(0.f, 1.f);
    for (int y = 0; y < map.H; ++y)
      for (int x = 0; x < map.W; ++x) {
        if (in_start_room(x, y)) continue; // Keep start area safe!
        Tile &t = map.at(x, y);
        if (t == CORRIDOR && roll(rng_) < corridor_prob)
          t = TRAP;
        else if (t == FLOOR && roll(rng_) < floor_prob)
          t = TRAP;
      }
  }

  // ── 3f. Enemies ────────────────────────────────────────
  void place_enemies() {
    bool ambush = (cfg_.enemy_type == "ambush");
    float p = cfg_.enemy_density * cfg_.difficulty * 0.2f;
    std::uniform_real_distribution<float> roll(0.f, 1.f);

    for (int y = 0; y < map.H; ++y) {
      for (int x = 0; x < map.W; ++x) {
        if (in_start_room(x, y)) continue; // Keep start area safe!
        Tile &t = map.at(x, y);
        if (ambush) {
          if (t == CORRIDOR && is_junction(x, y) && roll(rng_) < p * 0.5f)
            t = ENEMY;
          else if (t == FLOOR && is_corner(x, y) && roll(rng_) < p * 0.4f)
            t = ENEMY;
        } else {
          if ((t == FLOOR || t == CORRIDOR) && roll(rng_) < p * 0.2f)
            t = ENEMY;
        }
      }
    }
  }




  // Returns true if this tile has 3+ walkable neighbours (junction)
  bool is_junction(int x, int y) {
    int walkable = 0;
    const int dx[] = {1, -1, 0, 0};
    const int dy[] = {0, 0, 1, -1};
    for (int i = 0; i < 4; ++i) {
      int nx = x + dx[i], ny = y + dy[i];
      if (map.inBounds(nx, ny) && map.at(nx, ny) != WALL)
        ++walkable;
    }
    return walkable >= 3;
  }

  // Returns true if this tile has 2+ wall neighbours (corner / dead-end)
  bool is_corner(int x, int y) {
    int walls = 0;
    const int dx[] = {1, -1, 0, 0};
    const int dy[] = {0, 0, 1, -1};
    for (int i = 0; i < 4; ++i) {
      int nx = x + dx[i], ny = y + dy[i];
      if (!map.inBounds(nx, ny) || map.at(nx, ny) == WALL)
        ++walls;
    }
    return walls >= 2;
  }

  // ── 3g. Chests (inside rooms only) ────────────────────
  void place_chests() {
    float p = cfg_.reward_density;
    std::uniform_real_distribution<float> roll(0.f, 1.f);
    for (auto &room : rooms)
      for (int ry = room.y; ry < room.y + room.h; ++ry)
        for (int rx = room.x; rx < room.x + room.w; ++rx) {
          Tile &t = map.at(rx, ry);
          if (t == FLOOR && roll(rng_) < p)
            t = CHEST;
        }
  }

  // ── 3h. Fog (low visibility mode) ─────────────────────
  void apply_fog() {
    for (int y = 0; y < map.H; ++y)
      for (int x = 0; x < map.W; ++x)
        if (map.at(x, y) == CORRIDOR && !near_room(x, y, 3))
          map.at(x, y) = FOG;
  }

  bool near_room(int x, int y, int dist) const {
    for (auto &r : rooms)
      if (x >= r.x - dist && x < r.x + r.w + dist && y >= r.y - dist &&
          y < r.y + r.h + dist)
        return true;
    return false;
  }
};

// ══════════════════════════════════════════════════════════════
//  SECTION 4 — Procedural Textures & Renderer
//
//  Instead of flat colours, each tile type gets a procedurally
//  generated texture built from:
//    • value noise  — organic variation
//    • hash-based   — deterministic per pixel, no state needed
//    • per-tile rules — cracks for walls, grain for floors, etc.
// ══════════════════════════════════════════════════════════════

struct RGB {
  uint8_t r, g, b;
};

// ── Fast integer hash (gives a pseudo-random float 0..1) ──────
static float hash2(int x, int y, int seed = 0) {
  unsigned h = static_cast<unsigned>(x * 1619 + y * 31337 + seed * 6791);
  h ^= h >> 16;
  h *= 0x45d9f3b;
  h ^= h >> 16;
  return static_cast<float>(h & 0xFFFF) / 65535.f;
}

// ── Simple value noise (smooth variation) ─────────────────────
static float value_noise(float px, float py, int seed = 0) {
  int ix = static_cast<int>(std::floor(px));
  int iy = static_cast<int>(std::floor(py));
  float fx = px - ix, fy = py - iy;
  // smoothstep
  float ux = fx * fx * (3 - 2 * fx);
  float uy = fy * fy * (3 - 2 * fy);
  float v00 = hash2(ix, iy, seed);
  float v10 = hash2(ix + 1, iy, seed);
  float v01 = hash2(ix, iy + 1, seed);
  float v11 = hash2(ix + 1, iy + 1, seed);
  return v00 + (v10 - v00) * ux + (v01 - v00) * uy +
         (v00 - v10 - v01 + v11) * ux * uy;
}

// ── Fractal noise (layered octaves) ───────────────────────────
static float fbm(float px, float py, int octaves = 3, int seed = 0) {
  float val = 0, amp = 0.5f, freq = 1.f, max_amp = 0;
  for (int o = 0; o < octaves; ++o) {
    val += value_noise(px * freq, py * freq, seed + o) * amp;
    max_amp += amp;
    amp *= 0.5f;
    freq *= 2.1f;
  }
  return val / max_amp;
}

// ── Lerp between two colours ──────────────────────────────────
static RGB lerp_rgb(RGB a, RGB b, float t) {
  return {static_cast<uint8_t>(a.r + (b.r - a.r) * t),
          static_cast<uint8_t>(a.g + (b.g - a.g) * t),
          static_cast<uint8_t>(a.b + (b.b - a.b) * t)};
}

// ── Generate one pixel of procedural texture for a tile type ──
//  (px, py) are pixel coordinates within the tile (0..tsize-1)
//  (tx, ty) are tile grid coordinates (for global variation)
//  Returns the final RGB for this pixel.
static RGB texture_pixel(Tile tile, int px, int py, int tx, int ty, int tsize,
                         bool dark_theme) {
  // Global position used for large-scale variation
  float gx = (tx * tsize + px) / 4.f;
  float gy = (ty * tsize + py) / 4.f;

  // Local position (0..1) within this tile
  float lx = static_cast<float>(px) / tsize;
  float ly = static_cast<float>(py) / tsize;

  // Small noise for micro-detail
  float n = fbm(gx * 0.5f, gy * 0.5f, 3, 0); // slow variation
  float n2 = hash2(tx * tsize + px, ty * tsize + py, 7) * 0.12f; // grain

  switch (tile) {

  // ── WALL: dark stone vs light marble ─────────────────
  case WALL: {
    RGB base = dark_theme ? RGB{16, 14, 24} : RGB{203, 213, 225};
    RGB light = dark_theme ? RGB{32, 28, 46} : RGB{226, 232, 240};
    RGB crack = dark_theme ? RGB{8, 7, 12} : RGB{148, 163, 184};
    // Large-scale noise gives stone block variation
    float stone = fbm(gx * 0.3f, gy * 0.3f, 2, 1);
    // Crack pattern: sharp threshold on a different frequency
    float c = fbm(gx * 1.2f, gy * 1.2f, 4, 42);
    bool is_crack = (c > 0.72f);
    RGB col = lerp_rgb(base, light, stone);
    if (is_crack)
      col = lerp_rgb(col, crack, 0.8f);
    col.r = static_cast<uint8_t>(std::clamp(col.r + n2 * 10 - 5, 0.f, 255.f));
    col.g = static_cast<uint8_t>(std::clamp(col.g + n2 * 10 - 5, 0.f, 255.f));
    col.b = static_cast<uint8_t>(std::clamp(col.b + n2 * 10 - 5, 0.f, 255.f));
    return col;
  }

  // ── FLOOR: worn stone vs pure white room floor ───────
  case FLOOR: {
    RGB base = dark_theme ? RGB{50, 45, 68} : RGB{255, 255, 255};
    RGB grout = dark_theme ? RGB{30, 27, 42} : RGB{226, 232, 240};
    // Tile grout lines every ~8 pixels
    bool grout_line = (px % 8 == 0 || py % 8 == 0);
    float wear = fbm(gx * 0.4f, gy * 0.4f, 2, 2) * 0.3f;
    RGB col = lerp_rgb(base, grout, grout_line ? 0.6f : 0.f);
    col.r = static_cast<uint8_t>(
        std::clamp(col.r * (0.85f + wear) + n2 * 10, 0.f, 255.f));
    col.g = static_cast<uint8_t>(
        std::clamp(col.g * (0.85f + wear) + n2 * 10, 0.f, 255.f));
    col.b = static_cast<uint8_t>(
        std::clamp(col.b * (0.85f + wear) + n2 * 10, 0.f, 255.f));
    return col;
  }

  // ── CORRIDOR: rougher, narrower stone ────────────────
  case CORRIDOR: {
    RGB base = dark_theme ? RGB{34, 30, 50} : RGB{241, 245, 249};
    RGB dark2 = dark_theme ? RGB{20, 18, 30} : RGB{203, 213, 225};
    float f = fbm(gx * 0.6f, gy * 0.6f, 3, 3);
    RGB col = lerp_rgb(dark2, base, f);
    col.r = static_cast<uint8_t>(std::clamp(col.r + n2 * 10 - 5, 0.f, 255.f));
    col.g = static_cast<uint8_t>(std::clamp(col.g + n2 * 10 - 5, 0.f, 255.f));
    col.b = static_cast<uint8_t>(std::clamp(col.b + n2 * 10 - 5, 0.f, 255.f));
    return col;
  }


  // ── DOOR: aged wood planks ────────────────────────────
  case DOOR: {
    RGB plank = dark_theme ? RGB{110, 70, 30} : RGB{160, 100, 45};
    RGB grain = dark_theme ? RGB{80, 50, 20} : RGB{130, 80, 35};
    // Vertical wood grain lines
    float g = fbm(static_cast<float>(px) * 0.4f, gy * 0.05f, 2, 4);
    bool stripe = ((px / 3) % 2 == 0);
    RGB col = lerp_rgb(grain, plank, g);
    if (stripe)
      col = lerp_rgb(col, grain, 0.25f);
    // Iron banding every ~6 pixels vertically
    bool band = (py % 6 <= 1);
    if (band)
      col = lerp_rgb(col, RGB{50, 50, 55}, 0.7f);
    return col;
  }

  // ── TRAP: dark floor with a faint pressure plate glyph
  case TRAP: {
    RGB base = dark_theme ? RGB{45, 18, 18} : RGB{170, 80, 70};
    RGB mark = dark_theme ? RGB{160, 40, 40} : RGB{220, 50, 40};
    // Circular pressure plate
    float cx2 = lx - 0.5f, cy2 = ly - 0.5f;
    float dist = std::sqrt(cx2 * cx2 + cy2 * cy2);
    bool ring = (dist > 0.28f && dist < 0.38f);
    bool cross = (std::abs(lx - 0.5f) < 0.06f || std::abs(ly - 0.5f) < 0.06f) &&
                 dist < 0.38f;
    float noise = fbm(gx * 0.4f, gy * 0.4f, 2, 5) * 0.2f;
    RGB col = lerp_rgb(base, RGB{30, 12, 12}, noise);
    if (ring || cross)
      col = lerp_rgb(col, mark, 0.8f);
    return col;
  }

  // ── ENEMY: menacing red with skull-ish pattern ────────
  case ENEMY: {
    RGB base = dark_theme ? RGB{140, 28, 28} : RGB{200, 55, 50};
    RGB glow = dark_theme ? RGB{200, 50, 50} : RGB{240, 80, 60};
    float cx2 = lx - 0.5f, cy2 = ly - 0.5f;
    float dist = std::sqrt(cx2 * cx2 + cy2 * cy2);
    float radial = 1.f - std::min(dist * 2.f, 1.f);
    RGB col = lerp_rgb(base, glow, radial * 0.7f);
    // Pulsing ring
    bool ring = (dist > 0.30f && dist < 0.36f);
    if (ring)
      col = lerp_rgb(col, glow, 0.9f);
    return col;
  }

  // ── CHEST: golden metal with rivets ───────────────────
  case CHEST: {
    RGB gold = dark_theme ? RGB{200, 155, 25} : RGB{230, 185, 40};
    RGB dark3 = dark_theme ? RGB{120, 80, 10} : RGB{160, 120, 20};
    RGB rivet = dark_theme ? RGB{240, 200, 60} : RGB{255, 220, 80};
    float grain =
        fbm(static_cast<float>(px) * 0.3f, static_cast<float>(py) * 0.3f, 2, 6);
    RGB col = lerp_rgb(dark3, gold, 0.5f + grain * 0.5f);
    // Corner rivets
    bool rv = ((px < 2 || px >= tsize - 2) && (py < 2 || py >= tsize - 2));
    if (rv)
      col = lerp_rgb(col, rivet, 0.9f);
    // Horizontal latch band
    if (py >= tsize / 2 - 1 && py <= tsize / 2 + 1)
      col = lerp_rgb(col, dark3, 0.5f);
    return col;
  }

  // ── START: glowing green portal ──────────────────────
  case START: {
    RGB inner = dark_theme ? RGB{80, 240, 160} : RGB{60, 200, 130};
    RGB outer = dark_theme ? RGB{20, 80, 50} : RGB{20, 90, 60};
    float cx2 = lx - 0.5f, cy2 = ly - 0.5f;
    float dist = std::sqrt(cx2 * cx2 + cy2 * cy2);
    float t2 = 1.f - std::min(dist * 2.2f, 1.f);
    // Swirl effect
    float angle = std::atan2(cy2, cx2);
    float swirl = std::sin(angle * 4 + dist * 8) * 0.15f;
    return lerp_rgb(outer, inner, std::clamp(t2 + swirl, 0.f, 1.f));
  }

  // ── EXIT: blue/purple vortex ─────────────────────────
  case EXIT: {
    RGB inner = dark_theme ? RGB{100, 160, 255} : RGB{80, 140, 230};
    RGB outer = dark_theme ? RGB{20, 30, 90} : RGB{30, 50, 140};
    float cx2 = lx - 0.5f, cy2 = ly - 0.5f;
    float dist = std::sqrt(cx2 * cx2 + cy2 * cy2);
    float t2 = 1.f - std::min(dist * 2.2f, 1.f);
    float angle = std::atan2(cy2, cx2);
    float swirl = std::sin(angle * 6 - dist * 10) * 0.15f;
    return lerp_rgb(outer, inner, std::clamp(t2 + swirl, 0.f, 1.f));
  }

  // ── FOG: murky, barely-visible ────────────────────────
  case FOG: {
    RGB base = dark_theme ? RGB{18, 16, 28} : RGB{90, 85, 75};
    RGB misty = dark_theme ? RGB{28, 25, 42} : RGB{110, 104, 92};
    float f = fbm(gx * 0.2f, gy * 0.2f, 4, 8);
    return lerp_rgb(base, misty, f * 0.6f);
  }

  default:
    return {0, 0, 0};
  }
}

// ── Grid line overlay (thin border around each tile) ──────────
static RGB apply_grid(RGB c, int px, int py, bool dark_theme) {
  if (px == 0 || py == 0) {
    uint8_t gv = dark_theme ? 8 : 45;
    return {static_cast<uint8_t>((c.r + gv) / 2),
            static_cast<uint8_t>((c.g + gv) / 2),
            static_cast<uint8_t>((c.b + gv) / 2)};
  }
  return c;
}

// ── Render the full map to a PNG byte buffer ──────────────────
static std::vector<uint8_t> render_map(const Map &map, const Config &cfg) {
  const int TILE = 12; // pixels per tile (12 gives nice detail for textures)
  int imgW = map.W * TILE;
  int imgH = map.H * TILE;
  bool dark = (cfg.theme != "light");

  std::vector<uint8_t> img(imgW * imgH * 3, 0);

  for (int ty = 0; ty < map.H; ++ty) {
    for (int tx = 0; tx < map.W; ++tx) {
      Tile t = map.at(tx, ty);
      for (int py = 0; py < TILE; ++py) {
        for (int px = 0; px < TILE; ++px) {
          RGB col = texture_pixel(t, px, py, tx, ty, TILE, dark);
          col = apply_grid(col, px, py, dark);
          int idx = ((ty * TILE + py) * imgW + (tx * TILE + px)) * 3;
          img[idx + 0] = col.r;
          img[idx + 1] = col.g;
          img[idx + 2] = col.b;
        }
      }
    }
  }

  // ── Legend strip at the bottom (24px) ─────────────────
  const int LHEIGHT = 24;
  img.resize((imgH + LHEIGHT) * imgW * 3, 0);
  int n_tiles = static_cast<int>(TILE_COUNT);
  int sw = imgW / n_tiles; // width per legend swatch

  for (int i = 0; i < n_tiles; ++i) {
    Tile t = static_cast<Tile>(i);
    for (int py = 0; py < LHEIGHT; ++py) {
      for (int px = 0; px < sw; ++px) {
        // Sample a representative pixel from that tile type
        RGB col = texture_pixel(t, px % TILE, py % TILE, i, 99, TILE, dark);
        int ix = i * sw + px, iy = imgH + py;
        if (ix >= imgW)
          break;
        int idx = (iy * imgW + ix) * 3;
        img[idx + 0] = col.r;
        img[idx + 1] = col.g;
        img[idx + 2] = col.b;
      }
    }
  }

  return img; // caller saves to file (imgW x imgH+LHEIGHT, 3 channels)
}

static std::string export_map_json_str(const DungeonGenerator &gen, const Config &cfg, unsigned seed) {
  std::ostringstream ss;
  ss << "{\n";
  ss << "  \"width\": " << gen.map.W << ",\n";
  ss << "  \"height\": " << gen.map.H << ",\n";
  ss << "  \"seed\": " << seed << ",\n";
  ss << "  \"config\": {\n";
  ss << "    \"theme\": \"" << cfg.theme << "\",\n";
  ss << "    \"layout_style\": \"" << cfg.layout_style << "\",\n";
  ss << "    \"corridor_width\": " << cfg.corridor_width << ",\n";
  ss << "    \"room_density\": " << cfg.room_density << ",\n";
  ss << "    \"enemy_density\": " << cfg.enemy_density << ",\n";
  ss << "    \"enemy_type\": \"" << cfg.enemy_type << "\",\n";
  ss << "    \"difficulty\": " << cfg.difficulty << ",\n";
  ss << "    \"trap_probability\": " << cfg.trap_probability << ",\n";
  ss << "    \"visibility\": \"" << cfg.visibility << "\",\n";
  ss << "    \"reward_density\": " << cfg.reward_density << "\n";
  ss << "  },\n";

  ss << "  \"rooms\": [\n";
  for (size_t i = 0; i < gen.rooms.size(); ++i) {
    const auto &r = gen.rooms[i];
    ss << "    {\"x\": " << r.x << ", \"y\": " << r.y << ", \"w\": " << r.w << ", \"h\": " << r.h << "}"
       << (i + 1 < gen.rooms.size() ? ",\n" : "\n");
  }
  ss << "  ],\n";

  int start_x = -1, start_y = -1;
  int exit_x = -1, exit_y = -1;
  struct Entity { int x, y; std::string type; };
  std::vector<Entity> enemies;
  std::vector<Entity> traps;
  std::vector<Entity> chests;

  for (int y = 0; y < gen.map.H; ++y) {
    for (int x = 0; x < gen.map.W; ++x) {
      Tile t = gen.map.at(x, y);
      if (t == START) { start_x = x; start_y = y; }
      else if (t == EXIT) { exit_x = x; exit_y = y; }
      else if (t == ENEMY) { enemies.push_back({x, y, cfg.enemy_type}); }
      else if (t == TRAP) { traps.push_back({x, y, "trap"}); }
      else if (t == CHEST) { chests.push_back({x, y, "chest"}); }
    }
  }

  ss << "  \"start\": {\"x\": " << start_x << ", \"y\": " << start_y << "},\n";
  ss << "  \"exit\": {\"x\": " << exit_x << ", \"y\": " << exit_y << "},\n";

  ss << "  \"enemies\": [\n";
  for (size_t i = 0; i < enemies.size(); ++i) {
    ss << "    {\"x\": " << enemies[i].x << ", \"y\": " << enemies[i].y << ", \"type\": \"" << enemies[i].type << "\"}"
       << (i + 1 < enemies.size() ? ",\n" : "\n");
  }
  ss << "  ],\n";

  ss << "  \"traps\": [\n";
  for (size_t i = 0; i < traps.size(); ++i) {
    ss << "    {\"x\": " << traps[i].x << ", \"y\": " << traps[i].y << "}"
       << (i + 1 < traps.size() ? ",\n" : "\n");
  }
  ss << "  ],\n";

  ss << "  \"chests\": [\n";
  for (size_t i = 0; i < chests.size(); ++i) {
    ss << "    {\"x\": " << chests[i].x << ", \"y\": " << chests[i].y << "}"
       << (i + 1 < chests.size() ? ",\n" : "\n");
  }
  ss << "  ],\n";

  ss << "  \"tiles\": [\n";
  for (int y = 0; y < gen.map.H; ++y) {
    ss << "    [";
    for (int x = 0; x < gen.map.W; ++x) {
      ss << static_cast<int>(gen.map.at(x, y)) << (x + 1 < gen.map.W ? "," : "");
    }
    ss << "]" << (y + 1 < gen.map.H ? ",\n" : "\n");
  }
  ss << "  ]\n";
  ss << "}\n";
  return ss.str();
}

// Save to PNG file ──────────────────────────────────────────
static bool save_png(const std::string &path, const std::vector<uint8_t> &img,
                     int W, int H) {
  return stbi_write_png(path.c_str(), W, H, 3, img.data(), W * 3) != 0;
}


// ══════════════════════════════════════════════════════════════
//  SECTION 5 — Built-in Web Server
//
//  A minimal HTTP/1.0 server so you can edit JSON in a browser
//  and get a PNG back without touching the command line.
//
//  Routes:
//    GET  /          → HTML form page
//    POST /generate  → accepts JSON body, returns PNG bytes
// ══════════════════════════════════════════════════════════════

// ── HTML page (served as GET /) ───────────────────────────────
//  The form posts JSON to /generate, which returns the PNG.
//  JavaScript then displays it inline and offers a download link.
static const char *HTML_PAGE = R"HTML(<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Dungeon Generator</title>
<style>
  :root {
    --bg: #0d0c14; --panel: #16141f; --border: #2a2640;
    --accent: #7c5cbf; --accent2: #3fbfa0; --text: #ccc8e8;
    --muted: #6e6a88; --danger: #bf5c5c;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text);
         font-family: 'Courier New', monospace; min-height: 100vh;
         display: flex; flex-direction: column; align-items: center; padding: 2rem; }
  h1 { font-size: 1.6rem; letter-spacing: .15em; color: var(--accent2);
       margin-bottom: 0.3rem; text-shadow: 0 0 18px #3fbfa066; }
  .subtitle { color: var(--muted); font-size: 0.78rem; margin-bottom: 2rem; }
  .layout { display: flex; gap: 2rem; width: 100%; max-width: 1100px; align-items: flex-start; }
  .panel { background: var(--panel); border: 1px solid var(--border);
           border-radius: 6px; padding: 1.4rem; flex: 1; }
  h2 { font-size: 0.85rem; letter-spacing: .1em; color: var(--accent);
       margin-bottom: 1rem; text-transform: uppercase; }
  .field { margin-bottom: 0.9rem; }
  label { display: block; font-size: 0.7rem; color: var(--muted);
          margin-bottom: 0.3rem; letter-spacing: .05em; }
  input, select, textarea {
    width: 100%; background: #0d0c14; border: 1px solid var(--border);
    color: var(--text); font-family: inherit; font-size: 0.85rem;
    padding: 0.4rem 0.6rem; border-radius: 4px; outline: none;
    transition: border-color .2s;
  }
  input:focus, select:focus, textarea:focus { border-color: var(--accent); }
  textarea { height: 220px; resize: vertical; }
  .row { display: flex; gap: 0.8rem; }
  .row .field { flex: 1; }
  input[type=range] { padding: 0; cursor: pointer; accent-color: var(--accent); }
  .slider-row { display: flex; align-items: center; gap: 0.5rem; }
  .slider-row input { flex: 1; }
  .slider-val { font-size: 0.75rem; color: var(--accent2); width: 3rem; text-align: right; }
  button {
    width: 100%; padding: 0.7rem; background: var(--accent);
    color: #fff; border: none; border-radius: 4px; font-family: inherit;
    font-size: 0.9rem; letter-spacing: .08em; cursor: pointer;
    transition: background .2s, transform .1s;
    margin-top: 0.5rem;
  }
  button:hover { background: #9b7ad4; }
  button:active { transform: scale(0.98); }
  #dlbtn { background: var(--accent2); display: none; margin-top: 0.6rem; }
  #dlbtn:hover { background: #58d4b5; }
  #status { font-size: 0.75rem; color: var(--muted); margin-top: 0.5rem; min-height: 1.2em; }
  #status.err { color: var(--danger); }
  #preview { margin-top: 1.2rem; text-align: center; }
  #preview img { max-width: 100%; border: 1px solid var(--border); border-radius: 4px;
                 image-rendering: pixelated; }
  .tabs { display: flex; gap: 0; margin-bottom: 1rem; }
  .tab { flex: 1; padding: 0.4rem; font-family: inherit; font-size: 0.72rem;
         background: transparent; border: 1px solid var(--border);
         color: var(--muted); cursor: pointer; transition: all .2s; }
  .tab:first-child { border-radius: 4px 0 0 4px; }
  .tab:last-child  { border-radius: 0 4px 4px 0; }
  .tab.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  #formPane, #jsonPane { display: none; }
  #formPane.active, #jsonPane.active { display: block; }
</style>
</head>
<body>
<h1>⚔ DUNGEON GENERATOR</h1>
<p class="subtitle">configure → generate → download png</p>
<div class="layout">
  <div class="panel" style="max-width:380px">
    <h2>Parameters</h2>
    <div class="tabs">
      <button class="tab active" onclick="switchTab('form')">Form</button>
      <button class="tab"        onclick="switchTab('json')">Raw JSON</button>
    </div>

    <!-- FORM MODE -->
    <div id="formPane" class="active">
      <div class="row">
        <div class="field">
          <label>THEME</label>
          <select id="theme"><option value="dark">Dark</option><option value="light">Light</option></select>
        </div>
        <div class="field">
          <label>LAYOUT</label>
          <select id="layout_style">
            <option value="balanced">Balanced</option>
            <option value="room-heavy">Room-Heavy</option>
            <option value="corridor-heavy">Corridor-Heavy</option>
          </select>
        </div>
      </div>
      <div class="row">
        <div class="field">
          <label>ENEMY TYPE</label>
          <select id="enemy_type">
            <option value="ambush">Ambush</option>
            <option value="roaming">Roaming</option>
          </select>
        </div>
        <div class="field">
          <label>VISIBILITY</label>
          <select id="visibility">
            <option value="normal">Normal</option>
            <option value="low">Low (fog)</option>
          </select>
        </div>
      </div>
      <div class="field">
        <label>CORRIDOR WIDTH</label>
        <select id="corridor_width">
          <option value="1">1 (narrow)</option>
          <option value="2">2 (medium)</option>
          <option value="3">3 (wide)</option>
        </select>
      </div>

      <div class="field"><label>ROOM DENSITY <span id="rdv" class="slider-val"></span></label>
        <div class="slider-row"><input type="range" id="room_density" min="0" max="1" step="0.05" value="0.5" oninput="sv('rdv',this)"></div></div>

      <div class="field"><label>ENEMY DENSITY <span id="edv" class="slider-val"></span></label>
        <div class="slider-row"><input type="range" id="enemy_density" min="0" max="0.5" step="0.02" value="0.15" oninput="sv('edv',this)"></div></div>

      <div class="field"><label>TRAP PROBABILITY <span id="tpv" class="slider-val"></span></label>
        <div class="slider-row"><input type="range" id="trap_probability" min="0" max="0.5" step="0.02" value="0.12" oninput="sv('tpv',this)"></div></div>

      <div class="field"><label>REWARD DENSITY <span id="rrv" class="slider-val"></span></label>
        <div class="slider-row"><input type="range" id="reward_density" min="0" max="0.5" step="0.02" value="0.08" oninput="sv('rrv',this)"></div></div>

      <div class="field"><label>DIFFICULTY <span id="dfv" class="slider-val"></span></label>
        <div class="slider-row"><input type="range" id="difficulty" min="0" max="1" step="0.05" value="0.5" oninput="sv('dfv',this)"></div></div>
    </div>

    <!-- RAW JSON MODE -->
    <div id="jsonPane">
      <textarea id="rawJson" placeholder='{"theme":"dark","room_density":0.5,...}'>{
  "theme": "dark",
  "layout_style": "balanced",
  "corridor_width": 1,
  "room_density": 0.5,
  "enemy_density": 0.15,
  "enemy_type": "ambush",
  "difficulty": 0.5,
  "trap_probability": 0.12,
  "visibility": "normal",
  "reward_density": 0.08
}</textarea>
    </div>

    <button onclick="generate()">⚡ GENERATE DUNGEON</button>
    <button id="dlbtn" onclick="download()">⬇ DOWNLOAD PNG</button>
    <div id="status">ready.</div>
  </div>

  <div class="panel" style="flex:2">
    <h2>Preview</h2>
    <div id="preview"><p style="color:var(--muted);font-size:.8rem">Generate a dungeon to see the map here.</p></div>
  </div>
</div>

<script>
let currentTab = 'form';
let pngBlob = null;

// Init slider displays
document.querySelectorAll('input[type=range]').forEach(el => {
  const span = document.getElementById(el.id.replace(/_/g,'').substring(0,3)+'v') ||
               document.getElementById({'room_density':'rdv','enemy_density':'edv',
               'trap_probability':'tpv','reward_density':'rrv','difficulty':'dfv'}[el.id]);
  if (span) span.textContent = el.value;
});

function sv(id, el) { document.getElementById(id).textContent = parseFloat(el.value).toFixed(2); }

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active', (i==0)==(tab=='form')));
  document.getElementById('formPane').classList.toggle('active', tab==='form');
  document.getElementById('jsonPane').classList.toggle('active', tab==='json');
}

function buildJson() {
  if (currentTab === 'json') {
    try { JSON.parse(document.getElementById('rawJson').value); }
    catch(e) { throw new Error('Invalid JSON: ' + e.message); }
    return document.getElementById('rawJson').value;
  }
  return JSON.stringify({
    theme:            document.getElementById('theme').value,
    layout_style:     document.getElementById('layout_style').value,
    corridor_width:   parseInt(document.getElementById('corridor_width').value),
    room_density:     parseFloat(document.getElementById('room_density').value),
    enemy_density:    parseFloat(document.getElementById('enemy_density').value),
    enemy_type:       document.getElementById('enemy_type').value,
    difficulty:       parseFloat(document.getElementById('difficulty').value),
    trap_probability: parseFloat(document.getElementById('trap_probability').value),
    visibility:       document.getElementById('visibility').value,
    reward_density:   parseFloat(document.getElementById('reward_density').value)
  });
}

async function generate() {
  const status = document.getElementById('status');
  status.className = '';
  status.textContent = 'generating…';
  document.getElementById('dlbtn').style.display = 'none';
  let body;
  try { body = buildJson(); } catch(e) {
    status.className = 'err'; status.textContent = e.message; return;
  }
  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body
    });
    if (!res.ok) { throw new Error('Server error: ' + res.status); }
    const blob = await res.blob();
    pngBlob = blob;
    const url = URL.createObjectURL(blob);
    document.getElementById('preview').innerHTML =
      '<img src="' + url + '" alt="dungeon map">';
    document.getElementById('dlbtn').style.display = 'block';
    status.textContent = 'done!';
  } catch(e) {
    status.className = 'err';
    status.textContent = 'error: ' + e.message;
  }
}

function download() {
  if (!pngBlob) return;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(pngBlob);
  a.download = 'dungeon_map.png';
  a.click();
}
</script>
</body>
</html>
)HTML";

// ── HTTP helpers ──────────────────────────────────────────────
static std::string recv_all(socket_t sock) {
  std::string buf;
  char tmp[4096];
  while (true) {
    ssize_t n = recv(sock, tmp, sizeof(tmp), 0);
    if (n <= 0)
      break;
    buf.append(tmp, n);
    // Simple heuristic: stop when we have headers + body
    auto hdr_end = buf.find("\r\n\r\n");
    if (hdr_end == std::string::npos)
      continue;
    // Check Content-Length
    auto cl_pos = buf.find("Content-Length:");
    if (cl_pos == std::string::npos)
      break;
    auto cl_end = buf.find("\r\n", cl_pos);
    int content_len =
        std::stoi(buf.substr(cl_pos + 15, cl_end - (cl_pos + 15)));
    int body_start = (int)hdr_end + 4;
    if ((int)buf.size() >= body_start + content_len)
      break;
  }
  return buf;
}

static void send_all(socket_t sock, const char *data, int len) {
  int sent = 0;
  while (sent < len) {
    ssize_t n = send(sock, data + sent, len - sent, 0);
    if (n <= 0)
      break;
    sent += (int)n;
  }
}

static void handle_client(socket_t client) {
  std::string req = recv_all(client);

  auto first_line_end = req.find("\r\n");
  std::string first_line = req.substr(0, first_line_end);

  // Route: GET /
  if (first_line.find("GET /") != std::string::npos &&
      first_line.find("GET / ") != std::string::npos) {
    std::string resp = "HTTP/1.0 200 OK\r\n"
                       "Content-Type: text/html; charset=utf-8\r\n"
                       "Connection: close\r\n\r\n";
    resp += HTML_PAGE;
    send_all(client, resp.c_str(), (int)resp.size());
    CLOSE_SOCKET(client);
    return;
  }

  // Route: POST /generate
  if (first_line.find("POST /generate") != std::string::npos) {
    // Extract JSON body
    auto body_start = req.find("\r\n\r\n");
    std::string json_body =
        (body_start != std::string::npos) ? req.substr(body_start + 4) : "{}";

    // Generate dungeon
    Config cfg = parse_config(json_body);
    DungeonGenerator gen(cfg, 42);
    gen.generate();

    const int TILE = 12;
    int imgW = gen.map.W * TILE;
    int imgH = gen.map.H * TILE + 24; // +24 for legend
    auto pixels = render_map(gen.map, cfg);

    // Encode PNG to memory buffer
    std::vector<uint8_t> png_bytes;
    stbi_write_png_to_func(
        [](void *ctx, void *data, int size) {
          auto *v = static_cast<std::vector<uint8_t> *>(ctx);
          auto *p = static_cast<uint8_t *>(data);
          v->insert(v->end(), p, p + size);
        },
        &png_bytes, imgW, imgH, 3, pixels.data(), imgW * 3);

    // Send PNG response
    std::string header = "HTTP/1.0 200 OK\r\n"
                         "Content-Type: image/png\r\n"
                         "Content-Length: " +
                         std::to_string(png_bytes.size()) +
                         "\r\n"
                         "Connection: close\r\n\r\n";
    send_all(client, header.c_str(), (int)header.size());
    send_all(client, (char *)png_bytes.data(), (int)png_bytes.size());
    CLOSE_SOCKET(client);
    return;
  }

  // Route: POST /generate_json or POST /api/map
  if (first_line.find("POST /generate_json") != std::string::npos ||
      first_line.find("POST /api/map") != std::string::npos) {
    auto body_start = req.find("\r\n\r\n");
    std::string json_body =
        (body_start != std::string::npos) ? req.substr(body_start + 4) : "{}";

    Config cfg = parse_config(json_body);
    unsigned seed = cfg.seed ? cfg.seed : (unsigned)time(nullptr);
    DungeonGenerator gen(cfg, seed);
    gen.generate();

    std::string map_json = export_map_json_str(gen, cfg, seed);

    std::string header = "HTTP/1.0 200 OK\r\n"
                         "Content-Type: application/json\r\n"
                         "Access-Control-Allow-Origin: *\r\n"
                         "Content-Length: " +
                         std::to_string(map_json.size()) +
                         "\r\n"
                         "Connection: close\r\n\r\n";
    send_all(client, header.c_str(), (int)header.size());
    send_all(client, map_json.c_str(), (int)map_json.size());
    CLOSE_SOCKET(client);
    return;
  }


  // 404
  const char *not_found =
      "HTTP/1.0 404 Not Found\r\nConnection: close\r\n\r\nNot Found";
  send_all(client, not_found, (int)strlen(not_found));
  CLOSE_SOCKET(client);
}

static void run_server(int port) {
#ifdef _WIN32
  WSADATA wsa;
  WSAStartup(MAKEWORD(2, 2), &wsa);
#endif

  socket_t server = socket(AF_INET, SOCK_STREAM, 0);
  if (server == (socket_t)SOCK_ERR) {
    std::cerr << "Failed to create socket\n";
    return;
  }
  int opt = 1;
  setsockopt(server, SOL_SOCKET, SO_REUSEADDR, (char *)&opt, sizeof(opt));

  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons((uint16_t)port);
  addr.sin_addr.s_addr = INADDR_ANY;

  if (bind(server, (sockaddr *)&addr, sizeof(addr)) == SOCK_ERR) {
    std::cerr << "bind() failed on port " << port << "\n";
    return;
  }
  listen(server, 8);

  std::cout << "=== Dungeon Generator Web UI ===\n";
  std::cout << "Open:  http://localhost:" << port << "\n";
  std::cout << "Press Ctrl+C to stop.\n\n";

  while (true) {
    socket_t client = accept(server, nullptr, nullptr);
    if (client == (socket_t)SOCK_ERR)
      continue;
    // Handle each request in its own thread
    std::thread([client] { handle_client(client); }).detach();
  }

  CLOSE_SOCKET(server);
#ifdef _WIN32
  WSACleanup();
#endif
}

// ══════════════════════════════════════════════════════════════
//  SECTION 6 — Main Entry Point
// ══════════════════════════════════════════════════════════════

int main(int argc, char **argv) {
  // ── Mode 1: Web server ────────────────────────────────
  if (argc >= 2 && std::string(argv[1]) == "--serve") {
    int port = (argc >= 3) ? std::stoi(argv[2]) : 8080;
    run_server(port);
    return 0;
  }

  // ── Mode 2: CLI ───────────────────────────────────────
  std::string input_path = (argc >= 2) ? argv[1] : "input.json";
  std::string output_path = (argc >= 3) ? argv[2] : "dungeon_map.png";

  Config cfg = parse_config_file(input_path);

  std::cout << "=== Dungeon Map Generator ===\n";
  std::cout << "Theme:         " << cfg.theme << "\n";
  std::cout << "Layout:        " << cfg.layout_style << "\n";
  std::cout << "Corridor W:    " << cfg.corridor_width << "\n";
  std::cout << "Room density:  " << cfg.room_density << "\n";
  std::cout << "Enemy density: " << cfg.enemy_density << " (" << cfg.enemy_type
            << ")\n";
  std::cout << "Difficulty:    " << cfg.difficulty << "\n";
  std::cout << "Trap prob:     " << cfg.trap_probability << "\n";
  std::cout << "Visibility:    " << cfg.visibility << "\n";
  std::cout << "Reward:        " << cfg.reward_density << "\n";
  std::cout << "Generating…\n";

  unsigned seed = cfg.seed ? cfg.seed : (unsigned)time(nullptr);
  DungeonGenerator gen(cfg, seed);
  gen.generate();

  std::cout << "Rooms placed:  " << gen.rooms.size() << "\n";

  const int TILE = 12;
  int imgW = gen.map.W * TILE;
  int imgH = gen.map.H * TILE + 24;
  auto pixels = render_map(gen.map, cfg);

  if (argc >= 4 && (std::string(argv[3]) == "--json" || std::string(argv[3]) == "--export-json")) {
    std::string json_data = export_map_json_str(gen, cfg, seed);
    std::ofstream f(output_path);
    if (f) {
      f << json_data;
      std::cout << "Saved Map JSON: " << output_path << "\n";
    } else {
      std::cerr << "Failed to write JSON: " << output_path << "\n";
    }
  } else {
    if (save_png(output_path, pixels, imgW, imgH))
      std::cout << "Saved: " << output_path << "\n";
    else
      std::cerr << "Failed to write " << output_path << "\n";
  }


  // ── Tile count summary ────────────────────────────────
  std::cout << "\n-- Tile summary --\n";
  std::map<Tile, int> counts;
  for (auto t : gen.map.cells)
    counts[t]++;
  for (auto &[tile, cnt] : counts)
    std::cout << "  " << tile_name(tile) << ": " << cnt << "\n";

  return 0;
}
