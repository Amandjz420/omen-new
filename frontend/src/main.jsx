import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/notifications/styles.css';
import './global.css';
import './legacy.css';

import {MantineProvider} from '@mantine/core';
import {ModalsProvider} from '@mantine/modals';
import {Notifications} from '@mantine/notifications';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {lazy, Suspense} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserRouter, Route, Routes} from 'react-router';

import {theme} from './app/theme.js';
import {SessionProvider} from './app/session.jsx';
import {Shell} from './app/Shell.jsx';
import {Gate} from './screens/Gate.jsx';
import {Home} from './screens/Home.jsx';
import {LeadDetail, Leads} from './screens/Leads.jsx';
import {Offices} from './screens/Offices.jsx';
import {ImportHistory, MigrationStatus} from './screens/System.jsx';
import {NotFound} from './screens/NotFound.jsx';
import {LegacyScreen} from './screens/LegacyScreen.jsx';

import {LoadingState} from './components/States.jsx';

// Each workflow screen is loaded when first opened, so a phone on weak signal
// downloads only what the person uses.
const screen = (loader, name) => lazy(() => loader().then(module => ({default: module[name]})));
const IntakeWorkspace = screen(() => import('./intake.jsx'), 'default');
const Valuations = screen(() => import('./valuations.jsx'), 'Valuations');
const Verifications = screen(() => import('./verifications.jsx'), 'Verifications');
const BankReports = screen(() => import('./bankreports.jsx'), 'BankReports');
const Approvals = screen(() => import('./approvals.jsx'), 'Approvals');
const Invoices = screen(() => import('./invoices.jsx'), 'Invoices');
const Receipts = screen(() => import('./receipts.jsx'), 'Receipts');
const Dispatch = screen(() => import('./dispatch.jsx'), 'Dispatch');

// A failed request is shown to the person, not silently repeated: many of these
// endpoints change money or state, and retrying them is the server's decision.
const queryClient = new QueryClient({defaultOptions: {queries: {retry: 1, refetchOnWindowFocus: false, staleTime: 15_000},
                                                       mutations: {retry: 0}}});

const legacy = (title, description, component) => <Suspense fallback={<LoadingState label={`Opening ${title.toLowerCase()}`}/>}>
  <LegacyScreen title={title} description={description} component={component}/>
</Suspense>;

export function App() {
  return <MantineProvider theme={theme} defaultColorScheme="light">
    <Notifications position="top-right"/>
    <QueryClientProvider client={queryClient}>
      <ModalsProvider>
        <SessionProvider>
          <BrowserRouter>
            <Gate>
              <Routes>
                <Route element={<Shell/>}>
                  <Route index element={<Home/>}/>
                  <Route path="leads" element={<Leads/>}/>
                  <Route path="leads/new" element={legacy('New lead or client', 'Record a client office, its contacts, and a new lead.', IntakeWorkspace)}/>
                  <Route path="leads/:id" element={<LeadDetail/>}/>
                  <Route path="offices" element={<Offices/>}/>
                  <Route path="valuations" element={legacy('Valuations', 'Start a valuation, fill in its form, and submit it for verification.', Valuations)}/>
                  <Route path="verification" element={legacy('Verification', 'Legal, technical, social and general checks, each in its own queue.', Verifications)}/>
                  <Route path="bank-reports" element={legacy('Bank reports', 'Prepare the report a bank receives, once all four checks are done.', BankReports)}/>
                  <Route path="approval" element={legacy('Final approval', 'Issue reports to banks, or send them back for correction.', Approvals)}/>
                  <Route path="invoices" element={legacy('Invoices', 'Tax invoices, payments, write-offs and credit notes.', Invoices)}/>
                  <Route path="receipts" element={legacy('Receipts', 'Money received, made, checked and verified before it counts.', Receipts)}/>
                  <Route path="dispatch" element={legacy('Dispatch', 'Send approved reports and track them to delivery.', Dispatch)}/>
                  <Route path="system/migration" element={<MigrationStatus/>}/>
                  <Route path="system/imports" element={<ImportHistory/>}/>
                  <Route path="*" element={<NotFound/>}/>
                </Route>
              </Routes>
            </Gate>
          </BrowserRouter>
        </SessionProvider>
      </ModalsProvider>
    </QueryClientProvider>
  </MantineProvider>;
}

const root = document.getElementById('root');
if (root) createRoot(root).render(<App/>);
