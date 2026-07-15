import { getApiBaseUrl } from '../runtimeConfig';

describe('server runtime API configuration', () => {
  const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;
  const originalInternalApiUrl = process.env.INTERNAL_API_BASE_URL;
  const originalWindow = Object.getOwnPropertyDescriptor(globalThis, 'window');

  beforeEach(() => {
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: undefined,
    });
  });

  afterEach(() => {
    if (originalApiUrl === undefined) delete process.env.NEXT_PUBLIC_API_URL;
    else process.env.NEXT_PUBLIC_API_URL = originalApiUrl;

    if (originalInternalApiUrl === undefined) delete process.env.INTERNAL_API_BASE_URL;
    else process.env.INTERNAL_API_BASE_URL = originalInternalApiUrl;

    if (originalWindow) Object.defineProperty(globalThis, 'window', originalWindow);
  });

  it('uses the internal service URL during server-side requests', () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8001';
    process.env.INTERNAL_API_BASE_URL = 'http://backend:8000';

    expect(getApiBaseUrl()).toBe('http://backend:8000');
  });
});
