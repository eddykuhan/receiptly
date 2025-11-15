# PWA Testing Guide - Receiptly

## 🚀 Server Running
✅ Production build server: **http://localhost:8080**
`npx ng build && npx http-server dist/angular-app/browser -p 8080`
✅ Service Worker: Enabled
✅ Theme Color: #6366f1 (Indigo)

---

## 📱 Test 1: Chrome Desktop (Installability)

### Steps:
1. Open **Chrome** browser
2. Navigate to: `http://localhost:8080`
3. Look for **Install** icon in address bar (⊕ or computer icon)
4. Check **Developer Tools**:
   - Press `F12`
   - Go to **Application** tab
   - Click **Manifest** → Verify all details:
     - Name: "Receiptly - Smart Receipt Scanner"
     - Short Name: "Receiptly"
     - Theme Color: #6366f1
     - Start URL: ./
     - Display: standalone
     - Icons: 8 icons (72x72 to 512x512)
   - Click **Service Workers** → Should see "ngsw-worker.js" registered

### Expected Results:
✅ Manifest loads without errors
✅ Service worker registers successfully
✅ Install prompt banner appears at bottom
✅ Clicking "Install" button adds app to desktop

---

## 📱 Test 2: Chrome Android (Full PWA Experience)

### Steps:
1. Access on Android device: `http://192.168.100.240:8080`
   - (Make sure your phone is on same WiFi network)
2. Look for **install banner** at bottom of screen
3. Tap **"Install"** button
4. App installs to home screen
5. Open from home screen → Should open full-screen (no browser UI)

### Expected Results:
✅ Banner appears: "Install Receiptly - Install our app for a better experience"
✅ Tapping "Install" shows native install dialog
✅ App appears on home screen with indigo icon
✅ Opens in standalone mode (no address bar)
✅ Theme color #6366f1 shows in status bar

---

## 📱 Test 3: iOS Safari (Add to Home Screen)

### Steps:
1. Access on iPhone: `http://192.168.100.240:8080`
   - (Make sure your iPhone is on same WiFi network)
2. Look for **iOS install banner** at bottom
3. Banner should say: "Add to Home Screen - Tap the Share button, then tap 'Add to Home Screen'"
4. Follow iOS instructions:
   - Tap **Share** button (square with arrow)
   - Scroll down and tap **"Add to Home Screen"**
   - Verify app name: "Receiptly"
   - Tap **"Add"**
5. Open from home screen

### Expected Results:
✅ Custom iOS instructions appear in banner
✅ Share sheet shows proper app name and icon
✅ App installs to home screen
✅ Opens full-screen (no Safari UI)
✅ Status bar uses theme color

---

## 🔌 Test 4: Offline Functionality

### Steps:
1. With app **installed** (from Test 2 or 3)
2. Open **Developer Tools** → **Application** → **Service Workers**
3. Check **"Offline"** checkbox
4. Reload the page
5. Navigate between pages (Dashboard, History, Camera)

### Expected Results:
✅ App loads completely offline
✅ App shell (HTML, CSS, JS) loads from cache
✅ Navigation works between all pages
✅ Previously loaded receipt data shows
✅ No network errors in console

---

## 📦 Test 5: Caching Strategy

### Check API Caching:
1. Open **Developer Tools** → **Application** → **Cache Storage**
2. Verify these caches exist:
   - `ngsw:/:db:control`
   - `ngsw:/:....:assets:...:cache`
   - `ngsw:/:....:data:dynamic:...:cache`

### Test API Cache:
1. Load receipts (requires backend running)
2. Go offline
3. Navigate to History page
4. Should see cached receipts (up to 1 hour old)

### Test Image Cache:
1. View receipt images
2. Go offline
3. Images should load from cache (up to 7 days)

### Expected Results:
✅ App shell cached (prefetch strategy)
✅ Assets cached lazily
✅ API responses cached (freshness - 1h)
✅ S3 images cached (performance - 7d)

---

## 🎨 Test 6: Install Prompt Dismissal

### Steps:
1. Visit app without installing
2. Install banner appears
3. Click **"Not now"** button
4. Reload page
5. Wait 7 days (or clear localStorage to test immediately)

### Expected Results:
✅ Banner dismisses smoothly
✅ Dismissal saved to localStorage
✅ Banner doesn't appear again for 7 days
✅ Clearing localStorage brings banner back

