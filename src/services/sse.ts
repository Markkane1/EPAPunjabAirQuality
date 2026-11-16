/**
 * EPA Punjab Air Quality Monitoring, Processing, and Visualization System
 * Live Server-Sent Events (SSE) Stream Manager (/api/v1/stream/live)
 *
 * Implements:
 * - Browser EventSource connection to /api/v1/stream/live
 * - 45-second silent TCP drop watchdog timer (reset on hourly_update, keepalive, ping, and generic messages)
 * - Randomized exponential backoff with full jitter:
 *     base = min(30000, 2000 * 1.5^attempts)
 *     delay = base * (0.5 + Math.random() * 0.5)
 * - Max reconnection attempts (5) with fallback state transition
 */

export type StreamMode = 'live' | 'fallback';

export interface SSEUpdatePayload {
  timestamp: string;
  mean_aqi?: number;
  peak_aqi?: number;
  peak_district?: string;
  districts_committed?: number;
  stations_committed?: number;
  readings?: Record<string, number | null>;
  [key: string]: any;
}

export class LiveStreamManager {
  private url: string;
  private eventSource: EventSource | null = null;
  private watchdogTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private watchdogTimeoutMs: number = 45000;
  private reconnectAttempts: number = 0;
  public maxReconnectAttempts: number = 5;
  private isDestroyed: boolean = false;

  private onUpdateCallback?: (data: SSEUpdatePayload) => void;
  private onErrorCallback?: (err: any) => void;
  private onStatusChangeCallback?: (mode: StreamMode) => void;

  constructor(url: string = '/api/v1/stream/live') {
    this.url = url;
    this.maxReconnectAttempts = 5;
  }

  /**
   * Connect to the SSE live stream with callbacks.
   */
  connect(
    onUpdate: (data: SSEUpdatePayload) => void,
    onError?: (err: any) => void,
    onStatusChange?: (mode: StreamMode) => void
  ): void {
    this.isDestroyed = false;
    this.onUpdateCallback = onUpdate;
    this.onErrorCallback = onError;
    this.onStatusChangeCallback = onStatusChange;
    this.initEventSource();
  }

  private initEventSource(): void {
    this.cleanup();
    if (this.isDestroyed) return;

    try {
      this.eventSource = new EventSource(this.url);

      this.eventSource.onopen = () => {
        this.reconnectAttempts = 0;
        this.onStatusChangeCallback?.('live');
        this.resetWatchdog();
      };

      this.eventSource.addEventListener('hourly_update', (event: MessageEvent) => {
        this.resetWatchdog();
        try {
          const payload = JSON.parse(event.data) as SSEUpdatePayload;
          this.onUpdateCallback?.(payload);
        } catch (err) {
          console.error('Failed to parse SSE hourly_update payload:', err);
        }
      });

      this.eventSource.addEventListener('keepalive', () => {
        this.resetWatchdog();
      });

      this.eventSource.addEventListener('ping', () => {
        this.resetWatchdog();
      });

      this.eventSource.onmessage = () => {
        this.resetWatchdog();
      };

      this.eventSource.onerror = (err) => {
        console.warn('SSE connection interrupted, initiating fallback backoff...', err);
        this.clearWatchdog();
        this.closeEventSource();
        this.onStatusChangeCallback?.('fallback');
        this.onErrorCallback?.(err);
        this.scheduleReconnect();
      };
    } catch (err) {
      console.warn('EventSource initialization failed:', err);
      this.onStatusChangeCallback?.('fallback');
      this.scheduleReconnect();
    }
  }

  /**
   * Resets the 45-second silent TCP drop watchdog timer.
   */
  private resetWatchdog(): void {
    this.clearWatchdog();
    this.watchdogTimer = setTimeout(() => {
      console.warn('SSE Watchdog: 45s silence detected. Reconnecting...');
      this.closeEventSource();
      this.onStatusChangeCallback?.('fallback');
      this.scheduleReconnect();
    }, this.watchdogTimeoutMs);
  }

  private clearWatchdog(): void {
    if (this.watchdogTimer) {
      clearTimeout(this.watchdogTimer);
      this.watchdogTimer = null;
    }
  }

  /**
   * Schedules reconnection using randomized exponential backoff with full jitter.
   */
  private scheduleReconnect(): void {
    if (this.isDestroyed) return;
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn(`SSE: Maximum reconnection attempts (${this.maxReconnectAttempts}) reached, remaining in fallback.`);
      this.onStatusChangeCallback?.('fallback');
      return;
    }
    this.reconnectAttempts++;

    // Randomized exponential backoff with full jitter: min(30000, 2000 * 1.5^attempts)
    const attemptExp = Math.min(this.reconnectAttempts, 10);
    const base = Math.min(30000, 2000 * Math.pow(1.5, attemptExp));
    const delay = base * (0.5 + Math.random() * 0.5);

    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.initEventSource();
    }, delay);
  }

  private closeEventSource(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  private cleanup(): void {
    this.clearWatchdog();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.closeEventSource();
  }

  /**
   * Gracefully disconnects and stops all timers.
   */
  disconnect(): void {
    this.isDestroyed = true;
    this.cleanup();
    this.onStatusChangeCallback?.('fallback');
  }

  destroy(): void {
    this.disconnect();
  }

  getMode(): StreamMode {
    return this.eventSource && this.eventSource.readyState === EventSource.OPEN
      ? 'live'
      : 'fallback';
  }

  getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }
}

// Aliases for convenience
export { LiveStreamManager as SSEManager, LiveStreamManager as SSEStreamService };
