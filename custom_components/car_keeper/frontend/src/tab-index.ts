// The entry point of `cars-tab.js`, the ES module that the Home Keeper panel
// imports for the Cars tab.
import { HomeKeeperCarsTab } from './tab';

export const TAB_TAG = 'home-keeper-cars-tab';

if (!customElements.get(TAB_TAG)) {
  customElements.define(TAB_TAG, HomeKeeperCarsTab);
}

export { HomeKeeperCarsTab };
