import ApplicationLogo from "@/Components/application-logo";
import { PageProps } from "@/types";
import { Head } from "@inertiajs/react";

export default function Invitation({
    status,
}: PageProps<{
    status: "success" | "invalid" | "unregistered";
}>) {
    const titles = {
        success: "Success",
        invalid: "Invalid Invitation",
        unregistered: "Unregistered User",
    };

    const descriptions = {
        success:
            "You have successfully accepted the workspace invitation. Welcome aboard!",
        invalid: "The invitation link you used is invalid.",
        unregistered:
            "It seems you are not registered. Please sign up to Runarion then try again.",
    };

    return (
        <>
            <Head title="Workspace Invitation" />
            <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-4">
                <div className="bg-white shadow-md rounded-lg p-6 max-w-lg w-full">
                    <div className="flex items-center justify-center gap-4 mb-6">
                        <ApplicationLogo className="block h-8 w-auto fill-current text-muted-foreground" />
                        <div className="text-lg font-bold text-gray-600">
                            Runarion Workspace Invitation
                        </div>
                    </div>
                    <h1 className="text-3xl font-bold text-gray-800 mb-4 text-center">
                        {titles[status]}
                    </h1>
                    <p className="text-gray-600 text-center">
                        {descriptions[status]}
                    </p>
                </div>
            </div>
        </>
    );
}
