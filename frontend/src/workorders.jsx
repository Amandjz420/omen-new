import {uuid} from './lib/uuid.js';  // crypto.randomUUID exists only on secure pages
import {useLookups} from './screens/IntakeForms.jsx';
import {ResponsiveTable} from './components/ResponsiveTable.jsx';
import React, {useEffect, useRef, useState} from 'react';
import {IntakeLead} from './intake.jsx';

const when = value => value ? new Date(value).toLocaleString('en-IN') : '';

const label = (rows, code) => (rows || []).find(r => String(r.code) === String(code))?.label;

export function WorkOrders({api, leadId, onChange}) {
  const {data: lookups} = useLookups();
  const [state, setState] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  // One request id per borrower, kept until the order succeeds. A retry after a
  // lost response reuses it, so the server returns the original order rather
  // than issuing a second one.
  const pending = useRef({});

  async function load() {
    try {setState(await api(`work-orders/leads/${leadId}/`)); setError('');}
    catch (e) {setError(e.message);}
  }
  useEffect(() => {load();}, [leadId]);

  async function issue(borrower) {
    const lastOne = state.outstanding === 1;
    const warning = lastOne ? '\n\nThis is the last borrower without a work order, so the lead will be closed.' : '';
    if (!window.confirm(`Issue a work order for ${borrower.name}?${warning}`)) return;
    const key = pending.current[borrower.id] ||= uuid();
    setBusy(borrower.id); setError('');
    try {
      await api('work-orders/', {method: 'POST', body: JSON.stringify({request_id: key, borrower: borrower.id})});
      delete pending.current[borrower.id];
      await load();
      onChange?.();
    } catch (e) {setError(e.message);}
    finally {setBusy('');}
  }

  if (!state) return <section className="panel"><h3>Work orders</h3>{error ? <p role="alert" className="error">{error}</p> : <p>Loading work orders…</p>}</section>;
  const total = state.borrowers.length;
  return <section className="panel">
    <div className="section-title"><h3>Work orders</h3><span>{state.ordered} of {total} borrower{total === 1 ? '' : 's'} ordered</span></div>
    <p className="muted">A work order is issued per borrower. The lead closes once every active borrower has one.</p>
    {state.closed && state.outstanding > 0 && <p className="notice">This lead was closed with {state.outstanding} borrower{state.outstanding === 1 ? '' : 's'} still unordered, a known effect of the previous system. Their work orders can still be issued here.</p>}
    {state.closed && state.outstanding === 0 && <p className="notice">Every borrower is ordered and the lead is closed. Closure means the work has been ordered; it is not valuation approval or payment completion.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {total === 0 ? <p>Add a borrower before issuing work orders.</p> :
    <ResponsiveTable><table><thead><tr><th>Name of customer / owner</th><th>Cases entered</th><th>Paid by</th><th>Payment by mode</th><th>Payment mode</th><th>Work order</th><th></th></tr></thead><tbody>
      {state.borrowers.map(b => <tr key={b.id}>
        <td>{b.name}{(b.contact_number || b.email) && <><br/><small>{[b.contact_number, b.email].filter(Boolean).join(' · ')}</small></>}</td>
        <td className="num">{b.cases}{b.declared_cases ? `/${b.declared_cases}` : ''}</td>
        <td>{label(lookups?.payers, b.payer) || '—'}</td>
        <td>{b.fee_basis === 2 ? `Fixed ₹${Number(b.agreed_fee || 0).toLocaleString('en-IN')}` : label(lookups?.fee_bases, b.fee_basis) || '—'}</td>
        <td>{label(lookups?.payment_methods, b.customer_payment_method) || '—'}</td>
        <td>{b.work_order ? <><strong>{b.work_order.number}</strong>{b.work_order.issued_at && <><br/><small>{when(b.work_order.issued_at)}{b.work_order.issued_by ? ` · ${b.work_order.issued_by}` : ''}</small></>}</> : <span className="muted">Not issued</span>}</td>
        <td>{b.work_order
          ? (b.work_order.document_available
              ? <a href={`/api/work-orders/${b.work_order.id}/document/`} target="_blank" rel="noopener">View letter</a>
              : <small className="muted">{b.work_order.document ? 'Letter not found in storage' : 'No letter'}</small>)
          : b.eligible
            ? <button disabled={busy === b.id} onClick={() => issue(b)}>{busy === b.id ? 'Issuing…' : 'Issue work order'}</button>
            : <small className="muted">{b.reasons.join('; ')}</small>}</td>
      </tr>)}
    </tbody></table></ResponsiveTable>}
  </section>;
}

// Intake and work orders for one lead. Issuing an order can close the lead and
// lock intake, so intake reloads whenever an order is issued.
// onChanged tells the page hosting this workspace that the lead changed, so what it
// shows outside (the lead's header, its stage track, lists and counts) is refreshed.
// Both panels report their saves; they were once lost here, so a work order issued
// on the lead page left its header and stage track stale (review BF5).
export function LeadWorkspace({api, leadId, onChanged}) {
  const [version, setVersion] = useState(0);
  return <>
    <IntakeLead key={`${leadId}-${version}`} api={api} leadId={leadId} onChange={onChanged}/>
    <WorkOrders api={api} leadId={leadId} onChange={() => {setVersion(v => v + 1); onChanged?.();}}/>
  </>;
}
