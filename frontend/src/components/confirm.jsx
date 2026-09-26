import {Text} from '@mantine/core';
import {modals} from '@mantine/modals';

/** Ask before an action that cannot be undone, stating what will happen.
 * Resolves true when confirmed. Replaces the browser's plain confirm pop-up. */
export function confirmAction({title, consequence, confirmLabel, danger = false}) {
  return new Promise(resolve => {
    modals.openConfirmModal({
      title,
      children: <Text size="sm">{consequence}</Text>,
      labels: {confirm: confirmLabel, cancel: 'Go back'},
      confirmProps: {color: danger ? 'red' : 'omen'},
      onConfirm: () => resolve(true),
      onCancel: () => resolve(false),
      onClose: () => resolve(false),
    });
  });
}
