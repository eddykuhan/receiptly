import { Injectable, signal } from '@angular/core';

export interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  toasts = signal<Toast[]>([]);
  private nextId = 0;
  private readonly MAX_MESSAGE_LENGTH = 100;

  /**
   * Calculate duration based on message length
   * Short messages (< 30 chars): 3s
   * Medium messages (30-60 chars): 4s
   * Long messages (> 60 chars): 5s
   */
  private calculateDuration(message: string, baseMin: number, baseMax: number): number {
    const length = message.length;
    if (length < 30) return baseMin;
    if (length < 60) return Math.floor((baseMin + baseMax) / 2);
    return baseMax;
  }

  /**
   * Truncate message if too long
   */
  private truncateMessage(message: string): string {
    if (message.length <= this.MAX_MESSAGE_LENGTH) {
      return message;
    }
    return message.substring(0, this.MAX_MESSAGE_LENGTH - 3) + '...';
  }

  show(message: string, type: Toast['type'] = 'info', duration?: number): void {
    const truncatedMessage = this.truncateMessage(message);
    const calculatedDuration = duration ?? this.calculateDuration(truncatedMessage, 3000, 5000);
    
    const toast: Toast = {
      id: this.nextId++,
      message: truncatedMessage,
      type,
      duration: calculatedDuration
    };

    this.toasts.update(toasts => [...toasts, toast]);

    if (calculatedDuration > 0) {
      setTimeout(() => this.remove(toast.id), calculatedDuration);
    }
  }

  success(message: string, duration?: number): void {
    this.show(message, 'success', duration ?? this.calculateDuration(message, 3000, 4000));
  }

  error(message: string, duration?: number): void {
    this.show(message, 'error', duration ?? this.calculateDuration(message, 4000, 6000));
  }

  warning(message: string, duration?: number): void {
    this.show(message, 'warning', duration ?? this.calculateDuration(message, 3500, 5000));
  }

  info(message: string, duration?: number): void {
    this.show(message, 'info', duration ?? this.calculateDuration(message, 3000, 4000));
  }

  remove(id: number): void {
    this.toasts.update(toasts => toasts.filter(t => t.id !== id));
  }

  clear(): void {
    this.toasts.set([]);
  }
}
