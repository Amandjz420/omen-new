import {fireEvent, screen} from '@testing-library/react';
import {Table} from '@mantine/core';
import {describe, expect, it, vi} from 'vitest';
import {renderApp} from '../test/render.jsx';
import {ResponsiveTable} from './ResponsiveTable.jsx';

describe('ResponsiveTable', () => {
  it('labels cells through conditional header fragments without duplicating action handlers', () => {
    const open = vi.fn();
    const {container} = renderApp(<ResponsiveTable><table>
      <thead><tr><><th>Invoice</th><th>Total</th><th/></></tr></thead>
      <tbody><tr><td>I-001</td><td>1200</td><td><button onClick={open}>Open</button></td></tr></tbody>
    </table></ResponsiveTable>);
    expect([...container.querySelectorAll('td')].map(c => c.dataset.label)).toEqual(['Invoice', 'Total', 'Actions']);
    fireEvent.click(screen.getByRole('button', {name: 'Open'}));
    expect(open).toHaveBeenCalledTimes(1);
  });

  it('preserves Mantine table semantics and changes mobile labels when headers change', () => {
    const {container} = renderApp(<ResponsiveTable><Table>
      <Table.Thead><Table.Tr><Table.Th>Office</Table.Th><Table.Th>Branch</Table.Th></Table.Tr></Table.Thead>
      <Table.Tbody><Table.Tr><Table.Td>Bank</Table.Td><Table.Td>Main</Table.Td></Table.Tr></Table.Tbody>
    </Table></ResponsiveTable>);
    expect(screen.getByRole('table')).toBeTruthy();
    expect([...container.querySelectorAll('td')].map(c => c.dataset.label)).toEqual(['Office', 'Branch']);
    expect(screen.getAllByRole('cell')).toHaveLength(2);
  });
});
