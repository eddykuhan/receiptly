/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('daisyui'),
  ],
  daisyui: {
    themes: [
      {
        cheapsy: {
          "primary": "#7c3aed", // Violet 600
          "primary-content": "#ffffff",
          "secondary": "#d946ef", // Fuchsia 500
          "secondary-content": "#ffffff",
          "accent": "#8b5cf6", // Violet 500
          "accent-content": "#ffffff",
          "neutral": "#1f2937",
          "neutral-content": "#ffffff",
          "base-100": "#ffffff",
          "base-200": "#f3f4f6",
          "base-300": "#e5e7eb",
          "base-content": "#1f2937",
          "info": "#3abff8",
          "success": "#36d399",
          "warning": "#fbbd23",
          "error": "#f87272",
        },
      },
      "night"
    ],
    darkTheme: "night",
  },
  // Light: Emerald, Dark: Night
}
