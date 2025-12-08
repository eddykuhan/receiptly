import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR'
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  context?: any;
  userId?: string;
  sessionId?: string;
  userAgent?: string;
  url?: string;
}

@Injectable({
  providedIn: 'root'
})
export class CloudWatchLoggerService {
  private readonly LOG_GROUP = 'receiptly-frontend';
  private readonly LOG_STREAM = `frontend-${environment.production ? 'prod' : 'dev'}`;
  private readonly BATCH_SIZE = 10;
  private readonly FLUSH_INTERVAL = 5000; // 5 seconds

  private logBuffer: LogEntry[] = [];
  private sessionId: string;
  private flushTimer: any;
  private isEnabled = environment.enableCloudWatchLogging === true;

  constructor(private http: HttpClient) {
    this.sessionId = this.generateSessionId();

    if (this.isEnabled) {
      this.startAutoFlush();
      this.setupBeforeUnloadHandler();
    }
  }

  /**
   * Log debug message
   */
  debug(message: string, context?: any): void {
    this.log(LogLevel.DEBUG, message, context);
  }

  /**
   * Log info message
   */
  info(message: string, context?: any): void {
    this.log(LogLevel.INFO, message, context);
  }

  /**
   * Log warning message
   */
  warn(message: string, context?: any): void {
    this.log(LogLevel.WARN, message, context);
  }

  /**
   * Log error message
   */
  error(message: string, context?: any): void {
    this.log(LogLevel.ERROR, message, context);
  }

  /**
   * Log an error object
   */
  logError(error: Error, additionalContext?: any): void {
    this.error(error.message, {
      name: error.name,
      stack: error.stack,
      ...additionalContext
    });
  }

  /**
   * Core logging method
   */
  private log(level: LogLevel, message: string, context?: any): void {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      context,
      sessionId: this.sessionId,
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    // Always log to console in development
    if (!environment.production) {
      this.logToConsole(entry);
    }

    // Buffer for CloudWatch only if enabled
    if (this.isEnabled) {
      this.logBuffer.push(entry);

      // Flush immediately for errors, or when buffer is full
      if (level === LogLevel.ERROR || this.logBuffer.length >= this.BATCH_SIZE) {
        this.flush();
      }
    }
  }

  /**
   * Log to browser console
   */
  private logToConsole(entry: LogEntry): void {
    const prefix = `[${entry.level}] ${entry.timestamp}:`;
    const message = entry.message;
    const data = entry.context ? [message, entry.context] : [message];

    switch (entry.level) {
      case LogLevel.ERROR:
        console.error(prefix, ...data);
        break;
      case LogLevel.WARN:
        console.warn(prefix, ...data);
        break;
      case LogLevel.INFO:
        console.info(prefix, ...data);
        break;
      case LogLevel.DEBUG:
        console.debug(prefix, ...data);
        break;
    }
  }

  /**
   * Flush logs to CloudWatch
   */
  private flush(): void {
    if (this.logBuffer.length === 0) return;

    const logs = [...this.logBuffer];
    this.logBuffer = [];

    // Send to backend API which will forward to CloudWatch
    this.http.post(`${environment.apiUrl}/logs/frontend`, {
      logGroup: this.LOG_GROUP,
      logStream: this.LOG_STREAM,
      logs
    }).subscribe({
      error: (err) => {
        console.error('Failed to send logs to CloudWatch:', err);
        // In case of error, we could implement retry logic or store in localStorage
      }
    });
  }

  /**
   * Start automatic flushing
   */
  private startAutoFlush(): void {
    this.flushTimer = setInterval(() => {
      this.flush();
    }, this.FLUSH_INTERVAL);
  }

  /**
   * Setup handler to flush logs before page unload
   */
  private setupBeforeUnloadHandler(): void {
    window.addEventListener('beforeunload', () => {
      this.flush();
    });
  }

  /**
   * Generate unique session ID
   */
  private generateSessionId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Set user ID for logging context
   */
  setUserId(userId: string): void {
    this.logBuffer.forEach(entry => entry.userId = userId);
  }

  /**
   * Manually flush all buffered logs
   */
  forceFlush(): void {
    this.flush();
  }

  /**
   * Cleanup
   */
  ngOnDestroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }
    this.flush();
  }
}
