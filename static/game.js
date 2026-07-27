// Closed-Loop LLM PCG Dungeon Game Engine v2 (High-Aesthetic Edition)

const Tile = {
  WALL: 0,
  FLOOR: 1,
  CORRIDOR: 2,
  DOOR: 3,
  TRAP: 4,
  ENEMY: 5,
  CHEST: 6,
  START: 7,
  EXIT: 8,
  FOG: 9
};

const TileColorsDark = {
  [Tile.WALL]: '#111422',
  [Tile.FLOOR]: '#1e2436',
  [Tile.CORRIDOR]: '#181d2e',
  [Tile.DOOR]: '#8b5cf6',
  [Tile.TRAP]: '#ef4444',
  [Tile.ENEMY]: '#f43f5e',
  [Tile.CHEST]: '#f59e0b',
  [Tile.START]: '#10b981',
  [Tile.EXIT]: '#06b6d4',
  [Tile.FOG]: '#050609'
};

const TileColorsLight = {
  [Tile.WALL]: '#cbd5e1',     // Light marble wall stone
  [Tile.FLOOR]: '#ffffff',    // Pure white room floor!
  [Tile.CORRIDOR]: '#f1f5f9', // Off-white light corridor
  [Tile.DOOR]: '#7c3aed',     // Royal violet door
  [Tile.TRAP]: '#dc2626',     // Red trap
  [Tile.ENEMY]: '#e11d48',    // Crimson enemy
  [Tile.CHEST]: '#d97706',    // Amber gold chest
  [Tile.START]: '#059669',    // Emerald start
  [Tile.EXIT]: '#0891b2',     // Cyan exit
  [Tile.FOG]: '#94a3b8'       // Light haze fog
};


class SoundFX {
  constructor() {
    this.ctx = null;
    this.muted = false;
  }

  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
  }

  playSlash() {
    if (this.muted || !this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(400, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(80, this.ctx.currentTime + 0.12);
      gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.01, this.ctx.currentTime + 0.12);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.12);
    } catch(e) {}
  }

  playHit() {
    if (this.muted || !this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'square';
      osc.frequency.setValueAtTime(160, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(40, this.ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.4, this.ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.01, this.ctx.currentTime + 0.15);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.15);
    } catch(e) {}
  }

  playChest() {
    if (this.muted || !this.ctx) return;
    try {
      const notes = [523.25, 659.25, 783.99, 1046.50];
      notes.forEach((freq, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime + idx * 0.06);
        gain.gain.setValueAtTime(0.2, this.ctx.currentTime + idx * 0.06);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + idx * 0.06 + 0.2);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(this.ctx.currentTime + idx * 0.06);
        osc.stop(this.ctx.currentTime + idx * 0.06 + 0.2);
      });
    } catch(e) {}
  }

  playTrap() {
    if (this.muted || !this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(220, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(60, this.ctx.currentTime + 0.2);
      gain.gain.setValueAtTime(0.5, this.ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.01, this.ctx.currentTime + 0.2);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.2);
    } catch(e) {}
  }

  playFanfare() {
    if (this.muted || !this.ctx) return;
    try {
      const notes = [440, 554.37, 659.25, 880];
      notes.forEach((freq, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime + idx * 0.1);
        gain.gain.setValueAtTime(0.25, this.ctx.currentTime + idx * 0.1);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + idx * 0.1 + 0.35);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(this.ctx.currentTime + idx * 0.1);
        osc.stop(this.ctx.currentTime + idx * 0.1 + 0.35);
      });
    } catch(e) {}
  }
}

class GameEngine {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.tileSize = 22;
    this.sfx = new SoundFX();
    
    // State
    this.levelNumber = 1;
    this.sessionId = 'session_' + Date.now();
    this.mapData = null;
    this.currentConfig = null;
    this.isLoaded = false;
    this.isGameOver = false;

    // Player State
    this.player = {
      x: 0,
      y: 0,
      hp: 100,
      maxHp: 100,
      score: 0,
      attackCooldown: 0,
      invulnerableTimer: 2.0
    };

    // Entities
    this.enemies = [];
    this.chests = [];
    this.traps = [];
    this.particles = [];
    this.floatingTexts = [];
    this.explored = {};
    this.screenShake = 0;

