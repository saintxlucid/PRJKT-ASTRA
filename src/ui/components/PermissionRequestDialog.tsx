/**
 * Permission request dialog component.
 * Displays plugin permission requests and collects user responses.
 */
import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  FormControlLabel,
  Checkbox
} from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';

interface Permission {
  name: string;
  description?: string;
}

interface PermissionRequestProps {
  open: boolean;
  pluginId: string;
  pluginName?: string;
  actionName: string;
  actionDescription?: string;
  permissions: Permission[];
  onClose: (response: { granted: boolean; remember: boolean }) => void;
}

export const PermissionRequestDialog: React.FC<PermissionRequestProps> = ({
  open,
  pluginId,
  pluginName,
  actionName,
  actionDescription,
  permissions,
  onClose
}) => {
  const [remember, setRemember] = useState(false);

  const handleAllow = () => {
    onClose({ granted: true, remember });
  };

  const handleDeny = () => {
    onClose({ granted: false, remember });
  };

  return (
    <Dialog open={open} maxWidth="sm" fullWidth>
      <DialogTitle>
        Permission Request
      </DialogTitle>
      <DialogContent>
        <Typography variant="subtitle1" gutterBottom>
          {pluginName || pluginId} requests permissions for {actionName}:
        </Typography>
        
        {actionDescription && (
          <Typography variant="body2" color="textSecondary" paragraph>
            {actionDescription}
          </Typography>
        )}
        
        <List>
          {permissions.map(permission => (
            <ListItem key={permission.name}>
              <ListItemIcon>
                <LockIcon />
              </ListItemIcon>
              <ListItemText
                primary={permission.name}
                secondary={permission.description}
              />
            </ListItem>
          ))}
        </List>
        
        <FormControlLabel
          control={
            <Checkbox
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
            />
          }
          label="Remember this decision"
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleDeny} color="inherit">
          Deny
        </Button>
        <Button onClick={handleAllow} color="primary" variant="contained">
          Allow
        </Button>
      </DialogActions>
    </Dialog>
  );
};