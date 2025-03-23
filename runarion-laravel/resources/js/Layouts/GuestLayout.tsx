import ApplicationLogo from '@/Components/application-logo';
import { Link } from '@inertiajs/react';
import { PropsWithChildren } from 'react';
import { Card } from "@/Components/ui/card";

export default function Guest({ children }: PropsWithChildren) {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-background p-6">
            <div className="mb-8">
                <Link href="/">
                    <ApplicationLogo className="h-16 w-16 fill-current text-muted-foreground" />
                </Link>
            </div>

            <Card className="w-full max-w-md p-6">
                {children}
            </Card>
        </div>
    );
}
