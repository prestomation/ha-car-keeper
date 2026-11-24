// The `--ck-*` tokens. Each one reads a Home Assistant theme variable, with a
// literal color only as the fallback.
export const TOKENS = `
  :host {
    --ck-surface: var(--card-background-color, #fff);
    --ck-text: var(--primary-text-color, #1c1b1f);
    --ck-muted: var(--secondary-text-color, #5f6368);
    --ck-primary: var(--primary-color, #03a9f4);
    --ck-divider: var(--divider-color, rgba(0, 0, 0, 0.12));
    --ck-radius: var(--ha-card-border-radius, 12px);
    --ck-ok: var(--success-color, #2e7d32);
    --ck-soon: var(--warning-color, #b26a00);
    --ck-overdue: var(--error-color, #c62828);
    display: block;
    color: var(--ck-text);
    font-family: var(--ha-font-family-body, Roboto, sans-serif);
  }
`;

const SHARED = `
  .ck-muted { color: var(--ck-muted); }
  .ck-chip { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px;
    font-weight: 500; color: #fff; background: var(--ck-ok); white-space: nowrap; }
  .ck-chip.soon { background: var(--ck-soon); }
  .ck-chip.overdue { background: var(--ck-overdue); }
  .ck-btn { font: inherit; padding: 8px 14px; border-radius: 8px; cursor: pointer;
    border: 1px solid var(--ck-divider); background: transparent; color: var(--ck-text);
    text-decoration: none; display: inline-flex; align-items: center; min-height: 36px; }
  .ck-btn.primary { background: var(--ck-primary); border-color: var(--ck-primary);
    color: var(--text-primary-color, #fff); }
  .ck-btn.text { border-color: transparent; color: var(--ck-primary); }
  .ck-btn.danger { color: var(--ck-overdue); }
  .ck-btn.primary.danger, .ck-dialog .ck-btn.danger { background: var(--ck-overdue);
    border-color: var(--ck-overdue); color: #fff; }
  .ck-btn:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--ck-primary);
    outline-offset: 2px; }
  .ck-list { list-style: none; margin: 0; padding: 0; }
  .ck-big { font-size: 28px; font-weight: 500; margin: 4px 0; }
  input, select { font: inherit; color: var(--ck-text); background: var(--ck-surface);
    border: 1px solid var(--ck-divider); border-radius: 8px; padding: 8px; min-width: 0;
    box-sizing: border-box; }
  input[type='checkbox'] { padding: 0; width: 18px; height: 18px; flex: 0 0 auto; margin: 0;
    accent-color: var(--ck-primary); }
  .ck-list { margin-top: 8px; }
`;

