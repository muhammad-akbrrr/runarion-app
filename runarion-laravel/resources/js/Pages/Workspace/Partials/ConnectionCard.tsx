import { Button } from "@/Components/ui/button";

export default function ConnectionCard({
    logo_url,
    name,
    description,
    connected,
    onConnect,
    disabled = false,
}: {
    logo_url: string;
    name: string;
    description: string;
    connected: boolean;
    onConnect: () => void;
    disabled?: boolean;
}) {
    return (
        <div className="flex h-24 items-center justify-between border border-slate-400 rounded-md p-4 bg-slate-50">
            <div className="flex items-center gap-4">
                <img
                    src={logo_url}
                    alt={`${name} logo`}
                    className="w-16 max-w-16 max-h-16"
                />
                <div>
                    <div className="font-semibold">{name}</div>
                    <div className="text-sm text-muted-foreground">
                        {description}
                    </div>
                </div>
            </div>
            <Button
                variant={connected ? "default" : "destructive"}
                className={
                    connected
                        ? "bg-blue-500 text-white shadow-xs hover:bg-blue-600 focus-visible:ring-blue-500 text-sm"
                        : "text-sm"
                }
                onClick={onConnect}
                disabled={disabled}
            >
                {connected ? "Connected" : "Connect"}
            </Button>
        </div>
    );
}