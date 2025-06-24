import { Button } from "@/Components/ui/button";

export default function ConnectionCard({
    logo_url,
    name,
    description,
    connected,
    onConnect,
    onDisconnect,
    disabled = false,
}: {
    logo_url: string;
    name: string;
    description: string;
    connected: boolean;
    onConnect: () => void;
    onDisconnect?: () => void;
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
            {connected ? (
                <div className="flex gap-2">
                    <Button
                        variant="default"
                        className="bg-blue-500 text-white shadow-xs hover:bg-blue-600 focus-visible:ring-blue-500 text-sm"
                        disabled={true}
                    >
                        Connected
                    </Button>
                    <Button
                        variant="destructive"
                        className="text-sm"
                        onClick={onDisconnect}
                        disabled={disabled}
                    >
                        Disconnect
                    </Button>
                </div>
            ) : (
                <Button
                    variant="default"
                    className="bg-blue-500 text-white shadow-xs hover:bg-blue-600 focus-visible:ring-blue-500 text-sm"
                    onClick={onConnect}
                    disabled={disabled}
                >
                    Connect
                </Button>
            )}
        </div>
    );
}
