import {Children, cloneElement, isValidElement} from 'react';
import './ResponsiveTable.css';

// Keep one set of rows and event handlers. On phones the same cells become
// labeled cards; on larger screens they retain their native table layout.
const mantineTags = {Table: 'table', TableThead: 'thead', TableTbody: 'tbody', TableTfoot: 'tfoot', TableTr: 'tr', TableTh: 'th', TableTd: 'td'};
const tag = node => typeof node.type === 'string' ? node.type : mantineTags[node.type?.displayName?.split('/').pop()];
const text = children => Children.toArray(children).map(c => isValidElement(c) ? text(c.props.children) : String(c)).join(' ').trim();

export function ResponsiveTable({children}) {
  const headings = [];
  function collect(nodes, inHeader = false) {
    Children.forEach(nodes, node => {
      if (!isValidElement(node)) return;
      const kind = tag(node);
      if (kind === 'th' && inHeader) headings.push(text(node.props.children) || 'Actions');
      else collect(node.props.children, inHeader || kind === 'thead');
    });
  }
  collect(children);
  function decorate(nodes, inBody = false) {
    return Children.map(nodes, node => {
      if (!isValidElement(node)) return node;
      const kind = tag(node);
      if (kind === 'tr' && inBody) {
        let column = 0;
        return cloneElement(node, {role: 'row'}, Children.map(node.props.children, cell => {
          if (!isValidElement(cell)) return cell;
          const label = headings[column] || 'Details';
          column += Number(cell.props.colSpan || 1);
          return cloneElement(cell, {role: 'cell', 'data-label': label, 'data-wide': cell.props.colSpan > 1 || undefined},
            <div className="mobile-cell-value">{cell.props.children}</div>);
        }));
      }
      const role = {table: 'table', thead: 'rowgroup', tbody: 'rowgroup', tfoot: 'rowgroup', tr: 'row', th: 'columnheader'}[kind];
      return cloneElement(node, role ? {role} : {}, decorate(node.props.children, inBody || kind === 'tbody'));
    });
  }
  return <div className="responsive-table">{decorate(children)}</div>;
}
