// MAP-Elites Archive Heatmap and Evolutionary Metrics Dashboard

class EvoDashboard {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        this.gridSize = 10;
        this.archiveData = null;
        this.history = [];
    }

    renderHeatmap(archiveStats, playerPos = null) {
        if (!this.ctx || !archiveStats || !archiveStats.grid) return;

        this.archiveData = archiveStats;
        const width = this.canvas.width;
        const height = this.canvas.height;
        const cellSize = width / this.gridSize;

        this.ctx.clearRect(0, 0, width, height);

        // Background
        this.ctx.fillStyle = "#090d16";
        this.ctx.fillRect(0, 0, width, height);

        const grid = archiveStats.grid;

        for (let x = 0; x < this.gridSize; x++) {
            for (let y = 0; y < this.gridSize; y++) {
                const cell = grid[x][y];
                const px = x * cellSize;
                const py = (this.gridSize - 1 - y) * cellSize; // Flip Y so 0 is bottom

                if (cell) {
                    // Color based on fitness (red -> yellow -> emerald)
                    const fit = cell.fitness;
                    const r = Math.floor(255 * Math.max(0, 1 - (fit - 0.5) * 2));
                    const g = Math.floor(255 * Math.min(1, fit * 1.5));
                    const b = 100;
                    this.ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
                    this.ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);

                    // Fitness label inside cell
                    this.ctx.fillStyle = "#000";
                    this.ctx.font = "bold 9px 'JetBrains Mono', monospace";
                    this.ctx.textAlign = "center";
                    this.ctx.fillText(fit.toFixed(2), px + cellSize / 2, py + cellSize / 2 + 3);
                } else {
                    // Empty cell
                    this.ctx.fillStyle = "#161d2f";
                    this.ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
                }
            }
        }

        // Draw Player Niche Marker
        if (playerPos && typeof playerPos.x === 'number' && typeof playerPos.y === 'number') {
            const px = playerPos.x * cellSize + cellSize / 2;
            const py = (this.gridSize - 1 - playerPos.y) * cellSize + cellSize / 2;

            this.ctx.strokeStyle = "#00ffff";
            this.ctx.lineWidth = 2.5;
            this.ctx.beginPath();
            this.ctx.arc(px, py, cellSize / 3, 0, Math.PI * 2);
            this.ctx.stroke();

            this.ctx.fillStyle = "#ffffff";
            this.ctx.beginPath();
            this.ctx.arc(px, py, 3, 0, Math.PI * 2);
            this.ctx.fill();
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
