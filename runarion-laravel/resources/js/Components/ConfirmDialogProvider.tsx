import {
    createContext,
    useCallback,
    useContext,
    useMemo,
    useRef,
    useState,
    type ReactNode,
} from "react";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/Components/ui/alert-dialog";

export interface ConfirmDialogOptions {
    title?: string;
    description: string;
    actionLabel?: string;
    cancelLabel?: string;
}

type ConfirmFn = (options: string | ConfirmDialogOptions) => Promise<boolean>;

const ConfirmDialogContext = createContext<ConfirmFn | null>(null);

interface PendingConfirm extends ConfirmDialogOptions {
    open: boolean;
}

export function ConfirmDialogProvider({
    children,
}: {
    children: ReactNode;
}) {
    const resolverRef = useRef<((value: boolean) => void) | null>(null);
    const [pendingConfirm, setPendingConfirm] = useState<PendingConfirm | null>(
        null,
    );

    const closeDialog = useCallback((result: boolean) => {
        resolverRef.current?.(result);
        resolverRef.current = null;
        setPendingConfirm(null);
    }, []);

    const confirm = useCallback<ConfirmFn>((options) => {
        return new Promise<boolean>((resolve) => {
            resolverRef.current = resolve;

            if (typeof options === "string") {
                setPendingConfirm({
                    open: true,
                    title: "Please confirm",
                    description: options,
                    actionLabel: "Continue",
                    cancelLabel: "Cancel",
                });
                return;
            }

            setPendingConfirm({
                open: true,
                title: options.title || "Please confirm",
                description: options.description,
                actionLabel: options.actionLabel || "Continue",
                cancelLabel: options.cancelLabel || "Cancel",
            });
        });
    }, []);

    const value = useMemo(() => confirm, [confirm]);

    return (
        <ConfirmDialogContext.Provider value={value}>
            {children}

            <AlertDialog
                open={pendingConfirm?.open ?? false}
                onOpenChange={(open) => {
                    if (!open) {
                        closeDialog(false);
                    }
                }}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            {pendingConfirm?.title}
                        </AlertDialogTitle>
                        <AlertDialogDescription className="whitespace-pre-line">
                            {pendingConfirm?.description}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel
                            onClick={() => closeDialog(false)}
                        >
                            {pendingConfirm?.cancelLabel}
                        </AlertDialogCancel>
                        <AlertDialogAction onClick={() => closeDialog(true)}>
                            {pendingConfirm?.actionLabel}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </ConfirmDialogContext.Provider>
    );
}

export function useConfirm(): ConfirmFn {
    const context = useContext(ConfirmDialogContext);

    if (!context) {
        throw new Error(
            "useConfirm must be used within a ConfirmDialogProvider",
        );
    }

    return context;
}
