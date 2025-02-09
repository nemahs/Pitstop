import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {createInertiaApp} from '@inertiajs/react';
import { Layout } from "./pages/App";

import '@mantine/core/styles.css'
import { MantineProvider } from '@mantine/core'


document.addEventListener('DOMContentLoaded', () => {
    createInertiaApp({
        resolve: (name) => {
            const pages = import.meta.glob('./pages/**/*.tsx', {eager: true});
            let page: any = pages[`./pages/${name}.tsx`];
            page.default.layout = page.default.layout || ((page: any) => <MantineProvider defaultColorScheme='dark'><Layout type={page.type} {...page.props}>{page}</Layout></MantineProvider>);
            return page;
        },
        setup({el, App, props}) {
            createRoot(el).render(
              <MantineProvider defaultColorScheme='dark'>           
                <StrictMode>
                    <App {...props} />
                </StrictMode>
              </MantineProvider>
            );
        }
    }).then(() => {
    });
});