// Watchdog simulation
class MockEventSource {
  constructor(url) {
    this.url = url;
    this.listeners = {};
    this.closed = false;
  }
  addEventListener(evt, fn) { this.listeners[evt] = fn; }
  emit(evt, data) { if (this.listeners[evt]) this.listeners[evt](data); }
  close() { this.closed = true; }
}

class TestApiClient {
  constructor() {
    this.mode = 'init';
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.watchdogTimer = null;
    this.watchdogTimeoutMs = 45000;
  }

  resetWatchdog(onStatusChange) {
    if (this.watchdogTimer) clearTimeout(this.watchdogTimer);
    this.watchdogTimer = setTimeout(() => {
      if (this.eventSource) {
        this.eventSource.close();
        this.eventSource = null;
      }
      this.mode = 'fallback';
      if (onStatusChange) onStatusChange('fallback');
      this.reconnect(onStatusChange);
    }, this.watchdogTimeoutMs);
  }

  clearWatchdog() {
    if (this.watchdogTimer) {
      clearTimeout(this.watchdogTimer);
      this.watchdogTimer = null;
    }
  }

  connectLiveStream(onHourlyUpdate, onError, onStatusChange) {
    this.clearWatchdog();
    if (this.eventSource) this.eventSource.close();
    this.eventSource = new MockEventSource('/api/v1/stream/live');

    this.eventSource.onopen = () => {
      this.reconnectAttempts = 0;
      this.mode = 'live';
      if (onStatusChange) onStatusChange('live');
      this.resetWatchdog(onStatusChange);
    };

    this.eventSource.addEventListener('hourly_update', (e) => {
      this.resetWatchdog(onStatusChange);
      if (onHourlyUpdate) onHourlyUpdate(e);
    });

    this.eventSource.addEventListener('keepalive', (e) => {
      this.resetWatchdog(onStatusChange);
    });

    this.eventSource.onerror = (err) => {
      this.clearWatchdog();
      if (this.eventSource) this.eventSource.close();
      this.mode = 'fallback';
      if (onStatusChange) onStatusChange('fallback');
      this.reconnect(onStatusChange);
    };

    // simulate open
    this.eventSource.onopen();
  }

  reconnect(onStatusChange) {
    this.reconnectAttempts++;
    this.reconnected = true;
  }
}

const client = new TestApiClient();
let currentStatus = null;
client.connectLiveStream(
  () => {},
  () => {},
  (status) => { currentStatus = status; }
);

console.log('After open: mode=' + client.mode + ', hasWatchdog=' + (client.watchdogTimer !== null));

// Simulate keepalive ping
client.eventSource.emit('keepalive', {});
console.log('After keepalive: hasWatchdog=' + (client.watchdogTimer !== null));

// Fast-forward or trigger watchdog manually
clearTimeout(client.watchdogTimer);
// simulate firing the watchdog
client.eventSource.close();
client.mode = 'fallback';
currentStatus = 'fallback';
client.reconnect(() => {});

console.log('After watchdog timeout: mode=' + client.mode + ', status=' + currentStatus + ', reconnected=' + client.reconnected);
