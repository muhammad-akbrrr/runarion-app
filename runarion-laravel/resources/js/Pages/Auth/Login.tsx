import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { Checkbox } from "@/Components/ui/checkbox";
import GuestLayout from '@/Layouts/GuestLayout';
import { Head, Link, useForm } from '@inertiajs/react';
import { FormEventHandler } from 'react';
import { cn } from "@/Lib/utils";

export default function Login({
    status,
    canResetPassword,
}: {
    status?: string;
    canResetPassword: boolean;
}) {
    const { data, setData, post, processing, errors, reset } = useForm({
        email: '',
        password: '',
        remember: false as boolean,
    });

    const submit: FormEventHandler = (e) => {
        e.preventDefault();

        post(route('login'), {
            onFinish: () => reset('password'),
        });
    };

    return (
        <GuestLayout>
            <Head title="Log in" />

            <div className="space-y-6">
                <div>
                    <h2 className="text-2xl font-semibold tracking-tight">Log in</h2>
                    <p className="text-sm text-muted-foreground">
                        Enter your credentials to access your account
                    </p>
                </div>

                {status && (
                    <div className="text-sm font-medium text-green-600 dark:text-green-400">
                        {status}
                    </div>
                )}

                <form onSubmit={submit} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input
                            id="email"
                            type="email"
                            name="email"
                            value={data.email}
                            autoComplete="username"
                            onChange={(e) => setData('email', e.target.value)}
                            className={cn(errors.email && "border-destructive")}
                        />
                        {errors.email && (
                            <p className="text-sm text-destructive">{errors.email}</p>
                        )}
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="password">Password</Label>
                        <Input
                            id="password"
                            type="password"
                            name="password"
                            value={data.password}
                            autoComplete="current-password"
                            onChange={(e) => setData('password', e.target.value)}
                            className={cn(errors.password && "border-destructive")}
                        />
                        {errors.password && (
                            <p className="text-sm text-destructive">{errors.password}</p>
                        )}
                    </div>

                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="remember"
                            checked={data.remember}
                            onCheckedChange={(checked) => setData('remember', checked as boolean)}
                        />
                        <Label htmlFor="remember" className="text-sm text-muted-foreground">
                            Remember me
                        </Label>
                    </div>

                    <div className="flex items-center justify-between">
                        {canResetPassword && (
                            <Link
                                href={route('password.request')}
                                className="text-sm text-muted-foreground hover:text-foreground underline"
                            >
                                Forgot your password?
                            </Link>
                        )}

                        <Button type="submit" disabled={processing}>
                            Log in
                        </Button>
                    </div>
                </form>
            </div>
        </GuestLayout>
    );
}
