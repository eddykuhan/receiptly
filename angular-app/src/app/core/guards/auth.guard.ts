import { Injectable } from '@angular/core';
import { Router, CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, UrlTree } from '@angular/router';
import { Observable } from 'rxjs';
import { map, take } from 'rxjs/operators';
import { ClerkAuthService } from '../services/clerk-auth.service';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {
  constructor(
    private authService: ClerkAuthService,
    private router: Router
  ) {}

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return this.authService.isAuthenticated$.pipe(
      take(1),
      map((isAuthenticated) => {
        if (isAuthenticated) {
          return true;
        }

        // Prevent redirect loop - don't redirect if already on auth pages
        const currentPath = state.url;
        if (currentPath.includes('/sign-in') || currentPath.includes('/sign-up')) {
          return false;
        }

        // Store the attempted URL for redirecting after sign in
        console.log('Not authenticated, redirecting to sign-in');
        this.router.navigate(['/sign-in'], { queryParams: { returnUrl: state.url } });
        return false;
      })
    );
  }
}