    // Telemetry Recording
    this.telemetry = {
      startTime: 0,
      endTime: 0,
      time_taken_sec: 0,
      damage_taken: 0,
      health_remaining: 100,
      deaths_retries: 0,
      enemies_killed: 0,
      total_enemies: 0,
      chests_opened: 0,
      total_chests: 0,
      traps_triggered: 0,
      exploration_percent: 0,
      segment_times: []
    };

    this.keys = {};
    this.lastFrameTime = performance.now();
    this.initInput();
    this.loadMap(this.createFallbackMap());
  }

  createFallbackMap() {
    const W = 40, H = 30;
    const tiles = Array(H).fill(null).map((_, y) => 
      Array(W).fill(null).map((_, x) => {
        if (x === 0 || x === W - 1 || y === 0 || y === H - 1) return Tile.WALL;
        return Tile.FLOOR;
      })
    );
    return {
      width: W,
      height: H,
      start: { x: 5, y: 5 },
      exit: { x: 35, y: 25 },
      enemies: [
        { x: 20, y: 15, type: 'patrol' },
        { x: 30, y: 20, type: 'roaming' }
      ],
      chests: [
        { x: 10, y: 10 },
        { x: 25, y: 25 }
      ],
      traps: [
        { x: 15, y: 12 }
      ],
      tiles: tiles,
      config: {
        theme_name: "Dark Obsidian Abyss",
        theme: "dark",
        visibility: "normal",
        difficulty: 0.5,
        palette: {
          background: "#050609",
          wall: "#111422",
          floor: "#1e2436",
          corridor: "#181d2e",
          door: "#8b5cf6",
          trap: "#ef4444",
          enemy: "#f43f5e",
          chest: "#f59e0b",
          start: "#10b981",
          exit: "#06b6d4",
          fog: "#050609"
        }
      }
    };
  }


  initInput() {
    window.addEventListener('keydown', (e) => {
      const targetTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      if (targetTag === 'input' || targetTag === 'textarea') {
        return;
      }
      this.sfx.init();
      const key = e.key.toLowerCase();
      this.keys[key] = true;
      if (key === ' ' && this.isLoaded && !this.isGameOver) {
        e.preventDefault();
        this.handleAttack();
      }
    });

    window.addEventListener('keyup', (e) => {
      const key = e.key.toLowerCase();
      this.keys[key] = false;
    });

    window.addEventListener('blur', () => {
      this.keys = {};
    });

    this.canvas.addEventListener('mousedown', () => {
      this.sfx.init();
      if (this.isLoaded && !this.isGameOver) {
        this.handleAttack();
      }
    });
  }

  loadMap(mapJson) {
    if (!mapJson || !mapJson.start || !mapJson.tiles) {
      console.error("Invalid map JSON structure received:", mapJson);
      return;
    }
    this.keys = {}; // Reset any stuck keys on map load
    this.mapData = mapJson;
    this.currentConfig = mapJson.config;
    
    this.player.x = mapJson.start.x;
    this.player.y = mapJson.start.y;
    this.player.hp = Math.min(100, this.player.hp + 25);
    this.player.invulnerableTimer = 2.5; // 2.5s safe start i-frames!


    this.enemies = mapJson.enemies.map((e, idx) => ({
      id: idx,
      x: e.x,
      y: e.y,
      type: e.type || 'patrol',
      hp: 40 + this.levelNumber * 5,
      maxHp: 40 + this.levelNumber * 5,
      isElite: Math.random() < (0.15 + this.levelNumber * 0.05),
      attackCooldown: 0
    }));


    this.chests = mapJson.chests.map(c => ({
      x: c.x,
      y: c.y,
      opened: false
    }));

    this.traps = mapJson.traps.map(t => ({
      x: t.x,
      y: t.y,
      triggered: false
    }));

    // Reset telemetry
    this.telemetry.startTime = performance.now();
    this.telemetry.damage_taken = 0;
    this.telemetry.enemies_killed = 0;
    this.telemetry.total_enemies = this.enemies.length;
    this.telemetry.chests_opened = 0;
    this.telemetry.total_chests = this.chests.length;
    this.telemetry.traps_triggered = 0;
    this.telemetry.segment_times = [];

    this.explored = {};
    this.revealFog(this.player.x, this.player.y, 8);

    this.isLoaded = true;
    this.isGameOver = false;

    this.canvas.width = mapJson.width * this.tileSize;
    this.canvas.height = mapJson.height * this.tileSize;

    this.updateHUD();
  }

  revealFog(px, py, radius) {
    if (!this.mapData) return;
    for (let dy = -radius; dy <= radius; dy++) {
      for (let dx = -radius; dx <= radius; dx++) {
        const nx = px + dx;
        const ny = py + dy;
        if (nx >= 0 && nx < this.mapData.width && ny >= 0 && ny < this.mapData.height) {
          if (dx*dx + dy*dy <= radius*radius) {
            this.explored[`${nx},${ny}`] = true;
          }
        }
      }
    }
  }

  update(dt) {
    if (!this.isLoaded || this.isGameOver) return;

    if (this.player.invulnerableTimer > 0) {
      this.player.invulnerableTimer -= dt;
    }

    if (this.screenShake > 0) {
      this.screenShake -= dt * 25;
      if (this.screenShake < 0) this.screenShake = 0;
    }

    if (this.player.attackCooldown > 0) {
      this.player.attackCooldown -= dt;
    }

    // Player Movement
    this.moveTimer = (this.moveTimer || 0) + dt;
    if (this.moveTimer >= 0.11) {
      let dx = 0, dy = 0;
      if (this.keys['w'] || this.keys['arrowup']) dy -= 1;
      else if (this.keys['s'] || this.keys['arrowdown']) dy += 1;
      else if (this.keys['a'] || this.keys['arrowleft']) dx -= 1;
      else if (this.keys['d'] || this.keys['arrowright']) dx += 1;

      if (dx !== 0 || dy !== 0) {
        this.tryMovePlayer(dx, dy);
        this.moveTimer = 0;
      }
    }

    // Enemy AI
    this.updateEnemies(dt);

    // Update Particles
    this.particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      p.life -= dt;
    });
    this.particles = this.particles.filter(p => p.life > 0);

    // Update Floating Text
    this.floatingTexts.forEach(ft => {
      ft.y -= 15 * dt;
      ft.alpha -= 0.8 * dt;
    });
    this.floatingTexts = this.floatingTexts.filter(ft => ft.alpha > 0);

    this.telemetry.time_taken_sec = (performance.now() - this.telemetry.startTime) / 1000;
    this.updateHUD();
  }

  tryMovePlayer(dx, dy) {
    const nx = this.player.x + dx;
    const ny = this.player.y + dy;

    if (!this.isWalkable(nx, ny)) return;

    this.player.x = nx;
    this.player.y = ny;

    this.revealFog(nx, ny, (this.currentConfig && this.currentConfig.visibility === 'low') ? 6 : 9);


    // Check Traps
    const trapIndex = this.traps.findIndex(t => t.x === nx && t.y === ny && !t.triggered);
    if (trapIndex !== -1 && this.player.invulnerableTimer <= 0) {
      this.traps[trapIndex].triggered = true;
      this.player.hp -= 15;
      this.player.invulnerableTimer = 0.8; // 0.8s i-frames
      this.telemetry.damage_taken += 15;
      this.telemetry.traps_triggered += 1;
      this.screenShake = 6;
      this.sfx.playTrap();
      this.spawnParticles(nx, ny, '#ef4444', 15);
      this.addFloatingText(nx, ny, '-15 HP', '#ef4444');
      this.addLog(`⚠️ Triggered Trap! (-15 HP)`);
      if (this.player.hp <= 0) this.handlePlayerDeath();
    }

    // Check Chests
    const chestIndex = this.chests.findIndex(c => c.x === nx && c.y === ny && !c.opened);
    if (chestIndex !== -1) {
      this.chests[chestIndex].opened = true;
      const scoreGain = 100 + this.levelNumber * 25;
      this.player.score += scoreGain;
      this.player.hp = Math.min(this.player.maxHp, this.player.hp + 25);
      this.telemetry.chests_opened += 1;
      this.sfx.playChest();
      this.spawnParticles(nx, ny, '#f59e0b', 20);
      this.addFloatingText(nx, ny, `+${scoreGain} PTS`, '#f59e0b');
      this.addLog(`💰 Found Vault Chest! (+${scoreGain} Score, +25 HP)`);
    }

    // Check Exit Portal
    if (nx === this.mapData.exit.x && ny === this.mapData.exit.y) {
      this.sfx.playFanfare();
      this.handleLevelClear();
    }
  }

  isWalkable(x, y) {
    if (x < 0 || y < 0 || x >= this.mapData.width || y >= this.mapData.height) return false;
    const tile = this.mapData.tiles[y][x];
    return tile !== Tile.WALL;
  }


  handleAttack() {
    if (this.player.attackCooldown > 0) return;
    this.player.attackCooldown = 0.25;
    this.sfx.playSlash();

    const attackRadius = 2.2; // Generous attack radius
    let hitAny = false;

    this.enemies.forEach(e => {
      const dist = Math.hypot(e.x - this.player.x, e.y - this.player.y);
      if (dist <= attackRadius && e.hp > 0) {
        const dmg = 45;
        e.hp -= dmg;
        hitAny = true;
        this.sfx.playHit();
        this.spawnParticles(e.x, e.y, '#38bdf8', 12);
        this.addFloatingText(e.x, e.y, `-${dmg}`, '#38bdf8');
        if (e.hp <= 0) {
          this.telemetry.enemies_killed += 1;
          const scoreVal = e.isElite ? 150 : 60;
          this.player.score += scoreVal;
          this.addFloatingText(e.x, e.y, `+${scoreVal}`, '#a78bfa');
          this.addLog(`⚔ Slain ${e.isElite ? 'Elite Monster' : 'Monster'}! (+${scoreVal} PTS)`);
        }
      }
    });

    if (hitAny) {
      this.spawnParticles(this.player.x, this.player.y, '#8b5cf6', 10);
    }
  }

  updateEnemies(dt) {
    this.enemiesTimer = (this.enemiesTimer || 0) + dt;
    if (this.enemiesTimer < 0.35) return;
    this.enemiesTimer = 0;

    const isAmbush = (this.currentConfig && this.currentConfig.enemy_type === 'ambush');


    this.enemies.forEach(e => {
      if (e.hp <= 0) return;

      if (e.attackCooldown > 0) e.attackCooldown -= 0.35;

      const distToPlayer = Math.hypot(this.player.x - e.x, this.player.y - e.y);

      if (distToPlayer <= 1.4) {
        if (this.player.invulnerableTimer <= 0 && (e.attackCooldown || 0) <= 0) {
          const dmg = e.isElite ? 16 : 10;
          this.player.hp -= dmg;
          this.player.invulnerableTimer = 0.8; // 0.8s i-frames
          e.attackCooldown = 1.5; // 1.5s per-enemy attack cooldown!
          this.telemetry.damage_taken += dmg;
          this.screenShake = 5;
          this.sfx.playHit();
          this.spawnParticles(this.player.x, this.player.y, '#ef4444', 12);
          this.addFloatingText(this.player.x, this.player.y, `-${dmg} HP`, '#ef4444');
          this.addLog(`💥 Enemy Hit You! (-${dmg} HP)`);
          if (this.player.hp <= 0) this.handlePlayerDeath();
        }
        return;
      }

      let shouldChase = distToPlayer <= (isAmbush ? 9 : 6);

      if (shouldChase) {
        let dx = 0, dy = 0;
        if (this.player.x > e.x) dx = 1;
        else if (this.player.x < e.x) dx = -1;
        if (this.player.y > e.y) dy = 1;
        else if (this.player.y < e.y) dy = -1;

        if (dx !== 0 && this.isWalkable(e.x + dx, e.y)) e.x += dx;
        else if (dy !== 0 && this.isWalkable(e.x, e.y + dy)) e.y += dy;
      } else {
        const dirs = [[1,0], [-1,0], [0,1], [0,-1]];
        const [dx, dy] = dirs[Math.floor(Math.random() * dirs.length)];
        if (this.isWalkable(e.x + dx, e.y + dy)) {
          e.x += dx;
          e.y += dy;
        }
      }
    });
  }


  spawnParticles(x, y, color, count) {
    for (let i = 0; i < count; i++) {
      this.particles.push({
        x: (x + 0.5) * this.tileSize,
        y: (y + 0.5) * this.tileSize,
        vx: (Math.random() - 0.5) * 5,
        vy: (Math.random() - 0.5) * 5,
        life: 0.35 + Math.random() * 0.3,
        color: color
      });
    }
  }

  addFloatingText(x, y, text, color) {
    this.floatingTexts.push({
      x: (x + 0.5) * this.tileSize,
      y: y * this.tileSize,
      text: text,
      color: color,
      alpha: 1.0
    });
  }

  handlePlayerDeath() {
    this.isGameOver = true;
    this.telemetry.deaths_retries += 1;
    this.telemetry.health_remaining = 0;
    this.addLog(`💀 YOU DIED! Respawning in Start Room...`);
    setTimeout(() => {
      this.player.hp = 100;
      this.player.x = this.mapData.start.x;
      this.player.y = this.mapData.start.y;
      this.player.invulnerableTimer = 3.0; // Safe respawn i-frames
      this.isGameOver = false;
    }, 1200);
  }


  handleLevelClear() {
    this.isGameOver = true;
    this.telemetry.endTime = performance.now();
    this.telemetry.time_taken_sec = (this.telemetry.endTime - this.telemetry.startTime) / 1000;
    this.telemetry.health_remaining = this.player.hp;

    const totalWalkable = this.mapData.tiles.flat().filter(t => t !== Tile.WALL && t !== Tile.FOG).length;
    const exploredCount = Object.keys(this.explored).length;
    this.telemetry.exploration_percent = Math.min(100, (exploredCount / totalWalkable) * 100);

    if (window.showLevelCompleteModal) {
      window.showLevelCompleteModal(this.levelNumber, this.telemetry, this.currentConfig);
    }
  }

  getPalette(config) {
    if (config && config.palette) {
      return {
        bg: config.palette.background || '#050609',
        [Tile.WALL]: config.palette.wall || '#111422',
        [Tile.FLOOR]: config.palette.floor || '#1e2436',
        [Tile.CORRIDOR]: config.palette.corridor || '#181d2e',
        [Tile.DOOR]: config.palette.door || '#8b5cf6',
        [Tile.TRAP]: config.palette.trap || '#ef4444',
        [Tile.ENEMY]: config.palette.enemy || '#f43f5e',
        [Tile.CHEST]: config.palette.chest || '#f59e0b',
        [Tile.START]: config.palette.start || '#10b981',
        [Tile.EXIT]: config.palette.exit || '#06b6d4',
        [Tile.FOG]: config.palette.fog || '#050609'
      };
    }
    const isLight = config && config.theme === 'light';
    const base = isLight ? TileColorsLight : TileColorsDark;
    return {
      bg: isLight ? '#f8fafc' : '#050609',
      ...base
    };
  }

  draw() {
    if (!this.isLoaded) return;

    this.ctx.save();
    if (this.screenShake > 0) {
      const rx = (Math.random() - 0.5) * this.screenShake;
      const ry = (Math.random() - 0.5) * this.screenShake;
      this.ctx.translate(rx, ry);
    }

    const activePalette = this.getPalette(this.currentConfig);
    const isLight = this.currentConfig && this.currentConfig.theme === 'light';

    this.ctx.fillStyle = activePalette.bg;
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    const isLowVis = this.currentConfig.visibility === 'low';

    // Draw Map Tiles
    for (let y = 0; y < this.mapData.height; y++) {
      for (let x = 0; x < this.mapData.width; x++) {
        const isExplored = this.explored[`${x},${y}`];
        if (isLowVis && !isExplored) {
          this.ctx.fillStyle = activePalette[Tile.FOG];
          this.ctx.fillRect(x * this.tileSize, y * this.tileSize, this.tileSize, this.tileSize);
          continue;
        }

        const tile = this.mapData.tiles[y][x];
        this.ctx.fillStyle = activePalette[tile] || activePalette[Tile.WALL];
        this.ctx.fillRect(x * this.tileSize, y * this.tileSize, this.tileSize, this.tileSize);

        // Tile Grid Highlight
        if (tile === Tile.FLOOR || tile === Tile.CORRIDOR) {
          this.ctx.strokeStyle = isLight ? 'rgba(0, 0, 0, 0.08)' : 'rgba(255, 255, 255, 0.025)';
          this.ctx.strokeRect(x * this.tileSize, y * this.tileSize, this.tileSize, this.tileSize);
        }
      }
    }



    // Dynamic Torch Lighting Effects around Player & Exit
    const pxPixel = (this.player.x + 0.5) * this.tileSize;
    const pyPixel = (this.player.y + 0.5) * this.tileSize;

    const torchGlow = this.ctx.createRadialGradient(pxPixel, pyPixel, 10, pxPixel, pyPixel, this.tileSize * (isLowVis ? 5 : 8));
    torchGlow.addColorStop(0, 'rgba(255, 255, 255, 0.12)');
    torchGlow.addColorStop(0.5, 'rgba(139, 92, 246, 0.05)');
    torchGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
    this.ctx.fillStyle = torchGlow;
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw Traps
    this.traps.forEach(t => {
      if (isLowVis && !this.explored[`${t.x},${t.y}`]) return;
      this.ctx.fillStyle = t.triggered ? '#7f1d1d' : '#ef4444';
      this.ctx.beginPath();
      this.ctx.arc((t.x + 0.5) * this.tileSize, (t.y + 0.5) * this.tileSize, 5, 0, Math.PI * 2);
      this.ctx.fill();
    });

    // Draw Chests
    this.chests.forEach(c => {
      if (isLowVis && !this.explored[`${c.x},${c.y}`]) return;
      this.ctx.fillStyle = c.opened ? '#78350f' : '#f59e0b';
      this.ctx.fillRect(c.x * this.tileSize + 4, c.y * this.tileSize + 4, this.tileSize - 8, this.tileSize - 8);
    });

    // Draw Exit Portal with Aura
    const ex = (this.mapData.exit.x + 0.5) * this.tileSize;
    const ey = (this.mapData.exit.y + 0.5) * this.tileSize;
    const portalGlow = this.ctx.createRadialGradient(ex, ey, 2, ex, ey, 20);
    portalGlow.addColorStop(0, '#06b6d4');
    portalGlow.addColorStop(1, 'rgba(6, 182, 212, 0)');
    this.ctx.fillStyle = portalGlow;
    this.ctx.beginPath();
    this.ctx.arc(ex, ey, 20, 0, Math.PI * 2);
    this.ctx.fill();

    // Draw Enemies
    this.enemies.forEach(e => {
      if (e.hp <= 0) return;
      if (isLowVis && !this.explored[`${e.x},${e.y}`]) return;

      const exPixel = (e.x + 0.5) * this.tileSize;
      const eyPixel = (e.y + 0.5) * this.tileSize;

      this.ctx.fillStyle = e.isElite ? '#ec4899' : activePalette[Tile.ENEMY];

      if (e.isElite) {
        this.ctx.shadowColor = '#ec4899';
        this.ctx.shadowBlur = 10;
      }

      this.ctx.beginPath();
      this.ctx.arc(exPixel, eyPixel, this.tileSize / 2 - 2, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.shadowBlur = 0;

      // Enemy HP Bar
      const hpWidth = (this.tileSize - 4) * (e.hp / e.maxHp);
      this.ctx.fillStyle = '#10b981';
      this.ctx.fillRect(e.x * this.tileSize + 2, e.y * this.tileSize - 4, hpWidth, 3);
    });

    // Draw Player Character (High-Contrast Hero Avatar)
    const isInvuln = this.player.invulnerableTimer > 0;
    const blinkAlpha = isInvuln ? (Math.floor(performance.now() / 120) % 2 === 0 ? 0.3 : 0.95) : 1.0;

    this.ctx.save();
    this.ctx.globalAlpha = blinkAlpha;

    // Outer Hero Aura Glow
    const heroGlow = this.ctx.createRadialGradient(pxPixel, pyPixel, 2, pxPixel, pyPixel, this.tileSize * 1.2);
    heroGlow.addColorStop(0, isInvuln ? 'rgba(56, 189, 248, 0.8)' : 'rgba(0, 240, 255, 0.7)');
    heroGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
    this.ctx.fillStyle = heroGlow;
    this.ctx.beginPath();
    this.ctx.arc(pxPixel, pyPixel, this.tileSize * 1.2, 0, Math.PI * 2);
    this.ctx.fill();

    // Dark Stroke Outline for High Contrast against ANY Floor Color
    this.ctx.fillStyle = isInvuln ? '#38bdf8' : '#00f0ff';
    this.ctx.strokeStyle = '#050609';
    this.ctx.lineWidth = 2.5;

    this.ctx.beginPath();
    this.ctx.arc(pxPixel, pyPixel, this.tileSize / 2 - 2, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.stroke();

    // Inner White Core
    this.ctx.fillStyle = '#ffffff';
    this.ctx.beginPath();
    this.ctx.arc(pxPixel, pyPixel, this.tileSize / 4, 0, Math.PI * 2);
    this.ctx.fill();

    this.ctx.restore();



    // Sword Swing Arc Effect
    if (this.player.attackCooldown > 0.12) {
      this.ctx.strokeStyle = '#a78bfa';
      this.ctx.lineWidth = 3;
      this.ctx.beginPath();
      this.ctx.arc(pxPixel, pyPixel, this.tileSize * 1.3, 0, Math.PI * 2);
      this.ctx.stroke();
    }

    // Draw Particles
    this.particles.forEach(p => {
      this.ctx.fillStyle = p.color;
      this.ctx.fillRect(p.x, p.y, 3, 3);
    });

    // Draw Floating Texts
    this.floatingTexts.forEach(ft => {
      this.ctx.font = 'bold 12px "JetBrains Mono", monospace';
      this.ctx.fillStyle = ft.color;
      this.ctx.globalAlpha = Math.max(0, ft.alpha);
      this.ctx.fillText(ft.text, ft.x - 12, ft.y);
      this.ctx.globalAlpha = 1.0;
    });

    this.ctx.restore();
  }

  updateHUD() {
    const hpElem = document.getElementById('hudHp');
    const scoreElem = document.getElementById('hudScore');
    const timeElem = document.getElementById('hudTime');
    const levelElem = document.getElementById('hudLevel');
    const hpBar = document.getElementById('hudHpFill');

    if (hpElem) hpElem.textContent = `${this.player.hp}/${this.player.maxHp}`;
    if (hpBar) hpBar.style.width = `${Math.max(0, this.player.hp)}%`;
    if (scoreElem) scoreElem.textContent = this.player.score;
    if (timeElem) timeElem.textContent = `${this.telemetry.time_taken_sec.toFixed(1)}s`;
    if (levelElem) levelElem.textContent = `Lvl ${this.levelNumber}`;

    const mTime = document.getElementById('mTime');
    const mDmg = document.getElementById('mDmg');
    const mKills = document.getElementById('mKills');
    const mChests = document.getElementById('mChests');
    const mDiff = document.getElementById('mDiff');

    if (mTime) mTime.textContent = `${this.telemetry.time_taken_sec.toFixed(1)}s`;
    if (mDmg) mDmg.textContent = `${this.telemetry.damage_taken} HP`;
    if (mKills) mKills.textContent = `${this.telemetry.enemies_killed}/${this.telemetry.total_enemies}`;
    if (mChests) mChests.textContent = `${this.telemetry.chests_opened}/${this.telemetry.total_chests}`;
    if (mDiff && this.currentConfig) mDiff.textContent = `${(this.currentConfig.difficulty * 100).toFixed(0)}%`;

    const themeBadge = document.getElementById('hudThemeBadge');
    if (themeBadge && this.currentConfig) {
      const themeName = this.currentConfig.theme_name || (this.currentConfig.theme === 'light' ? '⚪ Light Marble Vault' : '🌑 Dark Obsidian Abyss');
      themeBadge.textContent = themeName;
      if (this.currentConfig.theme === 'light') {
        themeBadge.style.background = '#f1f5f9';
        themeBadge.style.color = '#0f172a';
        themeBadge.style.borderColor = '#94a3b8';
      } else {
        themeBadge.style.background = 'rgba(139, 92, 246, 0.15)';
        themeBadge.style.color = '#c4b5fd';
        themeBadge.style.borderColor = 'var(--accent)';
      }
    }
  }



  addLog(msg) {
    const logList = document.getElementById('gameLogs');
    if (!logList) return;
    const li = document.createElement('div');
    li.className = 'log-item';
    li.textContent = `[${new Date().toLocaleTimeString().split(' ')[0]}] ${msg}`;
    logList.prepend(li);
    if (logList.children.length > 5) logList.removeChild(logList.lastChild);
  }

  startLoop() {
    const loop = () => {
      const now = performance.now();
      const dt = (now - this.lastFrameTime) / 1000;
      this.lastFrameTime = now;

      this.update(dt);
      this.draw();

      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
}

window.GameEngine = GameEngine;
