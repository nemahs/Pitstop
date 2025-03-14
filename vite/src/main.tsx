import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {createInertiaApp} from '@inertiajs/react';
import { Layout } from "./pages/App";

import '@mantine/core/styles.css'


document.addEventListener('DOMContentLoaded', () => {
    createInertiaApp({
        resolve: (name) => {
            const pages = import.meta.glob('./pages/**/*.tsx', {eager: true});
            let page: any = pages[`./pages/${name}.tsx`];
            page.default.layout = page.default.layout || ((page: any) => <Layout name={name} {...page.props}>{page}</Layout>);
            return page;
        },
        setup({el, App, props}) {
            createRoot(el).render(
            <StrictMode>
                <App {...props} />
            </StrictMode>
            );
        }
    }).then(() => {
    });
});