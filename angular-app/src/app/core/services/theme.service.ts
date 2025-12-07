import { Injectable, signal, effect } from '@angular/core';

export type Theme = 'light' | 'dark';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly THEME_KEY = 'user-theme-preference';
  private readonly LIGHT_THEME = 'cheapsy';
  private readonly DARK_THEME = 'night';

  // Signal for current theme
  theme = signal<Theme>(this.getInitialTheme());

  constructor() {
    // Effect to apply theme changes to the DOM
    effect(() => {
      this.applyTheme(this.theme());
    });
  }

  /**
   * Get initial theme from localStorage or system preference
   */
  private getInitialTheme(): Theme {
    // Check localStorage first
    const savedTheme = localStorage.getItem(this.THEME_KEY) as Theme;
    if (savedTheme === 'light' || savedTheme === 'dark') {
      return savedTheme;
    }

    // Fall back to system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }

    return 'light';
  }

  /**
   * Apply theme to the document
   */
  private applyTheme(theme: Theme): void {
    const htmlElement = document.documentElement;
    const daisyTheme = theme === 'dark' ? this.DARK_THEME : this.LIGHT_THEME;
    
    htmlElement.setAttribute('data-theme', daisyTheme);
    
    // Save to localStorage
    localStorage.setItem(this.THEME_KEY, theme);
    
    // Update meta theme-color for mobile browsers
    this.updateMetaThemeColor(theme);
  }

  /**
   * Update meta theme-color tag for mobile browsers
   */
  private updateMetaThemeColor(theme: Theme): void {
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      // Use primary color for light theme, dark color for dark theme
      const color = theme === 'dark' ? '#1f2937' : '#7c3aed';
      metaThemeColor.setAttribute('content', color);
    }
  }

  /**
   * Toggle between light and dark themes
   */
  toggleTheme(): void {
    this.theme.update(current => current === 'light' ? 'dark' : 'light');
  }

  /**
   * Set a specific theme
   */
  setTheme(theme: Theme): void {
    this.theme.set(theme);
  }

  /**
   * Get current theme value
   */
  getCurrentTheme(): Theme {
    return this.theme();
  }

  /**
   * Check if dark mode is active
   */
  isDarkMode(): boolean {
    return this.theme() === 'dark';
  }
}
