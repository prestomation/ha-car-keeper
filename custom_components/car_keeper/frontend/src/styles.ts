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
    display: block;
    color: var(--ck-text);
    font-family: var(--ha-font-family-body, Roboto, sans-serif);
  }
`;

export const TAB_STYLES = `${TOKENS}
  .ck-page { padding: 16px; max-width: 1100px; margin: 0 auto; }
  .ck-empty { padding: 48px 16px; text-align: center; color: var(--ck-muted); }
  .ck-empty h2 { color: var(--ck-text); margin: 0 0 8px; font-size: 20px; }
  @media (max-width: 699px) { .ck-page { padding: 8px; } }
`;

export const CARD_STYLES = `${TOKENS}
  ha-card { padding: 16px; }
  .ck-title { font-size: 18px; margin: 0 0 8px; }
  .ck-empty { color: var(--ck-muted); }
`;
