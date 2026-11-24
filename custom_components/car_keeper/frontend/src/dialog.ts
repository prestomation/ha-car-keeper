// The shared dialogs of the tab. Each delete asks first in `confirmDestructive`:
// there is no undo, so the question comes before the call.
import { t } from './i18n';
import { escapeHTML } from './utils';

export interface ConfirmOptions {
  title: string;
  text: string;
  confirm?: string;
  onConfirm: () => void | Promise<void>;
}

/**
 * Show a modal question in *root*. The confirm button runs `onConfirm` and closes
 * the dialog. Cancel, Escape and a click on the backdrop close it with no call.
 */
export function confirmDestructive(root: ShadowRoot, opts: ConfirmOptions): HTMLElement {
  root.querySelector('.ck-modal[data-confirm]')?.remove();
  const wrap = document.createElement('div');
  wrap.className = 'ck-modal';
  wrap.dataset.confirm = '';
  wrap.innerHTML = `<div class="ck-dialog" role="alertdialog" aria-modal="true"
      aria-labelledby="ck-confirm-title">
    <h3 id="ck-confirm-title">${escapeHTML(opts.title)}</h3>
    <p>${escapeHTML(opts.text)}</p>
    <div class="ck-actions">
      <button class="ck-btn" data-confirm-act="cancel">${escapeHTML(t('action.cancel'))}</button>
      <button class="ck-btn danger" data-confirm-act="ok">${escapeHTML(
        opts.confirm ?? t('action.delete'),
      )}</button>
    </div></div>`;
  const close = (): void => {
    wrap.remove();
    document.removeEventListener('keydown', onKey);
  };
  const onKey = (ev: KeyboardEvent): void => {
    // A tab that the panel removed takes its dialog with it: stop listening.
    if (!wrap.isConnected || ev.key === 'Escape') close();
  };
  wrap.addEventListener('click', (ev) => {
    const target = ev.target as HTMLElement;
    const act = target.closest<HTMLElement>('[data-confirm-act]')?.dataset.confirmAct;
    if (target === wrap || act === 'cancel') close();
    if (act === 'ok') {
      close();
      void opts.onConfirm();
    }
  });
  document.addEventListener('keydown', onKey);
  root.appendChild(wrap);
  wrap.querySelector<HTMLElement>('[data-confirm-act="cancel"]')?.focus();
  return wrap;
}