---

## 🔍 Test 7: Lighthouse PWA Audit

### Steps:
1. Open **Chrome DevTools** (`F12`)
2. Go to **Lighthouse** tab
3. Select:
   - ✅ Progressive Web App
   - ✅ Performance
   - Device: Mobile
4. Click **"Analyze page load"**

### Expected Results:
✅ PWA Score: 90+ (out of 100)
✅ All PWA checks pass:
   - ✅ Installable
   - ✅ Service worker registered
   - ✅ Responds with 200 when offline
   - ✅ Uses HTTPS (or localhost)
   - ✅ Configured for custom splash screen
   - ✅ Sets theme color
   - ✅ Content sized correctly for viewport

---

## 🧪 Test 8: Service Worker Update

### Steps:
1. With app installed and open
2. Make a small code change
3. Run `npm run build` again
4. Service worker detects update
5. Reload triggers update

### Expected Results:
✅ New service worker installs in background
✅ Old version serves until reload
✅ After reload, new version active
✅ No data loss during update

---

## 📊 Test 9: Screenshots & App Info

### Desktop Chrome:
1. Right-click app → **"Install Receiptly"**
2. In install dialog, check:
   - App name
   - Screenshots (if available)
   - Description

### Android Chrome:
1. Tap install banner
2. Native install sheet shows:
   - App name: "Receiptly - Smart Receipt Scanner"
   - Publisher: Your domain
   - Size: ~500KB
   - Screenshots: Dashboard, Camera, History

---

## 🎯 Test 10: Cross-Browser Compatibility

### Browsers to Test:
- ✅ Chrome (Desktop & Android) - Full PWA support
- ✅ Safari (iOS) - Add to Home Screen
- ✅ Edge (Desktop) - Full PWA support
- ✅ Firefox (Desktop) - Limited PWA support
- ❌ Safari (macOS) - No PWA install

---

## 🛠️ Troubleshooting

### Install button doesn't appear:
- Service worker must be registered
- Manifest must be valid
- Must be HTTPS or localhost
- All icons must load successfully

### Service worker not registering:
- Check console for errors
- Verify `ngsw-config.json` syntax
- Clear cache and hard reload (`Cmd+Shift+R`)
- Check Network tab for 404s

### Offline doesn't work:
- Service worker must be active
- At least one online visit required to cache
- Check cache storage for assets
- Verify cache strategies in config

### iOS doesn't show banner:
- iOS doesn't support native install prompts
- Our custom banner provides manual instructions
- Users must use Share → Add to Home Screen

---

## ✅ Quick Verification Checklist

### Before Testing:
- [x] Production build completed
- [x] Service worker files generated
- [x] Server running on port 8080
- [x] Manifest.webmanifest configured
- [x] All icons present (8 sizes)
- [x] Theme color set (#6366f1)

### During Testing:
- [ ] Install banner appears
- [ ] App installs successfully
- [ ] Opens in standalone mode
- [ ] Service worker registers
- [ ] Works offline
- [ ] Caching strategies work
- [ ] Updates properly
- [ ] Lighthouse PWA score 90+

---

## 📱 Current Server Status

**Production Server:** http://localhost:8080
**Network Access:** http://192.168.100.240:8080

**Service Worker:** ✅ Active
**Manifest:** ✅ Configured
**Icons:** ✅ 8 sizes available
**Caching:** ✅ App shell + API + Images

---

## 🎉 Success Criteria

A fully working PWA should:
1. ✅ Install on Chrome/Edge (desktop & Android)
2. ✅ Add to home screen on iOS
3. ✅ Open in standalone mode (no browser UI)
4. ✅ Work completely offline
5. ✅ Cache assets and API data
6. ✅ Update seamlessly
7. ✅ Show install prompt
8. ✅ Use theme color throughout
9. ✅ Pass Lighthouse PWA audit
10. ✅ Provide native app-like experience

---

## 📝 Testing Notes

**Start Testing:**
1. Open browser to http://localhost:8080
2. Open DevTools (F12)
3. Go to Application tab
4. Check Manifest and Service Workers
5. Follow test scenarios above

**Stop Server:**
```bash
# Press CTRL+C in terminal to stop http-server
```

**Rebuild if Needed:**
```bash
cd angular-app
npm run build
npx http-server dist/angular-app/browser -p 8080 -c-1
```

---

Good luck testing! 🚀
