import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import GuestLayout from '@/Layouts/GuestLayout';
import { Head, useForm } from '@inertiajs/react';
import { FormEventHandler } from 'react';
import { cn } from "@/Lib/utils";

export default function ConfirmPassword() {
    const { data, setData, post, processing, errors, reset } = useForm({
        password: '',
    });

    const submit: FormEventHandler = (e) => {
        e.preventDefault();

        post(route('password.confirm'), {
            onFinish: () => reset('password'),
        });
    };

    return (
        <GuestLayout>
            <Head title="Confirm Password" />

            <div className="space-y-6">
                <div>
                    <h2 className="text-2xl font-semibold tracking-tight">Confirm Password</h2>
                    <p className="text-sm text-muted-foreground">
                        This is a secure area of the application. Please confirm your password before continuing.
                    </p>
                </div>

                <form onSubmit={submit} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="password">Password</Label>
                        <Input
                            id="password"
                            type="password"
                            name="password"
                            value={data.password}
                            onChange={(e) => setData('password', e.target.value)}
                            className={cn(errors.password && "border-destructive")}
                        />
                        {errors.password && (
                            <p className="text-sm text-destructive">{errors.password}</p>
                        )}
                    </div>

                    <Button type="submit" disabled={processing} className="w-full">
                        Confirm
                    </Button>
                </form>
            </div>
        </GuestLayout>
    );
}
