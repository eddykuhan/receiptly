import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { Clerk } from '@clerk/clerk-js';
import { environment } from '../../../environments/environment';

export interface AuthUser {
  id: string;
  email?: string;
  firstName?: string;
  lastName?: string;
  imageUrl?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ClerkAuthService {
  private userSubject = new BehaviorSubject<AuthUser | null>(null);
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(false);
  private sessionTokenSubject = new BehaviorSubject<string | null>(null);
  private clerk: Clerk | null = null;

  public user$: Observable<AuthUser | null> = this.userSubject.asObservable();
  public isAuthenticated$: Observable<boolean> = this.isAuthenticatedSubject.asObservable();
  public sessionToken$: Observable<string | null> = this.sessionTokenSubject.asObservable();

  constructor() {
    this.initializeClerk();
  }

  /**
   * Initialize Clerk instance
   */
  private async initializeClerk(): Promise<void> {
    try {
      const publishableKey = environment.clerkPublishableKey;
      
      if (!publishableKey) {
        console.warn('Clerk publishable key not found in environment');
        return;
      }

      // Initialize Clerk from the npm package
      this.clerk = new Clerk(publishableKey);
      await this.clerk.load();

      console.log('Clerk loaded, user:', this.clerk.user);

      // Set up auth state immediately after load
      this.checkAuthStatus();

      // Listen for auth state changes
      this.clerk.addListener((state: any) => {
        console.log('Clerk state change:', state);
        // Only update auth state if we have both user AND session
        if (state.user && state.session) {
          this.updateUserState(state.user);
          this.getSessionToken();
        } else {
          this.clearAuthState();
        }
      });
    } catch (error) {
      console.error('Error initializing Clerk:', error);
    }
  }

  /**
   * Check current authentication status
   */
  private checkAuthStatus(): void {
    try {
      // Check if there's both a user AND an active session
      if (this.clerk?.user && this.clerk?.session) {
        console.log('User authenticated:', this.clerk.user.id);
        this.updateUserState(this.clerk.user);
        this.getSessionToken();
      } else {
        console.log('Not authenticated, user:', this.clerk?.user, 'session:', this.clerk?.session);
        this.clearAuthState();
      }
    } catch (error) {
      console.error('Error checking auth status:', error);
      this.clearAuthState();
    }
  }

  /**
   * Update user state from Clerk user object
   */
  private updateUserState(clerkUser: any): void {
    const user: AuthUser = {
      id: clerkUser.id,
      email: clerkUser.emailAddresses?.[0]?.emailAddress,
      firstName: clerkUser.firstName || undefined,
      lastName: clerkUser.lastName || undefined,
      imageUrl: clerkUser.imageUrl
    };

    this.userSubject.next(user);
    this.isAuthenticatedSubject.next(true);
  }

  /**
   * Get current session token from Clerk
   */
  private async getSessionToken(): Promise<void> {
    try {
      if (this.clerk?.session) {
        // Use default token instead of custom template
        const token = await this.clerk.session.getToken();
        this.sessionTokenSubject.next(token);
      }
    } catch (error) {
      console.error('Error retrieving session token:', error);
    }
  }

  /**
   * Clear all auth state
   */
  private clearAuthState(): void {
    this.userSubject.next(null);
    this.isAuthenticatedSubject.next(false);
    this.sessionTokenSubject.next(null);
  }

  /**
   * Get current user
   */
  getCurrentUser(): AuthUser | null {
    return this.userSubject.value;
  }

  /**
   * Get authentication status
   */
  isAuthenticated(): boolean {
    return this.isAuthenticatedSubject.value;
  }

  /**
   * Get current session token
   */
  getCurrentToken(): string | null {
    return this.sessionTokenSubject.value;
  }

  /**
   * Get session token observable
   */
  getSessionToken$(): Observable<string | null> {
    return this.sessionTokenSubject.asObservable();
  }

  /**
   * Refresh authentication state
   */
  async refreshAuthState(): Promise<void> {
    this.checkAuthStatus();
    // Give Clerk a moment to update, then get fresh token
    await new Promise(resolve => setTimeout(resolve, 100));
    if (this.clerk?.session) {
      await this.getSessionToken();
    }
  }

  /**
   * Get the Clerk instance (for mounting UI components)
   */
  async getClerk(): Promise<Clerk | null> {
    // Wait for Clerk to be initialized
    let attempts = 0;
    while (!this.clerk && attempts < 100) {
      await new Promise(resolve => setTimeout(resolve, 100));
      attempts++;
    }
    
    if (!this.clerk) {
      return null;
    }

    // Wait for Clerk to be fully loaded (client and session loaded)
    attempts = 0;
    while (this.clerk.client === undefined && attempts < 100) {
      await new Promise(resolve => setTimeout(resolve, 100));
      attempts++;
    }

    return this.clerk;
  }

  /**
   * Sign out user
   */
  async signOut(): Promise<void> {
    try {
      if (this.clerk) {
        await this.clerk.signOut();
        this.clearAuthState();
      }
    } catch (error) {
      console.error('Error signing out:', error);
    }
  }

  /**
   * Sign in with redirect
   */
  async signIn(): Promise<void> {
    try {
      if (this.clerk) {
        await this.clerk.redirectToSignIn();
      }
    } catch (error) {
      console.error('Error signing in:', error);
    }
  }
}
