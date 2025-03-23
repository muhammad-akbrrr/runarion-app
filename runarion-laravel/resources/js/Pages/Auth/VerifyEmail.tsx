import { Button } from "@/Components/ui/button";
import GuestLayout from '@/Layouts/GuestLayout';
import { Head, Link, useForm } from '@inertiajs/react';
import { FormEventHandler } from 'react';

export default function VerifyEmail({ status }: { status?: string }) {
    const { post, processing } = useForm({});

    const submit: FormEventHandler = (e) => {
        e.preventDefault();

        post(route('verification.send'));
    };

    return (
        <GuestLayout>
            <Head title="Email Verification" />

            <div className="space-y-6">
                <div>
                    <h2 className="text-2xl font-semibold tracking-tight">Email Verification</h2>
                    <p className="text-sm text-muted-foreground">
                        Thanks for signing up! Before getting started, could you verify your email address by clicking on the link we just emailed to you? If you didn't receive the email, we will gladly send you another.
                    </p>
                </div>

                {status === 'verification-link-sent' && (
                    <div className="text-sm font-medium text-green-600 dark:text-green-400">
                        A new verification link has been sent to the email address you provided during registration.
                    </div>
                )}

                <form onSubmit={submit} className="flex items-center justify-between">
                    <Button type="submit" disabled={processing}>
                        Resend Verification Email
                    </Button>

                    <Link
                        href={route('logout')}
                        method="post"
                        as="button"
                        className="text-sm text-muted-foreground hover:text-foreground underline"
                    >
                        Log Out
                    </Link>
                </form>
            </div>
        </GuestLayout>
    );
}
