export interface DomainNavLink {
  to: string
  label: string
}

export interface DomainConfig {
  brand: string
  links: DomainNavLink[]
  theme?: 'dark'
  /** 'panel' = docked Cmd-K assistant (NavBar shows the launcher). 'inline' = bespoke in-page chat. */
  assistant: 'panel' | 'inline'
  /** Fills the viewport below the nav, no footer, no page scroll - for app-like single-screen domains. */
  fullHeight?: boolean
  /** Commerce fields - omitted for domains with no cart (e.g. Vendor). */
  commerce?: {
    shopTo: string
    cartTo: string
    checkoutTo: string
    orderPrefix: string
    checkoutNote: string
    successNote: string
  }
}

export const DOMAINS: Record<string, DomainConfig> = {
  brewcraft: {
    brand: 'BrewCraft',
    links: [
      { to: '/brewcraft', label: 'Home' },
      { to: '/brewcraft/shop', label: 'Shop' },
      { to: '/brewcraft/docs', label: 'Guides' },
    ],
    assistant: 'panel',
    commerce: {
      shopTo: '/brewcraft/shop',
      cartTo: '/brewcraft/cart',
      checkoutTo: '/brewcraft/checkout',
      orderPrefix: 'BC',
      checkoutNote: 'free shipping over $75 · 30-day returns',
      successNote: 'Thanks - your mock order is confirmed.',
    },
  },
  emporium: {
    brand: 'Emporium',
    links: [
      { to: '/emporium', label: 'Shop' },
      { to: '/emporium/news', label: 'News' },
    ],
    theme: 'dark',
    assistant: 'panel',
    commerce: {
      shopTo: '/emporium',
      cartTo: '/emporium/cart',
      checkoutTo: '/emporium/checkout',
      orderPrefix: 'EMP',
      checkoutNote: 'no returns · no refunds · no regrets',
      successNote: 'Thanks - your mock order is confirmed. Do not question it further.',
    },
  },
  vendor: {
    brand: 'The Vendor',
    links: [{ to: '/vendor', label: 'Counter' }],
    assistant: 'inline',
    fullHeight: true,
  },
}
