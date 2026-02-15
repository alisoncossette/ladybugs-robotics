/* Orchestration Walkthrough Controller
   Replays the BookReaderOrchestrator state machine visually. */

class WalkthroughController {
    constructor() {
        this.mode = 'prerecorded';    // prerecorded | live
        this.readingMode = 'verbose'; // verbose | skim
        this.state = 'idle';          // idle | playing | paused | complete
        this.speed = 1;
        this.cycleIdx = 0;
        this.substepIdx = 0;
        this._paused = false;
        this._pauseResolve = null;
        this._aborted = false;
        this._textStreamAbort = false;
        this.totalWordsRead = 0;
        this.totalStepsExecuted = 0;
        this.sessionStartTime = 0;

        // DOM refs
        this.timelineEl = document.getElementById('timeline');
        this.bookImageEl = document.getElementById('book-image');
        this.bookInfoEl = document.getElementById('book-info');
        this.motorOverlay = document.getElementById('motor-overlay');
        this.motorGif = document.getElementById('motor-gif');
        this.motorLabelEl = document.getElementById('motor-label');
        this.textContentEl = document.getElementById('text-content');
        this.textLabelEl = document.getElementById('text-label');
        this.wordCountEl = document.getElementById('word-count');
        this.cursorEl = document.getElementById('cursor');
        this.audioEl = document.getElementById('audio-player');

        this.bindControls();
    }

