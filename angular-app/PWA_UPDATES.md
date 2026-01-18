# PWA Update Management

## Overview

The Angular app now automatically checks for and applies updates without requiring users to manually close and reopen the app.

## How It Works

### Automatic Update Checks
- **On Startup**: Checks for updates when the app becomes stable (after initial load)
- **Periodic**: Checks every 6 hours while the app is running
- **User Triggered**: Can manually check via the update service

### Update Flow
1. Service worker detects a new version is available
2. User sees a toast notification: "New version available! Tap to update."
3. User taps "Update" button (or it auto-reloads if configured)
4. App activates the update and reloads the page
5. User sees the new version immediately

## Configuration Options

### Option 1: User Prompt (Current Default)
Shows a toast notification with an "Update" button. User controls when to apply the update.

```typescript
// In pwa-update.service.ts - promptUserToUpdate()
this.toastService.info(
  'New version available! Tap to update.',
  { 
    duration: 0, // Don't auto-hide
    action: {
      label: 'Update',
      handler: () => this.activateUpdate()
    }
  }
);
```

### Option 2: Automatic Reload
Automatically reloads when an update is detected. No user interaction needed.

```typescript
// In pwa-update.service.ts - promptUserToUpdate()
// Uncomment this line:
this.activateUpdate();
```

### Option 3: Native Confirm Dialog
Uses a simple browser confirm dialog (fallback option).

```typescript
// In pwa-update.service.ts - promptUserToUpdate()
if (confirm('New version available! Load new version?')) {
  this.activateUpdate();
}
```

## Update Check Frequency

Change the check interval in [pwa-update.service.ts](../src/app/core/services/pwa-update.service.ts):

```typescript
// Check every 6 hours (default)
const everySixHours$ = interval(6 * 60 * 60 * 1000);

// Or customize:
const everyHour$ = interval(60 * 60 * 1000);        // 1 hour
const everyTwelveHours$ = interval(12 * 60 * 60 * 1000);  // 12 hours
```

## Manual Update Check

Add a "Check for Updates" button in your settings/profile page:

```typescript
import { PwaUpdateService } from './core/services/pwa-update.service';

export class SettingsComponent {
  private updateService = inject(PwaUpdateService);

  checkForUpdates(): void {
    this.updateService.checkNow();
  }
}
```

```html
<button (click)="checkForUpdates()">
  Check for Updates
</button>
```

## Service Worker Registration Strategy

Currently set to register 30 seconds after the app becomes stable:

```typescript
// In app.config.ts
provideServiceWorker('ngsw-worker.js', {
  enabled: !isDevMode(),
  registrationStrategy: 'registerWhenStable:30000'
})
```

### Other strategies:
- `registerImmediately`: Registers as soon as possible
- `registerWithDelay:5000`: Registers after 5 seconds
- `registerWhenStable`: Registers when app is stable (no delay)

## Testing Updates Locally

1. **Build the production app:**
   ```bash
   npm run build
   ```

2. **Serve with http-server:**
   ```bash
   npx http-server -p 4200 -c-1 dist/angular-app/browser
   ```

3. **Open in browser:** http://localhost:4200

4. **Make a change and rebuild:**
   - Edit any component
   - Run `npm run build` again
   - The running app should detect the update automatically

5. **Verify update notification appears**

## Troubleshooting

### Updates Not Detected
1. Check browser console for service worker logs
2. Verify service worker is registered: DevTools > Application > Service Workers
3. Ensure you're in production mode (not using `ng serve`)
4. Check `ngsw.json` is generated in the build output

### Update Stuck in Waiting State
- The old service worker might be controlling the page
- Force refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
- Or use: DevTools > Application > Service Workers > "Skip waiting"

### Toast Not Showing
- Verify `ToastService` is properly injected
- Check browser console for errors
- Ensure `ToastContainerComponent` is in the app template

## Best Practices

1. **Test Updates in Staging**: Always test the update flow in a staging environment
2. **Clear Communication**: Make update messages clear about what's happening
3. **Don't Force Immediately**: Give users time to finish what they're doing
4. **Handle Errors**: Log and handle update errors gracefully
5. **Monitor**: Track update success rates in production

## Features

✅ Automatic background update checks
✅ User-friendly update notifications
✅ Configurable update strategies
✅ Manual update check capability
✅ Error handling and recovery
✅ Works offline after initial install

## Related Files

- [pwa-update.service.ts](../src/app/core/services/pwa-update.service.ts) - Main update logic
- [toast.service.ts](../src/app/core/services/toast.service.ts) - Notification system
- [toast-container.component.ts](../src/app/shared/components/toast-container/toast-container.component.ts) - Toast UI
- [app.ts](../src/app/app.ts) - Service initialization
- [ngsw-config.json](../ngsw-config.json) - Service worker configuration
