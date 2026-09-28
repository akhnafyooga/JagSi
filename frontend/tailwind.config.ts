import type { Config } from 'tailwindcss';

// Material Design 3 token palette exported from the Stitch design
// (docs/design/stitch/13184975747163673874).
const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#45608a',
        'on-primary': '#f8f8ff',
        'primary-container': '#b2cdfe',
        'on-primary-container': '#29446d',
        'primary-dim': '#39547d',
        'inverse-primary': '#b2cdfe',

        background: '#f9f9fe',
        'on-background': '#2f323b',

        surface: '#f9f9fe',
        'on-surface': '#2f323b',
        'on-surface-variant': '#5b5f68',
        'surface-container-lowest': '#ffffff',
        'surface-container-low': '#f2f3fb',
        'surface-container': '#ecedf6',
        'surface-container-high': '#e6e8f1',
        'surface-container-highest': '#dfe2ed',
        'surface-variant': '#dfe2ed',
        'surface-dim': '#d7dae4',
        'surface-bright': '#f9f9fe',
        'surface-tint': '#45608a',

        outline: '#777b84',
        'outline-variant': '#aeb2bc',

        secondary: '#565f71',
        'on-secondary': '#f8f8ff',
        'secondary-container': '#dae2f8',
        'on-secondary-container': '#495264',

        tertiary: '#665881',
        'on-tertiary': '#fef7ff',
        'tertiary-container': '#deccfd',
        'on-tertiary-container': '#50426a',

        error: '#a83836',
        'on-error': '#fff7f6',
        'error-container': '#fa746f',
        'on-error-container': '#6e0a12',

        'inverse-surface': '#0c0e12',
        'inverse-on-surface': '#9c9ca2',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
};

export default config;
