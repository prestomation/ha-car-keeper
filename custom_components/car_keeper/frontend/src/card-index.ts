// The entry point of `car-keeper-card.js`, the Lovelace resource of the cards.
import { CAR_CARD_TAG, CarKeeperCarCard, CarKeeperGarageCard, GARAGE_CARD_TAG } from './card';
import { t } from './i18n';

if (!customElements.get(GARAGE_CARD_TAG)) customElements.define(GARAGE_CARD_TAG, CarKeeperGarageCard);
if (!customElements.get(CAR_CARD_TAG)) customElements.define(CAR_CARD_TAG, CarKeeperCarCard);

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
for (const [type, name, description] of [
  [GARAGE_CARD_TAG, t('card.garage_name'), t('card.garage_description')],
  [CAR_CARD_TAG, t('card.car_name'), t('card.car_description')],
]) {
  if (!w.customCards.some((c) => c.type === type)) {
    w.customCards.push({
      type,
      name,
      description,
      preview: true,
      documentationURL: 'https://prestomation.github.io/ha-car-keeper/docs/guide/cards',
    });
  }
}

export { CarKeeperCarCard, CarKeeperGarageCard };
