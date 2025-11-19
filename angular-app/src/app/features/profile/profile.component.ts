import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface UserProfile {
    id: string;
    name: string;
    email: string;
    avatar?: string;
    phone?: string;
    memberSince: Date;
    authProvider: 'google' | 'apple';
    linkedAccounts: {
        google?: {
            email: string;
            linkedAt: Date;
            isPrimary: boolean;
        };
        apple?: {
            email: string;
            linkedAt: Date;
            isPrimary: boolean;
        };
    };
    stats: {
        totalReceipts: number;
        totalSaved: number;
        uniqueStores: number;
        avgReceiptValue: number;
    };
    preferences: {
        theme: 'light' | 'dark';
        language: string;
        currency: string;
        dateFormat: string;
    };
    notifications: {
        email: boolean;
        priceDrops: boolean;
        weeklySummary: boolean;
        rewards: boolean;
    };
    security: {
        twoFactorEnabled: boolean;
    };
}

@Component({
    selector: 'app-profile',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './profile.component.html',
    styleUrl: './profile.component.scss'
})
export class ProfileComponent {
    // Mock user profile data
    profile = signal<UserProfile>({
        id: 'user-123',
        name: 'John Doe',
        email: 'john.doe@gmail.com',
        avatar: undefined,
        phone: '+60 12-345 6789',
        memberSince: new Date('2024-01-15'),
        authProvider: 'google',
        linkedAccounts: {
            google: {
                email: 'john.doe@gmail.com',
                linkedAt: new Date('2024-01-15'),
                isPrimary: true
            }
        },
        stats: {
            totalReceipts: 125,
            totalSaved: 450.50,
            uniqueStores: 8,
            avgReceiptValue: 35.20
        },
        preferences: {
            theme: 'light',
            language: 'en',
            currency: 'MYR',
            dateFormat: 'DD/MM/YYYY'
        },
        notifications: {
            email: true,
            priceDrops: true,
            weeklySummary: false,
            rewards: true
        },
        security: {
            twoFactorEnabled: false
        }
    });

    editMode = signal(false);
    showSaveMessage = signal(false);

    toggleEditMode() {
        this.editMode.set(!this.editMode());
    }

    saveProfile() {
        // In production, save to backend
        this.editMode.set(false);
        this.showSaveMessage.set(true);
        setTimeout(() => this.showSaveMessage.set(false), 3000);
    }

    toggleTheme() {
        const current = this.profile();
        const newTheme = current.preferences.theme === 'light' ? 'dark' : 'light';
        this.profile.update(p => ({
            ...p,
            preferences: { ...p.preferences, theme: newTheme }
        }));
        // In production, apply theme to document and save to backend
    }

    toggleNotification(key: keyof UserProfile['notifications']) {
        this.profile.update(p => ({
            ...p,
            notifications: { ...p.notifications, [key]: !p.notifications[key] }
        }));
    }

    linkAppleAccount() {
        // In production, initiate Apple Sign-In flow
        alert('Apple Sign-In flow would start here');
    }

    unlinkAccount(provider: 'google' | 'apple') {
        // In production, unlink account via backend
        alert(`Unlink ${provider} account`);
    }

    exportData() {
        // In production, trigger data export
        alert('Data export would start here. You will receive an email with your data.');
    }

    deleteAccount() {
        if (confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
            // In production, delete account via backend
            alert('Account deletion would be processed here');
        }
    }

    onAvatarChange(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.profile.update(p => ({ ...p, avatar: e.target?.result as string }));
            };
            reader.readAsDataURL(input.files[0]);
        }
    }

    getMemberDuration(): string {
        const months = Math.floor(
            (new Date().getTime() - this.profile().memberSince.getTime()) / (1000 * 60 * 60 * 24 * 30)
        );
        if (months < 1) return 'Less than a month';
        if (months === 1) return '1 month';
        if (months < 12) return `${months} months`;
        const years = Math.floor(months / 12);
        return years === 1 ? '1 year' : `${years} years`;
    }
}
