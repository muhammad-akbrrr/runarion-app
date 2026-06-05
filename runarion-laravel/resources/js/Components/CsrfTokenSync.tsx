import { usePage } from "@inertiajs/react";
import { useEffect } from "react";
import { syncCsrfToken } from "@/Lib/http";
import type { PageProps } from "@/types";

export default function CsrfTokenSync() {
    const page = usePage<PageProps>();
    const { auth } = page.props;

    useEffect(() => {
        syncCsrfToken(auth?.csrf_token);
    }, [page.url, auth?.csrf_token]);

    return null;
}
