// The workspaces, in the order work flows through the firm. One definition drives
// the sidebar, the phone menu and the page titles.
export const WORKSPACES = [
  {label: 'My work', items: [{to: '/', label: 'My work', end: true}]},
  {label: 'Leads', items: [{to: '/leads', label: 'Leads', end: true}, {to: '/leads/new', label: 'New lead or client'}, {to: '/offices', label: 'Client offices'}]},
  {label: 'Valuation', items: [{to: '/valuations', label: 'Valuations'}]},
  {label: 'Review', items: [{to: '/verification', label: 'Verification'}, {to: '/bank-reports', label: 'Bank reports'}, {to: '/approval', label: 'Final approval'}]},
  {label: 'Finance', items: [{to: '/invoices', label: 'Invoices'}, {to: '/receipts', label: 'Receipts'}]},
  {label: 'Dispatch', items: [{to: '/dispatch', label: 'Dispatch'}]},
  {label: 'Reports', items: [{to: '/reports', label: 'Reports'}]},
  {label: 'System', items: [{to: '/system/migration', label: 'Migration status'}, {to: '/system/imports', label: 'Import history'}]},
];

// The phone's bottom bar: the three places people go most, and the full menu.
export const PHONE_TABS = [
  {to: '/', label: 'My work', end: true},
  {to: '/valuations', label: 'Valuations'},
  {to: '/verification', label: 'Review'},
];
