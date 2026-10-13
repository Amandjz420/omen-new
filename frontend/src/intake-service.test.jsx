import {fireEvent, render, screen} from '@testing-library/react';
import {describe, expect, it, vi} from 'vitest';
import {ServiceForm} from './intake.jsx';

// The subtype list showed only "Select…" because the service it depends on came after it.
const catalog = {
  services: [{id: 'val', name: 'Valuation of asset'}, {id: 'worth', name: 'WORTH ASSESSMENT'}],
  subtypes: [{id: 'lb', name: 'L & B', service_id: 'val'}, {id: 'flat', name: 'Flat', service_id: 'val'}],
};

describe('adding a requested service', () => {
  it('asks for the service first, and says why the subtype is waiting', () => {
    render(<ServiceForm catalog={catalog} save={vi.fn()}/>);
    const [service, subtype] = [screen.getByLabelText('Service'), screen.getByLabelText('Asset subtype')];
    expect(service.compareDocumentPosition(subtype) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();   // service comes first
    expect(subtype.disabled).toBe(true);
    expect(subtype.textContent).toBe('Choose a service first');
  });

  it('lists the chosen service’s subtypes', () => {
    render(<ServiceForm catalog={catalog} save={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Service'), {target: {value: 'val'}});
    const subtype = screen.getByLabelText('Asset subtype');
    expect(subtype.disabled).toBe(false);
    expect([...subtype.options].map(o => o.textContent)).toEqual(['Select…', 'L & B', 'Flat']);
  });

  it('says so when the service has no subtypes', () => {
    render(<ServiceForm catalog={catalog} save={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Service'), {target: {value: 'worth'}});
    expect(screen.getByLabelText('Asset subtype').textContent).toBe('This service has no subtypes');
  });

  it('saves the service and subtype', async () => {
    const save = vi.fn().mockResolvedValue({});
    render(<ServiceForm catalog={catalog} save={save}/>);
    fireEvent.change(screen.getByLabelText('Service'), {target: {value: 'val'}});
    fireEvent.change(screen.getByLabelText('Asset subtype'), {target: {value: 'lb'}});
    fireEvent.click(screen.getByRole('button', {name: 'Save'}));
    await vi.waitFor(() => expect(save).toHaveBeenCalled());
    expect(save.mock.calls[0][0]).toMatchObject({service: 'val', subtype: 'lb'});
  });
});
