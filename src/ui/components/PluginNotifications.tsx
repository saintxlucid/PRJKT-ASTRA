/**
 * Plugin notification components.
 * Displays plugin load and error notifications.
 */
import React from 'react';
import { Alert, AlertTitle, Snackbar, Typography } from '@mui/material';

interface PluginLoadNotificationProps {
  open: boolean;
  pluginId: string;
  pluginName?: string;
  onClose: () => void;
}

export const PluginLoadNotification: React.FC<PluginLoadNotificationProps> = ({
  open,
  pluginId,
  pluginName,
  onClose
}) => (
  <Snackbar
    open={open}
    autoHideDuration={3000}
    onClose={onClose}
    anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
  >
    <Alert onClose={onClose} severity="info">
      <AlertTitle>Plugin Loaded</AlertTitle>
      {pluginName || pluginId} has been loaded successfully
    </Alert>
  </Snackbar>
);

interface PluginErrorNotificationProps {
  open: boolean;
  pluginId: string;
  error: string;
  details?: string;
  onClose: () => void;
}

export const PluginErrorNotification: React.FC<PluginErrorNotificationProps> = ({
  open,
  pluginId,
  error,
  details,
  onClose
}) => (
  <Snackbar
    open={open}
    autoHideDuration={6000}
    onClose={onClose}
    anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
  >
    <Alert onClose={onClose} severity="error">
      <AlertTitle>Plugin Error - {pluginId}</AlertTitle>
      {error}
      {details && (
        <Typography variant="body2" style={{ marginTop: 8 }}>
          {details}
        </Typography>
      )}
    </Alert>
  </Snackbar>
);