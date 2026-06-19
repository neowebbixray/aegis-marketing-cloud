'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/auth-store';
import type { Notification, NotificationType } from '@/types';

// ─── Constants ─────────────────────────────────────────────

const DEFAULT_WS_URL = 'ws://localhost:8000/ws/notifications';
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30_000;
const HEARTBEAT_INTERVAL_MS = 30_000;
const HEARTBEAT_TIMEOUT_MS = 10_000;

// ─── Incoming WebSocket message shapes ─────────────────────

interface WsNotificationMessage {
  type: 'notification';
  notification: Notification;
}

interface WsPongMessage {
  type: 'pong';
}

interface WsUnreadCountMessage {
  type: 'unread_count';
  count: number;
}

interface WsNotificationsListMessage {
  type: 'notifications';
  notifications: Notification[];
}

type WsIncomingMessage =
  | WsNotificationMessage
  | WsPongMessage
  | WsUnreadCountMessage
  | WsNotificationsListMessage
  | Record<string, unknown>;

// ─── Toast helper ──────────────────────────────────────────

function showNotificationToast(notification: Notification) {
  const variant: Record<NotificationType, typeof toast.info> = {
    info: toast.info,
    success: toast.success,
    warning: toast.warning,
    error: toast.error,
  };

  const show = variant[notification.type] ?? toast.info;

  show(notification.title, {
    description: notification.message,
    duration: 5000,
    closeButton: true,
  });
}

// ─── Hook ──────────────────────────────────────────────────

export interface UseNotificationsReturn {
  /** All notifications received during this session (newest first). */
  notifications: Notification[];
  /** Count of unread notifications. */
  unreadCount: number;
  /** Whether the WebSocket is currently connected. */
  isConnected: boolean;
  /** Open (or reopen) the WebSocket connection. */
  connect: () => void;
  /** Close the WebSocket connection. */
  disconnect: () => void;
  /** Mark a single notification as read (optimistic + API call). */
  markRead: (id: string) => Promise<void>;
  /** Mark all notifications as read. */
  markAllRead: () => Promise<void>;
}

export function useNotifications(): UseNotificationsReturn {
  // ── Refs (stable references, never trigger re-renders) ───
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const heartbeatTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const manualDisconnectRef = useRef(false);

  // ── State ────────────────────────────────────────────────
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  // ── Derive WS URL from auth store ────────────────────────
  const getWsUrl = useCallback((): string => {
    const token = useAuthStore.getState().token;
    const baseUrl =
      typeof window !== 'undefined'
        ? window.__NEXT_DATA__?.props?.pageProps?.WS_URL ??
          process.env.NEXT_PUBLIC_WS_URL ??
          DEFAULT_WS_URL
        : DEFAULT_WS_URL;

    const url = new URL(baseUrl);
    if (token) {
      url.searchParams.set('token', token);
    }
    return url.toString();
  }, []);

  // ── Schedule reconnect ───────────────────────────────────
  const scheduleReconnect = useCallback(() => {
    if (manualDisconnectRef.current) return;

    const attempt = reconnectAttemptRef.current;
    const delay = Math.min(
      RECONNECT_BASE_MS * 2 ** attempt,
      RECONNECT_MAX_MS,
    );
    reconnectAttemptRef.current = attempt + 1;

    reconnectTimerRef.current = setTimeout(() => {
      connectWs();
    }, delay);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Heartbeat management ─────────────────────────────────
  const clearHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(
    (ws: WebSocket) => {
      clearHeartbeat();

      heartbeatTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }

        // If we don't get a pong within the timeout, consider dead
        heartbeatTimeoutRef.current = setTimeout(() => {
          ws.close();
        }, HEARTBEAT_TIMEOUT_MS);
      }, HEARTBEAT_INTERVAL_MS);
    },
    [clearHeartbeat],
  );

  // ── Core WebSocket connection logic ──────────────────────
  const connectWs = useCallback(() => {
    if (manualDisconnectRef.current) return;

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      const url = getWsUrl();
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptRef.current = 0;
        setIsConnected(true);
        startHeartbeat(ws);
      };

      ws.onmessage = (event: MessageEvent) => {
        let data: WsIncomingMessage;
        try {
          data = JSON.parse(event.data) as WsIncomingMessage;
        } catch {
          // Ignore malformed messages
          return;
        }

        // Pong — reset heartbeat timeout
        if (data.type === 'pong') {
          if (heartbeatTimeoutRef.current) {
            clearTimeout(heartbeatTimeoutRef.current);
            heartbeatTimeoutRef.current = null;
          }
          return;
        }

        // Single notification
        if (data.type === 'notification') {
          const notif = data.notification as Notification;
          setNotifications((prev) => [notif, ...prev]);
          if (!notif.read) {
            setUnreadCount((prev) => prev + 1);
          }
          showNotificationToast(notif);
          return;
        }

        // Unread count sync
        if (data.type === 'unread_count' && typeof data.count === 'number') {
          setUnreadCount(data.count);
          return;
        }

        // Full notification list (e.g. on connect)
        if (data.type === 'notifications' && Array.isArray(data.notifications)) {
          const notifs = data.notifications as Notification[];
          setNotifications(notifs);
          setUnreadCount(notifs.filter((n) => !n.read).length);
          return;
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        clearHeartbeat();
        scheduleReconnect();
      };

      ws.onerror = () => {
        // onclose will fire after onerror, handling cleanup + reconnect
        ws.close();
      };
    } catch {
      // WebSocket constructor threw (e.g. bad URL)
      scheduleReconnect();
    }
  }, [getWsUrl, startHeartbeat, clearHeartbeat, scheduleReconnect]);

  // ── Public API ───────────────────────────────────────────

  const connect = useCallback(() => {
    manualDisconnectRef.current = false;
    reconnectAttemptRef.current = 0;
    connectWs();
  }, [connectWs]);

  const disconnect = useCallback(() => {
    manualDisconnectRef.current = true;

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    clearHeartbeat();

    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, [clearHeartbeat]);

  const markRead = useCallback(async (id: string) => {
    // Optimistic update
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));

    try {
      // Fallback to REST API if WS doesn't handle ack
      const { useAuthStore: auth } = await import('@/stores/auth-store');
      const token = auth.getState().token;
      await fetch(`/api/v1/notifications/${id}/read`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
    } catch {
      // Revert on failure
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: false } : n)),
      );
      setUnreadCount((prev) => prev + 1);
    }
  }, []);

  const markAllRead = useCallback(async () => {
    // Optimistic update
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    setUnreadCount(0);

    try {
      const { useAuthStore: auth } = await import('@/stores/auth-store');
      const token = auth.getState().token;
      await fetch('/api/v1/notifications/read-all', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
    } catch {
      // Revert on failure
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, read: false })),
      );
      setUnreadCount((prev) => prev + 1);
    }
  }, []);

  // ── Cleanup on unmount ───────────────────────────────────
  useEffect(() => {
    return () => {
      manualDisconnectRef.current = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      clearHeartbeat();
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [clearHeartbeat]);

  return {
    notifications,
    unreadCount,
    isConnected,
    connect,
    disconnect,
    markRead,
    markAllRead,
  };
}
