// Browser features jsdom lacks and Mantine needs.
import {cleanup} from '@testing-library/react';
import {afterEach} from 'vitest';

afterEach(cleanup);
if (!window.matchMedia) {
  window.matchMedia = query => ({matches: false, media: query, onchange: null, addEventListener() {}, removeEventListener() {},
                                 addListener() {}, removeListener() {}, dispatchEvent: () => false});
}
if (!window.ResizeObserver) window.ResizeObserver = class {observe() {} unobserve() {} disconnect() {}};
if (!Element.prototype.scrollIntoView) Element.prototype.scrollIntoView = () => {};
