import {screen} from '@testing-library/react';
import {describe, expect, it} from 'vitest';
import {renderApp} from '../test/render.jsx';
import {StageTrack} from './StageTrack.jsx';
import {Money} from './Money.jsx';

describe('StageTrack', () => {
  const stages = [{key: 'a', label: 'Intake', state: 'done'}, {key: 'b', label: 'Valuation', state: 'current', detail: 'Being filled in'},
                  {key: 'c', label: 'Invoice', state: 'waiting', to: '/invoices', count: 1204}];
  it('marks the current stage for assistive technology and numbers the rest', () => {
    renderApp(<StageTrack stages={stages} label="Case stages"/>);
    expect(screen.getByRole('list', {name: 'Case stages'})).toBeTruthy();
    const items = screen.getAllByRole('listitem');
    expect(items[1].getAttribute('aria-current')).toBe('step');
    expect(items[0].getAttribute('aria-current')).toBeNull();
    expect(screen.getByText('Being filled in')).toBeTruthy();
  });
  it('links a stage to its queue and shows its count with Indian grouping', () => {
    renderApp(<StageTrack stages={stages}/>);
    expect(screen.getByRole('link', {name: /Invoice/}).getAttribute('href')).toBe('/invoices');
    expect(screen.getByText('1,204')).toBeTruthy();
  });
});

describe('Money', () => {
  it('shows rupees with fixed-width figures', () => {
    renderApp(<Money value={1180}/>);
    const el = screen.getByText('₹1,180.00');
    expect(el.className).toContain('num');
  });
});
