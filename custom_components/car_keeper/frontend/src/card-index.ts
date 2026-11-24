// The entry point of `car-keeper-card.js`, the Lovelace resource of the cards.
import { CarKeeperGarageCard, GARAGE_CARD_TAG } from './card';
import { t } from './i18n';

if (!customElements.get(GARAGE_CARD_TAG)) customElements.define(GARAGE_CARD_TAG, CarKeeperGarageCard);

interface CustomCard {
  type: string;
  name: string;
  description: string;
  preview?: boolean;
  documentationURL?: string;
}

// Add the cards to the dashboard card picker.
const w = window as unknown as { customCards?: CustomCard[] };
w.customCards = w.customCards || [];
if (!w.customCards.some((c) => c.type === GARAGE_CARD_TAG)) {
  w.customCards.push({
    type: GARAGE_CARD_TAG,
    name: t('card.garage_name'),
    description: t('card.garage_description'),
    preview: true,
    documentationURL: 'https://github.com/prestomation/ha-car-keeper',
  });
}

export { CarKeeperGarageCard };
