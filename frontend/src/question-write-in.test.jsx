import {fireEvent, render, screen} from '@testing-library/react';
import {expect, it, vi} from 'vitest';
import {Question} from './valuations.jsx';

// An option with no label is the slot for a written-in answer. It was shown as a
// radio button with no label, which saved nothing, so "Location of property" and the
// GLR and PMR values could not be answered from the desktop form.
const ONLY_WRITE_IN = {id: 'q1', text: 'Location of property', kind: 'single', options: [{id: 'o0', label: ''}]};
const WITH_OPTIONS = {id: 'q2', text: 'Characteristics of the site', kind: 'single',
  options: [{id: 'o0', label: ''}, {id: 'o1', label: 'Hilly'}, {id: 'o2', label: 'Rocky'}]};

it('a question whose only option is the write-in slot is answered by typing', () => {
  const onChange = vi.fn();
  render(<Question q={ONLY_WRITE_IN} value={{selected: [], custom: ''}} onChange={onChange}/>);
  expect(screen.queryByRole('radio')).toBeNull();                          // no unlabelled radio button
  fireEvent.change(screen.getByLabelText('Your answer'), {target: {value: 'Near Kolar Road'}});
  expect(onChange).toHaveBeenLastCalledWith({selected: [], custom: 'Near Kolar Road'});
});

it('a single choice is an option or written text, never both', () => {
  const onChange = vi.fn();
  const {rerender} = render(<Question q={WITH_OPTIONS} value={{selected: ['o1'], custom: ''}} onChange={onChange}/>);
  expect(screen.getAllByRole('radio')).toHaveLength(2);                   // the blank slot is not offered as a choice
  fireEvent.change(screen.getByLabelText('Or write your own answer'), {target: {value: 'Sloping'}});
  expect(onChange).toHaveBeenLastCalledWith({selected: [], custom: 'Sloping'});
  rerender(<Question q={WITH_OPTIONS} value={{selected: [], custom: 'Sloping'}} onChange={onChange}/>);
  fireEvent.click(screen.getByLabelText('Rocky'));
  expect(onChange).toHaveBeenLastCalledWith({selected: ['o2'], custom: ''});
});

it('a stored written-in answer is shown, also where verifiers read it', () => {
  render(<Question q={WITH_OPTIONS} value={{selected: [], custom: 'Sloping'}} readOnly onChange={() => {}}/>);
  expect(screen.getByLabelText('Or write your own answer').value).toBe('Sloping');
});