export const TAB_STYLES = `${TOKENS}${SHARED}
  .ck-page { padding: 16px; max-width: 1100px; margin: 0 auto; }
  .ck-empty { padding: 48px 16px; text-align: center; color: var(--ck-muted); }
  .ck-empty h2 { color: var(--ck-text); margin: 0 0 8px; font-size: 20px; }
  .ck-head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 8px 0 12px; }
  .ck-head h1 { font-size: 24px; margin: 0; flex: 1 1 auto; min-width: 0; overflow-wrap: anywhere; }
  .ck-head-actions { display: flex; gap: 8px; }
  .ck-sub { margin: -8px 0 12px; }
  .ck-grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
  .ck-car { display: flex; flex-direction: column; gap: 4px; text-align: left; font: inherit;
    color: var(--ck-text); background: var(--ck-surface); border: 1px solid var(--ck-divider);
    border-left: 4px solid var(--ck-ok); border-radius: var(--ck-radius); padding: 14px; cursor: pointer; }
  .ck-car.soon { border-left-color: var(--ck-soon); }
  .ck-car.overdue { border-left-color: var(--ck-overdue); }
  .ck-car-top { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
  .ck-car-name { font-size: 18px; font-weight: 500; overflow-wrap: anywhere; }
  .ck-car-odo { font-size: 20px; }
  .ck-columns { display: grid; gap: 12px; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); }
  .ck-columns > div { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .ck-card { background: var(--ck-surface); border: 1px solid var(--ck-divider);
    border-radius: var(--ck-radius); padding: 16px; min-width: 0; }
  .ck-card h2 { font-size: 18px; margin: 0 0 8px; }
  .ck-card-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .ck-row { display: flex; gap: 8px; align-items: flex-end; flex-wrap: wrap; }
  .ck-row .ck-field { flex: 1 1 180px; }
  .ck-item { border-top: 1px solid var(--ck-divider); padding: 10px 0; display: flex;
    flex-direction: column; gap: 4px; }
  .ck-item.off { opacity: 0.6; }
  .ck-item-main { display: flex; justify-content: space-between; gap: 8px; align-items: center; flex-wrap: wrap; }
  .ck-item-name { font-weight: 500; overflow-wrap: anywhere; }
  .ck-actions { display: flex; gap: 8px; justify-content: flex-end; align-items: center;
    flex-wrap: wrap; margin-top: 8px; }
  .ck-form { display: flex; flex-direction: column; gap: 10px; }
  .ck-field { display: flex; flex-direction: column; gap: 4px; font-size: 14px; }
  .ck-check { display: flex; gap: 8px; align-items: center; padding: 4px 0; }
  .ck-jobs { border: 1px solid var(--ck-divider); border-radius: 8px; padding: 8px 12px; margin: 0; }
  .ck-kv { display: flex; justify-content: space-between; gap: 12px; padding: 4px 0;
    border-top: 1px solid var(--ck-divider); overflow-wrap: anywhere; }
  .ck-note { font-size: 13px; color: var(--ck-muted); margin: 8px 0 0; }
  .ck-error { color: var(--ck-overdue); margin: 8px 0 0; }
  .ck-table-wrap { overflow-x: auto; }
  .ck-table { width: 100%; border-collapse: collapse; }
  .ck-table th, .ck-table td { text-align: left; padding: 6px; border-top: 1px solid var(--ck-divider); }
  .ck-table input[type='number'] { width: 84px; }
  .ck-table td:first-child { width: 100%; }
  .ck-presets { list-style: none; margin: 0; padding: 0; }
  .ck-presets li { display: grid; grid-template-columns: minmax(10rem, 18rem) minmax(0, 1fr);
    gap: 4px 16px; padding: 8px 0; border-top: 1px solid var(--ck-divider); }
  .ck-preset-brand { font-weight: 500; }
  .ck-modal { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.45); display: flex;
    align-items: center; justify-content: center; z-index: 10; padding: 16px; }
  .ck-dialog { background: var(--ck-surface); color: var(--ck-text); border-radius: var(--ck-radius);
    padding: 20px; width: min(480px, 100%); max-height: calc(100vh - 32px); overflow: auto;
    display: flex; flex-direction: column; gap: 10px; box-sizing: border-box; }
  .ck-dialog h3 { margin: 0; font-size: 20px; }
  @media (max-width: 699px) {
    .ck-page { padding: 8px 16px; }
    .ck-columns { grid-template-columns: minmax(0, 1fr); }
    .ck-head h1 { font-size: 20px; }
    .ck-presets li { grid-template-columns: minmax(0, 1fr); }
  }
`;

export const CARD_STYLES = `${TOKENS}${SHARED}
  ha-card { padding: 16px; }
  .ck-title { font-size: 18px; margin: 0 0 8px; }
  .ck-empty { color: var(--ck-muted); }
  .ck-line { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .ck-line input { flex: 1 1 auto; }
  .ck-name { font-weight: 500; overflow-wrap: anywhere; }
  .ck-row-card { border-top: 1px solid var(--ck-divider); padding: 8px 0; display: flex;
    flex-direction: column; gap: 4px; }
  .ck-scroll { overflow-y: auto; }
`;
