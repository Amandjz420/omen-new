import {PageHeader} from '../components/PageHeader.jsx';
import {api} from '../lib/api.js';

/** Hosts a screen from the previous interface inside the new shell, unchanged, with
 * its styles confined to it, until that screen is rebuilt on the new foundations. */
export function LegacyScreen({title, description, component: Screen, ...props}) {
  return <>
    <PageHeader title={title} description={description}/>
    <div className="legacy-screen"><Screen api={api} {...props}/></div>
  </>;
}
