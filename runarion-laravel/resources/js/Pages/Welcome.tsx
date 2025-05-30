import { Button } from "@/Components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/Components/ui/card";
import { Head, Link } from '@inertiajs/react';

export default function Welcome({ auth, laravelVersion, phpVersion }: { auth: any, laravelVersion: string, phpVersion: string }) {
    return (
        <>
            <Head title="Welcome" />
            <div className="relative sm:flex sm:justify-center sm:items-center min-h-screen bg-background">
                <div className="max-w-7xl mx-auto p-6 lg:p-8">
                    <div className="flex justify-center">
                        <h1 className="text-4xl font-bold text-foreground">
                            Welcome to Runarion
                        </h1>
                    </div>

                    <div className="mt-16">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8">
                            <Card className="flex flex-col gap-4 justify-between items-stretch">
                                <CardHeader>
                                    <CardTitle>About Runarion</CardTitle>
                                    <CardDescription>
                                        Your new application is ready to explore.
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-muted-foreground">
                                        Built with Laravel {laravelVersion} and PHP {phpVersion}
                                    </p>
                                </CardContent>
                            </Card>

                            <Card className="flex flex-col gap-4 justify-between items-stretch">
                                <CardHeader>
                                    <CardTitle>Getting Started</CardTitle>
                                    <CardDescription>
                                        Ready to begin your journey?
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {auth.user ? (
                                        <Link href={route('workspace.dashboard', auth.user.primary_workspace_id)}>
                                            <Button className="w-full">
                                                Go to Dashboard
                                            </Button>
                                        </Link>
                                    ) : (
                                        <div className="flex flex-col gap-2">
                                            <Link href={route('login')}>
                                                <Button className="w-full">
                                                    Log in
                                                </Button>
                                            </Link>
                                            <Link href={route('register')}>
                                                <Button variant="outline" className="w-full">
                                                    Register
                                                </Button>
                                            </Link>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}
