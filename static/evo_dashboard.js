// MAP-Elites Archive Heatmap and Evolutionary Metrics Dashboard

class EvoDashboard {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        this.gridSize = 10;
        this.archiveData = null;
        this.history = [];
    }

    getFitnessColor(fit) {
        // low fitness = '#1e3a5f' (30, 58, 95)
        // mid fitness = '#3b7dd8' (59, 125, 216)
        // high fitness = '#8bb8f0' (139, 184, 240)
        // max fitness = '#e0ecff' (224, 236, 255)
        const stops = [
            { val: 0.0, color: [30, 58, 95] },
            { val: 0.33, color: [59, 125, 216] },
            { val: 0.66, color: [139, 184, 240] },
            { val: 1.0, color: [224, 236, 255] }
        ];
        
        let c1 = stops[0], c2 = stops[stops.length - 1];
        for (let i = 0; i < stops.length - 1; i++) {
            if (fit >= stops[i].val && fit <= stops[i+1].val) {
                c1 = stops[i];
                c2 = stops[i+1];
                break;
            }
        }
        
        const t = (c2.val === c1.val) ? 0 : (fit - c1.val) / (c2.val - c1.val);
        const r = Math.round(c1.color[0] + t * (c2.color[0] - c1.color[0]));
        const g = Math.round(c1.color[1] + t * (c2.color[1] - c1.color[1]));
        const b = Math.round(c1.color[2] + t * (c2.color[2] - c1.color[2]));
        return `rgb(${r}, ${g}, ${b})`;
    }

    renderHeatmap(archiveStats, playerPos = null) {
        if (!this.ctx || !archiveStats || !archiveStats.grid) return;

        this.archiveData = archiveStats;
        const width = this.canvas.width;
        const height = this.canvas.height;
        const cellSize = width / this.gridSize;

        this.ctx.clearRect(0, 0, width, height);

        // Background
        this.ctx.fillStyle = "#1a1d28";
        this.ctx.fillRect(0, 0, width, height);

        const grid = archiveStats.grid;

        for (let x = 0; x < this.gridSize; x++) {
            for (let y = 0; y < this.gridSize; y++) {
                const cell = grid[x][y];
                const px = x * cellSize;
                const py = (this.gridSize - 1 - y) * cellSize; // Flip Y so 0 is bottom

                if (cell) {
                    const fit = cell.fitness;
                    this.ctx.fillStyle = this.getFitnessColor(fit);
                    this.ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);

                    // Fitness label inside cell
                    this.ctx.fillStyle = (fit > 0.5) ? "#1a1d28" : "#e0ecff"; // Contrast color for readability
                    this.ctx.font = "9px 'Inter', sans-serif";
                    this.ctx.textAlign = "center";
                    this.ctx.fillText(fit.toFixed(2), px + cellSize / 2, py + cellSize / 2 + 3);
                } else {
                    // Empty cell
                    this.ctx.fillStyle = "#1a1d28";
                    this.ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
                }
            }
        }

        // Draw Player Niche Marker
        if (playerPos && typeof playerPos.x === 'number' && typeof playerPos.y === 'number') {
            const px = playerPos.x * cellSize;
            const py = (this.gridSize - 1 - playerPos.y) * cellSize;

            this.ctx.strokeStyle = "#ffffff";
            this.ctx.lineWidth = 2;
            this.ctx.strokeRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
        }
    }

    updateStatsUI(archiveStats, evalRecord) {
        if (!archiveStats) return;

        const covElem = document.getElementById('evoCoverage');
        const avgFitElem = document.getElementById('evoAvgFitness');
        const maxFitElem = document.getElementById('evoMaxFitness');
        const genElem = document.getElementById('evoGenerations');

        if (covElem) covElem.textContent = `${archiveStats.coverage_percent}% (${archiveStats.filled_cells}/100)`;
        if (avgFitElem) avgFitElem.textContent = archiveStats.avg_fitness.toFixed(3);
        if (maxFitElem) maxFitElem.textContent = archiveStats.max_fitness.toFixed(3);
        if (genElem) genElem.textContent = archiveStats.total_evaluations;

        if (evalRecord && evalRecord.behavior) {
            const nicheElem = document.getElementById('playerNicheLabel');
            if (nicheElem) {
                nicheElem.textContent = `${evalRecord.behavior.dim1_name}: ${(evalRecord.behavior.dim1_val*100).toFixed(0)}% | ${evalRecord.behavior.dim2_name}: ${(evalRecord.behavior.dim2_val*100).toFixed(0)}% [Cell ${evalRecord.grid_pos.x},${evalRecord.grid_pos.y}]`;
            }
        }
    }
}

window.EvoDashboard = EvoDashboard;
