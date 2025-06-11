import { useEffect, useRef, useState } from "react";
import { Progress } from "@/Components/ui/progress";

export default function LoadingOverlay({
    visible,
    message = "Loading project...",
    progress = 100,
}: {
    visible: boolean;
    message?: string;
    progress?: number;
}) {
    const [animatedProgress, setAnimatedProgress] = useState(0);
    const prevVisible = useRef(visible);
    const maxAnimatedProgress = useRef(0);

    useEffect(() => {
        if (visible && !prevVisible.current) {
            setAnimatedProgress(0);
            maxAnimatedProgress.current = 0;
        }
        prevVisible.current = visible;
    }, [visible]);

    useEffect(() => {
        if (!visible) return;
        let frame: number;
        let start: number | null = null;
        const startValue = Math.max(
            animatedProgress,
            maxAnimatedProgress.current
        );
        const targetValue = Math.max(progress, startValue);
        const duration = 600; // duration for each step
        const animate = (timestamp: number) => {
            if (start === null) start = timestamp;
            const elapsed = timestamp - start;
            const nextValue = Math.min(
                targetValue,
                startValue + (elapsed / duration) * (targetValue - startValue)
            );
            setAnimatedProgress(nextValue);
            maxAnimatedProgress.current = Math.max(
                maxAnimatedProgress.current,
                nextValue
            );
            if (elapsed < duration && nextValue < targetValue) {
                frame = requestAnimationFrame(animate);
            } else {
                setAnimatedProgress(targetValue);
                maxAnimatedProgress.current = Math.max(
                    maxAnimatedProgress.current,
                    targetValue
                );
            }
        };
        frame = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(frame);
    }, [progress, visible]);

    return (
        <div
            className={`fixed inset-0 z-[9999] flex items-center justify-center transition-opacity duration-300 bg-white ${
                visible
                    ? "opacity-100 pointer-events-auto"
                    : "opacity-0 pointer-events-none"
            }`}
            aria-hidden={!visible}
        >
            <div className="flex flex-col items-center gap-4 w-64">
                <div className="text-lg text-gray-700">{message}</div>
                <Progress value={animatedProgress} />
            </div>
        </div>
    );
}