    bindControls() {
        document.getElementById('btn-play').addEventListener('click', () => this.play());
        document.getElementById('btn-pause').addEventListener('click', () => this.pause());
        document.getElementById('btn-step').addEventListener('click', () => this.stepForward());
        document.getElementById('btn-restart').addEventListener('click', () => this.restart());
        document.getElementById('speed-select').addEventListener('change', (e) => {
            this.speed = parseInt(e.target.value);
        });

        // Mode toggles
        document.getElementById('btn-prerecorded').addEventListener('click', () => {
            this.mode = 'prerecorded';
            document.getElementById('btn-prerecorded').classList.add('active');
            document.getElementById('btn-live').classList.remove('active');
            document.getElementById('live-dot').style.display = 'none';
        });
        document.getElementById('btn-live').addEventListener('click', async () => {
            const url = prompt('Enter Vultr API base URL:', 'http://localhost:8000');
            if (!url) return;
            LiveAPI.setBaseUrl(url);
            const dot = document.getElementById('live-dot');
            dot.style.display = 'inline-block';
            dot.className = 'live-dot';
            const ok = await LiveAPI.healthCheck();
            dot.classList.add(ok ? 'connected' : 'disconnected');
            if (ok) {
                this.mode = 'live';
                document.getElementById('btn-live').classList.add('active');
                document.getElementById('btn-prerecorded').classList.remove('active');
            } else {
                alert('Could not connect to API. Staying in pre-recorded mode.');
            }
        });

        document.getElementById('btn-verbose').addEventListener('click', () => {
            this.readingMode = 'verbose';
            document.getElementById('btn-verbose').classList.add('active');
            document.getElementById('btn-skim').classList.remove('active');
        });
        document.getElementById('btn-skim').addEventListener('click', () => {
            this.readingMode = 'skim';
            document.getElementById('btn-skim').classList.add('active');
            document.getElementById('btn-verbose').classList.remove('active');
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === ' ') { e.preventDefault(); this.state === 'playing' ? this.pause() : this.play(); }
            if (e.key === 'ArrowRight') { e.preventDefault(); this.stepForward(); }
        });
    }

    // ── Playback Controls ──

    async play() {
        if (this.state === 'complete') return;

        if (this.state === 'paused') {
            this._paused = false;
            if (this._pauseResolve) this._pauseResolve();
            this.showPlayState(true);
            return;
        }

        if (this.state === 'playing') return;

        this.state = 'playing';
        this._aborted = false;
        this.sessionStartTime = performance.now();
        this.showPlayState(true);
        this.buildTimeline();

        for (let c = this.cycleIdx; c < WALKTHROUGH_SESSION.steps.length; c++) {
            if (this._aborted) break;
            this.cycleIdx = c;
            const cycle = WALKTHROUGH_SESSION.steps[c];

            for (let s = (c === this.cycleIdx ? this.substepIdx : 0); s < cycle.substeps.length; s++) {
                if (this._aborted) break;
                this.substepIdx = s;
                await this.executeSubstep(c, s);
                await this.checkPaused();
            }
            this.substepIdx = 0;
        }

        if (!this._aborted) this.showComplete();
    }

    pause() {
        if (this.state !== 'playing') return;
        this.state = 'paused';
        this._paused = true;
        this.audioEl.pause();
        this.showPlayState(false);
    }

    async stepForward() {
        if (this.state === 'complete') return;

        if (this.state === 'idle') {
            this.sessionStartTime = performance.now();
            this.buildTimeline();
        }

        this.state = 'paused';
        this._paused = true;
        this.showPlayState(false);

        const cycle = WALKTHROUGH_SESSION.steps[this.cycleIdx];
        if (!cycle) { this.showComplete(); return; }

        await this.executeSubstep(this.cycleIdx, this.substepIdx);
        this.substepIdx++;

        if (this.substepIdx >= cycle.substeps.length) {
            this.cycleIdx++;
            this.substepIdx = 0;
        }
        if (this.cycleIdx >= WALKTHROUGH_SESSION.steps.length) {
            this.showComplete();
        }
    }

    restart() {
        this._aborted = true;
        this._paused = false;
        if (this._pauseResolve) this._pauseResolve();
        this.state = 'idle';
        this.cycleIdx = 0;
        this.substepIdx = 0;
        this.totalWordsRead = 0;
        this.totalStepsExecuted = 0;
        this.audioEl.pause();
        this.audioEl.currentTime = 0;
        this.timelineEl.innerHTML = '';
        this.textContentEl.innerHTML = '<span class="cursor" id="cursor"></span>';
        this.cursorEl = document.getElementById('cursor');
        this.wordCountEl.textContent = '';
        this.bookInfoEl.textContent = 'Waiting to start...';
        this.bookImageEl.src = 'images/spread-closed.jpg';
        this.motorOverlay.style.display = 'none';
        document.getElementById('session-complete').style.display = 'none';
        this.showPlayState(false);
    }

    // ── Timeline Building ──

    buildTimeline() {
        this.timelineEl.innerHTML = '';
        WALKTHROUGH_SESSION.steps.forEach((cycle, ci) => {
            // Cycle divider
            const divider = document.createElement('div');
            divider.className = 'cycle-divider';
            divider.textContent = cycle.label;
            divider.id = `divider-${ci}`;
            this.timelineEl.appendChild(divider);

            cycle.substeps.forEach((sub, si) => {
                const node = this.createStepNode(ci, si, sub);
                this.timelineEl.appendChild(node);
            });
        });
    }

    createStepNode(ci, si, sub) {
        const node = document.createElement('div');
        node.className = 'step-node pending';
        node.id = `step-${ci}-${si}`;

        node.innerHTML = `
            <div class="step-dot">${sub.icon || ''}</div>
            <div class="step-line"></div>
            <div class="step-card">
                <div class="step-card-header">
                    <span class="step-action">${sub.label}</span>
                    <span class="step-elapsed"></span>
                    <span class="step-spinner"></span>
                </div>
                <div class="step-detail">
                    <div class="step-input" style="font-size:0.7rem; color:var(--text-light);">${sub.input}</div>
                    <div class="step-result"></div>
                    <div class="step-decision"></div>
                </div>
            </div>
        `;
        return node;
    }

    // ── Step Execution ──

    async executeSubstep(ci, si) {
        const cycle = WALKTHROUGH_SESSION.steps[ci];
        const sub = cycle.substeps[si];
        const node = document.getElementById(`step-${ci}-${si}`);

        // Update book image on first substep of cycle
        if (si === 0) {
            this.bookImageEl.src = cycle.image;
            const spreadNum = ci + 1;
            this.bookInfoEl.textContent = `${WALKTHROUGH_SESSION.book.title} \u2014 Spread ${spreadNum} of ${WALKTHROUGH_SESSION.steps.length}`;
        }

        // Set running state
        node.className = 'step-node running';
        this.scrollToStep(node);

        // Show motor animation if applicable
        if (sub.animationOverlay) {
            this.motorGif.src = sub.animationOverlay;
            this.motorLabelEl.textContent = sub.motorLabel || 'Executing...';
            this.motorOverlay.style.display = 'flex';
        }

        // Wait for elapsed time
        const waitMs = sub.elapsed_ms / this.speed;
        const elapsedEl = node.querySelector('.step-elapsed');

        // Animate elapsed counter
        const startTime = performance.now();
        const counterInterval = setInterval(() => {
            const elapsed = performance.now() - startTime;
            elapsedEl.textContent = (elapsed / 1000).toFixed(1) + 's';
        }, 100);

        await this.sleep(Math.min(waitMs, 3000 / this.speed)); // Cap visual wait at 3s

        clearInterval(counterInterval);
        elapsedEl.textContent = (sub.elapsed_ms / 1000).toFixed(1) + 's';

        // Show result
        const resultEl = node.querySelector('.step-result');
        const resultText = sub.result || '';
        if (resultText.length > 80) {
            resultEl.textContent = resultText.substring(0, 80) + '...';
        } else {
            resultEl.textContent = resultText;
        }

        const decisionEl = node.querySelector('.step-decision');
        decisionEl.textContent = sub.decision || '';

        // Handle read steps — stream text + play audio
        if (sub.action === 'read_left' || sub.action === 'read_right') {
            const label = sub.action === 'read_left' ? 'Left Page' : 'Right Page';
            this.textLabelEl.textContent = `Reading ${label}`;

            if (sub.action === 'read_left') {
                this.textContentEl.innerHTML = '';
                this.cursorEl = document.createElement('span');
                this.cursorEl.className = 'cursor';
                this.textContentEl.appendChild(this.cursorEl);
            }

            // Play audio
            if (sub.audio) {
                this.audioEl.src = sub.audio;
                if (sub.audioStart) this.audioEl.currentTime = sub.audioStart;
                try { await this.audioEl.play(); } catch (e) { /* autoplay blocked */ }
                if (sub.audioEnd) {
                    const stopAt = sub.audioEnd;
                    const checkAudio = setInterval(() => {
                        if (this.audioEl.currentTime >= stopAt) {
                            this.audioEl.pause();
                            clearInterval(checkAudio);
                        }
                    }, 200);
                }
            }

            // Stream text
            await this.streamText(sub.result);
            const words = sub.result.split(/\s+/).filter(w => w.length > 0).length;
            this.totalWordsRead += words;
            this.wordCountEl.textContent = `${this.totalWordsRead} words total`;
        }

        // Hide motor overlay
        this.motorOverlay.style.display = 'none';

        // Mark complete
        node.className = sub.skipped ? 'step-node skipped' : 'step-node complete';
        this.totalStepsExecuted++;
    }

    async streamText(text) {
        if (!text) return;
        this._textStreamAbort = false;
        const chars = text.split('');
        const charsPerTick = Math.max(1, Math.floor(this.speed));
        for (let i = 0; i < chars.length; i += charsPerTick) {
            if (this._textStreamAbort) break;
            const chunk = chars.slice(i, i + charsPerTick).join('');
            this.textContentEl.insertBefore(
                document.createTextNode(chunk),
                this.cursorEl
            );
            this.textContentEl.scrollTop = this.textContentEl.scrollHeight;
            await this.sleep(20);
            await this.checkPaused();
        }
    }

    // ── Utilities ──

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    checkPaused() {
        if (!this._paused) return Promise.resolve();
        return new Promise(resolve => { this._pauseResolve = resolve; });
    }

    scrollToStep(node) {
        node.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    showPlayState(playing) {
        document.getElementById('btn-play').style.display = playing ? 'none' : 'flex';
        document.getElementById('btn-pause').style.display = playing ? 'flex' : 'none';
    }

    showComplete() {
        this.state = 'complete';
        this.showPlayState(false);
        const elapsed = ((performance.now() - this.sessionStartTime) / 1000).toFixed(0);
        const statsEl = document.getElementById('complete-stats');
        statsEl.innerHTML = `
            <div class="stat-item">
                <div class="stat-num">${this.totalStepsExecuted}</div>
                <div class="stat-label">Steps</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">${this.totalWordsRead}</div>
                <div class="stat-label">Words Read</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">${elapsed}s</div>
                <div class="stat-label">Duration</div>
            </div>
        `;
        document.getElementById('session-complete').style.display = 'flex';
        this.cursorEl.classList.add('hidden');
    }
}

// Initialize
const walkthrough = new WalkthroughController();
