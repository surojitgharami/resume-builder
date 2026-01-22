import { useEffect, useRef, useState } from "react";

/**
 * Poll a resume status endpoint until complete or error.
 * Usage:
 * const { startPolling, status, resume, error, stop } = useResumePolling();
 * startPolling(resumeId);
 */
export default function useResumePolling({
    intervalMs = 1500,
    maxAttempts = 40,
} = {}) {
    const [status, setStatus] = useState<string | null>(null);
    const [resume, setResume] = useState<any | null>(null);
    const [error, setError] = useState<string | null>(null);
    const attemptsRef = useRef(0);
    const abortRef = useRef<AbortController | null>(null);
    const runningRef = useRef(false);

    const stop = () => {
        runningRef.current = false;
        if (abortRef.current) {
            abortRef.current.abort();
            abortRef.current = null;
        }
    };

    const pollOnce = async (resumeId: string) => {
        attemptsRef.current += 1;
        abortRef.current = new AbortController();
        try {
            const resp = await fetch(`/api/v1/resumes/${resumeId}`, { signal: abortRef.current.signal, credentials: "include" });
            if (!resp.ok) {
                const text = await resp.text().catch(() => "");
                throw new Error(`Status ${resp.status}: ${text}`);
            }
            const data = await resp.json();
            setResume(data.resume ?? data);
            setStatus(data.resume?.status ?? data.status ?? null);
            // done conditions
            if ((data.resume?.status ?? data.status) === "complete") {
                stop();
                return;
            }
            if ((data.resume?.status ?? data.status) === "error") {
                setError(data.resume?.error || data.error || "Resume generation failed");
                stop();
                return;
            }
        } catch (e: any) {
            if (e.name === "AbortError") {
                // ignore abort
                return;
            }
            setError(e.message || "Polling error");
            stop();
            return;
        }
    };

    const startPolling = (resumeId: string) => {
        if (!resumeId) throw new Error("resumeId required");
        if (runningRef.current) return;
        runningRef.current = true;
        attemptsRef.current = 0;
        setError(null);
        setStatus("processing");
        (async function loop() {
            while (runningRef.current && attemptsRef.current < maxAttempts) {
                await pollOnce(resumeId);
                if (!runningRef.current) break;
                // exponential backoff slight increase
                const delay = intervalMs + Math.min(attemptsRef.current * 200, 3000);
                await new Promise((r) => setTimeout(r, delay));
            }
            if (runningRef.current) {
                setError("Resume generation timed out");
                runningRef.current = false;
            }
        })();
    };

    useEffect(() => {
        return () => stop();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return { startPolling, status, resume, error, stop };
}
