/* Live API client for calling the Vultr-hosted FastAPI */

const LiveAPI = {
    baseUrl: '', // Set via UI or config

    setBaseUrl(url) {
        this.baseUrl = url.replace(/\/$/, '');
    },

    async healthCheck() {
        try {
            const res = await fetch(`${this.baseUrl}/health`, { signal: AbortSignal.timeout(5000) });
            const data = await res.json();
            return data.status === 'ok';
        } catch {
            return false;
        }
    },

    async assess(imageBlob) {
        const formData = new FormData();
        formData.append('file', imageBlob, 'frame.jpg');
        const t0 = performance.now();
        const res = await fetch(`${this.baseUrl}/api/assess`, { method: 'POST', body: formData });
        const data = await res.json();
        data._elapsed_ms = Math.round(performance.now() - t0);
        return data;
    },

    async classify(imageBlob) {
        const formData = new FormData();
        formData.append('file', imageBlob, 'frame.jpg');
        const t0 = performance.now();
        const res = await fetch(`${this.baseUrl}/api/classify`, { method: 'POST', body: formData });
        const data = await res.json();
        data._elapsed_ms = Math.round(performance.now() - t0);
        return data;
    },

    async readSpread(imageBlob, mode = 'verbose') {
        const formData = new FormData();
        formData.append('file', imageBlob, 'frame.jpg');
        formData.append('mode', mode);
        const t0 = performance.now();
        const res = await fetch(`${this.baseUrl}/api/read-spread`, { method: 'POST', body: formData });
        const data = await res.json();
        data._elapsed_ms = Math.round(performance.now() - t0);
        return data;
    },

    async fetchImageBlob(imageUrl) {
        const res = await fetch(imageUrl);
        return await res.blob();
    }
};
