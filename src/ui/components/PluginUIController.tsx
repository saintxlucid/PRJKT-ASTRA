/**
 * Plugin UI controller.
 * Manages plugin dialogs and notifications.
 */
import React, { useState, useCallback, useEffect } from 'react';
import { PermissionRequestDialog } from './PermissionRequestDialog';
import {
  PluginLoadNotification,
  PluginErrorNotification
} from './PluginNotifications';

interface Permission {
  name: string;
  description?: string;
}

interface PermissionRequest {
  pluginId: string;
  pluginName?: string;
  actionName: string;
  actionDescription?: string;
  permissions: Permission[];
}

interface PluginNotification {
  type: 'load' | 'error';
  pluginId: string;
  pluginName?: string;
  error?: string;
  details?: string;
}

export const PluginUIController: React.FC = () => {
  // Permission request state
  const [permissionRequest, setPermissionRequest] = useState<PermissionRequest | null>(null);
  const [permissionResolver, setPermissionResolver] = useState<((response: { granted: boolean; remember: boolean }) => void) | null>(null);
  
  // Notification state
  const [notification, setNotification] = useState<PluginNotification | null>(null);
  
  useEffect(() => {
    // Setup IPC listeners for plugin events
    const handlePermissionRequest = (request: PermissionRequest) => {
      return new Promise<{ granted: boolean; remember: boolean }>((resolve) => {
        setPermissionRequest(request);
        setPermissionResolver(() => resolve);
      });
    };
    
    const handlePluginLoad = (data: { pluginId: string; pluginName?: string }) => {
      setNotification({
        type: 'load',
        ...data
      });
    };
    
    const handlePluginError = (data: {
      pluginId: string;
      error: string;
      details?: string;
    }) => {
      setNotification({
        type: 'error',
        ...data
      });
    };
    
    // Register IPC handlers
    window.electron.on('plugin:permission-request', handlePermissionRequest);
    window.electron.on('plugin:loaded', handlePluginLoad);
    window.electron.on('plugin:error', handlePluginError);
    
    return () => {
      // Cleanup IPC handlers
      window.electron.removeAllListeners('plugin:permission-request');
      window.electron.removeAllListeners('plugin:loaded');
      window.electron.removeAllListeners('plugin:error');
    };
  }, []);
  
  const handlePermissionResponse = useCallback((response: {
    granted: boolean;
    remember: boolean;
  }) => {
    if (permissionResolver) {
      permissionResolver(response);
      setPermissionResolver(null);
      setPermissionRequest(null);
    }
  }, [permissionResolver]);
  
  const handleNotificationClose = useCallback(() => {
    setNotification(null);
  }, []);
  
  return (
    <>
      {/* Permission Request Dialog */}
      {permissionRequest && (
        <PermissionRequestDialog
          open={true}
          {...permissionRequest}
          onClose={handlePermissionResponse}
        />
      )}
      
      {/* Notifications */}
      {notification?.type === 'load' && (
        <PluginLoadNotification
          open={true}
          pluginId={notification.pluginId}
          pluginName={notification.pluginName}
          onClose={handleNotificationClose}
        />
      )}
      
      {notification?.type === 'error' && (
        <PluginErrorNotification
          open={true}
          pluginId={notification.pluginId}
          error={notification.error || 'Unknown error'}
          details={notification.details}
          onClose={handleNotificationClose}
        />
      )}
    </>
  );
};