import {MantineProvider} from '@mantine/core';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {render} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
import {theme} from '../app/theme.js';

/** Render inside the same providers the app uses. */
export function renderApp(ui, {route = '/'} = {}) {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  // env="test": Mantine without transitions or portals, so dropdowns open synchronously in jsdom.
  return render(<MantineProvider theme={theme} env="test"><QueryClientProvider client={client}>
    <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter></QueryClientProvider></MantineProvider>);
}
