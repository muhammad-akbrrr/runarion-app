import '../css/app.css';
import './bootstrap';

import { createInertiaApp } from '@inertiajs/react';
import { resolvePageComponent } from 'laravel-vite-plugin/inertia-helpers';
import type { ComponentType, ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { Toaster } from '@/Components/ui/sonner';
import CsrfTokenSync from '@/Components/CsrfTokenSync';
import { ConfirmDialogProvider } from '@/Components/ConfirmDialogProvider';

const appName = import.meta.env.VITE_APP_NAME || 'Laravel';
type LayoutFunction = (page: ReactNode) => ReactNode;
type LayoutComponent = ComponentType<{ children: ReactNode }>;
type ReactComponentWithLayout = ComponentType<any> & {
    layout?: LayoutComponent | LayoutComponent[] | LayoutFunction;
};

createInertiaApp({
    title: (title) => `${title} - ${appName}`,
    resolve: (name) =>
        resolvePageComponent(
            `./Pages/${name}.tsx`,
            import.meta.glob('./Pages/**/*.tsx'),
        ),
    setup({ el, App, props }) {
        const root = createRoot(el);

        root.render(
            <ConfirmDialogProvider>
                <App {...props}>
                    {({ Component, props: pageProps, key }) => {
                        const PageComponent = Component as ReactComponentWithLayout;
                        const page = <PageComponent key={key} {...pageProps} />;

                        if (typeof PageComponent.layout === 'function') {
                            const layout = PageComponent.layout as LayoutFunction;

                            return (
                                <>
                                    <CsrfTokenSync />
                                    {layout(page)}
                                </>
                            );
                        }

                        if (Array.isArray(PageComponent.layout)) {
                            const layouts = PageComponent.layout as LayoutComponent[];

                            return (
                                <>
                                    <CsrfTokenSync />
                                    {layouts
                                        .slice()
                                        .reverse()
                                        .reduce<ReactNode>(
                                            (children, Layout) => (
                                                <Layout {...pageProps}>{children}</Layout>
                                            ),
                                            page,
                                        )}
                                </>
                            );
                        }

                        return (
                            <>
                                <CsrfTokenSync />
                                {page}
                            </>
                        );
                    }}
                </App>
                <Toaster />
            </ConfirmDialogProvider>
        );
    },
    progress: {
        color: '#4B5563',
    },
});
