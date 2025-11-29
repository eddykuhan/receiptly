import { bootstrapApplication } from '@angular/platform-browser';
import { defineCustomElements } from '@ionic/pwa-elements/loader';
import { appConfig } from './app/app.config';
import { App } from './app/app';

// Call the element loader after the platform has been bootstrapped
defineCustomElements(window);

bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));
